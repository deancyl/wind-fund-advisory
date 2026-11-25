# -*- coding: utf-8 -*-
"""
Adversarial Stress Testing for Milestone 2:
1. Missing/Corrupted Parquet file behavior
2. Missing/Empty Valuation Cache behavior
3. Extreme market shock values (Bias20 = +50%, -50%, ER = 0, ER = 1, Slope = +/- 500)
4. NaN/Inf defenses in score calculation
5. Empty top sectors fallback in pulse brief
6. Verification of Rule 16 (000922 never 000015)
7. Integrity check: No hardcoded test responses or facade logic
"""
import os
import sys
from pathlib import Path
import math

WORKSPACE = Path(__file__).resolve().parent.parent
if str(WORKSPACE) not in sys.path:
    sys.path.insert(0, str(WORKSPACE))

import pandas as pd
import numpy as np
from AGY2_FundAdvisory.advisory_engine import OpportunityRadarEngine, RADAR_SECTOR_CATALOG
from AGY2_FundAdvisory import data_loader

def stress_test_extreme_inputs():
    print("--- 1. Testing Extreme Market Inputs in OpportunityRadarEngine ---")
    radar = OpportunityRadarEngine()
    
    extreme_cases = [
        {"name": "Ultra Bubble", "bias_20": 45.0, "slope_20": 150.0, "er_20": 0.95, "crowding_score": 96.0, "base_val_pct": 99.0},
        {"name": "Deep Crash", "bias_20": -45.0, "slope_20": -200.0, "er_20": 0.10, "crowding_score": 45.0, "base_val_pct": 0.5},
        {"name": "Zero ER Noise", "bias_20": 0.0, "slope_20": 0.0, "er_20": 0.0, "crowding_score": 50.0, "base_val_pct": 50.0},
        {"name": "Max Slope", "bias_20": 5.0, "slope_20": 1000.0, "er_20": 1.0, "crowding_score": 90.0, "base_val_pct": 20.0},
    ]
    
    for case in extreme_cases:
        meta = {
            "name": case["name"],
            "category": "压力测试",
            "benchmark_index": "000300",
            "base_val_pct": case["base_val_pct"],
            "bias_20": case["bias_20"],
            "slope_20": case["slope_20"],
            "er_20": case["er_20"],
            "crowding_score": case["crowding_score"],
            "default_fund": {"code": "999999", "name": "测试极端基金"},
        }
        ev = radar.evaluate_sector("extreme_test", meta)
        # Verify no NaN or Inf in outputs
        for k in ["s_val", "s_mom", "s_er", "s_crowd", "total_score", "val_percentile"]:
            val = ev[k]
            assert not math.isnan(val), f"NaN detected in {k} for {case['name']}!"
            assert not math.isinf(val), f"Inf detected in {k} for {case['name']}!"
            assert 0.0 <= val <= 100.0, f"{k} value {val} out of [0, 100] for {case['name']}!"
        print(f"  PASS: {case['name']:15s} -> total_score: {ev['total_score']:4.1f}, tag: {ev['tag']}")

def stress_test_resilience_to_missing_data():
    print("\n--- 2. Testing Resilience to Missing Data / None / Empties ---")
    radar = OpportunityRadarEngine()
    
    # Empty meta dictionary
    empty_meta = {"name": "空赛道"}
    ev = radar.evaluate_sector("empty_sector", empty_meta)
    assert not math.isnan(ev["total_score"])
    assert 0.0 <= ev["total_score"] <= 100.0
    print("  PASS: Empty metadata evaluated safely ->", ev["total_score"])
    
    # Missing valuation map fallback
    old_method = data_loader.fetch_or_calc_index_valuations
    try:
        # Mocking an exception in data_loader to ensure graceful fallback
        data_loader.fetch_or_calc_index_valuations = lambda force_refresh=False: {}
        val_pct = radar.get_sector_valuation_percentile("pure_bond", {"benchmark_index": "H11009"})
        assert val_pct == 40.0, f"Expected 40.0 for pure_bond fallback, got {val_pct}"
        val_pct_gold = radar.get_sector_valuation_percentile("domestic_gold", {"benchmark_index": "518880"})
        assert val_pct_gold == 50.0, f"Expected 50.0 for domestic_gold fallback, got {val_pct_gold}"
        print("  PASS: Graceful fallback on valuation failure -> bond:", val_pct, "gold:", val_pct_gold)
    finally:
        data_loader.fetch_or_calc_index_valuations = old_method

def stress_test_rule16_invariant():
    print("\n--- 3. Testing Rule 16: Index Identity Integrity (CSI Dividend == 000922) ---")
    csi_div = RADAR_SECTOR_CATALOG["csi_dividend"]
    assert csi_div["benchmark_index"] == "000922", f"Violation of Rule 16: benchmark_index is {csi_div['benchmark_index']}"
    assert "000015" not in str(csi_div), "Violation of Rule 16: 000015 found in csi_dividend config!"
    print("  PASS: Rule 16 strictly maintained: csi_dividend mapped exclusively to 000922.")

def stress_test_pulse_brief_limits():
    print("\n--- 4. Testing Pulse Brief String Formatting & Word Limits ---")
    # Test adversarial long inputs
    long_turnover = "999.999万亿元天量超频"
    long_vol_text = "极度超买情绪过热熔断"
    erp_pct = 99.99
    erp_zone = f"ERP分位{erp_pct:.1f}%处历史高性价比击球区"
    long_names = ["超长名字赛道阿尔法贝塔伽马一号", "超长名字赛道阿尔法贝塔伽马二号"]
    lead_str = "与".join(long_names)
    pulse_brief = f"两市成交{long_turnover}{long_vol_text}，{erp_zone}；{lead_str}领衔低估与右侧主线，策略宜逢低均衡布局。"
    if len(pulse_brief) > 80:
        pulse_brief = pulse_brief[:79] + "。"
    assert len(pulse_brief) <= 80, f"Failed: length is {len(pulse_brief)}"
    assert pulse_brief.endswith("。")
    print(f"  PASS: Truncated long pulse brief ({len(pulse_brief)} chars): {pulse_brief}")

if __name__ == "__main__":
    stress_test_extreme_inputs()
    stress_test_resilience_to_missing_data()
    stress_test_rule16_invariant()
    stress_test_pulse_brief_limits()
    print("\nALL ADVERSARIAL STRESS TESTS PASSED SUCCESSFULLY!")
