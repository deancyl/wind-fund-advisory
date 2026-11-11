import sys
from pathlib import Path

sys.path.insert(0, str(Path("d:/Google/Workspace/Wind/AGY2_FundAdvisory")))

from strategy_bridge import StrategyBridge

snap = StrategyBridge.get_latest_market_snapshot()
print("target_weights_index:", snap.get("target_weights_index"))
print("target_weights_funds:", snap.get("target_weights_funds"))
print("market_state_code:", snap.get("market_state_code"))
print("market_state:", snap.get("market_state"))

for tier in ["conservative", "balanced", "growth", "aggressive"]:
    tw = StrategyBridge.compute_dynamic_tier_weights(tier=tier, market_snapshot=snap)
    print(f"Tier {tier} target weights: {tw}")
