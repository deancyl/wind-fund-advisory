# -*- coding: utf-8 -*-
"""
tests/test_g12_m1_challenge.py
Milestone 1 Independent Empirical Challenge Suite:
Adversarial stress testing of Bug 1 (Correlation mutation gate alignment)
and Bug 2 (ActiveRiskSentry Dimension 8 & 9 parameter penetration & alert triggers).

Author: teamwork_challenger (empirical challenger: critic, specialist)
"""

import sys
from pathlib import Path
from unittest.mock import patch
import pytest
import numpy as np

_CURRENT = Path(__file__).resolve().parent
_WORKSPACE = _CURRENT.parent
_AGY2_DIR = _WORKSPACE / "AGY2_FundAdvisory"
if str(_AGY2_DIR) not in sys.path:
    sys.path.insert(0, str(_AGY2_DIR))
if str(_WORKSPACE) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE))

from AGY2_FundAdvisory.portfolio_manager import (
    PortfolioManager,
    FundQuote,
    _apply_fund_valuation_calibration,
    clear_realtime_cache,
)
from AGY2_FundAdvisory.advisory_engine import (
    ActiveRiskSentry,
    SmartExecutionDCAEngine,
)
from AGY2_FundAdvisory.app_gui import (
    render_correlation_mutation_card_html,
)


@pytest.fixture(autouse=True)
def clean_environment():
    clear_realtime_cache()
    yield
    clear_realtime_cache()


# =====================================================================
# 1. Bug 1: Correlation Mutation Gate & Return Dictionaries Boundaries
# =====================================================================

