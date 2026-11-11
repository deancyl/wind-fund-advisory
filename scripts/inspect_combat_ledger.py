# -*- coding: utf-8 -*-
import sys
import os
sys.path.insert(0, os.path.abspath("."))

from AGY2_FundAdvisory.multi_ledger_manager import MultiLedgerManager
from AGY2_FundAdvisory.advisory_engine import generate_chief_advisor_memo

def inspect_combat():
    mlm = MultiLedgerManager()
    pm = mlm.get_pm("combat_29_funds")
    print(f"Total holdings: {len(pm.holdings)}")
    for k, h in pm.holdings.items():
        mv = getattr(h, "market_value", 0.0)
        cb = getattr(h, "cost_basis", 0.0)
        pnl = getattr(h, "floating_pnl", 0.0)
        pnl_pct = getattr(h, "floating_pnl_pct", 0.0)
        days = getattr(h, "holding_days", None)
        cls = getattr(h, "share_class", "")
        print(f"{k} | {h.fund_name} | mv={mv:.2f} | cb={cb:.2f} | pnl={pnl:.2f} | pnl_pct={pnl_pct:.2f}% | days={days} | class={cls}")

    memo = generate_chief_advisor_memo(holdings=pm.holdings)
    p = memo["portfolio_pathology"]
    print("--- MEMO PATHOLOGY ---")
    print(f"deep_loss_count: {p['deep_loss_count']}")
    print(f"frag_count: {p['frag_count']}")
    print(f"frag_amt: {p['frag_amt']:.2f}")
    print(f"content:\n{p['content']}")

if __name__ == "__main__":
    inspect_combat()
