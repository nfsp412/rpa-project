"""DataWorks 离线 Hive 表申请 RPA 入口。"""

from __future__ import annotations

import argparse
import asyncio
import subprocess
import sys
import time
from pathlib import Path

from playwright.async_api import async_playwright

from app.dataworks_hive_apply import run_apply, try_click_submit
from app.rpa_excel import default_excel_path, load_rpa_sheet_row

DATAWORKS_TASK_LIST = "http://dataworks.sina.com.cn/#/task/list"


def _notify_success(message: str) -> None:
    line = "=" * 60
    print(f"\n{line}\n✓ {message}\n{line}\n")
    if sys.platform == "darwin":
        safe = message.replace('"', "'")
        try:
            subprocess.run(
                [
                    "osascript",
                    "-e",
                    f'display notification "{safe}" with title "RPA 离线表申请"',
                ],
                check=False,
                capture_output=True,
            )
        except OSError:
            pass


async def _run(debug: bool, excel_path: Path) -> None:
    launch_kwargs: dict = {"headless": not debug}
    if debug:
        launch_kwargs["slow_mo"] = 80

    row = load_rpa_sheet_row(excel_path)
    print(f"已从 Excel 读取表单数据: {excel_path}\n", flush=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(**launch_kwargs)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(DATAWORKS_TASK_LIST, wait_until="domcontentloaded")

        print(
            "\n请在浏览器中完成内网登录（扫码等）。确认已进入任务列表后，回到终端继续。\n",
            flush=True,
        )
        await asyncio.to_thread(
            input,
            "登录完成并进入任务列表后按回车继续... ",
        )
        try:
            await page.wait_for_load_state("networkidle", timeout=15_000)
        except Exception:
            await page.wait_for_timeout(2000)

        t0 = time.perf_counter()
        await run_apply(page, row)
        elapsed = time.perf_counter() - t0

        if debug:
            print(
                "说明：debug 模式下不会自动点击「提交」；需要提交时请手动操作。\n",
                flush=True,
            )
        else:
            submitted = await try_click_submit(page, timeout_ms=10_000)
            if submitted:
                print("已尝试点击页面「提交」按钮。\n", flush=True)
            else:
                print(
                    "未在超时内找到可点击的「提交」按钮，请手动检查页面后提交。\n",
                    flush=True,
                )

        _notify_success(f"离线表申请流程已执行完毕（耗时 {elapsed:.1f}s）")

        if debug:
            print(
                "\n[debug] 浏览器将保持打开，便于核对页面填写内容。"
                "确认完毕后回到终端按回车再关闭浏览器。\n",
                flush=True,
            )
            await asyncio.to_thread(
                input,
                "[debug] 按回车关闭浏览器... ",
            )

        await browser.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "DataWorks 离线 Hive 表申请自动化。首次运行前请执行: playwright install chromium"
        ),
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="有头模式并放慢操作；流程结束后暂停，按回车再关闭浏览器",
    )
    parser.add_argument(
        "--excel",
        type=Path,
        default=None,
        help=(
            "create_table_info.xlsx 路径；默认与 rpa-project 同级目录下的 "
            "create-table-output/20260323/create_table_info.xlsx"
        ),
    )
    args = parser.parse_args()
    excel_path = args.excel if args.excel is not None else default_excel_path()
    asyncio.run(_run(args.debug, excel_path.resolve()))


if __name__ == "__main__":
    main()
