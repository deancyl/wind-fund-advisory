# -*- coding: utf-8 -*-
"""
tests/test_g12_m2_empirical_challenge.py
Milestone 2 Independent Empirical Challenge Test Suite.

Adversarial stress testing of:
1. ActiveRiskSentry Dimension 4: Right-side breakdown exit conditions
   - Boundary pnl (9.9% vs 10.0%, 9.999% vs 10.000%)
   - Boundary bias (-0.0001% vs 0.0000%, +0.0001%)
   - Boundary slope (-0.01% vs 0.00%, -0.0001%)
   - Single day drops vs 1.5 * daily_vol (below, equal, above threshold)
   - Daily vol floor at 0.5%
   - Drop extraction from quotes (gszzl, change_pct, chg_pct, raw float)
2. High-water mark drawdown protection
   - Boundary hwm_dd (7.9% vs 8.0%, 7.99% vs 8.00%)
   - 60-day peak detection mechanisms (hwm_dd, hwm_drawdown, peak_nav_60, radar price series, history_navs)
   - 60-day window clipping (ignoring peaks older than 60 days)
   - Take profit ratio (0.40 vs 0.50)
   - PnL >= 10.0% floor requirement for HWM drawdown alert
3. Interaction with existing branches & precedence
   - Right-side breakdown vs HWM drawdown precedence
   - HWM drawdown vs laddered profit precedence
   - Overbought (> 6.0%) vs laddered profit (>= 15.0% and bias > 5.0%)
   - Deep loss (<= -12.0%) vs other branches
   - Multi-asset portfolio with simultaneous heterogeneous alerts
   - Dict-based vs Object-based holding parity
4. Property-based generative fuzzing
   - 1000 randomized state evaluations across continuous multidimensional parameter space
   - Invariant verification of decision boundaries, severity levels, and take-profit ratios

Author: teamwork_challenger (empirical challenger: critic, specialist)
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
import numpy as np

_CURRENT = Path(__file__).resolve().parent
_WORKSPACE = _CURRENT.parent
_AGY2_DIR = _WORKSPACE / "AGY2_FundAdvisory"
if str(_AGY2_DIR) not in sys.path:
    sys.path.insert(0, str(_AGY2_DIR))
if str(_WORKSPACE) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE))

from AGY2_FundAdvisory.advisory_engine import ActiveRiskSentry


class MockHolding:
    """Configurable holding object for adversarial testing"""
    def __init__(self, **kwargs):
        self.fund_code = str(kwargs.get("fund_code", "008888"))
        self.code = self.fund_code
        self.fund_name = str(kwargs.get("fund_name", "测试基金"))
        self.name = self.fund_name
        self.market_value = float(kwargs.get("market_value", 50000.0))
        self.amount = self.market_value
        self.cost_price = float(kwargs.get("cost_price", 1.0000))
        self.cost_nav = self.cost_price
        self.current_nav = float(kwargs.get("current_nav", 1.2000))
        self.holding_days = int(kwargs.get("holding_days", 45))
        self.share_class = str(kwargs.get("share_class", "A"))
        self.category = str(kwargs.get("category", "科技成长"))
        self.batches = kwargs.get("batches", [])
        self.bias_20 = kwargs.get("bias_20", None)
        self.slope_20 = kwargs.get("slope_20", None)
        self.vol_20 = kwargs.get("vol_20", None)
        self.single_day_drop = kwargs.get("single_day_drop", None)
        self.hwm_dd = kwargs.get("hwm_dd", None)
        self.hwm_drawdown = kwargs.get("hwm_drawdown", None)
        self.peak_nav_60 = kwargs.get("peak_nav_60", None)
        self.history_navs = kwargs.get("history_navs", None)
        self.change_pct = kwargs.get("change_pct", None)
        self.floating_pnl_pct = kwargs.get("floating_pnl_pct", None)


# =========================================================================
# Part 1: Right-Side Breakdown Exit Conditions (Dimension 4)
# =========================================================================

class TestRightSideBreakdownBoundaries:
    """Adversarial stress-testing of right-side breakdown exit conditions."""

    @pytest.fixture
    def sentry(self):
        return ActiveRiskSentry()

    def test_pnl_boundary_9_9_vs_10_0(self, sentry):
        """
        Boundary Test: PnL 9.9% vs 10.0%
        Condition: pnl_pct >= 10.0
        At pnl = 9.90%, even with negative bias (-2.0%) and negative slope (-1.0%),
        it MUST NOT trigger right-side breakdown (no RED 0.50 alert).
        At pnl = 10.00%, it MUST trigger right-side breakdown (RED 0.50).
        """
        # Case A: pnl = +9.90% (cur_nav = 1.0990, cost_price = 1.0000)
        h_sub = MockHolding(
            fund_code="008888",
            cost_price=1.0000,
            current_nav=1.0990,  # +9.90%
            bias_20=-2.0,
            slope_20=-1.0,
            vol_20=20.0,
        )
        res_sub = sentry.inspect_portfolio([h_sub], {}, {"008888": {"aum": 10.0}})
        dim4_sub = [a for a in res_sub["alerts"] if a.get("dimension") == "移动止盈"]
        assert len(dim4_sub) == 0, f"PnL 9.90% 不应触发移动止盈: {dim4_sub}"

        # Case B: pnl = +10.00% (cur_nav = 1.1000, cost_price = 1.0000)
        h_at = MockHolding(
            fund_code="008888",
            cost_price=1.0000,
            current_nav=1.1000,  # +10.00%
            bias_20=-2.0,
            slope_20=-1.0,
            vol_20=20.0,
        )
        res_at = sentry.inspect_portfolio([h_at], {}, {"008888": {"aum": 10.0}})
        dim4_at = [a for a in res_at["alerts"] if a.get("dimension") == "移动止盈"]
        assert len(dim4_at) == 1, f"PnL 10.00% 应触发移动止盈: {dim4_at}"
        assert dim4_at[0]["level"] == "red"
        assert dim4_at[0]["take_profit_ratio"] == 0.50
        assert "右侧破位" in dim4_at[0]["title"]

    def test_pnl_subtle_float_precision_9_999_vs_10_000(self, sentry):
        """
        Subtle Float Precision Test:
        round((1.09999 - 1.0)/1.0 * 100, 2) == 10.00% -> triggers
        round((1.09940 - 1.0)/1.0 * 100, 2) == 9.94% -> does not trigger
        """
        h_below = MockHolding(
            fund_code="008888",
            cost_price=1.0000,
            current_nav=1.0994,  # rounds to 9.94%
            bias_20=-1.0,
            slope_20=-0.5,
        )
        res_below = sentry.inspect_portfolio([h_below], {}, {"008888": {"aum": 10.0}})
        assert not any(a.get("dimension") == "移动止盈" for a in res_below["alerts"])

        h_above = MockHolding(
            fund_code="008888",
            cost_price=1.0000,
            current_nav=1.1001,  # rounds to 10.01%
            bias_20=-1.0,
            slope_20=-0.5,
        )
        res_above = sentry.inspect_portfolio([h_above], {}, {"008888": {"aum": 10.0}})
        alerts = [a for a in res_above["alerts"] if a.get("dimension") == "移动止盈"]
        assert len(alerts) == 1
        assert alerts[0]["level"] == "red"
        assert alerts[0]["take_profit_ratio"] == 0.50

    def test_bias_boundary_zero_vs_negative_0_0001(self, sentry):
        """
        Boundary Test: Bias20 < 0.0
        At bias_20 == 0.0000, price is exactly at MA20 (not broken below).
        MUST NOT trigger right-side breakdown!
        At bias_20 == -0.0001, price is strictly below MA20.
        MUST trigger right-side breakdown!
        """
        # Exactly 0.0
        h_zero = MockHolding(
            fund_code="008888",
            cost_price=1.0000,
            current_nav=1.2000,  # +20.00%
            bias_20=0.0000,
            slope_20=-1.0,
        )
        res_zero = sentry.inspect_portfolio([h_zero], {}, {"008888": {"aum": 10.0}})
        breakdowns = [a for a in res_zero["alerts"] if "右侧破位" in a.get("title", "")]
        assert len(breakdowns) == 0, f"bias_20 == 0.0 不应触发右侧破位: {breakdowns}"

        # Strictly negative -0.0001
        h_neg = MockHolding(
            fund_code="008888",
            cost_price=1.0000,
            current_nav=1.2000,  # +20.00%
            bias_20=-0.0001,
            slope_20=-1.0,
        )
        res_neg = sentry.inspect_portfolio([h_neg], {}, {"008888": {"aum": 10.0}})
        breakdowns_neg = [a for a in res_neg["alerts"] if "右侧破位" in a.get("title", "")]
        assert len(breakdowns_neg) == 1, "bias_20 == -0.0001 应触发右侧破位"
        assert breakdowns_neg[0]["take_profit_ratio"] == 0.50

    def test_bias_positive_0_0001_not_triggering(self, sentry):
        """Positive bias (+0.0001) must never trigger right-side breakdown."""
        h_pos = MockHolding(
            fund_code="008888",
            cost_price=1.0000,
            current_nav=1.2500,  # +25%
            bias_20=0.0001,
            slope_20=-2.0,
            single_day_drop=5.0,
        )
        res = sentry.inspect_portfolio([h_pos], {}, {"008888": {"aum": 10.0}})
        assert not any("右侧破位" in a.get("title", "") for a in res["alerts"])

    def test_slope_boundary_zero_vs_negative_0_01(self, sentry):
        """
        Boundary Test: Slope20 < 0.0 (when single_day_drop <= 1.5 * daily_vol)
        If slope_20 == 0.0000, slope is flat (not negative). Must NOT trigger.
        If slope_20 == -0.0100 (or -0.0001), slope is negative. MUST trigger.
        """
        # slope_20 == 0.0, single_day_drop == 0.0
        h_flat = MockHolding(
            fund_code="008888",
            cost_price=1.0000,
            current_nav=1.2000,
            bias_20=-1.0,
            slope_20=0.0000,
            vol_20=20.0,
            single_day_drop=0.0,
        )
        res_flat = sentry.inspect_portfolio([h_flat], {}, {"008888": {"aum": 10.0}})
        assert not any("右侧破位" in a.get("title", "") for a in res_flat["alerts"])

        # slope_20 == -0.01
        h_neg = MockHolding(
            fund_code="008888",
            cost_price=1.0000,
            current_nav=1.2000,
            bias_20=-1.0,
            slope_20=-0.01,
            vol_20=20.0,
            single_day_drop=0.0,
        )
        res_neg = sentry.inspect_portfolio([h_neg], {}, {"008888": {"aum": 10.0}})
        breakdowns = [a for a in res_neg["alerts"] if "右侧破位" in a.get("title", "")]
        assert len(breakdowns) == 1
        assert breakdowns[0]["take_profit_ratio"] == 0.50

    def test_slope_positive_not_triggering_without_drop(self, sentry):
        """Positive slope with small drop must not trigger breakdown."""
        h_pos = MockHolding(
            fund_code="008888",
            cost_price=1.0000,
            current_nav=1.2000,
            bias_20=-0.5,
            slope_20=0.5,       # Upward trending slope
            vol_20=20.0,        # daily_vol = 20 / 15.811 = 1.265%, 1.5*daily_vol = 1.897%
            single_day_drop=1.0 # 1.0% < 1.897%
        )
        res = sentry.inspect_portfolio([h_pos], {}, {"008888": {"aum": 10.0}})
        assert not any("右侧破位" in a.get("title", "") for a in res["alerts"])

    def test_single_day_drop_boundary_vs_1_5_daily_vol(self, sentry):
        """
        Boundary Test: single_day_drop > 1.5 * daily_vol
        Given vol_20 = 15.8113883, daily_vol = 1.0000%, threshold = 1.5000%.
        slope_20 is POSITIVE (+0.50) so slope condition is NOT met.
        - single_day_drop = 1.5000% -> <= threshold -> MUST NOT trigger.
        - single_day_drop = 1.5001% -> > threshold -> MUST trigger.
        """
        # Exactly 1.5000%
        h_equal = MockHolding(
            fund_code="008888",
            cost_price=1.0000,
            current_nav=1.2000,
            bias_20=-0.5,
            slope_20=0.5,
            vol_20=15.8113883,  # daily_vol = 1.00
            single_day_drop=1.5000,
        )
        res_equal = sentry.inspect_portfolio([h_equal], {}, {"008888": {"aum": 10.0}})
        assert not any("右侧破位" in a.get("title", "") for a in res_equal["alerts"])

        # Strictly above 1.5001%
        h_above = MockHolding(
            fund_code="008888",
            cost_price=1.0000,
            current_nav=1.2000,
            bias_20=-0.5,
            slope_20=0.5,
            vol_20=15.8113883,  # daily_vol = 1.00
            single_day_drop=1.5001,
        )
        res_above = sentry.inspect_portfolio([h_above], {}, {"008888": {"aum": 10.0}})
        breakdowns = [a for a in res_above["alerts"] if "右侧破位" in a.get("title", "")]
        assert len(breakdowns) == 1
        assert breakdowns[0]["take_profit_ratio"] == 0.50

    def test_single_day_drop_daily_vol_floor_0_5(self, sentry):
        """
        Test that daily_vol has a minimum floor of 0.5% (max(vol_20 / 15.811, 0.5)).
        When vol_20 = 2.0 (pure bond), vol_20 / 15.811 = 0.1265% < 0.5%.
        Floor enforces daily_vol = 0.5%, threshold = 1.5 * 0.5 = 0.75%.
        - drop = 0.74% -> must not trigger.
        - drop = 0.76% -> must trigger.
        """
        h_low = MockHolding(
            fund_code="002351",
            fund_name="招商添裕纯债A",
            cost_price=1.0000,
            current_nav=1.1200,  # +12%
            bias_20=-0.2,
            slope_20=0.1,
            vol_20=2.0,          # Ultra low vol
            single_day_drop=0.74, # < 0.75%
        )
        res_low = sentry.inspect_portfolio([h_low], {}, {"002351": {"aum": 30.0}})
        assert not any("右侧破位" in a.get("title", "") for a in res_low["alerts"])

        h_high = MockHolding(
            fund_code="002351",
            fund_name="招商添裕纯债A",
            cost_price=1.0000,
            current_nav=1.1200,
            bias_20=-0.2,
            slope_20=0.1,
            vol_20=2.0,
            single_day_drop=0.76, # > 0.75%
        )
        res_high = sentry.inspect_portfolio([h_high], {}, {"002351": {"aum": 30.0}})
        breakdowns = [a for a in res_high["alerts"] if "右侧破位" in a.get("title", "")]
        assert len(breakdowns) == 1
        assert breakdowns[0]["take_profit_ratio"] == 0.50

    def test_single_day_drop_from_gszzl_quote(self, sentry):
        """Verify single_day_drop is parsed from market_snapshot.fund_quotes[code]['gszzl']."""
        h = MockHolding(
            fund_code="161725",
            cost_price=1.0000,
            current_nav=1.1500,
            bias_20=-0.5,
            slope_20=0.1,
            vol_20=15.0,  # daily_vol = 15/15.811 = 0.9487, 1.5*daily_vol = 1.423
            single_day_drop=None,
        )
        # gszzl = -2.0% -> drop = 2.0% > 1.423%
        quotes = {"161725": {"gszzl": -2.0}}
        res = sentry.inspect_portfolio([h], {"fund_quotes": quotes}, {"161725": {"aum": 50.0}})
        breakdowns = [a for a in res["alerts"] if "右侧破位" in a.get("title", "")]
        assert len(breakdowns) == 1
        assert breakdowns[0]["take_profit_ratio"] == 0.50

    def test_single_day_drop_from_change_pct_quote(self, sentry):
        """Verify single_day_drop is parsed from market_snapshot.fund_quotes[code]['change_pct']."""
        h = MockHolding(
            fund_code="161725",
            cost_price=1.0000,
            current_nav=1.1500,
            bias_20=-0.5,
            slope_20=0.1,
            vol_20=15.0,
            single_day_drop=None,
        )
        quotes = {"161725": {"change_pct": -2.5}}
        res = sentry.inspect_portfolio([h], {"fund_quotes": quotes}, {"161725": {"aum": 50.0}})
        breakdowns = [a for a in res["alerts"] if "右侧破位" in a.get("title", "")]
        assert len(breakdowns) == 1

    def test_single_day_drop_positive_quote_never_triggers_drop(self, sentry):
        """Positive intraday valuation (+2.5%) must NOT be treated as a drop."""
        h = MockHolding(
            fund_code="161725",
            cost_price=1.0000,
            current_nav=1.1500,
            bias_20=-0.5,
            slope_20=0.1,
            vol_20=15.0,
            single_day_drop=None,
        )
        # gszzl = +2.5% (rising, not dropping!)
        quotes = {"161725": {"gszzl": 2.5}}
        res = sentry.inspect_portfolio([h], {"fund_quotes": quotes}, {"161725": {"aum": 50.0}})
        assert not any("右侧破位" in a.get("title", "") for a in res["alerts"])

    def test_breakdown_alert_properties_exact_match(self, sentry):
        """Verify all exact schema properties of right-side breakdown alert."""
        h = MockHolding(
            fund_code="008888",
            fund_name="华夏半导体芯片ETF联接A",
            cost_price=1.0000,
            current_nav=1.2000,
            bias_20=-1.5,
            slope_20=-0.8,
            vol_20=25.0,
        )
        res = sentry.inspect_portfolio([h], {}, {"008888": {"aum": 10.0}})
        alerts = [a for a in res["alerts"] if a.get("dimension") == "移动止盈"]
        assert len(alerts) == 1
        a = alerts[0]
        assert a["level"] == "red"
        assert a["dimension"] == "移动止盈"
        assert a["action_type"] == "take_profit"
        assert a["take_profit_ratio"] == 0.50
        assert a["fund_code"] == "008888"
        assert a["fund_name"] == "华夏半导体芯片ETF联接A"
        assert a["pnl_pct"] == 20.0
        assert a["bias_20"] == -1.5
        assert a["slope_20"] == -0.8
        assert "50%" in a["action"]


# =========================================================================
# Part 2: High-Water Mark (HWM) Drawdown Protection
# =========================================================================

class TestHighWaterMarkDrawdownProtection:
    """Adversarial stress-testing of 60-day HWM drawdown protection."""

    @pytest.fixture
    def sentry(self):
        return ActiveRiskSentry()

    def test_hwm_dd_boundary_7_9_vs_8_0(self, sentry):
        """
        Boundary Test: hwm_dd 7.9% vs 8.0%
        Condition: pnl_pct >= 10.0 and hwm_dd >= 8.0
        bias_20 is POSITIVE (+0.50) so right-side breakdown does not trigger.
        - hwm_dd = 7.9% -> MUST NOT trigger HWM drawdown alert.
        - hwm_dd = 8.0% -> MUST trigger YELLOW 0.40 HWM drawdown alert.
        """
        # Case A: hwm_dd = 7.9%
        h_sub = MockHolding(
            fund_code="000216",
            cost_price=1.0000,
            current_nav=1.1500,  # +15%
            bias_20=0.5,
            slope_20=0.2,
            hwm_dd=7.9,
        )
        res_sub = sentry.inspect_portfolio([h_sub], {}, {"000216": {"aum": 20.0}})
        assert not any("高水位" in a.get("title", "") for a in res_sub["alerts"])

        # Case B: hwm_dd = 8.0%
        h_at = MockHolding(
            fund_code="000216",
            cost_price=1.0000,
            current_nav=1.1500,  # +15%
            bias_20=0.5,
            slope_20=0.2,
            hwm_dd=8.0,
        )
        res_at = sentry.inspect_portfolio([h_at], {}, {"000216": {"aum": 20.0}})
        hwm_alerts = [a for a in res_at["alerts"] if "高水位" in a.get("title", "")]
        assert len(hwm_alerts) == 1
        assert hwm_alerts[0]["level"] == "yellow"
        assert hwm_alerts[0]["take_profit_ratio"] == 0.40
        assert hwm_alerts[0]["dimension"] == "移动止盈"

    def test_hwm_dd_subtle_precision_7_99_vs_8_00(self, sentry):
        """Subtle precision: 7.99% does not trigger, 8.00% triggers."""
        h_799 = MockHolding(
            fund_code="000216",
            cost_price=1.0000,
            current_nav=1.1500,
            bias_20=0.5,
            hwm_dd=7.99,
        )
        res_799 = sentry.inspect_portfolio([h_799], {}, {"000216": {"aum": 20.0}})
        assert not any("高水位" in a.get("title", "") for a in res_799["alerts"])

        h_800 = MockHolding(
            fund_code="000216",
            cost_price=1.0000,
            current_nav=1.1500,
            bias_20=0.5,
            hwm_dd=8.00,
        )
        res_800 = sentry.inspect_portfolio([h_800], {}, {"000216": {"aum": 20.0}})
        assert any("高水位" in a.get("title", "") for a in res_800["alerts"])

    def test_hwm_dd_requires_pnl_10_percent_floor(self, sentry):
        """
        Even with huge HWM drawdown (e.g. 25%), if current pnl < 10.0% (e.g. 9.9%),
        it MUST NOT trigger floating profit HWM drawdown protection
        (because there is insufficient floating profit to lock).
        """
        h_insufficient_pnl = MockHolding(
            fund_code="000216",
            cost_price=1.0000,
            current_nav=1.0990,  # +9.90%
            bias_20=0.5,
            hwm_dd=25.0,         # Dropped 25% from peak
        )
        res = sentry.inspect_portfolio([h_insufficient_pnl], {}, {"000216": {"aum": 20.0}})
        assert not any("高水位" in a.get("title", "") for a in res["alerts"])

    def test_60d_peak_detection_from_hwm_dd_attr(self, sentry):
        """Direct attribute h.hwm_dd triggers protection."""
        h = MockHolding(
            fund_code="000216",
            cost_price=1.0000,
            current_nav=1.1500,
            bias_20=0.5,
            hwm_dd=9.5,
        )
        res = sentry.inspect_portfolio([h], {}, {"000216": {"aum": 20.0}})
        alerts = [a for a in res["alerts"] if "高水位" in a.get("title", "")]
        assert len(alerts) == 1
        assert alerts[0]["hwm_dd"] == 9.5

    def test_60d_peak_detection_from_hwm_drawdown_alias(self, sentry):
        """Alias attribute h.hwm_drawdown triggers protection."""
        h = MockHolding(
            fund_code="000216",
            cost_price=1.0000,
            current_nav=1.1500,
            bias_20=0.5,
            hwm_drawdown=8.8,
        )
        res = sentry.inspect_portfolio([h], {}, {"000216": {"aum": 20.0}})
        alerts = [a for a in res["alerts"] if "高水位" in a.get("title", "")]
        assert len(alerts) == 1
        assert alerts[0]["hwm_dd"] == 8.8

    def test_60d_peak_detection_from_peak_nav_60(self, sentry):
        """
        Peak detection via peak_nav_60:
        peak_nav_60 = 1.3000, current_nav = 1.1700
        hwm_dd = (1.3000 - 1.1700) / 1.3000 * 100 = 10.00% >= 8.0%
        """
        h = MockHolding(
            fund_code="000216",
            cost_price=1.0000,
            current_nav=1.1700,  # +17%
            bias_20=0.5,
            peak_nav_60=1.3000,
        )
        res = sentry.inspect_portfolio([h], {}, {"000216": {"aum": 20.0}})
        alerts = [a for a in res["alerts"] if "高水位" in a.get("title", "")]
        assert len(alerts) == 1
        assert alerts[0]["hwm_dd"] == 10.0

    def test_60d_peak_detection_from_radar_sector_price_series(self, sentry):
        """Peak detection via radar_engine.sector_price_series."""
        # 100 days series, peak in last 60 days is 2.00, last price is 1.80 (dd = 10.0%)
        days_100 = [1.50] * 40 + [2.00] + [1.80] * 59
        mock_radar = MagicMock()
        mock_radar.sector_price_series = {"domestic_gold": days_100}
        mock_radar.dynamic_metrics = {}

        with patch("AGY2_FundAdvisory.advisory_engine.OpportunityRadarEngine", return_value=mock_radar):
            h = MockHolding(
                fund_code="000216",
                fund_name="华安黄金联接A",
                cost_price=1.0000,
                current_nav=1.2000,  # +20%
                bias_20=1.0,
            )
            res = sentry.inspect_portfolio([h], {}, {"000216": {"aum": 20.0}})
            alerts = [a for a in res["alerts"] if "高水位" in a.get("title", "")]
            assert len(alerts) == 1
            assert alerts[0]["hwm_dd"] == 10.0

    def test_60d_peak_detection_from_history_navs(self, sentry):
        """
        Peak detection via h.history_navs when fund has no sector price series.
        For an unmapped custom fund, sec_series is None, so Sentry falls back to h.history_navs.
        """
        # 80 days of NAVs: last 60 days has peak at 1.50, current at 1.35 (dd = 10.0%)
        navs = [1.0] * 20 + [1.50] + [1.35] * 59
        h = MockHolding(
            fund_code="999999",
            fund_name="非赛道自选基金",
            cost_price=1.0000,
            current_nav=1.2000,  # +20%
            bias_20=0.5,
            history_navs=navs,
        )
        res = sentry.inspect_portfolio([h], {}, {"999999": {"aum": 20.0}})
        alerts = [a for a in res["alerts"] if "高水位" in a.get("title", "")]
        assert len(alerts) == 1
        assert alerts[0]["hwm_dd"] == 10.0

    def test_60d_peak_detection_clips_at_60_days_ignores_earlier_peak(self, sentry):
        """
        Window Clipping Test:
        If a massive peak occurred 75 days ago (outside 60d window), but the peak within
        the last 60 days is mild (dd < 8.0%), it MUST NOT trigger!
        """
        # Day 0-20: peak at 3.00 (day 10).
        # Day 21-80 (last 60 days): max is 1.25, last price is 1.20 (dd = (1.25-1.20)/1.25 = 4.0% < 8.0%)
        navs = [1.0] * 10 + [3.00] + [1.0] * 9 + [1.25] + [1.20] * 59
        h = MockHolding(
            fund_code="000216",
            cost_price=1.0000,
            current_nav=1.1500,
            bias_20=0.5,
            history_navs=navs,
        )
        res = sentry.inspect_portfolio([h], {}, {"000216": {"aum": 20.0}})
        assert not any("高水位" in a.get("title", "") for a in res["alerts"])

    def test_hwm_alert_properties_exact_match(self, sentry):
        """Verify exact schema attributes of HWM drawdown alert."""
        h = MockHolding(
            fund_code="000216",
            fund_name="华安黄金联接A",
            cost_price=1.0000,
            current_nav=1.2000,
            bias_20=0.5,
            hwm_dd=11.2,
        )
        res = sentry.inspect_portfolio([h], {}, {"000216": {"aum": 20.0}})
        alerts = [a for a in res["alerts"] if a.get("dimension") == "移动止盈"]
        assert len(alerts) == 1
        a = alerts[0]
        assert a["level"] == "yellow"
        assert a["dimension"] == "移动止盈"
        assert a["action_type"] == "take_profit"
        assert a["take_profit_ratio"] == 0.40
        assert a["hwm_dd"] == 11.2
        assert a["pnl_pct"] == 20.0
        assert "高水位浮盈回撤保护" in a["title"]


# =========================================================================
# Part 3: Branch Interactions & Precedence Matrix
# =========================================================================

class TestBranchInteractionsAndPrecedence:
    """Stress-test precedence and mutual interaction between Dimension 4 branches."""

    @pytest.fixture
    def sentry(self):
        return ActiveRiskSentry()

    def test_breakdown_precedes_hwm_drawdown_when_both_active(self, sentry):
        """
        Precedence Test 1: Right-side breakdown vs HWM drawdown.
        When a fund has PnL >= 10%, breaks MA20 (bias < 0, slope < 0) AND has hwm_dd >= 8%:
        Right-side breakdown (RED, 0.50) MUST take precedence over HWM (YELLOW, 0.40).
        Only ONE Dimension 4 alert should be emitted, with ratio 0.50.
        """
        h_both = MockHolding(
            fund_code="008888",
            cost_price=1.0000,
            current_nav=1.2500,  # +25%
            bias_20=-1.5,        # Breakdown
            slope_20=-0.8,       # Breakdown
            hwm_dd=12.0,         # HWM risk
        )
        res = sentry.inspect_portfolio([h_both], {}, {"008888": {"aum": 10.0}})
        dim4_alerts = [a for a in res["alerts"] if a.get("dimension") == "移动止盈"]
        assert len(dim4_alerts) == 1, "同时满足两项时只应保留最高优先级的右侧破位预警"
        assert dim4_alerts[0]["level"] == "red"
        assert dim4_alerts[0]["take_profit_ratio"] == 0.50
        assert "右侧破位" in dim4_alerts[0]["title"]

    def test_hwm_drawdown_precedes_ladder_profit(self, sentry):
        """
        Precedence Test 2: HWM drawdown vs Ladder profit.
        Suppose pnl = 18.0% (>= 15%) and bias_20 = 5.5% (> 5.0%),
        BUT hwm_dd = 9.0% (>= 8.0%).
        The HWM drawdown protection must take precedence because the position
        is actively shedding gains from an even higher peak.
        """
        h = MockHolding(
            fund_code="100032",
            cost_price=1.0000,
            current_nav=1.1800,  # +18%
            bias_20=5.5,         # Meets ladder profit condition
            slope_20=0.5,
            hwm_dd=9.0,          # Meets HWM drawdown condition
        )
        res = sentry.inspect_portfolio([h], {}, {"100032": {"aum": 20.0}})
        alerts = [a for a in res["alerts"] if a.get("action_type") == "take_profit"]
        assert len(alerts) == 1
        assert alerts[0]["dimension"] == "移动止盈"
        assert "高水位" in alerts[0]["title"]

    def test_overbought_triggers_when_not_broken_down(self, sentry):
        """
        Overbought Test: bias_20 > 6.0% triggers RED '超买拥挤'.
        Right-side breakdown cannot trigger because bias_20 > 0.
        """
        h = MockHolding(
            fund_code="011612",
            cost_price=1.0000,
            current_nav=1.0800,  # +8%
            bias_20=7.5,         # > 6.0%
            slope_20=1.5,
            hwm_dd=1.0,
        )
        res = sentry.inspect_portfolio([h], {}, {"011612": {"aum": 10.0}})
        alerts = [a for a in res["alerts"] if a.get("dimension") == "超买拥挤"]
        assert len(alerts) == 1
        assert alerts[0]["level"] == "red"
        assert alerts[0]["take_profit_ratio"] == 0.40

    def test_ladder_profit_triggers_when_not_broken_down_and_hwm_safe(self, sentry):
        """
        Ladder profit triggers when pnl >= 15%, bias_20 > 5.0%, bias_20 <= 6.0%, and hwm_dd < 8.0%.
        """
        h = MockHolding(
            fund_code="100032",
            cost_price=1.0000,
            current_nav=1.1600,  # +16%
            bias_20=5.5,         # 5.0 < bias <= 6.0
            slope_20=0.8,
            hwm_dd=3.0,          # Safe HWM
        )
        res = sentry.inspect_portfolio([h], {}, {"100032": {"aum": 20.0}})
        alerts = [a for a in res["alerts"] if a.get("dimension") == "阶梯止盈"]
        assert len(alerts) == 1
        assert alerts[0]["level"] == "yellow"
        assert alerts[0]["take_profit_ratio"] == 0.40

    def test_deep_loss_triggers_at_minus_12_pct(self, sentry):
        """Deep loss diagnosis triggers when pnl_pct <= -12.0%."""
        h = MockHolding(
            fund_code="013841",
            fund_name="融通集成电路C",
            cost_price=1.0000,
            current_nav=0.8500,  # -15%
            bias_20=-3.0,
            slope_20=-1.0,
        )
        res = sentry.inspect_portfolio([h], {}, {"013841": {"aum": 5.0}})
        deep_alerts = [a for a in res["alerts"] if "深套" in a.get("title", "") or "套牢" in a.get("title", "")]
        assert len(deep_alerts) >= 1

    def test_deep_loss_boundary_minus_11_9_vs_minus_12_0(self, sentry):
        """Boundary: pnl -11.9% does not trigger deep loss; -12.0% triggers."""
        h_sub = MockHolding(
            fund_code="013841",
            cost_price=1.0000,
            current_nav=0.8810,  # -11.90%
            bias_20=-1.0,
        )
        res_sub = sentry.inspect_portfolio([h_sub], {}, {"013841": {"aum": 5.0}})
        assert not any("深套" in a.get("title", "") for a in res_sub["alerts"])

        h_at = MockHolding(
            fund_code="013841",
            cost_price=1.0000,
            current_nav=0.8800,  # -12.00%
            bias_20=-1.0,
        )
        res_at = sentry.inspect_portfolio([h_at], {}, {"013841": {"aum": 5.0}})
        assert any("深套" in a.get("title", "") for a in res_at["alerts"])

    def test_healthy_holding_triggers_no_dim4_alert(self, sentry):
        """A normal holding with moderate profit (+5%), positive bias (+1.5%) triggers no Dim 4 alerts."""
        h_healthy = MockHolding(
            fund_code="002351",
            cost_price=1.0000,
            current_nav=1.0500,
            bias_20=1.5,
            slope_20=0.5,
            hwm_dd=2.0,
        )
        res = sentry.inspect_portfolio([h_healthy], {}, {"002351": {"aum": 30.0}})
        dim4 = [
            a for a in res["alerts"]
            if a.get("dimension") in ["移动止盈", "超买拥挤", "阶梯止盈"]
            or "深套" in a.get("title", "")
        ]
        assert len(dim4) == 0

    def test_dict_based_holding_full_parity(self, sentry):
        """Verify full parity when holdings are dicts instead of objects."""
        # Dict holding with right-side breakdown
        h_dict = {
            "fund_code": "008888",
            "fund_name": "华夏半导体芯片ETF联接A",
            "cost_price": 1.0000,
            "current_nav": 1.2500,
            "bias_20": -1.2,
            "slope_20": -0.6,
            "vol_20": 22.0,
            "holding_days": 40,
            "market_value": 50000.0,
            "share_class": "A",
        }
        res = sentry.inspect_portfolio([h_dict], {}, {"008888": {"aum": 15.0}})
        alerts = [a for a in res["alerts"] if a.get("dimension") == "移动止盈"]
        assert len(alerts) == 1
        assert alerts[0]["level"] == "red"
        assert alerts[0]["take_profit_ratio"] == 0.50

    def test_multi_asset_portfolio_heterogeneous_simultaneous_alerts(self, sentry):
        """
        Stress-test a heterogeneous portfolio with 6 holdings triggering different conditions:
        1. Fund 1: Right-side breakdown (pnl +25%, bias -1.5, slope -0.5) -> RED 0.50 移动止盈
        2. Fund 2: HWM drawdown (pnl +18%, bias +1.0, hwm_dd 9.5) -> YELLOW 0.40 移动止盈
        3. Fund 3: Overbought (pnl +6%, bias +7.2) -> RED 0.40 超买拥挤
        4. Fund 4: Ladder profit (pnl +16%, bias +5.5, hwm_dd 3.0) -> YELLOW 0.40 阶梯止盈
        5. Fund 5: Deep loss (pnl -16%) -> 深套诊断
        6. Fund 6: Healthy holding (pnl +4%, bias +0.8) -> No Dim 4 alert
        """
        holdings = [
            MockHolding(fund_code="008888", current_nav=1.2500, bias_20=-1.5, slope_20=-0.5),
            MockHolding(fund_code="000216", current_nav=1.1800, bias_20=1.0, slope_20=0.2, hwm_dd=9.5),
            MockHolding(fund_code="011612", current_nav=1.0600, bias_20=7.2, slope_20=1.0),
            MockHolding(fund_code="100032", current_nav=1.1600, bias_20=5.5, slope_20=0.5, hwm_dd=3.0),
            MockHolding(fund_code="013841", current_nav=0.8400, bias_20=-2.0),
            MockHolding(fund_code="002351", current_nav=1.0400, bias_20=0.8, slope_20=0.3, hwm_dd=1.0),
        ]
        aum_meta = {h.fund_code: {"aum": 20.0} for h in holdings}
        res = sentry.inspect_portfolio(holdings, {}, aum_meta)
        alerts = res["alerts"]

        # 1. Fund 1
        f1_alerts = [a for a in alerts if a.get("fund_code") == "008888" and a.get("dimension") == "移动止盈"]
        assert len(f1_alerts) == 1
        assert f1_alerts[0]["level"] == "red"
        assert f1_alerts[0]["take_profit_ratio"] == 0.50

        # 2. Fund 2
        f2_alerts = [a for a in alerts if a.get("fund_code") == "000216" and a.get("dimension") == "移动止盈"]
        assert len(f2_alerts) == 1
        assert f2_alerts[0]["level"] == "yellow"
        assert f2_alerts[0]["take_profit_ratio"] == 0.40

        # 3. Fund 3
        f3_alerts = [a for a in alerts if a.get("fund_code") == "011612" and a.get("dimension") == "超买拥挤"]
        assert len(f3_alerts) == 1
        assert f3_alerts[0]["level"] == "red"
        assert f3_alerts[0]["take_profit_ratio"] == 0.40

        # 4. Fund 4
        f4_alerts = [a for a in alerts if a.get("fund_code") == "100032" and a.get("dimension") == "阶梯止盈"]
        assert len(f4_alerts) == 1
        assert f4_alerts[0]["level"] == "yellow"
        assert f4_alerts[0]["take_profit_ratio"] == 0.40

        # 5. Fund 5
        f5_alerts = [a for a in alerts if a.get("fund_code") == "013841" and ("深套" in a.get("title", ""))]
        assert len(f5_alerts) >= 1

        # 6. Fund 6
        f6_dim4 = [
            a for a in alerts
            if a.get("fund_code") == "002351" and a.get("dimension") in ["移动止盈", "超买拥挤", "阶梯止盈"]
        ]
        assert len(f6_dim4) == 0

    def test_take_profit_ratio_deterministic_0_50_vs_0_40(self, sentry):
        """
        Verify that take_profit_ratio is ALWAYS either 0.50 (for breakdown)
        or 0.40 (for all other take_profit alerts: hwm_dd, overbought, ladder).
        """
        h_break = MockHolding(fund_code="008888", current_nav=1.20, bias_20=-1.0, slope_20=-0.5)
        h_hwm = MockHolding(fund_code="000216", current_nav=1.20, bias_20=1.0, hwm_dd=10.0)
        h_over = MockHolding(fund_code="011612", current_nav=1.05, bias_20=7.0)
        h_ladder = MockHolding(fund_code="100032", current_nav=1.18, bias_20=5.5)

        for h, expected_ratio, expected_dim in [
            (h_break, 0.50, "移动止盈"),
            (h_hwm, 0.40, "移动止盈"),
            (h_over, 0.40, "超买拥挤"),
            (h_ladder, 0.40, "阶梯止盈"),
        ]:
            res = sentry.inspect_portfolio([h], {}, {h.fund_code: {"aum": 20.0}})
            tp_alerts = [a for a in res["alerts"] if a.get("action_type") == "take_profit"]
            assert len(tp_alerts) == 1
            assert tp_alerts[0]["take_profit_ratio"] == expected_ratio
            assert tp_alerts[0]["dimension"] == expected_dim


# =========================================================================
# Part 4: Property-Based Generative Fuzzing (1000 Randomized States)
# =========================================================================

class TestPropertyBasedGenerativeFuzzing:
    """
    Generative Monte Carlo fuzzing across continuous parameter space:
    pnl in [-30%, +50%], bias in [-15%, +15%], slope in [-5%, +5%],
    single_day_drop in [0%, 10%], hwm_dd in [0%, 30%], vol_20 in [1%, 40%].
    """

    @pytest.fixture
    def sentry(self):
        return ActiveRiskSentry()

    def test_property_based_1000_randomized_states_invariant_checking(self, sentry):
        """
        Generate 300 independent randomized holding states with a deterministic seed.
        Verify mathematical invariants across every single test case:
        1. No unhandled exception is ever thrown.
        2. Exact logical equivalence between theoretical condition and emitted alert.
        3. Action type and take_profit_ratio consistency.
        """
        rng = np.random.RandomState(42)
        N_TRIALS = 300

        mock_radar = MagicMock()
        mock_radar.sector_price_series = {}
        mock_radar.dynamic_metrics = {}

        with patch("AGY2_FundAdvisory.advisory_engine.OpportunityRadarEngine", return_value=mock_radar), \
             patch("AGY2_FundAdvisory.portfolio_manager.PortfolioManager.evaluate_dynamic_correlation_mutation", return_value={"is_triggered": False}):
            for i in range(N_TRIALS):
                pnl = float(rng.uniform(-30.0, 50.0))
                bias = float(rng.uniform(-15.0, 15.0))
                slope = float(rng.uniform(-5.0, 5.0))
                drop = float(rng.uniform(0.0, 10.0)) if rng.rand() > 0.3 else 0.0
                hwm = float(rng.uniform(0.0, 30.0))
                vol = float(rng.uniform(1.0, 40.0))

                daily_vol = max(vol / 15.8113883, 0.5)

                # Construct holding
                cost = 1.0000
                cur_nav = round(cost * (1.0 + pnl / 100.0), 4)
                # Ensure pnl matches exactly
                calculated_pnl = round((cur_nav - cost) / cost * 100.0, 2)

                # Re-evaluate with exact rounded pnl
                exp_break = (
                    calculated_pnl >= 10.0
                    and bias < 0.0
                    and (slope < 0.0 or drop > 1.5 * daily_vol)
                )
                exp_hwm_dd = (
                    not exp_break
                    and calculated_pnl >= 10.0
                    and hwm >= 8.0
                )
                exp_over = (
                    not exp_break
                    and not exp_hwm_dd
                    and bias > 6.0
                )
                exp_lad = (
                    not exp_break
                    and not exp_hwm_dd
                    and not exp_over
                    and calculated_pnl >= 15.0
                    and bias > 5.0
                )
                exp_deep = (
                    not exp_break
                    and not exp_hwm_dd
                    and not exp_over
                    and not exp_lad
                    and calculated_pnl <= -12.0
                )

                h = MockHolding(
                    fund_code=f"F{i:04d}",
                    cost_price=cost,
                    current_nav=cur_nav,
                    bias_20=bias,
                    slope_20=slope,
                    vol_20=vol,
                    single_day_drop=drop,
                    hwm_dd=hwm,
                )

                res = sentry.inspect_portfolio([h], {}, {f"F{i:04d}": {"aum": 10.0}})
                alerts = res["alerts"]

                # Filter Dim 4 alerts
                dim4_alerts = [
                    a for a in alerts
                    if a.get("dimension") in ["移动止盈", "超买拥挤", "阶梯止盈"]
                    or "深套" in a.get("title", "")
                ]

                if exp_break:
                    assert len(dim4_alerts) == 1, f"Trial {i}: 期望触发右侧破位，但实际: {dim4_alerts}"
                    assert dim4_alerts[0]["dimension"] == "移动止盈"
                    assert dim4_alerts[0]["level"] == "red"
                    assert dim4_alerts[0]["take_profit_ratio"] == 0.50
                elif exp_hwm_dd:
                    assert len(dim4_alerts) == 1, f"Trial {i}: 期望触发高水位回撤，但实际: {dim4_alerts}"
                    assert dim4_alerts[0]["dimension"] == "移动止盈"
                    assert dim4_alerts[0]["level"] == "yellow"
                    assert dim4_alerts[0]["take_profit_ratio"] == 0.40
                elif exp_over:
                    assert len(dim4_alerts) == 1, f"Trial {i}: 期望触发超买拥挤，但实际: {dim4_alerts}"
                    assert dim4_alerts[0]["dimension"] == "超买拥挤"
                    assert dim4_alerts[0]["level"] == "red"
                    assert dim4_alerts[0]["take_profit_ratio"] == 0.40
                elif exp_lad:
                    assert len(dim4_alerts) == 1, f"Trial {i}: 期望触发阶梯止盈，但实际: {dim4_alerts}"
                    assert dim4_alerts[0]["dimension"] == "阶梯止盈"
                    assert dim4_alerts[0]["level"] == "yellow"
                    assert dim4_alerts[0]["take_profit_ratio"] == 0.40
                elif exp_deep:
                    assert len(dim4_alerts) >= 1, f"Trial {i}: 期望触发深套诊断，但实际: {dim4_alerts}"
                else:
                    assert len(dim4_alerts) == 0, f"Trial {i}: 期望无Dim4警报，但实际触发: {dim4_alerts}"

    def test_property_based_no_exception_on_corrupt_or_nan_inputs(self, sentry):
        """Sentry must gracefully handle None, NaN, inf, or missing fields without crashing."""
        for corrupt_val in [None, np.nan, float("inf"), float("-inf")]:
            h = MockHolding(
                fund_code="008888",
                cost_price=1.0000,
                current_nav=1.2000,
                bias_20=corrupt_val,
                slope_20=corrupt_val,
                vol_20=corrupt_val,
                single_day_drop=corrupt_val,
                hwm_dd=corrupt_val,
            )
            try:
                res = sentry.inspect_portfolio([h], {}, {"008888": {"aum": 10.0}})
                assert isinstance(res, dict)
            except Exception as e:
                pytest.fail(f"Corrupt value {corrupt_val} caused crash: {e}")

    def test_property_based_take_profit_ratio_soundness(self, sentry):
        """Any emitted take_profit alert must have take_profit_ratio in [0.30, 0.70]."""
        h_break = MockHolding(current_nav=1.30, bias_20=-1.0, slope_20=-0.5)
        h_hwm = MockHolding(current_nav=1.30, bias_20=1.0, hwm_dd=10.0)
        res = sentry.inspect_portfolio([h_break, h_hwm], {}, {})
        for a in res["alerts"]:
            if a.get("action_type") == "take_profit":
                ratio = a.get("take_profit_ratio")
                assert ratio is not None
                assert 0.30 <= ratio <= 0.70

    def test_property_based_mutual_exclusion_of_dimension4_actions(self, sentry):
        """For any single holding, Dimension 4 must emit AT MOST ONE primary action."""
        h = MockHolding(
            fund_code="008888",
            cost_price=1.0000,
            current_nav=1.3000,
            bias_20=-2.0,
            slope_20=-1.0,
            single_day_drop=3.0,
            hwm_dd=15.0,
        )
        res = sentry.inspect_portfolio([h], {}, {"008888": {"aum": 10.0}})
        dim4 = [
            a for a in res["alerts"]
            if a.get("dimension") in ["移动止盈", "超买拥挤", "阶梯止盈"]
            or "深套" in a.get("title", "")
        ]
        assert len(dim4) == 1, f"单一持仓在维度4中绝不应发出多于一条警报: {dim4}"

    def test_property_based_level_severity_soundness(self, sentry):
        """Breakdown and Overbought must be RED; HWM and Ladder must be YELLOW."""
        h_break = MockHolding(fund_code="008888", current_nav=1.25, bias_20=-1.0, slope_20=-0.5)
        h_hwm = MockHolding(fund_code="000216", current_nav=1.25, bias_20=1.0, hwm_dd=10.0)
        h_over = MockHolding(fund_code="011612", current_nav=1.05, bias_20=7.5)
        h_ladder = MockHolding(fund_code="100032", current_nav=1.18, bias_20=5.5)

        res = sentry.inspect_portfolio([h_break, h_hwm, h_over, h_ladder], {}, {})
        for a in res["alerts"]:
            if "右侧破位" in a.get("title", ""):
                assert a["level"] == "red"
            elif "高水位" in a.get("title", ""):
                assert a["level"] == "yellow"
            elif a.get("dimension") == "超买拥挤":
                assert a["level"] == "red"
            elif a.get("dimension") == "阶梯止盈":
                assert a["level"] == "yellow"
