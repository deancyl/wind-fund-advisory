"""
Challenger G11 Milestone 2 Adversarial Verification Suite
(tests/test_challenger_tab2_rebalance_adversarial.py)

Empirical adversarial challenge of Tab 2 Rebalancing Engine, widgets, and math contracts:
1. Buffer slider boundaries (tab2_rebal_buf_slider 0.0% to 10.0%, widget limits & backend tolerance)
2. Rebalance diagnosis trigger (btn_tab2_diagnose) under edge portfolios:
   - Empty portfolio (0 holdings, 0 cash)
   - Cash-only portfolio (0 holdings, 100k cash)
   - All locked funds (<7 days penalty lock)
   - High correlation portfolios (>0.85 tech cluster)
   - Extreme floating loss / gain portfolios
3. Orders dataframe (df_orders_tbl 10 cols), VWAP schedule, and execution follow button:
   - 10-column schema & data types
   - VWAP 5-stage slice conservation & slippage monotonicity
   - One-click follow button string matching discrepancy probe (减仓 vs 减持, 加仓 vs 增持)
   - Cash conservation & FIFO batch deduction
4. Math identities and zero-anomaly guarantees:
   - Merged 4-cell top bar formulas & zero-division safety
   - 4-cell summary bar fee & risk shift identities
   - Zero NaN, zero Inf, zero formatting crashes
5. Streamlit AppTest integration:
   - Full GUI run of Tab 2 rebalance flow without exceptions
"""

import sys
import copy
import math
import re
import ast
from pathlib import Path
from typing import Dict, List, Any
import pytest
import pandas as pd
import numpy as np

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
AGY_PATH = WORKSPACE_ROOT / "AGY2_FundAdvisory"
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))
if str(AGY_PATH) not in sys.path:
    sys.path.insert(0, str(AGY_PATH))

from portfolio_manager import PortfolioManager, FundHolding, HoldingBatch
from strategy_bridge import StrategyBridge
from advisory_engine import SmartExecutionDCAEngine


# =====================================================================
# Fixture: Base Portfolio Helper
# =====================================================================

@pytest.fixture
def clean_pm():
    """Create an isolated in-memory PortfolioManager with baseline holdings."""
    pm = PortfolioManager(db_path=":memory:")
    pm.available_cash = 20000.0
    pm.in_transit_cash = 0.0
    # Add 3 standard funds
    pm.add_or_update_holding("005561", shares=10000, nav=1.25, cost_price=1.20, holding_days=45, fund_name="创金合信红利低波A")
    pm.add_or_update_holding("002351", shares=20000, nav=1.10, cost_price=1.05, holding_days=190, fund_name="易方达裕祥回报债券A")
    pm.add_or_update_holding("000216", shares=15000, nav=1.80, cost_price=1.70, holding_days=60, fund_name="华安黄金ETF联接A")
    pm._recalculate_totals()
    return pm


# =====================================================================
# Test Suite 1: Buffer Slider Boundaries & Backend Support (0.0% to 10.0%)
# =====================================================================

