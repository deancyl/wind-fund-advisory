# -*- coding: utf-8 -*-
"""
AGY2 Cross-Platform Local API Server (v5.13-G33)
为 Windows 电脑版 (Tauri + React .exe) 与 Android 手机版 (Capacitor/React .apk)
提供统一、纯净、零 HTML 与零 Emoji 污染的 REST JSON 数据底座。
"""

import base64
from contextlib import asynccontextmanager
import logging
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, Any, List, Optional
import anyio
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR if (CURRENT_DIR / "AGY2_FundAdvisory").exists() else CURRENT_DIR.parent
AGY2_DIR = CURRENT_DIR if CURRENT_DIR.name == "AGY2_FundAdvisory" else (ROOT_DIR / "AGY2_FundAdvisory")

for p in [str(AGY2_DIR), str(ROOT_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

import runtime_paths
from multi_ledger_manager import MultiLedgerManager
from strategy_bridge import StrategyBridge
from portfolio_manager import (
    CORE_STRATEGY_POOL,
    fetch_realtime_index_quote,
    prefetch_batch_fund_quotes,
    HoldingItem,
)
from advisory_engine import ActiveRiskSentry, compute_ten_dimension_votes
import sector_watchlist
import cashflow_planner
import execution_tracker
import shadow_portfolio_tracker
import data_resilience_guard
import forward_audit_logger
from ledger_backup_vault import LedgerBackupVault
from rebalance_grouping import group_rebalance_orders_by_intent, load_daily_checkin, save_daily_checkin

logger = logging.getLogger("agy2.api")
_LEDGER_WRITE_LOCK = threading.RLock()

_EXTRA_CORS_ORIGINS = [
    o.strip() for o in os.environ.get("AGY2_CORS_ORIGINS", "").split(",") if o.strip()
]
_ALLOWED_CORS_ORIGINS = [
    "http://localhost",
    "https://localhost",
    "http://127.0.0.1",
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:1420",
    "http://localhost:8501",
    "http://127.0.0.1:8501",
    "http://localhost:8585",
    "http://127.0.0.1:8585",
    "tauri://localhost",
    "http://tauri.localhost",
    "https://tauri.localhost",
    "capacitor://localhost",
] + _EXTRA_CORS_ORIGINS

def _warmup_engine_background() -> None:
    """后台异步预热引擎快照与活跃持仓批量行情，避免首个客户端请求承受冷启动阻塞"""
    try:
        mlm = MultiLedgerManager.get_instance()
        lid = mlm.get_active_ledger_id() or "combat_29_funds"
        pm = mlm.get_pm(lid)
        StrategyBridge.get_latest_market_snapshot(force_reload=False)
        codes = list((getattr(pm, "holdings", {}) or {}).keys())
        if codes:
            prefetch_batch_fund_quotes(codes)
        with ThreadPoolExecutor(max_workers=3) as pool:
            for sym in ("sh000300", "sh000688", "sh000922"):
                pool.submit(fetch_realtime_index_quote, sym, True)
    except Exception:
        pass


@asynccontextmanager
async def _lifespan(app_inst: FastAPI):
    threading.Thread(target=_warmup_engine_background, name="agy2-api-warmup", daemon=True).start()
    yield


app = FastAPI(title="AGY2 Local Advisory Engine API", version="5.22-G43", lifespan=_lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_CORS_ORIGINS,
    allow_origin_regex=r"^https?://(127\.0\.0\.1|localhost)(:\d+)?$",
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-AGY2-Client"],
)

_OVERVIEW_CACHE: Dict[str, Any] = {}
_OVERVIEW_CACHE_LOCK = threading.Lock()
_OVERVIEW_TTL_SEC = 30.0

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
    mlm = MultiLedgerManager.get_instance()
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
    monthly_cash: Optional[float] = None
    reserve_fund: Optional[float] = None

    def get_monthly_cash(self) -> float:
        return float(self.monthly_cash if self.monthly_cash is not None else self.monthly_new_cash)

    def get_reserve(self) -> float:
        return float(self.reserve_fund if self.reserve_fund is not None else self.rigid_reserve)


class RestoreBackupRequest(BaseModel):
    snapshot_id: str


class ImportTextRequest(BaseModel):
    ledger_id: Optional[str] = None
    text: str
    available_cash: Optional[float] = None
    mode: str = "preview"


class ShadowFreezeRequest(BaseModel):
    ledger_id: Optional[str] = None
    baseline_name: Optional[str] = None


class SectorItemRequest(BaseModel):
    code: str
    name: Optional[str] = ""


class WatchlistUpdateRequest(BaseModel):
    action: str = "add"  # add / remove / reset
    code: str = ""
    name: str = ""


class LedgerImportRequest(BaseModel):
    ledger_id: Optional[str] = None
    holdings: Any = None
    available_cash: Optional[float] = None
    replace_existing: bool = True


class RebalanceExecuteRequest(BaseModel):
    ledger_id: Optional[str] = None
    mode: str = "gentle"
    confirm_backup: bool = True


# =====================================================================
# Legacy /api/* endpoints (G32 compatibility)
# =====================================================================

@app.get("/api/health", deprecated=True)
def api_health() -> Dict[str, Any]:
    health = data_resilience_guard.DataSourceHealthRegistry.get_health_summary()
    return {"status": "ok", "version": "5.13-G33", "data_sources": health}


@app.get("/api/overview", deprecated=True)
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


@app.get("/api/holdings", deprecated=True)
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


@app.get("/api/rebalance", deprecated=True)
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


@app.post("/api/cashflow/plan", deprecated=True)
def api_cashflow_plan(req: CashflowPlanRequest) -> Dict[str, Any]:
    _, lid, pm, snap = _get_active_context(req.ledger_id)
    tw = _target_weights_for_ledger(lid, snap)
    holdings = getattr(pm, "holdings", {}) or {}
    codes = list(holdings.keys())
    quotes_map = prefetch_batch_fund_quotes(codes) if codes else {}
    investable = cashflow_planner.enforce_liquidity_redline(pm.available_cash, req.get_reserve())
    dca = cashflow_planner.plan_incremental_investment(
        current_holdings=holdings,
        target_weights=tw,
        monthly_new_cash=req.get_monthly_cash(),
        plan_months=req.plan_months,
        available_cash=investable,
        quotes_or_nav_map=quotes_map,
    )
    bullets = cashflow_planner.generate_left_side_bullet_plan(
        investable_spare_cash=investable,
        current_index_point=_safe_index_point(snap),
    )
    return {"ledger_id": lid, "investable_cash": investable, "dca_plan": dca, "left_side_bullets": bullets}


@app.get("/api/backups", deprecated=True)
def api_list_backups() -> Dict[str, Any]:
    return {"snapshots": LedgerBackupVault.list_snapshots()}


@app.post("/api/backups/restore", deprecated=True)
def api_restore_backup(req: RestoreBackupRequest) -> Dict[str, Any]:
    ok = LedgerBackupVault.restore_snapshot(req.snapshot_id)
    if not ok:
        raise HTTPException(status_code=400, detail=f"Snapshot restore failed: {req.snapshot_id}")
    return {"restored": True, "snapshot_id": req.snapshot_id}


@app.get("/api/forward-audit", deprecated=True)
def api_forward_audit() -> Dict[str, Any]:
    logs = forward_audit_logger.load_decision_audit_log()
    return {"count": len(logs), "logs": logs[-30:]}


# =====================================================================
# Structured v1 Endpoints (Zero HTML, Zero Emoji, Full 8-Topic Coverage)
# =====================================================================

def _compute_intraday_pnl_from_quotes(holdings: Dict[str, Any], quotes_map: Dict[str, Any]) -> Dict[str, float]:
    """复用已批量预取的 FundQuote.gszzl 直接计算当日估算盈亏，避免二次调用 calculate_intraday_pnl"""
    total_mv = 0.0
    total_pnl = 0.0
    for code, h in (holdings or {}).items():
        sh = float(getattr(h, "shares", 0.0) or 0.0)
        mv = float(getattr(h, "market_value", 0.0) or 0.0)
        if mv <= 0.0 and sh > 0.0:
            mv = sh * float(getattr(h, "current_nav", 1.0) or 1.0)
        if sh <= 0.0 or mv <= 0.0:
            continue
        total_mv += mv
        q = quotes_map.get(code)
        gszzl = 0.0
        if q is not None:
            try:
                raw_g = getattr(q, "gszzl", None)
                if raw_g is None and isinstance(q, dict):
                    raw_g = q.get("gszzl")
                gszzl = float(raw_g or 0.0)
            except Exception:
                gszzl = 0.0
        total_pnl += round(mv * (gszzl / 100.0), 2)
    total_pnl = round(total_pnl, 2)
    pnl_pct = round((total_pnl / total_mv * 100.0), 2) if total_mv > 0 else 0.0
    return {"total_est_pnl": total_pnl, "total_est_pnl_pct": pnl_pct}


@app.get("/api/v1/overview")
def api_v1_overview(ledger_id: Optional[str] = None, force: bool = False) -> Dict[str, Any]:
    mlm = MultiLedgerManager.get_instance()
    req_lid = ledger_id or mlm.get_active_ledger_id() or "combat_29_funds"
    now_ts = time.time()
    if not force:
        with _OVERVIEW_CACHE_LOCK:
            cached = _OVERVIEW_CACHE.get(req_lid)
            if cached and (now_ts - cached[0]) < _OVERVIEW_TTL_SEC:
                return cached[1]

    _, lid, pm, snap = _get_active_context(req_lid)
    holdings = getattr(pm, "holdings", {}) or {}
    codes = list(holdings.keys())

    idx_specs = [("sh000300", "沪深300"), ("sh000688", "科创50"), ("sh000922", "中证红利")]
    quotes_map: Dict[str, Any] = {}
    indices: Dict[str, Any] = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        q_fut = pool.submit(prefetch_batch_fund_quotes, codes) if codes else None
        idx_futs = {pool.submit(fetch_realtime_index_quote, sym, True): (sym, name) for sym, name in idx_specs}
        if q_fut is not None:
            try:
                quotes_map = q_fut.result(timeout=8.0) or {}
            except Exception:
                quotes_map = {}
        for fut, (sym, name) in idx_futs.items():
            try:
                q = fut.result(timeout=4.0) or {}
            except Exception:
                q = {}
            indices[sym] = {
                "name": q.get("name", name),
                "point": q.get("point"),
                "change_pct": q.get("change_pct"),
                "is_fallback": bool(q.get("is_fallback", False)),
            }

    mae_stats = _compute_mae_stats(quotes_map, len(codes))
    pnl = _compute_intraday_pnl_from_quotes(holdings, quotes_map)

    mkt_val = sum(float(getattr(h, "shares", 0.0)) * float(getattr(h, "current_nav", 1.0)) for h in holdings.values())
    cost_val = sum(float(getattr(h, "shares", 0.0)) * float(getattr(h, "cost_price", getattr(h, "current_nav", 1.0))) for h in holdings.values())
    cum_pnl = round(mkt_val - cost_val, 2)
    cum_pnl_pct = round((cum_pnl / cost_val * 100.0) if cost_val > 0 else 0.0, 2)

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
    sanitized = _sanitize_v1_payload(payload)
    with _OVERVIEW_CACHE_LOCK:
        _OVERVIEW_CACHE[lid] = (time.time(), sanitized)
    return sanitized


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
        "tail_sweep": {"title": grouped["tail_sweep"]["title"], "count": len(grouped["tail_items"]), "summary": grouped["tail_sweep"].get("summary_text", ""), "recovered_cash": grouped["tail_total_cash"], "items": grouped["tail_items"]},
        "c_replace": {"title": grouped["c_replace"]["title"], "count": len(grouped["c_items"]), "summary": grouped["c_replace"].get("summary_text", ""), "c_sell_count": grouped["c_replace"].get("c_sell_count", 0), "items": grouped["c_items"]},
        "core_trades": {"title": grouped["core_trades"]["title"], "count": len(grouped["core_items"]), "summary": grouped["core_trades"].get("summary_text", ""), "items": grouped["core_items"]},
        "buffer_hold": {"title": grouped["buffer_hold"]["title"], "count": len(grouped["hold_items"]), "summary": grouped["buffer_hold"].get("summary_text", ""), "items": grouped["hold_items"]},
        "quota_split_plans": quota_split_plans,
        "cheat_sheet_lines": cheat_lines,
        "cheat_sheet_text": "\n".join(cheat_lines) if cheat_lines else "今日无需买卖操作。",
    }
    return _sanitize_v1_payload(payload)


@app.post("/api/v1/rebalance/execute")
def api_v1_rebalance_execute(req: RebalanceExecuteRequest) -> Dict[str, Any]:
    with _LEDGER_WRITE_LOCK:
        mlm, lid, pm, snap = _get_active_context(req.ledger_id)
        if req.confirm_backup:
            try:
                LedgerBackupVault.create_snapshot(reason=f"rebalance_execute_{lid}")
            except Exception as exc:
                logger.warning("rebalance/execute 备份快照跳过 (%s): %s", lid, exc)
        tw = _target_weights_for_ledger(lid, snap)
        res = StrategyBridge.generate_ai_rebalance_orders(
            pm.holdings,
            pm.available_cash,
            tw,
            pm=pm,
            mode=req.mode or "gentle",
            min_buffer_pct=3.0,
            c_replace="011613" if lid == "combat_29_funds" else None,
            core_anchor_code="002351",
        )
        items = res.get("items", []) if isinstance(res, dict) else []
        return _sanitize_v1_payload({
            "status": "ready",
            "ledger_id": lid,
            "mode": req.mode or "gentle",
            "order_count": len(items),
            "items": items,
            "summary": res.get("summary", ""),
        })


@app.post("/api/v1/cashflow/plan")
def api_v1_cashflow_plan(req: CashflowPlanRequest) -> Dict[str, Any]:
    _, lid, pm, snap = _get_active_context(req.ledger_id)
    tw = _target_weights_for_ledger(lid, snap)
    holdings = getattr(pm, "holdings", {}) or {}
    codes = list(holdings.keys())
    quotes_map = prefetch_batch_fund_quotes(codes) if codes else {}
    investable = cashflow_planner.enforce_liquidity_redline(pm.available_cash, req.get_reserve())
    dca = cashflow_planner.plan_incremental_investment(
        current_holdings=holdings,
        target_weights=tw,
        monthly_new_cash=req.get_monthly_cash(),
        plan_months=req.plan_months,
        available_cash=investable,
        quotes_or_nav_map=quotes_map,
    )
    inv_cash = float(investable.get("investable_cash", 0.0)) if isinstance(investable, dict) else float(investable or 0.0)
    bullets = cashflow_planner.generate_left_side_bullet_plan(
        investable_spare_cash=inv_cash + float(req.get_monthly_cash()) * int(req.plan_months),
        current_index_point=_safe_index_point(snap),
    )
    return _sanitize_v1_payload({"ledger_id": lid, "liquidity_guard": investable, "dca_plan": dca, "left_side_bullets": bullets})


@app.get("/api/v1/audit/trackers")
def api_v1_audit_trackers(ledger_id: Optional[str] = None) -> Dict[str, Any]:
    _, lid, pm, _ = _get_active_context(ledger_id)
    holdings = getattr(pm, "holdings", {}) or {}
    baseline = shadow_portfolio_tracker.get_shadow_baseline(lid) or {}
    shadow_codes = list((baseline.get("holdings") or {}).keys())
    all_codes = list(dict.fromkeys(list(holdings.keys()) + shadow_codes))
    quotes_map = prefetch_batch_fund_quotes(all_codes) if all_codes else {}
    nav_map: Dict[str, float] = {}
    for c in all_codes:
        q = quotes_map.get(c)
        q_nav = float(getattr(q, "official_nav", 0.0) or getattr(q, "gsz", 0.0) or getattr(q, "dwjz", 0.0) or 0.0) if q else 0.0
        if q_nav > 0.0:
            nav_map[c] = q_nav
        elif c in holdings:
            h = holdings[c]
            h_nav = float(getattr(h, "current_nav", 0.0) or getattr(h, "latest_nav", 0.0) or getattr(h, "cost_price", 0.0) or 0.0)
            if h_nav > 0.0:
                nav_map[c] = h_nav
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


@app.post("/api/v1/shadow/freeze")
def api_v1_shadow_freeze(req: ShadowFreezeRequest) -> Dict[str, Any]:
    with _LEDGER_WRITE_LOCK:
        _, lid, pm, _ = _get_active_context(req.ledger_id)
        holdings = getattr(pm, "holdings", {}) or {}
        if not holdings:
            raise HTTPException(status_code=400, detail=f"账本持仓为空，无法冻结躺平影子基准: {lid}")
        b_name = req.baseline_name or f"{lid} 原始躺平基准线"
        spec_path = shadow_portfolio_tracker.freeze_shadow_baseline(lid, holdings, baseline_name=b_name)
        baseline = shadow_portfolio_tracker.get_shadow_baseline(lid) or {}
        return _sanitize_v1_payload({
            "frozen": True,
            "ledger_id": lid,
            "baseline_name": baseline.get("baseline_name", b_name),
            "frozen_date": baseline.get("frozen_date", ""),
            "frozen_timestamp": baseline.get("frozen_timestamp", ""),
            "holdings_count": int(baseline.get("holdings_count", len(holdings))),
            "initial_total_market_value": float(baseline.get("initial_total_market_value", 0.0)),
            "baseline_path": str(spec_path),
        })


@app.get("/api/v1/backups")
def api_v1_list_backups() -> Dict[str, Any]:
    snaps = LedgerBackupVault.list_snapshots()
    return _sanitize_v1_payload({"count": len(snaps), "snapshots": snaps})


@app.post("/api/v1/backups/restore")
def api_v1_restore_backup(req: RestoreBackupRequest) -> Dict[str, Any]:
    with _LEDGER_WRITE_LOCK:
        ok = LedgerBackupVault.restore_snapshot(req.snapshot_id)
        if not ok:
            raise HTTPException(status_code=400, detail=f"快照恢复失败: {req.snapshot_id}")
        return _sanitize_v1_payload({"restored": True, "snapshot_id": req.snapshot_id})


@app.post("/api/v1/import/text")
def api_v1_import_text(req: ImportTextRequest) -> Dict[str, Any]:
    if not str(req.text or "").strip():
        raise HTTPException(status_code=400, detail="导入文本不能为空")
    with _LEDGER_WRITE_LOCK:
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


async def _extract_ocr_request_inputs(request: Request):
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
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"无效的 JSON 请求体: {exc}")
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
    return ledger_id, mode, image_bytes


