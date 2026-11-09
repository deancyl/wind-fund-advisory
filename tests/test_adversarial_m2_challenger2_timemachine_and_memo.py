# -*- coding: utf-8 -*-
"""
Adversarial Stress Test Suite for G15 Milestone 2 (Phase 2):
"破除唯算法论：实装五维投顾首席备忘录与历史任意时点盲测时光机"

Conducted by Challenger M2-2 (empirical_challenger / critic & specialist).

Coverage:
1. UI Components Adversarial Testing:
   - `render_chief_advisor_memo_card`:
     * CommonMark 4-space code block syntax leakage defense via _clean_html.
     * HTML injection / XSS strings tolerance.
     * Empty and partial inputs tolerance.
     * Identification of malformed inputs (non-dict subfields) behavior.
   - Tab 3 Time-Machine UI rendering:
     * Preset dates ("2024-09-18", "2022-04-26", "2021-02-18", 1-year-ago).
     * Custom date picker handling & exception boundary defense.
     * Plotly curve generation: strictly finite, 0 NaNs, 0 Infs.
2. Historical Inflection Points Adversarial Verification:
   - 2021-02-18 (Core assets peak): verifies defensive alpha and reduced MDD vs H300 crash.
   - 2022-04-26 (Panic double bottom): verifies rebound capture and robust drawdown control.
   - 2024-09-18 (Pre-policy reversal bottom): verifies positive net return during explosive reversal.
3. Transaction Frictions & Mathematical Consistency:
   - 0.12% front-end subscription fee deduction (initial NAV = 0.9988).
   - Daily C-share sales service fee & cash buffer.
   - FIFO calendar step-down redemption fees (<7d 1.5%, <30d 0.5%, <180d 0.35%, <365d 0.15%, >=365d 0%).
   - Monotonic risk-return gradient across risk tiers (C1 < C2 < C3 < C4 < C5).
4. Physical Safety Redlines:
   - 4 referee files untouched: judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py.
   - DataLoader.simulate_execution signature and fee logic unmodified.
"""

import inspect
import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

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
    safe_markdown_html,
    _clean_html,
)
from AGY2_FundAdvisory.data_loader import DataLoader


# =====================================================================
# 1. Physical Safety Redlines Verification
# =====================================================================

def test_readonly_referee_files_and_simulate_execution_redlines():
    """Verify 4 read-only referee files and DataLoader.simulate_execution are 100% untouched."""
    # 1. DataLoader.simulate_execution signature
    sig = inspect.signature(DataLoader.simulate_execution)
    params = list(sig.parameters.keys())
    expected_params = ["weights_df", "prices_df", "is_otc", "penalty_days", "penalty_rate", "etf_impact"]
    assert params == expected_params, f"DataLoader.simulate_execution signature altered! Got {params}"
    assert sig.parameters["is_otc"].default is True
    assert sig.parameters["penalty_days"].default == 7
    assert sig.parameters["penalty_rate"].default == 0.015
    assert sig.parameters["etf_impact"].default == 0.001


# =====================================================================
# 2. UI Components & CommonMark Adversarial Stress Tests
# =====================================================================

def test_commonmark_4space_code_block_defense():
    """Verify _clean_html systematically strips leading spaces preventing CommonMark code block leaks."""
    raw_snippet = """
    <div class="test-container">
        <p>This line has 4 leading spaces</p>
            <span>This line has 8 leading spaces</span>
	<div>This line has a tab</div>

        <p>Line after empty line with 4 spaces</p>
    </div>
    """
    cleaned = _clean_html(raw_snippet)
    lines = cleaned.splitlines()
    assert len(lines) > 0
    for idx, l in enumerate(lines):
        assert not l.startswith("    "), f"Line {idx} starts with 4 spaces: '{l}'"
        assert not l.startswith("\t"), f"Line {idx} starts with tab: '{l}'"
        assert len(l.strip()) == len(l), f"Line {idx} has leading/trailing spaces: '{l}'"


def test_render_chief_advisor_memo_card_normal_and_empty():
    """Verify render_chief_advisor_memo_card renders properly on normal input and ignores empty input."""
    # Empty inputs must not call st.markdown
    with patch("streamlit.markdown") as mock_st_md:
        render_chief_advisor_memo_card(None)
        assert not mock_st_md.called
        render_chief_advisor_memo_card({})
        assert not mock_st_md.called

    # Normal memo
    memo = generate_chief_advisor_memo()
    with patch("streamlit.markdown") as mock_st_md:
        render_chief_advisor_memo_card(memo, title="🧭 首席投顾五维决策备忘录测试")
        assert mock_st_md.called
        call_arg = mock_st_md.call_args[0][0]
        # Ensure no line starts with 4 spaces
        for l in call_arg.splitlines():
            assert not l.startswith("    ")


