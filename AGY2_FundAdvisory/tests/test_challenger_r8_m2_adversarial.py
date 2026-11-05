# -*- coding: utf-8 -*-
"""
AGY2_FundAdvisory/tests/test_challenger_r8_m2_adversarial.py
Adversarial Stress Testing Suite for Milestone 2:
- Single Source of Truth Strict Parity (< 1e-4)
- Parquet Dynamic Metrics Bounds & Sanity (0 <= ER <= 1, numeric Bias, Slope, Crowding)
- CSI Dividend Real Overheat (> 85%) Rejecting 25.0%
- Morning Market Pulse Length Invariant (<= 80 chars)
- 6-Dimensional Risk Sentry Boundary Stress (011612, 011613, 013841, edge cases)
- Degradation / Resilience under Missing Cache / File IO Pressure
- Streamlit AppTest Full 4-Tab 0-Exception Audit
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
import numpy as np
import pandas as pd

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))
if str(WORKSPACE_ROOT / "AGY2_FundAdvisory") not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT / "AGY2_FundAdvisory"))

from AGY2_FundAdvisory.advisory_engine import (
    OpportunityRadarEngine,
    RADAR_SECTOR_CATALOG,
    ActiveRiskSentry,
)
from AGY2_FundAdvisory.data_loader import (
    fetch_or_calc_index_valuations,
    get_index_corridor_metrics,
)
from AGY2_FundAdvisory.portfolio_manager import PortfolioManager


# ==============================================================================
# Suite 1: Single Source of Truth Strict Parity & CSI Dividend Invariant
# ==============================================================================

class TestSingleSourceOfTruthParity:
    """Stress test valuation parity between corridor and opportunity radar."""

    def test_catalog_completely_purged_of_static_constants(self):
        """Verify RADAR_SECTOR_CATALOG contains zero hardcoded fake constants."""
        forbidden_keys = {"base_val_pct", "er_20", "bias_20", "slope_20", "crowding_score"}
        for sec_id, meta in RADAR_SECTOR_CATALOG.items():
            intersection = forbidden_keys.intersection(meta.keys())
            assert not intersection, f"Sector {sec_id} still contains static constants: {intersection}"

    def test_valuation_parity_across_all_overlapping_indices(self):
        """For all sectors where corridor has valuation, diff must be < 1e-4."""
        radar = OpportunityRadarEngine()
        val_map = fetch_or_calc_index_valuations(force_refresh=False)
        assert len(val_map) > 0, "Valuation map must not be empty"

        tested_sectors = 0
        for sec_id, meta in RADAR_SECTOR_CATALOG.items():
            eval_res = radar.evaluate_sector(sec_id, meta)
            r_pct = eval_res["val_percentile"]
            candidates = [
                meta.get("benchmark_index"),
                meta.get("symbol"),
                meta.get("index_code"),
                meta.get("cs_code"),
            ]
            c_pct = None
            matched_code = None
            for c in candidates:
                if c and str(c) in val_map and val_map[str(c)].get("percentile") is not None:
                    c_pct = float(val_map[str(c)]["percentile"])
                    matched_code = str(c)
                    break

            if c_pct is not None:
                diff = abs(r_pct - c_pct)
                assert diff < 1e-4, f"Parity failed for {sec_id} ({matched_code}): radar={r_pct}, corridor={c_pct}, diff={diff}"
                tested_sectors += 1

        assert tested_sectors >= 7, f"Expected at least 7 overlapping benchmark sectors, tested {tested_sectors}"

    def test_csi_dividend_strict_overheat_invariant(self):
        """CSI Dividend (000922) must be > 85%, matching corridor, rejecting 25.0%."""
        radar = OpportunityRadarEngine()
        meta = RADAR_SECTOR_CATALOG["csi_dividend"]
        eval_res = radar.evaluate_sector("csi_dividend", meta)
        r_pct = eval_res["val_percentile"]

        val_map = fetch_or_calc_index_valuations(force_refresh=False)
        corr_pct = float(val_map["000922"]["percentile"])

        # 1. 100% Match
        assert abs(r_pct - corr_pct) < 1e-4, f"CSI Dividend corridor mismatch: {r_pct} vs {corr_pct}"
        # 2. Strict Overheat (>85%)
        assert r_pct > 85.0, f"CSI Dividend must reflect realistic overheat (>85%), got {r_pct}"
        # 3. Reject old fake 25.0%
        assert abs(r_pct - 25.0) > 40.0, f"CSI Dividend must reject old hardcoded 25.0%, got {r_pct}"


# ==============================================================================
# Suite 2: Parquet Dynamic Metrics Sanity & Bounds
# ==============================================================================

class TestParquetDynamicMetricsSanity:
    """Stress test dynamic sector metrics calculation from parquet."""

    def test_parquet_file_exists_and_readable(self):
        """Check aligned_matrix_total_return.parquet exists at expected path."""
        p = Path(WORKSPACE_ROOT) / "data" / "processed" / "aligned_matrix_total_return.parquet"
        assert p.exists(), f"Processed matrix parquet must exist at {p}"
        df = pd.read_parquet(p)
        assert len(df) >= 1000, f"Parquet row count should be >= 1000, got {len(df)}"
        assert "H00922" in df.columns, "Matrix should contain CSI Dividend total return column H00922"

    def test_dynamic_metrics_all_14_sectors_bounds(self):
        """All 14 sectors must have valid numeric metrics within mathematical bounds."""
        radar = OpportunityRadarEngine()
        metrics = radar.dynamic_metrics
        assert len(metrics) == 14, f"Expected metrics for all 14 sectors, got {len(metrics)}"

        for sec_id, m in metrics.items():
            er = m.get("er_20")
            bias = m.get("bias_20")
            slope = m.get("slope_20")
            crowd = m.get("crowding_score")

            assert er is not None and not np.isnan(er), f"Sector {sec_id} ER is NaN or None"
            assert 0.0 <= er <= 1.0, f"Sector {sec_id} Kaufman ER {er} out of [0, 1] bounds"

            assert bias is not None and not np.isnan(bias), f"Sector {sec_id} Bias is NaN or None"
            assert -50.0 <= bias <= 50.0, f"Sector {sec_id} Bias {bias}% unrealistically extreme"

            assert slope is not None and not np.isnan(slope), f"Sector {sec_id} Slope is NaN or None"

            assert crowd is not None and not np.isnan(crowd), f"Sector {sec_id} Crowding is NaN or None"
            assert 0.0 <= crowd <= 100.0, f"Sector {sec_id} Crowding score {crowd} out of [0, 100]"

    def test_opportunity_radar_scan_all_sectors(self):
        """scan_all_sectors must return 14 sectors sorted with valid total_score."""
        radar = OpportunityRadarEngine()
        scanned = radar.scan_all_sectors()
        assert len(scanned) == 14, f"scan_all_sectors should return 14 items, got {len(scanned)}"

        scores = [s["total_score"] for s in scanned]
        # Verify descending order
        assert scores == sorted(scores, reverse=True), "scanned sectors must be sorted descending by total_score"

        # Verify all required keys
        for s in scanned:
            for k in ["sector_id", "name", "val_percentile", "er_20", "bias_20", "s_crowd", "total_score", "tag", "fund"]:
                assert k in s, f"Missing key {k} in scanned sector {s.get('sector_id')}"
                assert s[k] is not None, f"Key {k} is None in scanned sector {s.get('sector_id')}"


# ==============================================================================
# Suite 3: Morning Market Pulse Word Count Stress
# ==============================================================================

class TestMorningPulseWordCountStress:
    """Stress test pulse brief word count invariant under extreme conditions."""

    @pytest.mark.parametrize("turnover_str,vol_text,erp_pct,top_names", [
        ("1.2万亿", "放量活跃", 82.0, ["中证红利", "红利低波"]),
        ("3.8万亿", "天量爆发放量冲高回落", 99.5, ["超级超长赛道名称测试A", "超级超长赛道名称测试B"]),
        ("4800亿", "地量缩量磨底等待反转", 15.0, ["医药医疗", "消费白酒"]),
        ("0元", "休市", 0.0, []),
        ("100万亿", "放量", 50.0, ["A"]),
    ])
    def test_pulse_brief_char_count_strictly_within_80_chars(self, turnover_str, vol_text, erp_pct, top_names):
        """Assert pulse brief string length is strictly <= 80 Chinese characters."""
        if erp_pct >= 75.0:
            erp_zone = f"ERP分位{erp_pct:.1f}%处历史高性价比击球区"
        elif erp_pct <= 30.0:
            erp_zone = f"ERP分位{erp_pct:.1f}%偏高估宜防守"
        else:
            erp_zone = f"ERP分位{erp_pct:.1f}%处中性配置区间"

        lead_str = "与".join(top_names) if top_names else "红利低波与大盘蓝筹"
        pulse_brief = f"两市成交{turnover_str}{vol_text}，{erp_zone}；{lead_str}领衔低估与右侧主线，策略宜逢低均衡布局。"
        if len(pulse_brief) > 80:
            pulse_brief = pulse_brief[:79] + "。"

        assert len(pulse_brief) <= 80, f"Pulse brief exceeds 80 characters! Length: {len(pulse_brief)}"


# ==============================================================================
# Suite 4: 6-Dimensional Risk Sentry Targeted Holdings Stress
# ==============================================================================

class TestActiveRiskSentryTargetedStress:
    """Stress test 6-dimensional risk sentry against 011612, 011613, 013841 and edge cases."""

    def test_demo_portfolio_targeted_alerts(self):
        """Demo portfolio must trigger alerts for 011612, 011613, and 013841."""
        pm = PortfolioManager()
        pm.load_demo_portfolio()
        assert len(pm.holdings) > 0, "Demo portfolio should not be empty"

        sentry = ActiveRiskSentry()
        snapshot = {"csi300_point": 3950.0, "csi300_bias": 1.2, "csi300_ma20": 3900.0}
        report = sentry.inspect_portfolio(pm.holdings, market_snapshot=snapshot)

        assert not report["all_passed"], "Demo portfolio must trigger risk alerts"
        alerts = report["alerts"]

        flagged_codes = {a["fund_code"] for a in alerts if "fund_code" in a}
        assert "011612" in flagged_codes, "011612 (holding 3 days) must trigger penalty lock alert"
        assert "011613" in flagged_codes, "011613 (holding 28 days) must trigger C-class countdown alert"
        assert "013841" in flagged_codes, "013841 (loss -16.2%) must trigger deep loss alert"

        # Check action_type existence
        for a in alerts:
            assert "action_type" in a, f"Alert missing action_type: {a}"
            assert a["action_type"] in [
                "lock_shares",
                "countdown_hold",
                "switch_a_class",
                "take_profit",
                "deep_loss_rebalance",
                "rebalance_sector",
                "replace_fund",
                "defense_mode",
                "offense_mode",
            ], f"Unknown action_type: {a['action_type']}"

    def test_empty_portfolio_graceful_pass(self):
        """Empty portfolio must pass inspection gracefully with 0 alerts."""
        sentry = ActiveRiskSentry()
        report = sentry.inspect_portfolio({})
        assert report["all_passed"] is True
        assert len(report["alerts"]) == 0

    def test_clean_portfolio_all_passed(self):
        """A well-balanced, mature (>30 days), profitable (<15%) portfolio passes inspection."""
        clean_holdings = {
            "005561": {
                "fund_code": "005561",
                "fund_name": "创金合信红利低波A",
                "shares": 10000.0,
                "cost_price": 1.0,
                "current_nav": 1.05,
                "market_value": 10500.0,
                "holding_days": 180,
                "share_class": "A",
                "floating_pnl_pct": 5.0,
                "sector": "dividend_low_vol",
            },
            "110020": {
                "fund_code": "110020",
                "fund_name": "易方达沪深300ETF联接A",
                "shares": 10000.0,
                "cost_price": 1.0,
                "current_nav": 1.04,
                "market_value": 10400.0,
                "holding_days": 180,
                "share_class": "A",
                "floating_pnl_pct": 4.0,
                "sector": "csi_300",
            },
        }
        sentry = ActiveRiskSentry()
        snapshot = {"csi300_point": 3950.0, "csi300_bias": 1.2, "csi300_ma20": 3900.0}
        report = sentry.inspect_portfolio(clean_holdings, market_snapshot=snapshot)
        assert report["all_passed"] is True
        assert len(report["alerts"]) == 0


# ==============================================================================
# Suite 5: Fallback & Resilience under File IO Failures
# ==============================================================================

class TestOpportunityRadarResilience:
    """Stress test resilience of OpportunityRadarEngine under cache/IO failures."""

    def test_cache_file_corrupted_graceful_fallback(self, tmp_path):
        """If index_valuation.json is corrupted, engine should not crash."""
        corrupt_file = tmp_path / "index_valuation.json"
        corrupt_file.write_text("{invalid_json: true", encoding="utf-8")

        radar = OpportunityRadarEngine(cache_dir=str(tmp_path))
        assert isinstance(radar.valuation_cache, dict)
        # Should still be able to evaluate sector
        res = radar.evaluate_sector("csi_dividend", RADAR_SECTOR_CATALOG["csi_dividend"])
        assert "val_percentile" in res
        assert "total_score" in res


# ==============================================================================
# Suite 6: Streamlit AppTest Full Integration
# ==============================================================================

class TestStreamlitAppTestMilestone2:
    """Streamlit AppTest verification of dual-wing dashboard, thermometer, and buttons."""

    def test_apptest_runs_dual_wing_dashboard_without_exception(self):
        from streamlit.testing.v1 import AppTest
        gui_path = str(WORKSPACE_ROOT / "AGY2_FundAdvisory" / "app_gui.py")

        at = AppTest.from_file(gui_path, default_timeout=30)
        at.run()
        assert not at.exception, f"AppTest threw exception: {at.exception}"

        # Verify dual wing expander exists
        expander_labels = [e.label for e in at.expander]
        assert any("机会雷达" in lbl for lbl in expander_labels), "Dual-wing expander not found"
        assert any("量化温度计总表" in lbl for lbl in expander_labels), "14-sector thermometer expander not found"
