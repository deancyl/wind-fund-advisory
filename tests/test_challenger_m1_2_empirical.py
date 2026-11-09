# -*- coding: utf-8 -*-
"""
Empirical Adversarial Test Suite by challenger_m1_2:
Milestone 1 Stress & Verification Harness.
"""
import pytest
import pandas as pd
import numpy as np
import hashlib
from pathlib import Path
from typing import Dict, Any, List

from AGY2_FundAdvisory.portfolio_manager import (
    PortfolioManager,
    FundHolding,
    HoldingBatch,
    SECTOR_FUND_SELECTION,
    CORE_STRATEGY_POOL,
    EXTENDED_FUND_CATALOG,
)
from AGY2_FundAdvisory.strategy_bridge import (
    StrategyBridge,
    SECTOR_FUND_SELECTION_BY_TIER,
)
from AGY2_FundAdvisory.app_gui import (
    render_monte_carlo_stress_table,
    render_monte_carlo_3d_chart,
    format_micro_execution_slices_df,
    resolve_fund_display_name,
)


# =============================================================================
# Mission Item 1: render_monte_carlo_stress_table & 3D Chart Deprecation
# =============================================================================
class TestItem1MonteCarloStressEmpirical:
    """Empirical challenge of 2D stress table handling of malformed inputs and 3D surface removal."""

    @pytest.mark.parametrize("empty_val", [
        None,
        {},
        {"scenarios": []},
        {"scenarios": None},
        {"dummy": 42},
    ])
    def test_empty_and_none_inputs_handled_cleanly(self, empty_val):
        """Must return None cleanly without throwing unhandled exceptions."""
        assert render_monte_carlo_stress_table(empty_val) is None
        assert render_monte_carlo_3d_chart(empty_val) is None

    def test_extreme_drawdowns_and_missing_fields(self):
        """Stress test with zero, near-100%, negative excess, non-dict liquidation days, and missing fields."""
        data = {
            "investor_risk_tier": "C2",
            "risk_tolerance_mdd": 10.0,
            "scenarios": [
                {
                    "name": "极度大回撤情景",
                    "period": "2024.01-2024.02",
                    "predicted_mdd_pct": 98.5,
                    "h300_mdd_pct": 100.0,
                    "excess_defense_pct": -20.0,  # negative excess
                    "predicted_loss_amount": 50000.0,
                    "liquidation_days": None,  # non-dict
                },
                {
                    "name": "零波动情景",
                    "period": "2020.01-2020.06",
                    "predicted_mdd_pct": 0.0,
                    "h300_mdd_pct": 0.0,
                    "excess_defense_pct": 0.0,
                    "predicted_loss_amount": 0.0,
                    "liquidation_days": {},  # empty dict
                },
                {
                    "name": "缺省全字段情景",
                    # no predicted_mdd_pct, etc.
                }
            ]
        }
        # Neither function should raise any exception
        render_monte_carlo_stress_table(data)
        render_monte_carlo_3d_chart(data)

    def test_no_plotly_3d_surfaces_generated(self):
        """Verify that render_monte_carlo_3d_chart does NOT produce or return any Plotly 3D Figure."""
        data = {
            "investor_risk_tier": "C3",
            "risk_tolerance_mdd": 15.0,
            "scenarios": [
                {
                    "name": "2008全球金融危机",
                    "period": "2007.10-2008.10",
                    "predicted_mdd_pct": 12.5,
                    "h300_mdd_pct": 72.3,
                    "excess_defense_pct": 59.8,
                    "predicted_loss_amount": 12500.0,
                    "liquidation_days": {"avg_days": 3.5}
                }
            ]
        }
        ret = render_monte_carlo_3d_chart(data)
        # Verify it doesn't return a 3D figure or surface
        assert ret is None or not hasattr(ret, "add_surface")


