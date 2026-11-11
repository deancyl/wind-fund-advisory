import sys
from pathlib import Path

# Add AGY2_FundAdvisory to sys.path
sys.path.insert(0, str(Path("d:/Google/Workspace/Wind/AGY2_FundAdvisory")))

from strategy_bridge import StrategyBridge
from advisory_engine import generate_chief_advisor_memo

snap = StrategyBridge.get_latest_market_snapshot()
print("=== SNAPSHOT KEYS ===")
print(list(snap.keys()))

print("\nSpecific keys in snap:")
for k in ["treasury_10y", "dr007", "dr007_spread_bp", "erp_percentile", "erp_val", "spot_usdcnh", "us_treasury_10y", "bias_20", "c300_price"]:
    print(f"  {k}: {snap.get(k)}")

memo = generate_chief_advisor_memo(snapshot=snap)
print("\n=== MEMO OUTPUT KEYS ===")
print(list(memo.keys()))
for k, v in memo.items():
    print(f"\n--- {k} ---")
    if isinstance(v, dict):
        for k2, v2 in v.items():
            print(f"  {k2}: {v2}")
    else:
        print(f"  {v}")
