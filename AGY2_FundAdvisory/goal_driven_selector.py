# -*- coding: utf-8 -*-
"""
AGY2 目标驱动量化选基与调仓评估引擎 (Goal-Driven Multi-Factor Selector)
核心闭环：
  1. 接收用户的【目标收益率 (%)】+【目标持有周期 (月)】+【风险档位 (C1~C5)】+【配置模型】；
  2. 反推所需年化收益率，校验「收益预期 vs 风险承受力」是否存在碰撞；
  3. 并发调用 fund_detail_service 读取每只候选基金的真实 4 大类 + 8 小类量化指标、
     费率、规模与经理稳定性，动态计算多因子综合得分 (0~100) 并对权重做因子倾斜优化；
  4. 在真实历史净值序列上执行全历史滚动窗口回测，统计「在目标周期内达到目标收益的
     历史达成概率 (%)、平均达标耗时、中位收益与最差回撤」，同时支持「当前持仓 vs 调仓后」达成率对比。
"""

from __future__ import annotations

import math
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from fund_detail_service import get_fund_full_detail
from strategy_bridge import StrategyBridge, map_target_return_to_tier

_TIER_ORDER = {"C1": 1, "C2": 2, "C3": 3, "C4": 4, "C5": 5}
_TIER_MAX_REALISTIC_CAGR = {"C1": 5.5, "C2": 8.5, "C3": 12.0, "C4": 16.5, "C5": 22.0}


def _parse_num(val: Any, default: float = 0.0) -> float:
    if isinstance(val, (int, float)):
        return float(val)
    m = re.search(r"-?\d+(?:\.\d+)?", str(val or ""))
    return float(m.group(0)) if m else default


def _extract_fund_factor_profile(code: str, detail: Dict[str, Any], tier: str, req_cagr: float) -> Dict[str, Any]:
    """从基金详情真数据中提取多因子量化特征并按目标风格动态打分 (0~100)。"""
    analytics = detail.get("analytics") or {}
    cats = {c.get("key"): c for c in (analytics.get("categories") or []) if isinstance(c, dict)}
    sub = analytics.get("sub_metrics") or {}

    def _sub_val(grp: str, name_kw: str, default: float = 0.0) -> float:
        for it in (sub.get(grp) or []):
            if name_kw in str(it.get("name", "")):
                return _parse_num(it.get("value"), default)
        return default

    sharpe = _sub_val("cost_performance", "夏普", 0.5)
    calmar = _sub_val("cost_performance", "卡玛", 0.4)
    max_dd = abs(_sub_val("risk_control", "最大回撤", 15.0))
    ann_vol = abs(_sub_val("risk_control", "波动率", 14.0))
    new_high = _sub_val("return_ability", "新高率", 10.0)
    excess = _sub_val("return_ability", "超额", 0.0)
    ir = _sub_val("tracking_ability", "信息比率", 0.0)
    te = _sub_val("tracking_ability", "跟踪误差", 10.0)

    # 基金基本面因子：规模、费率、经理稳定性
    prof = detail.get("profile") or {}
    scale_yi = prof.get("scale_yi")
    rules = detail.get("trading_rules") or {}
    total_fee_pct = (
        _parse_num(rules.get("management_fee"), 0.5)
        + _parse_num(rules.get("custody_fee"), 0.1)
        + _parse_num(rules.get("sales_service_fee"), 0.0)
    )
    mgrs = detail.get("managers") or []
    cur_mgr_days = max((int(m.get("days", 0) or 0) for m in mgrs if m.get("is_current")), default=365)

    # 基础四维分
    s_ratio = float((cats.get("cost_perf") or {}).get("score", 62))
    s_down = float((cats.get("downside") or {}).get("score", 62))
    s_vol = float((cats.get("volatility") or {}).get("score", 62))
    s_track = float((cats.get("tracking") or {}).get("score", 62))

    # 基本面加减分（规模 >= 2亿、费率 <= 0.8%、经理任职 >= 2年加分；迷你基/高费减分）
    fund_bonus = 0.0
    if scale_yi is not None:
        if float(scale_yi) >= 5.0:
            fund_bonus += 3.0
        elif float(scale_yi) < 1.0:
            fund_bonus -= 5.0
    if total_fee_pct <= 0.65:
        fund_bonus += 3.0
    elif total_fee_pct >= 1.5:
        fund_bonus -= 4.0
    if cur_mgr_days >= 730:
        fund_bonus += 2.0

    # 按目标年化收益高低动态分配多因子权重
    if req_cagr <= 6.5 or tier in ("C1", "C2"):
        # 防御/稳健目标：重抗下跌、抗波动与夏普性价比
        composite = 0.35 * s_down + 0.25 * s_vol + 0.25 * s_ratio + 0.15 * s_track + fund_bonus
        style_note = "低波抗跌优先"
    elif req_cagr >= 13.0 or tier in ("C4", "C5"):
        # 高目标/进取：重卡玛性价比、净值新高率与超额收益弹性
        s_ret = float(np.clip(55.0 + new_high * 1.1 + excess * 0.6, 25.0, 96.0))
        composite = 0.35 * s_ret + 0.30 * s_ratio + 0.20 * s_down + 0.15 * s_track + fund_bonus
        style_note = "弹性与性价比优先"
    else:
        # 均衡目标：四维均衡
        composite = 0.30 * s_ratio + 0.28 * s_down + 0.22 * s_vol + 0.20 * s_track + fund_bonus
        style_note = "风险收益均衡"

    score = int(round(float(np.clip(composite, 30.0, 98.0))))
    return {
        "fund_code": code,
        "quant_score": score,
        "style_note": style_note,
        "sharpe": round(sharpe, 2),
        "calmar": round(calmar, 2),
        "max_dd_pct": round(max_dd, 2),
        "ann_vol_pct": round(ann_vol, 2),
        "new_high_rate_pct": round(new_high, 2),
        "excess_pct": round(excess, 2),
        "info_ratio": round(ir, 2),
        "tracking_error_pct": round(te, 2),
        "total_fee_pct": round(total_fee_pct, 2),
        "scale_yi": scale_yi,
        "mgr_days": cur_mgr_days,
    }


