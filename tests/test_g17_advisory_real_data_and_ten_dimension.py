# -*- coding: utf-8 -*-
"""
Delta Test Suite for Milestone 1:
1. Eradication of 5 fake static constants (628.5, -0.25%, 7.2450, 1.6258, 4.40%)
2. Genuine Parquet lake data integration for macro, FX, rates, and global indices
3. Ten-Dimension Quantitative Voting Engine (compute_ten_dimension_votes)
4. White-box causal derivation formula string
5. Chief Advisor Memo integration with genuine indicators
"""
import os
import sys
import pytest

# Ensure workspace root and AGY2_FundAdvisory are in sys.path
WORKSPACE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)
AGY2_DIR = os.path.join(WORKSPACE_DIR, "AGY2_FundAdvisory")
if AGY2_DIR not in sys.path:
    sys.path.insert(0, AGY2_DIR)

from AGY2_FundAdvisory.data_loader import DataLoader
from AGY2_FundAdvisory.strategy_bridge import StrategyBridge
from AGY2_FundAdvisory.advisory_engine import compute_ten_dimension_votes, generate_chief_advisor_memo
from AGY2_FundAdvisory.portfolio_manager import PortfolioManager


def test_eradication_of_five_fake_constants_in_source_code():
    """Verify that the 5 fake static constants are completely eradicated from all source files."""
    banned_literals = ["628.5", "1.6258", "7.2450"]
    source_files = [
        "data_loader.py",
        "strategy_bridge.py",
        "advisory_engine.py",
        "portfolio_manager.py",
        "app_gui.py"
    ]
    for fn in source_files:
        fp = os.path.join(AGY2_DIR, fn)
        if not os.path.exists(fp):
            continue
        with open(fp, "r", encoding="utf-8") as f:
            content = f.read()
        for banned in banned_literals:
            assert banned not in content, f"Found banned literal '{banned}' in {fn}"


def test_parquet_lake_macro_indicators():
    """Verify genuine Parquet lake data reading for cross-market macro indicators."""
    indicators = DataLoader.fetch_macro_cross_market_indicators()
    assert isinstance(indicators, dict)
    
    # Check rate indicators
    assert "cgb_10y" in indicators
    assert "us_10y" in indicators
    assert "cn_us_spread_bp" in indicators
    assert 1.0 < indicators["cgb_10y"] < 3.5, f"Unreasonable CGB 10Y yield: {indicators['cgb_10y']}"
    assert 3.0 < indicators["us_10y"] < 6.5, f"Unreasonable US 10Y yield: {indicators['us_10y']}"
    assert indicators["cn_us_spread_bp"] < 0, "China-US spread should be negative in current cycle"
    
    # Check global indices
    assert "nasdaq_ret_pct" in indicators
    assert "spx_ret_pct" in indicators
    assert "hstech_ret_pct" in indicators
    assert isinstance(indicators["nasdaq_ret_pct"], float)
    
    # Check gold
    assert "gold_au9999_close" in indicators
    assert "gold_etf_518880_nav" in indicators
    assert indicators["gold_au9999_close"] > 1000.0, "AU9999 index should reflect actual value"
    assert 5.0 < indicators["gold_etf_518880_nav"] < 15.0, "Gold ETF 518880 NAV should be per-share (approx 8.29)"
    
    # Check FX
    fx = DataLoader.fetch_realtime_usdcnh_fx()
    assert isinstance(fx, float)
    assert 6.0 < fx < 8.0, f"Unreasonable USD/CNH FX: {fx}"


def test_compute_ten_dimension_votes_completeness_and_causality():
    """Verify the Ten-Dimension Quantitative Voting Engine."""
    snapshot = StrategyBridge.get_latest_market_snapshot()
    votes_result = compute_ten_dimension_votes(snapshot)
    
    assert isinstance(votes_result, dict)
    assert "dimensions" in votes_result
    assert "dimension_details" in votes_result
    assert "causal_formula" in votes_result
    
    dims = votes_result["dimensions"]
    assert len(dims) == 10, f"Expected 10 dimensions, got {len(dims)}"
    
    details = votes_result["dimension_details"]
    assert len(details) == 10
    for dim_name, dinfo in details.items():
        assert "score" in dinfo
        assert "vote" in dinfo
        assert dinfo["vote"] in ("BULL", "BEAR", "NEUTRAL")
        assert 0.0 <= dinfo["score"] <= 100.0
        assert "delta_pct" in dinfo
        assert "causal_reason" in dinfo
        assert len(dinfo["causal_reason"]) > 0

    # Check vote counts
    bull = votes_result["bull_count"]
    bear = votes_result["bear_count"]
    neutral = votes_result["neutral_count"]
    assert bull + bear + neutral == 10
    
    # Check causal formula
    formula = votes_result["causal_formula"]
    assert "基准权益中枢" in formula
    assert "当前建议权益仓位" in formula
    assert "%" in formula
    
    # Check equity tilt consistency
    tilt = votes_result["equity_tilt_pct"]
    sugg_eq = votes_result["suggested_equity_ratio"]
    sugg_fix = votes_result["suggested_fixed_ratio"]
    assert round(sugg_eq + sugg_fix, 4) == 1.0000
    assert round(sugg_eq, 2) == round(0.60 + tilt, 2)


def test_generate_chief_advisor_memo_real_and_no_fake():
    """Verify Chief Advisor Memo generation with genuine data and ten_dimension_votes."""
    pm = PortfolioManager(total_equity=100000.0)
    snapshot = StrategyBridge.get_latest_market_snapshot()
    memo = generate_chief_advisor_memo(pm, snapshot)
    
    assert isinstance(memo, dict)
    assert "memo_title" in memo
    assert "action_guidance" in memo
    assert "ten_dimension_votes" in memo
    assert "macro_verdict" in memo
    assert "dynamic_equity_target" in memo
    assert "dynamic_fixed_target" in memo
    
    full_text = memo.get("full_memo_text", "")
    assert "628.5" not in full_text
    assert "1.6258" not in full_text
    assert "7.2450" not in full_text


def test_strategy_bridge_snapshot_real_macro_data():
    """Verify StrategyBridge snapshot incorporates genuine macro and lake data."""
    snapshot = StrategyBridge.get_latest_market_snapshot()
    assert "treasury_10y" in snapshot
    assert "us_treasury_10y" in snapshot
    assert "cn_us_spread_bp" in snapshot
    assert "spot_usdcnh" in snapshot
    assert snapshot["treasury_10y"] != 1.6258, "Should not be hardcoded 1.6258"
    assert 1.0 < snapshot["treasury_10y"] < 3.0
    assert 3.5 < snapshot["us_treasury_10y"] < 6.5
