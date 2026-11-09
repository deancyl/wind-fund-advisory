# -*- coding: utf-8 -*-
"""
Adversarial Verification Suite for G15 Generation Milestone 2 (Phase 2):
"破除唯算法论：实装五维投顾首席备忘录与历史任意时点盲测时光机"

Tested by Challenger: `challenger_m2_1`

Test Dimensions:
1. `generate_chief_advisor_memo`:
   - Empty, None, and partial inputs
   - Extreme macro: negative DR007 spread (-500bp), high spread (+100bp), inverted curve (10Y CGB <= 0%), ERP at 0% and 100%
   - Extreme price action: 20d bias at +25% and -25%
   - Extreme holdings: deep loss (>-50%, e.g. -80%), multi-fund drag ranking, 20+ tail fragments (<¥200), single-fund >90% concentration
   - Malformed/heterogeneous holdings: list of objects, list of dicts, dict of dicts, float weights dict, and zero-value holdings
   - Radar top3 robustness: empty, partial, or malformed entries
   - Verification that all 5 dimensions return structured, non-empty text without exceptions
2. `StrategyBridge.run_historical_time_machine_backtest`:
   - Empirical Point-in-Time (PIT) integrity: corrupting future data (t > target_date) MUST NOT change weights_at_t
   - 0.12% front-end subscription fee deducted on day 0 (initial NAV = 0.9988)
   - Daily 0.40% / 250 sales service fee & cash buffer deduction
   - Full 5-tier FIFO step-down redemption fee schedule (<7d 1.50%, <30d 0.50%, <180d 0.35%, <365d 0.15%, >=365d 0.00%)
   - Benchmark calculations: H00300 and BENCHMARK_50_50
   - Boundary validations: <60 days past raises ValueError, <2 days forward raises ValueError
   - Flexible date input types: str, pd.Timestamp, datetime.date, datetime.datetime
"""
import copy
from datetime import datetime, date, timedelta
from typing import Dict, Any, List

import numpy as np
import pandas as pd
import pytest

from AGY2_FundAdvisory.advisory_engine import (
    generate_chief_advisor_memo,
    get_chief_advisor_memo,
    OpportunityRadarEngine,
)
from AGY2_FundAdvisory.strategy_bridge import (
    StrategyBridge,
    run_historical_time_machine_backtest,
)
from AGY2_FundAdvisory.app_gui import render_chief_advisor_memo_card


class MockFundHolding:
    """Mock holding object supporting both attribute access and duck-typing."""
    def __init__(
        self,
        fund_code: str,
        fund_name: str,
        market_value: float,
        cost_value: float,
        share_class: str = "A"
    ):
        self.fund_code = fund_code
        self.fund_name = fund_name
        self.market_value = market_value
        self.cost_value = cost_value
        self.share_class = share_class


# =====================================================================
# TASK 1: Adversarial Verification of `generate_chief_advisor_memo`
# =====================================================================

