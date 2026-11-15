# -*- coding: utf-8 -*-
"""
Empirical Adversarial Stress Test Suite for Milestone 2 Features 9, 10, 11
Author: Challenger 2 (EMPIRICAL CHALLENGER)
Target Files:
  - AGY2_FundAdvisory/strategy_bridge.py
  - AGY2_FundAdvisory/portfolio_manager.py
"""

import ast
import inspect
import math
import sys
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

# Ensure workspace packages are resolvable
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "AGY2_FundAdvisory"))

from AGY2_FundAdvisory.strategy_bridge import StrategyBridge, strategy_fn_for_tier
from AGY2_FundAdvisory.portfolio_manager import (
    parse_smart_text_holdings,
    parse_screenshot_ocr_holdings,
    MultiLedgerManager,
    CORE_STRATEGY_POOL,
    EXTENDED_FUND_CATALOG
)


# ============================================================================
# 1. Feature 9: Rolling DCA 3Y Blind Backtest Stress & Invariant Tests
# ============================================================================

class TestFeature9AdversarialRollingDCA:
    """Adversarial stress-testing of calculate_rolling_dca_3y_backtest."""

    @pytest.mark.parametrize("freq, min_periods", [
        ("bi-monthly", 18),
        ("BI-MONTHLY", 18),
        ("quarterly", 12),
        ("QUARTER", 12),
        ("quarterly_rolling", 12),
        ("unrecognized_freq", 18),  # should gracefully fall back to 18
    ])
    def test_total_periods_lower_bound_and_case_insensitivity(self, freq: str, min_periods: int):
        """Verify that total_periods >= 12 across standard and edge-case frequency inputs."""
        res = StrategyBridge.calculate_rolling_dca_3y_backtest(frequency=freq)
        assert res is not None
        assert "total_periods" in res
        assert res["total_periods"] >= 12, f"Expected total_periods >= 12, got {res['total_periods']}"
        assert res["total_periods"] == min_periods, f"Expected {min_periods}, got {res['total_periods']}"
        assert len(res["periods"]) == res["total_periods"]

    @pytest.mark.parametrize("tier", ["C1", "C2", "C3", "C4", "C5"])
    def test_win_rate_strictly_in_unit_interval_all_tiers(self, tier: str):
        """Verify that win_rate_180d and win_rate_365d are mathematically strictly bounded within [0.0, 1.0]."""
        res = StrategyBridge.calculate_rolling_dca_3y_backtest(frequency="quarterly", tier=tier)
        w180 = res["win_rate_180d"]
        w365 = res["win_rate_365d"]
        assert 0.0 <= w180 <= 1.0, f"Tier {tier} win_rate_180d out of bounds: {w180}"
        assert 0.0 <= w365 <= 1.0, f"Tier {tier} win_rate_365d out of bounds: {w365}"
        assert abs(res["win_rate_180d_pct"] - round(w180 * 100.0, 2)) < 1e-4
        assert abs(res["win_rate_365d_pct"] - round(w365 * 100.0, 2)) < 1e-4

    def test_alpha_exact_mathematical_consistency(self):
        """Verify that alpha calculations strictly match Strategy Return minus CSI 300 Return."""
        res = StrategyBridge.calculate_rolling_dca_3y_backtest(frequency="bi-monthly")

        # Global aggregate consistency
        avg_ret_180 = res["avg_net_return_180d_pct"]
        avg_h300_180 = res["avg_h300_return_180d_pct"]
        expected_alpha_180 = round(avg_ret_180 - avg_h300_180, 2)
        assert abs(res["alpha_vs_csi300_180d"] - expected_alpha_180) < 1e-4, (
            f"Alpha 180 mismatch: got {res['alpha_vs_csi300_180d']}, expected {expected_alpha_180}"
        )

        avg_ret_365 = res["avg_net_return_365d_pct"]
        avg_h300_365 = res["avg_h300_return_365d_pct"]
        expected_alpha_365 = round(avg_ret_365 - avg_h300_365, 2)
        assert abs(res["alpha_vs_csi300_365d"] - expected_alpha_365) < 1e-4, (
            f"Alpha 365 mismatch: got {res['alpha_vs_csi300_365d']}, expected {expected_alpha_365}"
        )

        # Period-by-period consistency
        for p in res["periods"]:
            if p["return_180d_pct"] is not None and p["h300_return_180d_pct"] is not None:
                exp_p_alpha = round(p["return_180d_pct"] - p["h300_return_180d_pct"], 2)
                assert abs(p["alpha_180d_pct"] - exp_p_alpha) < 1e-4, (
                    f"Period {p['period_idx']} alpha 180 mismatch: {p['alpha_180d_pct']} vs {exp_p_alpha}"
                )
            if p["return_365d_pct"] is not None and p["h300_return_365d_pct"] is not None:
                exp_p_alpha = round(p["return_365d_pct"] - p["h300_return_365d_pct"], 2)
                assert abs(p["alpha_365d_pct"] - exp_p_alpha) < 1e-4, (
                    f"Period {p['period_idx']} alpha 365 mismatch: {p['alpha_365d_pct']} vs {exp_p_alpha}"
                )

    def test_strict_zero_lookahead_bias_empirical_perturbation(self):
        """
        Adversarial zero-lookahead test:
        Take a point-in-time slice. If we perturb future data by 10x, the weights
        generated for that date MUST remain 100% identical.
        """
        df_real = StrategyBridge.load_matrix()
        test_idx = len(df_real) - 200

        # Run 1: unperturbed
        slice_unperturbed = df_real.iloc[:test_idx + 1].copy()
        w_clean = strategy_fn_for_tier(slice_unperturbed, tier="C3")

        # Run 2: create future-poisoned DataFrame where all future rows are 10x higher
        df_poisoned = df_real.copy()
        numeric_cols = [c for c in df_poisoned.columns if c not in ["date", "trade_date"]]
        df_poisoned.loc[df_poisoned.index > test_idx, numeric_cols] *= 10.0

        # Now slice at test_idx as calculate_rolling_dca_3y_backtest does: df.iloc[:s_idx + 1]
        slice_from_poisoned = df_poisoned.iloc[:test_idx + 1].copy()
        w_poisoned = strategy_fn_for_tier(slice_from_poisoned, tier="C3")

        assert w_clean == w_poisoned, "Lookahead detected: weights changed when future data was poisoned!"

    def test_fee_deduction_invariants_under_flat_market(self):
        """
        Synthesize a 1000-day flat market (0% daily return).
        Net return after 180d and 365d MUST BE NEGATIVE due to fee deduction (sub fee, mgmt fee, C fee).
        """
        dates = pd.date_range("2022-01-01", periods=1000, freq="B")
        flat_df = pd.DataFrame({
            "date": dates,
            "H00300": 100.0,
            "H11009": 100.0,
            "AU9999": 100.0,
            "H30269": 100.0,
            "H00922": 100.0,
            "STAR50_STITCH": 100.0,
            "SPX_CNY": 100.0,
            "H00852": 100.0,
            "H00905": 100.0
        })
        res = StrategyBridge.calculate_rolling_dca_3y_backtest(frequency="quarterly", df=flat_df)
        assert res["total_periods"] >= 12
        # Under flat prices, all evaluated periods must have net_return < 0 due to fees
        for p in res["periods"]:
            if p["return_180d_pct"] is not None:
                assert p["return_180d_pct"] < 0.0, f"Expected fee drag < 0, got {p['return_180d_pct']}"
            if p["return_365d_pct"] is not None:
                assert p["return_365d_pct"] < 0.0, f"Expected fee drag < 0, got {p['return_365d_pct']}"