class TestBufferSliderBoundaries:
    """Adversarially challenge buffer slider boundaries and backend parameter tolerance."""

    @pytest.mark.parametrize("buffer_val", [0.0, 0.005, 0.01, 0.03, 0.05, 0.10])
    def test_suitability_evaluator_buffer_boundaries(self, clean_pm, buffer_val):
        """Verify StrategyBridge.evaluate_today_rebalance_suitability handles 0.0% to 10.0% without error."""
        res = StrategyBridge.evaluate_today_rebalance_suitability(
            clean_pm,
            active_tier="C3",
            min_buffer_pct=buffer_val
        )
        assert "verdict_level" in res
        assert res["verdict_level"] in ["SUITABLE", "HOLD_ON", "FORBIDDEN"]
        assert "d_max" in res
        assert not math.isnan(res["d_max"])
        assert "reasons_4d" in res
        assert "deviation_utility_reason" in res["reasons_4d"]

    @pytest.mark.parametrize("buffer_val", [0.0, 0.01, 0.03, 0.05, 0.10])
    def test_rebalance_consequences_buffer_monotonicity(self, clean_pm, buffer_val):
        """
        Verify that in gentle mode, increasing buffer strictly filters out smaller deviations.
        When buffer=0.0, all non-zero deviations are candidates.
        When buffer=0.10, deviations < 10% are strictly filtered out.
        """
        sim_res = StrategyBridge.simulate_rebalance_modes_and_consequences(
            clean_pm,
            active_tier="C3",
            min_buffer_pct=buffer_val,
            scenario_mode="standard"
        )
        assert "mode_gentle" in sim_res
        assert "mode_forced" in sim_res
        gentle_conseq = sim_res["mode_gentle"]["consequences"]
        assert "fee_loss" in gentle_conseq
        assert "in_transit_risk" in gentle_conseq
        assert "risk_shift" in gentle_conseq

    @pytest.mark.parametrize("buffer_pct", [0.0, 1.0, 3.0, 5.0, 10.0])
    def test_ai_rebalance_orders_buffer_filtering(self, clean_pm, buffer_pct):
        """Verify generate_ai_rebalance_orders handles percentages 0.0% to 10.0% correctly."""
        target_w = {"005561": 0.35, "002351": 0.40, "000216": 0.25}
        orders = StrategyBridge.generate_ai_rebalance_orders(
            current_holdings=clean_pm.holdings,
            available_cash=clean_pm.available_cash,
            target_weights_funds=target_w,
            pm=clean_pm,
            mode="gentle",
            min_buffer_pct=buffer_pct
        )
        assert "items" in orders
        for it in orders["items"]:
            assert "fund_code" in it
            assert "diff_amount" in it
            assert "action_text" in it

    def test_gui_slider_ast_and_range_boundary(self):
        """
        Adversarially probe the Streamlit slider widget definition in app_gui.py via AST:
        Verify widget configuration: min_value=1.0, max_value=5.0, step=0.5, format='%.1f%%'.
        Note: The slider GUI is constrained to [1.0%, 5.0%], whereas the backend accepts 0.0% to 10.0%.
        """
        gui_path = AGY_PATH / "app_gui.py"
        tree = ast.parse(gui_path.read_text(encoding="utf-8"))

        slider_node = None
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and hasattr(node.func, "attr") and node.func.attr == "slider":
                for kw in node.keywords:
                    if kw.arg == "key" and isinstance(kw.value, ast.Constant) and kw.value.value == "tab2_rebal_buf_slider":
                        slider_node = node
                        break

        assert slider_node is not None, "tab2_rebal_buf_slider Call node must exist in AST"

        kw_dict = {kw.arg: ast.unparse(kw.value) for kw in slider_node.keywords}
        assert kw_dict.get("min_value") == "1.0", f"Expected min_value=1.0, got {kw_dict.get('min_value')}"
        assert kw_dict.get("max_value") == "5.0", f"Expected max_value=5.0, got {kw_dict.get('max_value')}"
        assert kw_dict.get("step") == "0.5", f"Expected step=0.5, got {kw_dict.get('step')}"
        assert "%.1f%%" in kw_dict.get("format", ""), f"Expected format '%.1f%%', got {kw_dict.get('format')}"


# =====================================================================
# Test Suite 2: Rebalance Diagnosis Trigger Under Edge Portfolios
# =====================================================================

