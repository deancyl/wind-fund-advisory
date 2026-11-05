import sys
sys.path.insert(0, r"d:\Google\Workspace\Wind\AGY2_FundAdvisory")
sys.path.insert(0, r"d:\Google\Workspace\Wind")

from advisory_engine import OpportunityRadarEngine

engine = OpportunityRadarEngine()
metrics = engine._calc_dynamic_sector_metrics()
print("Current dynamic sector metrics:")
for k, v in metrics.items():
    print(f"  {k}: {v}")
