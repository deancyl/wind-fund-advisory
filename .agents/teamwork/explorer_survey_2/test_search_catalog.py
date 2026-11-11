import sys
sys.path.insert(0, r"D:\Google\Workspace\Wind\AGY2_FundAdvisory")
from portfolio_manager import search_funds_in_catalog

print("search '05':", search_funds_in_catalog("05", limit=3))
print("search '0':", search_funds_in_catalog("0", limit=3))