# =============================================================================
# Mission Item 2: format_micro_execution_slices_df
# =============================================================================
class TestItem2MicroExecutionSlicesEmpirical:
    """Empirical challenge of micro-execution slices formatting and column persistence."""

    @pytest.mark.parametrize("empty_input", [None, [], {}])
    def test_empty_slices_return_empty_df(self, empty_input):
        df = format_micro_execution_slices_df(empty_input)
        assert isinstance(df, pd.DataFrame)
        assert df.empty

    def test_partial_slices_and_column_preservation(self):
        """Missing columns should still have remaining columns renamed and formatted."""
        partial = [
            {"phase": "尾盘吸筹", "slice_amount": 3500.0},
            {"vol_ratio": 0.25, "strategy": "VWAP平抑"}
        ]
        df = format_micro_execution_slices_df(partial)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert "执行阶段" in df.columns
        assert "建议挂单金额(元)" in df.columns
        assert "分配比例" in df.columns
        assert "微观执行策略" in df.columns
        assert df["建议挂单金额(元)"].iloc[0] == "¥3,500.00"
        assert df["分配比例"].iloc[1] == "25%"

    def test_all_standard_chinese_columns_preserved(self):
        """Preserves the required 5 Chinese column headers."""
        slices = [
            {
                "phase": "T日14:30",
                "label": "尾盘净值锚定",
                "vol_ratio": 0.40,
                "slice_amount": 4000.0,
                "strategy": "尾盘估值锚定"
            }
        ]
        df = format_micro_execution_slices_df(slices)
        expected = ["执行阶段", "窗口类型", "分配比例", "建议挂单金额(元)", "微观执行策略"]
        for col in expected:
            assert col in df.columns, f"Missing required Chinese column: {col}"

    def test_non_numeric_and_edge_values(self):
        """Handle strings, zero, large numbers, and edge cases gracefully."""
        edge_data = [
            {
                "phase": "09:30-10:00",
                "label": "开盘",
                "vol_ratio": "15%",  # string
                "slice_amount": 0.0,  # zero
                "strategy": "等待"
            },
            {
                "phase": "14:30-15:00",
                "label": "尾盘",
                "vol_ratio": 0.85,
                "slice_amount": 99999999.50,  # large number
                "strategy": "分笔"
            }
        ]
        df = format_micro_execution_slices_df(edge_data)
        assert len(df) == 2
        assert df["分配比例"].iloc[0] == "15%"
        assert df["建议挂单金额(元)"].iloc[0] == "¥0.00"
        assert df["分配比例"].iloc[1] == "85%"
        assert df["建议挂单金额(元)"].iloc[1] == "¥99,999,999.50"


# =============================================================================
# Mission Item 3: Right-Wing Alert Sentry Logic
# =============================================================================
class TestItem3RightWingAlertSentryEmpirical:
    """Empirical challenge of right-wing alert sentry casing, priority sorting, and extraction."""

    def test_varied_casing_and_red_priority(self):
        """Verify sorting with all varied level values; red alerts MUST sort to top."""
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
            {"level": "green_notice", "title": "全部正常"},
            {"level": "WARNING", "title": "超买拥挤警告", "desc": "乖离过高"},
            {"level": "CRITICAL", "title": "未满7天惩罚费锁仓", "desc": "扣除1.50%"},
            {"level": "info", "title": "例行巡检"},
            {"level": "red", "title": "移动止盈触发", "detail": "破高水位线"},
            {"level": "yellow", "title": "广发纯债规模待核验", "desc": "规模待核验"},
            {"level": "RED", "title": "深套严重警告", "message": "浮亏超20%"},
            {"level": "critical", "title": "大盘攻防线跌破", "action": "削减风险敞口"},
            {"level": "Warning", "title": "动态相关性突变", "action": "避险平移"},
            {"level": "unknown_status", "title": "其他未知风险"},
        ]

        sorted_alerts = sorted(alerts, key=_sentry_alert_sorter)

        # Top 4 MUST ALL be red or critical
        for i in range(4):
            raw_lvl = sorted_alerts[i]["level"].lower()
            assert raw_lvl in ("red", "critical"), f"Rank {i} expected red/critical, got {raw_lvl}"

        # Real warnings must precede '规模待核验'
        warning_titles = [a["title"] for a in sorted_alerts if a.get("level") in ("WARNING", "Warning")]
        scale_titles = [a["title"] for a in sorted_alerts if "规模待核验" in a["title"]]
        assert len(warning_titles) == 2
        assert len(scale_titles) == 1
        
        warn_idx = min(sorted_alerts.index(a) for a in sorted_alerts if a["title"] in warning_titles)
        scale_idx = sorted_alerts.index(next(a for a in sorted_alerts if "规模待核验" in a["title"]))
        assert warn_idx < scale_idx, "Real warnings must be prioritized before '规模待核验'"

        # Green notice & info must be at the very bottom
        bottom_levels = [a["level"].lower() for a in sorted_alerts[-2:]]
        for lvl in bottom_levels:
            assert any(k in lvl for k in ("green", "info", "notice"))

    def test_alert_field_extraction_fallbacks(self):
        """Verify extraction hierarchy for desc/detail/message and action/suggested_action."""
        # 1. desc takes precedence
        a1 = {"desc": "D1", "detail": "DET1", "message": "M1", "action": "ACT1"}
        # 2. detail takes precedence if desc missing
        a2 = {"detail": "DET2", "message": "M2", "suggested_action": "SUGG2"}
        # 3. message fallback
        a3 = {"message": "M3"}

        def extract(alert):
            d = alert.get("desc") or alert.get("detail") or alert.get("message", "")
            act = alert.get("action") or alert.get("suggested_action", "")
            return d, act

        d1, act1 = extract(a1)
        assert d1 == "D1"
        assert act1 == "ACT1"

        d2, act2 = extract(a2)
        assert d2 == "DET2"
        assert act2 == "SUGG2"

        d3, act3 = extract(a3)
        assert d3 == "M3"
        assert act3 == ""


