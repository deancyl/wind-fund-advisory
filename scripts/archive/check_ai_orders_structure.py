import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
AGY2_DIR = ROOT_DIR / "AGY2_FundAdvisory"
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(AGY2_DIR))

from strategy_bridge import StrategyBridge
from portfolio_manager import MultiLedgerManager

mlm = MultiLedgerManager.get_instance()
pm = mlm.get_pm('combat_29_funds')
rx = StrategyBridge.get_combat_29_vs_reconstructed_6_preset()
tw = dict(rx.get('reconstructed_6_weights', {}))

res = StrategyBridge.generate_ai_rebalance_orders(
    pm.holdings,
    pm.available_cash,
    tw,
    pm=pm,
    mode='gentle',
    min_buffer_pct=3.0,
    c_replace='011613',
    core_anchor_code='002351'
)

print("Keys:", res.keys())
items = res.get("items", [])
print("Total items:", len(items))
if items:
    print("Sample item 0:", items[0])
    print("Sample item -1:", items[-1])