# ============================================================================
# 2. Feature 10: Mutual Fund Friction Bill Dynamic Metrics & Zero Fake Constants
# ============================================================================

class TestFeature10AdversarialFrictionBill:
    """Adversarial stress-testing of calculate_mutual_fund_friction_bill."""

    def test_dynamic_cagr_and_mdd_across_distinct_portfolios(self):
        """
        Compare pure bond vs pure tech vs combat 29.
        Verify they produce distinct, realistic CAGRs and MDDs with zero pseudo constants.
        """
        # 1. Pure Bond
        bill_bond = StrategyBridge.calculate_mutual_fund_friction_bill({"002351": 1.0})
        # 2. Pure Tech
        bill_tech = StrategyBridge.calculate_mutual_fund_friction_bill({"011613": 1.0})
        # 3. Combat 29
        mlm = MultiLedgerManager.get_instance()
        pm_combat = mlm.get_pm("combat_29_funds")
        weights_combat = {h.fund_code: h.market_value for h in pm_combat.holdings}
        bill_combat = StrategyBridge.calculate_mutual_fund_friction_bill(weights_combat, is_combat_29=True)

        # Assert no old pseudo constants
        FORBIDDEN_CONSTANTS = [16.85, -16.76, -4.52, 22, 3.42]
        for name, bill in [("Bond", bill_bond), ("Tech", bill_tech), ("Combat29", bill_combat)]:
            for fc in FORBIDDEN_CONSTANTS:
                assert bill["cagr_pct"] != fc, f"{name} bill['cagr_pct'] matches pseudo constant {fc}"
                assert bill["mdd_all_pct"] != fc, f"{name} bill['mdd_all_pct'] matches pseudo constant {fc}"

        # Distinct profiles: Tech MDD must be significantly deeper than Bond MDD
        assert bill_tech["mdd_all_pct"] < bill_bond["mdd_all_pct"], (
            f"Tech MDD {bill_tech['mdd_all_pct']} should be worse than Bond MDD {bill_bond['mdd_all_pct']}"
        )
        assert abs(bill_tech["cagr_pct"] - bill_bond["cagr_pct"]) > 1.0, "CAGR should dynamically differ"

    @pytest.mark.parametrize("holding_days, expected_c_rate, expected_a_rate", [
        (0, 0.0150, 0.0150),   # 0 days -> <7d penalty
        (5, 0.0150, 0.0150),   # 5 days -> <7d penalty
        (6, 0.0150, 0.0150),   # 6 days -> <7d penalty
        (7, 0.0050, 0.0050),   # 7 days -> 7-29d tier
        (20, 0.0050, 0.0050),  # 20 days -> 7-29d tier
        (29, 0.0050, 0.0050),  # 29 days -> 7-29d tier
        (30, 0.0000, 0.0035),  # 30 days -> C is free, A is 0.35%
        (179, 0.0000, 0.0035), # 179 days -> C is free, A is 0.35%
        (180, 0.0000, 0.0015), # 180 days -> C is free, A is 0.15%
        (364, 0.0000, 0.0015), # 364 days -> C is free, A is 0.15%
        (365, 0.0000, 0.0000), # 365 days -> both free
    ])
    def test_tiered_redemption_fee_transitions(self, holding_days: int, expected_c_rate: float, expected_a_rate: float):
        """Stress-test exact tiered redemption fee transitions for C-class vs A-class."""
        capital = 100000.0

        # C-class fund: 011613 (华夏科创50联接C)
        bill_c = StrategyBridge.calculate_mutual_fund_friction_bill(
            {"011613": 1.0}, total_capital=capital, holding_days=holding_days
        )
        expected_c_fee = round(capital * expected_c_rate, 2)
        assert abs(bill_c["redemption_fee_yuan"] - expected_c_fee) < 0.1, (
            f"C-class at {holding_days}d: got {bill_c['redemption_fee_yuan']}, expected {expected_c_fee}"
        )

        # A-class fund: 002351 (易方达裕祥回报债券A)
        bill_a = StrategyBridge.calculate_mutual_fund_friction_bill(
            {"002351": 1.0}, total_capital=capital, holding_days=holding_days
        )
        expected_a_fee = round(capital * expected_a_rate, 2)
        assert abs(bill_a["redemption_fee_yuan"] - expected_a_fee) < 0.1, (
            f"A-class at {holding_days}d: got {bill_a['redemption_fee_yuan']}, expected {expected_a_fee}"
        )

    def test_qdii_quota_split_batches_scaling(self):
        """Stress-test QDII daily purchase quota splitting (1000 yuan daily limit)."""
        # 017436 has 1000 yuan daily limit
        # 800 yuan -> 1 batch
        b1 = StrategyBridge.calculate_mutual_fund_friction_bill({"017436": 1.0}, total_capital=800.0)
        assert b1["quota_split_batches"] == 1

        # 1000 yuan -> 1 batch
        b2 = StrategyBridge.calculate_mutual_fund_friction_bill({"017436": 1.0}, total_capital=1000.0)
        assert b2["quota_split_batches"] == 1

        # 1001 yuan -> 2 batches
        b3 = StrategyBridge.calculate_mutual_fund_friction_bill({"017436": 1.0}, total_capital=1001.0)
        assert b3["quota_split_batches"] == 2

        # 4500 yuan -> 5 batches
        b4 = StrategyBridge.calculate_mutual_fund_friction_bill({"017436": 1.0}, total_capital=4500.0)
        assert b4["quota_split_batches"] == 5

    def test_friction_accounting_conservation(self):
        """Verify fen-and-li accounting identity: total_friction == sub + c_srv + redemp + in_transit."""
        weights = {"002351": 0.4, "011613": 0.4, "017436": 0.2}
        bill = StrategyBridge.calculate_mutual_fund_friction_bill(weights, total_capital=30000.0, holding_days=15)

        sub_f = bill["subscription_fee_yuan"]
        c_f = bill["c_service_fee_yuan"]
        red_f = bill["redemption_fee_yuan"]
        drag_f = bill["in_transit_loss_yuan"]
        tot_f = bill["total_friction_yuan"]

        expected_tot = round(sub_f + c_f + red_f + drag_f, 2)
        assert abs(tot_f - expected_tot) < 0.01, f"Accounting break: {tot_f} vs {expected_tot}"

    def test_ast_scan_no_hardcoded_pseudo_constants(self):
        """Static AST scan of calculate_mutual_fund_friction_bill to ensure no hardcoded fake return values."""
        fn_source = inspect.getsource(StrategyBridge.calculate_mutual_fund_friction_bill)
        tree = ast.parse(fn_source)

        FORBIDDEN_NUMBERS = {16.85, -16.76, -4.52, 3.42}
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant):
                val = node.value
                assert val not in FORBIDDEN_NUMBERS, f"Found forbidden hardcoded constant {val} in AST!"