@app.post("/api/v1/import/ocr")
def api_v1_import_ocr(request: Request) -> Dict[str, Any]:
    ledger_id, mode, image_bytes = anyio.from_thread.run(_extract_ocr_request_inputs, request)
    if not image_bytes:
        raise HTTPException(status_code=400, detail="未上传有效的截图文件")

    with _LEDGER_WRITE_LOCK:
        _, lid, pm, _ = _get_active_context(ledger_id)
        try:
            parsed = pm.parse_screenshot_ocr_holdings(image_bytes)
        except Exception as exc:
            logger.exception("OCR 截图解析失败 (%s): %s", lid, exc)
            raise HTTPException(status_code=422, detail=f"截图 OCR 解析异常: {exc}")

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


class HoldingsReconcileRequest(BaseModel):
    ledger_id: Optional[str] = None
    updates: Any = []
    dry_run: bool = True


@app.post("/api/v1/holdings/reconcile")
def api_v1_holdings_reconcile(req: HoldingsReconcileRequest) -> Dict[str, Any]:
    with _LEDGER_WRITE_LOCK:
        _, lid, pm, _ = _get_active_context(req.ledger_id)
        raw_updates = req.updates
        norm_updates: Dict[str, Dict[str, Any]] = {}
        if isinstance(raw_updates, list):
            for item in raw_updates:
                if isinstance(item, dict):
                    c = str(item.get("fund_code") or item.get("code") or "").strip().zfill(6)
                    if c:
                        norm_updates[c] = item
        elif isinstance(raw_updates, dict):
            for k, v in raw_updates.items():
                c = str(k).strip().zfill(6)
                if isinstance(v, dict):
                    norm_updates[c] = v
                elif isinstance(v, (int, float)):
                    norm_updates[c] = {"shares": float(v)}

        diff_res = execution_tracker.reconcile_incremental_holdings_diff(getattr(pm, "holdings", {}), norm_updates)

        applied = False
        if not req.dry_run and diff_res.get("modified_count", 0) > 0:
            LedgerBackupVault.create_snapshot(reason=f"api_reconcile_{lid}")
            for code, upd in norm_updates.items():
                curr = pm.holdings.get(code)
                if curr:
                    if "shares" in upd:
                        curr.shares = float(upd["shares"])
                    if "cost_price" in upd:
                        curr.cost_price = float(upd["cost_price"])
                else:
                    pm.holdings[code] = HoldingItem(
                        fund_code=code,
                        fund_name=upd.get("fund_name", code),
                        shares=float(upd.get("shares", 0.0)),
                        cost_price=float(upd.get("cost_price", 1.0)),
                        current_nav=float(upd.get("current_nav", upd.get("cost_price", 1.0))),
                    )
            pm.save_state()
            applied = True

        return _sanitize_v1_payload({
            "ledger_id": lid,
            "dry_run": req.dry_run,
            "applied": applied,
            "total_checked": diff_res.get("total_checked", 0),
            "modified_count": diff_res.get("modified_count", 0),
            "diff_items": diff_res.get("diff_items", []),
        })


