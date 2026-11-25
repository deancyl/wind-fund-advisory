# -*- coding: utf-8 -*-
import sys
import os
sys.path.insert(0, os.path.abspath("."))

from AGY2_FundAdvisory.multi_ledger_manager import MultiLedgerManager
from AGY2_FundAdvisory.advisory_engine import generate_chief_advisor_memo

def inspect_losses():
    mlm = MultiLedgerManager()
    pm = mlm.get_pm("combat_29_funds")
    memo = generate_chief_advisor_memo(holdings=pm.holdings)
    p = memo["portfolio_pathology"]
    print("Content:\n", p["content"])

if __name__ == "__main__":
    inspect_losses()
