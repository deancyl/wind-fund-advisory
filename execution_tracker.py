# -*- coding: utf-8 -*-
"""
AGY2 Execution Tracker (G29 实盘执行闭环独立子模块)
===================================================
负责 QDII/高敏标的单日限购自动拆单执行日历、
A股/QDII 在途交割赎回确认倒计时（按工作日跳过周末）、局部增量份额对账 Diff、
以及躺平不动影子账本赛跑数据汇总（零硬编码假数）。
严格控制在 350 行以内，杜绝主文件巨石膨胀。
"""

import math
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
try:
    from shadow_portfolio_tracker import compare_live_vs_shadow as _shadow_compare
except Exception:
    try:
        from AGY2_FundAdvisory.shadow_portfolio_tracker import compare_live_vs_shadow as _shadow_compare
    except Exception:
        _shadow_compare = None


def _add_business_days(start_dt: datetime, n_days: int) -> datetime:
    """按工作日（跳过周六、周日）推算 T+N 日期。"""
    cur = start_dt
    added = 0
    target = max(0, int(n_days))
    while added < target:
        cur += timedelta(days=1)
        if cur.weekday() < 5:
            added += 1
    return cur


def _read_pos_float(obj: Any, field: str) -> Optional[float]:
    if obj is None:
        return None
    val = obj.get(field) if isinstance(obj, dict) else getattr(obj, field, None)
    if val is None or val == "":
        return None
    try:
        f = float(val)
        return f if f > 0.0 else None
    except (TypeError, ValueError):
        return None


def _compute_live_equity_and_cost(
    holdings: Dict[str, Any],
    quotes: Dict[str, Any],
) -> tuple[float, float]:
    """根据真实持仓与可选行情计算实盘当前市值与成本基础。"""
    live_mv = 0.0
    live_cost = 0.0
    for code, h in (holdings or {}).items():
        sh = _read_pos_float(h, "shares") or 0.0
        q = quotes.get(code) if quotes else None
        if q is None and quotes:
            q = quotes.get(str(code))

        q_nav: Optional[float] = None
        if q is not None:
            if isinstance(q, (int, float)):
                q_nav = float(q) if float(q) > 0.0 else None
            else:
                for k in ("official_nav", "gsz", "dwjz", "current_nav", "latest_nav", "nav", "unit_nav"):
                    q_nav = _read_pos_float(q, k)
                    if q_nav is not None:
                        break

        h_nav: Optional[float] = None
        for k in ("current_nav", "latest_nav", "nav", "unit_nav", "cost_price"):
            h_nav = _read_pos_float(h, k)
            if h_nav is not None:
                break

        direct_mv = _read_pos_float(h, "market_value")
        if q_nav is not None and sh > 0.0:
            mv = sh * q_nav
        elif direct_mv is not None:
            mv = direct_mv
        elif h_nav is not None and sh > 0.0:
            mv = sh * h_nav
        else:
            mv = sh * 1.0

        cost_basis = _read_pos_float(h, "cost_basis")
        if cost_basis is None:
            cost_price = _read_pos_float(h, "cost_price") or h_nav or q_nav or 1.0
            cost_basis = sh * cost_price if sh > 0.0 else mv

        live_mv += mv
        live_cost += cost_basis
    return live_mv, live_cost