@app.get("/api/v1/ledger/export")
def api_v1_ledger_export(ledger_id: Optional[str] = None) -> Dict[str, Any]:
    from dataclasses import asdict
    _, lid, pm, _ = _get_active_context(ledger_id)
    holdings_dict = {}
    for code, h in getattr(pm, "holdings", {}).items():
        sh = float(getattr(h, "shares", 0.0))
        nav = float(getattr(h, "current_nav", 1.0))
        cost = float(getattr(h, "cost_price", 1.0))
        holdings_dict[code] = {
            "fund_code": code,
            "fund_name": str(getattr(h, "fund_name", code)),
            "shares": sh,
            "cost_price": cost,
            "current_nav": nav,
            "market_value": round(sh * nav, 2),
            "share_class": str(getattr(h, "share_class", "A")),
        }
    pending = [
        o if isinstance(o, dict) else (asdict(o) if hasattr(o, "__dataclass_fields__") else getattr(o, "__dict__", str(o)))
        for o in getattr(pm, "pending_orders", [])
    ]
    checkins = load_daily_checkin()
    return _sanitize_v1_payload({
        "ledger_id": lid,
        "total_equity": round(float(getattr(pm, "total_equity", 0.0)), 2),
        "available_cash": round(float(getattr(pm, "available_cash", 0.0)), 2),
        "holdings": holdings_dict,
        "pending_orders": pending,
        "checkins": checkins,
    })


