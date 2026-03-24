# rpa-project

DataWorks「离线表申请」表单自动化（Playwright Python）。

## 项目结构

- `app/`：入口 `main`、Excel `rpa_excel`、填表 `dataworks_hive_apply`、无头 Cookie `dw_cookies`
- `tests/`：`unittest` 单元测试（`test_rpa_excel` / `test_dw_cookies`）
- `scripts/`：辅助脚本（如无头 Cookie 登录探测）

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

**无头（上条命令，未加 `--debug`）** 需在 `rpa-project/.env` 或环境中配置三条 `RPA_TEST_COOKIE_*`（与 [`app/dw_cookies.py`](rpa-project/app/dw_cookies.py) 一致），否则会退出并提示；用于注入 Cookie 后免扫码进入任务列表。

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

单测覆盖范围：

| 模块 | 文件 | 内容概要 |
|------|------|----------|
| `rpa_excel` | `tests/test_rpa_excel.py` | `rpa` 表必填列/数仓分层/缺行与文件不存在等 |
| `dw_cookies` | `tests/test_dw_cookies.py` | `dw_cookies_from_env` 缺项与空白、`load_dw_dotenv` 从临时 `.env` 注入 |

**未覆盖**：Playwright 填表、`main._run` 端到端；这些依赖内网 DataWorks 与有效 Cookie，请用 `--debug` 或 `scripts/test_headless_cookies_login.py` 人工/实验验证。

### 无头模式 + 预置 Cookie（实验）

脚本 [`scripts/test_headless_cookies_login.py`](scripts/test_headless_cookies_login.py) 用于探测：在无头 Chromium 中写入 `dw`、`dw_username`、`dwdataworks` 等 Cookie 后访问任务列表，是否仍出现扫码/登录相关文案（**仅启发式判断**，请以截图或 `--headed` 为准）。

**勿把令牌写入仓库**。推荐在 **`rpa-project` 根目录** 放置 `.env`（已加入 `.gitignore`），脚本会通过 `python-dotenv` 自动加载其中的 `RPA_TEST_COOKIE_*`；也可继续使用 `export`：

```bash
# 方式 A：仅依赖 .env（需先 uv sync 安装 python-dotenv）
uv run python scripts/test_headless_cookies_login.py --screenshot /tmp/dw-cookie-test.png

# 方式 B：环境变量
export RPA_TEST_COOKIE_DW='…'
export RPA_TEST_COOKIE_DW_USERNAME='…'
export RPA_TEST_COOKIE_DWDATAWORKS='…'
uv run python scripts/test_headless_cookies_login.py
```

`.env` 示例（等号两侧不要多余空格；JWT 很长时一般无需引号）：

```env
RPA_TEST_COOKIE_DW=12334
RPA_TEST_COOKIE_DW_USERNAME=your_name
RPA_TEST_COOKIE_DWDATAWORKS=eyJ...
```

可选 `--headed` 打开有头窗口对照；JWT 过期或 Cookie 与线上一致性不足时会失败。domain 与变量名统一维护在 [`app/dw_cookies.py`](rpa-project/app/dw_cookies.py)（`python -m app.main` 无头模式共用）。

## 说明

- 访问地址为内网。**`--debug`**：在浏览器中手动登录（扫码等），终端按提示回车继续。**非 debug 无头**：依赖 `.env` 中 Cookie，无终端登录步骤。
- **非 debug**（无头）时，填表结束后会自动尝试点击「提交」；**`--debug`** 时不会自动提交，便于核对后再手动提交。
- **数据描述、建表语句、存储路径**从 Excel 工作表 **`rpa`** 读取：第 1 行为表头（列名须含 `数据描述信息`、`建表语句`、`存储路径值`），第 2 行为数据。可选列 **`数仓分层`**（如 `ods` / `DWD`）用于「数仓分层」下拉；缺列或空单元格时默认 `ODS`。映射见 `app/rpa_excel.py`。
- 成功结束时终端会打印提示；在 macOS 上还会尝试发送系统通知。
