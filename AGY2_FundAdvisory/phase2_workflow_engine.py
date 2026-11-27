# -*- coding: utf-8 -*-
"""
AGY2 Phase 2 Money-Making Workflow Engine (phase2_workflow_engine.py)
=====================================================================
面向中国场外买基人的「赚钱 + 守住果实」实盘闭环后端引擎：
  1. 真实资金加权年化收益率 XIRR（牛顿迭代 + 二分法兜底）与本机私有流水账本；
  2. 持仓级三阶移动止盈与守果雷达（高点回撤落袋 / 达标追踪 / 7日惩罚红线 / 深套勿割）；
  3. 智能分批建仓向导（短线过热自动降首笔 + 限购拆单 + 短期 C 类省费 + 银行/支付宝清单）；
  4. 14:30 尾盘实盘速决卡（复用 TradingClock 15:00 生死线与 Top 3 优先动作聚合）。
"""

from __future__ import annotations

import json
import math
import os
import re
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

import runtime_paths
from trading_clock_fee import TradingClock


def _parse_date_safe(val: Any, fallback: Optional[date] = None) -> date:
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    s = str(val or "").strip()[:10]
    if s:
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
            try:
                return datetime.strptime(s, fmt).date()
            except ValueError:
                continue
    return fallback or date.today()


def _safe_float(val: Any, default: float = 0.0) -> float:
    try:
        v = float(val)
        return v if math.isfinite(v) else default
    except Exception:
        return default


# =====================================================================
# 1. Exact Annualized Money-Weighted XIRR & Per-Ledger Cashflow Store
# =====================================================================

def compute_xirr(cashflows: List[Tuple[date, float]]) -> Optional[float]:
    """
    计算标准资金加权年化收益率 XIRR（十进制，如 0.125 = +12.5%）：
    约定：买入/入金为负（< 0），赎回/分红/期末总资产为正（> 0）。
    采用带保护的牛顿迭代 + 区间二分兜底，保证单调 cashflow 必然收敛至 1e-7 精度。
    """
    cleaned = [(d, float(a)) for d, a in cashflows if math.isfinite(float(a)) and abs(float(a)) > 1e-6]
    if len(cleaned) < 2:
        return None
    has_pos = any(a > 0 for _, a in cleaned)
    has_neg = any(a < 0 for _, a in cleaned)
    if not (has_pos and has_neg):
        return None

    cleaned.sort(key=lambda x: x[0])
    d0 = cleaned[0][0]
    span_days = (cleaned[-1][0] - d0).days
    if span_days < 1:
        return None

    t_years = [((d - d0).days / 365.0) for d, _ in cleaned]
    amounts = [a for _, a in cleaned]

    def _npv(rate: float) -> float:
        base = 1.0 + rate
        if base <= 1e-9:
            return float("inf")
        total = 0.0
        for a, t in zip(amounts, t_years):
            total += a / (base ** t)
        return total

    def _dnpv(rate: float) -> float:
        base = 1.0 + rate
        if base <= 1e-9:
            return float("nan")
        total = 0.0
        for a, t in zip(amounts, t_years):
            if t != 0.0:
                total -= (t * a) / (base ** (t + 1.0))
        return total

    # 1. Safeguarded Newton-Raphson
    r = 0.10
    for _ in range(60):
        f = _npv(r)
        if not math.isfinite(f):
            break
        if abs(f) < 1e-7:
            return max(-0.99, min(10.0, r))
        df = _dnpv(r)
        if not math.isfinite(df) or abs(df) < 1e-12:
            break
        r_next = r - f / df
        if not math.isfinite(r_next) or r_next <= -0.99 or r_next > 20.0:
            break
        if abs(r_next - r) < 1e-8:
            return max(-0.99, min(10.0, r_next))
        r = r_next

    # 2. Bracketed bisection fallback
    grid = [-0.95, -0.80, -0.50, -0.25, -0.10, 0.0, 0.05, 0.15, 0.30, 0.60, 1.0, 2.0, 5.0, 10.0]
    lo, hi = None, None
    f_prev = _npv(grid[0])
    for i in range(1, len(grid)):
        f_cur = _npv(grid[i])
        if math.isfinite(f_prev) and math.isfinite(f_cur) and f_prev * f_cur <= 0.0:
            lo, hi = grid[i - 1], grid[i]
            break
        f_prev = f_cur

    if lo is None or hi is None:
        return None

    f_lo = _npv(lo)
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        f_mid = _npv(mid)
        if not math.isfinite(f_mid):
            return None
        if abs(f_mid) < 1e-7 or (hi - lo) < 1e-8:
            return max(-0.99, min(10.0, mid))
        if f_lo * f_mid <= 0.0:
            hi = mid
        else:
            lo = mid
            f_lo = f_mid
    return max(-0.99, min(10.0, 0.5 * (lo + hi)))