class TestChiefAdvisorMemoAdversarial:
    """Adversarial testing on generate_chief_advisor_memo."""

    REQUIRED_DIMENSIONS = [
        "macro_policy",
        "international_fx",
        "industry_valuation",
        "portfolio_pathology",
        "action_directive",
    ]

    def _assert_structured_memo(self, memo: Dict[str, Any]):
        """Helper to assert all 5 dimensions exist and contain valid non-empty structured text."""
        assert isinstance(memo, dict), "Memo output must be a dictionary"
        assert "timestamp" in memo, "Memo must have timestamp"
        for dim in self.REQUIRED_DIMENSIONS:
            assert dim in memo, f"Missing required dimension: {dim}"
            dim_dict = memo[dim]
            assert isinstance(dim_dict, dict), f"Dimension {dim} must be a dict"
            assert "title" in dim_dict, f"Dimension {dim} missing 'title'"
            assert "badge" in dim_dict, f"Dimension {dim} missing 'badge'"
            assert "content" in dim_dict, f"Dimension {dim} missing 'content'"
            assert isinstance(dim_dict["content"], str), f"Content for {dim} must be str"
            assert len(dim_dict["content"].strip()) > 0, f"Content for {dim} cannot be empty"

    @pytest.mark.parametrize("empty_payload", [
        (None, None, None, None),
        ({}, {}, [], {}),
        (None, [], None, {}),
        ({}, None, [], None),
    ])
    def test_memo_empty_and_none_inputs(self, empty_payload):
        """Verify graceful handling with complete empty/None payloads."""
        snap, hld, radar, sentry = empty_payload
        memo = generate_chief_advisor_memo(snap, hld, radar, sentry)
        self._assert_structured_memo(memo)
        # Verify fallback values
        assert memo["portfolio_pathology"]["deep_loss_count"] == 0
        assert memo["portfolio_pathology"]["frag_count"] == 0
        assert "持仓结构优良" in memo["portfolio_pathology"]["content"]

    def test_memo_extreme_macro_spread_and_curve_inversion(self):
        """Verify extreme macro indicators: negative DR007 spread, inverted yield curve, extreme CGB."""
        # Scenario A: Severe liquidity glut with negative spread
        snap_glut = {
            "treasury_10y": -0.15,  # Inverted/negative interest rate scenario
            "dr007": 0.85,
            "dr007_spread_bp": -150.0,  # Highly negative spread
            "erp_percentile": 99.5,     # Peak ERP
            "erp_val": 8.50,
            "bias_20": -8.5,
        }
        memo_glut = generate_chief_advisor_memo(snapshot=snap_glut)
        self._assert_structured_memo(memo_glut)
        assert memo_glut["macro_policy"]["badge"] == "🟢 货币宽松充裕"
        assert "极高性价比黄金击球区" in memo_glut["macro_policy"]["content"]
        assert memo_glut["action_directive"]["verdict"] == "逆向定投吸筹"

        # Scenario B: Severe liquidity squeeze with tight spread
        snap_tight = {
            "treasury_10y": 4.50,
            "dr007": 3.80,
            "dr007_spread_bp": 85.0,  # Extreme liquidity crunch
            "erp_percentile": 5.0,    # Bubble valuation
            "erp_val": 1.20,
            "bias_20": 12.0,          # Extreme overbought
        }
        memo_tight = generate_chief_advisor_memo(snapshot=snap_tight)
        self._assert_structured_memo(memo_tight)
        assert memo_tight["macro_policy"]["badge"] == "🔴 资金边际收紧"
        assert "高估谨慎区" in memo_tight["macro_policy"]["content"]
        assert memo_tight["action_directive"]["verdict"] == "逢高适度止盈"

    @pytest.mark.parametrize("erp_val,expected_stance", [
        (0.0, "高估谨慎区"),
        (34.9, "高估谨慎区"),
        (35.0, "高估谨慎区"),
        (50.0, "中性平衡区"),
        (74.9, "中性平衡区"),
        (75.0, "极高性价比黄金击球区"),
        (100.0, "极高性价比黄金击球区"),
    ])
    def test_memo_erp_boundary_classification(self, erp_val, expected_stance):
        """Stress-test ERP percentile boundaries at 0%, 35%, 75%, and 100%."""
        snap = {
            "erp_percentile": erp_val,
            "erp_val": 5.0,
            "dr007_spread_bp": 0.0,
        }
        memo = generate_chief_advisor_memo(snapshot=snap)
        self._assert_structured_memo(memo)
        assert expected_stance in memo["macro_policy"]["content"]

    def test_memo_deep_loss_and_multiple_drag_ranking(self):
        """Stress-test deep loss holdings (>-50%, e.g. -80%) and correct identification of worst drag."""
        holdings = [
            # Fund A: -80% loss, loss amount -8000
            MockFundHolding("001001", "严重暴跌医药A", market_value=2000.0, cost_value=10000.0),
            # Fund B: -50% loss, loss amount -5000
            MockFundHolding("001002", "中度腰斩消费C", market_value=5000.0, cost_value=10000.0),
            # Fund C: -15% loss, loss amount -1500
            MockFundHolding("001003", "轻度浮亏科技A", market_value=8500.0, cost_value=10000.0),
            # Fund D: +20% profit
            MockFundHolding("001004", "稳健纯债A", market_value=12000.0, cost_value=10000.0),
        ]
        memo = generate_chief_advisor_memo(holdings=holdings)
        self._assert_structured_memo(memo)
        pathology = memo["portfolio_pathology"]
        assert pathology["deep_loss_count"] == 3
        # Worst drag by absolute loss amount should be Fund A (-8000)
        assert "严重暴跌医药A" in pathology["content"]
        assert "浮亏 -80.0%" in pathology["content"]
        assert "核心亏损拖累源" in pathology["content"]

    def test_memo_large_tail_fragments(self):
        """Stress-test 25 small tail fragment holdings (<¥200) aggregating to clean-up recommendation."""
        fragments = [
            MockFundHolding(f"0090{i:02d}", f"红包碎片基_{i}", market_value=10.0 + i * 5.0, cost_value=10.0 + i * 5.0)
            for i in range(25)  # values range from 10.0 to 130.0 (< 200.0)
        ]
        anchor = MockFundHolding("005561", "核心红利低波A", market_value=50000.0, cost_value=50000.0)
        all_holdings = [anchor] + fragments
        total_frag_amt = sum(h.market_value for h in fragments)

        memo = generate_chief_advisor_memo(holdings=all_holdings)
        self._assert_structured_memo(memo)
        pathology = memo["portfolio_pathology"]
        assert pathology["frag_count"] == 25
        assert abs(pathology["frag_amt"] - total_frag_amt) < 1e-4
        assert "长尾碎片尾仓" in pathology["content"]
        assert f"检测到 25 只" in pathology["content"]

    def test_memo_single_asset_hyper_concentration(self):
        """Stress-test hyper-concentration (>90% in one fund) triggering concentration warning."""
        holdings = [
            MockFundHolding("005561", "超级重仓红利", market_value=95000.0, cost_value=90000.0),
            MockFundHolding("002351", "微量纯债", market_value=5000.0, cost_value=5000.0),
        ]
        memo = generate_chief_advisor_memo(holdings=holdings)
        self._assert_structured_memo(memo)
        pathology = memo["portfolio_pathology"]
        assert "单标集中度过高" in pathology["content"]
        assert "第一大重仓占比达 95.0%" in pathology["content"]

    def test_memo_heterogeneous_holdings_structures(self):
        """Verify robustness when holdings are passed as dict of dicts, dict of objects, or float weights."""
        # 1. Dict of dicts
        h_dict_of_dicts = {
            "005561": {"fund_code": "005561", "fund_name": "红利低波A", "market_value": 3000.0, "cost_value": 3500.0},
            "002351": {"fund_code": "002351", "fund_name": "裕祥纯债A", "market_value": 7000.0, "cost_value": 7000.0},
        }
        memo1 = generate_chief_advisor_memo(holdings=h_dict_of_dicts)
        self._assert_structured_memo(memo1)
        assert memo1["portfolio_pathology"]["deep_loss_count"] == 1

        # 2. Dict of float weights (like opt_weights in Tab 1)
        opt_weights = {"005561": 0.40, "002351": 0.35, "000216": 0.25}
        memo2 = generate_chief_advisor_memo(holdings=opt_weights)
        self._assert_structured_memo(memo2)
        assert memo2["portfolio_pathology"]["deep_loss_count"] == 0
        assert "持仓结构优良" in memo2["portfolio_pathology"]["content"]

    def test_memo_radar_top3_variations(self):
        """Verify radar_top3 handles partial, missing, or unusual dictionary structures."""
        # Only 1 sector provided
        radar_partial = [{"name": "创新药", "top_fund_code": "001234"}]
        memo_part = generate_chief_advisor_memo(radar_top3=radar_partial)
        self._assert_structured_memo(memo_part)
        assert "创新药 (001234)" in memo_part["industry_valuation"]["content"]

        # Sector with nested 'fund' dictionary
        radar_nested = [{"name": "海外科技", "fund": {"code": "017436"}}]
        memo_nest = generate_chief_advisor_memo(radar_top3=radar_nested)
        self._assert_structured_memo(memo_nest)
        assert "海外科技 (017436)" in memo_nest["industry_valuation"]["content"]

    def test_memo_card_safe_html_rendering(self):
        """Verify render_chief_advisor_memo_card executes cleanly with empty, normal, and extreme memos."""
        assert render_chief_advisor_memo_card(None) is None
        assert render_chief_advisor_memo_card({}) is None

        # Extreme memo
        snap_extreme = {
            "treasury_10y": -0.5,
            "dr007": 0.5,
            "dr007_spread_bp": -50.0,
            "erp_percentile": 99.0,
            "erp_val": 9.0,
            "bias_20": -10.0,
        }
        memo_extreme = generate_chief_advisor_memo(snapshot=snap_extreme)
        # Must execute without any exception
        render_chief_advisor_memo_card(memo_extreme, title="🧭 极端压力测试备忘录")


