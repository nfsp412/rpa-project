"""
DataWorks「离线表申请」表单自动化步骤（由 Playwright codegen TS 翻译而来）。

说明：
- 多个「请选择」使用 .nth(4) 等与录制一致的顺序定位，依赖当前页面 DOM 顺序；改版后需调整。
- 录制末尾未包含「提交」；现阶段 main 不自动点击「提交」（测试开发阶段）。
"""

from __future__ import annotations

import asyncio
import re
import time

from playwright.async_api import Locator, Page, TimeoutError as PlaywrightTimeoutError

from app.rpa_excel import RpaSheetRow


async def _fill_ace_ddl(page: Page, sql: str) -> None:
    """
    表 Schema 使用 ACE：.ace_content 会拦截对隐藏 textarea 的 click()。
    优先用页面全局 ace.edit 写 session；否则对 textarea focus() + fill（勿 click）。
    """
    wrap = page.locator("#aceEditorWrap")
    if await wrap.count() > 0:
        await wrap.scroll_into_view_if_needed()

    via_ace = await page.evaluate(
        """sql => {
            const g = window;
            const ace = g.ace;
            if (!ace || typeof ace.edit !== 'function') return false;
            const host = document.querySelector('#aceEditorWrap .ace_editor');
            if (!host) return false;
            try {
                const ed = ace.edit(host);
                ed.setValue(sql, -1);
                ed.clearSelection();
                return true;
            } catch (e) {
                return false;
            }
        }""",
        sql,
    )
    if via_ace:
        return

    ta = (
        wrap.locator("textarea.ace_text-input")
        if await wrap.count() > 0
        else page.locator("textarea.ace_text-input").first
    )
    await ta.wait_for(state="attached", timeout=15_000)
    await ta.focus()
    await ta.fill(sql)
    await ta.evaluate(
        """el => {
            el.dispatchEvent(new InputEvent('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
        }"""
    )


def _label_pattern(label: str, *, exact: bool) -> re.Pattern[str]:
    return re.compile(f"^{re.escape(label)}$") if exact else re.compile(re.escape(label))


async def _visible_cascader_panel(page: Page, timeout_ms: int = 15_000) -> Locator | None:
    """返回第一个可见的 .el-cascader-panel，超时返回 None。"""
    deadline = time.monotonic() + timeout_ms / 1000.0
    while time.monotonic() < deadline:
        panels = page.locator(".el-cascader-panel")
        for i in range(await panels.count()):
            p = panels.nth(i)
            if await p.is_visible():
                return p
        await asyncio.sleep(0.1)
    return None


async def _click_cascader_node_in_menu(menu: Locator, pattern: re.Pattern[str]) -> None:
    """点击级联某一列中的整行节点（避免只点 __label 导致未真正选中）。"""
    # 优先可交互行：li.el-cascader-node / [role=menuitem]
    row = menu.locator(".el-cascader-node").filter(has_text=pattern)
    if await row.count() == 0:
        row = menu.get_by_role("menuitem", name=pattern)
    await row.first.click()


async def _try_click_radio_on_cascader_leaf(menu: Locator, leaf_label: str) -> bool:
    """
    部分页面在级联叶子行内嵌 el-radio：仅点整行不会勾选，需点 .el-radio__inner 或原生 input。
    仅在给定 menu 列内查找文案匹配的节点。
    """
    pattern = _label_pattern(leaf_label, exact=True)
    nodes = menu.locator(".el-cascader-node").filter(has_text=pattern)
    if await nodes.count() == 0:
        return False
    node = nodes.first
    inner = node.locator(".el-radio__inner")
    if await inner.count() > 0 and await inner.first.is_visible():
        await inner.first.click()
        return True
    inp = node.locator("input[type='radio']")
    if await inp.count() > 0:
        await inp.first.click(force=True)
        return True
    return False


async def _click_theme_leaf_radio_in_form(page: Page, leaf_label: str) -> None:
    """仅在「* 主题」所在表单项内点叶子 radio，避免点到「用户主题」。"""
    theme_item = page.locator(".el-form-item").filter(
        has=page.get_by_role("textbox", name="* 主题")
    )
    pattern = _label_pattern(leaf_label, exact=True)
    by_role = theme_item.get_by_role("radio", name=pattern)
    if await by_role.count() > 0:
        await by_role.first.click()
        return
    lab = theme_item.locator("label.el-radio").filter(has_text=pattern)
    if await lab.count() > 0:
        await lab.first.click()
        return
    wrap = theme_item.locator(".el-radio").filter(has_text=pattern)
    if await wrap.count() > 0:
        inner = wrap.first.locator(".el-radio__inner")
        if await inner.count() > 0:
            await inner.first.click()
            return


