"""rpa 工作表解析单元测试（unittest + 临时 xlsx）。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

from app.rpa_excel import (
    HEADER_DDL,
    HEADER_STORAGE_PATH,
    HEADER_TABLE_DESCRIPTION,
    HEADER_WAREHOUSE_LAYER,
    SHEET_NAME,
    load_rpa_sheet_row,
)


def _write_rpa_xlsx(path: Path, headers: list[str], row2: list[object] | None) -> None:
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = SHEET_NAME
    for c, h in enumerate(headers, start=1):
        ws.cell(row=1, column=c, value=h)
    if row2 is not None:
        for c, val in enumerate(row2, start=1):
            ws.cell(row=2, column=c, value=val)
    wb.save(path)


class TestLoadRpaSheetRow(unittest.TestCase):
    def test_warehouse_layer_from_cell_uppercases(self) -> None:
        headers = [
            HEADER_TABLE_DESCRIPTION,
            HEADER_DDL,
            HEADER_STORAGE_PATH,
            HEADER_WAREHOUSE_LAYER,
        ]
        row2 = ["desc", "CREATE TABLE t (i INT);", "/path", "dwd"]
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "t.xlsx"
            _write_rpa_xlsx(p, headers, row2)
            row = load_rpa_sheet_row(p)
        self.assertEqual(row.warehouse_layer, "DWD")
        self.assertEqual(row.table_description, "desc")
        self.assertIn("CREATE TABLE", row.ddl_sql)

    def test_warehouse_layer_defaults_when_column_absent(self) -> None:
        headers = [HEADER_TABLE_DESCRIPTION, HEADER_DDL, HEADER_STORAGE_PATH]
        row2 = ["d", "sql", "/p"]
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "t.xlsx"
            _write_rpa_xlsx(p, headers, row2)
            row = load_rpa_sheet_row(p)
        self.assertEqual(row.warehouse_layer, "ODS")

    def test_warehouse_layer_defaults_when_cell_empty(self) -> None:
        headers = [
            HEADER_TABLE_DESCRIPTION,
            HEADER_DDL,
            HEADER_STORAGE_PATH,
            HEADER_WAREHOUSE_LAYER,
        ]
        row2 = ["d", "sql", "/p", ""]
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "t.xlsx"
            _write_rpa_xlsx(p, headers, row2)
            row = load_rpa_sheet_row(p)
        self.assertEqual(row.warehouse_layer, "ODS")

    def test_raises_when_required_column_missing(self) -> None:
        headers = [HEADER_TABLE_DESCRIPTION, HEADER_STORAGE_PATH]
        row2 = ["d", "/p"]
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "t.xlsx"
            _write_rpa_xlsx(p, headers, row2)
            with self.assertRaises(ValueError) as ctx:
                load_rpa_sheet_row(p)
        self.assertIn(HEADER_DDL, str(ctx.exception))

    def test_raises_when_no_data_row(self) -> None:
        headers = [HEADER_TABLE_DESCRIPTION, HEADER_DDL, HEADER_STORAGE_PATH]
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "t.xlsx"
            _write_rpa_xlsx(p, headers, None)
            with self.assertRaises(ValueError) as ctx:
                load_rpa_sheet_row(p)
        self.assertIn("没有数据行", str(ctx.exception))

    def test_raises_file_not_found(self) -> None:
        with self.assertRaises(FileNotFoundError):
            load_rpa_sheet_row(Path("/nonexistent/dir/no.xlsx"))


if __name__ == "__main__":
    unittest.main()