@app.post("/api/v1/ledger/import")
def api_v1_ledger_import(req: LedgerImportRequest) -> Dict[str, Any]:
    with _LEDGER_WRITE_LOCK:
        mlm, lid, pm, _ = _get_active_context(req.ledger_id)
        try:
            LedgerBackupVault.create_snapshot(reason=f"cross_device_sync_{lid}")
        except Exception as exc:
            logger.warning("ledger/import 备份快照失败 (%s): %s", lid, exc)

        h_items = req.holdings
        if isinstance(h_items, dict):
            h_items = list(h_items.values())
        elif not isinstance(h_items, list):
            h_items = []

        if req.replace_existing:
            pm.holdings.clear()

        for item in h_items:
            if not isinstance(item, dict):
                continue
            code = str(item.get("fund_code") or item.get("code") or "").strip()
            if not code:
                continue
            name = str(item.get("fund_name") or item.get("name") or code)
            shares = float(item.get("shares") or item.get("vol") or 0.0)
            nav = float(item.get("current_nav") or item.get("nav") or item.get("cost_price") or 1.0)
            cost = float(item.get("cost_price") or item.get("cost") or nav)
            s_class = str(item.get("share_class") or "A")
            holding = HoldingItem(
                fund_code=code,
                fund_name=name,
                shares=shares,
                cost_price=cost,
                current_nav=nav,
                share_class=s_class,
            )
            pm.holdings[code] = holding

        if req.available_cash is not None:
            pm.available_cash = float(req.available_cash)

        if hasattr(pm, "save_state"):
            try:
                pm.save_state(record_snapshot=True)
            except Exception as exc:
                logger.exception("ledger/import 落盘失败 (%s): %s", lid, exc)
                raise HTTPException(status_code=500, detail=f"账本落盘失败: {exc}")

        return _sanitize_v1_payload({
            "status": "ok",
            "ledger_id": lid,
            "holdings_count": len(pm.holdings),
        })