async def _select_business_party_dw_ad(page: Page) -> None:
    """
    业务方两级均为 dw_ad：Element Plus Cascader 需在「同一 panel」内按列点整行节点，
    第二列展开后再点；不能用全局 text 或只点 label，否则看起来点了但值未写入。
    """
    await page.get_by_role("textbox", name="* 业务方").click()
    visible_panel = await _visible_cascader_panel(page)
    if visible_panel is None:
        await _click_visible_dropdown_option(page, "dw_ad", pick="first")
        await asyncio.sleep(0.3)
        await _click_visible_dropdown_option(page, "dw_ad", pick="last")
        return

    pattern = _label_pattern("dw_ad", exact=True)
    menus = visible_panel.locator(".el-cascader-menu")
    await menus.first.wait_for(state="visible", timeout=10_000)
    await _click_cascader_node_in_menu(menus.nth(0), pattern)

    # 等待第二列菜单出现（同一 panel 内 ul 数量增加）
    deadline = time.monotonic() + 10.0
    while time.monotonic() < deadline:
        cnt = await menus.count()
        if cnt >= 2 and await menus.nth(1).is_visible():
            break
        await asyncio.sleep(0.08)
    else:
        raise PlaywrightTimeoutError("业务方级联第二列未在 10s 内出现")

    await _click_cascader_node_in_menu(menus.nth(1), pattern)
    await asyncio.sleep(0.2)
    # 若浮层仍打开，点一次空白处收起，避免影响后续定位
    await page.keyboard.press("Escape")


async def _select_theme_ad_weibo_fans_tong(page: Page) -> None:
    """
    「* 主题」三级：广告主题 → 微博广告 → 粉丝通广告。
    与业务方相同，在同一 .el-cascader-panel 内按列点整行节点；勿用表单上含「主题」
    的 .el-radio，否则会误触「用户主题」等其它表单项。
    叶子行若内嵌 el-radio，整行点击往往不会勾选，需在 panel 内点 radio 或回退到本表单项内点击。
    """
    labels = ("广告主题", "微博广告", "粉丝通广告")
    leaf = labels[-1]
    await page.get_by_role("textbox", name="* 主题").click()
    visible_panel = await _visible_cascader_panel(page)
    if visible_panel is None:
        for label in labels:
            await _click_visible_dropdown_option(page, label, exact=True)
            await asyncio.sleep(0.3)
        await _click_theme_leaf_radio_in_form(page, leaf)
        await page.keyboard.press("Escape")
        return

    menus = visible_panel.locator(".el-cascader-menu")
    await menus.first.wait_for(state="visible", timeout=10_000)
    for col_idx, label in enumerate(labels):
        pattern = _label_pattern(label, exact=True)
        await _click_cascader_node_in_menu(menus.nth(col_idx), pattern)
        if col_idx >= len(labels) - 1:
            break
        next_col = col_idx + 1
        deadline = time.monotonic() + 10.0
        while time.monotonic() < deadline:
            cnt = await menus.count()
            if cnt > next_col and await menus.nth(next_col).is_visible():
                break
            await asyncio.sleep(0.08)
        else:
            raise PlaywrightTimeoutError(
                f"主题级联第 {next_col + 1} 列未在 10s 内出现（已选 {labels[: col_idx + 1]}）"
            )

    await asyncio.sleep(0.2)
    last_col = len(labels) - 1
    radio_ok = await _try_click_radio_on_cascader_leaf(menus.nth(last_col), leaf)
    if not radio_ok:
        for i in range(await menus.count()):
            if await _try_click_radio_on_cascader_leaf(menus.nth(i), leaf):
                radio_ok = True
                break
    if not radio_ok:
        panel_node = visible_panel.locator(".el-cascader-node").filter(
            has_text=_label_pattern(leaf, exact=True)
        )
        inner = panel_node.locator(".el-radio__inner")
        if await inner.count() > 0 and await inner.first.is_visible():
            await inner.first.click()
            radio_ok = True
    if not radio_ok:
        await _click_theme_leaf_radio_in_form(page, leaf)

    await asyncio.sleep(0.15)
    await page.keyboard.press("Escape")


