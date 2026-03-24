"""
DataWorks 无头登录用 Cookie：从 .env / 环境变量读取，供 main 与 scripts 复用。
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ENV_DW = "RPA_TEST_COOKIE_DW"
ENV_DW_USERNAME = "RPA_TEST_COOKIE_DW_USERNAME"
ENV_DWDATAWORKS = "RPA_TEST_COOKIE_DWDATAWORKS"


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_dw_dotenv() -> None:
    """加载 rpa-project/.env，再加载当前工作目录 .env（后者可覆盖）。"""
    load_dotenv(_project_root() / ".env")
    load_dotenv()


def dw_cookies_from_env() -> list[dict[str, str]] | None:
    """
    若三项环境变量均非空，返回 Playwright context.add_cookies 用列表；
    否则返回 None。domain 与浏览器 DevTools 中常见配置一致。
    """
    dw = os.environ.get(ENV_DW, "").strip()
    user = os.environ.get(ENV_DW_USERNAME, "").strip()
    token = os.environ.get(ENV_DWDATAWORKS, "").strip()
    if not dw or not user or not token:
        return None
    return [
        {"name": "dw", "value": dw, "domain": ".sina.com.cn", "path": "/"},
        {
            "name": "dw_username",
            "value": user,
            "domain": "dataworks.sina.com.cn",
            "path": "/",
        },
        {
            "name": "dwdataworks",
            "value": token,
            "domain": ".dataworks.sina.com.cn",
            "path": "/",
        },
    ]
