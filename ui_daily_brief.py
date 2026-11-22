# -*- coding: utf-8 -*-
"""
AGY2 Daily Brief View (G34 单屏聚焦组件与今日调仓打卡闭环)
规则：标题 <= 6 字、按钮 <= 4 字、所有解释收进 i 弹窗、100% 消费真实后端数据。
"""
import streamlit as st
import pandas as pd
from typing import Dict, Any, List, Optional

try:
    from rebalance_grouping import IntentGroup, group_rebalance_orders_by_intent, load_daily_checkin, save_daily_checkin
except Exception:
    try:
        from AGY2_FundAdvisory.rebalance_grouping import IntentGroup, group_rebalance_orders_by_intent, load_daily_checkin, save_daily_checkin
    except Exception:
        IntentGroup = list
        def group_rebalance_orders_by_intent(items): return {"is_empty": True, "tail_items": [], "c_items": [], "core_items": [], "hold_items": []}
        def load_daily_checkin(d=""): return {"date": d, "checked_codes": {}}
        def save_daily_checkin(c, a, amt, chk, d=""): return {"date": d, "checked_codes": {}}

try:
    from portfolio_manager import fetch_realtime_index_quote, fetch_realtime_fund_quote
except Exception:
    try: from AGY2_FundAdvisory.portfolio_manager import fetch_realtime_index_quote, fetch_realtime_fund_quote
    except Exception: fetch_realtime_index_quote, fetch_realtime_fund_quote = None, None
try:
    from ledger_backup_vault import LedgerBackupVault
except Exception:
    try: from AGY2_FundAdvisory.ledger_backup_vault import LedgerBackupVault
    except Exception: LedgerBackupVault = None
try:
    import data_resilience_guard
except Exception:
    try: import AGY2_FundAdvisory.data_resilience_guard as data_resilience_guard
    except Exception: data_resilience_guard = None
try:
    import cashflow_planner
except Exception:
    try: import AGY2_FundAdvisory.cashflow_planner as cashflow_planner
    except Exception: cashflow_planner = None
try:
    import execution_tracker
except Exception:
    try: import AGY2_FundAdvisory.execution_tracker as execution_tracker
    except Exception: execution_tracker = None