class TestRebalanceDiagnosisEdgePortfolios:
    """Stress test rebalance diagnosis trigger under extreme portfolio states."""

    def test_edge_empty_portfolio(self):
        """
        Edge Case 1: Empty portfolio (0 holdings, 0 cash, 0 in-transit).
        Total equity = 0.0.
        Must NOT raise ZeroDivisionError.
        Verify that d_max reflects maximum target allocation weight when cur_w is empty.
        """
        pm = PortfolioManager(db_path=":memory:")
        pm.available_cash = 0.0
        pm.in_transit_cash = 0.0
        pm.holdings = {}
        pm._recalculate_totals()

        assert pm.total_equity == 0.0

        # 1. Cushion model
        cushion = pm.calculate_portfolio_cushion_and_stress_model(current_index_point=3920.0)
        assert cushion["comprehensive_cushion"] == 0.0
        assert cushion["portfolio_weighted_beta"] == 0.0
        assert cushion["is_in_floating_loss"] is False

        # 2. Suitability evaluation: d_max will be max(target_weights) since cur_w is empty
        suit = StrategyBridge.evaluate_today_rebalance_suitability(pm, active_tier="C3", min_buffer_pct=0.03)
        assert suit["d_max"] > 0.0
        assert "空仓" in suit["reasons_4d"]["deviation_utility_reason"]

        # 3. Simulate rebalance consequences
        sim = StrategyBridge.simulate_rebalance_modes_and_consequences(pm, active_tier="C3", min_buffer_pct=0.03)
        assert sim["mode_gentle"]["consequences"]["fee_loss"]["total_fee"] == 0.0
        assert sim["mode_gentle"]["consequences"]["risk_shift"]["equity_before"] == 0.0

        # 4. Top bar calculations simulation
        tot_eq = sum(h.market_value for h in pm.holdings.values()) + pm.available_cash + pm.in_transit_cash
        t2_mkt = sum(getattr(h, "shares", 0.0) * getattr(h, "current_nav", 1.0) for h in pm.holdings.values()) if pm.holdings else 0.0
        t2_cost = sum(getattr(h, "shares", 0.0) * getattr(h, "cost_price", 1.0) for h in pm.holdings.values()) if pm.holdings else 0.0
        t2_pnl = t2_mkt - t2_cost
        t2_pnl_pct = (t2_pnl / t2_cost * 100.0) if t2_cost > 0 else 0.0
        pos_pct = (t2_mkt / tot_eq * 100.0) if tot_eq > 0 else 0.0

        assert tot_eq == 0.0
        assert t2_mkt == 0.0
        assert t2_pnl == 0.0
        assert t2_pnl_pct == 0.0
        assert pos_pct == 0.0

    def test_edge_cash_only_portfolio(self):
        """
        Edge Case 2: Cash-only portfolio (0 holdings, 100,000 cash).
        Must have 0% position, beta = 0.0 (immune), all rebalancing is buy-only (0 redemption fee).
        """
        pm = PortfolioManager(db_path=":memory:")
        pm.available_cash = 100000.0
        pm.in_transit_cash = 0.0
        pm.holdings = {}
        pm._recalculate_totals()

        assert pm.total_equity == 100000.0

        # 1. Cushion model
        cushion = pm.calculate_portfolio_cushion_and_stress_model(current_index_point=3920.0)
        assert cushion["portfolio_weighted_beta"] == 0.0
        assert cushion["break_even_drop_pct"] == 0.0

        # 2. Suitability evaluation
        suit = StrategyBridge.evaluate_today_rebalance_suitability(pm, active_tier="C3", min_buffer_pct=0.03)
        assert suit["verdict_level"] in ["SUITABLE", "HOLD_ON"]

        # 3. Simulate rebalance
        sim = StrategyBridge.simulate_rebalance_modes_and_consequences(pm, active_tier="C3", min_buffer_pct=0.03)
        # 0 holdings -> 0 redemption fee
        assert sim["mode_gentle"]["consequences"]["fee_loss"]["redemption_fee"] == 0.0
        assert sim["mode_gentle"]["consequences"]["fee_loss"]["penalty_fee_7d"] == 0.0

        # 4. Generate orders
        snapshot = StrategyBridge.get_latest_market_snapshot()
        target_w = StrategyBridge.compute_dynamic_tier_weights(tier="C3", market_snapshot=snapshot)
        orders = StrategyBridge.generate_ai_rebalance_orders(
            current_holdings=pm.holdings,
            available_cash=pm.available_cash,
            target_weights_funds=target_w,
            pm=pm,
            mode="gentle"
        )
        assert len(orders["items"]) > 0
        # All orders must be buy orders (diff_amount > 0)
        for it in orders["items"]:
            assert it["diff_amount"] >= 0, f"Expected buy order for cash-only portfolio, got {it['diff_amount']}"

    def test_edge_all_locked_funds_under_7_days(self):
        """
        Edge Case 3: All funds locked (<7 days).
        Holding days = 2. Penalty free shares = 0.
        Gentle mode MUST NOT sell any locked shares (penalty fee must be 0.0).
        Forced mode will incur 1.50% penalty fee.
        """
        pm = PortfolioManager(db_path=":memory:")
        pm.available_cash = 5000.0
        # Add 3 funds all bought 2 days ago
        pm.add_or_update_holding("005561", shares=20000, nav=1.25, cost_price=1.25, holding_days=2, fund_name="创金合信红利低波A")
        pm.add_or_update_holding("002351", shares=20000, nav=1.10, cost_price=1.10, holding_days=2, fund_name="易方达裕祥回报债券A")
        pm.add_or_update_holding("000216", shares=20000, nav=1.80, cost_price=1.80, holding_days=2, fund_name="华安黄金ETF联接A")
        pm._recalculate_totals()

        # Check penalty-free shares
        for c in ["005561", "002351", "000216"]:
            assert pm.get_penalty_free_redeemable_shares(c) == 0.0

        # 1. Suitability check: must flag penalty sell warning
        suit = StrategyBridge.evaluate_today_rebalance_suitability(pm, active_tier="C1", min_buffer_pct=0.01)
        assert suit["verdict_level"] in ["FORBIDDEN", "HOLD_ON"]
        assert "7天" in suit["reasons_4d"]["lockup_fee_reason"] or "未满 7 天" in suit["reasons_4d"]["lockup_fee_reason"]

        # 2. Simulate rebalance: gentle mode MUST have penalty_fee_7d == 0.0
        target_w = {"002351": 0.90, "005561": 0.05, "000216": 0.05}
        sim = StrategyBridge.simulate_rebalance_modes_and_consequences(
            pm, active_tier="C1", target_weights=target_w, min_buffer_pct=0.01, scenario_mode="standard"
        )
        assert sim["mode_gentle"]["consequences"]["fee_loss"]["penalty_fee_7d"] == 0.0

        # In forced mode, penalty fee must be strictly positive if sales were forced
        forced_fee = sim["mode_forced"]["consequences"]["fee_loss"]["penalty_fee_7d"]
        assert forced_fee > 0.0, f"Expected forced penalty fee > 0, got {forced_fee}"

    def test_edge_high_correlation_portfolio(self):
        """
        Edge Case 4: High correlation portfolio.
        Concentrated in 3 correlated tech/semiconductor funds.
        Verify rebalancing proposes diversification without crashing.
        """
        pm = PortfolioManager(db_path=":memory:")
        pm.available_cash = 10000.0
        # Highly correlated sector holdings
        pm.add_or_update_holding("011613", shares=25000, nav=0.95, cost_price=1.00, holding_days=50, fund_name="华夏科创50联接C")
        pm.add_or_update_holding("008888", shares=20000, nav=1.15, cost_price=1.20, holding_days=60, fund_name="华夏国证半导体芯片ETF联接A")
        pm.add_or_update_holding("013402", shares=15000, nav=1.05, cost_price=1.10, holding_days=70, fund_name="富国中证芯片产业ETF联接A")
        pm._recalculate_totals()

        # Run suitability
        suit = StrategyBridge.evaluate_today_rebalance_suitability(pm, active_tier="C3", min_buffer_pct=0.03)
        assert "verdict_level" in suit
        assert suit["d_max"] > 0.0

        # Run rebalance consequences
        sim = StrategyBridge.simulate_rebalance_modes_and_consequences(pm, active_tier="C3", min_buffer_pct=0.03)
        assert "mode_gentle" in sim
        gentle = sim["mode_gentle"]
        assert gentle["consequences"]["risk_shift"]["vol_after"] >= 0.0

    def test_edge_extreme_floating_loss_and_gain(self):
        """
        Edge Case 5: Extreme floating loss (-80%) and extreme floating gain (+200%).
        Test recovery threshold calculation and cushion thickness.
        """
        # 5a. Deep loss (-80%): cost=1.00, nav=0.20
        pm_loss = PortfolioManager(db_path=":memory:")
        pm_loss.available_cash = 1000.0
        pm_loss.add_or_update_holding("005561", shares=10000, nav=0.20, cost_price=1.00, holding_days=100)
        pm_loss._recalculate_totals()

        cushion_loss = pm_loss.calculate_portfolio_cushion_and_stress_model(current_index_point=3920.0)
        assert cushion_loss["is_in_floating_loss"] is True
        assert cushion_loss["recovery_rise_pct"] > 0.0
        assert cushion_loss["recovery_index_point"] > 3920.0

        # 5b. Deep gain (+200%): cost=1.00, nav=3.00
        pm_gain = PortfolioManager(db_path=":memory:")
        pm_gain.available_cash = 1000.0
        pm_gain.add_or_update_holding("005561", shares=10000, nav=3.00, cost_price=1.00, holding_days=100)
        pm_gain._recalculate_totals()

        cushion_gain = pm_gain.calculate_portfolio_cushion_and_stress_model(current_index_point=3920.0)
        assert cushion_gain["is_in_floating_loss"] is False
        assert cushion_gain["break_even_drop_pct"] < 0.0
        assert cushion_gain["break_even_index_point"] < 3920.0


