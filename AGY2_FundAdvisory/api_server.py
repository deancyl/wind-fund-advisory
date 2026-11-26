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
from typing import Dict, Any, List, Optional, Tuple
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


app = FastAPI(title="AGY2-FundAdvisory Local Quant API", version="2.0.3", lifespan=_lifespan)
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
_BACKTEST_CURVES_CACHE: Dict[str, Any] = {}
_BACKTEST_CURVES_LOCK = threading.Lock()


def _invalidate_overview_cache(lid: Optional[str] = None) -> None:
    with _OVERVIEW_CACHE_LOCK:
        if lid:
            _OVERVIEW_CACHE.pop(lid, None)
        else:
            _OVERVIEW_CACHE.clear()


def _detect_c_replace_code(lid: str, holdings: Dict[str, Any]) -> Optional[str]:
    """动态识别当前账本中满 30 天且可零费率 C 转 A 的标的，消除 combat_29_funds 硬编码。"""
    if lid == "combat_29_funds":
        return "011613"
    h = (holdings or {}).get("011613")
    if h is not None:
        days = int(getattr(h, "holding_days", 0) or 0)
        mv = float(getattr(h, "market_value", 0.0) or 0.0)
        if days >= 30 and mv >= 200.0:
            return "011613"
    return None

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
            "asset_class": pm.classify_fund_asset_class(code, getattr(h, "fund_name", code)),
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
def api_v1_rebalance(
    ledger_id: Optional[str] = None,
    min_buffer_pct: float = 3.0,
    target_return_pct: float = 10.0,
    horizon_months: int = 12,
    tier: str = "C3",
    target_source: str = "ledger_smooth",
    model: str = "all_weather",
    fund_count: int = 6,
    universe_mode: str = "full_market",
) -> Dict[str, Any]:
    _, lid, pm, snap = _get_active_context(ledger_id)
    clean_tier = str(tier or "C3").upper().strip()
    if clean_tier not in _RISK_TIER_META:
        clean_tier = "C3"
    clean_source = str(target_source or "ledger_smooth").strip().lower()
    if clean_source not in ("ledger_smooth", "full_market_solved"):
        clean_source = "ledger_smooth"
    clean_model = str(model or "all_weather").strip().lower()
    if clean_model not in _QUANT_MODELS_META:
        clean_model = "all_weather"
    u_mode = str(universe_mode or "full_market").strip().lower()
    if u_mode not in ("full_market", "index_only"):
        u_mode = "full_market"
    n_funds = max(3, min(8, int(fund_count or 6)))

    solved_for_reb: Optional[Dict[str, Any]] = None
    cards_meta_reb: Dict[str, Dict[str, Any]] = {}
    if clean_source == "full_market_solved":
        from goal_driven_selector import solve_goal_driven_portfolio
        solved_for_reb = solve_goal_driven_portfolio(
            risk_level=clean_tier,
            fund_count=n_funds,
            model_id=clean_model,
            target_return_pct=float(target_return_pct),
            horizon_months=int(horizon_months),
            universe_mode=u_mode,
            market_snapshot=snap,
            force_recompute=False,
        )
        tw = dict(solved_for_reb["final_weights"])
        cards_meta_reb = dict(solved_for_reb.get("fund_cards_meta") or {})
        u_lbl = "全市场量化海选" if u_mode == "full_market" else "仅指数低费池"
        target_summary = f"已对齐首页全市场方案：{_QUANT_MODELS_META[clean_model]['name']} · {clean_tier} · {u_lbl} · {n_funds}只"
    else:
        tw = _target_weights_for_ledger(lid, snap)
        target_summary = "稳健低换手模式：优先平滑优化存量持仓、保护现有核心底仓"

    res = StrategyBridge.generate_ai_rebalance_orders(
        pm.holdings,
        pm.available_cash,
        tw,
        pm=pm,
        mode="gentle",
        min_buffer_pct=min_buffer_pct,
        c_replace=_detect_c_replace_code(lid, pm.holdings),
        core_anchor_code="002351",
    )
    items = res.get("items", [])
    # 全市场目标模式下补全湖仓新基金中文名称，避免退化为纯代码
    if cards_meta_reb:
        for it in items:
            c_key = str(it.get("fund_code") or it.get("code") or "").strip().zfill(6)
            cm = cards_meta_reb.get(c_key)
            if cm and cm.get("fund_name"):
                cur_n = str(it.get("fund_name") or it.get("name") or "").strip()
                if (not cur_n) or cur_n == c_key or cur_n.startswith("公募基金_"):
                    it["fund_name"] = cm["fund_name"]
                    if "name" in it:
                        it["name"] = cm["fund_name"]
    grouped = group_rebalance_orders_by_intent(items)

    quota_split_plans = []
    for it in (grouped["c_items"] + grouped["core_items"]):
        amt = float(it.get("diff_amount") or it.get("amount") or 0.0)
        if amt <= 0:
            continue
        code = str(it.get("fund_code", "") or it.get("code", "")).strip()
        cm = cards_meta_reb.get(code, {})
        name = str(it.get("fund_name", "") or it.get("name", "") or cm.get("fund_name") or code)
        meta = CORE_STRATEGY_POOL.get(code, {})
        d_lim = float(cm.get("daily_limit") or meta.get("daily_limit", 1e8))
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

    # 目标收益 × 目标周期：对比「调仓前当前持仓」vs「调仓后目标组合」的历史达成概率（动态使用用户真实档位）
    goal_comparison: Optional[Dict[str, Any]] = None
    try:
        from goal_driven_selector import evaluate_goal_achievement
        tot_mv = sum(float(getattr(h, "market_value", 0.0) or 0.0) for h in (pm.holdings or {}).values())
        cur_w = {
            c: round(float(getattr(h, "market_value", 0.0) or 0.0) / tot_mv, 4)
            for c, h in (pm.holdings or {}).items()
            if float(getattr(h, "market_value", 0.0) or 0.0) > 1e-4
        } if tot_mv > 1e-4 else {}
        if cur_w and tw:
            after_bt_override = solved_for_reb.get("real_bt_df") if solved_for_reb else None
            with ThreadPoolExecutor(max_workers=2) as gpool:
                f_before = gpool.submit(evaluate_goal_achievement, cur_w, target_return_pct, horizon_months, clean_tier, snap)
                f_after = gpool.submit(evaluate_goal_achievement, tw, target_return_pct, horizon_months, clean_tier, snap, after_bt_override)
                before_eval = f_before.result(timeout=10.0)
                after_eval = f_after.result(timeout=10.0)
            goal_comparison = {
                "target_return_pct": round(float(target_return_pct), 1),
                "horizon_months": int(horizon_months),
                "tier": clean_tier,
                "before": before_eval,
                "after": after_eval,
                "hit_rate_delta_pct": round(after_eval["historical_hit_rate_pct"] - before_eval["historical_hit_rate_pct"], 1),
                "worst_return_delta_pct": round(after_eval["p05_worst_return_pct"] - before_eval["p05_worst_return_pct"], 2),
            }
    except Exception:
        goal_comparison = None

    payload = {
        "ledger_id": lid,
        "tier": clean_tier,
        "target_source": clean_source,
        "target_summary": target_summary,
        "plan_mode": "对齐首页全市场方案" if clean_source == "full_market_solved" else ("存量瘦身重构" if lid == "combat_29_funds" else "动态股债平衡"),
        "is_empty": grouped["is_empty"],
        "goal_comparison": goal_comparison,
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
    # 标准化 dca_plan.allocations 字段，同时保留原中文字段兼容旧调用方
    if isinstance(dca, dict) and isinstance(dca.get("allocations"), list):
        norm_allocs = []
        for it in dca["allocations"]:
            if not isinstance(it, dict):
                continue
            code = str(it.get("fund_code") or it.get("基金代码") or "").strip().zfill(6)
            h_obj = holdings.get(code)
            fname = str(
                it.get("fund_name")
                or it.get("基金名称")
                or (getattr(h_obj, "fund_name", "") if h_obj else "")
                or (CORE_STRATEGY_POOL.get(code) or {}).get("fund_name", "")
                or code
            )
            m_amt = float(it.get("monthly_amount") or it.get("每月定投金额(元)") or it.get("amount") or 0.0)
            gap_amt = float(it.get("gap_amount") or it.get("当前市值缺口(元)") or 0.0)
            pct_raw = str(it.get("目标配置占比") or it.get("target_weight_pct") or "0").replace("%", "").strip()
            try:
                w_pct = float(pct_raw)
            except Exception:
                w_pct = 0.0
            merged = dict(it)
            merged.update({
                "fund_code": code,
                "fund_name": fname,
                "monthly_amount": round(m_amt, 2),
                "target_weight_pct": round(w_pct, 2),
                "gap_amount": round(gap_amt, 2),
                "reason": f"当前距目标权重缺口约 ¥{gap_amt:,.0f}，用新钱定向补齐免赎回费" if gap_amt > 0 else "按目标权重均衡定投",
            })
            norm_allocs.append(merged)
        dca = dict(dca)
        dca["allocations"] = norm_allocs
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
    raw_snaps = LedgerBackupVault.list_snapshots()
    snaps = [
        s for s in raw_snaps
        if not any(
            tok in str(s.get("reason", "")).lower() or tok in str(s.get("snapshot_id", "")).lower()
            for tok in ("g29_gate_test", "test_rollback", "pytest")
        )
    ]
    return _sanitize_v1_payload({"count": len(snaps), "snapshots": snaps})


@app.post("/api/v1/backups/restore")
def api_v1_restore_backup(req: RestoreBackupRequest) -> Dict[str, Any]:
    with _LEDGER_WRITE_LOCK:
        ok = LedgerBackupVault.restore_snapshot(req.snapshot_id)
        if not ok:
            raise HTTPException(status_code=400, detail=f"快照恢复失败: {req.snapshot_id}")
        _invalidate_overview_cache()
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
            _invalidate_overview_cache(lid)
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
            _invalidate_overview_cache(lid)
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
            _invalidate_overview_cache(lid)
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
        tw = _target_weights_for_ledger(lid, snapshot)
        tgt_cats: Dict[str, float] = {}
        for tcode, tw_val in (tw or {}).items():
            tname = (CORE_STRATEGY_POOL.get(tcode) or {}).get("fund_name", tcode)
            tcat = pm.classify_fund_asset_class(tcode, tname)
            tgt_cats[tcat] = tgt_cats.get(tcat, 0.0) + float(tw_val or 0.0)
        target_classes = {
            k: round(v, 4)
            for k, v in sorted(tgt_cats.items(), key=lambda x: x[1], reverse=True)
            if v > 1e-4
        }
        return _sanitize_v1_payload({
            "subview": "exposure",
            "ledger_id": lid,
            "status": "ready",
            "holdings_count": len(holdings),
            "total_equity": round(total_mv, 2),
            "asset_classes": asset_classes,
            "target_classes": target_classes,
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


@app.get("/api/v1/funds/{fund_code}/detail")
def api_v1_fund_detail(fund_code: str, dca_monthly: float = 1000.0) -> Dict[str, Any]:
    from fund_detail_service import get_fund_full_detail
    data = get_fund_full_detail(fund_code=fund_code, dca_monthly=dca_monthly)
    return _sanitize_v1_payload(data)


class ActiveLedgerRequest(BaseModel):
    ledger_id: str


class CreateLedgerRequest(BaseModel):
    name: str
    description: str = ""
    initial_cash: float = 0.0


class UpdateCashRequest(BaseModel):
    ledger_id: Optional[str] = None
    available_cash: float


@app.get("/api/v1/ledgers")
def api_v1_list_ledgers() -> Dict[str, Any]:
    mlm = MultiLedgerManager.get_instance()
    active_id = mlm.get_active_ledger_id() or "combat_29_funds"
    items = []
    for meta in mlm.list_ledgers():
        lid = str(meta.get("id", ""))
        try:
            pm = mlm.get_pm(lid)
            cnt = len(getattr(pm, "holdings", {}) or {})
            eq = round(float(getattr(pm, "total_equity", 0.0) or 0.0), 2)
        except Exception:
            cnt = 0
            eq = 0.0
        items.append({
            "id": lid,
            "name": str(meta.get("name", lid)),
            "description": str(meta.get("description", "")),
            "is_demo": lid == "combat_29_funds",
            "holding_count": cnt,
            "total_equity": eq,
            "is_active": lid == active_id,
        })
    return _sanitize_v1_payload({"active_ledger_id": active_id, "count": len(items), "items": items})


@app.post("/api/v1/ledgers/active")
def api_v1_set_active_ledger(req: ActiveLedgerRequest) -> Dict[str, Any]:
    with _LEDGER_WRITE_LOCK:
        mlm = MultiLedgerManager.get_instance()
        ok = mlm.set_active_ledger_id(req.ledger_id)
        if not ok:
            raise HTTPException(status_code=404, detail=f"账本不存在: {req.ledger_id}")
        _invalidate_overview_cache()
        return _sanitize_v1_payload({"active_ledger_id": req.ledger_id, "switched": True})


@app.post("/api/v1/ledgers")
def api_v1_create_ledger(req: CreateLedgerRequest) -> Dict[str, Any]:
    name = str(req.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="账本名称不能为空")
    with _LEDGER_WRITE_LOCK:
        mlm = MultiLedgerManager.get_instance()
        new_id = mlm.create_ledger(name=name, description=req.description or "用户自建实盘账本")
        if req.initial_cash and float(req.initial_cash) > 0:
            pm = mlm.get_pm(new_id)
            pm.available_cash = float(req.initial_cash)
            pm.save_state()
        mlm.set_active_ledger_id(new_id)
        _invalidate_overview_cache()
        return _sanitize_v1_payload({"ledger_id": new_id, "name": name, "created": True})


@app.delete("/api/v1/holdings/{fund_code}")
def api_v1_delete_holding(fund_code: str, ledger_id: Optional[str] = None) -> Dict[str, Any]:
    code = str(fund_code or "").strip().zfill(6)
    with _LEDGER_WRITE_LOCK:
        _, lid, pm, _ = _get_active_context(ledger_id)
        if code not in pm.holdings:
            raise HTTPException(status_code=404, detail=f"账本 {lid} 中未找到基金 {code}")
        LedgerBackupVault.create_snapshot(reason=f"api_delete_holding_{lid}_{code}")
        del pm.holdings[code]
        pm.save_state()
        _invalidate_overview_cache(lid)
        return _sanitize_v1_payload({"ledger_id": lid, "fund_code": code, "deleted": True})


@app.post("/api/v1/holdings/cash")
def api_v1_update_cash(req: UpdateCashRequest) -> Dict[str, Any]:
    cash_val = max(0.0, float(req.available_cash))
    with _LEDGER_WRITE_LOCK:
        _, lid, pm, _ = _get_active_context(req.ledger_id)
        LedgerBackupVault.create_snapshot(reason=f"api_update_cash_{lid}")
        pm.available_cash = round(cash_val, 2)
        pm.save_state()
        _invalidate_overview_cache(lid)
        return _sanitize_v1_payload({"ledger_id": lid, "available_cash": pm.available_cash, "updated": True})


_RISK_TIER_META: Dict[str, Dict[str, str]] = {
    "C1": {"label": "C1 稳健型", "drawdown_hint": "历史最大回撤约 3%~6%", "desc": "以纯债与高股息底仓为主，严控波动，适合稳健理财替代资金"},
    "C2": {"label": "C2 偏稳型", "drawdown_hint": "历史最大回撤约 6%~11%", "desc": "固收打底 + 红利增强，兼顾抗跌与温和增值"},
    "C3": {"label": "C3 均衡型", "drawdown_hint": "历史最大回撤约 12%~17%", "desc": "全天候攻守兼备，红利/宽基/债/海外/黄金多元分散，适合 1 年以上资金"},
    "C4": {"label": "C4 进取型", "drawdown_hint": "历史最大回撤约 18%~24%", "desc": "提高权益与科技弹性权重，博取中长期超额回报"},
    "C5": {"label": "C5 积极型", "drawdown_hint": "历史最大回撤约 24%+", "desc": "高弹性权益配置，适合能承受较大短期波动的长期资金"},
}

_FUND_PLAIN_WHY: Dict[str, Dict[str, str]] = {
    "005561": {"role": "红利低波主锚", "why": "高股息叠加低波动筛选，震荡市与防御期的核心抗跌收益来源"},
    "100032": {"role": "红利增强底仓", "why": "聚焦高分红蓝筹并叠加量化增强，长期复利稳健"},
    "110020": {"role": "A股核心宽基", "why": "覆盖A股最核心大盘资产，费率低廉，稳稳捕捉估值修复"},
    "000478": {"role": "中盘量化增强", "why": "锚定中证500中盘成长风格并叠加量化增强，衔接大盘与小盘轮动"},
    "004194": {"role": "小盘量化增强", "why": "覆盖中证1000高弹性小盘股并做量化选股增强，牛市修复期弹性显著"},
    "002351": {"role": "固收安全垫", "why": "稳健债券底仓，在权益大幅波动时提供正收益缓冲与补仓弹药"},
    "000086": {"role": "纯债压舱石", "why": "高信用等级债券配置，有效平滑组合净值波动"},
    "018757": {"role": "固收增强垫", "why": "稳健固收打底叠加少量权益增强，提升防御端票息回报"},
    "017436": {"role": "美股科技对冲", "why": "与A股低相关，分散单一市场风险，共享全球科技龙头的长期成长"},
    "050025": {"role": "美股宽基对冲", "why": "追踪标普500核心美股资产，与国内权益形成跨市场互补"},
    "011612": {"role": "硬核科技进攻", "why": "A类份额适合长期持有，低估值区间布局国产科技成长弹性"},
    "011613": {"role": "硬核科技进攻", "why": "紧跟硬核科技成长板块，低位分批布局放大反弹弹性"},
    "000216": {"role": "黄金避险气垫", "why": "对冲地缘与汇率波动风险，进一步压低组合整体最大回撤"},
}


_QUANT_MODELS_META: Dict[str, Dict[str, str]] = {
    "all_weather": {
        "id": "all_weather",
        "name": "全天候动态均衡模型",
        "tag": "全档位适配",
        "recommended_tiers": "C1~C5",
        "scenario": "适用场景：不确定牛熊拐点、希望跨周期稳健复利的大多数投资者",
        "principle": "在所选 C 档风险预算内，按十维宏观信号动态平衡红利、宽基、纯债、海外与黄金。",
    },
    "risk_parity": {
        "id": "risk_parity",
        "name": "风险平价抗跌模型",
        "tag": "推荐 C1~C3",
        "recommended_tiers": "C1~C3",
        "scenario": "适用场景：熊市/震荡防御期、厌恶大回撤、追求稳健持有体验的资金",
        "principle": "在所选 C 档风险预算内，按各资产近 60 日波动率倒数配权，让每类资产贡献均衡风险。",
    },
    "dividend_defense": {
        "id": "dividend_defense",
        "name": "高股息红利防御模型",
        "tag": "推荐 C1~C3",
        "recommended_tiers": "C1~C3",
        "scenario": "适用场景：利率下行期、市场震荡筑底、偏好高股息与纯债吃息的稳健配置",
        "principle": "在所选 C 档权益预算内，重点倾斜中证红利低波与红利增强，压降高波动成长敞口。",
    },
    "barbell_growth": {
        "id": "barbell_growth",
        "name": "杠铃攻守策略模型",
        "tag": "推荐 C3~C5",
        "recommended_tiers": "C3~C5",
        "scenario": "适用场景：科技估值处于历史低位、愿意“纯债黄金保底 + 科技/美股搏弹性”的配置",
        "principle": "在所选 C 档风险预算内，一端用纯债黄金守底线，另一端集中配置科创50与纳指100。",
    },
}

_MODEL_CANDIDATE_POOL: List[str] = [
    "005561",  # 红利低波
    "002351",  # 固收安全垫
    "110020",  # 沪深300
    "017436",  # 纳斯达克100
    "000216",  # 黄金
    "011612",  # 科创50A
    "100032",  # 红利增强
    "000086",  # 纯债压舱石
]


def _build_model_weights(model_id: str, tier: str, snap: Dict[str, Any], fund_count: int) -> Dict[str, float]:
    """根据用户选择的量化模型、风险档位与期望基金数量，动态计算总和严格为 1.0 的权重字典。"""
    import numpy as np

    base_res = StrategyBridge.compute_dynamic_tier_weights(tier=tier, market_snapshot=snap)
    base_w: Dict[str, float] = dict(base_res.get("weights", base_res) if isinstance(base_res, dict) else {})
    # 将 011613(C) 在空仓建仓推荐中统一优先映射到 011612(A) 避免长期持有C类高费率
    if "011613" in base_w:
        w_c = base_w.pop("011613")
        base_w["011612"] = round(base_w.get("011612", 0.0) + w_c, 4)

    # 风险档位对应的权益系数（用于调整非默认模型的进攻/防御倾斜）
    eq_scale_map = {"C1": 0.45, "C2": 0.72, "C3": 1.0, "C4": 1.25, "C5": 1.45}
    eq_s = eq_scale_map.get(tier, 1.0)

    if model_id == "risk_parity":
        # 按真实历史 60 日波动率倒数分配风险预算（对齐 aligned_matrix_total_return.parquet 真实列名）
        col_map = {
            "005561": "H30269", "100032": "H00922", "110020": "H00300",
            "002351": "H11009", "000086": "H11009", "017436": "SPX_CNY",
            "011612": "STAR50_STITCH", "000216": "AU9999",
        }
        vols: Dict[str, float] = {}
        try:
            df_mat = StrategyBridge.load_matrix()
            for code, col in col_map.items():
                if col in df_mat.columns:
                    s = df_mat[col].dropna().tail(61)
                    if len(s) >= 20:
                        v = float(s.pct_change().dropna().std() * np.sqrt(250))
                        if v > 0.005:
                            vols[code] = v
        except Exception:
            pass
        # 防御类适当控上限，避免纯债 90% 独大，保留多元分散
        raw = {}
        for code in _MODEL_CANDIDATE_POOL:
            v = vols.get(code, 0.16)
            inv_v = 1.0 / max(v, 0.04)
            is_bond = code in ("002351", "000086")
            raw[code] = inv_v * (0.55 / eq_s if is_bond else eq_s)
        # 避免两只纯债重复，保留主锚 002351 除非用户选 8 只
        if fund_count < 8:
            raw.pop("000086", None)
        weights = raw
    elif model_id == "dividend_defense":
        weights = {
            "005561": 0.34 * eq_s,
            "002351": 0.32 / eq_s,
            "100032": 0.16 * eq_s,
            "000216": 0.10,
            "110020": 0.08 * eq_s,
            "000086": 0.10 / eq_s,
            "017436": 0.06 * eq_s,
            "011612": 0.03 * eq_s,
        }
    elif model_id == "barbell_growth":
        weights = {
            "002351": 0.36 / eq_s,
            "011612": 0.22 * eq_s,
            "017436": 0.20 * eq_s,
            "000216": 0.12,
            "005561": 0.10 * eq_s,
            "110020": 0.08 * eq_s,
            "100032": 0.05 * eq_s,
            "000086": 0.08 / eq_s,
        }
    else:
        # all_weather: 以 StrategyBridge.compute_dynamic_tier_weights 为主体，按需补足候选池供大 N 选择
        weights = dict(base_w)
        fallback_fill = {"005561": 0.12, "110020": 0.10, "002351": 0.18, "017436": 0.10, "011612": 0.08, "000216": 0.08, "100032": 0.07, "000086": 0.06}
        for c, fw in fallback_fill.items():
            if len(weights) >= fund_count:
                break
            if c not in weights:
                weights[c] = fw

    # 过滤掉极小权重并按权重降序裁剪到用户指定的 fund_count
    cleaned = [(c, float(w)) for c, w in weights.items() if float(w) > 1e-4]
    cleaned.sort(key=lambda x: x[1], reverse=True)
    selected = cleaned[: max(2, min(8, int(fund_count)))]
    tot = sum(w for _, w in selected) or 1.0
    norm: Dict[str, float] = {}
    acc = 0.0
    for idx, (c, w) in enumerate(selected):
        if idx == len(selected) - 1:
            norm[c] = round(max(0.0, 1.0 - acc), 4)
        else:
            nw = round(w / tot, 4)
            norm[c] = nw
            acc += nw
    return norm


_EXTREME_CYCLE_CACHE: Dict[Tuple[Any, ...], Tuple[float, Dict[str, Any]]] = {}
_EXTREME_CYCLE_LOCK = threading.Lock()

_QUANT_JOBS: Dict[str, Dict[str, Any]] = {}
_QUANT_JOBS_LOCK = threading.Lock()


class QuantSolveRequest(BaseModel):
    risk_level: str = "C3"
    amount: float = 50000.0
    fund_count: int = 6
    model: str = "all_weather"
    target_return_pct: float = 10.0
    horizon_months: int = 12
    universe_mode: str = "full_market"
    period: str = "1y"
    force: bool = False


class LakehouseSyncRequest(BaseModel):
    cooldown_minutes: int = 30


def _build_blueprint_payload(
    solved: Dict[str, Any],
    tier: str,
    model_id: str,
    n_funds: int,
    cap: float,
    t_ret: float,
    h_mon: int,
    u_mode: str,
    pm: Any,
    snap: Dict[str, Any],
) -> Dict[str, Any]:
    from goal_driven_selector import _POOL_BY_CODE

    target_w = solved["final_weights"]
    factor_profiles = solved["factor_profiles"]
    alloc_breakdown = solved["allocation_breakdown"]
    goal_analysis = solved["goal_analysis"]
    solver_audit = solved["solver_audit"]
    allocation_logic_summary = solved["allocation_logic_summary"]
    cards_meta = solved.get("fund_cards_meta") or {}
    funnel_audit = solved.get("funnel_audit") or {}
    real_bt_info = solved.get("real_bt_info") or {}

    # 严格按用户选定的 fund_count 输出精确只数（支持全市场 266+ 精英湖仓任意入选标的）
    items = []
    regime_label = str(snap.get("market_state") or snap.get("regime") or "中性均衡")
    for code, w_frac in sorted(target_w.items(), key=lambda x: x[1], reverse=True):
        w_pct = round(float(w_frac) * 100.0, 1)
        buy_amt = round(cap * w_pct / 100.0, 2)

        cm = cards_meta.get(code) or {}
        meta = _FUND_PLAIN_WHY.get(code, {})
        pool_m = CORE_STRATEGY_POOL.get(code, {})
        opt_m = _POOL_BY_CODE.get(code, {})
        fname = str(cm.get("fund_name") or pool_m.get("fund_name") or opt_m.get("name") or code)
        d_lim = float(cm.get("daily_limit") or pool_m.get("daily_limit", 1e8))
        fp = factor_profiles.get(code) or {}
        ab = alloc_breakdown.get(code) or {}

        quant_signal = ""
        try:
            cr = pm.get_fund_smart_money_crowding(code) or {}
            b20 = float(cr.get("bias_20", 0.0) or 0.0)
            q_raw = _clean_text(cr.get("quadrant_tag") or "")
            q_rename = {
                "低估击球区": "低估布局区",
                "放量分歧/避险区": "分歧避险区",
                "温和复苏区": "温和修复区",
                "右侧主升/偏热区": "高位偏热区",
            }
            q_tag = q_rename.get(q_raw, q_raw)
            if q_tag:
                quant_signal = f"当前处于【{q_tag}】（MA20乖离 {b20:+.1f}%），"
        except Exception:
            pass

        role_text = str(cm.get("role") or meta.get("role") or opt_m.get("role") or pool_m.get("asset_class") or "核心配置")
        base_why = str(cm.get("why") or meta.get("why") or "符合当前量化风险预算与资产分散目标")
        q_score = int(fp.get("quant_score", 68))
        pcr_pct = float(ab.get("risk_contribution_pcr_pct", w_pct))
        solver_w_pct = float(ab.get("solver_weight_pct", w_pct))
        tilt_delta_pct = float(ab.get("factor_tilt_delta_pct", 0.0))
        quant_reason = (
            f"模型原始求解 {solver_w_pct:.1f}%，叠加详情多因子 {q_score} 分（夏普 {fp.get('sharpe', 0):.2f} / "
            f"最大回撤 -{fp.get('max_dd_pct', 0):.1f}% / 费率 {fp.get('total_fee_pct', 0.6):.2f}%）"
            f"调整 {tilt_delta_pct:+.1f}% → 终值 {w_pct:.1f}%（风险贡献 PCR {pcr_pct:.1f}%）；{quant_signal}"
            f"围绕 {h_mon} 个月 +{t_ret:.0f}% 目标与 {tier} 回撤护栏生成。"
        )
        is_c_share = fname.endswith(("C", "C类")) or str(opt_m.get("share_class", "A")) == "C"
        fee_note = (
            "C 类持有满 30 天免赎回费，适合作为防御/波段机动仓"
            if is_c_share
            else "底仓首选 A 类份额，长期持有免每日计提销售服务费"
        )
        quota_note = ""
        if d_lim < 1e7 and buy_amt > d_lim:
            days_need = max(2, int((buy_amt + d_lim - 1) // d_lim))
            quota_note = f"该基金单日限购 ¥{int(d_lim):,}，建议分约 {days_need} 个交易日买入或改用同类不限购标的承接"

        items.append({
            "fund_code": code,
            "fund_name": fname,
            "role": role_text,
            "bucket_label": str(cm.get("bucket_label") or role_text),
            "asset_class": str(cm.get("asset_class") or "equity"),
            "is_active_fund": bool(cm.get("is_active_fund", False)),
            "real_scale_yi": cm.get("real_scale_yi"),
            "max_star": cm.get("max_star", 0),
            "inception_date": str(cm.get("inception_date", ""))[:10],
            "why": base_why,
            "quant_reason": quant_reason,
            "quant_score": q_score,
            "factor_profile": fp,
            "allocation_breakdown": ab,
            "solver_weight_pct": solver_w_pct,
            "factor_tilt_delta_pct": tilt_delta_pct,
            "risk_contribution_pcr_pct": pcr_pct,
            "fee_note": fee_note,
            "quota_note": quota_note,
            "action_guide": quota_note or "不限购，可按建议金额分批或一次配置",
            "weight_pct": w_pct,
            "suggested_amount": buy_amt,
            "daily_limit": d_lim,
        })

    # 保证展示占比总和严格等于 100.0% 且金额平账
    if items:
        acc_w = 0.0
        for idx, x in enumerate(items):
            if idx == len(items) - 1:
                x["weight_pct"] = round(max(0.0, 100.0 - acc_w), 1)
            else:
                acc_w += x["weight_pct"]
            x["suggested_amount"] = round(cap * x["weight_pct"] / 100.0, 2)

    return _sanitize_v1_payload({
        "risk_level": tier,
        "risk_meta": _RISK_TIER_META[tier],
        "all_risk_levels": _RISK_TIER_META,
        "model": model_id,
        "model_meta": _QUANT_MODELS_META[model_id],
        "all_models": list(_QUANT_MODELS_META.values()),
        "universe_mode": u_mode,
        "fund_count": n_funds,
        "total_amount": round(cap, 2),
        "market_regime": regime_label,
        "goal_analysis": goal_analysis,
        "solver_audit": solver_audit,
        "funnel_audit": funnel_audit,
        "real_bt_info": real_bt_info,
        "allocation_logic_summary": allocation_logic_summary,
        "portfolio_weights": target_w,
        "count": len(items),
        "items": items,
    })


def _build_backtest_curves_payload(
    solved_bundle: Optional[Dict[str, Any]],
    clean_tier: str,
    mode: str,
    clean_model: str,
    n_funds: int,
    clean_period: str,
    t_ret: float,
    h_mon: int,
    u_mode: str,
    snap: Dict[str, Any],
    force: bool = False,
) -> Dict[str, Any]:
    import numpy as np
    from extreme_cycle_analyzer import analyze_extreme_recovery_and_cycles
    from goal_driven_selector import reconcile_goal_vs_backtest, solve_goal_driven_portfolio

    period_days_map = {"3m": 63, "6m": 126, "1y": 252, "2y": 504, "all": 0}
    period_label_map = {"3m": "近 3 个月", "6m": "近 6 个月", "1y": "近 1 年", "2y": "近 2 年", "all": "全周期 (共同存续至今)"}
    if clean_period not in period_days_map:
        clean_period = "1y"

    proxy_early_df = None
    real_bt_info: Dict[str, Any] = {}
    funnel_audit: Optional[Dict[str, Any]] = None

    if mode == "preset_combat_29_vs_6":
        preset = StrategyBridge.get_combat_29_vs_reconstructed_6_preset() or {}
        primary_w = dict(preset.get("reconstructed_6_weights") or _build_model_weights(clean_model, clean_tier, snap, n_funds))
        secondary_w = dict(preset.get("raw_29_weights") or {})
        primary_name = "投顾重构 6 基核心组合"
        secondary_name = "原始 29 基存量组合"
        req_cagr_bt = round((((1.0 + t_ret / 100.0) ** (12.0 / h_mon)) - 1.0) * 100.0, 2)
        df_bt = StrategyBridge.build_custom_portfolio_backtest(
            fund_weights=primary_w,
            secondary_weights=secondary_w if secondary_w else None,
            tier=clean_tier,
            target_return_pct=max(3.0, min(30.0, req_cagr_bt)),
        )
    else:
        if solved_bundle is None:
            solved_bundle = solve_goal_driven_portfolio(
                risk_level=clean_tier,
                fund_count=n_funds,
                model_id=clean_model,
                target_return_pct=t_ret,
                horizon_months=h_mon,
                universe_mode=u_mode,
                market_snapshot=snap,
                force_recompute=bool(force),
            )
        primary_w = dict(solved_bundle["final_weights"])
        secondary_w = None
        u_tag = "全市场" if u_mode == "full_market" else "低费指数"
        primary_name = f"{_QUANT_MODELS_META[clean_model]['name']} ({clean_tier}·{u_tag}·{n_funds}只)"
        secondary_name = ""
        df_bt = solved_bundle.get("real_bt_df")
        proxy_early_df = solved_bundle.get("proxy_early_df")
        real_bt_info = dict(solved_bundle.get("real_bt_info") or {})
        funnel_audit = solved_bundle.get("funnel_audit")
        if df_bt is None or df_bt.empty:
            req_cagr_bt = round((((1.0 + t_ret / 100.0) ** (12.0 / h_mon)) - 1.0) * 100.0, 2)
            df_bt = StrategyBridge.build_custom_portfolio_backtest(
                fund_weights=primary_w,
                secondary_weights=None,
                tier=clean_tier,
                target_return_pct=max(3.0, min(30.0, req_cagr_bt)),
            )

    if df_bt is None or df_bt.empty:
        return _sanitize_v1_payload({"status": "empty", "dates": []})

    # 按用户选定周期切片并重归一化起点为 1.000
    tail_n = period_days_map[clean_period]
    df_win = df_bt.tail(tail_n).copy() if (tail_n > 0 and len(df_bt) > tail_n) else df_bt.copy()

    def _rebase(series):
        vals = series.astype(float).ffill().bfill()
        base = float(vals.iloc[0]) if len(vals) > 0 and float(vals.iloc[0]) > 0 else 1.0
        return vals / base

    nav_pri = _rebase(df_win["strategy_nav"])
    nav_otc = _rebase(df_win["strategy_nav_otc"]) if "strategy_nav_otc" in df_win.columns else (nav_pri * 0.995)
    nav_h300 = _rebase(df_win["bm_nav_沪深300"]) if "bm_nav_沪深300" in df_win.columns else None
    nav_div = _rebase(df_win["bm_nav_红利低波"]) if "bm_nav_红利低波" in df_win.columns else None
    nav_bond = _rebase(df_win["bm_nav_纯债指数"]) if "bm_nav_纯债指数" in df_win.columns else None
    nav_sec = _rebase(df_win["secondary_nav"]) if "secondary_nav" in df_win.columns else None

    def _dd_series(nav_s):
        peak = nav_s.cummax()
        return ((nav_s / peak) - 1.0) * 100.0

    dd_pri = _dd_series(nav_otc)
    dd_h300 = _dd_series(nav_h300) if nav_h300 is not None else None
    dd_sec = _dd_series(nav_sec) if nav_sec is not None else None

    # 实时计算所选周期内的客观绩效指标
    otc_ret = round((float(nav_otc.iloc[-1]) - 1.0) * 100.0, 2)
    theo_ret = round((float(nav_pri.iloc[-1]) - 1.0) * 100.0, 2)
    h300_ret = round((float(nav_h300.iloc[-1]) - 1.0) * 100.0, 2) if nav_h300 is not None else 0.0
    excess_ret = round(otc_ret - h300_ret, 2)
    n_days = max(len(df_win), 1)
    ann_ret = round((float(nav_otc.iloc[-1]) ** (252.0 / n_days) - 1.0) * 100.0, 2) if n_days >= 200 else None
    mdd_pct = round(float(dd_pri.min()), 2)
    h300_mdd = round(float(dd_h300.min()), 2) if dd_h300 is not None else 0.0

    daily_rets = nav_otc.pct_change().dropna()
    std_d = float(daily_rets.std()) if len(daily_rets) > 2 else 0.0
    sharpe = round(((float(daily_rets.mean()) * 252.0 - 0.02) / (std_d * np.sqrt(252.0))), 2) if std_d > 1e-8 else 0.0

    # 按周期合理计算正收益胜率（短周期按周、长周期按月，客观无绝对化夸大）
    bucket = 5 if n_days <= 90 else 21
    bucket_unit = "周" if bucket == 5 else "个月"
    win_rate_period_label = "周度正收益占比" if bucket == 5 else "月度正收益占比"
    chunk_rets = []
    arr = nav_otc.values
    for i in range(0, len(arr) - 1, bucket):
        j = min(i + bucket, len(arr) - 1)
        if arr[i] > 0:
            chunk_rets.append((arr[j] / arr[i]) - 1.0)
    pos_chunks = sum(1 for r in chunk_rets if r > 0)
    tot_chunks = max(len(chunk_rets), 1)
    win_pct = round(pos_chunks / tot_chunks * 100.0, 1)

    metrics_obj = {
        "period_return_pct": otc_ret,
        "theoretical_return_pct": theo_ret,
        "annualized_return_pct": ann_ret,
        "hs300_return_pct": h300_ret,
        "excess_return_pct": excess_ret,
        "max_drawdown_pct": mdd_pct,
        "hs300_mdd_pct": h300_mdd,
        "win_rate_label": win_rate_period_label,
        "win_rate_pct": win_pct,
        "win_rate_detail": f"{pos_chunks} / {tot_chunks} {bucket_unit}录得正收益",
        "sharpe_ratio": sharpe,
        "trading_days": n_days,
    }

    # 目标收益 vs 历史回测偏差归因
    goal_reconciliation = None
    if solved_bundle is not None:
        goal_reconciliation = reconcile_goal_vs_backtest(
            goal_analysis=solved_bundle["goal_analysis"],
            backtest_metrics=metrics_obj,
            period_key=clean_period,
            period_label=period_label_map[clean_period],
            tier=clean_tier,
            model_name=_QUANT_MODELS_META[clean_model]["name"],
            solver_audit=solved_bundle.get("solver_audit"),
        )

    # 极端市场预计修复天数、历史修复天数、完整牛熊周期与量化止盈锚点（全周期 df_bt + 早期透明参考）
    ext_key = (clean_tier, mode, clean_model, n_funds, round(t_ret, 1), h_mon, u_mode)
    extreme_cycle_analysis = None
    if not force:
        with _EXTREME_CYCLE_LOCK:
            ec_hit = _EXTREME_CYCLE_CACHE.get(ext_key)
            if ec_hit and (time.time() - ec_hit[0]) < 600.0:
                extreme_cycle_analysis = ec_hit[1]
    if extreme_cycle_analysis is None:
        extreme_cycle_analysis = analyze_extreme_recovery_and_cycles(
            df_bt=df_bt,
            target_return_pct=t_ret,
            horizon_months=h_mon,
            tier=clean_tier,
            market_snapshot=snap,
            n_simulations=10000,
            df_proxy_early=proxy_early_df,
        )
        with _EXTREME_CYCLE_LOCK:
            _EXTREME_CYCLE_CACHE[ext_key] = (time.time(), extreme_cycle_analysis)

    # 抽样用于前端 ECharts 渲染（约 260 点）
    n_rows = len(df_win)
    step = max(1, n_rows // 260)
    idx_list = list(range(0, n_rows, step))
    if idx_list[-1] != n_rows - 1:
        idx_list.append(n_rows - 1)

    dates = [str(d)[:10] for d in df_win["date"].iloc[idx_list].tolist()]
    d_start = dates[0] if dates else "2018-01-02"
    d_end = dates[-1] if dates else "2026-11-25"
    raw_slices = [
        {"start": "2018-01-02", "end": "2018-12-28", "label": "去杠杆熊市", "color": "rgba(239, 68, 68, 0.08)"},
        {"start": "2019-01-02", "end": "2020-12-31", "label": "核心资产牛市", "color": "rgba(16, 185, 129, 0.08)"},
        {"start": "2021-01-04", "end": "2021-12-31", "label": "赛道股分化", "color": "rgba(245, 158, 11, 0.08)"},
        {"start": "2022-01-04", "end": "2022-12-30", "label": "加息杀估值", "color": "rgba(239, 68, 68, 0.08)"},
        {"start": "2023-01-03", "end": "2024-08-30", "label": "高股息避险", "color": "rgba(56, 189, 248, 0.08)"},
        {"start": "2024-09-02", "end": "2025-06-30", "label": "924大转向", "color": "rgba(16, 185, 129, 0.08)"},
        {"start": "2025-07-01", "end": d_end, "label": "样本外区间", "color": "rgba(139, 92, 246, 0.10)"},
    ]
    # 仅保留落在真实回测日期区间内的背景切片，避免空 X 轴截断
    slices = []
    if clean_period == "all" and dates:
        for sl in raw_slices:
            if sl["end"] < d_start or sl["start"] > d_end:
                continue
            slices.append({
                **sl,
                "start": max(sl["start"], d_start),
                "end": min(sl["end"], d_end),
            })

    def _pick(s, digits=4):
        if s is None:
            return []
        return [round(float(x), digits) for x in s.iloc[idx_list].fillna(0.0).tolist()]

    def _col_alloc(col: str):
        if col not in df_win.columns:
            return []
        return [round(float(x) * 100.0, 1) for x in df_win[col].iloc[idx_list].fillna(0.0).tolist()]

    weight_vs_pcr: List[Dict[str, Any]] = []
    if solved_bundle is not None:
        ab_map = solved_bundle.get("allocation_breakdown") or {}
        cm_map = solved_bundle.get("fund_cards_meta") or {}
        for code, wf in sorted(primary_w.items(), key=lambda kv: -float(kv[1])):
            cm = cm_map.get(code) or {}
            ab = ab_map.get(code) or {}
            fname = str(cm.get("fund_name") or code)
            weight_vs_pcr.append({
                "fund_code": code,
                "fund_name": fname,
                "short_name": fname[:8],
                "bucket_label": str(cm.get("bucket_label") or ab.get("bucket") or "核心配置"),
                "weight_pct": round(float(wf) * 100.0, 1),
                "pcr_pct": round(float(ab.get("risk_contribution_pcr_pct", float(wf) * 100.0)), 1),
            })

    return _sanitize_v1_payload({
        "status": "ready",
        "tier": clean_tier,
        "model": clean_model,
        "universe_mode": u_mode,
        "fund_count": n_funds,
        "target_return_pct": t_ret,
        "horizon_months": h_mon,
        "period": clean_period,
        "period_label": period_label_map[clean_period],
        "date_range": f"{d_start} ~ {d_end}" if dates else "",
        "mode": mode,
        "primary_name": primary_name,
        "secondary_name": secondary_name,
        "portfolio_weights": primary_w,
        "weight_vs_pcr": weight_vs_pcr,
        "solver_audit": solved_bundle["solver_audit"] if solved_bundle else None,
        "funnel_audit": funnel_audit,
        "real_bt_info": real_bt_info,
        "goal_reconciliation": goal_reconciliation,
        "extreme_cycle_analysis": extreme_cycle_analysis,
        "metrics": metrics_obj,
        "dates": dates,
        "nav": {
            "primary": _pick(nav_pri, 4),
            "primary_otc": _pick(nav_otc, 4),
            "secondary": _pick(nav_sec, 4),
            "hs300": _pick(nav_h300, 4),
            "dividend": _pick(nav_div, 4),
            "bond": _pick(nav_bond, 4),
        },
        "cagr": {
            "primary": theo_ret,
            "primary_otc": otc_ret,
            "secondary": round((float(nav_sec.iloc[-1]) - 1.0) * 100.0, 2) if nav_sec is not None else None,
            "hs300": h300_ret,
            "dividend": round((float(nav_div.iloc[-1]) - 1.0) * 100.0, 2) if nav_div is not None else None,
            "bond": round((float(nav_bond.iloc[-1]) - 1.0) * 100.0, 2) if nav_bond is not None else None,
        },
        "drawdown": {
            "primary": _pick(dd_pri, 2),
            "secondary": _pick(dd_sec, 2),
            "hs300": _pick(dd_h300, 2),
        },
        "allocation": {
            "ashare": _col_alloc("weight_ashare"),
            "bond": _col_alloc("weight_bond"),
            "gold": _col_alloc("weight_gold"),
            "spx": _col_alloc("weight_spx"),
        },
        "slices": slices,
    })


@app.get("/api/v1/lakehouse/status")
def api_v1_lakehouse_status() -> Dict[str, Any]:
    from market_lakehouse import get_lakehouse_status
    return _sanitize_v1_payload(get_lakehouse_status())


@app.post("/api/v1/lakehouse/sync_daily")
def api_v1_lakehouse_sync_daily(req: Optional[LakehouseSyncRequest] = None) -> Dict[str, Any]:
    from goal_driven_selector import clear_goal_solver_cache
    from market_lakehouse import incremental_daily_sync

    cd = int(req.cooldown_minutes) if req is not None else 30
    res = incremental_daily_sync(cooldown_minutes=max(0, min(1440, cd)))
    if res.get("updated_dates", 0) > 0:
        clear_goal_solver_cache()
        with _BACKTEST_CURVES_LOCK:
            _BACKTEST_CURVES_CACHE.clear()
        with _EXTREME_CYCLE_LOCK:
            _EXTREME_CYCLE_CACHE.clear()
    return _sanitize_v1_payload(res)


@app.post("/api/v1/quant/solve")
def api_v1_quant_solve_start(req: QuantSolveRequest) -> Dict[str, Any]:
    """启动异步全市场量化求解任务并立即返回 job_id（供前端 4 阶段真实进度条轮询）。"""
    import uuid
    from goal_driven_selector import solve_goal_driven_portfolio

    tier = str(req.risk_level or "C3").upper().strip()
    if tier not in _RISK_TIER_META:
        tier = "C3"
    model_id = str(req.model or "all_weather").strip().lower()
    if model_id not in _QUANT_MODELS_META:
        model_id = "all_weather"
    u_mode = str(req.universe_mode or "full_market").strip().lower()
    if u_mode not in ("full_market", "index_only"):
        u_mode = "full_market"
    n_funds = max(3, min(8, int(req.fund_count or 6)))
    cap = max(1000.0, float(req.amount or 50000.0))
    t_ret = max(2.0, min(60.0, float(req.target_return_pct or 10.0)))
    h_mon = max(3, min(60, int(req.horizon_months or 12)))
    clean_period = str(req.period or "1y").strip().lower()
    if clean_period not in ("3m", "6m", "1y", "2y", "all"):
        clean_period = "1y"

    job_id = uuid.uuid4().hex[:12]
    now_ts = time.time()
    job_rec: Dict[str, Any] = {
        "job_id": job_id,
        "status": "running",
        "progress_pct": 5,
        "stage_text": "正在初始化全市场量化求解引擎与本地真净值湖仓...",
        "created_ts": now_ts,
        "elapsed_ms": 0,
        "result": None,
        "error": None,
    }
    with _QUANT_JOBS_LOCK:
        # 清理超过 15 分钟的旧任务防内存增长
        if len(_QUANT_JOBS) > 40:
            stale = [k for k, v in _QUANT_JOBS.items() if (now_ts - float(v.get("created_ts", 0))) > 900.0]
            for k in stale:
                _QUANT_JOBS.pop(k, None)
        _QUANT_JOBS[job_id] = job_rec

    def _run_job() -> None:
        t0 = time.monotonic()

        def _cb(pct: int, msg: str) -> None:
            with _QUANT_JOBS_LOCK:
                if job_id in _QUANT_JOBS:
                    _QUANT_JOBS[job_id]["progress_pct"] = min(84, max(5, int(pct * 0.84)))
                    _QUANT_JOBS[job_id]["stage_text"] = str(msg)
                    _QUANT_JOBS[job_id]["elapsed_ms"] = int(round((time.monotonic() - t0) * 1000.0))

        try:
            _, _, pm, snap = _get_active_context(None)
            solved = solve_goal_driven_portfolio(
                risk_level=tier,
                fund_count=n_funds,
                model_id=model_id,
                target_return_pct=t_ret,
                horizon_months=h_mon,
                universe_mode=u_mode,
                market_snapshot=snap,
                force_recompute=bool(req.force),
                progress_cb=_cb,
            )
            with _QUANT_JOBS_LOCK:
                if job_id in _QUANT_JOBS:
                    _QUANT_JOBS[job_id]["progress_pct"] = 88
                    _QUANT_JOBS[job_id]["stage_text"] = "正在合成真实复权净值回测曲线与 10,000 次极端修复周期测算..."
                    _QUANT_JOBS[job_id]["elapsed_ms"] = int(round((time.monotonic() - t0) * 1000.0))

            bp_payload = _build_blueprint_payload(
                solved=solved,
                tier=tier,
                model_id=model_id,
                n_funds=n_funds,
                cap=cap,
                t_ret=t_ret,
                h_mon=h_mon,
                u_mode=u_mode,
                pm=pm,
                snap=snap,
            )
            bt_payload = _build_backtest_curves_payload(
                solved_bundle=solved,
                clean_tier=tier,
                mode="model_live",
                clean_model=model_id,
                n_funds=n_funds,
                clean_period=clean_period,
                t_ret=t_ret,
                h_mon=h_mon,
                u_mode=u_mode,
                snap=snap,
                force=bool(req.force),
            )
            cache_key = f"{tier}:model_live:{model_id}:{n_funds}:{clean_period}:{round(t_ret, 1)}:{h_mon}:{u_mode}"
            with _BACKTEST_CURVES_LOCK:
                _BACKTEST_CURVES_CACHE[cache_key] = (time.time(), bt_payload)

            with _QUANT_JOBS_LOCK:
                if job_id in _QUANT_JOBS:
                    _QUANT_JOBS[job_id]["status"] = "done"
                    _QUANT_JOBS[job_id]["progress_pct"] = 100
                    _QUANT_JOBS[job_id]["stage_text"] = "全市场量化选基、真实净值回测与极端周期测算完成"
                    _QUANT_JOBS[job_id]["elapsed_ms"] = int(round((time.monotonic() - t0) * 1000.0))
                    _QUANT_JOBS[job_id]["result"] = {
                        "blueprint": bp_payload,
                        "backtest_curves": bt_payload,
                    }
        except Exception as exc:
            logger.exception("异步量化求解失败: %s", exc)
            with _QUANT_JOBS_LOCK:
                if job_id in _QUANT_JOBS:
                    _QUANT_JOBS[job_id]["status"] = "error"
                    _QUANT_JOBS[job_id]["error"] = str(exc)
                    _QUANT_JOBS[job_id]["stage_text"] = f"求解中断：{exc}"
                    _QUANT_JOBS[job_id]["elapsed_ms"] = int(round((time.monotonic() - t0) * 1000.0))

    threading.Thread(target=_run_job, name=f"agy2-quant-solve-{job_id}", daemon=True).start()
    return _sanitize_v1_payload({
        "job_id": job_id,
        "status": "running",
        "progress_pct": 5,
        "stage_text": job_rec["stage_text"],
    })


@app.get("/api/v1/quant/solve/{job_id}")
def api_v1_quant_solve_status(job_id: str) -> Dict[str, Any]:
    with _QUANT_JOBS_LOCK:
        job = _QUANT_JOBS.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="求解任务不存在或已过期")
        snap_job = {
            "job_id": job["job_id"],
            "status": job["status"],
            "progress_pct": job["progress_pct"],
            "stage_text": job["stage_text"],
            "elapsed_ms": job["elapsed_ms"],
            "error": job.get("error"),
        }
        if job["status"] == "done":
            snap_job["result"] = job.get("result")
    return _sanitize_v1_payload(snap_job)


@app.get("/api/v1/recommend/blueprint")
def api_v1_recommend_blueprint(
    risk_level: str = "C3",
    amount: float = 50000.0,
    fund_count: int = 6,
    model: str = "all_weather",
    target_return_pct: float = 10.0,
    horizon_months: int = 12,
    universe_mode: str = "full_market",
    force: bool = False,
) -> Dict[str, Any]:
    from goal_driven_selector import solve_goal_driven_portfolio

    tier = str(risk_level or "C3").upper().strip()
    if tier not in _RISK_TIER_META:
        tier = "C3"
    model_id = str(model or "all_weather").strip().lower()
    if model_id not in _QUANT_MODELS_META:
        model_id = "all_weather"
    u_mode = str(universe_mode or "full_market").strip().lower()
    if u_mode not in ("full_market", "index_only"):
        u_mode = "full_market"
    n_funds = max(3, min(8, int(fund_count or 6)))
    cap = max(1000.0, float(amount or 50000.0))
    t_ret = max(2.0, min(60.0, float(target_return_pct or 10.0)))
    h_mon = max(3, min(60, int(horizon_months or 12)))

    _, _, pm, snap = _get_active_context(None)
    solved = solve_goal_driven_portfolio(
        risk_level=tier,
        fund_count=n_funds,
        model_id=model_id,
        target_return_pct=t_ret,
        horizon_months=h_mon,
        universe_mode=u_mode,
        market_snapshot=snap,
        force_recompute=bool(force),
    )
    return _build_blueprint_payload(
        solved=solved,
        tier=tier,
        model_id=model_id,
        n_funds=n_funds,
        cap=cap,
        t_ret=t_ret,
        h_mon=h_mon,
        u_mode=u_mode,
        pm=pm,
        snap=snap,
    )


@app.get("/api/v1/charts/backtest_curves")
def api_v1_charts_backtest_curves(
    tier: str = "C3",
    mode: str = "model_live",
    model: str = "all_weather",
    fund_count: int = 6,
    period: str = "1y",
    target_return_pct: float = 10.0,
    horizon_months: int = 12,
    universe_mode: str = "full_market",
    force: bool = False,
) -> Dict[str, Any]:
    clean_tier = str(tier or "C3").upper().strip()
    if clean_tier not in _RISK_TIER_META:
        clean_tier = "C3"
    clean_model = str(model or "all_weather").strip().lower()
    if clean_model not in _QUANT_MODELS_META:
        clean_model = "all_weather"
    u_mode = str(universe_mode or "full_market").strip().lower()
    if u_mode not in ("full_market", "index_only"):
        u_mode = "full_market"
    n_funds = max(3, min(8, int(fund_count or 6)))
    t_ret = max(2.0, min(60.0, float(target_return_pct or 10.0)))
    h_mon = max(3, min(60, int(horizon_months or 12)))
    clean_period = str(period or "1y").strip().lower()
    if clean_period not in ("3m", "6m", "1y", "2y", "all"):
        clean_period = "1y"

    cache_key = f"{clean_tier}:{mode}:{clean_model}:{n_funds}:{clean_period}:{round(t_ret, 1)}:{h_mon}:{u_mode}"
    if not force:
        with _BACKTEST_CURVES_LOCK:
            cached = _BACKTEST_CURVES_CACHE.get(cache_key)
            if cached and (time.time() - cached[0]) < 300.0:
                return cached[1]

    snap = StrategyBridge.get_latest_market_snapshot(force_reload=False)
    payload = _build_backtest_curves_payload(
        solved_bundle=None,
        clean_tier=clean_tier,
        mode=mode,
        clean_model=clean_model,
        n_funds=n_funds,
        clean_period=clean_period,
        t_ret=t_ret,
        h_mon=h_mon,
        u_mode=u_mode,
        snap=snap,
        force=bool(force),
    )
    with _BACKTEST_CURVES_LOCK:
        _BACKTEST_CURVES_CACHE[cache_key] = (time.time(), payload)
    return payload


@app.get("/api/v1/charts/crowding_quadrant")
def api_v1_charts_crowding_quadrant(
    ledger_id: Optional[str] = None,
    codes: Optional[str] = None,
) -> Dict[str, Any]:
    _, lid, pm, _ = _get_active_context(ledger_id)
    holdings = getattr(pm, "holdings", {}) or {}
    # 若前端显式传入上方全市场推荐组合代码列表，则严格展示该方案的真实 MA20 乖离与拥挤度象限；否则回退当前账本核心持仓
    explicit_codes: List[str] = []
    if codes:
        for tok in str(codes).split(","):
            c = tok.strip().zfill(6) if tok.strip().isdigit() else tok.strip()
            if c and c not in explicit_codes:
                explicit_codes.append(c)

    if explicit_codes:
        core_codes = explicit_codes[:12]
        scope_mode = "recommended_portfolio"
    else:
        core_codes = [c for c, h in sorted(holdings.items(), key=lambda x: -float(getattr(x[1], "market_value", 0.0) or 0.0)) if float(getattr(h, "market_value", 0.0) or 0.0) >= 200.0]
        if not core_codes:
            core_codes = ["005561", "110020", "002351", "017436", "011612", "000216"]
        else:
            for c in ("005561", "110020", "002351", "017436", "011612", "000216"):
                if c not in core_codes and len(core_codes) < 12:
                    core_codes.append(c)
        scope_mode = "ledger_holdings"

    points = []
    for code in core_codes[:12]:
        try:
            d = pm.get_fund_smart_money_crowding(code, force_reload=True) or {}
            fname = str(d.get("fund_name") or code)
            points.append({
                "fund_code": code,
                "fund_name": fname,
                "short_name": str(d.get("short_name") or fname)[:10],
                "bias_20": round(float(d.get("bias_20", 0.0) or 0.0), 2),
                "crowding_score": round(float(d.get("crowding_score", 50.0) or 50.0), 1),
                "ret_20d": round(float(d.get("ret_20d", 0.0) or 0.0), 2),
                "quadrant": str(d.get("quadrant_tag") or "温和复苏区"),
                "advisory_tip": str(d.get("advisory_tip") or ""),
                "in_holdings": code in holdings,
            })
        except Exception:
            continue

    return _sanitize_v1_payload({"ledger_id": lid, "scope_mode": scope_mode, "count": len(points), "points": points})


@app.get("/api/v1/charts/scenario_backtest")
def api_v1_charts_scenario_backtest(
    start_date: str = "2024-09-18",
    tier: str = "C3",
    capital: float = 100000.0,
    dynamic_rebalance: bool = True,
    model: Optional[str] = None,
    fund_count: Optional[int] = None,
    target_return_pct: Optional[float] = None,
    horizon_months: Optional[int] = None,
    universe_mode: str = "full_market",
) -> Dict[str, Any]:
    clean_tier = str(tier or "C3").upper().strip()
    if clean_tier not in _RISK_TIER_META:
        clean_tier = "C3"
    clean_date = str(start_date or "2024-09-18").strip()[:10]
    cap = max(1000.0, float(capital or 100000.0))

    portfolio_name = f"动态策略模板 ({clean_tier})"
    used_proxy_early = False
    proxy_note = ""
    portfolio_weights: Optional[Dict[str, float]] = None

    if model is not None:
        from goal_driven_selector import simulate_portfolio_scenario_backtest, solve_goal_driven_portfolio

        clean_model = str(model or "all_weather").strip().lower()
        if clean_model not in _QUANT_MODELS_META:
            clean_model = "all_weather"
        u_mode = str(universe_mode or "full_market").strip().lower()
        if u_mode not in ("full_market", "index_only"):
            u_mode = "full_market"
        n_funds = max(3, min(8, int(fund_count or 6)))
        t_ret = max(2.0, min(60.0, float(target_return_pct if target_return_pct is not None else 10.0)))
        h_mon = max(3, min(60, int(horizon_months if horizon_months is not None else 12)))

        snap = StrategyBridge.get_latest_market_snapshot(force_reload=False)
        solved = solve_goal_driven_portfolio(
            risk_level=clean_tier,
            fund_count=n_funds,
            model_id=clean_model,
            target_return_pct=t_ret,
            horizon_months=h_mon,
            universe_mode=u_mode,
            market_snapshot=snap,
            force_recompute=False,
        )
        res = simulate_portfolio_scenario_backtest(
            solved_bundle=solved,
            start_date=clean_date,
            dynamic_rebalance=bool(dynamic_rebalance),
        )
        u_tag = "全市场" if u_mode == "full_market" else "低费指数"
        portfolio_name = f"{_QUANT_MODELS_META[clean_model]['name']} ({clean_tier}·{u_tag}·{n_funds}只)"
        used_proxy_early = bool(res.get("used_proxy_early", False))
        proxy_note = str(res.get("proxy_note", ""))
        portfolio_weights = res.get("portfolio_weights")
    else:
        res = StrategyBridge.run_historical_time_machine_backtest(
            target_date=clean_date,
            tier=clean_tier,
            capital=cap,
            dynamic_rebalance=bool(dynamic_rebalance),
        ) or {}

    curve_df = res.get("curve_df")
    dates: List[str] = []
    strat_nav: List[float] = []
    h300_nav: List[float] = []
    bm50_nav: List[float] = []
    if curve_df is not None and not curve_df.empty:
        n_rows = len(curve_df)
        step = max(1, n_rows // 240)
        idx_list = list(range(0, n_rows, step))
        if idx_list[-1] != n_rows - 1:
            idx_list.append(n_rows - 1)
        df_s = curve_df.iloc[idx_list]
        dates = [str(d)[:10] for d in df_s["date"].tolist()]
        strat_nav = [round(float(x), 4) for x in df_s["strategy_net_nav"].fillna(1.0).tolist()]
        h300_nav = [round(float(x), 4) for x in df_s["h300_nav"].fillna(1.0).tolist()]
        if "benchmark_nav" in df_s.columns:
            bm50_nav = [round(float(x), 4) for x in df_s["benchmark_nav"].fillna(1.0).tolist()]

    return _sanitize_v1_payload({
        "start_date": str(res.get("target_date") or clean_date),
        "tier": clean_tier,
        "portfolio_name": portfolio_name,
        "used_proxy_early": used_proxy_early,
        "proxy_note": proxy_note,
        "portfolio_weights": portfolio_weights,
        "dynamic_rebalance": bool(dynamic_rebalance),
        "kpis": {
            "m3": res.get("kpi_3m"),
            "m6": res.get("kpi_6m"),
            "y1": res.get("kpi_1y"),
            "all": res.get("kpi_all"),
        },
        "dates": dates,
        "strategy_nav": strat_nav,
        "hs300_nav": h300_nav,
        "balanced_nav": bm50_nav,
    })


@app.get("/api/v1/tools/etf_premiums")
def api_v1_tools_etf_premiums() -> Dict[str, Any]:
    _, _, pm, _ = _get_active_context(None)
    try:
        alerts = pm.check_etf_premiums() or []
    except Exception as exc:
        logger.warning("check_etf_premiums 异常: %s", exc)
        alerts = []
    items = [
        {
            "code": str(a.get("code", "")),
            "name": str(a.get("name", "")),
            "price": float(a.get("price", 0.0) or 0.0),
            "iopv": float(a.get("iopv", 0.0) or 0.0),
            "premium_pct": round(float(a.get("premium_pct", 0.0) or 0.0), 2),
            "advice": "场内溢价超过 0.8% 安全线，建议改用场外联接基金或等待溢价回落，避免高位接盘。",
        }
        for a in alerts
    ]
    return _sanitize_v1_payload({"alert_count": len(items), "items": items})


@app.get("/api/v1/tools/dividend_advice")
def api_v1_tools_dividend_advice(ledger_id: Optional[str] = None) -> Dict[str, Any]:
    _, lid, pm, snap = _get_active_context(ledger_id)
    cur_erp = round(float(snap.get("erp_percentile", 75.0) or 75.0), 1)
    if cur_erp >= 70.0:
        rec_mode = "reinvest"
        rec_label = "红利再投资"
        summary = f"当前股债性价比（ERP）历史分位达 {cur_erp:.1f}%，处于偏低估区间：建议基金分红方式优先设为【红利再投资】，免申购费自动积累更多份额。"
    elif cur_erp <= 35.0:
        rec_mode = "cash"
        rec_label = "现金分红"
        summary = f"当前股债性价比（ERP）历史分位为 {cur_erp:.1f}%，处于偏高估区间：建议基金分红方式优先设为【现金分红】，零赎回费落袋为安。"
    else:
        rec_mode = "neutral"
        rec_label = "红利基金选再投资，成长基金选现金分红"
        summary = f"当前股债性价比（ERP）历史分位为 {cur_erp:.1f}%，处于中性均衡区间：红利与宽基底仓可设为【红利再投资】，高波动成长基金可设为【现金分红】。"

    return _sanitize_v1_payload({
        "ledger_id": lid,
        "erp_percentile": cur_erp,
        "recommended_mode": rec_mode,
        "recommended_label": rec_label,
        "summary": summary,
    })


# =====================================================================
# 单端口静态前端托管（当 web/dist 构建产物存在时自动挂载）
# =====================================================================
_WEB_DIST_DIR = ROOT_DIR / "web" / "dist"
if (_WEB_DIST_DIR / "index.html").exists():
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles

    _assets_dir = _WEB_DIST_DIR / "assets"
    if _assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="web_assets")

    @app.get("/", include_in_schema=False)
    def _serve_spa_root():
        return FileResponse(str(_WEB_DIST_DIR / "index.html"))

    @app.get("/{full_path:path}", include_in_schema=False)
    def _serve_spa_fallback(full_path: str):
        if full_path.startswith("api/") or full_path in ("docs", "redoc", "openapi.json"):
            raise HTTPException(status_code=404, detail="Not Found")
        candidate = _WEB_DIST_DIR / full_path
        if candidate.is_file():
            return FileResponse(str(candidate))
        return FileResponse(str(_WEB_DIST_DIR / "index.html"))


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
