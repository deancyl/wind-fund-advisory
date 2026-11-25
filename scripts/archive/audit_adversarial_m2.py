import sys
import os
sys.path.insert(0, os.path.abspath("."))
from AGY2_FundAdvisory.portfolio_manager import parse_smart_text_holdings, fuzzy_match_fund_by_name

print("=== ADVERSARIAL STRESS TEST: parse_smart_text_holdings ===")

test_cases = [
    # Case 1: Unseen fund with noise
    ("易方达蓝筹精选混合 \n 昨日收益 -120.50 \n 持有金额 15,200.00 \n 持有收益 +2,350.50", "005827", 15200.0, 2350.5),
    # Case 2: Code with spaces and commas
    ("110011 易方达中小盘 30,000.00 持有收益 -5,000.00", "110011", 30000.0, -5000.0),
    # Case 3: C-class fund with A/C disambiguation
    ("富国中证红利指数增强C \n 持有金额 4,500.00 \n 持有收益 -300.00", "008682", 4500.0, -300.0),
    # Case 4: A-class fund
    ("富国中证红利指数增强A 8,800.00 收益 500.00", "100032", 8800.0, 500.0),
    # Case 5: 19 fragments from combat 29 funds
    ("华夏中证500ETF联接C 124.14 亏27.28", "001053", 124.14, -27.28),
    ("博时标普500ETF联接A 89.60 收益 1.20", "050025", 89.60, 1.20),
    ("摩根标普500指数A 54.12 收益 0.85", "001071", 54.12, 0.85),
    ("招商中证红利稳益增强C 34.50 亏15.50", "018757", 34.50, -15.50),
]

all_passed = True
for raw_text, exp_code, exp_mv, exp_pnl in test_cases:
    res = parse_smart_text_holdings(raw_text)
    if not res:
        print(f"[FAIL] Parsed empty for input:\n{raw_text}")
        all_passed = False
        continue
    item = res[0]
    matched_code = item.get("fund_code")
    mv = item.get("market_value")
    pnl = item.get("floating_pnl")
    cost = item.get("cost_basis")
    
    code_ok = (matched_code == exp_code)
    mv_ok = abs(mv - exp_mv) < 0.05
    pnl_ok = (pnl is None and exp_pnl is None) or (abs(pnl - exp_pnl) < 0.05)
    cost_ok = abs(cost - (exp_mv - exp_pnl)) < 0.05
    
    if code_ok and mv_ok and pnl_ok and cost_ok:
        print(f"[PASS] {matched_code} | MV: {mv:.2f} | PnL: {pnl:.2f} | Cost: {cost:.2f}")
    else:
        print(f"[FAIL] Expected ({exp_code}, {exp_mv}, {exp_pnl}), got ({matched_code}, {mv}, {pnl}, cost={cost})")
        all_passed = False

if all_passed:
    print("ALL ADVERSARIAL CASES PASSED GENUINELY!")
else:
    print("SOME CASES FAILED!")
