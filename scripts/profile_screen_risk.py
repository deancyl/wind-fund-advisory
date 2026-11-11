import sys
from pathlib import Path
sys.path.insert(0, str(Path("AGY2_FundAdvisory").resolve()))
import time
from portfolio_manager import PortfolioManager

pm = PortfolioManager()
print(f"Testing screen_fund_look_through_risk for 6 holdings...")

for h in pm.holdings.values():
    t0 = time.time()
    res = pm.screen_fund_look_through_risk(h.fund_code)
    t1 = time.time()
    print(f"Fund {h.fund_code} ({h.fund_name}): {t1 - t0:.3f}s")
