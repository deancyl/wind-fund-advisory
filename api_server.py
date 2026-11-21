# -*- coding: utf-8 -*-
"""
AGY2 Cross-Platform Local API Server (v5.13-G33)
为 Windows 电脑版 (Tauri + React .exe) 与 Android 手机版 (Capacitor/React .apk)
提供统一、纯净、零 HTML 与零 Emoji 污染的 REST JSON 数据底座。
"""

import base64
import re
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR if (CURRENT_DIR / "AGY2_FundAdvisory").exists() else CURRENT_DIR.parent
AGY2_DIR = ROOT_DIR / "AGY2_FundAdvisory"

for p in [str(ROOT_DIR), str(AGY2_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from multi_ledger_manager import MultiLedgerManager
from strategy_bridge import StrategyBridge
from portfolio_manager import (
    CORE_STRATEGY_POOL,
    fetch_realtime_index_quote,
    prefetch_batch_fund_quotes,
)
from advisory_engine import ActiveRiskSentry
import cashflow_planner
import execution_tracker
import shadow_portfolio_tracker
import data_resilience_guard
import forward_audit_logger
from ledger_backup_vault import LedgerBackupVault
from ui_daily_brief import group_rebalance_orders_by_intent

app = FastAPI(title="AGY2 Local Advisory Engine API", version="5.13-G33")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_EMOJI_RE = re.compile(r"[\U0001F300-\U0001FAFF\u2600-\u27BF\uFE0F\u200D]")


def _clean_text(val: Any) -> str:
    s = str(val or "")
    s = _HTML_TAG_RE.sub("", s)
    s = _EMOJI_RE.sub("", s)
    return re.sub(r"\s{2,}", " ", s).strip()


def _sanitize_v1_payload(obj: Any) -> Any:
    """递归剥离 HTML 标签与 Unicode Emoji，保证 /api/v1/* 返回纯净结构化 JSON。"""
    if isinstance(obj, str):
        return _clean_text(obj)
    if isinstance(obj, list):
        return [_sanitize_v1_payload(x) for x in obj]
    if isinstance(obj, tuple):
        return [_sanitize_v1_payload(x) for x in obj]
    if isinstance(obj, dict):
        return {str(k): _sanitize_v1_payload(v) for k, v in obj.items()}
    return obj


def _get_active_context(ledger_id: Optional[str] = None):
    mlm = MultiLedgerManager()
    lid = ledger_id or mlm.get_active_ledger_id() or "combat_29_funds"
    try:
        pm = mlm.get_pm(lid)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"账本未找到: {lid}")
    snap = StrategyBridge.get_latest_market_snapshot(force_reload=False)
    return mlm, lid, pm, snap


def _target_weights_for_ledger(lid: str, snap: Dict[str, Any]) -> Dict[str, float]:
    rx = StrategyBridge.get_combat_29_vs_reconstructed_6_preset() if lid == "combat_29_funds" else {}
    if rx and rx.get("reconstructed_6_weights"):
        return dict(rx["reconstructed_6_weights"])
    return dict(StrategyBridge.compute_dynamic_tier_weights("C3", snap).get("weights", {}))


def _redemption_fee_status(holding_days: int, share_class: str) -> Dict[str, Any]:
    s_cls = str(share_class or "A").strip().upper()
    if holding_days < 7:
        return {"fee_rate_pct": 1.5, "status_code": "PENALTY_LOCKED", "label": "未满7天惩罚锁"}
    if s_cls == "C":
        if holding_days >= 30:
            return {"fee_rate_pct": 0.0, "status_code": "EXEMPT", "label": "满30天免赎"}
        return {"fee_rate_pct": 0.5, "status_code": "SHORT_HOLD", "label": "未满30天0.5%"}
    if holding_days >= 365:
        return {"fee_rate_pct": 0.0, "status_code": "EXEMPT", "label": "满1年免赎"}
    if holding_days >= 180:
        return {"fee_rate_pct": 0.25, "status_code": "LOW_FEE", "label": "低费0.25%"}
    if holding_days >= 30:
        return {"fee_rate_pct": 0.5, "status_code": "STANDARD_FEE", "label": "标准0.5%"}
    return {"fee_rate_pct": 0.75, "status_code": "SHORT_HOLD", "label": "短期0.75%"}


def _compute_mae_stats(quotes_map: Dict[str, Any], total_holdings: int) -> Dict[str, Any]:
    off_diffs: List[float] = []
    dual_diffs: List[float] = []
    for q in quotes_map.values():
        if not q:
            continue
        est_v = getattr(q, "est_gszzl", getattr(q, "gszzl", None))
        off_v = getattr(q, "official_chg_pct", None)
        tt_v = getattr(q, "tiantian_gszzl", None)
        pen_v = getattr(q, "penetration_gszzl", None)
        if getattr(q, "is_official_nav", False) and off_v is not None and est_v is not None:
            off_diffs.append(abs(float(est_v) - float(off_v)))
        if tt_v is not None and pen_v is not None:
            dual_diffs.append(abs(float(pen_v) - float(tt_v)))
    off_cnt = len(off_diffs)
    return {
        "official_published_count": off_cnt,
        "total_holdings_count": total_holdings,
        "mae_pct": round(sum(off_diffs) / off_cnt, 4) if off_cnt > 0 else None,
        "dual_source_diff_pct": round(sum(dual_diffs) / len(dual_diffs), 4) if dual_diffs else None,
        "is_official_nav": (total_holdings > 0 and off_cnt == total_holdings),
    }


def _safe_index_point(snap: Dict[str, Any]) -> float:
    q = fetch_realtime_index_quote("sh000300", use_cache=True) or {}
    return float(q.get("point") or snap.get("c300_close") or snap.get("hs300_point") or snap.get("c300_price") or 0.0)


class CashflowPlanRequest(BaseModel):
    ledger_id: Optional[str] = None
    monthly_new_cash: float = 3000.0
    plan_months: int = 3
    rigid_reserve: float = 0.0


class RestoreBackupRequest(BaseModel):
    snapshot_id: str


class ImportTextRequest(BaseModel):
    ledger_id: Optional[str] = None
    text: str
    available_cash: Optional[float] = None
    mode: str = "preview"


# =====================================================================
# Legacy /api/* endpoints (G32 compatibility)
# =====================================================================

@app.get("/api/health")
def api_health() -> Dict[str, Any]:
    health = data_resilience_guard.DataSourceHealthRegistry.get_health_summary()
    return {"status": "ok", "version": "5.13-G33", "data_sources": health}


@app.get("/api/overview")
def api_overview(ledger_id: Optional[str] = None) -> Dict[str, Any]:
    mlm, lid, pm, snap = _get_active_context(ledger_id)
    pnl = pm.calculate_intraday_pnl() if hasattr(pm, "calculate_intraday_pnl") else {}
    indices = {}
    for sym, name in [("sh000300", "沪深300"), ("sh000688", "科创50"), ("sh000922", "中证红利")]:
        q = fetch_realtime_index_quote(sym, use_cache=True) or {}
        indices[sym] = {
            "name": q.get("name", name),
            "point": q.get("point"),
            "change_pct": q.get("change_pct"),
        }
    return {
        "ledger_id": lid,
        "market_state": snap.get("market_state", "待同步"),
        "regime": snap.get("regime", "NEUTRAL"),
        "plan_mode": "存量瘦身重构" if lid == "combat_29_funds" else "动态股债平衡",
        "indices": indices,
        "total_equity": round(float(getattr(pm, "total_equity", 0.0)), 2),
        "available_cash": round(float(getattr(pm, "available_cash", 0.0)), 2),
        "today_est_pnl": round(float(pnl.get("total_est_pnl", 0.0) or 0.0), 2),
        "today_est_pnl_pct": round(float(pnl.get("total_est_pnl_pct", 0.0) or 0.0), 2),
        "holding_count": len(getattr(pm, "holdings", {})),
    }


@app.get("/api/holdings")
def api_holdings(ledger_id: Optional[str] = None) -> Dict[str, Any]:
    _, lid, pm, _ = _get_active_context(ledger_id)
    rows = []
    for code, h in getattr(pm, "holdings", {}).items():
        sh = float(getattr(h, "shares", 0.0))
        nav = float(getattr(h, "current_nav", 1.0))
        cost = float(getattr(h, "cost_price", nav))
        mv = round(sh * nav, 2)
        pnl = round(mv - sh * cost, 2)
        rows.append({
            "fund_code": code,
            "fund_name": getattr(h, "fund_name", code),
            "share_class": getattr(h, "share_class", "A"),
            "market_value": mv,
            "floating_pnl": pnl,
            "floating_pnl_pct": round((pnl / (sh * cost) * 100.0) if (sh * cost) > 0 else 0.0, 2),
        })
    rows.sort(key=lambda x: x["market_value"], reverse=True)
    return {"ledger_id": lid, "count": len(rows), "items": rows}


@app.get("/api/rebalance")
def api_rebalance(ledger_id: Optional[str] = None) -> Dict[str, Any]:
    _, lid, pm, snap = _get_active_context(ledger_id)
    tw = _target_weights_for_ledger(lid, snap)
    res = StrategyBridge.generate_ai_rebalance_orders(
        pm.holdings,
        pm.available_cash,
        tw,
        pm=pm,
        mode="gentle",
        min_buffer_pct=3.0,
        c_replace="011613" if lid == "combat_29_funds" else None,
        core_anchor_code="002351",
    )
    grouped = group_rebalance_orders_by_intent(res.get("items", []))
    return {
        "ledger_id": lid,
        "is_empty": grouped["is_empty"],
        "tail_sweep": {"title": grouped["tail_sweep"]["title"], "recovered_cash": grouped["tail_total_cash"], "items": grouped["tail_items"]},
        "c_replace": {"title": grouped["c_replace"]["title"], "c_sell_count": grouped["c_replace"].get("c_sell_count", 0), "items": grouped["c_items"]},
        "core_trades": {"title": grouped["core_trades"]["title"], "items": grouped["core_items"]},
        "buffer_hold": {"title": grouped["buffer_hold"]["title"], "count": len(grouped["hold_items"]), "items": grouped["hold_items"]},
    }


@app.post("/api/cashflow/plan")
def api_cashflow_plan(req: CashflowPlanRequest) -> Dict[str, Any]:
    _, lid, pm, snap = _get_active_context(req.ledger_id)
    tw = _target_weights_for_ledger(lid, snap)
    investable = cashflow_planner.enforce_liquidity_redline(pm.available_cash, req.rigid_reserve)
    dca = cashflow_planner.plan_incremental_investment(
        current_holdings=pm.holdings,
        target_weights=tw,
        monthly_new_cash=req.monthly_new_cash,
        plan_months=req.plan_months,
        available_cash=investable,
    )
    bullets = cashflow_planner.generate_left_side_bullet_plan(
        investable_spare_cash=investable,
        current_index_point=_safe_index_point(snap),
    )
    return {"ledger_id": lid, "investable_cash": investable, "dca_plan": dca, "left_side_bullets": bullets}


@app.get("/api/backups")
def api_list_backups() -> Dict[str, Any]:
    return {"snapshots": LedgerBackupVault.list_snapshots()}


@app.post("/api/backups/restore")
def api_restore_backup(req: RestoreBackupRequest) -> Dict[str, Any]:
    ok = LedgerBackupVault.restore_snapshot(req.snapshot_id)
    if not ok:
        raise HTTPException(status_code=400, detail=f"Snapshot restore failed: {req.snapshot_id}")
    return {"restored": True, "snapshot_id": req.snapshot_id}


@app.get("/api/forward-audit")
def api_forward_audit() -> Dict[str, Any]:
    logs = forward_audit_logger.load_decision_audit_log()
    return {"count": len(logs), "logs": logs[-30:]}


# =====================================================================
# Structured v1 Endpoints (Zero HTML, Zero Emoji, Full 8-Topic Coverage)
# =====================================================================

@app.get("/api/v1/overview")
def api_v1_overview(ledger_id: Optional[str] = None) -> Dict[str, Any]:
    _, lid, pm, snap = _get_active_context(ledger_id)
    holdings = getattr(pm, "holdings", {}) or {}
    codes = list(holdings.keys())
    quotes_map = prefetch_batch_fund_quotes(codes) if codes else {}
    mae_stats = _compute_mae_stats(quotes_map, len(codes))
    pnl = pm.calculate_intraday_pnl() if hasattr(pm, "calculate_intraday_pnl") else {}

    mkt_val = sum(float(getattr(h, "shares", 0.0)) * float(getattr(h, "current_nav", 1.0)) for h in holdings.values())
    cost_val = sum(float(getattr(h, "shares", 0.0)) * float(getattr(h, "cost_price", getattr(h, "current_nav", 1.0))) for h in holdings.values())
    cum_pnl = round(mkt_val - cost_val, 2)
    cum_pnl_pct = round((cum_pnl / cost_val * 100.0) if cost_val > 0 else 0.0, 2)

    indices = {}
    for sym, name in [("sh000300", "沪深300"), ("sh000688", "科创50"), ("sh000922", "中证红利")]:
        q = fetch_realtime_index_quote(sym, use_cache=True) or {}
        indices[sym] = {
            "name": q.get("name", name),
            "point": q.get("point"),
            "change_pct": q.get("change_pct"),
            "is_fallback": bool(q.get("is_fallback", False)),
        }

    state_code = str(snap.get("market_state_code") or snap.get("regime") or "NEUTRAL").upper()
    action_tag = "分批进攻" if ("BULL" in state_code or "OFFENSIVE" in state_code) else ("防守控仓" if ("BEAR" in state_code or "DEFENSE" in state_code or "RISK" in state_code) else "安心持仓")
    plan_mode = "存量瘦身重构" if lid == "combat_29_funds" else "动态股债平衡"

    top_alert = None
    try:
        s_rep = ActiveRiskSentry().inspect_portfolio(holdings=holdings, snapshot=snap)
        alerts = s_rep.get("alerts") or []
        if alerts:
            a0 = alerts[0]
            top_alert = {
                "level": a0.get("level", "yellow"),
                "dimension": a0.get("dimension", "风控"),
                "title": a0.get("title") or a0.get("message", ""),
                "action": a0.get("action", ""),
            }
    except Exception:
        pass

    payload = {
        "ledger_id": lid,
        "total_equity": round(float(getattr(pm, "total_equity", 0.0)), 2),
        "available_cash": round(float(getattr(pm, "available_cash", 0.0)), 2),
        "in_transit_cash": round(float(getattr(pm, "in_transit_cash", 0.0)), 2),
        "holding_count": len(holdings),
        "today_est_pnl": round(float(pnl.get("total_est_pnl", 0.0) or 0.0), 2),
        "today_est_pnl_pct": round(float(pnl.get("total_est_pnl_pct", 0.0) or 0.0), 2),
        "cumulative_pnl": cum_pnl,
        "cumulative_pnl_pct": cum_pnl_pct,
        "is_official_nav": mae_stats["is_official_nav"],
        "market_verdict": {
            "short_label": snap.get("market_state") or snap.get("advisory_verdict") or "待同步",
            "action_tag": action_tag,
            "regime": state_code,
            "plan_mode": plan_mode,
            "detail_explanation": snap.get("core_action_advice") or snap.get("advisory_takeaway") or "保持均衡配置。",
            "data_safety_note": "每次写入账本前自动生成不可变冷备快照，支持一键可逆还原。",
        },
        "indices": indices,
        "data_health": data_resilience_guard.DataSourceHealthRegistry.get_health_summary(),
        "valuation_mae": mae_stats,
        "top_risk_alert": top_alert,
    }
    return _sanitize_v1_payload(payload)


@app.get("/api/v1/holdings")
def api_v1_holdings(ledger_id: Optional[str] = None) -> Dict[str, Any]:
    _, lid, pm, snap = _get_active_context(ledger_id)
    holdings = getattr(pm, "holdings", {}) or {}
    codes = list(holdings.keys())
    quotes_map = prefetch_batch_fund_quotes(codes) if codes else {}
    total_eq = float(getattr(pm, "total_equity", 0.0)) or 1.0

    risk_map: Dict[str, List[str]] = {}
    try:
        s_rep = ActiveRiskSentry().inspect_portfolio(holdings=holdings, snapshot=snap)
        for a in (s_rep.get("alerts") or []):
            fc = str(a.get("fund_code", "")).strip()
            dim = str(a.get("dimension", "")).strip()
            if fc and dim and dim not in risk_map.setdefault(fc, []):
                risk_map[fc].append(dim)
    except Exception:
        pass

    rows = []
    for code, h in holdings.items():
        sh = float(getattr(h, "shares", 0.0))
        nav = float(getattr(h, "current_nav", 1.0))
        cost = float(getattr(h, "cost_price", nav))
        mv = round(sh * nav, 2)
        pnl = round(mv - sh * cost, 2)
        s_cls = str(getattr(h, "share_class", "A") or "A")
        h_days = int(getattr(h, "holding_days", 30))

        q = quotes_map.get(code)
        est_chg = round(float(getattr(q, "est_gszzl", getattr(q, "gszzl", 0.0))), 2) if q else 0.0
        off_chg_raw = getattr(q, "official_chg_pct", None) if q else None
        is_off = bool(getattr(q, "is_official_nav", False) and off_chg_raw is not None) if q else False
        off_chg = round(float(off_chg_raw), 2) if off_chg_raw is not None else None
        est_diff = round(est_chg - off_chg, 2) if (is_off and off_chg is not None) else None

        rows.append({
            "fund_code": code,
            "fund_name": getattr(h, "fund_name", code),
            "share_class": s_cls,
            "shares": round(sh, 4),
            "current_nav": round(nav, 4),
            "cost_price": round(cost, 4),
            "market_value": mv,
            "weight_pct": round(mv / total_eq * 100.0, 2),
            "floating_pnl": pnl,
            "floating_pnl_pct": round((pnl / (sh * cost) * 100.0) if (sh * cost) > 0 else 0.0, 2),
            "est_chg_pct": est_chg,
            "official_chg_pct": off_chg,
            "is_official_nav": is_off,
            "est_diff_pct": est_diff,
            "holding_days": h_days,
            "redemption_fee_status": _redemption_fee_status(h_days, s_cls),
            "risk_tags": risk_map.get(code, []),
        })
    rows.sort(key=lambda x: x["market_value"], reverse=True)
    return _sanitize_v1_payload({"ledger_id": lid, "count": len(rows), "items": rows})


@app.get("/api/v1/rebalance")
def api_v1_rebalance(ledger_id: Optional[str] = None, min_buffer_pct: float = 3.0) -> Dict[str, Any]:
    _, lid, pm, snap = _get_active_context(ledger_id)
    tw = _target_weights_for_ledger(lid, snap)
    res = StrategyBridge.generate_ai_rebalance_orders(
        pm.holdings,
        pm.available_cash,
        tw,
        pm=pm,
        mode="gentle",
        min_buffer_pct=min_buffer_pct,
        c_replace="011613" if lid == "combat_29_funds" else None,
        core_anchor_code="002351",
    )
    items = res.get("items", [])
    grouped = group_rebalance_orders_by_intent(items)

    quota_split_plans = []
    for it in (grouped["c_items"] + grouped["core_items"]):
        amt = float(it.get("diff_amount") or it.get("amount") or 0.0)
        if amt <= 0:
            continue
        code = str(it.get("fund_code", "") or it.get("code", "")).strip()
        name = str(it.get("fund_name", "") or it.get("name", code))
        meta = CORE_STRATEGY_POOL.get(code, {})
        d_lim = float(meta.get("daily_limit", 1e8))
        is_qdii = bool(pm.is_qdii_fund(code, name)) if hasattr(pm, "is_qdii_fund") else ("纳斯达克" in name or "标普" in name)
        settlement = execution_tracker.estimate_settlement_timeline("BUY", is_qdii=is_qdii)
        if amt > d_lim and d_lim < 1e7:
            cal = execution_tracker.split_quota_dca_calendar(code, name, amt, daily_limit=d_lim)
            cal["settlement"] = settlement
            quota_split_plans.append(cal)
        else:
            quota_split_plans.append({
                "fund_code": code,
                "fund_name": name,
                "needs_split": False,
                "total_amount": round(amt, 2),
                "days_needed": 1,
                "settlement": settlement,
            })

    actionable = [
        it for it in (grouped["tail_items"] + grouped["c_items"] + grouped["core_items"])
        if abs(float(it.get("diff_amount") or it.get("amount") or 0.0)) > 1e-4
    ]
    cheat_lines = []
    for idx, it in enumerate(actionable, 1):
        c_code = str(it.get("fund_code", it.get("code", "")))
        c_name = _clean_text(it.get("fund_name", it.get("name", "")))
        amt = float(it.get("diff_amount") or it.get("amount") or 0.0)
        act_s = "买入" if amt > 0 else "卖出"
        cheat_lines.append(f"{idx}. {c_code} {c_name} {act_s} ¥{abs(amt):,.2f}")

    payload = {
        "ledger_id": lid,
        "plan_mode": "存量瘦身重构" if lid == "combat_29_funds" else "动态股债平衡",
        "is_empty": grouped["is_empty"],
        "groups": {
            "tail_sweep": {"title": grouped["tail_sweep"]["title"], "count": len(grouped["tail_items"]), "recovered_cash": grouped["tail_total_cash"], "items": grouped["tail_items"]},
            "c_replace": {"title": grouped["c_replace"]["title"], "count": len(grouped["c_items"]), "c_sell_count": grouped["c_replace"].get("c_sell_count", 0), "items": grouped["c_items"]},
            "core_trades": {"title": grouped["core_trades"]["title"], "count": len(grouped["core_items"]), "items": grouped["core_items"]},
            "buffer_hold": {"title": grouped["buffer_hold"]["title"], "count": len(grouped["hold_items"]), "items": grouped["hold_items"]},
        },
        "quota_split_plans": quota_split_plans,
        "cheat_sheet_lines": cheat_lines,
        "cheat_sheet_text": "\n".join(cheat_lines) if cheat_lines else "今日无需买卖操作。",
    }
    return _sanitize_v1_payload(payload)


@app.post("/api/v1/cashflow/plan")
def api_v1_cashflow_plan(req: CashflowPlanRequest) -> Dict[str, Any]:
    _, lid, pm, snap = _get_active_context(req.ledger_id)
    tw = _target_weights_for_ledger(lid, snap)
    investable = cashflow_planner.enforce_liquidity_redline(pm.available_cash, req.rigid_reserve)
    dca = cashflow_planner.plan_incremental_investment(
        current_holdings=pm.holdings,
        target_weights=tw,
        monthly_new_cash=req.monthly_new_cash,
        plan_months=req.plan_months,
        available_cash=investable,
    )
    inv_cash = float(investable.get("investable_cash", 0.0)) if isinstance(investable, dict) else float(investable or 0.0)
    bullets = cashflow_planner.generate_left_side_bullet_plan(
        investable_spare_cash=inv_cash + float(req.monthly_new_cash) * int(req.plan_months),
        current_index_point=_safe_index_point(snap),
    )
    return _sanitize_v1_payload({"ledger_id": lid, "liquidity_guard": investable, "dca_plan": dca, "left_side_bullets": bullets})


@app.get("/api/v1/audit/trackers")
def api_v1_audit_trackers(ledger_id: Optional[str] = None) -> Dict[str, Any]:
    _, lid, pm, _ = _get_active_context(ledger_id)
    holdings = getattr(pm, "holdings", {}) or {}
    codes = list(holdings.keys())
    quotes_map = prefetch_batch_fund_quotes(codes) if codes else {}
    nav_map = {
        c: float(getattr(quotes_map.get(c), "gsz", 0.0) or getattr(quotes_map.get(c), "dwjz", 0.0) or getattr(h, "current_nav", 1.0))
        for c, h in holdings.items()
    }
    shadow_comp = shadow_portfolio_tracker.compare_live_vs_shadow(lid, holdings, nav_map)
    c300_q = fetch_realtime_index_quote("sh000300", use_cache=True) or {}
    c300_pt = float(c300_q.get("point") or 0.0) or None
    fwd_eval = forward_audit_logger.evaluate_forward_performance(current_nav_map=nav_map, current_hs300=c300_pt)
    logs = forward_audit_logger.load_decision_audit_log()
    return _sanitize_v1_payload({
        "ledger_id": lid,
        "shadow_tracker": shadow_comp,
        "forward_audit": fwd_eval,
        "recent_logs_count": len(logs),
        "recent_logs": logs[-30:],
    })


@app.get("/api/v1/backups")
def api_v1_list_backups() -> Dict[str, Any]:
    snaps = LedgerBackupVault.list_snapshots()
    return _sanitize_v1_payload({"count": len(snaps), "snapshots": snaps})


@app.post("/api/v1/backups/restore")
def api_v1_restore_backup(req: RestoreBackupRequest) -> Dict[str, Any]:
    ok = LedgerBackupVault.restore_snapshot(req.snapshot_id)
    if not ok:
        raise HTTPException(status_code=400, detail=f"快照恢复失败: {req.snapshot_id}")
    return _sanitize_v1_payload({"restored": True, "snapshot_id": req.snapshot_id})


@app.post("/api/v1/import/text")
def api_v1_import_text(req: ImportTextRequest) -> Dict[str, Any]:
    if not str(req.text or "").strip():
        raise HTTPException(status_code=400, detail="导入文本不能为空")
    _, lid, pm, _ = _get_active_context(req.ledger_id)
    parsed = pm.parse_smart_text_holdings(req.text)
    applied = False
    if req.mode in ("merge", "overwrite") and parsed:
        LedgerBackupVault.create_snapshot(reason=f"api_import_text_{lid}")
        pm.import_from_smart_text(
            parsed,
            available_cash=float(req.available_cash if req.available_cash is not None else pm.available_cash),
            replace_existing=(req.mode == "overwrite"),
        )
        pm.save_state()
        applied = True
    return _sanitize_v1_payload({
        "ledger_id": lid,
        "mode": req.mode,
        "applied": applied,
        "parsed_count": len(parsed),
        "items": parsed,
    })


@app.post("/api/v1/import/ocr")
async def api_v1_import_ocr(request: Request) -> Dict[str, Any]:
    ctype = str(request.headers.get("content-type", "")).lower()
    ledger_id: Optional[str] = None
    mode = "preview"
    image_bytes = b""

    if "multipart/form-data" in ctype:
        form = await request.form()
        up_file = form.get("file")
        if up_file is not None and hasattr(up_file, "read"):
            image_bytes = await up_file.read()
        ledger_id = str(form.get("ledger_id")) if form.get("ledger_id") else None
        if form.get("mode"):
            mode = str(form.get("mode"))
    else:
        try:
            body = await request.json()
        except Exception:
            body = {}
        if isinstance(body, dict):
            ledger_id = body.get("ledger_id")
            mode = str(body.get("mode", "preview"))
            b64 = str(body.get("image_base64", "") or "")
            if "," in b64:
                b64 = b64.split(",", 1)[1]
            if b64:
                try:
                    image_bytes = base64.b64decode(b64)
                except Exception:
                    raise HTTPException(status_code=400, detail="无效的 image_base64 编码")

    if not image_bytes:
        raise HTTPException(status_code=400, detail="未上传有效的截图文件")

    _, lid, pm, _ = _get_active_context(ledger_id)
    try:
        parsed = pm.parse_screenshot_ocr_holdings(image_bytes)
    except Exception:
        parsed = []

    applied = False
    if mode in ("merge", "overwrite") and parsed:
        LedgerBackupVault.create_snapshot(reason=f"api_import_ocr_{lid}")
        pm.import_from_smart_text(parsed, available_cash=pm.available_cash, replace_existing=(mode == "overwrite"))
        pm.save_state()
        applied = True

    return _sanitize_v1_payload({
        "ledger_id": lid,
        "mode": mode,
        "applied": applied,
        "parsed_count": len(parsed),
        "items": parsed,
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_server:app", host="127.0.0.1", port=8000, reload=False)
