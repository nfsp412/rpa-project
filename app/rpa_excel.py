"""从 create_table_info.xlsx 的 `rpa` 工作表读取 RPA 表单字段。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from openpyxl import load_workbook

SHEET_NAME = "rpa"
HEADER_TABLE_DESCRIPTION = "数据描述信息"
HEADER_DDL = "建表语句"
HEADER_STORAGE_PATH = "存储路径值"
HEADER_WAREHOUSE_LAYER = "数仓分层"

_DEFAULT_WAREHOUSE_LAYER = "ODS"


def default_excel_path() -> Path:
    """与 rpa-project 同级的 create-table-output/.../create_table_info.xlsx。"""
    rpa_project_root = Path(__file__).resolve().parent.parent
    workspace_root = rpa_project_root.parent
    return (
        workspace_root
        / "create-table-output"
        / "20260323"
        / "create_table_info.xlsx"
    )


@dataclass(frozen=True)
class RpaSheetRow:
    table_description: str
    ddl_sql: str
    storage_path: str
    warehouse_layer: str


def _cell_str(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_warehouse_layer(raw: str) -> str:
    """与 DataWorks 下拉 option 文案对齐：空则默认 ODS，否则 strip 后转大写。"""
    s = raw.strip()
    if not s:
        return _DEFAULT_WAREHOUSE_LAYER
    return s.upper()


def load_rpa_sheet_row(xlsx_path: Path) -> RpaSheetRow:
    if not xlsx_path.is_file():
        raise FileNotFoundError(f"未找到 Excel 文件: {xlsx_path}")

    wb = load_workbook(xlsx_path, read_only=True, data_only=True)
    try:
        if SHEET_NAME not in wb.sheetnames:
            raise ValueError(
                f"工作簿中不存在工作表 {SHEET_NAME!r}，现有: {wb.sheetnames}"
            )
        ws = wb[SHEET_NAME]
        rows = ws.iter_rows(min_row=1, max_row=2, values_only=True)
        try:
            header_row = next(rows)
        except StopIteration as e:
            raise ValueError(f"工作表 {SHEET_NAME!r} 为空") from e

        headers = [_cell_str(h) for h in header_row]
        idx: dict[str, int] = {}
        for i, name in enumerate(headers):
            if name and name not in idx:
                idx[name] = i

        missing = [
            h
            for h in (
                HEADER_TABLE_DESCRIPTION,
                HEADER_DDL,
                HEADER_STORAGE_PATH,
            )
            if h not in idx
        ]
        if missing:
            raise ValueError(
                f"表头缺少列: {missing}。当前表头: {[h for h in headers if h]}"
            )

        try:
            data_row = next(rows)
        except StopIteration as e:
            raise ValueError(
                f"工作表 {SHEET_NAME!r} 没有数据行（至少需要第 2 行）"
            ) from e

        def col(key: str) -> str:
            i = idx[key]
            if i >= len(data_row):
                return ""
            return _cell_str(data_row[i])

        if HEADER_WAREHOUSE_LAYER in idx:
            layer_raw = col(HEADER_WAREHOUSE_LAYER)
        else:
            layer_raw = ""

        return RpaSheetRow(
            table_description=col(HEADER_TABLE_DESCRIPTION),
            ddl_sql=col(HEADER_DDL),
            storage_path=col(HEADER_STORAGE_PATH),
            warehouse_layer=_normalize_warehouse_layer(layer_raw),
        )
    finally:
        wb.close()