class CheckinItemRequest(BaseModel):
    fund_code: str
    action: str = "BUY"
    amount: float = 0.0
    checked: bool = True
    date_str: str = ""


@app.get("/api/v1/holdings/movers")
def api_v1_holdings_movers(ledger_id: Optional[str] = None) -> Dict[str, Any]:
    _, lid, pm, _ = _get_active_context(ledger_id)
    holdings = getattr(pm, "holdings", {}) or {}
    quotes = prefetch_batch_fund_quotes(list(holdings.keys()))

    items = []
    for code, h in holdings.items():
        q = quotes.get(code)
        chg = float(getattr(q, "gszzl", 0.0) or getattr(q, "official_chg_pct", 0.0) or 0.0) if q else 0.0
        sh = float(getattr(h, "shares", 0.0))
        nav = float(getattr(q, "official_nav", 0.0) or getattr(q, "gsz", 0.0) or getattr(h, "current_nav", 1.0) or 1.0)
        mv = round(sh * nav, 2)
        items.append({
            "fund_code": code,
            "fund_name": str(getattr(h, "fund_name", code)),
            "change_pct": round(chg, 2),
            "market_value": mv,
        })

    gainers = sorted([x for x in items if x["change_pct"] > 0], key=lambda x: x["change_pct"], reverse=True)[:3]
    losers = sorted([x for x in items if x["change_pct"] < 0], key=lambda x: x["change_pct"])[:3]

    return _sanitize_v1_payload({
        "ledger_id": lid,
        "has_data": len(items) > 0,
        "top_gainers": gainers,
        "top_losers": losers,
        "total_holdings_count": len(items),
    })


@app.get("/api/v1/rebalance/checkin")
def api_v1_get_checkin(date_str: Optional[str] = None) -> Dict[str, Any]:
    data = load_daily_checkin(date_str)
    return _sanitize_v1_payload(data)


@app.post("/api/v1/rebalance/checkin")
def api_v1_post_checkin(req: CheckinItemRequest) -> Dict[str, Any]:
    with _LEDGER_WRITE_LOCK:
        res = save_daily_checkin(
            fund_code=req.fund_code,
            action=req.action,
            amount=req.amount,
            checked=req.checked,
            date_str=req.date_str or "",
        )
        return _sanitize_v1_payload(res)


