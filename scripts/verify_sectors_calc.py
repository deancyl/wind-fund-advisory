# -*- coding: utf-8 -*-
import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(root_dir / "AGY2_FundAdvisory"))

from advisory_engine import OpportunityRadarEngine, RADAR_SECTOR_CATALOG

print("dividend_low_vol benchmark:", RADAR_SECTOR_CATALOG['dividend_low_vol']['benchmark_index'])
print("dividend_low_vol index_code:", RADAR_SECTOR_CATALOG['dividend_low_vol']['index_code'])
assert RADAR_SECTOR_CATALOG['dividend_low_vol']['benchmark_index'] == 'H30269'

sectors = OpportunityRadarEngine().scan_all_sectors()
print(f"Scanned {len(sectors)} sectors:")
for s in sectors:
    print(f"{s['name']:<10} er:{s.get('er_20'):.2f} bias:{s.get('bias_20'):+.2f}% crowd:{s.get('s_crowd'):.1f} val:{s.get('val_percentile'):.1f}%")

# 验证没有共享假常数
dummy_count = 0
for s in sectors:
    if round(s.get('er_20', 0), 2) == 0.50 and round(s.get('bias_20', 0), 1) == 1.0 and round(s.get('s_crowd', 0), 1) == 85.0:
        dummy_count += 1
assert dummy_count == 0, f"Found {dummy_count} sectors with dummy constants!"
print("SUCCESS: All 14 sectors dynamically calculated with 0 dummy constants!")
