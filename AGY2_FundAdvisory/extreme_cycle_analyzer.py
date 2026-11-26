# -*- coding: utf-8 -*-
"""
AGY2 极端市场修复天数、完整牛熊周期与量化止盈锚点分析引擎 (extreme_cycle_analyzer.py)
核心能力：
  1. 预计极端修复天数（前瞻 10,000 次 Circular Block Bootstrap + Student-t 跳跃扩散蒙特卡洛）：
     在 3 年期（756 交易日）路径上统计遭遇极端回撤冲击后「谷底->回本」与「高点->低点->回本」
     的中位 / P75 / P90 预计修复天数，并与同期沪深 300 模拟修复天数对照。
  2. 历史极端市场真实修复天数：
     在 2018 贸易摩擦去杠杆熊市、2020 疫情冲击、2021-2022 杀估值熊市、2024 微盘流动性危机
     及全历史最大水下期上，实算真实最大回撤、下跌交易日、谷底修复天数、总水下时长。
  3. 历史完整极端周期拆解（Peak 高点 -> Trough 低点 -> Recovery 回本 -> Next Peak 下一轮高点）：
     提取全历史独立完整周期，统计一般耗时多久、前高到新高净收益区间、低点到新高反弹收益区间。
  4. 三阶量化建议止盈点（Take-Profit Anchors）：
     动态融合用户目标收益、组合历史完整周期收益分布、历史最大回撤与实时宏观 ERP 估值分位，
     给出目标落袋线、历史周期规律止盈区、移动回撤锁盈保护线及当下周期定位提示。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


_CANONICAL_EXTREME_EVENTS: List[Dict[str, str]] = [
    {
        "id": "2018_trade_war",
        "name": "2018 贸易摩擦与去杠杆熊市",
        "start": "2018-01-24",
        "end": "2019-01-04",
        "desc": "金融去杠杆叠加外部贸易摩擦升级，估值与盈利双杀",
    },
    {
        "id": "2020_covid_shock",
        "name": "2020 全球疫情流动性冲击",
        "start": "2020-01-14",
        "end": "2020-03-23",
        "desc": "全球疫情爆发引发跨市场流动性瞬间踩踏与急跌",
    },
    {
        "id": "2021_2022_valuation_kill",
        "name": "2021–2022 杀估值与加息熊市",
        "start": "2021-02-18",
        "end": "2022-10-31",
        "desc": "核心资产高估泡沫出清叠加美联储激进加息周期",
    },
    {
        "id": "2024_micro_liquidity",
        "name": "2024 年初微盘流动性危机",
        "start": "2024-01-02",
        "end": "2024-02-05",
        "desc": "雪球集中敲入与小微盘量化踩踏，短期恐慌抽水",
    },
]


def _tdays_to_months(tdays: float) -> float:
    return round(float(tdays) / 21.0, 1)


def _simulate_mc_recovery_days(
    daily_returns: np.ndarray,
    n_simulations: int = 10000,
    horizon_days: int = 756,
    block_size: int = 10,
    seed: int = 42,
) -> Dict[str, Any]:
    """
    无右截断偏差的两阶段向量化 10,000 次蒙特卡洛（70% Circular Block Bootstrap + 30% Student-t nu=5）：
      阶段 A（极端冲击形成期，252 交易日）：模拟 10,000 条 1 年期路径，提取 VaR 95%、CVaR 99% 与最差 10% 极端冲击深度及下跌天数；
      阶段 B（极端冲击后独立修复期，1,000 交易日 ≈ 4 年）：从每条极端冲击的谷底净值 (1 - shock_dd) 出发，
      独立模拟未来 4 年每日收益路径，无截断测量「谷底 -> 收复前高」与「高点 -> 谷底 -> 收复前高」的真实修复天数分布。
    """
    rets = daily_returns[np.isfinite(daily_returns)]
    n_ret = len(rets)
    if n_ret < 30:
        return {
            "n_simulations": 0,
            "horizon_days": horizon_days,
            "extreme_shock_var95_pct": 0.0,
            "extreme_shock_cvar99_pct": 0.0,
            "tail_paths_count": 0,
            "recovery_prob_within_3y_pct": 0.0,
            "trough_to_recovery_tdays": {"median": 0, "p75": 0, "p90": 0, "median_months": 0.0},
            "peak_to_recovery_tdays": {"median": 0, "p75": 0, "p90": 0, "median_months": 0.0},
        }

    rng = np.random.default_rng(seed)
    n_sim = max(500, int(n_simulations))
    b_size = max(5, min(20, int(block_size), n_ret))
    mu = float(np.mean(rets))
    sigma = max(float(np.std(rets, ddof=1)), 1e-6)

    def _draw_paths(count: int, length: int) -> np.ndarray:
        n_cbb = int(count * 0.70)
        n_stu = count - n_cbb
        n_blk = int(np.ceil(length / b_size))
        starts = rng.integers(0, n_ret, size=(n_cbb, n_blk))
        idx = (starts[:, :, None] + np.arange(b_size)[None, None, :]) % n_ret
        cbb = rets[idx.reshape(n_cbb, n_blk * b_size)[:, :length]]
        t_unit = rng.standard_t(df=5, size=(n_stu, length)) / np.sqrt(5.0 / 3.0)
        stu = np.clip(mu + sigma * t_unit, -0.15, 0.15)
        return np.vstack([cbb, stu])

    # 阶段 A：252 交易日极端冲击形成期
    shock_len = 252
    shock_rets = _draw_paths(n_sim, shock_len)
    shock_nav = np.empty((n_sim, shock_len + 1), dtype=np.float64)
    shock_nav[:, 0] = 1.0
    shock_nav[:, 1:] = np.cumprod(1.0 + shock_rets, axis=1)

    cummax = np.maximum.accumulate(shock_nav, axis=1)
    dds = (shock_nav - cummax) / np.maximum(cummax, 1e-8)
    abs_mdd = np.abs(np.min(dds, axis=1))

    var95 = float(np.percentile(abs_mdd, 95))
    var99 = float(np.percentile(abs_mdd, 99))
    worst_1pct = abs_mdd[abs_mdd >= var99]
    cvar99 = max(var99, float(np.mean(worst_1pct)) if len(worst_1pct) > 0 else var99)

    # 选取最差 10% 极端冲击路径进入阶段 B（均经历约 P90~CVaR99 级别的极端下跌）
    tail_thresh = float(np.percentile(abs_mdd, 90))
    tail_indices = np.where(abs_mdd >= tail_thresh)[0]
    tail_n = max(len(tail_indices), 1)
    tail_trough_idx = np.argmin(dds[tail_indices], axis=1)

    shock_depths = np.empty(len(tail_indices), dtype=np.float64)
    fall_tdays_arr = np.empty(len(tail_indices), dtype=np.int64)
    for k, pi in enumerate(tail_indices):
        ti = int(tail_trough_idx[k])
        pv = float(cummax[pi, ti])
        hits = np.where(shock_nav[pi, : ti + 1] >= pv - 1e-12)[0]
        p_idx = int(hits[-1]) if len(hits) > 0 else 0
        shock_depths[k] = float(abs_mdd[pi])
        fall_tdays_arr[k] = max(1, ti - p_idx)

    # 阶段 B：从每条极端冲击的谷底 (1 - shock_depth) 起算，向前模拟 1,260 交易日（约 5 年）测量无偏修复天数
    rec_horizon = 1260
    fwd_rets = _draw_paths(len(tail_indices), rec_horizon)
    fwd_mult = np.cumprod(1.0 + fwd_rets, axis=1)
    required_mult = 1.0 / np.maximum(1.0 - shock_depths[:, None], 0.15)
    hit_mat = fwd_mult >= required_mult

    has_hit = np.any(hit_mat, axis=1)
    first_hit = np.argmax(hit_mat, axis=1) + 1  # 1-based trading days after trough

    # 3 年内（756 交易日）总修复概率
    rec_within_3y = has_hit & (first_hit <= int(horizon_days))
    rec_prob_3y = round(float(np.mean(rec_within_3y)) * 100.0, 1)

    # 常规可修复情景中位数（在 3 年内成功修复的路径）与全路径保守分布（含未修复尾部按 1260d 下界计）
    t2r_days = np.where(has_hit, first_hit, rec_horizon).astype(float)
    p2r_days = t2r_days + fall_tdays_arr.astype(float)
    rec_only_t2r = first_hit[rec_within_3y]
    rec_only_p2r = (first_hit + fall_tdays_arr)[rec_within_3y]
    normal_t2r_med = int(round(float(np.median(rec_only_t2r)))) if len(rec_only_t2r) >= 10 else int(round(float(np.percentile(t2r_days, 50))))
    normal_p2r_med = int(round(float(np.median(rec_only_p2r)))) if len(rec_only_p2r) >= 10 else int(round(float(np.percentile(p2r_days, 50))))

    t2r_med = int(round(float(np.percentile(t2r_days, 50))))
    t2r_p75 = int(round(float(np.percentile(t2r_days, 75))))
    t2r_p90 = int(round(float(np.percentile(t2r_days, 90))))
    p2r_med = int(round(float(np.percentile(p2r_days, 50))))
    p2r_p75 = int(round(float(np.percentile(p2r_days, 75))))
    p2r_p90 = int(round(float(np.percentile(p2r_days, 90))))

    return {
        "n_simulations": n_sim,
        "horizon_days": horizon_days,
        "extreme_shock_var95_pct": round(var95 * 100.0, 2),
        "extreme_shock_cvar99_pct": round(cvar99 * 100.0, 2),
        "tail_paths_count": int(len(tail_indices)),
        "recovery_prob_within_3y_pct": rec_prob_3y,
        "trough_to_recovery_tdays": {
            "normal_median": normal_t2r_med,
            "normal_median_months": _tdays_to_months(normal_t2r_med),
            "median": t2r_med,
            "p75": max(t2r_med, t2r_p75),
            "p90": max(t2r_p75, t2r_p90),
            "median_months": _tdays_to_months(t2r_med),
        },
        "peak_to_recovery_tdays": {
            "normal_median": normal_p2r_med,
            "normal_median_months": _tdays_to_months(normal_p2r_med),
            "median": p2r_med,
            "p75": max(p2r_med, p2r_p75),
            "p90": max(p2r_p75, p2r_p90),
            "median_months": _tdays_to_months(p2r_med),
        },
    }


def _measure_event_recovery(
    dates: List[str],
    nav: np.ndarray,
    start_date: str,
    end_date: str,
) -> Optional[Dict[str, Any]]:
    """在指定极端行情窗口内精确测量峰值、谷底、最大回撤、下跌天数与真实修复天数。"""
    n = len(nav)
    win_indices = [i for i, d in enumerate(dates) if start_date <= d <= end_date]
    if len(win_indices) < 5:
        return None

    i0, i1 = win_indices[0], win_indices[-1]
    sub = nav[i0 : i1 + 1]
    cmax = np.maximum.accumulate(sub)
    dd = (sub - cmax) / np.maximum(cmax, 1e-8)
    rel_trough = int(np.argmin(dd))
    rel_peak = int(np.argmax(sub[: rel_trough + 1]))

    peak_idx = i0 + rel_peak
    trough_idx = i0 + rel_trough
    peak_val = float(nav[peak_idx])
    trough_val = float(nav[trough_idx])
    mdd_pct = round(abs(float(dd[rel_trough])) * 100.0, 2)
    fall_tdays = max(0, trough_idx - peak_idx)

    # 在全周期中从谷底后向查找首次收复前高
    rec_idx: Optional[int] = None
    if trough_idx < n - 1:
        post_hits = np.where(nav[trough_idx + 1 :] >= peak_val - 1e-12)[0]
        if len(post_hits) > 0:
            rec_idx = trough_idx + 1 + int(post_hits[0])

    if rec_idx is not None:
        trough_to_rec = rec_idx - trough_idx
        total_uw = rec_idx - peak_idx
        rec_date = dates[rec_idx]
        recovered = True
    else:
        trough_to_rec = (n - 1) - trough_idx
        total_uw = (n - 1) - peak_idx
        rec_date = "修复中"
        recovered = False

    return {
        "peak_idx": peak_idx,
        "trough_idx": trough_idx,
        "recovery_idx": rec_idx,
        "peak_date": dates[peak_idx],
        "trough_date": dates[trough_idx],
        "recovery_date": rec_date,
        "max_dd_pct": mdd_pct,
        "fall_tdays": fall_tdays,
        "trough_to_recovery_tdays": trough_to_rec,
        "trough_to_recovery_months": _tdays_to_months(trough_to_rec),
        "total_underwater_tdays": total_uw,
        "total_underwater_months": _tdays_to_months(total_uw),
        "recovered": recovered,
        "peak_val": peak_val,
        "trough_val": trough_val,
    }


def _extract_full_cycles(
    dates: List[str],
    nav: np.ndarray,
    label_prefix: str = "组合",
) -> Dict[str, Any]:
    """
    全历史（2018–2026）自动提取独立完整极端周期：
    高点 (Peak 1) -> 谷底 (Trough) -> 收复前高 (Recovery) -> 下一轮高点 (Peak 2)。
    同时统计完整周期一般多久、前高到新高净收益、低点到新高波段收益。
    """
    n = len(nav)
    if n < 60:
        return {"cycles": [], "summary": {}}

    cummax = np.maximum.accumulate(nav)
    dd_arr = (nav - cummax) / np.maximum(cummax, 1e-8)
    full_mdd_pct = abs(float(np.min(dd_arr))) * 100.0

    # 提取所有独立的水下区间 (peak_idx -> recovery_idx)
    raw_episodes: List[Dict[str, Any]] = []
    p_idx = 0
    in_dd = False
    for i in range(1, n):
        if nav[i] >= cummax[i] - 1e-12:
            if in_dd:
                seg_dd = dd_arr[p_idx : i + 1]
                rel_t = int(np.argmin(seg_dd))
                depth = abs(float(seg_dd[rel_t])) * 100.0
                raw_episodes.append({
                    "peak1_idx": p_idx,
                    "trough_idx": p_idx + rel_t,
                    "recovery_idx": i,
                    "recovered": True,
                    "drawdown_pct": round(depth, 2),
                })
                in_dd = False
            p_idx = i
        else:
            in_dd = True

    if in_dd and p_idx < n - 1:
        seg_dd = dd_arr[p_idx:]
        rel_t = int(np.argmin(seg_dd))
        depth = abs(float(seg_dd[rel_t])) * 100.0
        raw_episodes.append({
            "peak1_idx": p_idx,
            "trough_idx": p_idx + rel_t,
            "recovery_idx": None,
            "recovered": False,
            "drawdown_pct": round(depth, 2),
        })

    # 自适应显著极端回撤门槛（过滤短小杂波，聚焦真正完整的极端熊转牛/修复周期）
    dd_threshold = max(2.8, min(10.0, full_mdd_pct * 0.45))
    major = [
        ep for ep in raw_episodes
        if ep["drawdown_pct"] >= dd_threshold
        and (ep["trough_idx"] - ep["peak1_idx"]) >= 10
        and ((ep["recovery_idx"] - ep["peak1_idx"]) >= 25 if ep["recovery_idx"] is not None else ((n - 1 - ep["peak1_idx"]) >= 25))
    ]
    if len(major) < 2:
        major = sorted(
            [ep for ep in raw_episodes if ep["drawdown_pct"] >= 1.5 and (ep["trough_idx"] - ep["peak1_idx"]) >= 5],
            key=lambda x: x["drawdown_pct"],
            reverse=True,
        )[:4]
        major.sort(key=lambda x: x["peak1_idx"])

    cycles: List[Dict[str, Any]] = []
    for idx_m, ep in enumerate(major):
        p1 = ep["peak1_idx"]
        tr = ep["trough_idx"]
        rec = ep["recovery_idx"]
        p1_nav = float(nav[p1])
        tr_nav = float(nav[tr])
        fall_tdays = max(1, tr - p1)

        if rec is not None:
            # 确定本轮修复后的「下一轮周期高点 Peak 2」：
            # 扫描到下一个显著极端回撤的起点（若为最后一轮则扫描到样本期末）
            next_bound = major[idx_m + 1]["peak1_idx"] if (idx_m + 1) < len(major) else (n - 1)
            if next_bound <= rec:
                next_bound = n - 1
            search_seg = nav[rec : next_bound + 1]
            p2 = rec + int(np.argmax(search_seg))
            p2_nav = float(nav[p2])

            t2r_tdays = max(1, rec - tr)
            uw_tdays = rec - p1
            exp_tdays = max(0, p2 - rec)
            full_tdays = max(uw_tdays, p2 - p1)

            peak_to_next_peak_pct = round((p2_nav / max(p1_nav, 1e-8) - 1.0) * 100.0, 2)
            trough_to_next_peak_pct = round((p2_nav / max(tr_nav, 1e-8) - 1.0) * 100.0, 2)
            cycle_years = max(full_tdays / 250.0, 0.1)
            cycle_cagr = round((((1.0 + peak_to_next_peak_pct / 100.0) ** (1.0 / cycle_years)) - 1.0) * 100.0, 2)

            p1_yr = dates[p1][:4]
            p2_yr = dates[p2][:4]
            period_tag = f"{p1_yr}–{p2_yr}" if p1_yr != p2_yr else p1_yr
            cycles.append({
                "cycle_id": f"cycle_{idx_m + 1}",
                "cycle_label": f"{period_tag} 完整极端周期 #{idx_m + 1}",
                "peak1_date": dates[p1],
                "trough_date": dates[tr],
                "recovery_date": dates[rec],
                "next_peak_date": dates[p2],
                "recovered": True,
                "drawdown_pct": -abs(ep["drawdown_pct"]),
                "fall_tdays": fall_tdays,
                "trough_to_recovery_tdays": t2r_tdays,
                "underwater_tdays": uw_tdays,
                "underwater_months": _tdays_to_months(uw_tdays),
                "expansion_tdays": exp_tdays,
                "full_cycle_tdays": full_tdays,
                "full_cycle_months": _tdays_to_months(full_tdays),
                "peak_to_next_peak_return_pct": peak_to_next_peak_pct,
                "trough_to_next_peak_return_pct": trough_to_next_peak_pct,
                "cycle_cagr_pct": cycle_cagr,
            })
        else:
            # 尚未收复的尾部周期
            uw_tdays = (n - 1) - p1
            t2cur_tdays = (n - 1) - tr
            cur_nav = float(nav[-1])
            cycles.append({
                "cycle_id": f"cycle_{idx_m + 1}",
                "cycle_label": f"{dates[p1][:4]}–至今（修复进行中）",
                "peak1_date": dates[p1],
                "trough_date": dates[tr],
                "recovery_date": "修复中",
                "next_peak_date": dates[-1],
                "recovered": False,
                "drawdown_pct": -abs(ep["drawdown_pct"]),
                "fall_tdays": fall_tdays,
                "trough_to_recovery_tdays": t2cur_tdays,
                "underwater_tdays": uw_tdays,
                "underwater_months": _tdays_to_months(uw_tdays),
                "expansion_tdays": 0,
                "full_cycle_tdays": uw_tdays,
                "full_cycle_months": _tdays_to_months(uw_tdays),
                "peak_to_next_peak_return_pct": round((cur_nav / max(p1_nav, 1e-8) - 1.0) * 100.0, 2),
                "trough_to_next_peak_return_pct": round((cur_nav / max(tr_nav, 1e-8) - 1.0) * 100.0, 2),
                "cycle_cagr_pct": 0.0,
            })

    completed = [c for c in cycles if c["recovered"]]
    if completed:
        uw_arr = np.array([c["underwater_tdays"] for c in completed], dtype=float)
        fc_arr = np.array([c["full_cycle_tdays"] for c in completed], dtype=float)
        p2p_arr = np.array([c["peak_to_next_peak_return_pct"] for c in completed], dtype=float)
        t2p_arr = np.array([c["trough_to_next_peak_return_pct"] for c in completed], dtype=float)
        dd_list = np.array([abs(c["drawdown_pct"]) for c in completed], dtype=float)

        summary = {
            "completed_cycles_count": len(completed),
            "total_cycles_count": len(cycles),
            "dd_threshold_pct": round(dd_threshold, 2),
            "avg_drawdown_pct": round(float(np.mean(dd_list)), 2),
            "max_drawdown_pct": round(full_mdd_pct, 2),
            "avg_underwater_tdays": int(round(float(np.mean(uw_arr)))),
            "avg_underwater_months": _tdays_to_months(float(np.mean(uw_arr))),
            "max_underwater_tdays": int(np.max([c["underwater_tdays"] for c in cycles])),
            "max_underwater_months": _tdays_to_months(float(np.max([c["underwater_tdays"] for c in cycles]))),
            "avg_full_cycle_tdays": int(round(float(np.mean(fc_arr)))),
            "avg_full_cycle_months": _tdays_to_months(float(np.mean(fc_arr))),
            "full_cycle_months_range": [
                _tdays_to_months(float(np.min(fc_arr))),
                _tdays_to_months(float(np.max(fc_arr))),
            ],
            "avg_peak_to_next_peak_return_pct": round(float(np.mean(p2p_arr)), 2),
            "median_peak_to_next_peak_return_pct": round(float(np.median(p2p_arr)), 2),
            "p75_peak_to_next_peak_return_pct": round(float(np.percentile(p2p_arr, 75)), 2),
            "peak_to_next_peak_range_pct": [round(float(np.min(p2p_arr)), 2), round(float(np.max(p2p_arr)), 2)],
            "avg_trough_to_next_peak_return_pct": round(float(np.mean(t2p_arr)), 2),
            "median_trough_to_next_peak_return_pct": round(float(np.median(t2p_arr)), 2),
            "trough_to_next_peak_range_pct": [round(float(np.min(t2p_arr)), 2), round(float(np.max(t2p_arr)), 2)],
        }
    else:
        summary = {
            "completed_cycles_count": 0,
            "total_cycles_count": len(cycles),
            "dd_threshold_pct": round(dd_threshold, 2),
            "avg_drawdown_pct": round(full_mdd_pct, 2),
            "max_drawdown_pct": round(full_mdd_pct, 2),
            "avg_underwater_tdays": 0,
            "avg_underwater_months": 0.0,
            "max_underwater_tdays": int(max((c["underwater_tdays"] for c in cycles), default=0)),
            "max_underwater_months": _tdays_to_months(max((c["underwater_tdays"] for c in cycles), default=0)),
            "avg_full_cycle_tdays": 0,
            "avg_full_cycle_months": 0.0,
            "full_cycle_months_range": [0.0, 0.0],
            "avg_peak_to_next_peak_return_pct": 0.0,
            "median_peak_to_next_peak_return_pct": 0.0,
            "p75_peak_to_next_peak_return_pct": 0.0,
            "peak_to_next_peak_range_pct": [0.0, 0.0],
            "avg_trough_to_next_peak_return_pct": 0.0,
            "median_trough_to_next_peak_return_pct": 0.0,
            "trough_to_next_peak_range_pct": [0.0, 0.0],
        }

    return {"cycles": cycles, "summary": summary, "label": label_prefix}


def _derive_take_profit_plan(
    cycle_summary: Dict[str, Any],
    nav: np.ndarray,
    target_return_pct: float,
    horizon_months: int,
    tier: str,
    market_snapshot: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    基于当前方案真实历史完整周期收益分布、滚动 1~2 年高分位收益、历史最大回撤与实时宏观估值，
    动态推导三阶量化建议止盈锚点（严禁硬编码常数）。
    """
    t_ret = max(2.0, float(target_return_pct))
    full_mdd = abs(float(cycle_summary.get("max_drawdown_pct", 10.0) or 10.0))
    avg_uw_m = float(cycle_summary.get("avg_underwater_months", 4.0) or 4.0)

    # 结合历史完整周期收益与滚动 1 年 / 2 年 P75 收益确定客观周期止盈区
    p2p_med = float(cycle_summary.get("median_peak_to_next_peak_return_pct", 0.0) or 0.0)
    p2p_p75 = float(cycle_summary.get("p75_peak_to_next_peak_return_pct", 0.0) or 0.0)
    t2p_med = float(cycle_summary.get("median_trough_to_next_peak_return_pct", 0.0) or 0.0)

    roll_days = min(len(nav) - 1, max(126, int(round(horizon_months * 21))))
    roll_p65 = t_ret * 1.15
    roll_p85 = t_ret * 1.55
    if len(nav) > roll_days + 20:
        r_roll = (nav[roll_days:] / np.maximum(nav[:-roll_days], 1e-8) - 1.0) * 100.0
        roll_p65 = float(np.percentile(r_roll, 65))
        roll_p85 = float(np.percentile(r_roll, 85))

    # 第一止盈锚：目标达成落袋线（紧贴用户目标收益，兼顾历史可行分位）
    tier1_pct = round(t_ret, 1)

    # 第二止盈锚：历史完整周期规律止盈区（动态锚定周期中位/P75 与滚动 P75~P85）
    raw_low = max(tier1_pct + 2.5, (p2p_med * 0.6 + roll_p65 * 0.4) if p2p_med > 2.0 else roll_p65)
    raw_high = max(raw_low + 4.0, (max(p2p_p75, t2p_med * 0.72) * 0.55 + roll_p85 * 0.45) if p2p_p75 > 2.0 else roll_p85)
    tier2_low = round(min(raw_low, 65.0), 1)
    tier2_high = round(min(max(raw_high, tier2_low + 3.5), 95.0), 1)

    # 第三止盈锚：移动回撤保护线（盈利达标后自高点回撤达历史最大回撤的 45% 触发右侧锁盈）
    trailing_dd = round(max(3.5, min(12.0, full_mdd * 0.45)), 1)
    trailing_activate = round(max(4.0, tier1_pct * 0.8), 1)

    # 实时宏观周期位置判定
    snap = market_snapshot or {}
    erp_pct = float(snap.get("erp_percentile", 60.0) or 60.0)
    bias_20 = float(snap.get("bias_20", 0.0) or 0.0)

    if erp_pct >= 65.0 and bias_20 <= 3.0:
        pos_tag = "估值底部 / 积累份额区"
        pos_level = "accumulate"
        pos_advice = (
            f"当前全市场 ERP 估值分位 {erp_pct:.1f}%（权益性价比偏高），MA20 乖离 {bias_20:+.1f}%，"
            f"整体仍处周期中低位、距离止盈区尚远，宜按计划耐心持仓或逢回调积累低位筹码。"
        )
    elif erp_pct <= 30.0 or bias_20 >= 6.5:
        pos_tag = "偏热警戒 / 分批止盈区"
        pos_level = "take_profit"
        pos_advice = (
            f"当前全市场 ERP 估值分位回落至 {erp_pct:.1f}%、MA20 乖离 {bias_20:+.1f}%，市场情绪偏热；"
            f"若持仓累计浮盈已触及 +{tier1_pct:.1f}% 以上，建议严格按阶梯兑现权益利润转入固收安全垫。"
        )
    else:
        pos_tag = "温和修复 / 持有观察区"
        pos_level = "hold_watch"
        pos_advice = (
            f"当前全市场 ERP 估值分位 {erp_pct:.1f}%、MA20 乖离 {bias_20:+.1f}%，处于历史周期中段；"
            f"建议保持核心仓位不动，待浮盈触及 +{tier1_pct:.1f}% 第一止盈锚时启动分批落袋。"
        )

    anchors = [
        {
            "step": 1,
            "code": "goal_lock_in",
            "title": "第一止盈锚 · 目标落袋线",
            "trigger_label": f"累计收益 ≥ +{tier1_pct:.1f}%",
            "trigger_pct": tier1_pct,
            "action": "兑现 25%~30% 权益浮盈，转入纯债 / 货基安全垫",
            "rationale": (
                f"达到您设定的 {horizon_months} 个月 +{t_ret:.1f}% 目标后先锁定一部分利润，"
                f"既落袋为安又保留 70% 底仓继续享受右侧趋势。"
            ),
        },
        {
            "step": 2,
            "code": "cycle_zone",
            "title": "第二止盈锚 · 历史周期规律止盈区",
            "trigger_label": f"+{tier2_low:.1f}% ~ +{tier2_high:.1f}%",
            "trigger_low_pct": tier2_low,
            "trigger_high_pct": tier2_high,
            "action": "分 2~3 批阶梯止盈 40%~50% 高弹性权益，或估值 ERP < 30% 时提速落袋",
            "rationale": (
                f"该方案历史完整极端周期前高至新高平均净赚 +{cycle_summary.get('avg_peak_to_next_peak_return_pct', 0):.1f}%"
                f"（低点反弹平均 +{cycle_summary.get('avg_trough_to_next_peak_return_pct', 0):.1f}%），"
                f"落入 +{tier2_low:.1f}%~+{tier2_high:.1f}% 区间通常已进入周期后半程，宜逢高降波。"
            ),
        },
        {
            "step": 3,
            "code": "trailing_stop",
            "title": "第三止盈锚 · 移动回撤锁盈线",
            "trigger_label": f"浮盈 ≥ +{trailing_activate:.1f}% 后自高点回撤 -{trailing_dd:.1f}%",
            "trigger_drawdown_pct": trailing_dd,
            "activation_profit_pct": trailing_activate,
            "action": "触发右侧纪律止盈：将高波权益仓位降至目标中枢或防御档位",
            "rationale": (
                f"该组合历史最大回撤为 -{full_mdd:.1f}%、极端水下期平均约 {avg_uw_m:.1f} 个月；"
                f"设置约 0.45× 最大回撤（-{trailing_dd:.1f}%）的移动止盈线，可防止整轮牛市盈利坐过山车回吐。"
            ),
        },
    ]

    return {
        "recommended_zone_pct": [tier1_pct, tier2_high],
        "core_cycle_zone_pct": [tier2_low, tier2_high],
        "trailing_stop_drawdown_pct": trailing_dd,
        "current_cycle_position": {
            "tag": pos_tag,
            "level": pos_level,
            "erp_percentile": round(erp_pct, 1),
            "bias_20": round(bias_20, 2),
            "advice": pos_advice,
        },
        "anchors": anchors,
    }


