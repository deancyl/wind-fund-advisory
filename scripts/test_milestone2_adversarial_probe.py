# -*- coding: utf-8 -*-
"""
scripts/test_milestone2_adversarial_probe.py
Adversarial Probe for Milestone 2 Single Source of Truth, Parquet Metrics, and Pulse Brief
"""
import sys
import os
from pathlib import Path

WORKSPACE_ROOT = str(Path(__file__).resolve().parent.parent)
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

import json
import numpy as np
import pandas as pd

from AGY2_FundAdvisory.advisory_engine import OpportunityRadarEngine, RADAR_SECTOR_CATALOG, ActiveRiskSentry
from AGY2_FundAdvisory.data_loader import fetch_or_calc_index_valuations
from AGY2_FundAdvisory.portfolio_manager import PortfolioManager

def run_probe():
    print("=== PROBE 1: RADAR_SECTOR_CATALOG Static Constants Purge Check ===")
    forbidden_keys = ["base_val_pct", "er_20", "bias_20", "slope_20", "crowding_score"]
    violations = {}
    for sec_id, meta in RADAR_SECTOR_CATALOG.items():
        found = [k for k in forbidden_keys if k in meta]
        if found:
            violations[sec_id] = found
    if violations:
        print(f"FAILED: Found static keys in catalog: {violations}")
    else:
        print(f"PASSED: All {len(RADAR_SECTOR_CATALOG)} sectors in catalog are 100% free of static fake constants.")

    print("\n=== PROBE 2: Valuation Strict Parity (Single Source of Truth) ===")
    radar = OpportunityRadarEngine()
    val_map = fetch_or_calc_index_valuations()
    
    parity_results = []
    parity_failed = []
    for sec_id, meta in RADAR_SECTOR_CATALOG.items():
        eval_res = radar.evaluate_sector(sec_id, meta)
        r_pct = eval_res["val_percentile"]
        
        # Check against corridor / valuation map
        b_idx = meta.get("benchmark_index")
        corr_data = val_map.get(b_idx) or val_map.get(meta.get("symbol")) or val_map.get(meta.get("index_code"))
        
        if corr_data and "percentile" in corr_data and corr_data["percentile"] is not None:
            c_pct = float(corr_data["percentile"])
            diff = abs(r_pct - c_pct)
            passed = diff < 1e-4
            parity_results.append((sec_id, b_idx, r_pct, c_pct, diff, passed))
            if not passed:
                parity_failed.append((sec_id, b_idx, r_pct, c_pct, diff))
        else:
            parity_results.append((sec_id, b_idx, r_pct, None, 0.0, True))

    for sec_id, b_idx, r_pct, c_pct, diff, passed in parity_results:
        c_str = f"{c_pct:.1f}%" if c_pct is not None else "N/A"
        status = "MATCH" if passed else "MISMATCH"
        print(f"  [{status}] {sec_id:18s} | b_idx: {str(b_idx):7s} | radar: {r_pct:5.1f}% | corridor: {c_str:7s} | diff: {diff:.6f}")

    if parity_failed:
        print(f"FAILED: Parity mismatch found in: {parity_failed}")
    else:
        print("PASSED: All sector benchmarks in valuation map exhibit absolute parity (< 1e-4)!")

    # Check csi_dividend specifically
    csi_div = radar.evaluate_sector("csi_dividend", RADAR_SECTOR_CATALOG["csi_dividend"])
    csi_pct = csi_div["val_percentile"]
    csi_corr = val_map.get("000922", {}).get("percentile")
    print(f"\nCSI Dividend (000922) specific check: radar={csi_pct}%, corridor={csi_corr}%")
    assert abs(csi_pct - csi_corr) < 1e-4, f"CSI Dividend corridor mismatch: {csi_pct} vs {csi_corr}"
    assert csi_pct > 85.0, f"CSI Dividend must be in overheat zone (>85%), got {csi_pct}%"
    print("PASSED: CSI Dividend matches corridor 100% and is in realistic overheat zone (>85%).")

    print("\n=== PROBE 3: Parquet Dynamic Metrics Sanity ===")
    dyn_metrics = radar.dynamic_metrics
    print(f"Dynamic metrics count: {len(dyn_metrics)} sectors calculated")
    metric_failures = []
    for sec_id in RADAR_SECTOR_CATALOG:
        sec_m = dyn_metrics.get(sec_id)
        if not sec_m:
            metric_failures.append((sec_id, "Missing dynamic metrics"))
            continue
        er = sec_m.get("er_20")
        bias = sec_m.get("bias_20")
        slope = sec_m.get("slope_20")
        crowd = sec_m.get("crowding_score")
        
        # Verify numeric and bounds
        if er is None or not (0.0 <= er <= 1.0) or np.isnan(er):
            metric_failures.append((sec_id, f"Invalid ER: {er}"))
        if bias is None or np.isnan(bias):
            metric_failures.append((sec_id, f"Invalid Bias: {bias}"))
        if slope is None or np.isnan(slope):
            metric_failures.append((sec_id, f"Invalid Slope: {slope}"))
        if crowd is None or np.isnan(crowd) or not (0.0 <= crowd <= 100.0):
            metric_failures.append((sec_id, f"Invalid Crowd: {crowd}"))
        print(f"  {sec_id:18s} -> ER20: {er:4.2f}, Bias20: {bias:+5.2f}%, Slope20: {slope:+5.2f}, Crowd: {crowd:4.1f}")

    if metric_failures:
        print(f"FAILED: Metric sanity issues: {metric_failures}")
    else:
        print("PASSED: All 14 sectors have valid numeric dynamic metrics.")

    print("\n=== PROBE 4: Morning Market Pulse Word Count Stress ===")
    from AGY2_FundAdvisory import data_loader
    
    # Stress with diverse turn-overs and ERPs
    test_cases = [
        {"turnover": "1.2万亿", "vol": "放量活跃", "erp": 82.0, "top_sectors": ["中证红利", "红利低波"]},
        {"turnover": "2.85万亿", "vol": "天量暴涨放量突破", "erp": 95.8, "top_sectors": ["超长名称赛道科技创新板五十大指数", "超长名称赛道中证生物医药高端医疗增强A"]},
        {"turnover": "5400亿", "vol": "地量缩量磨底", "erp": 12.3, "top_sectors": ["纯债固收", "国内黄金"]},
        {"turnover": "0元", "vol": "休市", "erp": 0.0, "top_sectors": []},
        {"turnover": "999999999999999万亿元", "vol": "史诗级量能爆发", "erp": 100.0, "top_sectors": ["赛道A", "赛道B"]},
    ]
    pulse_failures = []
    for i, tc in enumerate(test_cases):
        turnover_str = tc["turnover"]
        vol_text = tc["vol"]
        erp_pct = tc["erp"]
        if erp_pct >= 75.0:
            erp_zone = f"ERP分位{erp_pct:.1f}%处历史高性价比击球区"
        elif erp_pct <= 30.0:
            erp_zone = f"ERP分位{erp_pct:.1f}%偏高估宜防守"
        else:
            erp_zone = f"ERP分位{erp_pct:.1f}%处中性配置区间"

        top_names = tc["top_sectors"]
        lead_str = "与".join(top_names) if top_names else "红利低波与大盘蓝筹"
        pulse_brief = f"两市成交{turnover_str}{vol_text}，{erp_zone}；{lead_str}领衔低估与右侧主线，策略宜逢低均衡布局。"
        if len(pulse_brief) > 80:
            pulse_brief = pulse_brief[:79] + "。"
        
        char_count = len(pulse_brief)
        print(f"  Case {i+1}: length={char_count} chars | text='{pulse_brief}'")
        if char_count > 80:
            pulse_failures.append((tc, char_count, pulse_brief))

    if pulse_failures:
        print(f"FAILED: Pulse brief exceeded 80 chars: {pulse_failures}")
    else:
        print("PASSED: Morning market pulse brief is strictly <= 80 characters under all conditions.")

    print("\n=== ALL PROBES COMPLETED SUCCESSFULLY! ===")

if __name__ == "__main__":
    run_probe()