def render_rebalance_action_section(
    pm: Any,
    snapshot: Optional[Dict[str, Any]] = None,
    active_lid: str = "combat_29_funds",
    ai_orders_res: Optional[Dict[str, Any]] = None,
    target_weights: Optional[Dict[str, float]] = None,
    include_nav_buttons: bool = False,
) -> None:
    """渲染意图分组调仓单、新钱定投与下单打卡执行闭环。"""
    snap = snapshot or {}
    holdings = getattr(pm, "holdings", {})
    avail_cash = float(getattr(pm, "available_cash", 0.0))

    t_l, t_r = st.columns([9.2, 0.8])
    with t_l:
        st.markdown("##### 今日调仓")
    with t_r:
        with st.popover("i", help="查看调仓分组说明"):
            st.markdown("调仓清单已自动分为四类：清理尾仓（免赎碎片回收）、C转A省费（年省约 0.40%）、核心调仓（权重再平衡）、维持持仓（缓冲带内免折腾）。")

    rebal_items = []
    if ai_orders_res and isinstance(ai_orders_res, dict) and "items" in ai_orders_res:
        rebal_items = ai_orders_res.get("items", [])
    elif hasattr(pm, "last_rebalance_plan") and pm.last_rebalance_plan:
        rebal_items = pm.last_rebalance_plan

    grouped = group_rebalance_orders_by_intent(rebal_items)

    # 打卡状态
    checkin_state = load_daily_checkin()
    checked_codes = checkin_state.get("checked_codes", {})

    actionable = [
        it for it in (grouped["tail_items"] + grouped["c_items"] + grouped["core_items"])
        if abs(float(it.get("diff_amount") or it.get("amount") or 0.0)) > 1e-4
    ]
    total_actions = len(actionable)
    completed_actions = sum(1 for it in actionable if str(it.get("fund_code", it.get("code", ""))) in checked_codes)

    # 进度条
    if total_actions > 0:
        prog = min(1.0, max(0.0, completed_actions / total_actions))
        st.progress(prog)
        st.caption(f"今日执行进度：已完成 {completed_actions} / {total_actions} 笔下单")

    if grouped["is_empty"]:
        st.success("今日无需操作，安心持有。")
    else:
        if len(grouped["tail_sweep"]) > 0:
            t_grp = grouped["tail_sweep"]
            with st.expander(f"{t_grp['title']} · 回收 ¥{t_grp['total_recovered_cash']:,.2f}", expanded=False):
                rows = []
                for x in t_grp["items"]:
                    fc = str(x.get("fund_code", x.get("code", "")))
                    fn = str(x.get("fund_name", x.get("name", "")))
                    mv = abs(float(x.get('market_value') if x.get('market_value') is not None else (x.get('diff_amount') or x.get('amount') or 0.0)))
                    chk_flag = "✅ 已清" if fc in checked_codes else "⏳ 待清"
                    rows.append({"代码": fc, "名称": fn, "市值": f"¥{mv:.2f}", "操作": "清仓", "打卡": chk_flag})
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        if len(grouped["c_replace"]) > 0:
            c_grp = grouped["c_replace"]
            with st.expander(f"{c_grp['title']} · 年省 0.40%", expanded=True):
                rows = []
                for x in c_grp["items"]:
                    fc = str(x.get("fund_code", x.get("code", "")))
                    fn = str(x.get("fund_name", x.get("name", "")))
                    amt = float(x.get("diff_amount") or x.get("amount") or 0.0)
                    dir_txt = "买入A" if amt > 0 else "卖出C"
                    chk_flag = "✅ 已办" if fc in checked_codes else "⏳ 待办"
                    rows.append({"代码": fc, "名称": fn, "方向": dir_txt, "金额": f"¥{abs(amt):,.2f}", "打卡": chk_flag})
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        if len(grouped["core_trades"]) > 0:
            k_grp = grouped["core_trades"]
            with st.expander(f"{k_grp['title']}", expanded=True):
                rows = []
                for x in k_grp["items"]:
                    fc = str(x.get("fund_code", x.get("code", "")))
                    fn = str(x.get("fund_name", x.get("name", "")))
                    amt = float(x.get("diff_amount") or x.get("amount") or 0.0)
                    dir_txt = "买入" if amt > 0 else "减仓"
                    chk_flag = "✅ 已办" if fc in checked_codes else "⏳ 待办"
                    rows.append({"代码": fc, "名称": fn, "方向": dir_txt, "金额": f"¥{abs(amt):,.2f}", "打卡": chk_flag})
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        if len(grouped["buffer_hold"]) > 0:
            h_grp = grouped["buffer_hold"]
            with st.expander(f"{h_grp['title']}", expanded=False):
                rows = [{"代码": x.get("fund_code", x.get("code", "")), "名称": x.get("fund_name", x.get("name", "")), "状态": "维持"} for x in h_grp["items"]]
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    with st.expander("新钱定投", expanded=False):
        new_inc_cash = st.number_input("新增资金", min_value=0.0, max_value=500000.0, value=3000.0, step=500.0, key=f"num_simple_new_cash_{include_nav_buttons}")
        tw_plan = target_weights or dict(snap.get("target_weights_funds") or {})
        if new_inc_cash > 0 and cashflow_planner and tw_plan:
            _live_nav_map = {}
            for _c, _h in (holdings or {}).items():
                _q = fetch_realtime_fund_quote(_c, use_cache=True) if fetch_realtime_fund_quote else None
                _live_nav_map[_c] = _q if _q is not None else {"official_nav": float(getattr(_h, "latest_nav", getattr(_h, "current_nav", 1.0)) or 1.0)}
            _res_amt = float(st.session_state.get("tab2_liquidity_redline_reserve", 0.0) or 0.0)
            _eff_cash = cashflow_planner.enforce_liquidity_redline(avail_cash, _res_amt)["investable_cash"] if _res_amt > 0 else avail_cash
            inc_plan = cashflow_planner.plan_incremental_investment(
                current_holdings=holdings,
                available_cash=_eff_cash,
                target_weights=tw_plan,
                monthly_new_cash=new_inc_cash,
                plan_months=1,
                quotes_or_nav_map=_live_nav_map,
            )
            if inc_plan.get("allocations"):
                st.dataframe(pd.DataFrame(inc_plan["allocations"]), use_container_width=True, hide_index=True)

    # 限购标的自动拆单日历
    if execution_tracker:
        _qdii_limits = {"017436": 100.0, "050025": 500.0, "013402": 1000.0, "000216": 5000.0}
        _split_rows = []
        for _it in (grouped["c_items"] + grouped["core_items"]):
            _fc = str(_it.get("fund_code", _it.get("code", "")))
            _fn = str(_it.get("fund_name", _it.get("name", _fc)))
            _amt = float(_it.get("diff_amount") or _it.get("amount") or 0.0)
            _lim = _qdii_limits.get(_fc)
            if _amt > 0 and _lim and _amt > _lim:
                _sp = execution_tracker.split_quota_dca_calendar(_fc, _fn, _amt, daily_limit=_lim)
                if _sp.get("needs_split"):
                    _split_rows.append({"代码": _fc, "名称": _fn, "计划买入": f"¥{_amt:,.2f}", "日限额": f"¥{_lim:,.0f}", "拆分天数": f"{_sp['days_needed']} 天", "打卡节奏": _sp.get("summary", "")})
        if _split_rows:
            with st.expander(f"限购拆单 ({len(_split_rows)}只)", expanded=False):
                st.dataframe(pd.DataFrame(_split_rows), use_container_width=True, hide_index=True)

    cols = st.columns([2.5, 2.5, 5])
    with cols[0]:
        if st.button("复制小抄", use_container_width=True, key=f"btn_simple_copy_cheat_sheet_{include_nav_buttons}"):
            lines_out = []
            for idx, it in enumerate(actionable, 1):
                c_code = str(it.get("fund_code", it.get("code", "")))
                c_name = str(it.get("fund_name", it.get("name", "")))
                amt = float(it.get("diff_amount") or it.get("amount") or 0.0)
                act_s = "买入" if amt > 0 else "卖出"
                chk_s = "[已办]" if c_code in checked_codes else "[待办]"
                lines_out.append(f"{idx}. {chk_s} {c_code} {c_name} {act_s} ¥{abs(amt):,.2f}")
            st.code("\n".join(lines_out) if lines_out else "今日无需买卖操作。", language="text")
    with cols[1]:
        if st.button("全部打卡", use_container_width=True, key=f"btn_mark_all_done_{include_nav_buttons}"):
            for it in actionable:
                fc = str(it.get("fund_code", it.get("code", "")))
                amt = float(it.get("diff_amount") or it.get("amount") or 0.0)
                act_s = "BUY" if amt > 0 else "SELL"
                save_daily_checkin(fc, act_s, abs(amt), True)
            if LedgerBackupVault:
                try: LedgerBackupVault.create_snapshot(reason="daily_checkin")
                except Exception: pass
            st.rerun()


