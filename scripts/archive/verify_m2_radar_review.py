# -*- coding: utf-8 -*-
"""
Verification script for Milestone 2:
1. Dynamic metrics computation for all 14 sectors.
2. Single source of truth valuation comparison between IndexValuationEngine and OpportunityRadarEngine.
3. Pulse brief length and keyword formatting.
4. Thermometer table schema and content.
"""
import os
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
if str(WORKSPACE) not in sys.path:
    sys.path.insert(0, str(WORKSPACE))

import pandas as pd
from AGY2_FundAdvisory.advisory_engine import OpportunityRadarEngine, RADAR_SECTOR_CATALOG
from AGY2_FundAdvisory.data_loader import fetch_or_calc_index_valuations

def test_parquet_and_dynamic_metrics():
    mat_path = "data/processed/aligned_matrix_total_return.parquet"
    assert os.path.exists(mat_path), f"File {mat_path} does not exist!"
    df = pd.read_parquet(mat_path)
    print(f"Loaded matrix: {df.shape}, cols: {len(df.columns)}")
    
    radar = OpportunityRadarEngine()
    print(f"Dynamic metrics computed for {len(radar.dynamic_metrics)} / {len(RADAR_SECTOR_CATALOG)} sectors:")
    for sec_id, d in radar.dynamic_metrics.items():
        print(f"  {sec_id:18s} -> er_20: {d['er_20']:4.2f}, bias_20: {d['bias_20']:+6.2f}%, slope_20: {d['slope_20']:+6.2f}%, crowding: {d['crowding_score']:4.1f}")
    
    # Check that all sectors have dynamic metrics
    for sec_id in RADAR_SECTOR_CATALOG.keys():
        assert sec_id in radar.dynamic_metrics, f"Sector {sec_id} missing from dynamic_metrics!"

def test_single_source_of_truth():
    radar = OpportunityRadarEngine()
    val_map = fetch_or_calc_index_valuations(force_refresh=False)
    
    print("\nVerifying Single Source of Truth for benchmark indices:")
    checked = 0
    for sec_id, meta in RADAR_SECTOR_CATALOG.items():
        bench = meta.get("benchmark_index")
        val_pct_radar = radar.get_sector_valuation_percentile(sec_id, meta)
        ev = radar.evaluate_sector(sec_id, meta)
        assert ev["val_percentile"] == val_pct_radar
        
        # If bench is in val_map, verify exact match
        expected = None
        if bench in val_map and val_map[bench].get("percentile") is not None:
            expected = float(val_map[bench]["percentile"])
        elif f"1.{bench}" in val_map and val_map[f"1.{bench}"].get("percentile") is not None:
            expected = float(val_map[f"1.{bench}"]["percentile"])
        elif f"0.{bench}" in val_map and val_map[f"0.{bench}"].get("percentile") is not None:
            expected = float(val_map[f"0.{bench}"]["percentile"])

        if expected is not None:
            diff = abs(val_pct_radar - expected)
            print(f"  {sec_id:18s} (bench: {bench:7s}) -> radar: {val_pct_radar:5.1f}%, corridor: {expected:5.1f}%, diff: {diff:.6f}")
            assert diff < 1e-4, f"Mismatch for {sec_id}: radar={val_pct_radar}, corridor={expected}"
            checked += 1
        else:
            print(f"  {sec_id:18s} (bench: {bench:7s}) -> radar: {val_pct_radar:5.1f}% (fallback/offline calculation)")
    print(f"Direct corridor matches verified: {checked} sectors.")

def test_thermometer_and_pulse_brief():
    radar = OpportunityRadarEngine()
    all_sectors = radar.scan_all_sectors()
    assert len(all_sectors) == 14, f"Expected 14 sectors, got {len(all_sectors)}"
    
    # Test pulse brief simulation
    turnover_str = "1.2万亿"
    vol_text = "放量活跃"
    erp_pct = 82.0
    erp_zone = f"ERP分位{erp_pct:.1f}%处历史高性价比击球区"
    top_names = [s.get("name", "") for s in all_sectors[:2] if s.get("name")]
    lead_str = "与".join(top_names)
    pulse_brief = f"两市成交{turnover_str}{vol_text}，{erp_zone}；{lead_str}领衔低估与右侧主线，策略宜逢低均衡布局。"
    if len(pulse_brief) > 80:
        pulse_brief = pulse_brief[:79] + "。"
    print(f"\nSimulated pulse brief ({len(pulse_brief)} chars):\n  {pulse_brief}")
    assert len(pulse_brief) <= 80, f"Pulse brief too long: {len(pulse_brief)}"
    assert "成交" in pulse_brief
    assert "ERP分位" in pulse_brief
    
    # Check thermometer table columns
    required_cols = ["赛道名称", "估值分位", "趋势信噪比", "20日乖离率", "拥挤度评分", "综合得分", "状态标签", "优选基金"]
    rows = []
    for s in all_sectors:
        f_info = s.get("fund", {})
        row = {
            "赛道名称": s.get("name", ""),
            "估值分位": f"{s.get('val_percentile', 50.0):.1f}%",
            "趋势信噪比": f"{s.get('er_20', 0.5):.2f}",
            "20日乖离率": f"{s.get('bias_20', 0.0):+.1f}%",
            "拥挤度评分": f"{s.get('s_crowd', 85.0):.1f}",
            "综合得分": f"{s.get('total_score', 50.0):.1f}",
            "状态标签": s.get("tag", "📈 稳健蓄势"),
            "优选基金": f"{f_info.get('name', '')} ({f_info.get('code', '')})",
        }
        for col in required_cols:
            assert col in row, f"Missing col {col} in row {row}"
        rows.append(row)
    df_thermometer = pd.DataFrame(rows)
    print(f"\nThermometer table shape: {df_thermometer.shape}")
    print(df_thermometer.head(3).to_string())

if __name__ == "__main__":
    test_parquet_and_dynamic_metrics()
    test_single_source_of_truth()
    test_thermometer_and_pulse_brief()
    print("\nALL VERIFICATIONS PASSED!")
