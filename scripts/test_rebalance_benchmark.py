import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
AGY2_DIR = ROOT_DIR / "AGY2_FundAdvisory"
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(AGY2_DIR))

from strategy_bridge import StrategyBridge
from portfolio_manager import MultiLedgerManager

mlm = MultiLedgerManager.get_instance()
pm = mlm.get_pm('combat_29_funds')
t0 = time.time()
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
t1 = time.time()
print(f"Time taken: {round(t1 - t0, 4)} s; items count: {len(res.get('items', []))}")