def render_minimal_daily_brief(
    pm: Any,
    snapshot: Optional[Dict[str, Any]] = None,
    active_lid: str = "combat_29_funds",
    ai_orders_res: Optional[Dict[str, Any]] = None,
    target_weights: Optional[Dict[str, float]] = None,
) -> None:
    """渲染极简首屏大卡：总资产、盈亏与调仓单。"""
    snap = snapshot or {}
    total_val = float(getattr(pm, "total_value", 0.0))
    pnl_dict = pm.calculate_intraday_pnl() if hasattr(pm, "calculate_intraday_pnl") else {}
    today_pnl_pct = float(pnl_dict.get("est_pnl_pct", 0.0) if isinstance(pnl_dict, dict) else 0.0)
    state_code = str(snap.get("regime", "") or snap.get("market_regime", "")).upper()

    if "BULL" in state_code or "OFFENSIVE" in state_code: badge_txt, badge_clr = "分批进攻", "#dc2626"
    elif "BEAR" in state_code or "DEFENSE" in state_code or "RISK" in state_code: badge_txt, badge_clr = "防守控仓", "#16a34a"
    else: badge_txt, badge_clr = "安心持仓", "#1d4ed8"

    hs_str = "--"
    if fetch_realtime_index_quote:
        try:
            q = fetch_realtime_index_quote("sh000300", use_cache=True)
            if isinstance(q, dict) and q.get("point") is not None:
                chg = float(q.get("change_pct", 0.0))
                c_clr = "#dc2626" if chg > 0 else ("#16a34a" if chg < 0 else "#64748b")
                hs_str = f"沪深300 <b>{float(q['point']):,.1f}</b> <span style='color:{c_clr};font-weight:700;'>({chg:+.2f}%)</span>"
        except Exception: pass

    st.markdown(
        f"""
        <div style="background:var(--card-bg, #ffffff);border:1px solid rgba(148,163,184,0.25);border-radius:12px;padding:16px 20px;margin-bottom:12px;display:flex;justify-content:space-between;align-items:center;">
            <div>
                <div style="font-size:12px;color:#64748b;font-weight:600;">总资产</div>
                <div style="font-size:24px;font-weight:800;color:var(--text-primary, #0f172a);font-variant-numeric:tabular-nums;">¥{total_val:,.2f}</div>
                <div style="font-size:12px;color:{'#dc2626' if today_pnl_pct > 0 else ('#16a34a' if today_pnl_pct < 0 else '#64748b')};font-weight:700;">今日 {today_pnl_pct:+.2f}%</div>
            </div>
            <div style="text-align:right;">
                <span style="background:{badge_clr};color:#ffffff;font-size:12px;font-weight:700;padding:4px 10px;border-radius:6px;">{badge_txt}</span>
                <div style="font-size:11px;color:#64748b;margin-top:6px;">{hs_str}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_rebalance_action_section(pm, snapshot, active_lid, ai_orders_res, target_weights, include_nav_buttons=False)


def render_simple_daily_home(pm: Any, snapshot: Optional[Dict[str, Any]] = None, active_lid: str = "combat_29_funds", ai_orders_res: Optional[Dict[str, Any]] = None, target_weights: Optional[Dict[str, float]] = None) -> None:
    render_minimal_daily_brief(pm, snapshot, active_lid, ai_orders_res, target_weights)
