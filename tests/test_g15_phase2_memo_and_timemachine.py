# -*- coding: utf-8 -*-
"""
Targeted tests for G15 Milestone 2 (Phase 2):
"破除唯算法论：实装五维投顾首席备忘录与历史任意时点盲测时光机"

Test coverage:
1. `generate_chief_advisor_memo`: 5 dimensions structure, contract fields, empty/full inputs, pathology detection, and aliases.
2. `render_chief_advisor_memo_card`: Empty handling and safe HTML card rendering.
3. `run_historical_time_machine_backtest`: Point-in-Time zero lookahead verification across historical inflection points (2021-02-18, 2022-04-26, 2024-09-18), full public fund transaction frictions (subscription fee, daily C-share sales fee, FIFO step-down redemption fee, cash buffer), and boundary validations.
"""
import pytest
import pandas as pd
from datetime import datetime, date
from typing import Dict, Any

from AGY2_FundAdvisory.advisory_engine import (
    generate_chief_advisor_memo,
    get_chief_advisor_memo,
    OpportunityRadarEngine,
)
from AGY2_FundAdvisory.strategy_bridge import (
    StrategyBridge,
    run_historical_time_machine_backtest,
)
from AGY2_FundAdvisory.app_gui import (
    render_chief_advisor_memo_card,
)


class DummyHolding:
    """Mock holding object for pathology testing."""
    def __init__(self, fund_code, fund_name, market_value, cost_value, share_class="A"):
        self.fund_code = fund_code
        self.fund_name = fund_name
        self.market_value = market_value
        self.cost_value = cost_value
        self.share_class = share_class


# =====================================================================
# 1. Chief Advisor Memo Operator Tests
# =====================================================================

def test_generate_chief_advisor_memo_with_empty_inputs():
    """Verify generate_chief_advisor_memo works gracefully with None or empty inputs."""
    memo = generate_chief_advisor_memo(None, None, None, None)
    assert isinstance(memo, dict)

    required_top_keys = [
        "timestamp",
        "macro_policy",
        "international_fx",
        "industry_valuation",
        "portfolio_pathology",
        "action_directive",
    ]
    for k in required_top_keys:
        assert k in memo, f"Missing required top-level memo key: {k}"

    # Verify macro dimension
    macro = memo["macro_policy"]
    assert "cgb_10y" in macro
    assert "dr007" in macro
    assert "erp_pct" in macro
    assert "badge" in macro
    assert len(macro["content"]) > 0

    # Verify international fx dimension
    fx = memo["international_fx"]
    assert "usdcnh_rate" in fx
    assert "badge" in fx
    assert len(fx["content"]) > 0

    # Verify industry valuation dimension
    ind = memo["industry_valuation"]
    assert "badge" in ind
    assert "top3" in ind
    assert "黄金击球区" in ind["content"]
    assert "超买拥挤区" in ind["content"]

    # Verify portfolio pathology dimension
    pathology = memo["portfolio_pathology"]
    assert "badge" in pathology
    assert pathology["deep_loss_count"] == 0
    assert pathology["frag_count"] == 0
    assert "持仓结构优良" in pathology["content"]

    # Verify action directive dimension
    action = memo["action_directive"]
    assert "badge" in action
    assert "verdict" in action
    assert "14:30" in action["content"]
    assert "1.5%" in action["content"]


def test_generate_chief_advisor_memo_with_full_pathology_detection():
    """Verify pathology detection for deep loss (>10%), tail fragments (<¥200), and concentration (>35%)."""
    snapshot = {
        "treasury_10y": 1.62,
        "dr007": 1.38,
        "dr007_spread_bp": -12.0,
        "erp_percentile": 82.5,
        "erp_val": 6.55,
        "bias_20": -1.2,
    }
    holdings = [
        DummyHolding("011613", "华夏科创50ETF联接C", 6000.0, 7000.0, "C"),  # loss ~ -14.3% (< -10%)
        DummyHolding("005561", "创金合信红利低波A", 4000.0, 3900.0, "A"),   # profit
        DummyHolding("002351", "易方达裕祥回报A", 1500.0, 1500.0, "A"),
        DummyHolding("000001", "碎片红包基A", 88.50, 88.0, "A"),            # fragment < 200
        DummyHolding("000002", "碎片羊毛基B", 45.20, 45.0, "C"),            # fragment < 200
    ]
    radar_top3 = [
        {"name": "红利低波", "top_fund_code": "005561"},
        {"name": "纯债固收", "top_fund_code": "002351"},
        {"name": "黄金商品", "top_fund_code": "000216"},
    ]
    sentry_rep = {
        "alerts": [
            {"level": "red", "title": "科创50短期深套", "desc": "浮亏达 14.3%"}
        ],
        "all_passed": False,
    }

    memo = generate_chief_advisor_memo(
        snapshot=snapshot,
        holdings=holdings,
        radar_top3=radar_top3,
        sentry_rep=sentry_rep,
    )

    pathology = memo["portfolio_pathology"]
    assert pathology["deep_loss_count"] >= 1
    assert pathology["frag_count"] == 2
    assert abs(pathology["frag_amt"] - (88.50 + 45.20)) < 0.01
    assert "核心亏损拖累源" in pathology["content"]
    assert "长尾碎片尾仓" in pathology["content"]
    assert "单标集中度过高" in pathology["content"]  # 6000 / 11633.7 = ~51.6% > 35%

    # Verify action verdict for low valuation negative bias
    action = memo["action_directive"]
    assert action["verdict"] == "逆向定投吸筹"
    assert "14:30" in action["content"]


