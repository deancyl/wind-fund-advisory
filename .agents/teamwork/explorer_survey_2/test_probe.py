import sys
sys.path.insert(0, r"D:\Google\Workspace\Wind\AGY2_FundAdvisory")
from portfolio_manager import fuzzy_match_fund_by_name, parse_smart_text_holdings

test_cases = [
    "华安黄金ETF联接C (395.73元)",
    "南方中证新能源ETF联接C \n 昨日收益 +0.05  34.50 \n 持有收益 -15.50  持有金额 19.00",
    "富国中证红利指数增强A 35000元",
    "华夏科创50ETF联接C 20000 亏500"
]

print("--- Testing fuzzy_match_fund_by_name ---")
for tc in test_cases:
    res = fuzzy_match_fund_by_name(tc)
    print(f"Input: {tc[:30]}... -> Result: {res}")

print("\n--- Testing parse_smart_text_holdings ---")
for tc in test_cases:
    res = parse_smart_text_holdings(tc)
    print(f"Input: {tc[:30]}... -> Result: {res}")