def score_and_tilt_weights_with_details(
    base_weights: Dict[str, float],
    tier: str,
    req_cagr: float,
) -> Tuple[Dict[str, float], Dict[str, Dict[str, Any]]]:
    """
    并发拉取候选基金详情数据，计算每只基金的多因子量化得分，
    并对基础权重实施温和的因子倾斜（±15% 内，保证不破坏大类风控纪律且权重和严格 = 1.0）。
    """
    codes = list(base_weights.keys())
    if not codes:
        return {}, {}

    profiles: Dict[str, Dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=min(6, len(codes))) as pool:
        futs = {pool.submit(get_fund_full_detail, c, 1000.0): c for c in codes}
        for fut, c in futs.items():
            try:
                det = fut.result(timeout=8.0) or {}
                profiles[c] = _extract_fund_factor_profile(c, det, tier, req_cagr)
            except Exception:
                profiles[c] = {
                    "fund_code": c,
                    "quant_score": 65,
                    "style_note": "基准评分",
                    "sharpe": 0.5,
                    "calmar": 0.4,
                    "max_dd_pct": 12.0,
                    "ann_vol_pct": 12.0,
                    "new_high_rate_pct": 10.0,
                    "excess_pct": 0.0,
                    "info_ratio": 0.0,
                    "tracking_error_pct": 10.0,
                    "total_fee_pct": 0.6,
                    "scale_yi": None,
                    "mgr_days": 365,
                }

    avg_score = sum(p["quant_score"] for p in profiles.values()) / max(len(profiles), 1)
    tilted: Dict[str, float] = {}
    for c, w in base_weights.items():
        sc = profiles[c]["quant_score"]
        # 温和因子倾斜系数 [0.85, 1.15]
        mult = float(np.clip(1.0 + (sc - avg_score) * 0.008, 0.85, 1.15))
        tilted[c] = float(w) * mult

    tot = sum(tilted.values()) or 1.0
    norm: Dict[str, float] = {}
    acc = 0.0
    items = sorted(tilted.items(), key=lambda x: x[1], reverse=True)
    for idx, (c, w) in enumerate(items):
        if idx == len(items) - 1:
            norm[c] = round(max(0.0, 1.0 - acc), 4)
        else:
            nw = round(w / tot, 4)
            norm[c] = nw
            acc += nw
    return norm, profiles


