# -*- coding: utf-8 -*-
import sys
from pathlib import Path
WORKSPACE_ROOT = Path(__file__).parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from AGY2_FundAdvisory.portfolio_manager import (
    fuzzy_match_fund_by_name,
    _load_fund_catalog_data,
)

print("--- Testing E-shares ---")
print("E: 天弘中证500指数E ->", fuzzy_match_fund_by_name("天弘中证500指数E"))
print("A: 天弘中证500指数A ->", fuzzy_match_fund_by_name("天弘中证500指数A"))
print("C: 天弘中证500指数C ->", fuzzy_match_fund_by_name("天弘中证500指数C"))

print("--- Testing 广发中证500 ---")
print("广发中证500A ->", fuzzy_match_fund_by_name("广发中证500A"))
print("广发中证500C ->", fuzzy_match_fund_by_name("广发中证500C"))
print("广发中证500E ->", fuzzy_match_fund_by_name("广发中证500E"))
