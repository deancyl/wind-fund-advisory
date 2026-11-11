import sys
sys.path.insert(0, r"D:\Google\Workspace\Wind\AGY2_FundAdvisory")
from portfolio_manager import parse_smart_text_holdings

tc = "南方中证新能源ETF联接C \n 昨日收益 +0.05  34.50 \n 持有收益 -15.50"
res = parse_smart_text_holdings(tc)
print("Result without explicit 持有金额 label:")
for r in res:
    print(r)
