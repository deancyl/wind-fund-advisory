import sys
import os
import numpy as np
WORKSPACE_DIR = r"D:\Google\Workspace\Wind"
sys.path.insert(0, WORKSPACE_DIR)
sys.path.insert(0, os.path.join(WORKSPACE_DIR, "AGY2_FundAdvisory"))

from AGY2_FundAdvisory.advisory_engine import OpportunityRadarEngine, RADAR_SECTOR_CATALOG

sectors = OpportunityRadarEngine.get_cached_sectors_fast()
print("Fast cached sectors count:", len(sectors) if sectors else None)
if not sectors:
    radar = OpportunityRadarEngine()
    sectors = radar.scan_all_sectors()
    print("Scanned sectors count:", len(sectors))

print("Total sectors catalog length:", len(RADAR_SECTOR_CATALOG))
vals = [s.get("val_percentile") for s in sectors]
crowds = [s.get("crowding_score", s.get("s_crowd")) for s in sectors]
names = [s.get("name") for s in sectors]
print("Sector names:", names)
print("Val percentiles:", vals)
print("Crowding scores:", crowds)
print("Top 3 sectors:", names[:3])
print("Top 3 val avg:", np.mean(vals[:3]))
print("All sectors median val:", np.median(vals))
print("All sectors avg crowd:", np.mean(crowds))
