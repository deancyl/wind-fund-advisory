# -*- coding: utf-8 -*-
"""
AGY2 Daily Brief View (G33 零废话精简组件与今日调仓区)
规则：标题 <= 6 字、按钮 <= 4 字、所有解释收进 i 弹窗、100% 消费真实后端数据。
"""
import streamlit as st
import pandas as pd
from typing import Dict, Any, List, Optional

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


class IntentGroup(list):
    """意图分组容器：兼容列表迭代与字典键值读取。"""
    def __init__(self, items: List[Dict[str, Any]], title: str = "", summary_text: str = "", **kwargs):
        super().__init__(items)
        self.title, self.summary_text, self.items, self.meta = title, summary_text, items, dict(kwargs)

    @property
    def count(self) -> int:
        return len(self)

    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, str):
            if key == "items": return self.items
            if key == "count": return len(self)
            if key == "title": return self.title
            if key == "summary_text": return self.summary_text
            if key in self.meta: return self.meta[key]
            raise KeyError(key)
        return super().__getitem__(key)

    def get(self, key: str, default: Any = None) -> Any:
        return self[key] if key in ("items", "count", "title", "summary_text") else self.meta.get(key, default)

    def __contains__(self, item: Any) -> bool:
        return True if (isinstance(item, str) and (item in ("items", "count", "title", "summary_text") or item in self.meta)) else super().__contains__(item)

    def keys(self) -> List[str]:
        return ["title", "count", "summary_text", "items"] + list(self.meta.keys())


