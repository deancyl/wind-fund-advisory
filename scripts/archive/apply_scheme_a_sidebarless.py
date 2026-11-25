# -*- coding: utf-8 -*-
"""
scripts/apply_scheme_a_sidebarless.py
彻底落地外部审计【方案 A：去侧边栏 + 顶栏外观Pop + 顶部单行指数走廊横条】
"""

import sys
import ast
import shutil
from pathlib import Path

REPLACEMENT_CODE = '''# -------------------------------------------------------------
# 方案 A 极简无侧栏架构：全局状态与自选行情走廊预设
# -------------------------------------------------------------
if "app_view_layout_mode" not in st.session_state:
    st.session_state.app_view_layout_mode = "📱 手机极简盯盘" if _is_mobile_viewport() else "🖥️ 桌面专业模式"

total_days = snapshot.get("total_days", 2142)
latest_date = snapshot.get("latest_date", "2026-11-04")
is_realtime_src = (
    mb_data.get("is_realtime", False)
    or any(k in str(mb_data.get("source", "")) for k in ["realtime", "eastmoney", "sina", "live"])
)
data_src_badge = "🟢 实时盘中源已连接" if is_realtime_src else "🟡 本地湖仓快照兜底"

saved_watchlist = load_custom_watchlist()
if "sb_corridor_display_limit" not in st.session_state:
    st.session_state.sb_corridor_display_limit = saved_watchlist.get("display_limit", 6)
if "sb_selected_corridor_indices" not in st.session_state:
    st.session_state.sb_selected_corridor_indices = saved_watchlist.get("selected_codes", ["000300", "000688", "000922", "000905", "000852", "518880"])
if "sb_custom_corridor_items" not in st.session_state:
    st.session_state.sb_custom_corridor_items = saved_watchlist.get("custom_items", {})

# -------------------------------------------------------------
# 🌐 全局紧凑顶栏：系统品牌标识 + 行情源状态角标 + 「📂 当前激活账本」切换 + 🎨 外观 + i 详情 + ↩️ 冷备
# -------------------------------------------------------------
mlm_inst = st.session_state.get("mlm") or (MultiLedgerManager.get_instance() if MultiLedgerManager else None)
all_ledgers = mlm_inst.list_ledgers() if mlm_inst else []
avail_lids = [l["id"] for l in all_ledgers]
active_lid = st.session_state.get("active_ledger_id", "main_live")
if active_lid not in avail_lids:
    active_lid = "main_live" if "main_live" in avail_lids else (avail_lids[0] if avail_lids else "main_live")
    st.session_state.active_ledger_id = active_lid

# 首次加载智能自动路由安全兜底 (持仓数 >= 10 只)
if "_initial_ledger_routed" not in st.session_state:
    st.session_state["_initial_ledger_routed"] = True
    cur_pm_init = mlm_inst.get_pm(active_lid) if mlm_inst else pm
    if cur_pm_init and len(cur_pm_init.holdings) >= 10:
        st.session_state["sel_tab2_active_ledger"] = active_lid
        st.session_state["tab2_view_mode"] = "💼 持仓诊断与智能调仓 (主流程)"
        st.session_state["pending_cross_tab_jump"] = {
            "tab_index": 0,
            "tab_name": "持仓",
            "action_name": "首次加载存量持仓",
            "target_title": active_lid,
            "detail": f"检测到【{active_lid}】包含 {len(cur_pm_init.holdings)} 只存量持仓，已自动聚焦持仓诊断与调仓工作区",
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }
        st.session_state["last_cross_tab_action"] = dict(st.session_state["pending_cross_tab_jump"])
        st.session_state.tab2_diagnosed = True
        st.session_state.tab2_rebalanced = True
        st.session_state.tab2_trigger_diagnose = True
        st.session_state.tab2_trigger_rebalance = True

# 预计算时钟与指数概览（供顶栏 i 弹窗与首屏 Hero 共享）
clock_color = active_co['color_up'] if market_status.is_golden_window else (active_co['color_down'] if market_status.is_after_market else active_th['accent_primary'])
clock_title = "14:30黄金窗口" if market_status.is_golden_window else ("盘后已关账" if market_status.is_after_market else "盘中观察期")
_plan_caliber = "存量瘦身重构" if active_lid == "combat_29_funds" else "动态股债平衡"
_q_c300 = fetch_realtime_index_quote("sh000300", use_cache=True) or {}
_q_kc50 = fetch_realtime_index_quote("sh000688", use_cache=True) or {}
_q_hldb = fetch_realtime_index_quote("sh000922", use_cache=True) or {}
_idx_bar = " ｜ ".join([
    f"沪深300 {float(_q_c300.get('point') or c300_disp):,.1f} ({float(_q_c300.get('change_pct') or 0.0):+.2f}%)",
    f"科创50 {float(_q_kc50.get('point') or 0.0):,.1f} ({float(_q_kc50.get('change_pct') or 0.0):+.2f}%)",
    f"中证红利 {float(_q_hldb.get('point') or 0.0):,.1f} ({float(_q_hldb.get('change_pct') or 0.0):+.2f}%)",
])

# 统一顶栏（彻底去除割裂侧栏，整合品牌/状态 + 账本选择 + 外观 + i详情 + 冷备撤回）
col_t_b, col_t_l = st.columns([4.2, 5.8])
with col_t_b:
    safe_markdown_html(f"""<div style="display:flex;align-items:center;gap:8px;padding-top:4px;flex-wrap:wrap;">
        <span style="font-size:15px;font-weight:800;color:var(--text-primary);white-space:nowrap;">AGY2 智投</span>
        <span style="font-size:11px;padding:2px 6px;border-radius:4px;background:rgba(37,99,235,0.08);color:var(--accent-primary);border:1px solid rgba(37,99,235,0.22);">{data_src_badge}</span>
        <span style="font-size:11px;color:var(--text-muted);font-family:monospace;white-space:nowrap;">底座: {latest_date}</span>
    </div>""")
with col_t_l:
    def _fmt_topbar_ledger(lid: str) -> str:
        m = mlm_inst.get_ledger_meta(lid) or {}
        tag = "[实盘]" if m.get("type") == "live" else ("[沙盒]" if m.get("type") == "sandbox" else "[家庭]")
        name_str = str(m.get("name", lid))
        if "¥" in name_str:
            return f"{tag} {name_str}"
        try:
            eq = float(mlm_inst.get_pm(lid).total_equity)
        except Exception:
            eq = 0.0
        return f"{tag} {name_str} (¥{eq:,.0f})"
    active_idx = next((i for i, l in enumerate(all_ledgers) if l["id"] == active_lid), 0)
    col_sel_ld, col_pop_theme, col_pop_info, col_pop_rv = st.columns([6.1, 1.3, 1.3, 1.3])
    with col_sel_ld:
        selected_lid = st.selectbox("当前激活账本", options=[l["id"] for l in all_ledgers], index=active_idx, format_func=_fmt_topbar_ledger, key=f"topbar_ledger_select_{active_lid}", label_visibility="collapsed")
        if selected_lid != active_lid:
            switch_active_ledger(selected_lid)
            st.rerun()
    with col_pop_theme:
        with st.popover("🎨", help="界面主题与涨跌色彩定制"):
            st.caption("🎨 界面外观与色彩定制")
            th_display_names = [
                "🏛️ 机构冷灰 (Institutional Slate)",
                "🌑 彭博暗黑 (Bloomberg Carbon)",
                "📜 金融暖卷 (FT Warm Paper)",
                "🌌 深海钛金 (Deep Titanium)",
                "❄️ 极昼纯白 (Nordic Frost)"
            ]
            th_keys = ["light_slate", "dark_terminal", "nordic_paper", "deep_titanium", "nordic_frost"]
            cur_th_k = st.session_state.get("app_theme_mode", "light_slate")
            alias_to_std = {
                "institutional_slate": "light_slate",
                "bloomberg_carbon": "dark_terminal",
                "ft_warm_paper": "nordic_paper"
            }
            cur_th_k = alias_to_std.get(cur_th_k, cur_th_k)
            cur_th_idx = th_keys.index(cur_th_k) if cur_th_k in th_keys else 0

            def _sync_theme_mode_change():
                sel_name = st.session_state.sb_theme_selector
                st.session_state.app_theme_mode = th_keys[th_display_names.index(sel_name)]

            st.selectbox(
                "界面主题风格",
                th_display_names,
                index=cur_th_idx,
                key="sb_theme_selector",
                on_change=_sync_theme_mode_change,
                help="5套专业级金融终端主题：机构冷灰、彭博暗黑、金融暖卷、深海钛金、极昼纯白"
            )

            co_display_names = ["🇨🇳 A股惯例 (红涨绿跌·默认)", "🌐 国际惯例 (绿涨红跌)"]
            co_keys = ["cn", "global"]
            cur_co_k = st.session_state.get("app_color_mode", "cn")
            cur_co_idx = co_keys.index(cur_co_k) if cur_co_k in co_keys else 0

            def _sync_color_mode_change():
                sel_c = st.session_state.sb_color_selector
                st.session_state.app_color_mode = co_keys[co_display_names.index(sel_c)]

            st.selectbox(
                "涨跌色彩体系",
                co_display_names,
                index=cur_co_idx,
                key="sb_color_selector",
                on_change=_sync_color_mode_change,
                help="自适应联动全站所有数字、行情带、持仓盈亏与穿透图表颜色"
            )
    with col_pop_info:
        with st.popover("i", help="查看时钟、估值与攻防详情"):
            st.markdown(f"**实时指数**：{_idx_bar}")
            st.markdown(f"**交易时钟**：{clock_title}（倒计时 {market_status.countdown_str}，距网格日 {days_to_next} 天）")
            st.markdown(f"**攻防边界**：沪深300 {c300_disp:,.1f} ｜ MA20 {m20_disp:,.0f} (偏离 {bias_disp:+.1f}%) ｜ 破 {surge_line:,.0f} 进攻 / 跌 {breakdown_line:,.0f} 防守")
            st.markdown(f"**估值资金**：ERP 分位 {erp_pct:.1f}% ｜ DR007 {dr007_val:.2f}% ｜ 两市成交 {t_str}")
            if data_resilience_guard and hasattr(data_resilience_guard, "DataSourceHealthRegistry"):
                hs = data_resilience_guard.DataSourceHealthRegistry.get_health_summary()
                _h_cnt = hs.get('healthy_count', hs.get('green_count', 0))
                _tot_cnt = hs.get('total_count', 6)
                st.markdown(f"**数据底座**：{hs.get('badge', '在线')} ({_h_cnt}/{_tot_cnt}) ｜ 每次写入自动冷备")
                _chans = hs.get("channels", {})
                if _chans:
                    st.caption("通道实时健康明细：")
                    for _ck, _cv in _chans.items():
                        _st = _cv.get("status", "UNKNOWN")
                        _st_icon = "🟢 正常" if _st == "GREEN" else ("⚪ 待命" if _st == "STANDBY" else ("🟡 波动" if _st == "YELLOW" else ("🔴 熔断" if _st == "RED" else "⏳ 待探")))
                        _lat = f"{_cv.get('latency_ms', 0):.0f}ms" if _cv.get('latency_ms') is not None else "--"
                        st.markdown(f"- **{_cv.get('name', _ck)}**：{_st_icon}（{_lat}）")
    with col_pop_rv:
        with st.popover("↩️", help="撤回至最近冷备快照"):
            st.caption("**冷备还原**")
            try:
                from ledger_backup_vault import LedgerBackupVault
                snaps = [s for s in LedgerBackupVault.list_snapshots() if not s.get("snapshot_id", "").startswith("test_")]
                if snaps:
                    last_s = snaps[0]
                    st.markdown(f"**快照**：`{last_s.get('snapshot_id')}`\\n\\n**时间**：{last_s.get('timestamp')}\\n\\n**原因**：{last_s.get('reason', '自动冷备')}")
                    if st.button("确认还原", key="btn_top_confirm_revert", use_container_width=True, help="还原至最近一次不可变冷备快照"):
                        if LedgerBackupVault.restore_snapshot(last_s.get("snapshot_id")):
                            st.toast("已还原至最近冷备快照")
                            st.rerun()
                        else:
                            st.error("还原失败")
                else:
                    st.info("暂无冷备快照")
            except Exception as _e:
                st.error(f"撤回失败: {_e}")

# -------------------------------------------------------------
# 顶部紧凑单行指数走廊横条 (Top Compact Index Strip · 32px 高度)
# -------------------------------------------------------------
display_limit = int(st.session_state.get("sb_corridor_display_limit", 6))
current_corridor_codes = st.session_state.get("sb_selected_corridor_indices", ["000300", "000688", "000922", "000905", "000852", "518880"])[:display_limit]

active_corridor_list = fetch_custom_realtime_indices(codes=current_corridor_codes, use_cache=True)
corridor_val_map = fetch_or_calc_index_valuations(force_refresh=False)

col_idx_strip, col_idx_cfg, col_idx_rf = st.columns([8.4, 0.8, 0.8])
with col_idx_strip:
    pills_html = []
    for idx_item in active_corridor_list:
        icode = idx_item["code"]
        c_pct = float(idx_item["change_pct"])
        c_sign = "+" if c_pct > 0 else ""
        c_cls = "top-index-chg-up" if c_pct > 0 else ("top-index-chg-down" if c_pct < 0 else "top-index-chg-flat")
        is_small_pt = (idx_item["point"] < 100.0)
        pt_fmt = f"{idx_item['point']:,.3f}" if is_small_pt else f"{idx_item['point']:,.2f}"

        v_meta = corridor_val_map.get(icode) or corridor_val_map.get(idx_item.get("secid", "")) or {}
        v_label = v_meta.get("label", "")
        v_status = v_meta.get("status", "mid")
        val_cls_name = f"val-{v_status.replace('_', '-')}"
        if not v_label:
            v_label = "适中"
            val_cls_name = "val-mid"
        v_badge_html = f'<span class="index-pill-val-badge {val_cls_name}">{v_label}</span>'

        pills_html.append(f'<div class="top-index-pill"><span class="top-index-name">{idx_item["name"]}</span><span class="top-index-pt">{pt_fmt}</span><span class="{c_cls}">{c_sign}{c_pct:.2f}%</span>{v_badge_html}</div>')

    safe_markdown_html(f'<div class="top-index-strip">{"".join(pills_html)}</div>')

with col_idx_cfg:
    with st.popover("⚙️", help="走廊展示数量、自选标的与多模检索定制"):
        st.caption("⚙️ 核心指数走廊自由定制")
        cur_limit = int(st.session_state.sb_corridor_display_limit)
        new_limit = st.slider(
            "走廊展示数量",
            min_value=3,
            max_value=15,
            value=cur_limit,
            step=1,
            key="sl_corridor_disp_limit",
            help="控制顶部单行卡片展示上限（3 至 15 只）"
        )
        if new_limit != cur_limit:
            st.session_state.sb_corridor_display_limit = new_limit
            saved_watchlist["display_limit"] = new_limit
            saved_watchlist["display_count"] = new_limit
            saved_watchlist["selected_codes"] = st.session_state.sb_selected_corridor_indices
            saved_watchlist["custom_items"] = st.session_state.sb_custom_corridor_items
            save_custom_watchlist(saved_watchlist)

        combined_catalog = dict(INDEX_CATALOG_38)
        combined_catalog.update(st.session_state.sb_custom_corridor_items)

        avail_options = []
        for c in st.session_state.sb_selected_corridor_indices:
            if c not in avail_options:
                avail_options.append(c)
        for c in combined_catalog.keys():
            if c not in avail_options:
                avail_options.append(c)

        def _fmt_option(k: str) -> str:
            item_info = combined_catalog.get(k, {})
            c_name = item_info.get("name", k)
            pinyin_str = item_info.get("pinyin", "")
            sec = item_info.get("sector", "")
            sec_tag = f"[{sec}] " if sec else ""
            return f"{sec_tag}{c_name} ({k}) [{pinyin_str}]"

        sel_corridor_keys = st.multiselect(
            "全市场自选列表 (支持拼音/代码/名称检索)",
            options=avail_options,
            default=st.session_state.sb_selected_corridor_indices,
            format_func=_fmt_option,
            key="ms_corridor_indices"
        )
        if sel_corridor_keys != st.session_state.sb_selected_corridor_indices:
            st.session_state.sb_selected_corridor_indices = sel_corridor_keys or ["000300", "000688", "000922", "000905", "000852", "518880"]
            saved_watchlist["display_limit"] = st.session_state.sb_corridor_display_limit
            saved_watchlist["display_count"] = st.session_state.sb_corridor_display_limit
            saved_watchlist["selected_codes"] = st.session_state.sb_selected_corridor_indices
            saved_watchlist["custom_items"] = st.session_state.sb_custom_corridor_items
            save_custom_watchlist(saved_watchlist)

        st.markdown("---")
        st.caption("➕ 智能检索接入标的 (支持拼音首字母/汉字/代码，如 hldb、红利低波、H30269、510300)")
        search_query = st.text_input("智能检索", placeholder="输入拼音/代码/中文 如 hldb、红利低波、H30269", label_visibility="collapsed", key="txt_add_custom_code")
        clean_query = str(search_query).strip() if search_query else ""
        cands = search_index_and_fund_candidates(clean_query, limit=8) if clean_query else []

        if cands:
            sel_cand = st.selectbox("选择匹配标的", options=cands, format_func=lambda x: str(x), key="sb_corridor_cand_select")
            if st.button("添加标的", key="btn_add_custom_code", type="primary", use_container_width=True, help="将选中标的加入自选指数走廊"):
                target_code = sel_cand.get("code")
                probe_res = validate_and_fetch_code(target_code) or dict(sel_cand)
                st.session_state.sb_custom_corridor_items[target_code] = probe_res
                if target_code not in st.session_state.sb_selected_corridor_indices:
                    st.session_state.sb_selected_corridor_indices.insert(0, target_code)
                st.session_state["ms_corridor_indices"] = list(st.session_state.sb_selected_corridor_indices)
                saved_watchlist["display_limit"] = st.session_state.sb_corridor_display_limit
                saved_watchlist["display_count"] = st.session_state.sb_corridor_display_limit
                saved_watchlist["selected_codes"] = st.session_state.sb_selected_corridor_indices
                saved_watchlist["custom_items"] = st.session_state.sb_custom_corridor_items
                save_custom_watchlist(saved_watchlist)
                st.success(f"已接入: {probe_res.get('name', target_code)} ({target_code})")
                st.rerun()
        elif clean_query:
            if st.button("接入标的", key="btn_add_custom_code_direct", use_container_width=True):
                probe_res = validate_and_fetch_code(clean_query)
                if probe_res:
                    target_code = probe_res.get("code", clean_query)
                    st.session_state.sb_custom_corridor_items[target_code] = probe_res
                    if target_code not in st.session_state.sb_selected_corridor_indices:
                        st.session_state.sb_selected_corridor_indices.insert(0, target_code)
                    st.session_state["ms_corridor_indices"] = list(st.session_state.sb_selected_corridor_indices)
                    saved_watchlist["display_limit"] = st.session_state.sb_corridor_display_limit
                    saved_watchlist["display_count"] = st.session_state.sb_corridor_display_limit
                    saved_watchlist["selected_codes"] = st.session_state.sb_selected_corridor_indices
                    saved_watchlist["custom_items"] = st.session_state.sb_custom_corridor_items
                    save_custom_watchlist(saved_watchlist)
                    st.success(f"已接入: {probe_res.get('name', target_code)} ({target_code})")
                    st.rerun()
                else:
                    st.error(f"代码/名称 {clean_query} 探针失败，未能获取有效盘中行情")

with col_idx_rf:
    if st.button("刷新", key="btn_refresh_all_live_quotes", help="极速刷新实时行情", use_container_width=True):
        clear_realtime_cache()
        fetch_custom_realtime_indices(codes=st.session_state.sb_selected_corridor_indices, use_cache=False)
        fetch_market_turnover_and_sentiment(force_refresh=True)
        fetch_or_calc_index_valuations(force_refresh=False)  # 严格使用 False，彻底消除外部 PE 爬虫卡死！
        if hasattr(pm, "holdings") and pm.holdings:
            prefetch_batch_fund_quotes(list(pm.holdings.keys()), force_refresh=True)  # 单次 HTTP 批量获取全量估值
        pm.sync_holdings_live_nav(use_intraday_gsz=True)
        st.session_state["_cached_session_intraday_pnl"] = None  # 强制使 60s 持仓盈亏缓存失效
        st.session_state["_cached_session_intraday_pnl_ts"] = 0
        StrategyBridge._cached_snapshot = None
        st.rerun()
'''


