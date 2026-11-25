import sys
import os
sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.abspath("AGY2_FundAdvisory"))

from advisory_engine import ActiveRiskSentry

sentry = ActiveRiskSentry()
try:
    sentry.inspect_portfolio([{"code": "001", "holding_days": None}])
    print("Handled None holding_days successfully")
except Exception as e:
    print(f"FAILED on None holding_days: {type(e).__name__}: {e}")