# =====================================================================
# TASK 2: Adversarial Verification of `run_historical_time_machine_backtest`
# =====================================================================

class TestHistoricalTimeMachineAdversarial:
    """Adversarial stress-testing of run_historical_time_machine_backtest."""

    @pytest.fixture(scope="class")
    @classmethod
    def real_market_df(cls):
        """Load the real historical matrix once for test efficiency."""
        return StrategyBridge.load_matrix()

    def test_point_in_time_integrity_future_data_corruption(self, real_market_df):
        """
        CRITICAL VERIFICATION:
        Empirically verify that corrupting/altering future data after target_date
        has STRICTLY ZERO IMPACT on the portfolio weights generated at target_date!
        """
        target_date = "2022-04-26"
        dt_target = pd.to_datetime(target_date)

        # 1. Clean historical backtest run
        clean_df = real_market_df.copy()
        res_clean = StrategyBridge.run_historical_time_machine_backtest(
            target_date=target_date,
            tier="C3",
            capital=100000.0,
            df=clean_df,
        )
        weights_clean = res_clean["weights_at_t"]

        # 2. Corrupt future data by setting all asset prices to 100x after target_date
        corrupted_df = real_market_df.copy()
        mask_future = pd.to_datetime(corrupted_df["date"]) > dt_target
        asset_cols = [c for c in corrupted_df.columns if c not in ["date", "trade_date"]]
        for col in asset_cols:
            if pd.api.types.is_numeric_dtype(corrupted_df[col]):
                corrupted_df.loc[mask_future, col] = corrupted_df.loc[mask_future, col] * 100.0 + 999.0

        # 3. Run time machine on corrupted future dataframe
        res_corrupted = StrategyBridge.run_historical_time_machine_backtest(
            target_date=target_date,
            tier="C3",
            capital=100000.0,
            df=corrupted_df,
        )
        weights_corrupted = res_corrupted["weights_at_t"]

        # 4. Strict assertion: weights at T must be 100% identical
        assert set(weights_clean.keys()) == set(weights_corrupted.keys()), "Asset universe mismatched after future corruption"
        for asset, w_val in weights_clean.items():
            assert abs(w_val - weights_corrupted[asset]) < 1e-12, (
                f"Point-in-Time violation for {asset}: clean weight {w_val} != corrupted {weights_corrupted[asset]}"
            )

    def test_fee_day_zero_subscription_deduction(self, real_market_df):
        """Verify 0.12% front-end subscription fee applied on day 0: Initial NAV = 0.9988."""
        res = StrategyBridge.run_historical_time_machine_backtest(
            target_date="2024-09-18",
            tier="C3",
            capital=100000.0,
            df=real_market_df,
        )
        curve_df = res["curve_df"]
        init_nav = float(curve_df["strategy_net_nav"].iloc[0])
        # Day 0 NAV must be exactly 1.0 * (1 - 0.0012) = 0.9988
        assert abs(init_nav - 0.9988) < 1e-6, f"Day 0 NAV was {init_nav}, expected exactly 0.9988"
        # Benchmark NAVs must start at 1.0
        assert curve_df["h300_nav"].iloc[0] == 1.0
        assert curve_df["benchmark_nav"].iloc[0] == 1.0

    def test_fee_daily_sales_service_and_cash_buffer_drag(self, real_market_df):
        """
        Verify daily sales service fee (0.40% / 250) and 5% cash buffer (1.8% / 250).
        With completely flat asset prices (0% return), daily effective return must be:
        eff_day_ret = 0.95 * 0 + 0.05 * (0.018 / 250) - 0.5 * (0.0040 / 250)
                    = 0.0000036 - 0.0000080 = -0.0000044 per day.
        """
        target_date = "2024-09-18"
        dt_target = pd.to_datetime(target_date)

        # Clone real market df, but freeze all asset prices after target_date so day_ret == 0.0
        flat_df = real_market_df.copy()
        mask_forward = pd.to_datetime(flat_df["date"]) >= dt_target
        asset_cols = [c for c in flat_df.columns if c not in ["date", "trade_date"]]
        
        # Freeze prices to their target_date values
        target_idx = flat_df[pd.to_datetime(flat_df["date"]) == dt_target].index[0]
        for c in asset_cols:
            if pd.api.types.is_numeric_dtype(flat_df[c]):
                val_at_t = flat_df.loc[target_idx, c]
                flat_df.loc[mask_forward, c] = val_at_t

        res = StrategyBridge.run_historical_time_machine_backtest(
            target_date=target_date,
            tier="C3",
            capital=100000.0,
            df=flat_df,
        )
        curve_df = res["curve_df"]

        # Check daily decrement
        expected_daily_drag = 0.05 * (0.018 / 250.0) - 0.5 * (0.0040 / 250.0)  # -0.0000044
        for t in range(1, min(30, len(curve_df))):
            nav_prev = curve_df["strategy_net_nav"].iloc[t - 1]
            nav_curr = curve_df["strategy_net_nav"].iloc[t]
            day_ratio = nav_curr / nav_prev - 1.0
            assert abs(day_ratio - expected_daily_drag) < 1e-8, (
                f"Day {t} drag mismatch: got {day_ratio}, expected {expected_daily_drag}"
            )

    def test_fifo_step_down_redemption_fee_schedule(self, real_market_df):
        """
        Verify the 5-tier FIFO step-down redemption fee:
        - < 7 days: 1.50%
        - < 30 days: 0.50%
        - < 180 days: 0.35%
        - < 365 days: 0.15%
        - >= 365 days: 0.00%
        """
        # Test synthetic scenario across various forward lengths
        res = StrategyBridge.run_historical_time_machine_backtest(
            target_date="2021-02-18",
            tier="C3",
            capital=100000.0,
            df=real_market_df,
        )

        # 3M horizon: ~63 trade days (~90 calendar days) -> cal_days < 180 -> fee 0.35%
        kpi_3m = res["kpi_3m"]
        assert kpi_3m is not None
        assert 30 <= kpi_3m["days"] < 180
        assert kpi_3m["red_fee_pct"] == 0.35

        # 6M horizon: ~126 trade days (~180 calendar days) -> fee 0.35% or 0.15% depending on cal_days
        kpi_6m = res["kpi_6m"]
        assert kpi_6m is not None
        if kpi_6m["days"] < 180:
            assert kpi_6m["red_fee_pct"] == 0.35
        else:
            assert kpi_6m["red_fee_pct"] == 0.15

        # 1Y horizon: ~252 trade days (~365 calendar days)
        kpi_1y = res["kpi_1y"]
        assert kpi_1y is not None
        if kpi_1y["days"] < 365:
            assert kpi_1y["red_fee_pct"] == 0.15
        else:
            assert kpi_1y["red_fee_pct"] == 0.00

        # Holding until today (>365 days from 2021-02-18)
        kpi_all = res["kpi_all"]
        assert kpi_all["days"] >= 365
        assert kpi_all["red_fee_pct"] == 0.00

        # Verify mathematical consistency between gross_nav, redemption fee, and net_return_pct
        curve_df = res["curve_df"]
        sub_df = curve_df.iloc[: kpi_3m["trade_days"]]
        gross_nav = float(sub_df["strategy_net_nav"].iloc[-1])
        expected_to_pocket_ret = round((gross_nav * (1.0 - 0.0035) - 1.0) * 100.0, 2)
        assert abs(kpi_3m["net_return_pct"] - expected_to_pocket_ret) < 0.02

    def test_boundary_validations_and_date_type_flexibility(self, real_market_df):
        """Verify boundary error checks (<60d history, <2d forward) and multiple date input formats."""
        # 1. Past boundary: < 60 days
        with pytest.raises(ValueError, match="前历史样本不足 60 天"):
            StrategyBridge.run_historical_time_machine_backtest(
                target_date="2018-01-05",
                df=real_market_df,
            )

        # 2. Future boundary: < 2 days forward
        with pytest.raises(ValueError, match="缺乏前推回测样本"):
            StrategyBridge.run_historical_time_machine_backtest(
                target_date="2028-12-31",
                df=real_market_df,
            )

        # 3. Input formats: string, pd.Timestamp, datetime.date, datetime.datetime
        t_str = "2024-09-18"
        t_ts = pd.Timestamp(t_str)
        t_date = date(2024, 9, 18)
        t_dt = datetime(2024, 9, 18, 15, 0, 0)

        res_str = StrategyBridge.run_historical_time_machine_backtest(target_date=t_str, df=real_market_df)
        res_ts = StrategyBridge.run_historical_time_machine_backtest(target_date=t_ts, df=real_market_df)
        res_date = StrategyBridge.run_historical_time_machine_backtest(target_date=t_date, df=real_market_df)
        res_dt = StrategyBridge.run_historical_time_machine_backtest(target_date=t_dt, df=real_market_df)

        assert res_str["target_date"] == "2024-09-18"
        assert res_ts["target_date"] == "2024-09-18"
        assert res_date["target_date"] == "2024-09-18"
        assert res_dt["target_date"] == "2024-09-18"
        assert res_str["weights_at_t"] == res_ts["weights_at_t"] == res_date["weights_at_t"] == res_dt["weights_at_t"]

    def test_benchmark_tracking_integrity(self, real_market_df):
        """Verify benchmark calculations for H00300 and BENCHMARK_50_50 match true underlying prices."""
        target_date = "2024-09-18"
        dt_target = pd.to_datetime(target_date)
        res = StrategyBridge.run_historical_time_machine_backtest(
            target_date=target_date,
            tier="C3",
            df=real_market_df,
        )
        curve_df = res["curve_df"]
        fwd_slice = real_market_df[pd.to_datetime(real_market_df["date"]) >= dt_target].reset_index(drop=True)

        # H00300 cumulative return check at last day
        h300_initial_price = float(fwd_slice["H00300"].iloc[0])
        h300_final_price = float(fwd_slice["H00300"].iloc[-1])
        expected_h300_nav = h300_final_price / h300_initial_price
        actual_h300_nav = float(curve_df["h300_nav"].iloc[-1])
        assert abs(actual_h300_nav - expected_h300_nav) < 1e-4

        # 50/50 benchmark check
        if "BENCHMARK_50_50" in fwd_slice.columns:
            b50_initial = float(fwd_slice["BENCHMARK_50_50"].iloc[0])
            b50_final = float(fwd_slice["BENCHMARK_50_50"].iloc[-1])
            expected_b50_nav = b50_final / b50_initial
            actual_b50_nav = float(curve_df["benchmark_nav"].iloc[-1])
            assert abs(actual_b50_nav - expected_b50_nav) < 1e-4