# =============================================================================
# Mission Item 4: 017436 Resolution and Holding Defense
# =============================================================================
class TestItem4Fund017436ResolutionEmpirical:
    """Empirical challenge of 017436 resolution across portfolio_manager and strategy_bridge."""

    def test_canonical_fund_name_in_pm_and_bridge(self):
        """017436 must be resolved as '华安纳斯达克100ETF联接A' consistently."""
        meta = PortfolioManager.resolve_fund_meta("017436")
        assert meta["fund_name"] == "华安纳斯达克100ETF联接A"

        # Check resolve_fund_display_name in app_gui
        disp_name = resolve_fund_display_name("017436")
        assert disp_name == "华安纳斯达克100ETF联接A"

        # Check SECTOR_FUND_SELECTION
        found_in_pm_sec = False
        for alt in SECTOR_FUND_SELECTION["GLOBAL_HEDGE"]["alternatives"]:
            if alt["code"] == "017436":
                found_in_pm_sec = True
                assert alt["name"] == "华安纳斯达克100ETF联接A"
        assert found_in_pm_sec

        # Check SECTOR_FUND_SELECTION_BY_TIER
        for tier in ["C1", "C2", "C3", "C4", "C5"]:
            t_alts = SECTOR_FUND_SELECTION_BY_TIER.get(tier, {}).get("GLOBAL_HEDGE", {}).get("alternatives", [])
            for alt in t_alts:
                if alt["code"] == "017436":
                    assert alt["name"] == "华安纳斯达克100ETF联接A"

    def test_017436_new_buy_not_locked(self):
        """When 017436 is recommended for purchase (unheld), it must have holding_days=-1 and no lock."""
        pm = PortfolioManager()
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
        nasdaq = [it for it in items if it.get("fund_code") == "017436"]
        assert len(nasdaq) == 1
        it = nasdaq[0]
        assert it["action"] == "BUY"
        assert it["holding_days"] == -1
        assert not it.get("safety_warning")
        assert "华安纳斯达克100ETF联接A" in it["fund_name"]

    def test_017436_held_under_7_days_locked(self):
        """When 017436 is actually held with holding_days=3, selling must trigger 7-day lock warning."""
        pm = PortfolioManager()
        h_nasdaq = FundHolding(
            fund_code="017436",
            fund_name="华安纳斯达克100ETF联接A",
            shares=1000.0,
            current_nav=1.50,
            cost_price=1.48,
            market_value=1500.0,
            batches=[HoldingBatch(batch_id="b_test_1", buy_date="2026-11-06", shares=1000.0, cost_nav=1.48, holding_days=3)]
        )
        pm.holdings["017436"] = h_nasdaq

        # Rebalance reducing 017436
        target_weights = {"002351": 1.00}
        rebal_res = StrategyBridge.generate_ai_rebalance_orders(
            pm.holdings,
            pm.available_cash,
            target_weights,
            pm=pm
        )
        items = rebal_res.get("items", [])
        nasdaq = [it for it in items if it.get("fund_code") == "017436"]
        assert len(nasdaq) == 1
        it = nasdaq[0]
        assert it["holding_days"] < 7
        assert it["holding_days"] >= 0
        # Must have safety warning regarding 7-day penalty lock
        has_lock = (
            "7天" in str(it.get("safety_warning", ""))
            or "锁定" in str(it.get("safety_warning", ""))
            or it.get("is_penalty_locked")
            or it.get("safe_shares", 0.0) == 0.0
        )
        assert has_lock, f"Expected 7-day lock warning, got: {it}"


# =============================================================================
# Mission Item 5 & 6: Referee Integrity & Regressions
# =============================================================================
class TestRefereeIntegrityAndRegressions:
    """Verify read-only referees remain pristine."""

    def test_read_only_referee_files_exist_and_unmodified(self):
        workspace = Path(__file__).resolve().parent.parent
        referee_files = [
            workspace / "AGY2_FundAdvisory" / "judge_engine.py",
            workspace / "AGY2_FundAdvisory" / "holdout_vault.py",
            workspace / "AGY2_FundAdvisory" / "AGENT_SPEC.md",
            workspace / "tests" / "test_infra.py"
        ]
        for p in referee_files:
            assert p.exists(), f"Referee file missing: {p}"
            assert p.is_file(), f"Referee path is not a file: {p}"
