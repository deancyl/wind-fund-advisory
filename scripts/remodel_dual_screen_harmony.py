# -*- coding: utf-8 -*-
"""
scripts/remodel_dual_screen_harmony.py
全面重塑双端体验：
1. 修复移动端顶栏折行坍塌，实现左账本右 3 小图标（🎨, i, ↩️）单行弹性锁定；
2. 修复单行指数走廊横条与 ⚙️ / 🔄 刷新按钮，右侧锁定 34px 不折行、左侧横向平滑滚动；
3. 将一键重塑修改为 type="secondary"，确保全屏仅留唯一的 Primary 蓝色主操作按钮【生成调仓】；
4. 修复移动端次级 6 按钮为标准 3 列流式网格，压缩垂直厚度。
"""

import sys
import ast
import shutil
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
APP_GUI_FILE = WORKSPACE_ROOT / "app_gui.py"
MIRROR_GUI_FILE = WORKSPACE_ROOT / "AGY2_FundAdvisory" / "app_gui.py"


def apply_dual_screen_remodel():
    print("Reading app_gui.py...")
    with open(APP_GUI_FILE, "r", encoding="utf-8") as f:
        text = f.read()

    # 1. 在 CSS 中注入顶栏、行情条、处方条与工具条专用非折行规则
    css_injection = """
    /* =========================================================================
       方案 A 高定无侧栏双端响应式规约 (Dual-Screen Harmony Invariants)
       ========================================================================= */
    /* 1. 顶栏工具行在桌面与移动端均锁定为单行 Flex 弹性布局，杜绝阶梯折行 */
    div[data-testid="stHorizontalBlock"]:has(.topbar-ledger-marker) {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: center !important;
        gap: 4px !important;
        width: 100% !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.topbar-ledger-marker) > div[data-testid="column"]:first-child,
    div[data-testid="stHorizontalBlock"]:has(.topbar-ledger-marker) > div[data-testid="stColumn"]:first-child {
        flex: 1 1 auto !important;
        min-width: 0 !important;
        max-width: none !important;
        width: auto !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.topbar-ledger-marker) > div[data-testid="column"]:not(:first-child),
    div[data-testid="stHorizontalBlock"]:has(.topbar-ledger-marker) > div[data-testid="stColumn"]:not(:first-child) {
        flex: 0 0 34px !important;
        min-width: 34px !important;
        max-width: 34px !important;
        width: 34px !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.topbar-ledger-marker) button[data-testid="stPopoverButton"] {
        width: 32px !important;
        min-width: 32px !important;
        max-width: 32px !important;
        height: 32px !important;
        min-height: 32px !important;
        padding: 0 !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        border-radius: 6px !important;
    }

    /* 2. 顶部单行指数行情横条专用布局（桌面与移动端统一不换行，左滑右固） */
    div[data-testid="stHorizontalBlock"]:has(.ticker-strip-marker) {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: center !important;
        gap: 4px !important;
        width: 100% !important;
        margin-top: 2px !important;
        margin-bottom: 6px !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.ticker-strip-marker) > div[data-testid="column"]:first-child,
    div[data-testid="stHorizontalBlock"]:has(.ticker-strip-marker) > div[data-testid="stColumn"]:first-child {
        flex: 1 1 auto !important;
        min-width: 0 !important;
        max-width: none !important;
        width: auto !important;
        overflow-x: auto !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.ticker-strip-marker) > div[data-testid="column"]:not(:first-child),
    div[data-testid="stHorizontalBlock"]:has(.ticker-strip-marker) > div[data-testid="stColumn"]:not(:first-child) {
        flex: 0 0 34px !important;
        min-width: 34px !important;
        max-width: 34px !important;
        width: 34px !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.ticker-strip-marker) button {
        width: 32px !important;
        min-width: 32px !important;
        max-width: 32px !important;
        height: 32px !important;
        min-height: 32px !important;
        padding: 0 !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        font-size: 13px !important;
        border-radius: 6px !important;
    }

    /* 3. 处方重塑单行条防膨胀规约 */
    div[data-testid="stHorizontalBlock"]:has(.prescription-action-marker) {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: center !important;
        gap: 6px !important;
        margin-bottom: 6px !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.prescription-action-marker) > div[data-testid="column"]:first-child,
    div[data-testid="stHorizontalBlock"]:has(.prescription-action-marker) > div[data-testid="stColumn"]:first-child {
        flex: 0 0 auto !important;
        min-width: 90px !important;
        width: auto !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.prescription-action-marker) > div[data-testid="column"]:nth-child(2),
    div[data-testid="stHorizontalBlock"]:has(.prescription-action-marker) > div[data-testid="stColumn"]:nth-child(2) {
        flex: 0 0 34px !important;
        min-width: 34px !important;
        max-width: 34px !important;
        width: 34px !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.prescription-action-marker) > div[data-testid="column"]:last-child,
    div[data-testid="stHorizontalBlock"]:has(.prescription-action-marker) > div[data-testid="stColumn"]:last-child {
        flex: 1 1 auto !important;
        min-width: 0 !important;
        width: auto !important;
    }

    /* 4. 移动端 6 次级操作按钮 3 列标准紧凑流 */
    div[data-testid="stHorizontalBlock"]:has(.toolbar-3col-marker) {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 4px !important;
        width: 100% !important;
        margin-bottom: 4px !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.toolbar-3col-marker) > div[data-testid="column"],
    div[data-testid="stHorizontalBlock"]:has(.toolbar-3col-marker) > div[data-testid="stColumn"] {
        flex: 1 1 33.333% !important;
        min-width: calc(33.333% - 4px) !important;
        max-width: calc(33.333% - 4px) !important;
        width: 33.333% !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.toolbar-3col-marker) button {
        height: 34px !important;
        min-height: 34px !important;
        font-size: 12px !important;
        padding: 0 4px !important;
    }
"""
    # 替换 CSS 中媒体查询对于 selectbox 和 button 的过度拦截
    old_sel_rule = '''        div[data-testid="stHorizontalBlock"]:has([data-testid="stSelectbox"]) > div[data-testid="column"],
        div[data-testid="stHorizontalBlock"]:has([data-testid="stSelectbox"]) > div[data-testid="stColumn"] {'''
    new_sel_rule = '''        div[data-testid="stHorizontalBlock"]:has([data-testid="stSelectbox"]):not(:has(.topbar-ledger-marker)) > div[data-testid="column"],
        div[data-testid="stHorizontalBlock"]:has([data-testid="stSelectbox"]):not(:has(.topbar-ledger-marker)) > div[data-testid="stColumn"] {'''
    if old_sel_rule in text:
        text = text.replace(old_sel_rule, new_sel_rule, 1)
        print("  [OK] Excluded topbar-ledger-marker from blanket selectbox rule")

    old_btn_rule = '''        div[data-testid="stHorizontalBlock"]:has(button:not([data-testid*="stNumberInput"])):not(:has(.main-metric-card)):not(:has([data-testid="stNumberInput"])):not(:has([data-testid="stSelectbox"])):not(:has([data-testid="stPlotlyChart"])),
        div[data-testid="stHorizontalBlock"]:has([data-testid="stPopover"]):not(:has([data-testid="stNumberInput"])):not(:has([data-testid="stSelectbox"])):not(:has([data-testid="stPlotlyChart"])) {'''
    new_btn_rule = '''        div[data-testid="stHorizontalBlock"]:has(button:not([data-testid*="stNumberInput"])):not(:has(.main-metric-card)):not(:has([data-testid="stNumberInput"])):not(:has([data-testid="stSelectbox"])):not(:has([data-testid="stPlotlyChart"])):not(:has(.ticker-strip-marker)):not(:has(.topbar-ledger-marker)):not(:has(.prescription-action-marker)):not(:has(.toolbar-3col-marker)),
        div[data-testid="stHorizontalBlock"]:has([data-testid="stPopover"]):not(:has([data-testid="stNumberInput"])):not(:has([data-testid="stSelectbox"])):not(:has([data-testid="stPlotlyChart"])):not(:has(.ticker-strip-marker)):not(:has(.topbar-ledger-marker)):not(:has(.prescription-action-marker)):not(:has(.toolbar-3col-marker)) {'''
    if old_btn_rule in text:
        text = text.replace(old_btn_rule, new_btn_rule, 1)
        print("  [OK] Excluded custom markers from blanket button block rule")

    old_btn_rule2 = '''        div[data-testid="stHorizontalBlock"]:has(button:not([data-testid*="stNumberInput"])):not(:has(.main-metric-card)):not(:has([data-testid="stNumberInput"])):not(:has([data-testid="stSelectbox"])):not(:has([data-testid="stPlotlyChart"])) > div[data-testid="column"],
        div[data-testid="stHorizontalBlock"]:has(button:not([data-testid*="stNumberInput"])):not(:has(.main-metric-card)):not(:has([data-testid="stNumberInput"])):not(:has([data-testid="stSelectbox"])):not(:has([data-testid="stPlotlyChart"])) > div[data-testid="stColumn"],
        div[data-testid="stHorizontalBlock"]:has([data-testid="stPopover"]):not(:has([data-testid="stNumberInput"])):not(:has([data-testid="stSelectbox"])):not(:has([data-testid="stPlotlyChart"])) > div[data-testid="column"],
        div[data-testid="stHorizontalBlock"]:has([data-testid="stPopover"]):not(:has([data-testid="stNumberInput"])):not(:has([data-testid="stSelectbox"])):not(:has([data-testid="stPlotlyChart"])) > div[data-testid="stColumn"] {'''
    new_btn_rule2 = '''        div[data-testid="stHorizontalBlock"]:has(button:not([data-testid*="stNumberInput"])):not(:has(.main-metric-card)):not(:has([data-testid="stNumberInput"])):not(:has([data-testid="stSelectbox"])):not(:has([data-testid="stPlotlyChart"])):not(:has(.ticker-strip-marker)):not(:has(.topbar-ledger-marker)):not(:has(.prescription-action-marker)):not(:has(.toolbar-3col-marker)) > div[data-testid="column"],
        div[data-testid="stHorizontalBlock"]:has(button:not([data-testid*="stNumberInput"])):not(:has(.main-metric-card)):not(:has([data-testid="stNumberInput"])):not(:has([data-testid="stSelectbox"])):not(:has([data-testid="stPlotlyChart"])):not(:has(.ticker-strip-marker)):not(:has(.topbar-ledger-marker)):not(:has(.prescription-action-marker)):not(:has(.toolbar-3col-marker)) > div[data-testid="stColumn"],
        div[data-testid="stHorizontalBlock"]:has([data-testid="stPopover"]):not(:has([data-testid="stNumberInput"])):not(:has([data-testid="stSelectbox"])):not(:has([data-testid="stPlotlyChart"])):not(:has(.ticker-strip-marker)):not(:has(.topbar-ledger-marker)):not(:has(.prescription-action-marker)):not(:has(.toolbar-3col-marker)) > div[data-testid="column"],
        div[data-testid="stHorizontalBlock"]:has([data-testid="stPopover"]):not(:has([data-testid="stNumberInput"])):not(:has([data-testid="stSelectbox"])):not(:has([data-testid="stPlotlyChart"])):not(:has(.ticker-strip-marker)):not(:has(.topbar-ledger-marker)):not(:has(.prescription-action-marker)):not(:has(.toolbar-3col-marker)) > div[data-testid="stColumn"] {'''
    if old_btn_rule2 in text:
        text = text.replace(old_btn_rule2, new_btn_rule2, 1)
        print("  [OK] Excluded custom markers from blanket column width rule")

    # 在顶部 CSS block 插入 css_injection
    css_target = '    /* 顶部紧凑单行指数走廊横条 (Top Compact Index Ticker Strip) */'
    if css_target in text:
        text = text.replace(css_target, css_injection.replace("{", "{{").replace("}", "}}") + "\n" + css_target, 1)
        print("  [OK] Injected custom dual-screen CSS rules")

    # 2. 更新 topbar 标记与内容
    old_topbar_b = '''    safe_markdown_html(f"""<div style="display:flex;align-items:center;gap:8px;padding-top:4px;flex-wrap:wrap;">
        <span style="font-size:15px;font-weight:800;color:var(--text-primary);white-space:nowrap;">AGY2 智投</span>
        <span style="font-size:11px;padding:2px 6px;border-radius:4px;background:rgba(37,99,235,0.08);color:var(--accent-primary);border:1px solid rgba(37,99,235,0.22);">{data_src_badge}</span>
        <span style="font-size:11px;color:var(--text-muted);font-family:monospace;white-space:nowrap;">底座: {latest_date}</span>
    </div>""")'''
    new_topbar_b = '''    safe_markdown_html(f"""<div style="display:flex;align-items:center;gap:8px;padding-top:4px;flex-wrap:wrap;">
        <span style="font-size:15px;font-weight:800;color:var(--text-primary);white-space:nowrap;">AGY2 智投</span>
        <span style="font-size:11px;padding:2px 6px;border-radius:4px;background:rgba(37,99,235,0.08);color:var(--accent-primary);border:1px solid rgba(37,99,235,0.22);">{data_src_badge}</span>
        <span style="font-size:11px;color:var(--text-muted);font-family:monospace;white-space:nowrap;">底座: {latest_date}</span>
        <span style="font-size:11px;padding:2px 6px;border-radius:4px;background:var(--bg-surface);color:var(--text-secondary);border:1px solid var(--border-subtle);white-space:nowrap;">⏰ {clock_title}（{market_status.countdown_str}）</span>
    </div>""")'''
    if old_topbar_b in text:
        text = text.replace(old_topbar_b, new_topbar_b, 1)
        print("  [OK] Updated topbar left branding with clock summary")

    old_sel_ld = '''    with col_sel_ld:
        selected_lid = st.selectbox("当前激活账本", options=[l["id"] for l in all_ledgers], index=active_idx, format_func=_fmt_topbar_ledger, key=f"topbar_ledger_select_{active_lid}", label_visibility="collapsed")'''
    new_sel_ld = '''    with col_sel_ld:
        safe_markdown_html('<span class="topbar-ledger-marker"></span>')
        selected_lid = st.selectbox("当前激活账本", options=[l["id"] for l in all_ledgers], index=active_idx, format_func=_fmt_topbar_ledger, key=f"topbar_ledger_select_{active_lid}", label_visibility="collapsed")'''
    if old_sel_ld in text:
        text = text.replace(old_sel_ld, new_sel_ld, 1)
        print("  [OK] Injected topbar-ledger-marker")

    # 3. 更新 ticker strip 标记与刷新按钮图标
    old_ticker_col = '''col_idx_strip, col_idx_cfg, col_idx_rf = st.columns([8.4, 0.8, 0.8])
with col_idx_strip:
    pills_html = []'''
    new_ticker_col = '''col_idx_strip, col_idx_cfg, col_idx_rf = st.columns([8.4, 0.8, 0.8])
with col_idx_strip:
    safe_markdown_html('<span class="ticker-strip-marker"></span>')
    pills_html = []'''
    if old_ticker_col in text:
        text = text.replace(old_ticker_col, new_ticker_col, 1)
        print("  [OK] Injected ticker-strip-marker")

    old_rf_btn = 'if st.button("刷新", key="btn_refresh_all_live_quotes", help="极速刷新实时行情", use_container_width=True):'
    new_rf_btn = 'if st.button("🔄", key="btn_refresh_all_live_quotes", help="极速刷新实时行情", use_container_width=True):'
    if old_rf_btn in text:
        text = text.replace(old_rf_btn, new_rf_btn, 1)
        print("  [OK] Updated refresh button to compact icon 🔄")

    # 4. 更新一键重塑为 type="secondary"
    old_rx_btn = 'if st.button("一键重塑", key="btn_apply_combat29_rx", type="primary", use_container_width=True, help="三步瘦身重构：清扫19只免赎尾仓、011613 C转A置换、聚焦6只核心池"):'
    new_rx_btn = 'if st.button("🧹 一键重塑", key="btn_apply_combat29_rx", type="secondary", use_container_width=True, help="三步瘦身重构：清扫19只免赎尾仓、011613 C转A置换、聚焦6只核心池"):'
    if old_rx_btn in text:
        text = text.replace(old_rx_btn, new_rx_btn, 1)
        print("  [OK] Changed btn_apply_combat29_rx to type='secondary'")

    old_rx_block = 'col_rx_btn1, col_rx_info, col_rx_cap = st.columns([3.0, 0.8, 6.2])\n            with col_rx_btn1:'
    new_rx_block = 'col_rx_btn1, col_rx_info, col_rx_cap = st.columns([3.0, 0.8, 6.2])\n            with col_rx_btn1:\n                safe_markdown_html(\'<span class="prescription-action-marker"></span>\')'
    if old_rx_block in text:
        text = text.replace(old_rx_block, new_rx_block, 1)
        print("  [OK] Injected prescription-action-marker")

    # 5. 更新次级 6 按钮标记
    old_act_quick = 'with col_act_quick:\n            with st.popover("录基"'
    new_act_quick = 'with col_act_quick:\n            safe_markdown_html(\'<span class="toolbar-3col-marker"></span>\')\n            with st.popover("录基"'
    if old_act_quick in text:
        text = text.replace(old_act_quick, new_act_quick, 1)
        print("  [OK] Injected toolbar-3col-marker in col_act_quick")

    old_act_undo = 'with col_act_undo:\n            if st.button("撤销修改"'
    new_act_undo = 'with col_act_undo:\n            safe_markdown_html(\'<span class="toolbar-3col-marker"></span>\')\n            if st.button("撤销修改"'
    if old_act_undo in text:
        text = text.replace(old_act_undo, new_act_undo, 1)
        print("  [OK] Injected toolbar-3col-marker in col_act_undo")

    # AST 语法树安全解析
    ast.parse(text)
    print("AST verification passed!")

    with open(APP_GUI_FILE, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"Successfully written to {APP_GUI_FILE}")

    # 同步至镜像目录
    shutil.copyfile(APP_GUI_FILE, MIRROR_GUI_FILE)
    print(f"Successfully mirrored to {MIRROR_GUI_FILE}")


if __name__ == "__main__":
    apply_dual_screen_remodel()