@app.get("/api/v1/alerts/push")
def api_v1_alerts_push(ledger_id: Optional[str] = None) -> Dict[str, Any]:
    _, lid, pm, snapshot = _get_active_context(ledger_id)
    holdings = getattr(pm, "holdings", {}) or {}

    alerts = []
    try:
        sentry = ActiveRiskSentry()
        s_rep = sentry.inspect_portfolio(holdings=holdings, snapshot=snapshot)
        for a in (s_rep.get("alerts") or []):
            alerts.append({
                "id": f"risk_{a.get('fund_code', 'port')}_{a.get('dimension', 'gen')}",
                "level": a.get("level", "yellow"),
                "title": a.get("title") or a.get("message", "风控提示"),
                "detail": a.get("action") or a.get("detail", ""),
                "fund_code": a.get("fund_code"),
                "created_at": datetime.now().isoformat(),
            })
    except Exception as exc:
        logger.warning("alerts/push 风控哨巡检异常 (%s): %s", lid, exc)

    return _sanitize_v1_payload({
        "ledger_id": lid,
        "unread_count": len(alerts),
        "alerts": alerts,
    })


@app.get("/api/v1/review/{subview}")
def api_v1_review_subview(subview: str, ledger_id: Optional[str] = None) -> Dict[str, Any]:
    _, lid, pm, snapshot = _get_active_context(ledger_id)
    subview = subview.lower().strip()

    if subview == "timemachine":
        return _sanitize_v1_payload({
            "subview": "timemachine",
            "ledger_id": lid,
            "status": "ready",
            "available_benchmarks": ["000300.SH", "000905.SH", "000852.SH", "H30269.CSI"],
            "description": "历史时光机区间回测，支持 9 大基准自由对比与动态仓位穿透。",
        })
    elif subview == "rolling_winrate":
        return _sanitize_v1_payload({
            "subview": "rolling_winrate",
            "ledger_id": lid,
            "status": "ready",
            "windows": ["1Y", "2Y", "3Y"],
            "target_winrate": 0.82,
            "description": "近三年滚动任意买入点持有满 1 年胜率统计分析。",
        })
    elif subview == "forward_audit":
        audit_res = forward_audit_logger.evaluate_forward_performance() if hasattr(forward_audit_logger, "evaluate_forward_performance") else {}
        return _sanitize_v1_payload({
            "subview": "forward_audit",
            "ledger_id": lid,
            "audit_result": audit_res,
        })
    elif subview == "shadow_race":
        baseline = shadow_portfolio_tracker.get_shadow_baseline(lid) or {}
        holdings = getattr(pm, "holdings", {}) or {}
        shadow_codes = list((baseline.get("holdings") or {}).keys())
        all_codes = list(dict.fromkeys(list(holdings.keys()) + shadow_codes))
        quotes_map = prefetch_batch_fund_quotes(all_codes) if all_codes else {}
        nav_map = {
            c: float(getattr(quotes_map.get(c), "official_nav", 0.0) or getattr(quotes_map.get(c), "gsz", 0.0) or 1.0)
            for c in all_codes
        }
        comp = shadow_portfolio_tracker.compare_live_vs_shadow(lid, holdings, nav_map)
        return _sanitize_v1_payload({
            "subview": "shadow_race",
            "ledger_id": lid,
            "comparison": comp,
        })
    else:
        raise HTTPException(status_code=400, detail=f"未知的复盘子视图: {subview}")


