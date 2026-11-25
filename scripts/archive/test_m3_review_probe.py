import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'AGY2_FundAdvisory'))

from AGY2_FundAdvisory.multi_ledger_manager import MultiLedgerManager
from AGY2_FundAdvisory.strategy_bridge import StrategyBridge

mlm = MultiLedgerManager.get_instance()
pm = mlm.get_pm('combat_29_funds')
print('Total holdings count:', len(pm.holdings))

# Case 1: Standard rebalance with gentle mode (what btn_apply_combat29_rx currently triggers)
tier_target_w = StrategyBridge.compute_dynamic_tier_weights('C3')

res1 = StrategyBridge.generate_ai_rebalance_orders(
    current_holdings=pm.holdings,
    available_cash=pm.available_cash,
    target_weights_funds=tier_target_w,
    pm=pm,
    mode='gentle',
    min_buffer_pct=0.03,
    c_replace='011613',
    scenario_mode='standard',
)
items1 = res1.get('items', [])
print('\n--- Case 1: btn_apply_combat29_rx actual behavior (scenario_mode=standard) ---')
print('Orders generated count:', len(items1))
sell_items1 = [it for it in items1 if it.get('diff_amount', 0.0) < 0]
print('Sell items count:', len(sell_items1))
for it in sell_items1:
    print(f"  Sell: {it.get('fund_code')} {it.get('fund_name')} amt: {it.get('diff_amount')}")

# Case 2: What happens if scenario_mode is sweep_tail_and_c_class
res2 = StrategyBridge.generate_ai_rebalance_orders(
    current_holdings=pm.holdings,
    available_cash=pm.available_cash,
    target_weights_funds=tier_target_w,
    pm=pm,
    mode='gentle',
    min_buffer_pct=0.03,
    c_replace='011613',
    scenario_mode='sweep_tail_and_c_class',
    core_anchor_code='002351'
)
items2 = res2.get('items', [])
print('\n--- Case 2: Expected sweep tail behavior (scenario_mode=sweep_tail_and_c_class) ---')
print('Orders generated count:', len(items2))
sell_items2 = [it for it in items2 if it.get('diff_amount', 0.0) < 0]
print('Sell items count:', len(sell_items2))
swept_fragments = [it for it in sell_items2 if abs(it.get('diff_amount', 0.0)) < 100]
print('Swept fragment tail items (<100):', len(swept_fragments))