async def _click_visible_dropdown_option(
    page: Page,
    label: str,
    *,
    exact: bool = True,
    timeout_ms: int = 15_000,
    pick: str = "first",
) -> None:
    """
    在当前「可见」的 Element Plus 下拉/级联浮层内点击选项。

    避免使用全局 get_by_text().first：页面上常有隐藏模板里的同名节点，会报 not visible。
    优先点击可选中行（.el-cascader-node、.el-select-dropdown__item），避免只点 __label。
    pick: \"first\" / \"last\" 在多个可见浮层均有匹配时的取舍。
    """
    pattern = _label_pattern(label, exact=exact)
    selectors = (
        ".el-select-dropdown",
        ".el-cascader__dropdown",
        ".el-cascader-panel",
        "div.el-popper",
    )
    # 不把 .el-cascader-node__label 作为点击目标，避免选中态不生效
    row_selectors = (
        ".el-cascader-node",
        ".el-select-dropdown__item",
        ".el-option",
        "[role='menuitem']",
        "[role='option']",
    )
    row_locator = ", ".join(row_selectors)
    deadline = time.monotonic() + timeout_ms / 1000.0
    while time.monotonic() < deadline:
        candidates: list = []
        for container_sel in selectors:
            containers = page.locator(container_sel)
            n = await containers.count()
            for i in range(n):
                box = containers.nth(i)
                if not await box.is_visible():
                    continue
                hit = box.locator(row_locator).filter(has_text=pattern)
                if await hit.count() == 0:
                    continue
                candidates.append(hit.first)
        if candidates:
            loc = candidates[-1] if pick == "last" else candidates[0]
            await loc.click()
            return
        await asyncio.sleep(0.1)
    raise PlaywrightTimeoutError(
        f'未在可见下拉中找到选项 {label!r}（{timeout_ms}ms）'
    )


async def _select_nth_placeholder(page: Page, index: int = 4) -> None:
    """点击第 n 个仅文案为「请选择」的 div（与录制一致，易受页面结构影响）。"""
    await page.locator("div").filter(has_text=re.compile(r"^请选择$")).nth(index).click()


async def run_apply(page: Page, row: RpaSheetRow) -> None:
    await page.locator("div").filter(has_text=re.compile(r"^离线数仓$")).click()
    await page.get_by_role("link", name="离线表申请").click()

    await _select_business_party_dw_ad(page)

    await page.get_by_role("textbox", name="* 产品业务线").click()
    await page.get_by_text("SINA", exact=True).click()
    await page.get_by_text("Weibo", exact=True).click()
    await page.get_by_text("Weibo AD").click()
    await page.get_by_text("微博超级粉丝通").click()
    await page.get_by_text("基础业务线").click()

    await _select_nth_placeholder(page, 4)
    await page.get_by_role("option", name="dw_ad_etl").click()

    await page.get_by_role("textbox", name="* 数据名").click()
    await page.get_by_role("textbox", name="* 数据名").fill(row.table_description)

    await page.locator("#editor_tableDataDesc-textarea").click()
    await page.locator("#editor_tableDataDesc-textarea").fill(row.table_description)

    await _select_theme_ad_weibo_fans_tong(page)

    await page.get_by_text("一键复制基础信息", exact=False).click()

    await _select_nth_placeholder(page, 4)
    await page.get_by_role("option", name="A").click()

    await _select_nth_placeholder(page, 4)
    await page.get_by_role("option", name=row.warehouse_layer).click()

    await page.get_by_role("textbox", name="* 保留天数").click()
    await page.get_by_role("textbox", name="* 保留天数").fill("720")

    await page.get_by_role("textbox", name="* 申请说明").click()
    await page.get_by_role("textbox", name="* 申请说明").fill(row.table_description)

    await _select_nth_placeholder(page, 4)
    await page.get_by_role("option", name="default").click()

    await _fill_ace_ddl(page, row.ddl_sql)

    await page.get_by_role("textbox", name="存储路径").click()
    await page.get_by_role("textbox", name="存储路径").fill(row.storage_path)

    await page.locator("div").filter(has_text=re.compile(r"^建表后自动授权的角色$")).nth(4).click()
    await page.get_by_role("option", name="role_mis").click()
    await page.get_by_role("option", name="role_dw_ad").click()

    await page.get_by_role("group", name="* 表Schema").click()


async def try_click_submit(page: Page, timeout_ms: int = 3000) -> bool:
    """若存在可见「提交」按钮则点击。无头模式（非 --debug）下由 main 在 run_apply 之后调用。"""
    try:
        btn = page.get_by_role("button", name=re.compile("提交"))
        await btn.first.click(timeout=timeout_ms)
        return True
    except PlaywrightTimeoutError:
        return False