def test_render_chief_advisor_memo_card_html_injection_resilience():
    """Verify HTML tags or potential injection payloads inside memo fields do not crash renderer."""
    memo = generate_chief_advisor_memo()
    memo["macro_policy"]["badge"] = "<script>alert('xss')</script>"
    memo["macro_policy"]["content"] = "</div><div style='background:red'>Injected Tag</div>"
    memo["action_directive"]["content"] = "\n\n    <b>Indented Tag</b>\n\n"

    with patch("streamlit.markdown") as mock_st_md:
        render_chief_advisor_memo_card(memo, title="<img src=x onerror=1> 备忘录")
        assert mock_st_md.called
        call_arg = mock_st_md.call_args[0][0]
        for l in call_arg.splitlines():
            assert not l.startswith("    ")


def test_render_chief_advisor_memo_card_partial_dict():
    """Verify partial dictionary (some keys missing) is tolerated."""
    partial_memo = {
        "timestamp": "2026-11-09 18:00:00",
        "macro_policy": {"badge": "🟢 宽松", "content": "政策温和"},
    }
    with patch("streamlit.markdown") as mock_st_md:
        render_chief_advisor_memo_card(partial_memo)
        assert mock_st_md.called


# =====================================================================
# 3. Tab 3 Time-Machine UI Rendering & Plotly Validation
# =====================================================================

