"""DataWorks 离线 Hive 表申请 RPA 入口。"""

from __future__ import annotations

import argparse
import asyncio
import subprocess
import sys
import time
from pathlib import Path

from playwright.async_api import Page, async_playwright

from app.dataworks_hive_apply import run_apply, try_click_submit
from app.dw_cookies import (
    ENV_DW,
    ENV_DW_USERNAME,
    ENV_DWDATAWORKS,
    dw_cookies_from_env,
    load_dw_dotenv,
)
from app.rpa_excel import default_excel_path, load_rpa_sheet_hive_rows, update_row_status

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


async def _goto_task_list_ready(page: Page) -> None:
    await page.goto(DATAWORKS_TASK_LIST, wait_until="domcontentloaded")
    try:
        await page.wait_for_load_state("networkidle", timeout=15_000)
    except Exception:
        await page.wait_for_timeout(2000)


async def _run(debug: bool, excel_path: Path) -> None:
    rows = load_rpa_sheet_hive_rows(excel_path)
    print(
        f"已从 Excel 读取: {excel_path}，有效 Hive 申请 {len(rows)} 条。\n",
        flush=True,
    )
    if not rows:
        print(
            "没有需要执行的 Hive 行（可能均为 clickhouse、未知表类型或已跳过）。\n",
            flush=True,
        )
        return

    launch_kwargs: dict = {"headless": not debug}
    if debug:
        launch_kwargs["slow_mo"] = 80

    async with async_playwright() as p:
        browser = await p.chromium.launch(**launch_kwargs)
        context = await browser.new_context()

        if not debug:
            load_dw_dotenv()
            cookies = dw_cookies_from_env()
            if cookies is None:
                print(
                    "\n无头模式需要登录 Cookie：请在 rpa-project/.env 或环境中设置（缺一不可）：\n"
                    f"  {ENV_DW}\n"
                    f"  {ENV_DW_USERNAME}\n"
                    f"  {ENV_DWDATAWORKS}\n"
                    "\n调试请使用: uv run python -m app.main --debug\n",
                    file=sys.stderr,
                    flush=True,
                )
                await browser.close()
                raise SystemExit(1)
            await context.add_cookies(cookies)

        page = await context.new_page()
        await _goto_task_list_ready(page)

        if debug:
            print(
                "\n请在浏览器中完成内网登录（扫码等）。确认已进入任务列表后，回到终端继续。\n",
                flush=True,
            )
            await asyncio.to_thread(
                input,
                "登录完成并进入任务列表后按回车继续... ",
            )

        t0 = time.perf_counter()
        total = len(rows)
        for i, row in enumerate(rows):
            if i > 0:
                await _goto_task_list_ready(page)

            print(
                f"--- 处理第 {i + 1}/{total} 条 Hive 申请 ---\n",
                flush=True,
            )

            try:
                await run_apply(page, row)
            except Exception as exc:
                print(
                    f"第 {i + 1} 条填写失败: {exc}\n",
                    flush=True,
                )
                update_row_status(excel_path, row.excel_row, "失败")
                continue

            if debug:
                print(
                    "说明：debug 模式下不会自动点击「提交」；"
                    "请在浏览器中手动点击提交按钮，完成后回到终端按回车继续下一条。\n",
                    flush=True,
                )
                await asyncio.to_thread(
                    input,
                    f"[debug] 第 {i + 1}/{total} 条已填写完毕，手动提交后按回车继续... ",
                )
                update_row_status(excel_path, row.excel_row, "成功")
            else:
                submitted = await try_click_submit(page, timeout_ms=10_000)
                status = "成功" if submitted else "失败"
                update_row_status(excel_path, row.excel_row, status)
                if submitted:
                    print("已尝试点击页面「提交」按钮。\n", flush=True)
                else:
                    print(
                        "未在超时内找到可点击的「提交」按钮，请手动检查页面后提交。\n",
                        flush=True,
                    )
                await page.wait_for_timeout(1500)

        elapsed = time.perf_counter() - t0

        _notify_success(
            f"离线表申请流程已执行完毕（共 {total} 条，耗时 {elapsed:.1f}s）"
        )

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
            "create-table-output/YYYYMMDD/create_table_info.xlsx（运行当日）"
        ),
    )
    args = parser.parse_args()
    excel_path = args.excel if args.excel is not None else default_excel_path()
    asyncio.run(_run(args.debug, excel_path.resolve()))


if __name__ == "__main__":
    main()