def evaluate_goal_achievement(
    fund_weights: Dict[str, float],
    target_return_pct: float,
    horizon_months: int,
    tier: str = "C3",
) -> Dict[str, Any]:
    """
    在真实历史净值序列上执行全历史滚动窗口检验：
    计算组合在 horizon_months 个月内达成 target_return_pct (%) 的历史概率、
    中位收益、最差回撤及平均达标耗时。
    """
    t_ret = float(target_return_pct)
    h_mon = max(3, min(60, int(horizon_months or 12)))
    req_cagr = round((((1.0 + t_ret / 100.0) ** (12.0 / h_mon)) - 1.0) * 100.0, 2) if t_ret > -90 else 0.0
    suggested_tier = map_target_return_to_tier(max(0.0, req_cagr))
    tier_clean = str(tier or "C3").upper().strip()
    if tier_clean not in _TIER_ORDER:
        tier_clean = "C3"

    # 预期偏差碰撞检测
    has_collision = _TIER_ORDER[suggested_tier] > _TIER_ORDER[tier_clean]
    max_realistic = _TIER_MAX_REALISTIC_CAGR[tier_clean]
    if has_collision:
        collision_msg = (
            f"目标冲突提醒：在 {h_mon} 个月内赚取 +{t_ret:.1f}% 折合年化 +{req_cagr:.1f}%，"
            f"超出 {tier_clean} 档位常规年化能力区间（约 ≤{max_realistic:.1f}%），"
            f"通常需要 {suggested_tier} 档位风险承受力，或建议将持有周期拉长 / 目标适当下调。"
        )
    else:
        collision_msg = (
            f"目标与风险匹配：在 {h_mon} 个月内目标收益 +{t_ret:.1f}%（折合年化 +{req_cagr:.1f}%），"
            f"与当前 {tier_clean} 风险承受力相容。"
        )

    # 历史滚动窗口实测
    hit_rate_pct = 0.0
    median_ret_pct = 0.0
    worst_ret_pct = 0.0
    best_ret_pct = 0.0
    avg_reach_months: Optional[float] = None
    windows_tested = 0

    try:
        df_bt = StrategyBridge.build_custom_portfolio_backtest(
            fund_weights=fund_weights,
            secondary_weights=None,
            tier=tier_clean,
            target_return_pct=max(3.0, min(30.0, req_cagr)),
        )
        if df_bt is not None and not df_bt.empty:
            col = "strategy_nav_otc" if "strategy_nav_otc" in df_bt.columns else "strategy_nav"
            navs = df_bt[col].astype(float).ffill().bfill().values
            win_days = max(21, int(round(h_mon * 21)))
            if len(navs) > win_days + 5:
                step = 5  # 按周滚动起点
                rets = []
                hits = 0
                reach_days_list = []
                target_ratio = 1.0 + t_ret / 100.0
                for i in range(0, len(navs) - win_days, step):
                    base = navs[i]
                    if base <= 0:
                        continue
                    seg = navs[i : i + win_days + 1] / base
                    end_r = (seg[-1] - 1.0) * 100.0
                    rets.append(end_r)
                    # 区间内任意交易日达到目标收益（可止盈落袋）或期末达到
                    reached_idx = np.where(seg >= target_ratio)[0]
                    if len(reached_idx) > 0:
                        hits += 1
                        reach_days_list.append(int(reached_idx[0]))
                if rets:
                    windows_tested = len(rets)
                    hit_rate_pct = round(hits / windows_tested * 100.0, 1)
                    median_ret_pct = round(float(np.median(rets)), 2)
                    worst_ret_pct = round(float(np.percentile(rets, 5)), 2)
                    best_ret_pct = round(float(np.percentile(rets, 95)), 2)
                    if reach_days_list:
                        avg_reach_months = round(float(np.mean(reach_days_list)) / 21.0, 1)
    except Exception:
        pass

    # 根据历史达成概率与目标给出客观可行性评级
    if hit_rate_pct >= 70.0 and not has_collision:
        feasibility = "高可行性"
        feasibility_level = "high"
    elif hit_rate_pct >= 45.0:
        feasibility = "中等可行性"
        feasibility_level = "medium"
    else:
        feasibility = "偏激进 / 建议调参"
        feasibility_level = "low"

    # 智能推荐最适配该目标的模型
    if req_cagr <= 6.0:
        rec_model = "risk_parity"
    elif req_cagr <= 9.5:
        rec_model = "dividend_defense"
    elif req_cagr <= 14.0:
        rec_model = "all_weather"
    else:
        rec_model = "barbell_growth"

    return {
        "target_return_pct": round(t_ret, 1),
        "horizon_months": h_mon,
        "required_cagr_pct": req_cagr,
        "current_tier": tier_clean,
        "suggested_tier": suggested_tier,
        "has_collision": has_collision,
        "collision_message": collision_msg,
        "recommended_model": rec_model,
        "feasibility": feasibility,
        "feasibility_level": feasibility_level,
        "historical_hit_rate_pct": hit_rate_pct,
        "windows_tested": windows_tested,
        "median_return_pct": median_ret_pct,
        "p05_worst_return_pct": worst_ret_pct,
        "p95_best_return_pct": best_ret_pct,
        "avg_reach_months": avg_reach_months,
    }
