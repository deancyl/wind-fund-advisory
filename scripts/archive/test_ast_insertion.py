import ast

code = '''
# G30 双态切换与顶部统一控制栏 (<= 60 lines insertion)
if "ui_experience_mode" not in st.session_state:
    st.session_state["ui_experience_mode"] = "每日极简投顾"

col_t_b, col_t_m, col_t_l, col_t_rf, col_t_rv = st.columns([2.6, 2.7, 3.1, 0.8, 0.8])
with col_t_b:
    safe_markdown_html(f"""<div style="display:flex;align-items:center;gap:6px;padding-top:4px;">
        <span style="font-size:15px;font-weight:800;color:var(--text-primary);white-space:nowrap;">🧭 AGY2 智投</span>
        <span style="font-size:11px;padding:2px 6px;border-radius:4px;background:rgba(16,185,129,0.1);color:var(--color-down);border:1px solid rgba(16,185,129,0.25);">{data_src_badge}</span>
    </div>""")
with col_t_m:
    cur_m = st.session_state.get("ui_experience_mode", "每日极简投顾")
    m_opts = ["每日极简投顾", "专家量化实验室"]
    sel_m = st.radio("模式", m_opts, index=m_opts.index(cur_m) if cur_m in m_opts else 0, horizontal=True, label_visibility="collapsed", key="ui_experience_mode_radio")
    if sel_m != cur_m:
        st.session_state["ui_experience_mode"] = sel_m
        st.rerun()
with col_t_l:
    def _fmt_topbar_ledger(lid: str) -> str:
        m = mlm_inst.get_ledger_meta(lid) or {}
        tag = "🟢 [实盘]" if m.get("type") == "live" else ("🧪 [沙盒]" if m.get("type") == "sandbox" else "👨‍👩‍👧 [家庭]")
        try: eq = float(mlm_inst.get_pm(lid).total_equity)
        except Exception: eq = 0.0
        return f"{tag} {m.get('name', lid)} (¥{eq:,.0f})"
    active_idx = next((i for i, l in enumerate(all_ledgers) if l["id"] == active_lid), 0)
    selected_lid = st.selectbox("当前激活账本", options=[l["id"] for l in all_ledgers], index=active_idx, format_func=_fmt_topbar_ledger, key=f"topbar_ledger_select_{active_lid}", label_visibility="collapsed")
    if selected_lid != active_lid:
        switch_active_ledger(selected_lid)
        st.rerun()
with col_t_rf:
    if st.button("🔄", help="极速刷新行情", key="btn_top_refresh_live", use_container_width=True):
        st.session_state["_cached_session_intraday_pnl"] = None
        StrategyBridge._cached_snapshot = None
        st.rerun()
with col_t_rv:
    if st.button("↩️", help="安全后悔键：撤回上次操作（对接冷备快照）", key="btn_top_revert_last", use_container_width=True):
        try:
            from ledger_backup_vault import LedgerBackupVault
            snaps = LedgerBackupVault.list_snapshots()
            if snaps and LedgerBackupVault.restore_snapshot(snaps[0].get("snapshot_id")):
                st.toast("✅ 已成功还原至上一次冷备快照")
                st.rerun()
        except Exception as _e:
            st.error(f"撤回失败: {_e}")

if st.session_state.get("ui_experience_mode") == "每日极简投顾":
    try:
        from ui_daily_brief import render_minimal_daily_brief
        _rx = StrategyBridge.get_combat_29_vs_reconstructed_6_preset() if active_lid == "combat_29_funds" else {}
        _tw = dict(_rx.get("reconstructed_6_weights", {})) if _rx else (StrategyBridge.compute_dynamic_tier_weights(st.session_state.get("active_tier_val", "C3"), snapshot).get("weights", {}))
        _ai_res = StrategyBridge.generate_ai_rebalance_orders(pm.holdings, pm.available_cash, _tw, pm=pm, mode="gentle", min_buffer_pct=float(st.session_state.get("rebalance_buffer_pct", 3.0)), c_replace="011613" if active_lid == "combat_29_funds" else None, core_anchor_code="002351")
        render_minimal_daily_brief(pm=pm, snapshot=snapshot, active_lid=active_lid, ai_orders_res=_ai_res)
    except Exception as _e:
        st.exception(_e)
    st.stop()
'''

tree = ast.parse(code)
lines = code.strip().splitlines()
print(f"AST parse successful! Number of lines: {len(lines)}")
'''
'''
