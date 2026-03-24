"""
无头模式下验证：预置 DataWorks 相关 Cookie 后是否可跳过扫码登录。

配置方式（任选，勿将令牌提交到 Git）：

1. 在 rpa-project 根目录创建 `.env`（已 gitignore），例如：

   RPA_TEST_COOKIE_DW=12334
   RPA_TEST_COOKIE_DW_USERNAME=sunpeng9
   RPA_TEST_COOKIE_DWDATAWORKS=<JWT 字符串>

   JWT 若含特殊字符，可用单引号包裹整段值（见 dotenv 文档）。

2. 或在 shell 中 export 同名环境变量后运行脚本。

  uv run python scripts/test_headless_cookies_login.py

可选：--headed 有头对照；--screenshot path.png 保存页面截图便于人工判断。

Cookie 的加载与 domain 与 `app.main` 无头模式一致，实现见 `app/dw_cookies.py`。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

from app.dw_cookies import (
    ENV_DW,
    ENV_DW_USERNAME,
    ENV_DWDATAWORKS,
    dw_cookies_from_env,
    load_dw_dotenv,
)

DATAWORKS_ORIGIN = "http://dataworks.sina.com.cn"
DATAWORKS_TASK_LIST = f"{DATAWORKS_ORIGIN}/#/task/list"


def main() -> int:
    parser = argparse.ArgumentParser(description="无头 Cookie 登录探测（DataWorks）")
    parser.add_argument(
        "--headed",
        action="store_true",
        help="有头模式，便于与无头结果对照",
    )
    parser.add_argument(
        "--screenshot",
        type=Path,
        default=None,
        help="保存整页截图路径（默认不保存）",
    )
    parser.add_argument(
        "--timeout-ms",
        type=int,
        default=60_000,
        help="goto 超时（毫秒）",
    )
    args = parser.parse_args()

    load_dw_dotenv()
    cookies = dw_cookies_from_env()
    if cookies is None:
        print(
            "未读取到 Cookie：请在 rpa-project/.env 或环境中设置（缺一不可）：\n"
            f"  {ENV_DW}\n"
            f"  {ENV_DW_USERNAME}\n"
            f"  {ENV_DWDATAWORKS}\n",
            file=sys.stderr,
        )
        return 2

    login_like_substrings = ("扫码", "请登录", "二维码", "微信")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.headed)
        context = browser.new_context()
        context.add_cookies(cookies)
        page = context.new_page()
        page.goto(DATAWORKS_TASK_LIST, wait_until="domcontentloaded", timeout=args.timeout_ms)
        page.wait_for_timeout(2500)
        url = page.url
        text = ""
        try:
            text = page.inner_text("body")
        except Exception:
            text = page.content()

        lower = text.lower()
        hits = [s for s in login_like_substrings if s.lower() in lower]

        if args.screenshot:
            args.screenshot.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(args.screenshot), full_page=True)
            print(f"已保存截图: {args.screenshot.resolve()}")

        print(f"当前 URL: {url}")
        print(
            "页面是否出现典型「未登录/扫码」文案: "
            + ("是 — " + ", ".join(hits) if hits else "未发现上述关键字（可能已登录或 DOM 不同）")
        )
        print(
            "\n结论仅供参考：请以截图或 --headed 实际页面为准；"
            "JWT 过期或 domain 不匹配时仍会要求登录。"
        )

        browser.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
