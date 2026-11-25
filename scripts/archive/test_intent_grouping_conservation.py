# -*- coding: utf-8 -*-
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "AGY2_FundAdvisory"))

from multi_ledger_manager import MultiLedgerManager
from strategy_bridge import StrategyBridge
from ui_daily_brief import group_rebalance_orders_by_intent, IntentGroup

def test_intent_grouping():
    mlm = MultiLedgerManager.get_instance()
    pm29 = mlm.get_pm("combat_29_funds")
    rx = StrategyBridge.get_combat_29_vs_reconstructed_6_preset()
    tw = dict(rx.get("reconstructed_6_weights", {}))

    orders = StrategyBridge.generate_ai_rebalance_orders(
        pm29.holdings,
        pm29.available_cash,
        tw,
        pm=pm29,
        mode="gentle",
        min_buffer_pct=3.0,
        c_replace="011613",
        core_anchor_code="002351"
    )
    items = orders.get("items", [])
    grouped = group_rebalance_orders_by_intent(items)

    tail = grouped["tail_sweep"]
    c_rep = grouped["c_replace"]
    core = grouped["core_trades"]
    hold = grouped["buffer_hold"]

    print(f"Items count: {len(items)}")
    print(f"Tail count: {len(tail)}, dict count: {tail['count']}, recovered cash: {tail['total_recovered_cash']}")
    print(f"C-replace count: {len(c_rep)}, dict count: {c_rep['count']}")
    print(f"Core count: {len(core)}, dict count: {core['count']}")
    print(f"Hold count: {len(hold)}, dict count: {hold['count']}")

    total_grouped = len(tail) + len(c_rep) + len(core) + len(hold)
    print(f"Total grouped: {total_grouped}")
    assert total_grouped == len(items), "Total item count must match!"
    assert len(tail) == 19, f"Expected 19 tail, got {len(tail)}"
    assert len(c_rep) == 2, f"Expected 2 C-rep, got {len(c_rep)}"
    assert len(core) == 2, f"Expected 2 core, got {len(core)}"
    assert len(hold) == 6, f"Expected 6 hold, got {len(hold)}"

    orig_net = sum(float(x.get("diff_amount", x.get("amount", 0.0))) for x in items)
    grouped_net = sum(float(x.get("diff_amount", x.get("amount", 0.0))) for g in (tail, c_rep, core, hold) for x in g)
    print(f"Orig net: {orig_net:.4f}, Grouped net: {grouped_net:.4f}")
    assert abs(orig_net - grouped_net) < 1e-4, "Net sum mismatch!"
    print("ALL GROUPING AND CONSERVATION TESTS PASSED 100%!")

if __name__ == "__main__":
    test_intent_grouping()