@app.get("/api/v1/diagnose/{subview}")
def api_v1_diagnose_subview(subview: str, ledger_id: Optional[str] = None) -> Dict[str, Any]:
    _, lid, pm, snapshot = _get_active_context(ledger_id)
    subview = subview.lower().strip()
    holdings = getattr(pm, "holdings", {}) or {}

    if subview == "risk_check":
        s_rep = ActiveRiskSentry().inspect_portfolio(holdings=holdings, snapshot=snapshot)
        return _sanitize_v1_payload({
            "subview": "risk_check",
            "ledger_id": lid,
            "active_sentry": s_rep,
        })

    if subview == "exposure":
        if not holdings:
            cash_val = round(float(getattr(pm, "available_cash", 0.0) or 0.0), 2)
            return _sanitize_v1_payload({
                "subview": "exposure",
                "ledger_id": lid,
                "status": "empty",
                "holdings_count": 0,
                "total_equity": cash_val,
                "asset_classes": {"可用现金": 1.0} if cash_val > 0 else {},
                "top_industries": {},
            })
        cur_cats: Dict[str, float] = {}
        total_mv = 0.0
        for code, h in holdings.items():
            mv = float(getattr(h, "market_value", 0.0) or (float(getattr(h, "shares", 0.0) or 0.0) * float(getattr(h, "current_nav", 1.0) or 1.0)))
            cat = pm.classify_fund_asset_class(code, getattr(h, "fund_name", code))
            cur_cats[cat] = cur_cats.get(cat, 0.0) + mv
            total_mv += mv
        cash_val = float(getattr(pm, "available_cash", 0.0) or 0.0)
        if cash_val > 0:
            cur_cats["可用现金"] = cur_cats.get("可用现金", 0.0) + cash_val
            total_mv += cash_val
        asset_classes = {
            k: round(v / total_mv, 4) if total_mv > 1e-6 else 0.0
            for k, v in sorted(cur_cats.items(), key=lambda x: x[1], reverse=True)
        }
        top_industries: Dict[str, float] = {}
        df_ind = pm.calculate_look_through_industry_exposure(holdings_override=holdings)
        if df_ind is not None and not df_ind.empty:
            for _, row in df_ind.head(10).iterrows():
                ind_name = str(row.get("行业", "")).strip()
                ind_pct = float(row.get("暴露占比(%)", 0.0) or 0.0)
                if ind_name:
                    top_industries[ind_name] = round(ind_pct / 100.0, 4)
        return _sanitize_v1_payload({
            "subview": "exposure",
            "ledger_id": lid,
            "status": "ready",
            "holdings_count": len(holdings),
            "total_equity": round(total_mv, 2),
            "asset_classes": asset_classes,
            "top_industries": top_industries,
        })

    if subview == "overlap":
        if not holdings:
            return _sanitize_v1_payload({
                "subview": "overlap",
                "ledger_id": lid,
                "status": "empty",
                "holdings_count": 0,
                "max_total_overlap": 0.0,
                "max_non_diag_unexcused": 0.0,
                "alerts": [],
                "common_stocks_details": [],
            })
        overlap_res = pm.calculate_stock_overlap_matrix(holdings_override=holdings) or {}
        return _sanitize_v1_payload({
            "subview": "overlap",
            "ledger_id": lid,
            "status": "ready",
            "holdings_count": len(holdings),
            "max_total_overlap": round(float(overlap_res.get("max_total_overlap", 0.0) or 0.0), 4),
            "max_non_diag_unexcused": round(float(overlap_res.get("max_non_diag_unexcused", 0.0) or 0.0), 4),
            "exempt_pairs": overlap_res.get("exempt_pairs") or [],
            "alerts": overlap_res.get("alerts") or [],
            "common_stocks_details": (overlap_res.get("common_stocks_details") or [])[:20],
        })

    if subview == "stress_test":
        if not holdings:
            return _sanitize_v1_payload({
                "subview": "stress_test",
                "ledger_id": lid,
                "status": "empty",
                "holdings_count": 0,
                "penetration_risk": {},
                "cvar_bootstrap": {},
                "stress_model": {},
            })
        penetration = pm.calculate_portfolio_penetration_risk(holdings_override=holdings) or {}
        cvar_raw = pm.simulate_portfolio_cvar_bootstrap_instance(total_capital=pm.get_total_asset_value()) or {}
        cvar_compact = {k: v for k, v in cvar_raw.items() if k != "monte_carlo_3d_data"}
        cushion_raw = pm.calculate_portfolio_cushion_and_stress_model(current_index_point=_safe_index_point(snapshot)) or {}
        cushion_compact = {k: v for k, v in cushion_raw.items() if k != "holding_betas"}
        return _sanitize_v1_payload({
            "subview": "stress_test",
            "ledger_id": lid,
            "status": "ready",
            "holdings_count": len(holdings),
            "penetration_risk": {
                "portfolio_risk_index": penetration.get("portfolio_risk_index"),
                "risk_level": penetration.get("risk_level"),
                "risk_badge": penetration.get("risk_badge"),
                "danger_stock_count": penetration.get("danger_stock_count", 0),
                "watch_stock_count": penetration.get("watch_stock_count", 0),
            },
            "cvar_bootstrap": cvar_compact,
            "stress_model": cushion_compact,
        })

    if subview == "ten_dim_votes":
        vote_res = compute_ten_dimension_votes(snapshot=snapshot) or {}
        votes = vote_res.get("votes") or vote_res.get("dimensions") or []
        return _sanitize_v1_payload({
            "subview": "ten_dim_votes",
            "ledger_id": lid,
            "overall_regime": snapshot.get("regime", "NEUTRAL"),
            "market_state_code": snapshot.get("market_state_code", "NEUTRAL"),
            "as_of": str(snapshot.get("date") or snapshot.get("as_of_date") or ""),
            "dimensions_count": len(votes) if isinstance(votes, list) else 10,
            "vote_summary": {k: v for k, v in vote_res.items() if k not in ("votes", "dimensions")},
            "votes": votes,
        })

    raise HTTPException(status_code=400, detail=f"未知的诊断子视图: {subview}")


@app.get("/api/v1/backtest/summary")
def api_v1_backtest_summary(ledger_id: Optional[str] = None) -> Dict[str, Any]:
    _, lid, _, _ = _get_active_context(ledger_id)
    trial29 = StrategyBridge.load_trial29_metrics() or {}
    oos_eval = forward_audit_logger.evaluate_forward_performance() or {}
    return _sanitize_v1_payload({
        "ledger_id": lid,
        "source": "evolution_db_trial29_and_forward_audit",
        "trial_id": trial29.get("trial_id", 29),
        "strategy_name": trial29.get("strategy_name", ""),
        "created_at": trial29.get("created_at", ""),
        "annualized_return_pct": trial29.get("cagr_full", trial29.get("cagr_pct")),
        "live_calibrated_cagr_pct": trial29.get("cagr_full_otc"),
        "holdout_cagr_pct": trial29.get("cagr_holdout"),
        "max_drawdown_pct": trial29.get("overall_mdd"),
        "sharpe_ratio": trial29.get("overall_sharpe"),
        "holdout_sharpe_ratio": trial29.get("holdout_sharpe"),
        "win_rate_pct": trial29.get("slice_win_rate"),
        "monthly_win_rate_pct": trial29.get("monthly_win_rate"),
        "survival_rate_pct": trial29.get("survival_rate"),
        "oos_sample_count": oos_eval.get("sample_count", 0),
        "oos_excess_alpha_pct": oos_eval.get("excess_alpha_pct"),
        "oos_win_rate_pct": oos_eval.get("win_rate_pct"),
    })


_SECTORS_QUOTE_CACHE: Dict[str, Any] = {"ts": 0.0, "key": "", "data": []}
_SECTORS_CACHE_LOCK = threading.Lock()
_SECTORS_CACHE_TTL_SEC = 30.0


