# -*- coding: utf-8 -*-
"""
AGY2 Shadow Portfolio Tracker (G29 真实跟单 vs 原始躺平影子账本实盘赛跑独立子模块)
=============================================================================
负责在组合瘦身（如 29 只瘦身为 6 只）或用户手动锁定基准时，将原始持仓切片
不可变冻结，并每日基于相同真实行情计算实盘超额收益（元与百分比）。
严格控制在 350 行以内，杜绝主文件巨石膨胀。
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from runtime_paths import get_data_dir

_DEFAULT_BENCHMARK_FILE = get_data_dir() / "shadow_benchmarks.json"
_DEFAULT_BASELINE_DIR = get_data_dir() / "frozen_shadow_baselines"
BENCHMARK_FILE = _DEFAULT_BENCHMARK_FILE
BASELINE_DIR = _DEFAULT_BASELINE_DIR


def _resolve_benchmark_file() -> Path:
    return BENCHMARK_FILE if BENCHMARK_FILE != _DEFAULT_BENCHMARK_FILE else (get_data_dir() / "shadow_benchmarks.json")


def _resolve_baseline_dir() -> Path:
    return BASELINE_DIR if BASELINE_DIR != _DEFAULT_BASELINE_DIR else (get_data_dir() / "frozen_shadow_baselines")


def _ensure_dir() -> None:
    _resolve_benchmark_file().parent.mkdir(parents=True, exist_ok=True)
    _resolve_baseline_dir().mkdir(parents=True, exist_ok=True)


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


def _resolve_holding_nav(h: Any) -> float:
    for field in ("current_nav", "latest_nav", "nav", "unit_nav", "cost_price"):
        v = _read_pos_float(h, field)
        if v is not None:
            return v
    mv = _read_pos_float(h, "market_value")
    sh = _read_pos_float(h, "shares")
    if mv is not None and sh is not None and sh > 0.0:
        return round(mv / sh, 4)
    return 1.0


def freeze_shadow_baseline(
    ledger_id: str,
    holdings_dict: Dict[str, Any],
    baseline_name: str = "原始29只躺平不动基准线",
) -> Path:
    """
    冻结保存原始持仓切片（只读不可篡改）
    """
    _ensure_dir()
    frozen_date = datetime.now().strftime("%Y-%m-%d")
    frozen_items = {}
    init_total_val = 0.0

    for code, h in holdings_dict.items():
        sh = float(getattr(h, "shares", 0.0) if hasattr(h, "shares") else h.get("shares", 0.0))
        nav = _resolve_holding_nav(h)
        cost = _read_pos_float(h, "cost_price") or nav
        fname = str(getattr(h, "fund_name", code) if hasattr(h, "fund_name") else h.get("fund_name", code))
        s_class = str(getattr(h, "share_class", "A") if hasattr(h, "share_class") else h.get("share_class", "A"))

        direct_mv = _read_pos_float(h, "market_value")
        mv = round(sh * nav, 2) if sh > 0.0 else round(direct_mv or 0.0, 2)
        init_total_val += mv
        frozen_items[str(code)] = {
            "fund_code": str(code),
            "fund_name": fname,
            "share_class": s_class,
            "frozen_shares": sh,
            "frozen_nav": nav,
            "cost_price": cost,
            "frozen_market_value": mv,
        }

    payload = {
        "ledger_id": str(ledger_id),
        "baseline_name": baseline_name,
        "frozen_date": frozen_date,
        "frozen_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "initial_total_market_value": round(init_total_val, 2),
        "holdings_count": len(frozen_items),
        "holdings": frozen_items,
    }

    # 1. 写入独立专属文件
    spec_path = _resolve_baseline_dir() / f"{ledger_id}_baseline.json"
    with open(spec_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    # 2. 同步写入总索引文件
    all_benchmarks = {}
    bm_file = _resolve_benchmark_file()
    if bm_file.exists():
        try:
            with open(bm_file, "r", encoding="utf-8") as f:
                all_benchmarks = json.load(f)
        except Exception:
            all_benchmarks = {}
    all_benchmarks[str(ledger_id)] = payload
    with open(bm_file, "w", encoding="utf-8") as f:
        json.dump(all_benchmarks, f, ensure_ascii=False, indent=2)

    return spec_path


def get_shadow_baseline(ledger_id: str) -> Optional[Dict[str, Any]]:
    """读取指定账本的冻结躺平基准"""
    spec_path = _resolve_baseline_dir() / f"{ledger_id}_baseline.json"
    if spec_path.exists():
        try:
            with open(spec_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    bm_file = _resolve_benchmark_file()
    if bm_file.exists():
        try:
            with open(bm_file, "r", encoding="utf-8") as f:
                all_b = json.load(f)
            return all_b.get(str(ledger_id))
        except Exception:
            pass
    return None


load_frozen_shadow_baseline = get_shadow_baseline


def compare_live_vs_shadow(
    ledger_id: str,
    live_holdings: Dict[str, Any],
    quotes_or_nav_map: Dict[str, Any],
) -> Dict[str, Any]:
    """
    使用同一套最新真实行情，计算实盘调仓相对原始躺平影子组合的超额收益
    """
    baseline = get_shadow_baseline(ledger_id)
    if not baseline or not baseline.get("holdings"):
        return {
            "has_shadow": False,
            "has_baseline": False,
            "ledger_id": ledger_id,
            "message": f"账本 [{ledger_id}] 尚未冻结原始躺平基准线，可点击上方「冻结基准」按钮建立对照。",
        }

    quotes = quotes_or_nav_map or {}

    # 提取行情字典辅助函数：缺失行情返回 None，严禁伪造 1.0 净值！
    def _extract_nav(c: str) -> Optional[float]:
        q = quotes.get(c)
        if q is None:
            q = quotes.get(str(c))
        if q is None:
            return None
        if isinstance(q, (int, float)):
            v = float(q)
            return v if v > 0.001 else None
        for k in ("official_nav", "gsz", "dwjz", "current_nav", "latest_nav", "nav", "unit_nav"):
            v = _read_pos_float(q, k)
            if v is not None and v > 0.001:
                return v
        return None

    # 1. 影子躺平持仓当前价值核算
    shadow_h = baseline.get("holdings", {})
    init_shadow_mv = float(baseline.get("initial_total_market_value", 0.0))
    curr_shadow_mv = 0.0
    missing_quote_codes: List[str] = []

    for code, item in shadow_h.items():
        c_nav = _extract_nav(code)
        f_sh = float(item.get("frozen_shares", 0.0) or 0.0)
        if c_nav is None or c_nav <= 0.001:
            missing_quote_codes.append(str(code))
            c_nav = float(item.get("frozen_nav", 0.0) or 0.0)
            if c_nav <= 0.001 and f_sh > 0.0:
                f_mv = float(item.get("frozen_market_value", 0.0) or 0.0)
                c_nav = (f_mv / f_sh) if f_mv > 0.0 else 1.0
        curr_shadow_mv += f_sh * c_nav

    shadow_ret_pct = 0.0
    if init_shadow_mv > 0.01:
        shadow_ret_pct = (curr_shadow_mv - init_shadow_mv) / init_shadow_mv * 100.0

    # 2. 实盘跟单持仓当前价值核算
    curr_live_mv = 0.0
    init_live_cost = 0.0
    for code, h in (live_holdings or {}).items():
        sh = float(getattr(h, "shares", 0.0) if hasattr(h, "shares") else h.get("shares", 0.0))
        h_nav = _resolve_holding_nav(h)
        cost = _read_pos_float(h, "cost_price") or h_nav
        c_nav = _extract_nav(code)
        if c_nav is None or c_nav <= 0.001:
            c_nav = h_nav
        curr_live_mv += sh * c_nav
        cost_basis = _read_pos_float(h, "cost_basis")
        init_live_cost += cost_basis if cost_basis is not None else (sh * cost)

    live_ret_pct = 0.0
    if init_live_cost > 0.01:
        live_ret_pct = (curr_live_mv - init_live_cost) / init_live_cost * 100.0

    # 3. 超额与比较指标
    excess_rmb = round(curr_live_mv - curr_shadow_mv, 2)
    excess_ret_pct = round(live_ret_pct - shadow_ret_pct, 2)

    return {
        "has_shadow": True,
        "has_baseline": True,
        "ledger_id": ledger_id,
        "frozen_date": baseline.get("frozen_date", ""),
        "shadow_count": baseline.get("holdings_count", len(shadow_h)),
        "live_count": len(live_holdings or {}),
        "shadow_initial_equity": round(init_shadow_mv, 2),
        "shadow_current_equity": round(curr_shadow_mv, 2),
        "shadow_return_pct": round(shadow_ret_pct, 2),
        "live_current_equity": round(curr_live_mv, 2),
        "live_cost_basis": round(init_live_cost, 2),
        "live_return_pct": round(live_ret_pct, 2),
        "excess_rmb": excess_rmb,
        "excess_return_pct": excess_ret_pct,
        "is_outperforming": excess_rmb >= 0,
        "missing_quote_codes": missing_quote_codes,
        "status_badge": "🟢 实盘跑赢躺平" if excess_rmb >= 0 else "🟡 暂时受摩擦拖累",
    }


class ShadowPortfolioTracker:
    """面向对象的影子账本追踪器"""
    @staticmethod
    def freeze_baseline(ledger_id: str, holdings: Dict[str, Any], name: str = "原始躺平基准线") -> Path:
        return freeze_shadow_baseline(ledger_id, holdings, name)

    @staticmethod
    def get_baseline(ledger_id: str) -> Optional[Dict[str, Any]]:
        return get_shadow_baseline(ledger_id)

    @staticmethod
    def compare(ledger_id: str, live_holdings: Dict[str, Any], quotes: Dict[str, Any]) -> Dict[str, Any]:
        return compare_live_vs_shadow(ledger_id, live_holdings, quotes)
