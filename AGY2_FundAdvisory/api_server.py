# -*- coding: utf-8 -*-
"""
AGY2 Cross-Platform Local API Server (G32)
为后续 Windows 电脑版 (Tauri + React .exe) 与 Android 手机版 (Capacitor/Flutter .apk)
提供统一、纯净、零 HTML 污染的 REST JSON 数据底座。
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException
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
from portfolio_manager import fetch_realtime_index_quote
import cashflow_planner
import data_resilience_guard
import forward_audit_logger
from ledger_backup_vault import LedgerBackupVault
from ui_daily_brief import group_rebalance_orders_by_intent

app = FastAPI(title="AGY2 Local Advisory Engine API", version="5.12-G32")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_active_context(ledger_id: Optional[str] = None):
    mlm = MultiLedgerManager()
    lid = ledger_id or mlm.get_active_ledger_id() or "combat_29_funds"
    try:
        pm = mlm.get_pm(lid)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"账本未找到: {lid}")
    snap = StrategyBridge.get_latest_market_snapshot(force_reload=False)
    return mlm, lid, pm, snap


class CashflowPlanRequest(BaseModel):
    ledger_id: Optional[str] = None
    monthly_new_cash: float = 3000.0
    plan_months: int = 3
    rigid_reserve: float = 0.0


class RestoreBackupRequest(BaseModel):
    snapshot_id: str


@app.get("/api/health")
def api_health() -> Dict[str, Any]:
    health = data_resilience_guard.DataSourceHealthRegistry.get_health_summary()
    return {"status": "ok", "version": "5.12-G32", "data_sources": health}


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
    rx = StrategyBridge.get_combat_29_vs_reconstructed_6_preset() if lid == "combat_29_funds" else {}
    tw = dict(rx.get("reconstructed_6_weights", {})) if rx else (
        StrategyBridge.compute_dynamic_tier_weights("C3", snap).get("weights", {})
    )
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
    rx = StrategyBridge.get_combat_29_vs_reconstructed_6_preset() if lid == "combat_29_funds" else {}
    tw = dict(rx.get("reconstructed_6_weights", {})) if rx else (
        StrategyBridge.compute_dynamic_tier_weights("C3", snap).get("weights", {})
    )
    investable = cashflow_planner.enforce_liquidity_redline(pm.available_cash, req.rigid_reserve)
    dca = cashflow_planner.plan_incremental_investment(
        current_holdings=pm.holdings,
        target_weights=tw,
        monthly_new_cash=req.monthly_new_cash,
        plan_months=req.plan_months,
        available_cash=investable,
    )
    c300_q = fetch_realtime_index_quote("sh000300", use_cache=True) or {}
    c300_pt = float(c300_q.get("point") or 3950.0)
    bullets = cashflow_planner.generate_left_side_bullet_plan(
        investable_spare_cash=investable,
        current_index_point=c300_pt,
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_server:app", host="127.0.0.1", port=8000, reload=False)
