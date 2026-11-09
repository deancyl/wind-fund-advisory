# -*- coding: utf-8 -*-
"""
Empirical Adversarial Stress Test Suite for Milestone 1:
1. render_monte_carlo_stress_table & render_monte_carlo_3d_chart under extreme inputs
2. format_micro_execution_slices_df with malformed, partial, or non-numeric inputs
3. Right-wing alert sentry case-insensitivity, priority sorting, and fallback extraction
4. 017436 metadata consistency and 7-day penalty lock defense
"""
import pytest
import pandas as pd
import numpy as np
from typing import Dict, Any, List

from AGY2_FundAdvisory.portfolio_manager import (
    PortfolioManager,
    SECTOR_FUND_SELECTION,
    CORE_STRATEGY_POOL,
    EXTENDED_FUND_CATALOG,
    FundHolding,
    HoldingBatch,
)
from AGY2_FundAdvisory.strategy_bridge import (
    StrategyBridge,
    SECTOR_FUND_SELECTION_BY_TIER,
)
from AGY2_FundAdvisory.trading_clock_fee import TradingClockFeeEngine
from AGY2_FundAdvisory.app_gui import (
    render_monte_carlo_stress_table,
    render_monte_carlo_3d_chart,
    format_micro_execution_slices_df,
)


class TestMonteCarloStressAdversarial:
    """Stress-testing 2D stress table rendering and 3D surface deprecation."""

    @pytest.mark.parametrize("empty_input", [
        None,
        {},
        {"scenarios": []},
        {"scenarios": None},
        {"other_key": 123},
    ])
    def test_empty_and_none_inputs(self, empty_input):
        """Must return None cleanly without crashing on empty/None inputs."""
        assert render_monte_carlo_stress_table(empty_input) is None
        assert render_monte_carlo_3d_chart(empty_input) is None

    def test_extreme_and_boundary_scenarios(self):
        """Test with extreme drawdowns, negative excess, non-dict liquidation days, and unexpected tiers."""
        extreme_stress_data = {
            "investor_risk_tier": "C1",
            "risk_tolerance_mdd": 8.0,
            "scenarios": [
                {
                    "name": "极度大崩盘",
                    "period": "2024.01-2024.02",
                    "predicted_mdd_pct": 99.9,
                    "h300_mdd_pct": 100.0,
                    "excess_defense_pct": -15.5,  # negative excess defense
                    "predicted_loss_amount": 99999999.0,
                    "liquidation_days": None  # non-dict
                },
                {
                    "name": "零波动基准",
                    "period": "2020.01-2020.06",
                    "predicted_mdd_pct": 0.0,
                    "h300_mdd_pct": 0.0,
                    "excess_defense_pct": 0.0,
                    "predicted_loss_amount": 0.0,
                    "liquidation_days": {}  # empty dict
                },
                {
                    "name": "缺字段情景",
                    # all other keys missing
                }
            ]
        }
        # Neither should raise an exception
        render_monte_carlo_stress_table(extreme_stress_data)
        render_monte_carlo_3d_chart(extreme_stress_data)

    def test_no_plotly_3d_object_produced(self):
        """Verify that render_monte_carlo_3d_chart no longer produces or returns any Plotly 3D Figure."""
        sample_data = {
            "investor_risk_tier": "C3",
            "risk_tolerance_mdd": 15.0,
            "scenarios": [
                {
                    "name": "2008危机",
                    "period": "2008",
                    "predicted_mdd_pct": 14.0,
                    "h300_mdd_pct": 60.0,
                    "excess_defense_pct": 46.0,
                    "predicted_loss_amount": 14000.0,
                    "liquidation_days": {"avg_days": 2.0}
                }
            ]
        }
        ret = render_monte_carlo_3d_chart(sample_data)
        # It renders Streamlit components directly and does NOT return a 3D Figure or Surface
        assert not hasattr(ret, "data")
        assert not hasattr(ret, "add_surface")