# ============================================================================
# 3. Feature 11: Text & OCR Smart Parsing Edge Cases & Dual-Channel Fusion
# ============================================================================

class TestFeature11AdversarialParsing:
    """Adversarial stress-testing of parse_smart_text_holdings & parse_screenshot_ocr_holdings."""

    def test_a500_index_and_180d_locking_text_parsing(self):
        """Verify: '易方达中证A500ETF联接A 锁定180天 35000元' -> holding_days=180, amount=35000.0."""
        text = "易方达中证A500ETF联接A 锁定180天 35000元"
        items = parse_smart_text_holdings(text)
        assert len(items) == 1
        item = items[0]
        assert "A500" in item["fund_name"] or item["fund_code"] in ["022459", "022460", "022461"]
        assert item["holding_days"] == 180, f"Expected 180 days, got {item['holding_days']}"
        assert abs(item["amount"] - 35000.0) < 0.1, f"Expected 35000.0, got {item['amount']}"
        assert abs(item["market_value"] - 35000.0) < 0.1

    def test_holding_30d_parenthesis_text_parsing(self):
        """Verify: '创金合信红利低波(持有30天) 5000元' -> holding_days=30, amount=5000.0."""
        text = "创金合信红利低波(持有30天) 5000元"
        items = parse_smart_text_holdings(text)
        assert len(items) == 1
        item = items[0]
        assert item["fund_code"] == "005561"
        assert item["holding_days"] == 30, f"Expected 30 days, got {item['holding_days']}"
        assert abs(item["amount"] - 5000.0) < 0.1, f"Expected 5000.0, got {item['amount']}"

    def test_tricky_index_numbers_and_holding_days_interference(self):
        """
        Adversarially challenge strings with tricky numbers:
        '华夏中证1000ETF 锁定1000天 25000元'
        Ensure 1000 (index) and 1000 (days) don't overwrite amount 25000.
        """
        text = "华夏中证1000ETF 锁定1000天 25000元"
        items = parse_smart_text_holdings(text)
        assert len(items) == 1
        item = items[0]
        assert item["holding_days"] == 1000
        assert abs(item["amount"] - 25000.0) < 0.1

    def test_duplicate_rows_deduplication(self):
        """Verify duplicate rows of same fund are cleanly deduplicated."""
        text = """
        005561 创金合信红利低波 5000元
        005561 创金合信红利低波 8000元
        002351 易方达裕祥回报 12000元
        002351 易方达裕祥回报 12000元
        """
        items = parse_smart_text_holdings(text)
        codes = [it["fund_code"] for it in items]
        assert len(codes) == 2, f"Expected 2 unique funds, got {len(codes)}: {codes}"
        assert set(codes) == {"005561", "002351"}

    def test_zero_amount_graceful_handling(self):
        """Verify zero amount does not raise ZeroDivisionError or crash."""
        text = "005561 0元"
        items = parse_smart_text_holdings(text)
        assert len(items) == 1
        # Should gracefully fall back to positive amount (e.g. 10000.0)
        assert items[0]["amount"] > 0
        assert items[0]["shares"] > 0

    def test_micro_amounts_below_100_preserved(self):
        """Verify micro amounts (0.01元, 5元, 12.34元) are preserved and not suppressed by >=100."""
        text = "005561 0.05元"
        items = parse_smart_text_holdings(text)
        assert len(items) == 1
        assert abs(items[0]["amount"] - 0.05) < 0.01
        assert items[0]["shares"] > 0

        text2 = "002351 12.34元"
        items2 = parse_smart_text_holdings(text2)
        assert len(items2) == 1
        assert abs(items2[0]["amount"] - 12.34) < 0.01

    def test_ocr_dual_channel_union_fusion_mock(self):
        """
        Adversarial test for parse_screenshot_ocr_holdings:
        Simulate OCR output where Channel 1 (text stream) captures Fund A (005561),
        and Channel 2 (spatial blocks) captures Fund B (002351) with yesterday_pnl.
        Verify dual-channel union fusion outputs BOTH Fund A and Fund B, with no early exit!
        """
        # Mock slice_long_screenshot_for_ocr to return a dummy slice
        dummy_slice = [("dummy_img", 0)]

        # Mock RapidOCR return value:
        # Box format: [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]
        mock_ocr_boxes = [
            # Fund 1 (005561) in text stream
            ([[10, 10], [100, 10], [100, 30], [10, 30]], "005561 创金合信红利低波 50000元", 0.95),
            # Fund 2 (002351) in spatial block format
            ([[10, 60], [100, 60], [100, 80], [10, 80]], "002351 易方达裕祥回报", 0.95),
            ([[10, 90], [100, 90], [100, 110], [10, 110]], "持有金额 20000 昨日收益 +150", 0.95),
        ]

        class MockOCR:
            def __call__(self, img):
                return mock_ocr_boxes, 0.0

        with patch("portfolio_manager.slice_long_screenshot_for_ocr", return_value=dummy_slice):
            with patch("rapidocr_onnxruntime.RapidOCR", return_value=MockOCR()):
                results = parse_screenshot_ocr_holdings(b"fake_png_data")

        assert results is not None
        result_codes = {r["fund_code"] for r in results}
        # Both funds must be present in the fused result
        assert "005561" in result_codes, "Channel 1 fund 005561 missing from fusion"
        assert "002351" in result_codes, "Channel 2 fund 002351 missing from fusion"
        assert len(results) >= 2, f"Expected at least 2 funds, got {len(results)}"

        # Check that yesterday_pnl was preserved on Fund 2
        f2 = next(r for r in results if r["fund_code"] == "002351")
        assert f2.get("yesterday_pnl") is not None
        assert abs(f2["yesterday_pnl"] - 150.0) < 1.0


if __name__ == "__main__":
    pytest.main(["-v", __file__])