class TestBug1CorrelationBoundaries:
    """
    Stress-test boundary values: 0.74, 0.75, 0.79, 0.80, 0.85
    Verify is_triggered and is_mutation_alarm are 100% aligned,
    and verify GUI gates evaluate identically across all representations.
    """

    @pytest.fixture
    def pm_instance(self):
        pm = PortfolioManager(db_path=":memory:")
        pm.add_or_update_holding("005561", shares=10000.0, nav=1.5, cost_price=1.4)
        pm.add_or_update_holding("011613", shares=20000.0, nav=0.8, cost_price=1.0)
        pm.add_or_update_holding("002351", shares=5000.0, nav=1.1, cost_price=1.1)
        return pm

    @pytest.mark.parametrize("corr, exp_triggered, exp_stress, exp_status, exp_level", [
        (0.74, False, False, "DECOUPLED_NORMAL", "green"),
        (0.75, True, False, "MUTATION_ALERT", "yellow"),
        (0.79, True, False, "MUTATION_ALERT", "yellow"),
        (0.80, True, True, "MUTATION_ALERT", "red"),
        (0.85, True, True, "MUTATION_ALERT", "red"),
        # 4-decimal precision boundaries (matching round(corr, 4))
        (0.7499, False, False, "DECOUPLED_NORMAL", "green"),
        (0.7500, True, False, "MUTATION_ALERT", "yellow"),
        (0.7501, True, False, "MUTATION_ALERT", "yellow"),
        (0.7999, True, False, "MUTATION_ALERT", "yellow"),
        (0.8000, True, True, "MUTATION_ALERT", "red"),
        (0.8001, True, True, "MUTATION_ALERT", "red"),
        # Extreme boundaries
        (-0.50, False, False, "DECOUPLED_NORMAL", "green"),
        (0.00, False, False, "DECOUPLED_NORMAL", "green"),
        (1.00, True, True, "MUTATION_ALERT", "red"),
    ])
    def test_boundary_values_and_key_alignment(self, pm_instance, corr, exp_triggered, exp_stress, exp_status, exp_level):
        """
        Adversarial test on exact threshold values.
        Property:
        - is_triggered == is_mutation_alarm ALWAYS
        - is_liquidity_shift_triggered == is_regime_shift_risk ALWAYS
        """
        res = pm_instance.evaluate_dynamic_correlation_mutation_instance(
            threshold=0.75,
            stress_threshold=0.80,
            simulated_corr=corr
        )

        # 1. Strict key alignment invariant
        assert res["is_triggered"] == res["is_mutation_alarm"], (
            f"Invariant violation: is_triggered ({res['is_triggered']}) != is_mutation_alarm ({res['is_mutation_alarm']}) at corr={corr}"
        )
        assert res["is_liquidity_shift_triggered"] == res["is_regime_shift_risk"], (
            f"Invariant violation: is_liquidity_shift_triggered ({res['is_liquidity_shift_triggered']}) != is_regime_shift_risk ({res['is_regime_shift_risk']}) at corr={corr}"
        )

        # 2. Strict value check
        assert res["is_triggered"] is exp_triggered, f"Failed at corr={corr}: expected is_triggered={exp_triggered}"
        assert res["is_liquidity_shift_triggered"] is exp_stress, f"Failed at corr={corr}: expected is_liquidity_shift_triggered={exp_stress}"
        assert res["status"] == exp_status, f"Failed at corr={corr}: expected status={exp_status}"
        assert res["alert_level"] == exp_level, f"Failed at corr={corr}: expected alert_level={exp_level}"

        # 3. GUI gate consistency check
        # Evaluate how app_gui.py renders or gates:
        gui_gate_combined = bool(
            res.get("is_triggered") or
            res.get("is_liquidity_shift_triggered") or
            res.get("is_mutation_alarm") or
            res.get("is_regime_shift_risk")
        )
        gui_gate_native_only = bool(res.get("is_triggered") or res.get("is_liquidity_shift_triggered"))
        gui_gate_alias_only = bool(res.get("is_mutation_alarm") or res.get("is_regime_shift_risk"))

        assert gui_gate_combined == exp_triggered, f"GUI combined gate failed at corr={corr}"
        assert gui_gate_native_only == exp_triggered, f"GUI native gate failed at corr={corr}"
        assert gui_gate_alias_only == exp_triggered, f"GUI alias gate failed at corr={corr}"

    def test_property_based_fuzzing_100_points(self, pm_instance):
        """
        Property-based test: generate 100 pseudo-random correlation values in [-1.0, 1.0].
        Verify that for every value, the dual keys are always aligned and weights sum to 1.0.
        """
        np.random.seed(42)
        random_corrs = np.random.uniform(-1.0, 1.0, size=100)

        for c in random_corrs:
            c_val = round(float(c), 4)
            res = pm_instance.evaluate_dynamic_correlation_mutation_instance(
                threshold=0.75,
                stress_threshold=0.80,
                simulated_corr=c_val
            )

            # Invariant 1: Keys alignment
            assert res["is_triggered"] == res["is_mutation_alarm"]
            assert res["is_liquidity_shift_triggered"] == res["is_regime_shift_risk"]

            # Invariant 2: Threshold math consistency
            assert res["is_triggered"] == (c_val >= 0.75)
            assert res["is_liquidity_shift_triggered"] == (c_val >= 0.80)

            # Invariant 3: Weight conservation
            adj_w = res.get("adjusted_weights", {})
            assert sum(adj_w.values()) == pytest.approx(1.0, abs=1e-5), f"Weight sum not 1.0 at corr={c_val}"
            assert all(w >= 0.0 for w in adj_w.values()), f"Negative weight generated at corr={c_val}"

            # Invariant 4: If triggered, defensive assets (002351 pure bond, 000216 gold) are boosted
            if res["is_triggered"]:
                orig_w = res.get("original_weights", {})
                assert adj_w.get("002351", 0.0) >= orig_w.get("002351", 0.0)
                assert adj_w.get("000216", 0.0) >= orig_w.get("000216", 0.0)

    def test_html_card_rendering_across_all_boundaries(self, pm_instance):
        """
        Verify render_correlation_mutation_card_html renders correctly and safely across boundaries.
        """
        for corr in [0.74, 0.75, 0.79, 0.80, 0.85]:
            res = pm_instance.evaluate_dynamic_correlation_mutation_instance(
                threshold=0.75,
                stress_threshold=0.80,
                simulated_corr=corr
            )
            html = render_correlation_mutation_card_html(res)
            assert isinstance(html, str)
            assert len(html) > 0
            if corr >= 0.80:
                assert "red" in res["alert_level"]
                assert ("0.80" in html or "流动性平移" in html or "极端" in html)
            elif corr >= 0.75:
                assert "yellow" in res["alert_level"]
                assert ("0.75" in html or "相关性" in html or "集中度" in html)


