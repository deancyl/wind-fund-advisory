import sys
import os
sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.abspath("AGY2_FundAdvisory"))

from portfolio_manager import PortfolioManager
from advisory_engine import ActiveRiskSentry

pm = PortfolioManager()
pm.load_demo_portfolio()
sentry = ActiveRiskSentry()
report = sentry.inspect_portfolio(pm.holdings)

print("Summary:", report["summary"])
print("Alert count:", len(report["alerts"]))
for i, a in enumerate(report["alerts"]):
    print(f"[{i}] Level: {a['level']} | Dim: {a['dimension']} | Fund: {a.get('fund_code', '')} | Action: {a['action_type']}")
    print(f"     Title: {a['title']}")
