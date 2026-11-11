# -*- coding: utf-8 -*-
"""
Adversarial Edge Case Stress Test for parse_smart_text_holdings
"""
import sys
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from AGY2_FundAdvisory.portfolio_manager import (
    parse_smart_text_holdings,
    fuzzy_match_fund_by_name
)

def test_adversarial_cases():
    print("=== Testing Adversarial Edge Cases ===")

    # 1. Empty / Whitespace / Garbage
    assert parse_smart_text_holdings("") == []
    assert parse_smart_text_holdings("   \n\n\t  ") == []
    assert parse_smart_text_holdings("昨日收益 +123.45\n昨日盈亏 -50.00") == []
    print("  [PASS] Empty/Garbage rejection")

    # 2. Chinese brackets and class suffixes
    cases_bracket = [
        ("华安黄金ETF联接(C类) 395.73元", "000217", "C", 395.73),
        ("华安黄金ETF联接（C类） 395.73元", "000217", "C", 395.73),
        ("南方中证新能源ETF联接(C类) 34.50元", "012832", "C", 34.50),
        ("华夏科创50(C类) 20000元", "011613", "C", 20000.0),
        ("富国中证红利(C类) 5000元", "008682", "C", 5000.0),
    ]
    for text, exp_code, exp_class, exp_mv in cases_bracket:
        res = parse_smart_text_holdings(text)
        assert len(res) == 1, f"Failed on {text}, got {res}"
        assert res[0]["fund_code"] == exp_code, f"Code mismatch on {text}: {res[0]['fund_code']} vs {exp_code}"
        assert res[0]["share_class"] == exp_class, f"Class mismatch on {text}: {res[0]['share_class']} vs {exp_class}"
        assert abs(res[0]["market_value"] - exp_mv) < 0.01, f"MV mismatch on {text}: {res[0]['market_value']} vs {exp_mv}"
    print("  [PASS] Chinese brackets and class suffixes")

    # 3. Comma formatting and decimals
    cases_comma = [
        ("南方中证新能源ETF联接C 1,234.50元 亏1,000.00元 昨日收益: +123.45", "012832", 1234.50, -1000.00, 2234.50),
        ("华安黄金ETF联接C 10,000.00 盈利2,500.00 昨日盈亏 +50.25", "000217", 10000.00, 2500.00, 7500.00),
    ]
    for text, exp_code, exp_mv, exp_pnl, exp_cost in cases_comma:
        res = parse_smart_text_holdings(text)
        assert len(res) == 1, f"Failed on {text}, got {res}"
        p = res[0]
        assert p["fund_code"] == exp_code
        assert abs(p["market_value"] - exp_mv) < 0.01
        assert abs(p["floating_pnl"] - exp_pnl) < 0.01
        assert abs(p["cost_basis"] - exp_cost) < 0.01
    print("  [PASS] Comma formatting and decimals")

    # 4. Multi-token splitting behavior (checking why 34.50 and 0.05 are not matched to catalog)
    import re
    remain = "   34.50   "
    words = [w for w in re.findall(r'[\u4e00-\u9fa5A-Za-z0-9]+', remain) if not w.isdigit() and len(w) >= 2]
    assert words == [], f"Expected empty words for {remain}, got {words}"
    print("  [PASS] Split token digit blocking verified")

    # 5. Extreme yesterday profit values (larger than market value or negative)
    text_extreme = "南方中证新能源ETF联接C \n 昨日收益 +999,999.00  34.50 \n 持有收益 -15.50"
    res_ext = parse_smart_text_holdings(text_extreme)
    assert len(res_ext) == 1
    assert res_ext[0]["fund_code"] == "012832"
    assert abs(res_ext[0]["market_value"] - 34.50) < 0.01
    print("  [PASS] Extreme yesterday profit does not bleed into market value")

    print("ALL ADVERSARIAL CASES PASSED!")

if __name__ == "__main__":
    test_adversarial_cases()