def _cashflow_file_path(ledger_id: str) -> Path:
    safe_id = re.sub(r"[^a-zA-Z0-9_-]", "_", str(ledger_id or "default")).strip("_") or "default"
    return runtime_paths.get_data_dir() / f"cashflows_{safe_id}.json"


def load_ledger_cashflows(ledger_id: str) -> List[Dict[str, Any]]:
    path = _cashflow_file_path(ledger_id)
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, list):
            return sorted(raw, key=lambda x: str(x.get("date", "")), reverse=True)
    except Exception:
        pass
    return []


def _save_ledger_cashflows(ledger_id: str, records: List[Dict[str, Any]]) -> None:
    path = _cashflow_file_path(ledger_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def append_ledger_cashflow(
    ledger_id: str,
    tx_date: str,
    tx_type: str,
    amount: float,
    fund_code: str = "",
    fund_name: str = "",
    note: str = "",
) -> Dict[str, Any]:
    """写入单条真实交易流水（BUY/DEPOSIT=入金负现金流；SELL/WITHDRAW/DIVIDEND=出金/分红正现金流）。"""
    clean_type = str(tx_type or "BUY").upper().strip()
    if clean_type not in ("BUY", "SELL", "DIVIDEND", "DEPOSIT", "WITHDRAW"):
        raise ValueError(f"Unsupported tx_type: {clean_type}")
    amt = abs(float(amount))
    if amt <= 0.0:
        raise ValueError("Amount must be > 0")
    dt_str = _parse_date_safe(tx_date).strftime("%Y-%m-%d")
    rec = {
        "id": f"cf_{uuid.uuid4().hex[:10]}",
        "date": dt_str,
        "tx_type": clean_type,
        "amount": round(amt, 2),
        "signed_cashflow": round(-amt if clean_type in ("BUY", "DEPOSIT") else amt, 2),
        "fund_code": str(fund_code or "").strip().zfill(6) if str(fund_code or "").strip().isdigit() else str(fund_code or "").strip(),
        "fund_name": str(fund_name or "").strip(),
        "note": str(note or "").strip(),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    records = load_ledger_cashflows(ledger_id)
    records.append(rec)
    records.sort(key=lambda x: (str(x.get("date", "")), str(x.get("created_at", ""))), reverse=True)
    _save_ledger_cashflows(ledger_id, records)
    return rec


def delete_ledger_cashflow(ledger_id: str, record_id: str) -> bool:
    records = load_ledger_cashflows(ledger_id)
    next_recs = [r for r in records if str(r.get("id", "")) != str(record_id)]
    if len(next_recs) == len(records):
        return False
    _save_ledger_cashflows(ledger_id, next_recs)
    return True


def summarize_ledger_xirr(
    ledger_id: str,
    holdings: Dict[str, Any],
    total_equity: float,
    available_cash: float = 0.0,
    as_of_date: Optional[date] = None,
) -> Dict[str, Any]:
    """
    汇总当前账本的资金加权年化 XIRR 与交易流水：
    - 优先使用用户实录的真实买卖/分红流水计算精准 XIRR；
    - 尚无手工流水时，自动从持仓批次与持有天数推算估算 XIRR，并明文标注来源。
    """
    today_d = as_of_date or date.today()
    records = load_ledger_cashflows(ledger_id)
    eq = max(0.0, _safe_float(total_equity, 0.0))
    cash = max(0.0, _safe_float(available_cash, 0.0))

    if records:
        cf_pairs: List[Tuple[date, float]] = []
        tot_in = 0.0
        tot_out = 0.0
        for r in records:
            dt = _parse_date_safe(r.get("date"), today_d)
            signed = _safe_float(r.get("signed_cashflow"), 0.0)
            if signed == 0.0:
                amt = abs(_safe_float(r.get("amount"), 0.0))
                signed = -amt if str(r.get("tx_type", "")).upper() in ("BUY", "DEPOSIT") else amt
            cf_pairs.append((dt, signed))
            if signed < 0:
                tot_in += -signed
            else:
                tot_out += signed
        cf_pairs.append((today_d, eq))
        xirr_dec = compute_xirr(cf_pairs)
        net_in = max(0.0, tot_in - tot_out)
        net_profit = round(eq + tot_out - tot_in, 2)
        simple_pct = round((net_profit / tot_in * 100.0) if tot_in > 0 else 0.0, 2)
        return {
            "ledger_id": ledger_id,
            "xirr_pct": round(xirr_dec * 100.0, 2) if xirr_dec is not None else None,
            "simple_return_pct": simple_pct,
            "total_invested": round(tot_in, 2),
            "total_withdrawn": round(tot_out, 2),
            "net_invested": round(net_in, 2),
            "current_equity": round(eq, 2),
            "net_profit": net_profit,
            "is_estimated": False,
            "source_label": f"基于 {len(records)} 笔实录交易流水精准核算",
            "record_count": len(records),
            "records": records[:50],
        }

    # 无手工流水时，自动基于持仓批次/买入日期与成本基数推算估算 XIRR
    cf_pairs = []
    tot_cost = 0.0
    tot_mv = 0.0
    for code, h in (holdings or {}).items():
        sh = _safe_float(getattr(h, "shares", 0.0) if not isinstance(h, dict) else h.get("shares", 0.0), 0.0)
        nav = _safe_float(getattr(h, "current_nav", 1.0) if not isinstance(h, dict) else h.get("current_nav", 1.0), 1.0)
        cost = _safe_float(getattr(h, "cost_price", nav) if not isinstance(h, dict) else h.get("cost_price", nav), nav)
        mv = sh * nav
        cb = sh * cost
        if cb <= 0.01:
            continue
        tot_cost += cb
        tot_mv += mv
        batches = getattr(h, "batches", None) if not isinstance(h, dict) else h.get("batches")
        if batches and isinstance(batches, list):
            for b in batches:
                b_sh = _safe_float(getattr(b, "shares", 0.0) if not isinstance(b, dict) else b.get("shares", 0.0), 0.0)
                b_nav = _safe_float(getattr(b, "cost_nav", cost) if not isinstance(b, dict) else b.get("cost_nav", cost), cost)
                b_dt = _parse_date_safe(getattr(b, "buy_date", "") if not isinstance(b, dict) else b.get("buy_date", ""), today_d - timedelta(days=90))
                if b_sh * b_nav > 0.01:
                    cf_pairs.append((b_dt, -(b_sh * b_nav)))
        else:
            h_days = max(7, int(_safe_float(getattr(h, "holding_days", 90) if not isinstance(h, dict) else h.get("holding_days", 90), 90)))
            f_dt_raw = getattr(h, "first_buy_date", "") if not isinstance(h, dict) else h.get("first_buy_date", "")
            b_dt = _parse_date_safe(f_dt_raw, today_d - timedelta(days=h_days))
            if (today_d - b_dt).days < 1:
                b_dt = today_d - timedelta(days=max(h_days, 7))
            cf_pairs.append((b_dt, -cb))

    if cash > 0.01 and cf_pairs:
        earliest = min(d for d, _ in cf_pairs)
        cf_pairs.append((earliest, -cash))
        tot_cost += cash

    terminal_val = eq if eq > 0 else (tot_mv + cash)
    if cf_pairs and terminal_val > 0:
        cf_pairs.append((today_d, terminal_val))
    xirr_dec = compute_xirr(cf_pairs) if len(cf_pairs) >= 2 else None
    net_profit = round(terminal_val - tot_cost, 2)
    simple_pct = round((net_profit / tot_cost * 100.0) if tot_cost > 0 else 0.0, 2)
    return {
        "ledger_id": ledger_id,
        "xirr_pct": round(xirr_dec * 100.0, 2) if xirr_dec is not None else None,
        "simple_return_pct": simple_pct,
        "total_invested": round(tot_cost, 2),
        "total_withdrawn": 0.0,
        "net_invested": round(tot_cost, 2),
        "current_equity": round(terminal_val, 2),
        "net_profit": net_profit,
        "is_estimated": True,
        "source_label": "基于持仓建仓批次推算（记入真实流水后更精准）",
        "record_count": 0,
        "records": [],
    }


# =====================================================================
# 2. Holding-Level 3-Stage Trailing Take-Profit & Protect-Gains Radar
# =====================================================================

def evaluate_holding_take_profit_radar(
    holdings: Dict[str, Any],
    nav_matrix: Optional[pd.DataFrame] = None,
    target_profit_pct: float = 15.0,
    trailing_dd_pct: float = 4.5,
) -> Dict[str, Dict[str, Any]]:
    """
    持仓级移动止盈与守果雷达：
    监控每只持仓的累计浮盈、建仓以来阶段高点回撤与 7 日赎回费红线，
    在盈利达标且高位回撤触发移动止盈线时明确提示分批落袋至中短债安全垫。
    """
    out: Dict[str, Dict[str, Any]] = {}
    today_d = date.today()
    tgt = max(3.0, float(target_profit_pct or 15.0))
    dd_th = max(1.5, float(trailing_dd_pct or 4.5))

    for code, h in (holdings or {}).items():
        code_s = str(code).strip().zfill(6)
        sh = _safe_float(getattr(h, "shares", 0.0) if not isinstance(h, dict) else h.get("shares", 0.0), 0.0)
        nav = _safe_float(getattr(h, "current_nav", 1.0) if not isinstance(h, dict) else h.get("current_nav", 1.0), 1.0)
        cost = _safe_float(getattr(h, "cost_price", nav) if not isinstance(h, dict) else h.get("cost_price", nav), nav)
        h_days = int(_safe_float(getattr(h, "holding_days", 30) if not isinstance(h, dict) else h.get("holding_days", 30), 30))
        mv = sh * nav
        pnl_pct = ((nav / cost - 1.0) * 100.0) if cost > 1e-6 else 0.0

        # 从本地真净值湖仓测算建仓以来的阶段最高净值（按相对涨跌幅对齐现价，规避复权/单位净值口径差）
        peak_nav = max(nav, cost)
        if nav_matrix is not None and not nav_matrix.empty and code_s in nav_matrix.columns:
            try:
                s = nav_matrix[code_s].dropna()
                if len(s) >= 5:
                    f_raw = getattr(h, "first_buy_date", "") if not isinstance(h, dict) else h.get("first_buy_date", "")
                    start_dt = _parse_date_safe(f_raw, today_d - timedelta(days=min(max(h_days, 14), 365)))
                    sub = s[s.index >= pd.Timestamp(start_dt)]
                    if len(sub) < 3:
                        sub = s.tail(min(len(s), max(10, int(h_days * 0.7))))
                    last_adj = float(sub.iloc[-1])
                    max_adj = float(sub.max())
                    if last_adj > 1e-6 and max_adj >= last_adj:
                        est_peak = nav * (max_adj / last_adj)
                        peak_nav = max(peak_nav, est_peak)
            except Exception:
                pass

        dd_from_peak_pct = round(((nav / max(peak_nav, 1e-6)) - 1.0) * 100.0, 2) if peak_nav > 0 else 0.0

        if h_days < 7:
            status = "HOLD_PENALTY"
            label = "未满7天禁赎"
            tone = "danger"
            action_tip = f"持有仅 {h_days} 天，赎回将触发 1.5% 惩罚性费用，请务必满 7 天后再操作。"
            suggested_redeem_ratio = 0.0
        elif pnl_pct >= tgt and abs(dd_from_peak_pct) >= dd_th and mv >= 200.0:
            status = "LOCK_PARTIAL"
            label = "触发移动止盈"
            tone = "profit_lock"
            lock_amt = round(mv / 3.0, 2)
            action_tip = (
                f"浮盈 +{pnl_pct:.1f}% 且自阶段高点回撤 {dd_from_peak_pct:.1f}%（超 -{dd_th:.1f}% 警戒线），"
                f"建议落袋 1/3（约 ¥{lock_amt:,.0f}）转入中短债现金垫锁定胜果。"
            )
            suggested_redeem_ratio = 0.33
        elif pnl_pct >= tgt and mv >= 200.0:
            status = "TARGET_REACHED"
            label = "达标追踪中"
            tone = "profit_watch"
            action_tip = (
                f"浮盈已达 +{pnl_pct:.1f}%（超 +{tgt:.0f}% 目标线），当前距高点回撤仅 {abs(dd_from_peak_pct):.1f}%，"
                f"继续持有让利润奔跑；若回撤扩大至 -{dd_th:.1f}% 即分批落袋。"
            )
            suggested_redeem_ratio = 0.0
        elif pnl_pct <= -10.0 and mv >= 200.0:
            status = "DEEP_VALUE_ZONE"
            label = "深套勿割"
            tone = "caution"
            action_tip = f"当前浮亏 {pnl_pct:.1f}%，切忌恐慌割肉；若符合核心配置方向，建议结合新增定投分批摊薄成本。"
            suggested_redeem_ratio = 0.0
        else:
            status = "NORMAL"
            label = "稳健持有"
            tone = "neutral"
            action_tip = "处于常规持有波动区间，保持纪律持有。"
            suggested_redeem_ratio = 0.0

        out[code_s] = {
            "status": status,
            "label": label,
            "tone": tone,
            "floating_pnl_pct": round(pnl_pct, 2),
            "peak_nav": round(peak_nav, 4),
            "drawdown_from_peak_pct": dd_from_peak_pct,
            "target_profit_pct": tgt,
            "trailing_dd_pct": dd_th,
            "suggested_redeem_ratio": suggested_redeem_ratio,
            "action_tip": action_tip,
        }
    return out


# =====================================================================
# 3. Smart Staged Entry Plan Wizard (Adopt QuantLab Blueprint)
# =====================================================================

def build_staged_entry_plan(
    items: List[Dict[str, Any]],
    total_amount: float,
    horizon_months: int = 24,
    mode: str = "smart_3_tranche",
    market_regime: str = "",
) -> Dict[str, Any]:
    """
    将量化实验室推荐方案转化为可直接在银行/支付宝/天天基金执行的分批建仓计划：
      - smart_3_tranche（默认）：40% / 30% / 30% 三批建仓，短线偏热标的（bias_20 > 3.5%）自动压降首笔至 25%；
      - dca_4_week：25% × 4 周均分定投；
      - lump_sum：100% 一次性建仓。
    """
    cap = max(1000.0, _safe_float(total_amount, 50000.0))
    h_mon = max(3, min(60, int(horizon_months or 24)))
    clean_mode = str(mode or "smart_3_tranche").strip().lower()
    if clean_mode not in ("smart_3_tranche", "dca_4_week", "lump_sum"):
        clean_mode = "smart_3_tranche"

    if clean_mode == "lump_sum":
        tranche_specs = [
            {"index": 1, "title": "第 1 批 · 一次性到位", "trigger": "今日 15:00 前完成全部申购（次交易日确认份额）", "base_ratio": 1.0},
        ]
        mode_label = "一次性到位建仓（100%）"
    elif clean_mode == "dca_4_week":
        tranche_specs = [
            {"index": 1, "title": "第 1 周 · 首笔定投 (25%)", "trigger": "本周交易日 14:30~14:55 买入首笔", "base_ratio": 0.25},
            {"index": 2, "title": "第 2 周 · 常规加码 (25%)", "trigger": "间隔 1 周（或期间单日大跌 >1.5% 提前打出）", "base_ratio": 0.25},
            {"index": 3, "title": "第 3 周 · 中段摊薄 (25%)", "trigger": "间隔 2 周按纪律定投", "base_ratio": 0.25},
            {"index": 4, "title": "第 4 周 · 尾笔收官 (25%)", "trigger": "间隔 3 周完成全仓配置", "base_ratio": 0.25},
        ]
        mode_label = "4 周均分定投建仓（25% × 4）"
    else:
        tranche_specs = [
            {"index": 1, "title": "第 1 批 · 先建底仓 (40%)", "trigger": "今日 14:30~14:55 优先打入底仓防踏空（短线偏热基自动压降至 25%）", "base_ratio": 0.40},
            {"index": 2, "title": "第 2 批 · 回调/双周加码 (30%)", "trigger": "2 周后或沪深 300 回调 ≥ -3% 时提前触发", "base_ratio": 0.30},
            {"index": 3, "title": "第 3 批 · 黄金坑收官 (30%)", "trigger": "4 周后或沪深 300 回调 ≥ -6% 时全部打完", "base_ratio": 0.30},
        ]
        mode_label = "智能三批建仓（40% / 30% / 30% · 偏热自动降首笔）"

    valid_items = [it for it in (items or []) if _safe_float(it.get("weight_pct"), 0.0) > 0]
    w_sum = sum(_safe_float(it.get("weight_pct"), 0.0) for it in valid_items) or 100.0

    tranches_out: List[Dict[str, Any]] = [
        {"index": ts["index"], "title": ts["title"], "trigger": ts["trigger"], "subtotal": 0.0, "orders": []}
        for ts in tranche_specs
    ]
    hot_throttled_codes: List[str] = []
    quota_split_codes: List[str] = []

    for it in valid_items:
        code = str(it.get("fund_code") or "").strip().zfill(6)
        name = str(it.get("fund_name") or code)
        w_pct = _safe_float(it.get("weight_pct"), 0.0)
        fund_total = round(cap * (w_pct / w_sum), 2)
        bias20 = it.get("bias_20")
        is_hot = bias20 is not None and _safe_float(bias20, 0.0) > 3.5
        d_lim = _safe_float(it.get("daily_limit"), 1e10)
        c_code = it.get("c_share_code")
        use_c_hint = (h_mon <= 12) and bool(c_code) and (str(c_code) != code)

        if clean_mode == "smart_3_tranche" and is_hot:
            ratios = [0.25, 0.35, 0.40]
            hot_throttled_codes.append(code)
        else:
            ratios = [ts["base_ratio"] for ts in tranche_specs]

        rem = fund_total
        for idx, ratio in enumerate(ratios):
            amt = round(rem, 2) if idx == len(ratios) - 1 else round(fund_total * ratio, 2)
            rem = max(0.0, rem - amt)
            split_days = int(math.ceil(amt / d_lim)) if (0 < d_lim < amt) else 1
            if split_days > 1 and code not in quota_split_codes:
                quota_split_codes.append(code)
            tranches_out[idx]["subtotal"] = round(tranches_out[idx]["subtotal"] + amt, 2)
            tranches_out[idx]["orders"].append({
                "fund_code": code,
                "fund_name": name,
                "bucket_label": str(it.get("bucket_label") or it.get("role") or ""),
                "amount": amt,
                "tranche_ratio_pct": round(ratio * 100.0, 0),
                "daily_limit": d_lim,
                "split_days": split_days,
                "is_hot_throttled": bool(clean_mode == "smart_3_tranche" and is_hot),
                "c_share_code": str(c_code) if use_c_hint else None,
                "execution_note": (
                    f"单日限购 ¥{int(d_lim):,}，需分 {split_days} 日定投买完"
                    if split_days > 1
                    else ("短线偏热已降首笔至 25% 防追高" if (clean_mode == "smart_3_tranche" and is_hot and idx == 0) else "不限购，14:30~14:55 执行")
                ),
            })

    lines = [
        f"【AGY2 场外基金分批建仓执行清单】总本金 ¥{cap:,.0f}｜计划持有 {h_mon} 个月｜{mode_label}",
        f"当前市场温度：{market_regime or '均衡观察'}（银行/支付宝/天天基金 15:00 前下单按当日净值确认）",
        "",
    ]
    for tr in tranches_out:
        lines.append(f"■ {tr['title']}（合计 ¥{tr['subtotal']:,.2f}）— {tr['trigger']}")
        for od in tr["orders"]:
            c_txt = f" [≤1年省费可选 C 类 {od['c_share_code']}]" if od["c_share_code"] else ""
            lim_txt = f" [限购分 {od['split_days']} 日]" if od["split_days"] > 1 else ""
            lines.append(f"  - {od['fund_code']} {od['fund_name']}：买入 ¥{od['amount']:,.2f}{c_txt}{lim_txt}")
        lines.append("")

    return {
        "mode": clean_mode,
        "mode_label": mode_label,
        "total_amount": round(cap, 2),
        "horizon_months": h_mon,
        "fund_count": len(valid_items),
        "hot_throttled_count": len(hot_throttled_codes),
        "quota_split_count": len(quota_split_codes),
        "tranches": tranches_out,
        "copyable_checklist_text": "\n".join(lines).strip(),
    }


# =====================================================================
# 4. 14:30 Cutoff Quick-Action Brief (Reusing TradingClock)
# =====================================================================

def build_cutoff_quick_brief(
    holdings_rows: List[Dict[str, Any]],
    rebalance_summary: Optional[Dict[str, Any]] = None,
    market_verdict: Optional[Dict[str, Any]] = None,
    now_dt: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    复用 TradingClock 生成 14:30 尾盘实盘速决卡：
    聚合当前北京 15:00 申赎生死线状态、生效成交日与 Top 3 最紧急实盘动作。
    """
    clock = TradingClock()
    win = clock.get_market_window_status(now_dt=now_dt)

    priority_actions: List[Dict[str, Any]] = []
    profit_lock_count = 0
    penalty_lock_count = 0

    for row in holdings_rows or []:
        tp = row.get("take_profit") or {}
        st = str(tp.get("status", "NORMAL"))
        if st == "LOCK_PARTIAL":
            profit_lock_count += 1
            priority_actions.append({
                "priority": 1,
                "tag": "移动止盈落袋",
                "tone": "profit_lock",
                "fund_code": str(row.get("fund_code", "")),
                "fund_name": str(row.get("fund_name", "")),
                "summary": str(tp.get("action_tip", "触发移动止盈，建议落袋 1/3 转入中短债安全垫")),
            })
        elif st == "HOLD_PENALTY":
            penalty_lock_count += 1

    reb = rebalance_summary or {}
    for c_item in (reb.get("c_replace") or {}).get("items", [])[:1]:
        priority_actions.append({
            "priority": 2,
            "tag": "C转A省费",
            "tone": "info",
            "fund_code": str(c_item.get("fund_code", "")),
            "fund_name": str(c_item.get("fund_name", "")),
            "summary": str(c_item.get("reason") or "已满 30 天免赎回费，建议置换同款 A 类省年化销售服务费"),
        })

    for core_item in (reb.get("core_trades") or {}).get("items", [])[:2]:
        amt = _safe_float(core_item.get("diff_amount", core_item.get("amount", 0.0)), 0.0)
        act_lbl = f"买入 ¥{abs(amt):,.0f}" if amt > 0 else f"减仓 ¥{abs(amt):,.0f}"
        priority_actions.append({
            "priority": 3,
            "tag": "核心调仓",
            "tone": "buy" if amt > 0 else "sell",
            "fund_code": str(core_item.get("fund_code", "")),
            "fund_name": str(core_item.get("fund_name", "")),
            "summary": f"{act_lbl} · {str(core_item.get('reason') or '对齐量化目标权重')}",
        })

    tail_cnt = int((reb.get("tail_sweep") or {}).get("count", 0) or 0)
    if tail_cnt > 0 and len(priority_actions) < 3:
        tail_cash = _safe_float((reb.get("tail_sweep") or {}).get("recovered_cash", 0.0), 0.0)
        priority_actions.append({
            "priority": 4,
            "tag": "尾仓归拢",
            "tone": "caution",
            "fund_code": "",
            "fund_name": f"{tail_cnt} 只碎片尾仓",
            "summary": f"可一次性清仓归拢回收 ¥{tail_cash:,.2f}（均满 7 天免惩罚费）",
        })

    priority_actions.sort(key=lambda x: int(x.get("priority", 9)))
    clean_title = re.sub(r"^[^\u4e00-\u9fffA-Za-z0-9]+", "", str(win.title or "")).strip()

    return {
        "window_type": win.window_type,
        "window_label": clean_title or "交易窗口状态",
        "message": win.message,
        "is_trade_day": bool(win.is_trade_day),
        "is_golden_window": bool(win.is_golden_window),
        "is_after_market": bool(win.is_after_market),
        "current_time_str": win.current_time_str,
        "seconds_to_close": int(round(max(0.0, win.seconds_to_close))),
        "countdown_str": win.countdown_str,
        "effective_trade_date": win.effective_trade_date,
        "market_verdict_label": str((market_verdict or {}).get("short_label") or ""),
        "profit_lock_count": profit_lock_count,
        "penalty_lock_count": penalty_lock_count,
        "priority_actions": priority_actions[:3],
    }
