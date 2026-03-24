# rpa-project

DataWorks「离线表申请」表单自动化（Playwright Python）。

## 项目结构

- `app/`：入口 `main`、Excel 读取 `rpa_excel`、填表步骤 `dataworks_hive_apply`
- `tests/`：`unittest` 单元测试（当前覆盖 `rpa_excel` 解析逻辑）

命令行入口：`uv run python -m app.main` 或 `uv run rpa`（见 `pyproject.toml` 的 `[project.scripts]`）。

## 准备

```bash
uv sync
playwright install chromium
```

## 运行

```bash
uv run python -m app.main
```

有头调试（内网扫码、观察填写；**流程结束后浏览器保持打开，终端按回车再关闭**）：

```bash
uv run python -m app.main --debug
```

指定 Excel（**默认路径**与 `app/rpa_excel.py` 中 `default_excel_path()` 一致：与 `rpa-project` 同级目录下 `create-table-output/20260323/create_table_info.xlsx`；更换默认目录或日期请直接改该函数）：

```bash
uv run python -m app.main --excel /path/to/create_table_info.xlsx
```

也可使用入口脚本：`uv run rpa` / `uv run rpa --debug`。

## 测试

使用标准库 `unittest`（不额外安装 pytest）。在 **`rpa-project` 根目录**执行：

```bash
uv run python -m unittest discover -s tests -p "test_*.py" -v
```

当前用例仅校验 Excel `rpa` 表解析与数仓分层默认值等纯逻辑；完整页面流程依赖内网 DataWorks，未做浏览器端到端自动化测试。

## 说明

- 访问地址为内网，需在浏览器中完成登录；终端出现提示后，登录完成再按回车继续。
- **非 debug**（无头）时，填表结束后会自动尝试点击「提交」；**`--debug`** 时不会自动提交，便于核对后再手动提交。
- **数据描述、建表语句、存储路径**从 Excel 工作表 **`rpa`** 读取：第 1 行为表头（列名须含 `数据描述信息`、`建表语句`、`存储路径值`），第 2 行为数据。可选列 **`数仓分层`**（如 `ods` / `DWD`）用于「数仓分层」下拉；缺列或空单元格时默认 `ODS`。映射见 `app/rpa_excel.py`。
- 成功结束时终端会打印提示；在 macOS 上还会尝试发送系统通知。
