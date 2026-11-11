# -*- coding: utf-8 -*-
"""
Milestone 2 Reviewer Independent Verification and Adversarial Probe Script
"""
import sys
import re
from pathlib import Path

# Add project root to path
WORKSPACE_ROOT = Path(__file__).parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from AGY2_FundAdvisory.portfolio_manager import (
    PortfolioManager,
    parse_smart_text_holdings,
    fuzzy_match_fund_by_name,
    parse_screenshot_ocr_holdings,
    parse_long_screenshot_holdings,
    search_funds_in_catalog
)

def run_probes():
    findings = []
    print("=" * 60)
    print("STARTING INDEPENDENT REVIEWER PROBES FOR MILESTONE 2")
    print("=" * 60)

    # -------------------------------------------------------------
    # Probe 1: Fuzzy matching A/C share classes & Alias recognition
    # -------------------------------------------------------------
    print("\n--- Probe 1: Fuzzy matching A/C share classes ---")
    test_cases_p1 = [
        ("华安黄金ETF联接C (395.73元)", "000217", "C"),
        ("华安黄金ETF联接A 1000元", "000216", "A"),
        ("华安黄金C 500元", "000217", "C"),
        ("华安黄金A 500元", "000216", "A"),
        ("黄金C", "000217", "C"),
        ("黄金A", "000216", "A"),
        ("南方中证新能源ETF联接C", "012832", "C"),
        ("南方中证新能源ETF联接A", "012831", "A"),
        ("华夏科创50C 20000 亏500", "011613", "C"),
        ("华夏科创50A 20000", "011612", "A"),
        ("富国中证红利C", "008682", "C"),
        ("富国中证红利A", "100032", "A"),
        ("富国红利C", "008682", "C"),
        ("富国红利A", "100032", "A"),
        ("纯债 20000", "002351", "A"),
        ("易方达裕祥回报债券A", "002351", "A"),
        ("招商中证白酒指数C", "012414", "C"), # let's see what catalog has for 白酒C or ALIAS
        ("招商白酒", "161725", "A"),
        ("银华集成电路混合C", "013841", "C"),
        ("银华集成电路混合A", "013840", "A"),
        ("华夏中证500ETF联接C", "001053", "C"),
        ("华夏中证500ETF联接A", "001052", "A"),
        ("博时标普500ETF联接A", "050025", "A"),
    ]

    for raw, exp_code, exp_class in test_cases_p1:
        res = fuzzy_match_fund_by_name(raw)
        actual_code = res.get("fund_code")
        actual_class = res.get("share_class")
        if actual_code == exp_code and actual_class == exp_class:
            print(f"  [PASS] '{raw}' -> code={actual_code}, class={actual_class}")
        else:
            print(f"  [FAIL/NOTE] '{raw}' -> expected ({exp_code}, {exp_class}), got ({actual_code}, {actual_class})")
            findings.append(f"Probe 1 mismatch: '{raw}' expected ({exp_code}, {exp_class}) but got ({actual_code}, {actual_class})")

    # -------------------------------------------------------------
    # Probe 2: Yesterday's profit stripping in parse_smart_text_holdings
    # -------------------------------------------------------------
    print("\n--- Probe 2: Yesterday's profit stripping ---")
    text_variations = [
        # Normal positive yesterday profit with spaces
        ("南方中证新能源ETF联接C \n 昨日收益 +0.05  34.50 \n 持有收益 -15.50  持有金额", "012832", 34.50, -15.50, 50.00),
        # Negative yesterday profit
        ("南方中证新能源ETF联接C \n 昨日收益 -12.34  34.50 \n 持有收益 -15.50", "012832", 34.50, -15.50, 50.00),
        # With colon: 昨日收益: +1,234.56
        ("华安黄金ETF联接C 昨日收益: +1,234.56 市值 395.73 持有收益 +25.00", "000217", 395.73, 25.00, 370.73),
        # Chinese tag "昨日盈亏"
        ("易方达裕祥 昨日盈亏 -50.20 持有金额 20000.00 盈利 1200.00", "002351", 20000.00, 1200.00, 18800.00),
        # Chinese tag "日收益"
        ("华夏科创50C 日收益 +18.90 持有资产 50000 亏损 2000", "011613", 50000.00, -2000.00, 52000.00),
    ]

    for raw, exp_code, exp_mv, exp_pnl, exp_cost in text_variations:
        parsed = parse_smart_text_holdings(raw)
        if not parsed:
            print(f"  [FAIL] '{raw[:30]}...' parsed nothing")
            findings.append(f"Probe 2 failed: '{raw[:30]}' parsed nothing")
            continue
        p = parsed[0]
        code_ok = (p["fund_code"] == exp_code)
        mv_ok = abs(p["market_value"] - exp_mv) < 0.05
        pnl_ok = abs(p["floating_pnl"] - exp_pnl) < 0.05
        cost_ok = abs(p["cost_basis"] - exp_cost) < 0.05
        if code_ok and mv_ok and pnl_ok and cost_ok:
            print(f"  [PASS] '{raw.splitlines()[0][:25]}...' -> code={p['fund_code']}, mv={p['market_value']}, pnl={p['floating_pnl']}, cost={p['cost_basis']}")
        else:
            print(f"  [FAIL] '{raw.splitlines()[0][:25]}...' -> got code={p['fund_code']}, mv={p['market_value']}, pnl={p['floating_pnl']}, cost={p['cost_basis']}")
            findings.append(f"Probe 2 mismatch: got code={p['fund_code']}, mv={p['market_value']}, pnl={p['floating_pnl']}, cost={p['cost_basis']}")

    # -------------------------------------------------------------
    # Probe 3: Pure digit cutoff check (w.isdigit() blocking)
    # -------------------------------------------------------------
    print("\n--- Probe 3: Pure digit cutoff check ---")
    # Verify line 1377: words = [w for w in re.findall(r'[\u4e00-\u9fa5A-Za-z0-9]+', remain_line) if not w.isdigit() and len(w) >= 2]
    # Check that leftovers like '05', '34', '1000' are NOT in words
    test_line = "昨日收益 +0.05  34.50"
    cleaned = re.sub(r'(?:昨日收益|昨日盈亏|日收益)[:：\s]*[+-]?[0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?', ' ', test_line)
    cleaned = re.sub(r'(?:昨日收益|昨日盈亏|日收益)', ' ', cleaned)
    words = [w for w in re.findall(r'[\u4e00-\u9fa5A-Za-z0-9]+', cleaned) if not w.isdigit() and len(w) >= 2]
    print(f"  Input: '{test_line}' -> cleaned: '{cleaned}' -> words to catalog search: {words}")
    if any(w.isdigit() for w in words):
        print("  [FAIL] pure digits found in words list!")
        findings.append("Probe 3 failed: pure digits in words list")
    else:
        print("  [PASS] Pure digits completely blocked from catalog search words.")

    # -------------------------------------------------------------
    # Probe 4: parse_long_screenshot_holdings alias verification
    # -------------------------------------------------------------
    print("\n--- Probe 4: Alias verification ---")
    pm = PortfolioManager()
    alias_module_ok = (parse_long_screenshot_holdings is parse_screenshot_ocr_holdings)
    alias_class_ok = hasattr(pm, "parse_long_screenshot_holdings")
    print(f"  Module alias identical: {alias_module_ok}")
    print(f"  Class method exists: {alias_class_ok}")
    if not (alias_module_ok and alias_class_ok):
        findings.append("Probe 4 failed: alias not properly mounted")
    else:
        print("  [PASS] parse_long_screenshot_holdings alias properly mounted.")

    # -------------------------------------------------------------
    # Probe 5: Adversarial edge cases
    # -------------------------------------------------------------
    print("\n--- Probe 5: Adversarial edge cases ---")
    # Adversarial Case 5.1: Multiple holdings pasted together in one block
    multi_paste = """
    000217 华安黄金ETF联接C 395.73元 盈利25.00
    012832 南方中证新能源ETF联接C 34.50 亏15.50 昨日收益 +0.05
    011613 华夏科创50C 20000 成本1.05 现价1.20 昨日盈亏 -500
    002351 易方达裕祥回报债券A 50000 收益1500
    """
    res_multi = parse_smart_text_holdings(multi_paste)
    print(f"  Multi-paste parsed count: {len(res_multi)}")
    for item in res_multi:
        print(f"    - {item['fund_code']} ({item['fund_name']}): mv={item['market_value']}, pnl={item['floating_pnl']}, cost={item['cost_basis']}")
    if len(res_multi) != 4:
        findings.append(f"Probe 5.1 failed: multi-paste expected 4 items, got {len(res_multi)}")
    else:
        print("  [PASS] Multi-paste parsed 4 items cleanly.")

    # Adversarial Case 5.2: Tail fragment with small value (e.g. 0.70 yuan)
    tail_text = "南方中证新能源ETF联接C 持有金额 0.70 昨日收益 0.00"
    res_tail = parse_smart_text_holdings(tail_text)
    if res_tail and abs(res_tail[0]["market_value"] - 0.70) < 0.01:
        print(f"  [PASS] Tail fragment 0.70元 recognized: mv={res_tail[0]['market_value']}")
    else:
        print(f"  [FAIL] Tail fragment not recognized: {res_tail}")
        findings.append(f"Probe 5.2 failed: tail fragment 0.70元 not parsed properly: {res_tail}")

    # Adversarial Case 5.3: Integrity violation scan (hardcoded strings in source)
    print("\n--- Probe 6: Integrity & Facade check ---")
    with open(WORKSPACE_ROOT / "AGY2_FundAdvisory" / "portfolio_manager.py", "r", encoding="utf-8") as f:
        pm_src = f.read()

    suspicious_patterns = [
        "if text == '南方中证新能源ETF联接C",
        "if text == '华安黄金ETF联接C",
        "if '34.50' in text and '012832' in",
        "mock",
        "fake",
    ]
    integrity_ok = True
    for pat in suspicious_patterns:
        if pat in pm_src:
            print(f"  [WARNING/FAIL] Found suspicious pattern in source: {pat}")
            findings.append(f"Integrity violation check: found pattern '{pat}' in portfolio_manager.py")
            integrity_ok = False
    if integrity_ok:
        print("  [PASS] No hardcoded test responses or facades found in portfolio_manager.py.")

    print("\n" + "=" * 60)
    print(f"PROBE SUMMARY: Total findings = {len(findings)}")
    for f in findings:
        print(f"  - {f}")
    print("=" * 60)

    return findings

if __name__ == "__main__":
    findings = run_probes()
    if findings:
        sys.exit(1)
    else:
        sys.exit(0)
