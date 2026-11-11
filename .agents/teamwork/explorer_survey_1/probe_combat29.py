import sys
from pathlib import Path

# Add AGY2_FundAdvisory to path
workspace_root = Path(r"D:\Google\Workspace\Wind")
sys.path.insert(0, str(workspace_root / "AGY2_FundAdvisory"))

from multi_ledger_manager import MultiLedgerManager
from advisory_engine import generate_chief_advisor_memo

mlm = MultiLedgerManager.get_instance(workspace_root)
pm_combat = mlm.get_pm("combat_29_funds")

print(f"Loaded combat_29_funds holdings count: {len(pm_combat.holdings)}")

# Inspect first 3 holdings attributes
for code, h in list(pm_combat.holdings.items())[:3]:
    print(f"\n--- Fund: {code} ({h.fund_name}) ---")
    print(f"type: {type(h)}")
    print(f"market_value: {h.market_value}")
    print(f"cost_basis: {getattr(h, 'cost_basis', 'N/A')}")
    print(f"cost_price: {getattr(h, 'cost_price', 'N/A')}")
    print(f"floating_pnl: {getattr(h, 'floating_pnl', 'N/A')}")
    print(f"floating_pnl_pct: {getattr(h, 'floating_pnl_pct', 'N/A')}")
    print(f"cost_value (hasattr): {hasattr(h, 'cost_value')}")

# Call generate_chief_advisor_memo with real combat_29_funds
memo = generate_chief_advisor_memo(holdings=pm_combat.holdings)
pathology = memo["portfolio_pathology"]
print("\n=== Current generate_chief_advisor_memo Output on combat_29_funds ===")
print(f"deep_loss_count: {pathology['deep_loss_count']}")
print(f"frag_count: {pathology['frag_count']}")
print(f"frag_amt: {pathology['frag_amt']}")
print(f"content: {pathology['content']}")