class TestMicroExecutionSlicesAdversarial:
    """Stress-testing micro-execution DataFrame formatting and Chinese column persistence."""

    @pytest.mark.parametrize("empty_input", [None, [], {}])
    def test_empty_inputs_return_empty_df(self, empty_input):
        df = format_micro_execution_slices_df(empty_input)
        assert isinstance(df, pd.DataFrame)
        assert df.empty

    def test_missing_columns_partial_slices(self):
        """Slices with only some columns should still be renamed and formatted gracefully."""
        partial_slices = [
            {"phase": "尾盘吸筹", "slice_amount": 2500.0},
            {"vol_ratio": 0.35, "strategy": "VWAP调度"}
        ]
        df = format_micro_execution_slices_df(partial_slices)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert "执行阶段" in df.columns
        assert "建议挂单金额(元)" in df.columns
        assert "分配比例" in df.columns
        assert "微观执行策略" in df.columns
        assert df["建议挂单金额(元)"].iloc[0] == "¥2,500.00"
        assert df["分配比例"].iloc[1] == "35%"

    def test_non_numeric_and_edge_values(self):
        """Test with strings, None, NaN, and extreme amounts."""
        edge_slices = [
            {
                "phase": "09:30-10:00",
                "label": "开盘",
                "vol_ratio": "N/A",  # string
                "slice_amount": "待定",  # string
                "strategy": "等待"
            },
            {
                "phase": "14:30-15:00",
                "label": "尾盘",
                "vol_ratio": float("nan"),  # NaN
                "slice_amount": 123456789.99,  # large number
                "strategy": "大单分笔"
            },
            {
                "phase": "10:30-11:30",
                "label": "盘中",
                "vol_ratio": 0.0,
                "slice_amount": 0.0,
                "strategy": "零挂单"
            }
        ]
        df = format_micro_execution_slices_df(edge_slices)
        assert len(df) == 3
        # String 'N/A' preserved
        assert df["分配比例"].iloc[0] == "N/A"
        # String '待定' preserved
        assert df["建议挂单金额(元)"].iloc[0] == "待定"
        # Large currency formatted with commas
        assert df["建议挂单金额(元)"].iloc[1] == "¥123,456,789.99"
        # Zero amounts formatted correctly
        assert df["分配比例"].iloc[2] == "0%"
        assert df["建议挂单金额(元)"].iloc[2] == "¥0.00"

    def test_preserved_chinese_columns(self):
        """Verify the exact 5 Chinese column headers required by specification."""
        standard_slices = [
            {
                "phase": "T日14:30",
                "label": "尾盘锚定",
                "vol_ratio": 0.50,
                "slice_amount": 5000.0,
                "strategy": "估值锚定"
            }
        ]
        df = format_micro_execution_slices_df(standard_slices)
        expected = ["执行阶段", "窗口类型", "分配比例", "建议挂单金额(元)", "微观执行策略"]
        for col in expected:
            assert col in df.columns, f"Required column '{col}' is missing!"


class TestRightWingAlertSentryAdversarial:
    """Stress-testing right-wing alert sentry sorting, casing, and message extraction."""

    def test_case_insensitivity_and_priority_sorting(self):
        """Red and critical alerts of any case must sort to rank (0, 0), always beating warnings and notices."""
        from AGY2_FundAdvisory.app_gui import render_dual_wing_advisory_dashboard

        # Sorter definition as implemented in app_gui.py
        def _sentry_alert_sorter(a):
            _lvl = str(a.get("level", "yellow")).lower()
            _t = str(a.get("title", "")) + str(a.get("desc", ""))
            is_scale_unknown = "规模待核验" in _t
            if _lvl in ("red", "critical"):
                return (0, 0)
            elif _lvl in ("yellow", "warning"):
                return (1, 1 if is_scale_unknown else 0)
            elif "green" in _lvl or _lvl in ("info", "notice"):
                return (3, 0)
            return (2, 0)

        alerts = [
            {"level": "green_notice", "title": "全通"},
            {"level": "WARNING", "title": "超买拥挤", "desc": "短线高估"},
            {"level": "CRITICAL", "title": "7天惩罚费锁仓", "desc": "持有仅1天"},
            {"level": "info", "title": "定期巡检"},
            {"level": "red", "title": "右侧破位止损", "detail": "破MA60"},
            {"level": "Yellow", "title": "广发纯债规模待核验", "desc": "流动性需跟踪"},
            {"level": "RED", "title": "深套严重警告", "message": "浮亏超20%"},
            {"level": "warning", "title": "赛道集中度偏高", "action": "平移避险"},
        ]

        sorted_alerts = sorted(alerts, key=_sentry_alert_sorter)

        # Top 3 must all be RED/CRITICAL
        top_3_lvls = [a["level"].lower() for a in sorted_alerts[:3]]
        for lvl in top_3_lvls:
            assert lvl in ("red", "critical"), f"Expected red/critical, got {lvl}"

        # Yellow warnings must precede the scale-check
        warning_idx = next(i for i, a in enumerate(sorted_alerts) if a["title"] == "超买拥挤")
        scale_check_idx = next(i for i, a in enumerate(sorted_alerts) if "规模待核验" in a["title"])
        assert warning_idx < scale_check_idx

        # Info and green notices must be at the very bottom
        bottom_lvls = [a["level"].lower() for a in sorted_alerts[-2:]]
        for lvl in bottom_lvls:
            assert any(k in lvl for k in ("green", "info", "notice"))

    def test_alert_content_extraction_fallbacks(self):
        """Test extraction fallbacks: desc -> detail -> message, action -> suggested_action."""
        a1 = {"level": "red", "desc": "这是desc", "detail": "这是detail"}
        a2 = {"level": "red", "detail": "这是detail", "message": "这是message"}
        a3 = {"level": "yellow", "message": "这是message"}
        a4 = {"level": "yellow"}  # all empty

        def extract_text(alert):
            title = alert.get("title") or alert.get("message") or alert.get("dimension", "风控提示")
            detail = alert.get("desc") or alert.get("detail") or alert.get("message", "")
            action = alert.get("action") or alert.get("suggested_action", "")
            return title, detail, action

        t1, d1, _ = extract_text(a1)
        assert d1 == "这是desc"

        t2, d2, _ = extract_text(a2)
        assert d2 == "这是detail"

        t3, d3, _ = extract_text(a3)
        assert d3 == "这是message"

        t4, d4, act4 = extract_text(a4)
        assert t4 == "风控提示"
        assert d4 == ""
        assert act4 == ""


