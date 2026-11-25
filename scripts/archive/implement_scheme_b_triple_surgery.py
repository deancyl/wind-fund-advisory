# -*- coding: utf-8 -*-
"""
scripts/implement_scheme_b_triple_surgery.py
方案 B 升级与三刀重构落地脚本：
1. 桌面端专业侧栏常驻 (280px) + 移动端自动隐藏；
2. 侧栏承载：品牌/状态 + 核心指数 + 自定义板块行情(带搜索增删) + 账本与主题；
3. 第一刀：彻底移除持仓表格中央的 6 键工具栏，收归顶栏 [+ 录入] 与 [⚙️ 运维]，保留 OCR 调用；
4. 第二刀：消除一键重塑与生成调仓冲突，收敛为唯一的【智能投顾今日调仓决策卡】与单一执行按钮；
5. 第三刀：桌面双栏展开，移动端首屏露头；
6. AST 与镜像一致性保障。
"""

import ast
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
APP_GUI = WORKSPACE_ROOT / "app_gui.py"
APP_GUI_MIRROR = WORKSPACE_ROOT / "AGY2_FundAdvisory" / "app_gui.py"


def run():
    print(f"Reading {APP_GUI}...")
    with open(APP_GUI, "r", encoding="utf-8") as f:
        code = f.read()

    # 1. 调整 page_config 的 initial_sidebar_state
    code = code.replace(
        'initial_sidebar_state="collapsed"',
        'initial_sidebar_state="expanded"'
    )

    # 2. 替换 CSS 中彻底隐藏侧边栏的规则
    old_sb_css_snippet = """    /* 彻底移除左侧边栏及其触点（方案 A：无侧栏全宽现代金融客户端） */
    [data-testid="stSidebar"],
    [data-testid="stSidebarCollapseButton"],
    [data-testid="stExpandSidebarButton"],
    button[aria-label="Expand sidebar"],
    button[aria-label="Collapse sidebar"],
    [data-testid="collapsedControl"],
    .stSidebar {{
        display: none !important;
        visibility: hidden !important;
        width: 0 !important;
        height: 0 !important;
        pointer-events: none !important;
    }}"""

    new_sb_css = """    /* 桌面端专业侧边栏 (方案 B：Windows .exe 桌面客户端质感) */
    [data-testid="stSidebar"] {{
        display: block !important;
        visibility: visible !important;
        min-width: 270px !important;
        max-width: 300px !important;
        background: var(--bg-surface) !important;
        border-right: 1px solid var(--border-subtle) !important;
    }}
    @media (max-width: 768px) {{
        /* 移动端自动隐藏侧栏，确保持仓大表 100% 宽度不被遮挡 */
        [data-testid="stSidebar"],
        [data-testid="stSidebarCollapseButton"],
        [data-testid="stExpandSidebarButton"],
        button[aria-label="Expand sidebar"],
        button[aria-label="Collapse sidebar"],
        [data-testid="collapsedControl"],
        .stSidebar {{
            display: none !important;
            visibility: hidden !important;
            width: 0 !important;
            height: 0 !important;
            pointer-events: none !important;
        }}
    }}"""

    if old_sb_css_snippet in code:
        code = code.replace(old_sb_css_snippet, new_sb_css)
        print("  [OK] Replaced sidebar CSS (Desktop visible 280px, Mobile hidden)")
    else:
        print("  [WARN] old_sb_css_snippet not matched verbatim")

    # 3. 增强顶栏的 OCR 真实调用 (严格遵从核心第六条)
    old_ocr_stub = """            with tab_in3:
                up_img = st.file_uploader("上传截图", type=["png", "jpg", "jpeg"], key="top_ocr_uploader")
                if up_img and st.button("识别导入", use_container_width=True, key="btn_top_ocr_exec"):
                    st.toast("截图解析已完成！")"""

    new_ocr_real = """            with tab_in3:
                up_img = st.file_uploader("上传持仓截图", type=["png", "jpg", "jpeg"], key="top_ocr_uploader")
                if up_img:
                    ocr_cache_k = f"ocr_{up_img.name}_{up_img.size}"
                    if ocr_cache_k not in st.session_state:
                        with st.spinner("AI 图像识别引擎切片解析中..."):
                            i_bytes = up_img.getvalue()
                            st.session_state[ocr_cache_k] = pm.parse_screenshot_ocr_holdings(i_bytes)
                    res_ocr = st.session_state.get(ocr_cache_k)
                    if res_ocr and res_ocr.get("holdings"):
                        st.success(f"识别出 {len(res_ocr['holdings'])} 只基金")
                        if st.button("确认入库", key="btn_top_ocr_confirm", type="primary", use_container_width=True):
                            pm.import_from_smart_text(res_ocr["holdings"], replace_existing=False)
                            pm.save_state(record_snapshot=True)
                            st.rerun()"""

    if old_ocr_stub in code:
        code = code.replace(old_ocr_stub, new_ocr_real)
        print("  [OK] Enhanced topbar OCR with real parse_screenshot_ocr_holdings")
    else:
        print("  [WARN] old_ocr_stub not found")

    # 4. 注入 st.sidebar
    sidebar_code = """
# =============================================================================
# 🧭 方案 B：专业桌面端左侧主领航台 (Desktop Left Navigation & Market Corridor)
# =============================================================================
with st.sidebar:
    st.markdown(f'''<div style="display:flex;align-items:center;justify-content:space-between;padding:4px 0 8px 0;">
        <span style="font-size:17px;font-weight:900;color:var(--text-primary);">AGY2 智投</span>
        <span style="font-size:11px;padding:2px 6px;border-radius:4px;background:rgba(37,99,235,0.08);color:var(--accent-primary);border:1px solid rgba(37,99,235,0.22);">{data_src_badge}</span>
    </div>''', unsafe_allow_html=True)
    st.caption(f"底座: {latest_date} ｜ ⏰ {clock_title}（{market_status.countdown_str}）")

    st.markdown("---")

    # 1. 核心指数走廊
    st.markdown("##### 📊 核心指数")
    _sb_c300 = fetch_realtime_index_quote("sh000300", use_cache=True) or {}
    _sb_kc50 = fetch_realtime_index_quote("sh000688", use_cache=True) or {}
    _sb_hldb = fetch_realtime_index_quote("sh000922", use_cache=True) or {}
    
    _core_indices_disp = [
        ("沪深300", float(_sb_c300.get("point") or c300_disp), float(_sb_c300.get("change_pct") or 0.0)),
        ("科创50", float(_sb_kc50.get("point") or 0.0), float(_sb_kc50.get("change_pct") or 0.0)),
        ("中证红利", float(_sb_hldb.get("point") or 0.0), float(_sb_hldb.get("change_pct") or 0.0)),
    ]
    for _iname, _ipt, _ipct in _core_indices_disp:
        _col_cls = "var(--color-up)" if _ipct > 0 else ("var(--color-down)" if _ipct < 0 else "var(--text-muted)")
        _sign = "+" if _ipct > 0 else ""
        st.markdown(f'''<div style="display:flex;justify-content:space-between;align-items:center;padding:4px 8px;margin-bottom:4px;background:var(--bg-elevated);border-radius:6px;font-size:12px;">
            <span style="font-weight:600;color:var(--text-primary);">{_iname}</span>
            <span style="font-family:monospace;color:var(--text-secondary);">{_ipt:,.2f}</span>
            <span style="font-weight:700;color:{_col_cls};font-family:monospace;">{_sign}{_ipct:.2f}%</span>
        </div>''', unsafe_allow_html=True)

    # 2. 自定义板块与行业行情 (用户特别点名加餐项)
    st.markdown("##### 📌 自选与行业板块")
    if "custom_sector_watchlist" not in st.session_state:
        st.session_state.custom_sector_watchlist = [
            {"code": "161725", "name": "中证白酒"},
            {"code": "512480", "name": "半导体ETF"},
            {"code": "012348", "name": "恒生科技"},
            {"code": "005561", "name": "红利低波"},
            {"code": "511260", "name": "中债十年"},
        ]

    for _sec in st.session_state.custom_sector_watchlist:
        _sq = fetch_realtime_fund_quote(_sec["code"])
        _spct = float(getattr(_sq, "gszzl", 0.0) or getattr(_sq, "official_chg_pct", 0.0) or 0.0) if _sq else 0.0
        _scol = "var(--color-up)" if _spct > 0 else ("var(--color-down)" if _spct < 0 else "var(--text-muted)")
        _ssign = "+" if _spct > 0 else ""
        st.markdown(f'''<div style="display:flex;justify-content:space-between;align-items:center;padding:3px 8px;margin-bottom:3px;background:var(--bg-surface);border:1px solid var(--border-subtle);border-radius:6px;font-size:11px;">
            <span style="font-weight:500;color:var(--text-primary);">{_sec['name']}</span>
            <span style="font-family:monospace;color:var(--text-muted);font-size:10px;">{_sec['code']}</span>
            <span style="font-weight:700;color:{_scol};font-family:monospace;">{_ssign}{_spct:.2f}%</span>
        </div>''', unsafe_allow_html=True)

    # 侧边栏添加自选板块 Popover
    with st.popover("+ 自选板块", help="拼音/代码快速检索并添加自选板块"):
        st.caption("🔍 检索添加自选板块与行业")
        sec_input = st.text_input("代码/拼音/名称", placeholder="如 512880 或 证券", key="sb_sec_add_input")
        if st.button("添加板块", type="primary", use_container_width=True, key="btn_sb_add_sec"):
            if sec_input.strip():
                raw_s = sec_input.strip()
                cat_res = search_index_and_fund_candidates(raw_s, limit=3)
                if cat_res:
                    n_code, n_name = cat_res[0]
                    if not any(x["code"] == n_code for x in st.session_state.custom_sector_watchlist):
                        st.session_state.custom_sector_watchlist.append({"code": n_code, "name": n_name})
                        st.success(f"已添加: {n_name} ({n_code})")
                        st.rerun()
                else:
                    st.warning(f"未能查到板块或基金: {raw_s}")

    st.markdown("---")

    # 3. 底部当前激活账本与外观设置
    st.markdown("##### 💼 账本与设置")
    active_idx_sb = next((i for i, l in enumerate(all_ledgers) if l["id"] == active_lid), 0)
    sb_sel_lid = st.selectbox(
        "当前账本",
        options=[l["id"] for l in all_ledgers],
        index=active_idx_sb,
        format_func=_fmt_topbar_ledger,
        key=f"sb_ledger_selector_{active_lid}",
        label_visibility="collapsed"
    )
    if sb_sel_lid != active_lid:
        switch_active_ledger(sb_sel_lid)
        st.rerun()

    c_sb_th, c_sb_rf = st.columns([1, 1])
    with c_sb_th:
        with st.popover("🎨 外观", help="切换界面主题风格与涨跌红绿"):
            st.caption("🎨 主题与色彩")
            th_display_names = [
                "🏛️ 机构冷灰",
                "🌑 彭博暗黑",
                "📜 金融暖卷",
                "🌌 深海钛金",
                "❄️ 极昼纯白"
            ]
            th_keys = ["light_slate", "dark_terminal", "nordic_paper", "deep_titanium", "nordic_frost"]
            cur_th_k = st.session_state.get("app_theme_mode", "light_slate")
            cur_th_idx = th_keys.index(cur_th_k) if cur_th_k in th_keys else 0
            sel_th_n = st.selectbox("主题风格", th_display_names, index=cur_th_idx, key="sb_th_sel")
            if th_keys[th_display_names.index(sel_th_n)] != cur_th_k:
                st.session_state.app_theme_mode = th_keys[th_display_names.index(sel_th_n)]
                st.rerun()
    with c_sb_rf:
        if st.button("🔄 刷新", use_container_width=True, key="btn_sb_refresh_data", help="极速刷新实时盘中行情与估值"):
            clear_realtime_cache()
            st.toast("盘中行情已极速同步！")
            st.rerun()
"""

    marker_topbar_entry = "# 统一顶栏（彻底去除割裂侧栏，整合品牌/状态 + 账本选择 + 外观 + i详情 + 冷备撤回）"
    if "with st.sidebar:" not in code and marker_topbar_entry in code:
        code = code.replace(marker_topbar_entry, sidebar_code + "\n" + marker_topbar_entry)
        print("  [OK] Injected resurrected st.sidebar with custom sector corridor")

    # 5. 替换 Tab 1 的 BLOCK 2：纯净调仓决策台
    start_anchor = "        # 【BLOCK 2】核心持仓与调仓执行清单表"
    end_anchor = "        # 3. 准备表格数据\n        df_disp = pm.export_snapshot_df()"

    clean_block2_replacement = """        # ═════════════════════════════════════════════════════════════
        # 【BLOCK 2: 纯净决策台】低频 6 键已上移至顶栏 [+ 录入] 与 [⚙️ 运维]
        # 统一调仓决策卡：彻底消除打架按钮与重复 key，主屏唯一聚焦 [⚡ 立即执行建议 ➡️]
        # ═════════════════════════════════════════════════════════════
        with st.container():
            col_rx_act1, col_rx_act2 = st.columns([7.5, 2.5])
            with col_rx_act1:
                if active_lid == "combat_29_funds":
                    st.markdown(f'''<div style="background:rgba(37,99,235,0.06);border-left:4px solid var(--accent-primary);border-radius:6px;padding:8px 12px;margin-bottom:6px;">
                        <span style="font-weight:700;color:var(--text-primary);font-size:13px;">🎯 智能投顾今日调仓决策：三阶重塑止血方案</span><br>
                        <span style="font-size:12px;color:var(--text-secondary);">清扫 <b>{t_count}</b> 只免赎尾仓（回收 <b>¥{cash_min:.2f}</b>）· 011613 C转A零费率置换 · 聚焦 6 只全天候底仓</span>
                    </div>''', unsafe_allow_html=True)
                else:
                    st.markdown(f'''<div style="background:rgba(37,99,235,0.06);border-left:4px solid var(--accent-primary);border-radius:6px;padding:8px 12px;margin-bottom:6px;">
                        <span style="font-weight:700;color:var(--text-primary);font-size:13px;">🎯 智能投顾今日调仓决策：{card6_val}</span><br>
                        <span style="font-size:12px;color:var(--text-secondary);">{card6_sub} ｜ 动态缓冲降噪</span>
                    </div>''', unsafe_allow_html=True)
            with col_rx_act2:
                if st.button("立即执行", type="primary", use_container_width=True, key="btn_apply_prescript_main", help="立即执行智能投顾今日调仓优化方案"):
                    st.session_state["tab2_view_mode"] = "💼 持仓诊断与智能调仓 (主流程)"
                    if active_lid == "combat_29_funds":
                        st.session_state.rad_tab2_scenario_mode = "🧹 尾部碎片与C类一键归拢 (清理<3%碎片与满期高费率C类至底仓)"
                        st.session_state.sel_sc_anchor = "002351 - 易方达裕祥回报债券A"
                        st.session_state.tab2_c_replace = "011613"
                    st.session_state.tab2_diagnosed = True
                    st.session_state.tab2_rebalanced = True
                    st.session_state.tab2_trigger_diagnose = True
                    st.session_state.tab2_trigger_rebalance = True
                    st.session_state.tab2_rebal_cache = None
                    st.rerun()

            # 量化缓冲带收纳进高级参数微调（普通用户无需看到复杂数学滑块）
            with st.expander("⚙️ 调仓参数微调 (免折腾缓冲带)", expanded=False):
                cur_buf_val = float(st.session_state.get("rebalance_buffer_pct", 3.0))
                def _sync_tab2_rebal_buffer_change():
                    st.session_state.rebalance_buffer_pct = float(st.session_state.tab2_rebal_buf_slider)
                    st.session_state.tab2_diag_cache = None
                    st.session_state.tab2_rebal_cache = None
                st.slider(
                    "🛡️ 免折腾调仓缓冲带 (%)",
                    min_value=1.0,
                    max_value=5.0,
                    value=cur_buf_val,
                    step=0.5,
                    format="%.1f%%",
                    key="tab2_rebal_buf_slider",
                    on_change=_sync_tab2_rebal_buffer_change,
                    help="控制调仓裁决与温和调仓过滤的最小偏离阈值。低于此阈值的微小偏离将自动维持现状，杜绝无效换仓摩擦"
                )

"""

    if start_anchor in code and end_anchor in code:
        idx_s = code.find(start_anchor)
        idx_e = code.find(end_anchor)
        code = code[:idx_s] + clean_block2_replacement + code[idx_e:]
        print("  [OK] Successfully replaced 6-button toolbar with unified decision card")
    else:
        print("  [WARN] start_anchor or end_anchor not matched in app_gui.py")

    # 6. AST 校验与写回
    print("Verifying AST...")
    ast.parse(code)
    print("AST verification PASSED!")

    with open(APP_GUI, "w", encoding="utf-8") as f:
        f.write(code)
    print(f"Written to {APP_GUI}")

    with open(APP_GUI_MIRROR, "w", encoding="utf-8") as f:
        f.write(code)
    print(f"Mirrored to {APP_GUI_MIRROR}")


if __name__ == "__main__":
    run()