# =====================================================================
# 2. Bug 2: ActiveRiskSentry Dimension 8 (C1 to C5 tiers)
# =====================================================================

class TestBug2SentryDimension8Suitability:
    """
    Stress-test ActiveRiskSentry Dimension 8 across:
    - Investor tiers: C1, C2, C3, C4, C5
    - Portfolio configurations: Conservative, Exactly-at-Limit, Over-Limit, Aggressive Tech
    - Parameter transmission routes: investor_risk_tier direct, lowercase, snapshot, kwargs
    """

    @pytest.fixture
    def sentry(self):
        return ActiveRiskSentry()

    @pytest.fixture
    def conservative_holdings(self):
        """100% 纯债 (002351)"""
        return {
            "002351": {
                "code": "002351",
                "name": "招商产业债A",
                "market_value": 100000.0,
                "shares": 100000.0,
                "cost_nav": 1.0,
                "current_nav": 1.0,
                "pnl_pct": 0.0,
                "category": "纯债固收"
            }
        }

    @pytest.fixture
    def aggressive_tech_holdings(self):
        """90% 科技/科创 (013841) + 10% 纯债 (002351)"""
        return {
            "013841": {
                "code": "013841",
                "name": "天弘中证芯片产业ETF联接C",
                "market_value": 90000.0,
                "shares": 90000.0,
                "cost_nav": 1.0,
                "current_nav": 1.0,
                "pnl_pct": 0.0,
                "category": "科技成长进攻"
            },
            "002351": {
                "code": "002351",
                "name": "招商产业债A",
                "market_value": 10000.0,
                "shares": 10000.0,
                "cost_nav": 1.0,
                "current_nav": 1.0,
                "pnl_pct": 0.0,
                "category": "纯债固收"
            }
        }

    @pytest.mark.parametrize("tier", ["C1", "C2", "C3", "C4", "C5"])
    def test_conservative_holdings_never_triggers_suitability_alert(self, sentry, conservative_holdings, tier):
        """
        Pure bond holdings (0% equity) must NEVER trigger suitability alert for any risk tier (C1-C5).
        """
        rep = sentry.inspect_portfolio(
            holdings=conservative_holdings,
            snapshot={},
            investor_risk_tier=tier
        )
        alerts = [a for a in rep.get("alerts", []) if a.get("dimension") == "投资者适当性"]
        assert len(alerts) == 0, f"Pure conservative holdings should not trigger suitability alert for {tier}"

    @pytest.mark.parametrize("tier, max_eq_pct", [
        ("C1", 20),
        ("C2", 40),
        ("C3", 78),
        ("C4", 85),
        ("C5", 95),
    ])
    def test_exact_limit_boundary_not_triggered(self, sentry, tier, max_eq_pct):
        """
        Holdings exactly at max_eq_pct equity must NOT trigger suitability alert (<= max_eq).
        """
        equity_mv = float(max_eq_pct) * 1000.0
        bond_mv = (100.0 - float(max_eq_pct)) * 1000.0

        holdings = {
            "100032": {
                "code": "100032",
                "name": "富国中证红利指数增强A",
                "market_value": equity_mv,
                "shares": equity_mv,
                "cost_nav": 1.0,
                "current_nav": 1.0,
                "pnl_pct": 0.0,
                "category": "权益类"
            },
            "002351": {
                "code": "002351",
                "name": "招商产业债A",
                "market_value": bond_mv,
                "shares": bond_mv,
                "cost_nav": 1.0,
                "current_nav": 1.0,
                "pnl_pct": 0.0,
                "category": "纯债固收"
            }
        }

        rep = sentry.inspect_portfolio(
            holdings=holdings,
            snapshot={},
            investor_risk_tier=tier
        )
        alerts = [a for a in rep.get("alerts", []) if a.get("dimension") == "投资者适当性"]
        assert len(alerts) == 0, f"Holding exactly at {max_eq_pct}% equity should not trigger alert for {tier}"

    @pytest.mark.parametrize("tier, max_eq_pct", [
        ("C1", 20),
        ("C2", 40),
        ("C3", 78),
        ("C4", 85),
        ("C5", 95),
    ])
    def test_over_limit_by_one_percent_triggers_alert(self, sentry, tier, max_eq_pct):
        """
        Holdings just 1% above max_eq_pct equity MUST trigger suitability alert.
        """
        over_pct = min(100.0, float(max_eq_pct) + 1.0)
        if over_pct > 100.0:
            return  # C5 95% + 1% = 96% <= 100%

        equity_mv = over_pct * 1000.0
        bond_mv = (100.0 - over_pct) * 1000.0

        holdings = {
            "100032": {
                "code": "100032",
                "name": "富国中证红利指数增强A",
                "market_value": equity_mv,
                "shares": equity_mv,
                "cost_nav": 1.0,
                "current_nav": 1.0,
                "pnl_pct": 0.0,
                "category": "权益类"
            },
            "002351": {
                "code": "002351",
                "name": "招商产业债A",
                "market_value": bond_mv,
                "shares": bond_mv,
                "cost_nav": 1.0,
                "current_nav": 1.0,
                "pnl_pct": 0.0,
                "category": "纯债固收"
            }
        }

        rep = sentry.inspect_portfolio(
            holdings=holdings,
            snapshot={},
            investor_risk_tier=tier
        )
        alerts = [a for a in rep.get("alerts", []) if a.get("dimension") == "投资者适当性"]
        assert len(alerts) >= 1, f"Holding at {over_pct}% equity (1% over) must trigger alert for {tier}"

    def test_aggressive_tech_across_all_tiers(self, sentry, aggressive_tech_holdings):
        """
        90% Tech + 10% Bond:
        - C1 (max 20%): Must trigger RED alert (excess = 70% >= 15% AND C1 holding high-vol tech).
        - C2 (max 40%): Must trigger RED alert (excess = 50% >= 15%).
        - C3 (max 78%): Must trigger YELLOW alert (excess = 12% < 15%).
        - C4 (max 85%): Must trigger YELLOW alert (excess = 5% < 15%).
        - C5 (max 95%): 90% <= 95% -> NO alert!
        """
        # C1
        rep_c1 = sentry.inspect_portfolio(aggressive_tech_holdings, snapshot={}, investor_risk_tier="C1")
        alerts_c1 = [a for a in rep_c1.get("alerts", []) if a.get("dimension") == "投资者适当性"]
        assert len(alerts_c1) == 1
        assert alerts_c1[0]["level"] == "red"
        assert "高波科技" in alerts_c1[0]["desc"]

        # C2
        rep_c2 = sentry.inspect_portfolio(aggressive_tech_holdings, snapshot={}, investor_risk_tier="C2")
        alerts_c2 = [a for a in rep_c2.get("alerts", []) if a.get("dimension") == "投资者适当性"]
        assert len(alerts_c2) == 1
        assert alerts_c2[0]["level"] == "red"

        # C3
        rep_c3 = sentry.inspect_portfolio(aggressive_tech_holdings, snapshot={}, investor_risk_tier="C3")
        alerts_c3 = [a for a in rep_c3.get("alerts", []) if a.get("dimension") == "投资者适当性"]
        assert len(alerts_c3) == 1
        assert alerts_c3[0]["level"] == "yellow"

        # C4
        rep_c4 = sentry.inspect_portfolio(aggressive_tech_holdings, snapshot={}, investor_risk_tier="C4")
        alerts_c4 = [a for a in rep_c4.get("alerts", []) if a.get("dimension") == "投资者适当性"]
        assert len(alerts_c4) == 1
        assert alerts_c4[0]["level"] == "yellow"

        # C5
        rep_c5 = sentry.inspect_portfolio(aggressive_tech_holdings, snapshot={}, investor_risk_tier="C5")
        alerts_c5 = [a for a in rep_c5.get("alerts", []) if a.get("dimension") == "投资者适当性"]
        assert len(alerts_c5) == 0

    @pytest.mark.parametrize("route", [
        ("arg_upper", lambda s, h: s.inspect_portfolio(h, snapshot={}, investor_risk_tier="C1")),
        ("arg_lower", lambda s, h: s.inspect_portfolio(h, snapshot={}, investor_risk_tier="c1")),
        ("kwarg_tier", lambda s, h: s.inspect_portfolio(h, snapshot={}, risk_tier="C1")),
        ("snapshot_tier", lambda s, h: s.inspect_portfolio(h, snapshot={"investor_risk_tier": "C1"})),
        ("snapshot_risk_tier", lambda s, h: s.inspect_portfolio(h, snapshot={"risk_tier": "c1"})),
    ])
    def test_parameter_passing_routes_and_case_insensitivity(self, sentry, aggressive_tech_holdings, route):
        """
        Verify investor_risk_tier parameter is correctly passed and parsed through all supported routes.
        """
        route_name, call_fn = route
        rep = call_fn(sentry, aggressive_tech_holdings)
        alerts = [a for a in rep.get("alerts", []) if a.get("dimension") == "投资者适当性"]
        assert len(alerts) == 1, f"Failed for route: {route_name}"
        assert alerts[0]["level"] == "red"
        assert alerts[0]["investor_risk_tier"] == "C1"

    def test_missing_tier_graceful_handling(self, sentry, aggressive_tech_holdings):
        """
        When investor_risk_tier is completely omitted / None, Dimension 8 is skipped without crashing.
        """
        rep = sentry.inspect_portfolio(aggressive_tech_holdings, snapshot={})
        alerts = [a for a in rep.get("alerts", []) if a.get("dimension") == "投资者适当性"]
        assert len(alerts) == 0