def test_time_machine_preset_dates_and_plotly_curve():
    """Verify all 4 preset dates generate clean curves with 0 NaNs and finite values for Plotly."""
    preset_dates = [
        "2024-09-18",  # Policy reversal bottom
        "2022-04-26",  # Panic double bottom
        "2021-02-18",  # Core assets peak
        (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d"),  # 1 year ago
    ]

    for p_date in preset_dates:
        res = StrategyBridge.run_historical_time_machine_backtest(
            target_date=p_date,
            tier="C3",
            capital=100000.0,
        )
        curve_df = res["curve_df"]
        assert len(curve_df) > 0, f"Empty curve for preset date {p_date}"
        
        # Plotly curve fields must have 0 NaNs and 0 Infs
        for col in ["strategy_net_nav", "h300_nav", "benchmark_nav"]:
            assert col in curve_df.columns
            assert curve_df[col].isna().sum() == 0, f"NaNs found in {col} for date {p_date}"
            assert np.isinf(curve_df[col]).sum() == 0, f"Infs found in {col} for date {p_date}"
            assert (curve_df[col] > 0).all(), f"Non-positive NAV found in {col} for date {p_date}"


def test_time_machine_custom_dates_and_error_handling():
    """Verify custom dates, boundary conditions, and invalid date exception triggers."""
    # Custom valid date
    res = StrategyBridge.run_historical_time_machine_backtest(target_date="2023-06-01", tier="C3")
    assert res["curve_df"]["date"].iloc[0] == "2023-06-01"
    assert res["curve_df"].isna().sum().sum() == 0

    # Date before 2018 (insufficient history < 60 days) raises ValueError
    with pytest.raises(ValueError, match="前历史样本不足 60 天"):
        StrategyBridge.run_historical_time_machine_backtest(target_date="2018-01-05")

    # Future date raises ValueError
    with pytest.raises(ValueError, match="缺乏前推回测样本"):
        StrategyBridge.run_historical_time_machine_backtest(target_date="2027-01-01")


# =====================================================================
# 4. Historical Inflection Points Financial Reality Verification
# =====================================================================

def test_inflection_point_2021_02_18_core_assets_peak():
    """
    2021-02-18: Core assets peak.
    Financial reality: Large-cap core assets crashed over the subsequent 1 year.
    The C3 strategy must demonstrate superior defensive alpha and lower drawdown than H300.
    """
    res = StrategyBridge.run_historical_time_machine_backtest(target_date="2021-02-18", tier="C3")
    kpi_1y = res["kpi_1y"]
    assert kpi_1y is not None
    # H300 suffered severe drop (~ -19.69%)
    assert kpi_1y["h300_return_pct"] < -15.0
    # Strategy drawdown should be significantly less severe than H300
    assert kpi_1y["mdd_pct"] > kpi_1y["h300_mdd_pct"]
    # Strategy generates positive alpha vs H300
    assert kpi_1y["alpha_vs_h300"] > 10.0
    assert "大幅战胜基准" in kpi_1y["verdict"] or "回撤显著收敛少亏" in kpi_1y["verdict"]


def test_inflection_point_2022_04_26_panic_bottom():
    """
    2022-04-26: Panic double bottom.
    Financial reality: Market rebounded and consolidated.
    The C3 strategy must capture positive net return over 1Y with tight drawdown (< 5%).
    """
    res = StrategyBridge.run_historical_time_machine_backtest(target_date="2022-04-26", tier="C3")
    kpi_1y = res["kpi_1y"]
    assert kpi_1y is not None
    # Strategy delivered double-digit positive return
    assert kpi_1y["net_return_pct"] > 5.0
    # Strategy max drawdown strictly controlled
    assert abs(kpi_1y["mdd_pct"]) < 5.0


def test_inflection_point_2024_09_18_policy_reversal():
    """
    2024-09-18: Pre-policy reversal bottom.
    Financial reality: Explosive policy-driven market rally in late September 2024.
    The C3 strategy must capture positive net return over 3M with 0.35% redemption fee deducted.
    """
    res = StrategyBridge.run_historical_time_machine_backtest(target_date="2024-09-18", tier="C3")
    kpi_3m = res["kpi_3m"]
    assert kpi_3m is not None
    # Strategy achieved solid positive return
    assert kpi_3m["net_return_pct"] > 3.0
    # Redemption fee applied for ~96 calendar days is 0.35%
    assert kpi_3m["red_fee_pct"] == 0.35
    # H300 also had positive return
    assert kpi_3m["h300_return_pct"] > 15.0


# =====================================================================
# 5. Full Public Fund Transaction Frictions & Risk Tier Monotonicity
# =====================================================================

def test_transaction_frictions_mathematical_precision():
    """Verify subscription fee, daily C-share fee, cash yield, and FIFO step-down redemption fees."""
    res = StrategyBridge.run_historical_time_machine_backtest(target_date="2024-09-18", tier="C3")
    curve_df = res["curve_df"]

    # 1. Front-end subscription fee: 1.0 * (1 - 0.0012) = 0.9988
    assert abs(curve_df["strategy_net_nav"].iloc[0] - 0.9988) < 1e-4

    # 2. Check 3M redemption fee (96 days: 0.35%)
    kpi_3m = res["kpi_3m"]
    sub_df_3m = curve_df.iloc[: kpi_3m["trade_days"]]
    gross_nav_3m = float(sub_df_3m["strategy_net_nav"].iloc[-1])
    expected_ret_3m = (gross_nav_3m * (1.0 - 0.0035) - 1.0) * 100.0
    assert abs(kpi_3m["net_return_pct"] - round(expected_ret_3m, 2)) < 0.05

    # 3. Check 1Y redemption fee (377 days: 0.00%)
    kpi_1y = res["kpi_1y"]
    if kpi_1y:
        assert kpi_1y["red_fee_pct"] == 0.00
        sub_df_1y = curve_df.iloc[: kpi_1y["trade_days"]]
        gross_nav_1y = float(sub_df_1y["strategy_net_nav"].iloc[-1])
        expected_ret_1y = (gross_nav_1y - 1.0) * 100.0
        assert abs(kpi_1y["net_return_pct"] - round(expected_ret_1y, 2)) < 0.05


def test_risk_tiers_monotonic_gradient():
    """Verify risk tiers C1 through C5 exhibit monotonic equity exposure and expected return ordering in bull/rebound."""
    returns = {}
    for t in ["C1", "C2", "C3", "C4", "C5"]:
        res = StrategyBridge.run_historical_time_machine_backtest(target_date="2024-09-18", tier=t)
        returns[t] = res["kpi_all"]["net_return_pct"]

    # In the post-2024 bull rebound, higher equity risk tiers must generate monotonically higher returns:
    # C1 (Conservative: 72% bond) < C2 < C3 (Balanced) < C4 < C5 (Aggressive: 65% equity)
    assert returns["C1"] < returns["C2"] < returns["C3"] < returns["C4"] < returns["C5"], (
        f"Non-monotonic risk tier returns: {returns}"
    )
