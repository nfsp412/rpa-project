"""app.dw_cookies：环境变量与 .env 加载行为单元测试。"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app.dw_cookies as dc
from app.dw_cookies import (
    ENV_DW,
    ENV_DW_USERNAME,
    ENV_DWDATAWORKS,
    dw_cookies_from_env,
    load_dw_dotenv,
)


class TestDwCookiesFromEnv(unittest.TestCase):
    def setUp(self) -> None:
        self._saved: dict[str, str | None] = {
            ENV_DW: os.environ.get(ENV_DW),
            ENV_DW_USERNAME: os.environ.get(ENV_DW_USERNAME),
            ENV_DWDATAWORKS: os.environ.get(ENV_DWDATAWORKS),
        }

    def tearDown(self) -> None:
        for key, val in self._saved.items():
            if val is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = val

    def test_returns_none_if_any_missing(self) -> None:
        full = {ENV_DW: "1", ENV_DW_USERNAME: "2", ENV_DWDATAWORKS: "3"}
        for omit in (ENV_DW, ENV_DW_USERNAME, ENV_DWDATAWORKS):
            with self.subTest(omit=omit):
                for k in full:
                    os.environ.pop(k, None)
                for k, v in full.items():
                    if k != omit:
                        os.environ[k] = v
                self.assertIsNone(dw_cookies_from_env())

    def test_returns_none_when_all_unset(self) -> None:
        for k in (ENV_DW, ENV_DW_USERNAME, ENV_DWDATAWORKS):
            os.environ.pop(k, None)
        self.assertIsNone(dw_cookies_from_env())

    def test_returns_none_if_value_blank(self) -> None:
        os.environ[ENV_DW] = "1"
        os.environ[ENV_DW_USERNAME] = "  "
        os.environ[ENV_DWDATAWORKS] = "t"
        self.assertIsNone(dw_cookies_from_env())

    def test_returns_playwright_cookie_list(self) -> None:
        os.environ[ENV_DW] = "12334"
        os.environ[ENV_DW_USERNAME] = "user1"
        os.environ[ENV_DWDATAWORKS] = "jwt-here"
        got = dw_cookies_from_env()
        assert got is not None
        self.assertEqual(len(got), 3)
        self.assertEqual(
            {c["name"] for c in got},
            {"dw", "dw_username", "dwdataworks"},
        )
        by_name = {c["name"]: c for c in got}
        self.assertEqual(by_name["dw"]["domain"], ".sina.com.cn")
        self.assertEqual(by_name["dw_username"]["domain"], "dataworks.sina.com.cn")
        self.assertEqual(by_name["dwdataworks"]["domain"], ".dataworks.sina.com.cn")
        self.assertEqual(by_name["dw"]["value"], "12334")
        self.assertEqual(by_name["dw_username"]["value"], "user1")
        self.assertEqual(by_name["dwdataworks"]["value"], "jwt-here")
        for c in got:
            self.assertEqual(c["path"], "/")


class TestLoadDwDotenv(unittest.TestCase):
    def test_loads_vars_from_fake_project_root(self) -> None:
        keys = (ENV_DW, ENV_DW_USERNAME, ENV_DWDATAWORKS)
        old = {k: os.environ.get(k) for k in keys}
        try:
            for k in keys:
                os.environ.pop(k, None)
            with tempfile.TemporaryDirectory() as td:
                root = Path(td)
                (root / ".env").write_text(
                    f"{ENV_DW}=fromfile\n"
                    f"{ENV_DW_USERNAME}=u\n"
                    f"{ENV_DWDATAWORKS}=tok\n",
                    encoding="utf-8",
                )
                with patch.object(dc, "_project_root", return_value=root):
                    load_dw_dotenv()
            self.assertEqual(os.environ.get(ENV_DW), "fromfile")
            self.assertEqual(os.environ.get(ENV_DW_USERNAME), "u")
            self.assertEqual(os.environ.get(ENV_DWDATAWORKS), "tok")
        finally:
            for k in keys:
                os.environ.pop(k, None)
                if old[k] is not None:
                    os.environ[k] = old[k]


if __name__ == "__main__":
    unittest.main()