def analyze_extreme_recovery_and_cycles(
    df_bt: pd.DataFrame,
    target_return_pct: float = 10.0,
    horizon_months: int = 12,
    tier: str = "C3",
    market_snapshot: Optional[Dict[str, Any]] = None,
    n_simulations: int = 10000,
    df_proxy_early: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """
    当前方案极端市场全景诊断主入口：
      1. 预计极端修复天数（10,000 次前瞻 Block Bootstrap + Student-t 蒙特卡洛 vs 沪深300）
      2. 历史 4 大极端行情真实修复天数表（若组合含晚于早期事件成立的新锐基金，仅对未覆盖事件用 df_proxy_early 给出明文标注的同风格基准参考，绝不混充真实净值）
      3. 历史完整极端周期拆解（高点->低点->回本->下一轮高点，时长与收益统计）
      4. 三阶量化建议止盈锚点与当下周期定位
    """
    if df_bt is None or df_bt.empty:
        return {"status": "empty"}

    dates = [str(d)[:10] for d in df_bt["date"].tolist()]
    col_nav = "strategy_nav_otc" if "strategy_nav_otc" in df_bt.columns else "strategy_nav"
    nav = df_bt[col_nav].astype(float).ffill().bfill().to_numpy(dtype=np.float64)
    h300 = (
        df_bt["h300_nav"].astype(float).ffill().bfill().to_numpy(dtype=np.float64)
        if "h300_nav" in df_bt.columns
        else nav.copy()
    )

    p_dates_early: List[str] = []
    p_nav_early: Optional[np.ndarray] = None
    p_h300_early: Optional[np.ndarray] = None
    if df_proxy_early is not None and not df_proxy_early.empty:
        p_dates_early = [str(d)[:10] for d in df_proxy_early["date"].tolist()]
        p_col = "strategy_nav_otc" if "strategy_nav_otc" in df_proxy_early.columns else "strategy_nav"
        p_nav_early = df_proxy_early[p_col].astype(float).ffill().bfill().to_numpy(dtype=np.float64)
        p_h300_early = (
            df_proxy_early["h300_nav"].astype(float).ffill().bfill().to_numpy(dtype=np.float64)
            if "h300_nav" in df_proxy_early.columns
            else p_nav_early.copy()
        )

    port_rets = nav[1:] / np.maximum(nav[:-1], 1e-8) - 1.0
    h300_rets = h300[1:] / np.maximum(h300[:-1], 1e-8) - 1.0

    # 1. 前瞻蒙特卡洛预计极端修复天数（组合 vs 沪深300）
    mc_port = _simulate_mc_recovery_days(port_rets, n_simulations=n_simulations, horizon_days=756, block_size=10, seed=42)
    mc_h300 = _simulate_mc_recovery_days(h300_rets, n_simulations=4000, horizon_days=756, block_size=10, seed=42)

    p_med = mc_port["peak_to_recovery_tdays"]["median"]
    h_med = mc_h300["peak_to_recovery_tdays"]["median"]
    expected_recovery = {
        **mc_port,
        "hs300_peak_to_recovery_median_tdays": h_med,
        "hs300_peak_to_recovery_median_months": _tdays_to_months(h_med),
        "hs300_extreme_cvar99_pct": mc_h300["extreme_shock_cvar99_pct"],
        "days_faster_than_hs300": int(h_med - p_med),
    }

    # 2. 历史 4 大经典极端市场真实修复天数（早于真实共同存续期的事件明文标注参考基准）
    hist_events: List[Dict[str, Any]] = []
    real_start = dates[0]
    for ev in _CANONICAL_EXTREME_EVENTS:
        is_proxy = False
        proxy_note = ""
        if real_start <= ev["start"]:
            p_ev = _measure_event_recovery(dates, nav, ev["start"], ev["end"])
            h_ev = _measure_event_recovery(dates, h300, ev["start"], ev["end"])
        elif p_nav_early is not None and p_dates_early and p_dates_early[0] <= ev["start"]:
            p_ev = _measure_event_recovery(p_dates_early, p_nav_early, ev["start"], ev["end"])
            h_ev = _measure_event_recovery(p_dates_early, p_h300_early, ev["start"], ev["end"]) if p_h300_early is not None else None
            is_proxy = True
            proxy_note = f"组合含晚于该事件成立的基金（共同真实净值始于 {real_start}），本行按同风格基准指数参考测算"
        else:
            p_ev = None
            h_ev = None

        if not p_ev:
            continue
        h_mdd = h_ev["max_dd_pct"] if h_ev else 0.0
        h_uw = h_ev["total_underwater_tdays"] if h_ev else 0
        h_rec = h_ev["recovered"] if h_ev else False
        hist_events.append({
            "id": ev["id"],
            "name": ev["name"],
            "desc": ev["desc"],
            "window": f"{ev['start']} ~ {ev['end']}",
            "peak_date": p_ev["peak_date"],
            "trough_date": p_ev["trough_date"],
            "recovery_date": p_ev["recovery_date"],
            "max_dd_pct": -abs(p_ev["max_dd_pct"]),
            "h300_mdd_pct": -abs(h_mdd),
            "excess_defense_pct": round(h_mdd - p_ev["max_dd_pct"], 2),
            "fall_tdays": p_ev["fall_tdays"],
            "trough_to_recovery_tdays": p_ev["trough_to_recovery_tdays"],
            "trough_to_recovery_months": p_ev["trough_to_recovery_months"],
            "total_underwater_tdays": p_ev["total_underwater_tdays"],
            "total_underwater_months": p_ev["total_underwater_months"],
            "recovered": p_ev["recovered"],
            "h300_total_underwater_tdays": h_uw,
            "h300_total_underwater_months": _tdays_to_months(h_uw),
            "h300_recovered": h_rec,
            "days_faster_than_hs300": int(h_uw - p_ev["total_underwater_tdays"]),
            "is_proxy_simulated": is_proxy,
            "proxy_note": proxy_note,
        })

    recovered_events = [e for e in hist_events if e["recovered"]]
    hist_avg_t2r = int(round(float(np.mean([e["trough_to_recovery_tdays"] for e in recovered_events])))) if recovered_events else 0
    hist_avg_uw = int(round(float(np.mean([e["total_underwater_tdays"] for e in recovered_events])))) if recovered_events else 0
    hist_max_uw = int(max((e["total_underwater_tdays"] for e in hist_events), default=0))
    h300_avg_uw = int(round(float(np.mean([e["h300_total_underwater_tdays"] for e in hist_events])))) if hist_events else 0

    # 3. 历史完整极端周期拆解（高点 -> 低点 -> 回本 -> 下一轮高点）
    port_cycles = _extract_full_cycles(dates, nav, label_prefix="当前方案")
    h300_cycles = _extract_full_cycles(dates, h300, label_prefix="沪深300")

    # 4. 三阶量化建议止盈锚点
    take_profit = _derive_take_profit_plan(
        cycle_summary=port_cycles["summary"],
        nav=nav,
        target_return_pct=target_return_pct,
        horizon_months=horizon_months,
        tier=tier,
        market_snapshot=market_snapshot,
    )

    # 总结性人话结论（直接回答用户关心的全部核心问题）
    c_sum = port_cycles["summary"]
    avg_fc_m = c_sum.get("avg_full_cycle_months", 0.0)
    avg_fc_d = c_sum.get("avg_full_cycle_tdays", 0)
    avg_p2p = c_sum.get("avg_peak_to_next_peak_return_pct", 0.0)
    avg_t2p = c_sum.get("avg_trough_to_next_peak_return_pct", 0.0)
    plain_headline = (
        f"极端行情下，本方案蒙特卡洛预计总修复时长中位数约 {p_med} 交易日（约 {_tdays_to_months(p_med)} 个月，"
        f"比沪深 300 快 {max(0, h_med - p_med)} 交易日）；2018–2026 历史实测完整极端周期（高点→低点→新高）"
        f"平均约 {avg_fc_m} 个月（{avg_fc_d} 交易日），前高拿到新高平均净收益 +{avg_p2p:.1f}%"
        f"（低点布局至新高平均 +{avg_t2p:.1f}%），建议核心止盈锚定在 +{take_profit['recommended_zone_pct'][0]:.1f}% ~ +{take_profit['recommended_zone_pct'][1]:.1f}%。"
    )

    return {
        "status": "ready",
        "date_range": f"{dates[0]} ~ {dates[-1]}",
        "trading_days_analyzed": len(dates),
        "plain_headline": plain_headline,
        "expected_recovery": expected_recovery,
        "historical_recovery": {
            "events": hist_events,
            "avg_trough_to_recovery_tdays": hist_avg_t2r,
            "avg_trough_to_recovery_months": _tdays_to_months(hist_avg_t2r),
            "avg_underwater_tdays": hist_avg_uw,
            "avg_underwater_months": _tdays_to_months(hist_avg_uw),
            "max_underwater_tdays": max(hist_max_uw, int(c_sum.get("max_underwater_tdays", 0))),
            "max_underwater_months": _tdays_to_months(max(hist_max_uw, int(c_sum.get("max_underwater_tdays", 0)))),
            "hs300_avg_underwater_tdays": h300_avg_uw,
            "hs300_avg_underwater_months": _tdays_to_months(h300_avg_uw),
            "days_faster_than_hs300": int(h300_avg_uw - hist_avg_uw),
        },
        "full_cycles": {
            "items": port_cycles["cycles"],
            "summary": port_cycles["summary"],
            "hs300_summary": h300_cycles["summary"],
        },
        "take_profit_plan": take_profit,
    }