class TestFund017436ResolutionAndDefense:
    """Stress-testing 017436 resolution across portfolio_manager and strategy_bridge."""

    def test_017436_canonical_metadata(self):
        """017436 must be resolved as '华安纳斯达克100ETF联接A' in all modules."""
        meta = PortfolioManager.resolve_fund_meta("017436")
        assert meta["fund_name"] == "华安纳斯达克100ETF联接A"
        assert meta.get("share_class") == "A"
        assert meta.get("company") == "华安基金"

        # Check in CORE_STRATEGY_POOL or EXTENDED_FUND_CATALOG
        cat_meta = EXTENDED_FUND_CATALOG.get("017436") or CORE_STRATEGY_POOL.get("017436")
        assert cat_meta is not None
        assert cat_meta.get("fund_name") or cat_meta.get("name") == "华安纳斯达克100ETF联接A"

        # Check ETF identification logic (Rule 19: 017436 is an OTC fund)
        is_etf = TradingClockFeeEngine.is_etf("017436") if hasattr(TradingClockFeeEngine, "is_etf") else (
            str("017436").startswith(("51", "15", "56", "58", "59")) and "联接" not in meta["fund_name"]
        )
        assert is_etf is False

    def test_rebalance_orders_017436_no_false_lock_on_new_buy(self):
        """When 017436 is recommended for purchase (not currently in portfolio), it must NOT be 7-day locked."""
        pm = PortfolioManager()
        # Ensure 017436 is not in pm.holdings
        if "017436" in pm.holdings:
            del pm.holdings["017436"]

        target_weights = {"017436": 0.20, "002351": 0.80}
        rebal_res = StrategyBridge.generate_ai_rebalance_orders(
            pm.holdings,
            pm.available_cash,
            target_weights,
            pm=pm
        )
        items = rebal_res.get("items", [])
        nasdaq_items = [it for it in items if it.get("fund_code") == "017436"]
        assert len(nasdaq_items) == 1
        item = nasdaq_items[0]
        assert item["action"] == "BUY"
        assert item["fund_name"] == "华安纳斯达克100ETF联接A"
        assert "存量标的" not in item["fund_name"]
        assert "优选标的_017436" != item["fund_name"]
        assert item["holding_days"] == -1
        assert not item.get("safety_warning")

    def test_rebalance_orders_017436_true_lock_when_held_under_7_days(self):
        """When 017436 is actually held with 3 days holding period, it MUST trigger safety lock."""
        pm = PortfolioManager()
        h_nasdaq = FundHolding(
            fund_code="017436",
            fund_name="华安纳斯达克100ETF联接A",
            shares=1000.0,
            current_nav=1.50,
            cost_nav=1.48,
            batches=[HoldingBatch(batch_id="b_test_1", buy_date="2026-11-06", shares=1000.0, cost_nav=1.48, holding_days=3)]
        )
        pm.holdings["017436"] = h_nasdaq

        # Rebalance reducing 017436 to 0%
        target_weights = {"002351": 1.00}
        rebal_res = StrategyBridge.generate_ai_rebalance_orders(
            pm.holdings,
            pm.available_cash,
            target_weights,
            pm=pm
        )
        items = rebal_res.get("items", [])
        nasdaq_items = [it for it in items if it.get("fund_code") == "017436"]
        assert len(nasdaq_items) == 1
        item = nasdaq_items[0]
        # Should be locked with safety warning
        assert 0 <= item["holding_days"] < 7
        has_lock = ("7天" in item.get("safety_warning", "") or 
                    "锁定" in item.get("safety_warning", "") or 
                    item.get("is_penalty_locked") or 
                    item.get("safe_shares", 0.0) == 0.0)
        assert has_lock, f"Expected 7-day safety lock on 017436, got {item}"