def split_quota_dca_calendar(
    fund_code: str,
    fund_name: str,
    total_buy_amount: float,
    daily_limit: float = 100.0,
    start_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    限购自动拆单日历：
    当买入金额大于单日限额（如限购 100 元/日，需买入 1,000 元）时，
    自动拆分为 N = ceil(buy_amount / daily_limit) 个交易日的打卡计划。
    """
    amt = max(0.0, float(total_buy_amount))
    lim = max(10.0, float(daily_limit))

    if amt <= lim:
        return {
            "needs_split": False,
            "total_amount": amt,
            "daily_limit": lim,
            "days_needed": 1,
            "schedule": [{"day_index": 1, "amount": amt, "status": "PENDING"}],
        }

    days_needed = math.ceil(amt / lim)
    schedule = []
    rem = amt

    for d in range(1, days_needed + 1):
        cur_amt = min(rem, lim)
        schedule.append({
            "day_index": d,
            "day_label": f"第 {d} 交易日",
            "amount": round(cur_amt, 2),
            "status": "PENDING",
        })
        rem -= cur_amt
        if rem <= 0.001:
            break

    return {
        "needs_split": True,
        "fund_code": fund_code,
        "fund_name": fund_name,
        "total_amount": amt,
        "daily_limit": lim,
        "days_needed": len(schedule),
        "schedule": schedule,
        "summary": f"标的限额 ¥{lim:,.2f}/日，总买入 ¥{amt:,.2f} 自动拆为 {len(schedule)} 笔日历打卡单。",
    }


def estimate_settlement_timeline(
    action_type: str,
    is_qdii: bool = False,
    submit_date_str: Optional[str] = None,
) -> Dict[str, Any]:
    """
    A股与 QDII 在途交割周期与预计到账日测算（按工作日跳过周六周日）
    """
    action = str(action_type).upper()
    sub_dt = datetime.strptime(submit_date_str, "%Y-%m-%d") if submit_date_str else datetime.now()

    if "BUY" in action:
        confirm_t = 2 if is_qdii else 1
        arrive_t = 3 if is_qdii else 2
        label = "申购确认份额"
    else:  # SELL / REDEEM
        confirm_t = 2 if is_qdii else 1
        arrive_t = 7 if is_qdii else 3
        label = "赎回资金到账"

    confirm_dt = _add_business_days(sub_dt, confirm_t)
    arrive_dt = _add_business_days(sub_dt, arrive_t)

    return {
        "action": action,
        "is_qdii": is_qdii,
        "confirm_days": confirm_t,
        "arrive_days": arrive_t,
        "description": f"{'QDII跨境' if is_qdii else 'A股/场外'} {label} 预计 T+{arrive_t} 个工作日确认",
        "expected_confirm_date": confirm_dt.strftime("%Y-%m-%d"),
        "expected_arrive_date": arrive_dt.strftime("%Y-%m-%d"),
    }


def reconcile_incremental_holdings_diff(
    current_holdings: Dict[str, Any],
    incremental_updates: Dict[str, Dict[str, float]],
) -> Dict[str, Any]:
    """
    二次增量份额对账 Diff
    """
    diff_records = []
    for code, upd in incremental_updates.items():
        code_str = str(code).strip().zfill(6)
        curr = current_holdings.get(code_str)

        old_sh = float(getattr(curr, "shares", 0.0) if curr else 0.0)
        new_sh = float(upd.get("shares", old_sh))
        old_cost = float(getattr(curr, "cost_price", 1.0) if curr else 1.0)
        new_cost = float(upd.get("cost_price", old_cost))

        sh_diff = round(new_sh - old_sh, 4)
        diff_records.append({
            "fund_code": code_str,
            "fund_name": getattr(curr, "fund_name", "") if curr else upd.get("fund_name", code_str),
            "old_shares": old_sh,
            "new_shares": new_sh,
            "shares_diff": sh_diff,
            "old_cost": old_cost,
            "new_cost": new_cost,
            "is_modified": abs(sh_diff) > 1e-4 or abs(new_cost - old_cost) > 1e-4,
        })

    return {
        "modified_count": sum(1 for d in diff_records if d["is_modified"]),
        "total_checked": len(diff_records),
        "diff_items": diff_records,
    }


def compare_live_vs_shadow(
    ledger_id: str = "combat_29_funds",
    live_holdings: Optional[Dict[str, Any]] = None,
    current_quotes: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    影子账本赛跑对账门面：
    严格遵循零硬编码假数铁律，无冻结基准时诚实返回 has_baseline=False 与实算实盘收益率。
    """
    holdings = live_holdings or {}
    quotes = current_quotes or {}

    raw_res = None
    if _shadow_compare:
        try:
            raw_res = _shadow_compare(ledger_id, holdings, quotes)
        except Exception:
            pass

    if raw_res and raw_res.get("has_shadow"):
        has_baseline = True
        shadow_mv = float(raw_res.get("shadow_current_equity", 0.0))
        shadow_ret = float(raw_res.get("shadow_return_pct", 0.0))
        live_mv = float(raw_res.get("live_current_equity", 0.0))
        live_cost_basis = float(raw_res.get("live_cost_basis", 0.0))
        live_ret = float(raw_res.get("live_return_pct", 0.0))
        excess_rmb = float(raw_res.get("excess_rmb", 0.0))
        excess_pct = float(raw_res.get("excess_return_pct", 0.0))
        badge = str(raw_res.get("status_badge", ""))
        summary_str = (
            f"实盘组合当前估值 ¥{live_mv:,.2f}，相较原始躺平影子线（¥{shadow_mv:,.2f}）"
            f"差额 ¥{excess_rmb:+,.2f} ({excess_pct:+.2f}%)。"
        )
    else:
        has_baseline = False
        live_mv, live_cost_basis = _compute_live_equity_and_cost(holdings, quotes)
        live_ret = ((live_mv - live_cost_basis) / live_cost_basis * 100.0) if live_cost_basis > 0.01 else 0.0
        shadow_mv = 0.0
        shadow_ret = 0.0
        excess_rmb = 0.0
        excess_pct = 0.0
        badge = "⚪ 尚未冻结躺平基准"
        summary_str = (
            f"账本 [{ledger_id}] 尚未冻结原始躺平基准线，当前实盘估值 ¥{live_mv:,.2f}"
            f"（累计收益率 {live_ret:+.2f}%），请先点击「冻结基准」建立对照起点。"
        )

    return {
        "has_baseline": has_baseline,
        "has_shadow": has_baseline,
        "ledger_id": ledger_id,
        "shadow_mv": round(shadow_mv, 2),
        "shadow_current_market_val": round(shadow_mv, 2),
        "shadow_ret_pct": round(shadow_ret, 2),
        "shadow_return_pct": round(shadow_ret, 2),
        "live_mv": round(live_mv, 2),
        "live_current_market_val": round(live_mv, 2),
        "live_cost_basis": round(live_cost_basis, 2),
        "live_ret_pct": round(live_ret, 2),
        "live_return_pct": round(live_ret, 2),
        "alpha_pct": round(excess_pct, 2),
        "excess_rmb": round(excess_rmb, 2),
        "excess_pct": round(excess_pct, 2),
        "excess_return_rmb": round(excess_rmb, 2),
        "excess_return_pct": round(excess_pct, 2),
        "summary": summary_str,
        "badge": badge,
        "status_badge": badge,
    }


class ExecutionTracker:
    """面向对象的实盘执行闭环门面"""
    @staticmethod
    def split_quota(**kwargs) -> Dict[str, Any]:
        return split_quota_dca_calendar(**kwargs)

    @staticmethod
    def settlement_timeline(**kwargs) -> Dict[str, Any]:
        return estimate_settlement_timeline(**kwargs)

    @staticmethod
    def reconcile_diff(curr: Dict, upd: Dict) -> Dict[str, Any]:
        return reconcile_incremental_holdings_diff(curr, upd)

    @staticmethod
    def compare_shadow(**kwargs) -> Dict[str, Any]:
        return compare_live_vs_shadow(**kwargs)