def group_rebalance_orders_by_intent(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """按操作意图聚合，保证 100% 项数与金额守恒；title 禁止携带任何图标。"""
    tail_items, c_items, core_items, hold_items = [], [], [], []
    for it in items:
        code = str(it.get("fund_code", "") or it.get("code", "")).strip()
        act = str(it.get("action", "") or it.get("direction", "")).upper()
        act_text = str(it.get("action_text", "") or "")
        notes = str(it.get("notes", "") or it.get("reason", ""))
        amt = float(it.get("diff_amount") or it.get("amount") or 0.0)
        mv = float(it.get("market_value") if it.get("market_value") is not None else abs(amt))

        is_c = bool(
            it.get("is_c_replace") or "C转A" in act_text or "C转A" in notes or "C转A" in act
            or (code in ("011612", "011613", "013841") and ("置换" in act_text or "置换" in notes))
        )
        if is_c:
            c_items.append(it)
            continue

        is_hold = bool(
            act == "HOLD" or "维持" in act_text or "维持" in act or "HOLD" in act_text
            or (abs(amt) < 1e-4 and "清仓" not in act_text and not it.get("is_tail"))
        )
        if is_hold:
            hold_items.append(it)
            continue

        is_tail = bool(
            it.get("is_tail") or "清仓" in act_text or "扫尾" in act_text or "归拢" in act_text or "归拢" in notes
            or (("SELL" in act or "减仓" in act) and mv < 200.0)
        )
        if is_tail:
            tail_items.append(it)
            continue

        core_items.append(it)

    tot_tail_cash = sum(abs(float(x.get("diff_amount") or x.get("amount") or x.get("market_value") or 0.0)) for x in tail_items)
    c_sell_cnt = sum(1 for x in c_items if float(x.get("diff_amount") or x.get("amount") or 0.0) < 0)
    c_pair_cnt = c_sell_cnt if c_sell_cnt > 0 else (len(c_items) // 2)

    tail_grp = IntentGroup(
        tail_items,
        title=f"清理尾仓 ({len(tail_items)}只)",
        summary_text=f"清扫 {len(tail_items)} 只免赎碎片尾仓，回收 ¥{tot_tail_cash:,.2f}" if tail_items else "无尾仓",
        total_recovered_cash=round(tot_tail_cash, 2)
    )
    c_grp = IntentGroup(
        c_items,
        title=f"C转A省费 ({c_pair_cnt}组)",
        summary_text=f"将 {c_pair_cnt} 只满30天免赎 C 类置换为 A 类，年省销售服务费约 0.40%" if c_items else "无C转A项",
        saved_fee_pct_annually=0.40,
        c_sell_count=c_pair_cnt
    )
    core_grp = IntentGroup(core_items, title=f"核心调仓 ({len(core_items)}只)", summary_text=f"核心持仓再平衡 ({len(core_items)} 只)" if core_items else "核心持仓平衡")
    hold_grp = IntentGroup(hold_items, title=f"维持持仓 ({len(hold_items)}只)", summary_text=f"{len(hold_items)} 只处于缓冲带内，免折腾")

    is_all_hold = (len(tail_items) == 0 and len(c_items) == 0 and len(core_items) == 0)
    return {
        "tail_sweep": tail_grp, "c_replace": c_grp, "core_trades": core_grp, "buffer_hold": hold_grp,
        "tail_items": tail_items, "c_items": c_items, "core_items": core_items, "hold_items": hold_items,
        "tail_total_cash": round(tot_tail_cash, 2), "total_count": len(items), "is_empty": (len(items) == 0 or is_all_hold)
    }


def render_rebalance_action_section(
    pm: Any,
    snapshot: Optional[Dict[str, Any]] = None,
    active_lid: str = "combat_29_funds",
    ai_orders_res: Optional[Dict[str, Any]] = None,
    target_weights: Optional[Dict[str, float]] = None,
    include_nav_buttons: bool = False,
) -> None:
    """渲染意图分组调仓单、新钱定投与纯文本下单小抄（供统一主视图与兼容易用接口复用）。"""
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

    if grouped["is_empty"]:
        st.success("今日无需操作，安心持有。")
    else:
        if len(grouped["tail_sweep"]) > 0:
            t_grp = grouped["tail_sweep"]
            with st.expander(f"{t_grp['title']} · 回收 ¥{t_grp['total_recovered_cash']:,.2f}", expanded=False):
                df_tail = pd.DataFrame([{"代码": x.get("fund_code", x.get("code", "")), "名称": x.get("fund_name", x.get("name", "")), "市值": f"¥{abs(float(x.get('market_value') if x.get('market_value') is not None else (x.get('diff_amount') or x.get('amount') or 0.0))):.2f}", "操作": "清仓"} for x in t_grp["items"]])
                st.dataframe(df_tail, use_container_width=True, hide_index=True)

        if len(grouped["c_replace"]) > 0:
            c_grp = grouped["c_replace"]
            with st.expander(f"{c_grp['title']} · 年省 0.40%", expanded=True):
                df_c = pd.DataFrame([{"代码": x.get("fund_code", x.get("code", "")), "名称": x.get("fund_name", x.get("name", "")), "方向": "买入A" if float(x.get("diff_amount") or x.get("amount") or 0.0) > 0 else "卖出C", "金额": f"¥{abs(float(x.get('diff_amount') or x.get('amount') or 0.0)):,.2f}"} for x in c_grp["items"]])
                st.dataframe(df_c, use_container_width=True, hide_index=True)

        if len(grouped["core_trades"]) > 0:
            k_grp = grouped["core_trades"]
            with st.expander(f"{k_grp['title']}", expanded=True):
                df_k = pd.DataFrame([{"代码": x.get("fund_code", x.get("code", "")), "名称": x.get("fund_name", x.get("name", "")), "方向": "买入" if float(x.get("diff_amount") or x.get("amount") or 0.0) > 0 else "减仓", "金额": f"¥{abs(float(x.get('diff_amount') or x.get('amount') or 0.0)):,.2f}"} for x in k_grp["items"]])
                st.dataframe(df_k, use_container_width=True, hide_index=True)

        if len(grouped["buffer_hold"]) > 0:
            h_grp = grouped["buffer_hold"]
            with st.expander(f"{h_grp['title']}", expanded=False):
                df_h = pd.DataFrame([{"代码": x.get("fund_code", x.get("code", "")), "名称": x.get("fund_name", x.get("name", "")), "状态": "维持"} for x in h_grp["items"]])
                st.dataframe(df_h, use_container_width=True, hide_index=True)

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

    # 限购标的自动拆单日历（QDII 或单笔较大买入自动提示分日打卡）
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

    cols = st.columns(3 if include_nav_buttons else [3, 7])
    with cols[0]:
        if st.button("复制小抄", use_container_width=True, key=f"btn_simple_copy_cheat_sheet_{include_nav_buttons}"):
            lines_out = []
            actionable = [
                it for it in (grouped["tail_items"] + grouped["c_items"] + grouped["core_items"])
                if abs(float(it.get("diff_amount") or it.get("amount") or 0.0)) > 1e-4
            ]
            for idx, it in enumerate(actionable, 1):
                c_code = it.get("fund_code", it.get("code", ""))
                c_name = it.get("fund_name", it.get("name", ""))
                amt = float(it.get("diff_amount") or it.get("amount") or 0.0)
                act_s = "买入" if amt > 0 else "卖出"
                lines_out.append(f"{idx}. {c_code} {c_name} {act_s} ¥{abs(amt):,.2f}")
            st.code("\n".join(lines_out) if lines_out else "今日无需买卖操作。", language="text")
    if include_nav_buttons:
        with cols[1]:
            if st.button("导入持仓", use_container_width=True, key="btn_goto_ledger_ops"):
                st.session_state["pending_cross_tab_jump"] = {"tab_index": 0, "tab_name": "持仓"}
                st.rerun()
        with cols[2]:
            if st.button("完整视图", use_container_width=True, key="btn_jump_to_expert_lab"):
                st.session_state["pending_cross_tab_jump"] = {"tab_index": 3, "tab_name": "工具"}
                st.rerun()


def render_minimal_daily_brief(
    pm: Any,
    snapshot: Optional[Dict[str, Any]] = None,
    active_lid: str = "combat_29_funds",
    sentry_rep: Optional[Dict[str, Any]] = None,
    ai_orders_res: Optional[Dict[str, Any]] = None,
    target_weights: Optional[Dict[str, float]] = None
) -> None:
    """渲染零废话日常主视图（所有解释性说明均收进 i 弹窗）。"""
    snap = snapshot or {}
    holdings = getattr(pm, "holdings", {})

    market_state = str(snap.get("market_state") or snap.get("advisory_verdict") or "待同步")
    core_action = str(snap.get("core_action_advice") or snap.get("advisory_takeaway") or "保持均衡配置。")
    state_code = str(snap.get("market_state_code") or snap.get("regime") or "NEUTRAL").upper()
    plan_mode_label = "存量瘦身重构" if active_lid == "combat_29_funds" else "动态股债平衡"

    if "BULL" in state_code or "OFFENSIVE" in state_code: badge_txt, badge_clr = "分批进攻", "#dc2626"
    elif "BEAR" in state_code or "DEFENSE" in state_code or "RISK" in state_code: badge_txt, badge_clr = "防守控仓", "#16a34a"
    else: badge_txt, badge_clr = "安心持仓", "#1d4ed8"

    def _fmt_idx(sym: str, label: str) -> str:
        if fetch_realtime_index_quote:
            try:
                q = fetch_realtime_index_quote(sym, use_cache=True)
                if isinstance(q, dict) and q.get("point") is not None:
                    chg = float(q.get("change_pct", 0.0))
                    c_clr = "#dc2626" if chg > 0 else ("#16a34a" if chg < 0 else "#64748b")
                    return f"{label} <b>{float(q['point']):,.1f}</b> <span style='color:{c_clr};font-weight:700;'>({chg:+.2f}%)</span>"
            except Exception: pass
        return f"{label} <b>--</b>"

    idx_line = " &nbsp;|&nbsp; ".join([
        _fmt_idx("sh000300", "沪深300"),
        _fmt_idx("sh000688", "科创50"),
        _fmt_idx("sh000922", "中证红利"),
    ])

    h1_l, h1_r = st.columns([9.2, 0.8])
    with h1_l:
        st.markdown(
            f"""<div style="background:var(--card-bg,rgba(148,163,184,0.08));border:1px solid var(--border-color,rgba(148,163,184,0.22));border-radius:8px;padding:10px 14px;margin-bottom:8px;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
                    <span style="font-weight:700;font-size:0.96rem;color:var(--text-primary);">市场定调 · {market_state}</span>
                    <span style="font-weight:700;font-size:0.82rem;color:{badge_clr};padding:1px 8px;border-radius:4px;border:1px solid {badge_clr};">{badge_txt}</span>
                </div>
                <div style="font-size:0.82rem;color:var(--text-secondary);">当前方案：{plan_mode_label} &nbsp;|&nbsp; {idx_line}</div>
            </div>""",
            unsafe_allow_html=True
        )
    with h1_r:
        with st.popover("i", help="查看定调依据与数据安全说明"):
            st.markdown(f"**大势研判**：{core_action}")
            st.markdown(f"**执行口径**：当前账本执行 `{plan_mode_label}`，与下方调仓清单严格同源。")
            st.markdown("**数据安全**：每次改写账本前均自动生成不可变冷备份，点击顶栏撤回图标即可一键恢复。")

    total_eq = float(getattr(pm, "total_equity", 0.0))
    avail_cash = float(getattr(pm, "available_cash", 0.0))
    mkt_val = sum(float(getattr(h, "shares", 0.0)) * float(getattr(h, "current_nav", 1.0)) for h in holdings.values()) if holdings else 0.0
    cost_val = sum(float(getattr(h, "shares", 0.0)) * float(getattr(h, "cost_price", getattr(h, "current_nav", 1.0))) for h in holdings.values()) if holdings else 0.0
    tot_pnl = mkt_val - cost_val
    tot_pnl_pct = (tot_pnl / cost_val * 100.0) if cost_val > 0 else 0.0

    day_pnl_rmb, day_pnl_pct = 0.0, 0.0
    if hasattr(pm, "calculate_intraday_pnl"):
        try:
            pnl_data = pm.calculate_intraday_pnl()
            if isinstance(pnl_data, dict):
                day_pnl_rmb = float(pnl_data.get("total_est_pnl", 0.0) or 0.0)
                day_pnl_pct = float(pnl_data.get("total_est_pnl_pct", 0.0) or 0.0)
        except Exception: pass

    c_m1, c_m2, c_m3 = st.columns(3)
    c_m1.metric("总资产", f"¥{total_eq:,.2f}", f"现金 ¥{avail_cash:,.2f}")
    c_m2.metric("今日预估", f"{day_pnl_pct:+.2f}%", f"{day_pnl_rmb:+,.2f} 元")
    c_m3.metric("累计盈亏", f"{tot_pnl_pct:+.2f}%", f"{tot_pnl:+,.2f} 元")

    if sentry_rep and isinstance(sentry_rep, dict) and sentry_rep.get("alerts"):
        top_a = sentry_rep["alerts"][0]
        st.caption(f"风控首条提示：{top_a.get('title') or top_a.get('message')}")

    render_rebalance_action_section(pm, snap, active_lid, ai_orders_res, target_weights, include_nav_buttons=True)


render_simple_daily_home = render_minimal_daily_brief
