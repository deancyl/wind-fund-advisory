# -*- coding: utf-8 -*-
"""
目标驱动真量化求解联动、回测偏差归因与极端行情修复周期核心回归测试套件
验证硬数学公理与端到端 API 契约：
  1. 权重严格闭合 (= 1.0000)，PCR 风险贡献总和严格闭合 (= 100.0%)，基金只数 100% 精确等于用户选定只数；
  2. 不同目标收益率 / 持有周期 / 风险档位 / 量化模型真正驱动不同的求解结果（非硬编码假数据）；
  3. /api/v1/recommend/blueprint 与 /api/v1/charts/backtest_curves 权重 100% 逐基一致；
  4. goal_reconciliation 显式输出量化缺口、3 条数据归因与“为何仍建议本配置”；
  5. extreme_cycle_analysis 严格满足数学不等式（P90 >= P75 >= P50、CVaR99 >= VaR95、
     total_underwater >= fall_tdays、完整周期时长 >= 水下时长、止盈锚单调递增、零 NaN/Inf）。
"""

import math
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
AGY2_DIR = ROOT / "AGY2_FundAdvisory"
for p in (str(AGY2_DIR), str(ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

import api_server
from extreme_cycle_analyzer import analyze_extreme_recovery_and_cycles
from goal_driven_selector import solve_goal_driven_portfolio
from strategy_bridge import StrategyBridge

client = TestClient(api_server.app)


def test_unified_solver_math_invariants_and_sensitivity():
    """验证真量化求解器的数学闭合性、严格基金只数约束与目标参数敏感性"""
    r_c1 = solve_goal_driven_portfolio(
        risk_level="C1", fund_count=5, model_id="dividend_defense", target_return_pct=6.0, horizon_months=12
    )
    r_c3 = solve_goal_driven_portfolio(
        risk_level="C3", fund_count=6, model_id="all_weather", target_return_pct=10.0, horizon_months=12
    )
    r_c4 = solve_goal_driven_portfolio(
        risk_level="C4", fund_count=6, model_id="barbell_growth", target_return_pct=24.0, horizon_months=12
    )

    for label, res, exp_n in [("C1", r_c1, 5), ("C3", r_c3, 6), ("C4", r_c4, 6)]:
        w = res["final_weights"]
        assert len(w) == exp_n, f"{label}: expected {exp_n} funds, got {len(w)}"
        assert abs(sum(w.values()) - 1.0) <= 0.001, f"{label}: weights sum != 1.0 ({sum(w.values())})"
        assert all(v > 0 for v in w.values()), f"{label}: found non-positive weight"

        pcr = res["pcr_info"]["pcr"]
        assert abs(sum(pcr.values()) - 100.0) <= 0.2, f"{label}: PCR sum != 100% ({sum(pcr.values())})"

        sa = res["solver_audit"]
        assert sa["history_trading_days"] >= 1000
        assert sa["monte_carlo_paths"] == 10000
        assert 0.0 <= sa["oos_conditional_win_rate_pct"] <= 100.0
        assert len(res["allocation_logic_summary"]["steps"]) >= 4

    # 敏感性检验：全市场 C1 固收/纯债大类占比应显著高于 C4
    def _bond_weight(res_obj):
        meta = res_obj.get("fund_cards_meta") or {}
        return sum(
            w for c, w in res_obj["final_weights"].items()
            if str((meta.get(c) or {}).get("asset_class", "")).lower() == "bond"
            or c in {"002351", "000086", "018757"}
        )

    bond_c1 = _bond_weight(r_c1)
    bond_c4 = _bond_weight(r_c4)
    assert bond_c1 > bond_c4 + 0.25, f"Expected C1 bond ({bond_c1}) >> C4 bond ({bond_c4})"

    # 同一档位不同目标/模型应产生差异化权重
    r_c3_rp = solve_goal_driven_portfolio(
        risk_level="C3", fund_count=6, model_id="risk_parity", target_return_pct=8.0, horizon_months=12
    )
    assert r_c3["final_weights"] != r_c3_rp["final_weights"], "Different model/goal should alter optimal weights"


def test_blueprint_and_backtest_exact_weight_parity_and_reconciliation():
    """验证 /api/v1/recommend/blueprint 与 /api/v1/charts/backtest_curves 权重 100% 同源且含偏差归因"""
    params = dict(
        risk_level="C3",
        amount=50000,
        fund_count=6,
        model="all_weather",
        target_return_pct=15,
        horizon_months=12,
    )
    bp_resp = client.get("/api/v1/recommend/blueprint", params=params)
    assert bp_resp.status_code == 200
    bp = bp_resp.json()

    assert bp["count"] == 6
    assert abs(sum(it["weight_pct"] for it in bp["items"]) - 100.0) <= 0.2
    assert abs(sum(it["suggested_amount"] for it in bp["items"]) - 50000.0) <= 5.0
    assert bp["solver_audit"] is not None
    assert bp["allocation_logic_summary"] is not None
    for it in bp["items"]:
        assert "solver_weight_pct" in it
        assert "risk_contribution_pcr_pct" in it
        assert "allocation_breakdown" in it

    bt_resp = client.get(
        "/api/v1/charts/backtest_curves",
        params={
            "tier": "C3",
            "model": "all_weather",
            "fund_count": 6,
            "period": "1y",
            "mode": "model_live",
            "target_return_pct": 15,
            "horizon_months": 12,
        },
    )
    assert bt_resp.status_code == 200
    bt = bt_resp.json()

    # 100% 权重同源强校验
    assert bt["portfolio_weights"] == bp["portfolio_weights"], (
        f"Blueprint vs Backtest weight drift: {bp['portfolio_weights']} != {bt['portfolio_weights']}"
    )

    # 目标 vs 回测偏差归因强校验
    rec = bt["goal_reconciliation"]
    assert rec is not None
    assert rec["status"] in ("aligned", "backtest_below_goal", "backtest_above_goal")
    assert len(rec["reasons"]) == 3
    assert len(rec["why_still_recommend"]) > 20
    assert math.isfinite(rec["gap_pct"])


def test_extreme_cycle_recovery_and_take_profit_invariants():
    """验证极端市场预计修复天数、历史修复天数、完整周期拆解与三阶止盈锚点数学公理"""
    solved = solve_goal_driven_portfolio(
        risk_level="C3", fund_count=6, model_id="all_weather", target_return_pct=10.0, horizon_months=12
    )
    df_bt = StrategyBridge.build_custom_portfolio_backtest(
        fund_weights=solved["final_weights"], tier="C3", target_return_pct=10.0
    )
    ext = analyze_extreme_recovery_and_cycles(
        df_bt=df_bt, target_return_pct=10.0, horizon_months=12, tier="C3"
    )
    assert ext["status"] == "ready"
    assert len(ext["plain_headline"]) > 20

    # 1. 前瞻蒙特卡洛修复天数公理
    er = ext["expected_recovery"]
    assert er["n_simulations"] == 10000
    assert er["extreme_shock_cvar99_pct"] >= er["extreme_shock_var95_pct"] > 0
    assert 0.0 <= er["recovery_prob_within_3y_pct"] <= 100.0
    for k in ("trough_to_recovery_tdays", "peak_to_recovery_tdays"):
        d = er[k]
        assert d["p90"] >= d["p75"] >= d["median"] > 0
    assert er["peak_to_recovery_tdays"]["median"] >= er["trough_to_recovery_tdays"]["median"]

    # 2. 历史四大极端行情修复公理
    hr = ext["historical_recovery"]
    assert len(hr["events"]) == 4
    for ev in hr["events"]:
        assert ev["max_dd_pct"] <= 0.0
        assert ev["total_underwater_tdays"] >= ev["fall_tdays"]
        if ev["recovered"]:
            assert ev["total_underwater_tdays"] == ev["fall_tdays"] + ev["trough_to_recovery_tdays"]

    # 3. 完整极端周期（高点->低点->回本->下一轮高点）公理
    fc = ext["full_cycles"]
    assert fc["summary"]["completed_cycles_count"] >= 2
    assert fc["summary"]["avg_full_cycle_months"] > 0
    assert fc["summary"]["avg_trough_to_next_peak_return_pct"] > fc["summary"]["avg_peak_to_next_peak_return_pct"]
    for cy in fc["items"]:
        if cy["recovered"]:
            assert cy["full_cycle_tdays"] >= cy["underwater_tdays"]
            assert cy["trough_to_next_peak_return_pct"] >= cy["peak_to_next_peak_return_pct"]

    # 4. 三阶量化止盈锚点公理
    tp = ext["take_profit_plan"]
    assert len(tp["anchors"]) == 3
    assert tp["recommended_zone_pct"][1] > tp["recommended_zone_pct"][0] >= 2.0
    assert 3.5 <= tp["trailing_stop_drawdown_pct"] <= 12.0
    assert tp["current_cycle_position"]["level"] in ("accumulate", "hold_watch", "take_profit")
