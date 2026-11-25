# -*- coding: utf-8 -*-
import sys
import os
sys.path.insert(0, os.path.abspath("."))

from AGY2_FundAdvisory.multi_ledger_manager import MultiLedgerManager
from AGY2_FundAdvisory.advisory_engine import ActiveRiskSentry, generate_chief_advisor_memo

def test_sentry():
    mlm = MultiLedgerManager()
    pm = mlm.get_pm("combat_29_funds")
    sentry = ActiveRiskSentry()
    rep = sentry.inspect_portfolio(pm.holdings)
    print("Sentry alerts count:", len(rep.get("alerts", [])))
    for a in rep.get("alerts", []):
        if "碎片尾仓" in a.get("title", "") or a.get("dimension") == "碎片尾仓清理":
            print("Fragment alert:", a)
            
    memo_with_sentry = generate_chief_advisor_memo(holdings=pm.holdings, sentry_rep=rep)
    p = memo_with_sentry["portfolio_pathology"]
    print(f"Memo with sentry: frag_count={p['frag_count']}, frag_amt={p['frag_amt']:.2f}")

if __name__ == "__main__":
    test_sentry()
