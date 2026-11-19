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
from typing import Dict, Any, Optional

BENCHMARK_FILE = Path("data/shadow_benchmarks.json")
BASELINE_DIR = Path("data/frozen_shadow_baselines")


def _ensure_dir() -> None:
    BENCHMARK_FILE.parent.mkdir(parents=True, exist_ok=True)
    BASELINE_DIR.mkdir(parents=True, exist_ok=True)


def freeze_shadow_baseline(
    ledger_id: str,
    holdings_dict: Dict[str, Any],
    baseline_name: str = "原始29只躺平不动基准线"
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
        nav = float(getattr(h, "current_nav", 1.0) if hasattr(h, "current_nav") else h.get("current_nav", 1.0))
        cost = float(getattr(h, "cost_price", nav) if hasattr(h, "cost_price") else h.get("cost_price", nav))
        fname = str(getattr(h, "fund_name", code) if hasattr(h, "fund_name") else h.get("fund_name", code))
        s_class = str(getattr(h, "share_class", "A") if hasattr(h, "share_class") else h.get("share_class", "A"))

        mv = round(sh * nav, 2)
        init_total_val += mv
        frozen_items[str(code)] = {
            "fund_code": str(code),
            "fund_name": fname,
            "share_class": s_class,
            "frozen_shares": sh,
            "frozen_nav": nav,
            "cost_price": cost,
            "frozen_market_value": mv
        }

    payload = {
        "ledger_id": str(ledger_id),
        "baseline_name": baseline_name,
        "frozen_date": frozen_date,
        "frozen_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "initial_total_market_value": round(init_total_val, 2),
        "holdings_count": len(frozen_items),
        "holdings": frozen_items
    }

    # 1. 写入独立专属文件
    spec_path = BASELINE_DIR / f"{ledger_id}_baseline.json"
    with open(spec_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    # 2. 同步写入总索引文件
    all_benchmarks = {}
    if BENCHMARK_FILE.exists():
        try:
            with open(BENCHMARK_FILE, "r", encoding="utf-8") as f:
                all_benchmarks = json.load(f)
        except Exception:
            all_benchmarks = {}
    all_benchmarks[str(ledger_id)] = payload
    with open(BENCHMARK_FILE, "w", encoding="utf-8") as f:
        json.dump(all_benchmarks, f, ensure_ascii=False, indent=2)

    return spec_path


def get_shadow_baseline(ledger_id: str) -> Optional[Dict[str, Any]]:
    """读取指定账本的冻结躺平基准"""
    spec_path = BASELINE_DIR / f"{ledger_id}_baseline.json"
    if spec_path.exists():
        try:
            with open(spec_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    if BENCHMARK_FILE.exists():
        try:
            with open(BENCHMARK_FILE, "r", encoding="utf-8") as f:
                all_b = json.load(f)
            return all_b.get(str(ledger_id))
        except Exception:
            pass
    return None


def compare_live_vs_shadow(
    ledger_id: str,
    live_holdings: Dict[str, Any],
    quotes_or_nav_map: Dict[str, Any]
) -> Dict[str, Any]:
    """
    使用同一套最新真实行情，计算实盘调仓相对原始躺平影子组合的超额收益
    """
    baseline = get_shadow_baseline(ledger_id)
    if not baseline or not baseline.get("holdings"):
        return {
            "has_shadow": False,
            "message": f"账本 [{ledger_id}] 尚未冻结原始躺平基准线，可点击上方「冻结基准」按钮建立对照。"
        }

    # 提取行情字典辅助函数
    def _extract_nav(c: str) -> float:
        q = quotes_or_nav_map.get(c)
        if q is None:
            return 1.0
        if isinstance(q, (int, float)):
            return float(q)
        if isinstance(q, dict):
            return float(q.get("official_nav") or q.get("gsz") or q.get("dwjz") or 1.0)
        return float(getattr(q, "official_nav", None) or getattr(q, "gsz", None) or getattr(q, "dwjz", 1.0))

    # 1. 影子躺平持仓当前价值核算
    shadow_h = baseline.get("holdings", {})
    init_shadow_mv = float(baseline.get("initial_total_market_value", 0.0))
    curr_shadow_mv = 0.0

    for code, item in shadow_h.items():
        c_nav = _extract_nav(code)
        if c_nav <= 0.001:
            c_nav = float(item.get("frozen_nav", 1.0))
        curr_shadow_mv += float(item.get("frozen_shares", 0.0)) * c_nav

    shadow_ret_pct = 0.0
    if init_shadow_mv > 0.01:
        shadow_ret_pct = (curr_shadow_mv - init_shadow_mv) / init_shadow_mv * 100.0

    # 2. 实盘跟单持仓当前价值核算
    curr_live_mv = 0.0
    init_live_cost = 0.0
    for code, h in live_holdings.items():
        sh = float(getattr(h, "shares", 0.0) if hasattr(h, "shares") else h.get("shares", 0.0))
        cost = float(getattr(h, "cost_price", 1.0) if hasattr(h, "cost_price") else h.get("cost_price", 1.0))
        c_nav = _extract_nav(code)
        curr_live_mv += sh * c_nav
        init_live_cost += sh * cost

    live_ret_pct = 0.0
    if init_live_cost > 0.01:
        live_ret_pct = (curr_live_mv - init_live_cost) / init_live_cost * 100.0

    # 3. 超额与比较指标
    excess_rmb = round(curr_live_mv - curr_shadow_mv, 2)
    excess_ret_pct = round(live_ret_pct - shadow_ret_pct, 2)

    return {
        "has_shadow": True,
        "ledger_id": ledger_id,
        "frozen_date": baseline.get("frozen_date", ""),
        "shadow_count": baseline.get("holdings_count", len(shadow_h)),
        "live_count": len(live_holdings),
        "shadow_initial_equity": round(init_shadow_mv, 2),
        "shadow_current_equity": round(curr_shadow_mv, 2),
        "shadow_return_pct": round(shadow_ret_pct, 2),
        "live_current_equity": round(curr_live_mv, 2),
        "live_return_pct": round(live_ret_pct, 2),
        "excess_rmb": excess_rmb,
        "excess_return_pct": excess_ret_pct,
        "is_outperforming": excess_rmb >= 0,
        "status_badge": "🟢 实盘跑赢躺平" if excess_rmb >= 0 else "🟡 暂时受摩擦拖累"
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
