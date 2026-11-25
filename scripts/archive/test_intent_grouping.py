import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
AGY2_DIR = ROOT_DIR / "AGY2_FundAdvisory"
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(AGY2_DIR))

from strategy_bridge import StrategyBridge
from portfolio_manager import MultiLedgerManager
from ui_daily_brief import group_rebalance_orders_by_intent

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

items = res.get("items", [])
grouped = group_rebalance_orders_by_intent(items)
print("Grouped keys:", grouped.keys())
print("Tail count:", grouped["tail_sweep"]["count"], "cash:", grouped["tail_sweep"]["total_recovered_cash"])
print("C-replace count:", grouped["c_replace"]["count"])
print("Core trades count:", grouped["core_trades"]["count"])
print("Total count check:", grouped["total_count"], "expected:", len(items))
assert grouped["total_count"] == len(items), "Count mismatch!"
print("Grouped orders intent verified!")