def apply_refactor(file_path: Path):
    print(f"Refactoring {file_path}...")
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. 查找开始标记与结束标记
    start_tag = "# 侧边栏：【🧭 全局领航台】"
    start_idx = content.find(start_tag)
    if start_idx == -1:
        start_tag = "with st.sidebar:"
        start_idx = content.find(start_tag)
    assert start_idx != -1, "Cannot find start tag"

    # 如果有注释行在前面，回溯到注释行
    comment_header = "# -------------------------------------------------------------\n# 侧边栏："
    header_idx = content.rfind("# -------------------------------------------------------------\n", 0, start_idx)
    if header_idx != -1 and header_idx > start_idx - 100:
        actual_start = header_idx
    else:
        actual_start = start_idx

    end_tag = "hero_c1, hero_c2, hero_c3 = st.columns(3)"
    end_idx = content.find(end_tag)
    assert end_idx != -1, "Cannot find end tag"

    # 找到 hero_c1 前面的那个注释行
    hero_comment = "# -------------------------------------------------------------\n# 首屏大字看板"
    h_comm_idx = content.rfind("# -------------------------------------------------------------\n", actual_start, end_idx)
    assert h_comm_idx != -1, "Cannot find hero comment header"

    new_content = content[:actual_start] + REPLACEMENT_CODE + "\n" + content[h_comm_idx:]

    # 静态语法树检查
    ast.parse(new_content)
    print("AST verification passed!")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"Successfully updated {file_path}")


if __name__ == "__main__":
    apply_refactor(Path("app_gui.py"))
    # 同步至镜像目录
    shutil.copyfile("app_gui.py", "AGY2_FundAdvisory/app_gui.py")
    print("Dual mirror sync complete!")