# =====================================================================
# 3. Bug 2: ActiveRiskSentry Dimension 9 (Intraday Shocks & Cushion)
# =====================================================================

class TestBug2SentryDimension9IntradayShocks:
    """
    Stress-test ActiveRiskSentry Dimension 9:
    - Single fund shock >= 2.0%
    - Cushion depletion levels (< 50% -> yellow, >= 50% -> red, 0 cushion -> red)
    - Sub-threshold shock (< 2.0% single fund and < 1.0% portfolio) -> no alert
    - Portfolio-level shock >= 1.0% without single fund >= 2.0% -> alert fires
    - Positive shock with gain -> no alert
    - FundQuote vs dict format flexibility
    """

    @pytest.fixture
    def sentry(self):
        return ActiveRiskSentry()

    @pytest.fixture
    def single_fund_holding(self):
        return {
            "013841": {
                "code": "013841",
                "name": "天弘中证芯片产业ETF联接C",
                "market_value": 100000.0,
                "shares": 100000.0,
                "cost_nav": 1.0,
                "current_nav": 1.1,
                "pnl_pct": 10.0,  # Cushion = 100000 - 100000/1.1 = 9090.91 RMB
                "category": "权益类"
            }
        }

    def test_single_fund_drop_boundary_2_percent(self, sentry, single_fund_holding):
        """
        Test single fund drop at boundaries:
        - -1.90%: below 2% boundary -> No alert (since portfolio drop -1.9%? Wait! Portfolio has 1 fund so portfolio drop is also -1.9% which is <= -1.0%!)
        Let's construct a portfolio with a buffer fund so portfolio drop is < 1.0% to test single fund 2.0% threshold cleanly!
        """
        # 2 funds: 10% in fund A (10k), 90% in fund B pure bond (90k). Total = 100k.
        two_fund_holdings = {
            "013841": {
                "code": "013841",
                "name": "芯片ETF联接",
                "market_value": 10000.0,
                "shares": 10000.0,
                "cost_nav": 1.0,
                "current_nav": 1.1,
                "pnl_pct": 10.0,  # cushion ~ 909元
                "category": "权益类"
            },
            "002351": {
                "code": "002351",
                "name": "纯债A",
                "market_value": 90000.0,
                "shares": 90000.0,
                "cost_nav": 1.0,
                "current_nav": 1.0,
                "pnl_pct": 0.0,
                "category": "纯债固收"
            }
        }
        # Portfolio total MV = 100k. Cushion = 909元.
        # If fund A drops -1.90%: delta = -190元.
        # Portfolio drop = -190 / 100000 = -0.19% (which is > -1.0%).
        # has_large_single_swing is False (1.90% < 2.0%).
        # abs(intraday_chg_pct) = 0.19% < 1.0%.
        # Condition (has_large_single_swing or abs(intraday_chg_pct) >= 1.0) is FALSE!
        # Expected: NO ALERT.
        snap_sub = {
            "fund_quotes": {
                "013841": {"gszzl": -1.90},
                "002351": {"gszzl": 0.0}
            },
            "cushion_yuan": 909.0
        }
        rep_sub = sentry.inspect_portfolio(two_fund_holdings, snapshot=snap_sub)
        d9_alerts_sub = [a for a in rep_sub.get("alerts", []) if a.get("dimension") == "盘中异动安全垫传导"]
        assert len(d9_alerts_sub) == 0, "Single fund drop of -1.90% with portfolio drop -0.19% should not trigger alert"

        # Now test single fund drops -2.00% (exact boundary):
        # delta = -200元.
        # has_large_single_swing is True (abs(-2.00) >= 2.0).
        # consumed_cushion_ratio = 200 / 909 = 22.0% (>= 20.0%).
        # Expected: ALERT FIRES!
        snap_boundary = {
            "fund_quotes": {
                "013841": {"gszzl": -2.00},
                "002351": {"gszzl": 0.0}
            },
            "cushion_yuan": 909.0
        }
        rep_boundary = sentry.inspect_portfolio(two_fund_holdings, snapshot=snap_boundary)
        d9_alerts_boundary = [a for a in rep_boundary.get("alerts", []) if a.get("dimension") == "盘中异动安全垫传导"]
        assert len(d9_alerts_boundary) == 1, "Single fund drop of -2.00% with cushion depletion 22% must trigger alert"
        assert d9_alerts_boundary[0]["level"] == "yellow"  # 22% < 50% -> yellow

    def test_cushion_depletion_severity_yellow_vs_red(self, sentry):
        """
        Verify cushion depletion ratio:
        - consumed_cushion_ratio < 50% -> level: 'yellow'
        - consumed_cushion_ratio >= 50% -> level: 'red'
        - cushion_yuan == 0 (depleted) -> level: 'red'
        """
        holdings = {
            "013841": {
                "code": "013841",
                "name": "芯片ETF联接",
                "market_value": 100000.0,
                "shares": 100000.0,
                "cost_nav": 1.0,
                "current_nav": 1.0,
                "pnl_pct": 0.0,
                "category": "权益类"
            }
        }

        # 1. Shock of -2.5% = -2500元. Cushion = 10,000元.
        # Consumed ratio = 2500 / 10000 = 25.0% (< 50%) -> YELLOW
        snap_yellow = {
            "fund_quotes": {"013841": FundQuote(name="芯片", dwjz=1.0, gsz=0.975, gszzl=-2.5, gztime="14:30", fund_code="013841")},
            "cushion_yuan": 10000.0
        }
        rep_yellow = sentry.inspect_portfolio(holdings, snapshot=snap_yellow)
        alerts_y = [a for a in rep_yellow.get("alerts", []) if a.get("dimension") == "盘中异动安全垫传导"]
        assert len(alerts_y) == 1
        assert alerts_y[0]["level"] == "yellow"
        assert alerts_y[0]["consumed_cushion_ratio"] == pytest.approx(25.0, abs=0.1)

        # 2. Shock of -2.5% = -2500元. Cushion = 4,000元.
        # Consumed ratio = 2500 / 4000 = 62.5% (>= 50%) -> RED
        snap_red = {
            "fund_quotes": {"013841": {"gszzl": -2.5}},
            "cushion_yuan": 4000.0
        }
        rep_red = sentry.inspect_portfolio(holdings, snapshot=snap_red)
        alerts_r = [a for a in rep_red.get("alerts", []) if a.get("dimension") == "盘中异动安全垫传导"]
        assert len(alerts_r) == 1
        assert alerts_r[0]["level"] == "red"
        assert alerts_r[0]["consumed_cushion_ratio"] == pytest.approx(62.5, abs=0.1)

        # 3. Cushion = 0 (no cushion at all).
        # Consumed ratio defaults to 100.0% -> RED
        snap_zero_cushion = {
            "fund_quotes": {"013841": {"gszzl": -2.5}},
            "cushion_yuan": 0.0
        }
        rep_zero = sentry.inspect_portfolio(holdings, snapshot=snap_zero_cushion)
        alerts_z = [a for a in rep_zero.get("alerts", []) if a.get("dimension") == "盘中异动安全垫传导"]
        assert len(alerts_z) == 1
        assert alerts_z[0]["level"] == "red"
        assert alerts_z[0]["consumed_cushion_ratio"] == 100.0

    def test_portfolio_level_shock_without_single_fund_reaching_2_percent(self, sentry):
        """
        3 funds, each dropping -1.2% (no single fund reaches 2.0%).
        Portfolio total drop = -1.2% <= -1.0%.
        This must trigger Dimension 9 alert!
        """
        holdings = {
            "100032": {"code": "100032", "name": "红利", "market_value": 30000.0, "cost_nav": 1.0, "current_nav": 1.0, "pnl_pct": 0.0},
            "005561": {"code": "005561", "name": "红利低波", "market_value": 30000.0, "cost_nav": 1.0, "current_nav": 1.0, "pnl_pct": 0.0},
            "011613": {"code": "011613", "name": "科创50", "market_value": 40000.0, "cost_nav": 1.0, "current_nav": 1.0, "pnl_pct": 0.0},
        }
        snap = {
            "fund_quotes": {
                "100032": {"gszzl": -1.20},
                "005561": {"gszzl": -1.20},
                "011613": {"gszzl": -1.20},
            },
            "cushion_yuan": 5000.0
        }
        rep = sentry.inspect_portfolio(holdings, snapshot=snap)
        alerts = [a for a in rep.get("alerts", []) if a.get("dimension") == "盘中异动安全垫传导"]
        assert len(alerts) == 1
        assert alerts[0]["intraday_chg_pct"] == pytest.approx(-1.20, abs=0.01)

    def test_positive_shock_does_not_trigger_depletion_alert(self, sentry):
        """
        If market surges +3.0% (single swing >= 2.0%), but intraday_pnl_sum > 0,
        it should NOT trigger cushion depletion alert.
        """
        holdings = {
            "013841": {"code": "013841", "name": "芯片", "market_value": 100000.0, "cost_nav": 1.0, "current_nav": 1.0, "pnl_pct": 0.0}
        }
        snap = {
            "fund_quotes": {"013841": {"gszzl": +3.50}},
            "cushion_yuan": 5000.0
        }
        rep = sentry.inspect_portfolio(holdings, snapshot=snap)
        alerts = [a for a in rep.get("alerts", []) if a.get("dimension") == "盘中异动安全垫传导"]
        assert len(alerts) == 0

    @pytest.mark.parametrize("quote_format", [
        ("fund_quote_obj", lambda: FundQuote(name="f", dwjz=1.0, gsz=0.97, gszzl=-3.0, gztime="14:30", fund_code="013841")),
        ("dict_gszzl", lambda: {"gszzl": -3.0}),
        ("dict_change_pct", lambda: {"change_pct": -3.0}),
        ("dict_chg_pct", lambda: {"chg_pct": -3.0}),
        ("raw_float", lambda: -3.0),
    ])
    def test_quote_data_format_flexibility(self, sentry, quote_format):
        """
        Verify Dimension 9 correctly ingests FundQuote object, dict with gszzl/change_pct/chg_pct, or raw float.
        """
        fmt_name, q_getter = quote_format
        holdings = {
            "013841": {"code": "013841", "name": "芯片", "market_value": 100000.0, "cost_nav": 1.0, "current_nav": 1.0, "pnl_pct": 0.0}
        }
        snap = {
            "fund_quotes": {"013841": q_getter()},
            "cushion_yuan": 10000.0
        }
        rep = sentry.inspect_portfolio(holdings, snapshot=snap)
        alerts = [a for a in rep.get("alerts", []) if a.get("dimension") == "盘中异动安全垫传导"]
        assert len(alerts) == 1, f"Failed for quote format: {fmt_name}"


