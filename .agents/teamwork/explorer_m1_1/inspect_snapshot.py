import sys
import os
WORKSPACE_DIR = r"D:\Google\Workspace\Wind"
sys.path.insert(0, WORKSPACE_DIR)
sys.path.insert(0, os.path.join(WORKSPACE_DIR, "AGY2_FundAdvisory"))

from AGY2_FundAdvisory.strategy_bridge import StrategyBridge
from AGY2_FundAdvisory.advisory_engine import compute_ten_dimension_votes

snap = StrategyBridge.get_latest_market_snapshot()
print("Snapshot keys:", [k for k in snap.keys() if "iv" in k or "basis" in k or "corr" in k or "crowd" in k])
print("option_iv_pct:", snap.get("option_iv_pct"))
print("ivix_index:", snap.get("ivix_index"))
print("ic_annualized_basis_rate:", snap.get("ic_annualized_basis_rate"))
print("dynamic_correlation:", snap.get("dynamic_correlation"))

res = compute_ten_dimension_votes(snap)
print("Current votes:")
for d in res["dimensions"]:
    print(f"  {d['name']}: vote={d['vote']}, score={d['score']}, delta={d['delta_pct']}%, reason={d['reason']}")
print("Causal formula:", res["causal_formula"])