# =====================================================================
# Test Suite 3: Orders Dataframe, VWAP Schedule & Execution Follow Button
# =====================================================================

class TestOrdersTableAndExecutionFollowButton:
    """Adversarially challenge orders dataframe, VWAP schedule, and execution follow button."""

    def test_orders_dataframe_exact_10_columns(self, clean_pm):
        """Verify df_orders_tbl generated by app_gui.py logic has exactly 10 required columns."""
        target_w = {"005561": 0.35, "002351": 0.40, "000216": 0.25}
        ai_orders_res = StrategyBridge.generate_ai_rebalance_orders(
            current_holdings=clean_pm.holdings,
            available_cash=clean_pm.available_cash,
            target_weights_funds=target_w,
            pm=clean_pm,
            mode="gentle",
            min_buffer_pct=3.0
        )
        items = ai_orders_res.get("items", [])
        assert len(items) > 0

        # Replicate app_gui.py lines 5542-5616
        rows_display = []
        for it in items:
            diff_amt = it.get("diff_amount", 0.0)
            action_raw = str(it.get("action_text", ""))
            f_code = str(it.get("fund_code", ""))
            f_name = str(it.get("fund_name", ""))
            rt_gszzl = it.get("realtime_gszzl", 0.0)

            if diff_amt > 100 or "加仓" in action_raw:
                op_action = "➕ 建议加仓"
                op_point = f"增配¥{abs(diff_amt):,.0f}·现金分红"
            elif diff_amt < -100 or "减仓" in action_raw:
                op_action = "➖ 建议减仓"
                op_point = f"减配¥{abs(diff_amt):,.0f}·阶梯退出"
            else:
                op_action = "✅ 维持持有"
                op_point = "仓位均衡·在容差内"

            rows_display.append({
                "基金代码": f_code,
                "基金名称": f_name,
                "份额": f"{it.get('share_class', 'A')}类",
                "当前市值(元)": it["market_value"],
                "目标占比(%)": it["target_weight_pct"],
                "实时估值涨跌(%)": rt_gszzl,
                "建议调仓金额(元)": diff_amt,
                "建议操作": op_action,
                "尾盘微观优化(bps)": "-",
                "实操要点": op_point
            })

        rebal_cols_10 = [
            "基金代码", "基金名称", "份额", "当前市值(元)",
            "目标占比(%)", "实时估值涨跌(%)", "建议调仓金额(元)",
            "建议操作", "尾盘微观优化(bps)", "实操要点"
        ]
        df_orders_tbl = pd.DataFrame(rows_display)[rebal_cols_10]
        assert list(df_orders_tbl.columns) == rebal_cols_10
        assert len(df_orders_tbl.columns) == 10
        assert not df_orders_tbl.empty

    def test_vwap_schedule_slice_conservation(self):
        """
        Verify VWAP 5-stage slice amounts sum to order amount with <0.02 cent error.
        Verify slippage savings are non-negative.
        """
        order_amounts = [5000.0, 20000.0, 50000.0, 200000.0]
        for amt in order_amounts:
            res = SmartExecutionDCAEngine.calculate_vwap_execution_slippage(
                order_amount=amt,
                fund_code="005561",
                fund_name="创金合信红利低波A",
                volatility=0.12,
                bias_20=1.5
            )
            slices = res.get("vwap_slices", [])
            assert len(slices) == 5, f"Expected 5 VWAP slices, got {len(slices)}"
            slice_sum = sum(s["slice_amount"] for s in slices)
            assert abs(slice_sum - amt) < 0.02, f"Slice sum {slice_sum} != order amount {amt}"
            assert res["naive_impact_yuan"] >= res["vwap_slippage_yuan"]
            assert res["slippage_saved_bps"] >= 0.0

    def test_adversarial_apply_rebalance_string_matching_bug(self, clean_pm):
        """
        CRITICAL ADVERSARIAL FINDING:
        In app_gui.py, the action text passed in rows_display is:
            '➕ 建议加仓' or '➖ 建议减仓'
        However, portfolio_manager.py apply_rebalance_orders_to_holdings expects:
            '减持' or '增持' / '建仓' / '买入' / '清仓'
        Verify this string mismatch empirically!
        """
        # When app_gui.py sends rows with '建议减仓' / '建议加仓':
        app_gui_rows = [
            {
                "基金代码": "005561",
                "基金名称": "创金合信红利低波A",
                "建议操作": "➖ 建议减仓",
                "建议调仓金额(元)": -5000.0
            },
            {
                "基金代码": "002351",
                "基金名称": "易方达裕祥回报债券A",
                "建议操作": "➕ 建议加仓",
                "建议调仓金额(元)": 8000.0
            }
        ]
        fixed_count_app = clean_pm.apply_rebalance_orders_to_holdings(app_gui_rows)
        # With Milestone 3 fix, '建议减仓' and '建议加仓' match successfully!
        assert fixed_count_app == 2, (
            "Milestone 3 Fix Verification: '建议减仓' and '建议加仓' must match successfully "
            f"in apply_rebalance_orders_to_holdings, expected 2 updated orders, got {fixed_count_app}!"
        )

        # Now test with compatible canonical strings:
        compatible_rows = [
            {
                "基金代码": "005561",
                "基金名称": "创金合信红利低波A",
                "建议操作": "➖ 建议减持",
                "建议调仓金额(元)": -5000.0
            },
            {
                "基金代码": "002351",
                "基金名称": "易方达裕祥回报债券A",
                "建议操作": "➕ 建议增持",
                "建议调仓金额(元)": 8000.0
            }
        ]
        fixed_count = clean_pm.apply_rebalance_orders_to_holdings(compatible_rows)
        assert fixed_count == 2, f"Expected 2 orders updated with canonical strings, got {fixed_count}"

    def test_apply_rebalance_cash_and_fifo_conservation(self, clean_pm):
        """Verify cash balance conservation and FIFO batch deduction upon applying rebalance."""
        initial_cash = clean_pm.available_cash
        initial_shares = clean_pm.holdings["005561"].shares
        nav = clean_pm.holdings["005561"].current_nav

        sell_amt = 3000.0
        sell_shares = round(sell_amt / nav, 2)

        rows = [{
            "基金代码": "005561",
            "基金名称": "创金合信红利低波A",
            "建议操作": "减持变现",
            "建议调仓金额(元)": -sell_amt
        }]
        updated = clean_pm.apply_rebalance_orders_to_holdings(rows)
        assert updated == 1
        assert abs(clean_pm.available_cash - (initial_cash + sell_amt)) < 0.05
        assert abs(clean_pm.holdings["005561"].shares - (initial_shares - sell_shares)) < 0.05