# =====================================================================
# 4. Bug 3 & 4 Verification
# =====================================================================

class TestBug3And4Integrity:
    """
    Verify Bug 3 feeder calibration factor and Bug 4 portfolio weighted bias & ERP.
    """

    def test_feeder_vs_index_factor_distinction(self):
        """
        011613 (联接) -> 0.95 factor
        100032 (指数) -> 1.00 factor
        002351 (纯债) -> no correction
        """
        mock_bench = {"change_pct": -2.00}
        with patch("AGY2_FundAdvisory.portfolio_manager.fetch_realtime_index_quote", return_value=mock_bench):
            # Feeder fund
            q_feeder = FundQuote(name="华夏恒生/科创50ETF联接A", dwjz=1.0, gsz=1.0, gszzl=0.0, gztime="14:30", fund_code="011613")
            res_feeder = _apply_fund_valuation_calibration(q_feeder)
            assert res_feeder.valuation_corrected is True
            assert res_feeder.gszzl == -1.90  # -2.00 * 0.95

            # Pure index fund
            q_index = FundQuote(name="富国中证红利指数增强A", dwjz=1.0, gsz=1.0, gszzl=0.0, gztime="14:30", fund_code="100032")
            res_index = _apply_fund_valuation_calibration(q_index)
            assert res_index.valuation_corrected is True
            assert res_index.gszzl == -2.00  # -2.00 * 1.00

            # Pure bond fund
            q_bond = FundQuote(name="招商产业债A", dwjz=1.0, gsz=1.0, gszzl=0.01, gztime="14:30", fund_code="002351")
            res_bond = _apply_fund_valuation_calibration(q_bond)
            assert res_bond.valuation_corrected is False
            assert res_bond.gszzl == 0.01

    def test_portfolio_weighted_bias_and_erp_unnormalized_weights(self):
        """
        Verify compute_portfolio_weighted_bias_and_erp handles unnormalized weights (e.g. weights sum to 100 or 50).
        """
        allocations = [
            {"code": "011613", "name": "华夏科创50联接", "weight": 60.0, "bias_20": 4.0},
            {"code": "005561", "name": "易方达红利低波联接A", "weight": 40.0, "bias_20": -2.0}
        ]
        erp_w, bias_w = SmartExecutionDCAEngine.compute_portfolio_weighted_bias_and_erp(
            allocations=allocations,
            snapshot={"erp_percentile": 70.0}
        )
        # 60/100 * 4.0 + 40/100 * (-2.0) = 2.4 - 0.8 = 1.60
        assert bias_w == 1.60
        # 0.6 * (70 - 4.0 * 1.5) + 0.4 * (70 - (-2.0) * 1.5) = 0.6 * 64 + 0.4 * 73 = 38.4 + 29.2 = 67.60
        assert erp_w == 67.60