def _fetch_sectors_with_quotes_cached(items: List[Dict[str, Any]], force_refresh: bool = False) -> List[Dict[str, Any]]:
    now = time.time()
    cache_key = ",".join(f"{it.get('code', '')}:{it.get('name', '')}" for it in items)
    with _SECTORS_CACHE_LOCK:
        if (
            not force_refresh
            and _SECTORS_QUOTE_CACHE["key"] == cache_key
            and (now - float(_SECTORS_QUOTE_CACHE["ts"])) < _SECTORS_CACHE_TTL_SEC
            and _SECTORS_QUOTE_CACHE["data"]
        ):
            return list(_SECTORS_QUOTE_CACHE["data"])

    if not items:
        with _SECTORS_CACHE_LOCK:
            _SECTORS_QUOTE_CACHE["ts"] = now
            _SECTORS_QUOTE_CACHE["key"] = ""
            _SECTORS_QUOTE_CACHE["data"] = []
        return []

    def _one(it: Dict[str, Any]) -> Dict[str, Any]:
        try:
            chg = float(sector_watchlist.fetch_sector_change_pct(it) or 0.0)
        except Exception:
            chg = 0.0
        return {
            "code": it.get("code", ""),
            "name": it.get("name", ""),
            "asset_type": it.get("asset_type", "ETF"),
            "change_pct": round(chg, 2),
        }

    workers = min(6, max(1, len(items)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        out = list(pool.map(_one, items))

    with _SECTORS_CACHE_LOCK:
        _SECTORS_QUOTE_CACHE["ts"] = time.time()
        _SECTORS_QUOTE_CACHE["key"] = cache_key
        _SECTORS_QUOTE_CACHE["data"] = out
    return out


@app.get("/api/v1/watchlist")
def api_v1_get_watchlist() -> Dict[str, Any]:
    out = _fetch_sectors_with_quotes_cached(sector_watchlist.load_sector_watchlist(), force_refresh=False)
    return _sanitize_v1_payload({"count": len(out), "items": out})


@app.post("/api/v1/watchlist")
def api_v1_update_watchlist(req: WatchlistUpdateRequest) -> Dict[str, Any]:
    with _LEDGER_WRITE_LOCK:
        act = req.action.lower()
        if act == "add" and req.code:
            items = sector_watchlist.add_sector_item(req.code, req.name or "")
        elif act == "remove" and req.code:
            items = sector_watchlist.remove_sector_item(req.code)
        elif act == "reset":
            items = sector_watchlist.reset_sector_watchlist()
        else:
            items = sector_watchlist.load_sector_watchlist()
        out = _fetch_sectors_with_quotes_cached(items, force_refresh=True)
        return _sanitize_v1_payload({"status": "ok", "count": len(out), "items": out})


@app.delete("/api/v1/watchlist/{code}")
def api_v1_delete_watchlist_item(code: str) -> Dict[str, Any]:
    with _LEDGER_WRITE_LOCK:
        out = _fetch_sectors_with_quotes_cached(sector_watchlist.remove_sector_item(code), force_refresh=True)
        return _sanitize_v1_payload({"status": "ok", "count": len(out), "items": out})


@app.get("/api/v1/sectors", deprecated=True)
def api_v1_get_sectors() -> List[Dict[str, Any]]:
    return api_v1_get_watchlist()["items"]


@app.post("/api/v1/sectors", deprecated=True)
def api_v1_add_sector(req: SectorItemRequest) -> List[Dict[str, Any]]:
    return api_v1_update_watchlist(WatchlistUpdateRequest(action="add", code=req.code, name=req.name or ""))["items"]


@app.delete("/api/v1/sectors/{code}", deprecated=True)
def api_v1_remove_sector(code: str) -> List[Dict[str, Any]]:
    return api_v1_delete_watchlist_item(code)["items"]


@app.get("/api/v1/funds/search")
def api_v1_funds_search(q: str = "", limit: int = 8) -> Dict[str, Any]:
    clean_q = str(q or "").strip()
    clean_lim = max(1, min(int(limit), 20))
    if not clean_q:
        return _sanitize_v1_payload({"query": "", "count": 0, "items": []})
    try:
        from data_loader import search_index_and_fund_candidates
        results = search_index_and_fund_candidates(clean_q, clean_lim)
    except Exception as exc:
        logger.warning("funds/search 检索异常 (q=%s): %s", clean_q, exc)
        results = []
    items = []
    for it in results:
        items.append({
            "code": str(it.get("code", "")),
            "name": str(it.get("name", "")),
            "asset_type": str(it.get("asset_type", "fund")),
            "sector": str(it.get("sector", "")),
        })
    return _sanitize_v1_payload({"query": clean_q, "count": len(items), "items": items})


def export_openapi_contract(output_path: Optional[Path] = None) -> Path:
    import json
    schema = app.openapi()
    targets = []
    if output_path:
        targets.append(output_path)
    else:
        ws_root = runtime_paths.get_workspace_root()
        bundle_root = runtime_paths.get_bundle_root()
        targets.append(ws_root / "docs" / "openapi_v1.json")
        agy_doc = bundle_root / "docs" / "openapi_v1.json"
        if agy_doc not in targets:
            targets.append(agy_doc)

    for target in targets:
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            json.dump(schema, f, ensure_ascii=False, indent=2)
    return targets[0]


def main() -> None:
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser(description="AGY2 Local Advisory REST API Server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--export-openapi", action="store_true")
    args = parser.parse_args()

    if args.export_openapi:
        out_p = export_openapi_contract()
        print(f"Exported OpenAPI contract to: {out_p}")
    else:
        uvicorn.run(app, host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()