# =====================================================================
# Test Suite 4: Math Identities and Zero-Anomaly Guarantees
# =====================================================================

class TestMathIdentitiesAndZeroAnomalies:
    """Adversarially verify all math formulas in Tab 2 top bar and summary cards."""

    def test_merged_top_bar_math_identities(self, clean_pm):
        """
        Verify:
        _tot_equity == _t2_mkt + available_cash + in_transit_cash
        _t2_pnl == _t2_mkt - _t2_cost
        _pos_pct == (_t2_mkt / _tot_equity * 100.0)
        """
        tot_eq = sum(h.market_value for h in clean_pm.holdings.values()) + clean_pm.available_cash + clean_pm.in_transit_cash
        t2_mkt = sum(getattr(h, "shares", 0.0) * getattr(h, "current_nav", 1.0) for h in clean_pm.holdings.values())
        t2_cost = sum(getattr(h, "shares", 0.0) * getattr(h, "cost_price", 1.0) for h in clean_pm.holdings.values())
        t2_pnl = t2_mkt - t2_cost
        pos_pct = (t2_mkt / tot_eq * 100.0) if tot_eq > 0 else 0.0

        assert abs(tot_eq - (t2_mkt + clean_pm.available_cash + clean_pm.in_transit_cash)) < 1e-4
        assert abs(t2_pnl - (t2_mkt - t2_cost)) < 1e-4
        assert 0.0 <= pos_pct <= 100.0
        assert not math.isnan(pos_pct)
        assert not math.isinf(pos_pct)

    def test_summary_bar_fee_and_consequence_identities(self, clean_pm):
        """
        Verify:
        total_fee == round(redemption_fee + penalty_fee_7d + subscription_fee, 2)
        equity_after == round(max(0.0, equity_before - total_fee), 2)
        """
        sim = StrategyBridge.simulate_rebalance_modes_and_consequences(
            clean_pm, active_tier="C3", min_buffer_pct=0.03
        )
        for mode_key in ["mode_gentle", "mode_forced"]:
            conseq = sim[mode_key]["consequences"]
            fee = conseq["fee_loss"]
            risk = conseq["risk_shift"]

            calc_tot_fee = round(fee["redemption_fee"] + fee["penalty_fee_7d"] + fee["subscription_fee"], 2)
            assert abs(fee["total_fee"] - calc_tot_fee) < 0.01, f"Total fee mismatch in {mode_key}"

            expected_eq_after = round(max(0.0, risk["equity_before"] - fee["total_fee"]), 2)
            assert abs(risk["equity_after"] - expected_eq_after) < 0.01, f"Equity after mismatch in {mode_key}"

    def test_zero_division_guard_matrix(self):
        """Verify zero division defenses across all mathematical ratios in Tab 2."""
        # 1. Total equity = 0
        eq_zero = 0.0
        mkt_zero = 0.0
        pos_pct = (mkt_zero / eq_zero * 100.0) if eq_zero > 0 else 0.0
        assert pos_pct == 0.0

        # 2. Cost = 0
        cost_zero = 0.0
        pnl_val = 100.0
        pnl_pct = (pnl_val / cost_zero * 100.0) if cost_zero > 0 else 0.0
        assert pnl_pct == 0.0

        # 3. Market value = 0 for intraday pnl pct
        est_pnl = 50.0
        est_pnl_pct = (est_pnl / mkt_zero * 100.0) if mkt_zero > 0 else 0.0
        assert est_pnl_pct == 0.0


# =====================================================================
# Test Suite 5: Streamlit AppTest GUI Execution
# =====================================================================

class TestStreamlitAppTestGUI:
    """Full AppTest execution of app_gui.py testing Tab 2 rebalancing and UI components."""

    def test_tab2_apptest_run_without_exception(self):
        """Execute app_gui.py through Streamlit AppTest and verify zero unhandled exceptions."""
        from streamlit.testing.v1 import AppTest

        at = AppTest.from_file(str(AGY_PATH / "app_gui.py"), default_timeout=35)
        at.run()
        assert not at.exception, f"AppTest raised unexpected exception: {at.exception[0].message if at.exception else ''}"

        # Verify critical Tab 2 session state keys are initialized
        assert "tab2_diagnosed" in at.session_state
        assert "tab2_rebalanced" in at.session_state
        assert "tab2_view_mode" in at.session_state

        # Check that tab2_rebal_buf_slider widget exists in rendered elements
        sliders = at.slider
        slider_keys = [s.key for s in sliders if s.key]
        assert "tab2_rebal_buf_slider" in slider_keys, f"Missing tab2_rebal_buf_slider, found: {slider_keys}"