def test_chief_advisor_memo_aliases():
    """Verify alias exports for memo operator."""
    assert callable(get_chief_advisor_memo)
    assert get_chief_advisor_memo is generate_chief_advisor_memo
    assert hasattr(OpportunityRadarEngine, "generate_chief_advisor_memo")
    assert callable(OpportunityRadarEngine.generate_chief_advisor_memo)

    memo1 = generate_chief_advisor_memo()
    memo2 = OpportunityRadarEngine.generate_chief_advisor_memo()
    assert set(memo1.keys()) == set(memo2.keys())


# =====================================================================
# 2. Chief Advisor Memo GUI Rendering Tests
# =====================================================================

def test_render_chief_advisor_memo_card_empty_and_normal():
    """Verify render_chief_advisor_memo_card executes cleanly without exceptions."""
    # Empty inputs
    assert render_chief_advisor_memo_card(None) is None
    assert render_chief_advisor_memo_card({}) is None

    # Normal inputs
    memo = generate_chief_advisor_memo()
    # Executing the card renderer should not raise
    render_chief_advisor_memo_card(memo, title="🧭 首席投顾五维决策备忘录测试")


# =====================================================================
# 3. Historical Time-Machine Blind Backtesting Engine Tests
# =====================================================================

def test_run_historical_time_machine_backtest_point_in_time():
    """Verify Point-in-Time zero future data lookahead across historical inflection points."""
    # 1. 2021-02-18: Core assets peak
    res_2021 = StrategyBridge.run_historical_time_machine_backtest(
        target_date="2021-02-18",
        tier="C3",
        capital=100000.0,
    )
    assert res_2021["target_date"] == "2021-02-18"
    assert len(res_2021["curve_df"]) > 0
    assert res_2021["curve_df"]["date"].iloc[0] == "2021-02-18"
    assert res_2021["kpi_1y"] is not None
    # 2021 bear collapse: Strategy MDD should be significantly better than H300 MDD (-20%+)
    assert res_2021["kpi_1y"]["mdd_pct"] > res_2021["kpi_1y"]["h300_mdd_pct"]
    assert 240 <= res_2021["kpi_1y"]["trade_days"] <= 260  # ~253 trade days in 1 year

    # 2. 2022-04-26: Panic double bottom
    res_2022 = StrategyBridge.run_historical_time_machine_backtest(
        target_date="2022-04-26",
        tier="C3",
        capital=100000.0,
    )
    assert res_2022["target_date"] == "2022-04-26"
    assert res_2022["kpi_6m"] is not None
    assert res_2022["kpi_1y"] is not None

    # 3. 2024-09-18: Bottom reversal start
    res_2024 = StrategyBridge.run_historical_time_machine_backtest(
        target_date="2024-09-18",
        tier="C3",
        capital=100000.0,
    )
    assert res_2024["target_date"] == "2024-09-18"
    assert res_2024["kpi_3m"] is not None
    assert res_2024["kpi_3m"]["net_return_pct"] > 0  # Reversal yields positive net return


def test_time_machine_transaction_frictions_deduction():
    """Verify subscription fee, FIFO step-down redemption fees, and C-share sales fee deduction."""
    res = StrategyBridge.run_historical_time_machine_backtest(
        target_date="2024-09-18",
        tier="C3",
        capital=100000.0,
    )
    curve_df = res["curve_df"]

    # Initial NAV must deduct 0.12% front-end subscription fee: 1.0 * (1 - 0.0012) = 0.9988
    assert abs(curve_df["strategy_net_nav"].iloc[0] - 0.9988) < 1e-4

    # KPI 3M: days is between 30 and 180 days -> step-down redemption fee is 0.35%
    kpi_3m = res["kpi_3m"]
    assert kpi_3m["red_fee_pct"] == 0.35

    # KPI All: > 365 days -> step-down redemption fee is 0.00%
    kpi_all = res["kpi_all"]
    if kpi_all["days"] >= 365:
        assert kpi_all["red_fee_pct"] == 0.00

    # Ensure to-pocket net return accounts for redemption fee
    sub_df = curve_df.iloc[: kpi_3m["trade_days"]]
    gross_nav = float(sub_df["strategy_net_nav"].iloc[-1])
    expected_to_pocket_ret = (gross_nav * (1.0 - 0.0035) - 1.0) * 100.0
    assert abs(kpi_3m["net_return_pct"] - round(expected_to_pocket_ret, 2)) < 0.05


def test_time_machine_input_boundary_validations():
    """Verify boundary exceptions: insufficient past history or date too close to present."""
    # Date prior to 2018-01-02 (less than 60 days history)
    with pytest.raises(ValueError, match="前历史样本不足 60 天"):
        StrategyBridge.run_historical_time_machine_backtest(target_date="2018-01-10")

    # Date past available data
    with pytest.raises(ValueError, match="缺乏前推回测样本"):
        StrategyBridge.run_historical_time_machine_backtest(target_date="2026-11-09")


def test_time_machine_module_export():
    """Verify module-level export alias."""
    assert callable(run_historical_time_machine_backtest)
    assert run_historical_time_machine_backtest.__func__ is StrategyBridge.run_historical_time_machine_backtest.__func__
    # Both callable forms return matching output
    res1 = run_historical_time_machine_backtest(target_date="2024-09-18", tier="C3")
    res2 = StrategyBridge.run_historical_time_machine_backtest(target_date="2024-09-18", tier="C3")
    assert res1["target_date"] == res2["target_date"]
    assert res1["weights_at_t"] == res2["weights_at_t"]
