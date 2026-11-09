import io
import sys
sys.path.insert(0, ".")
from PIL import Image
import pandas as pd
from AGY2_FundAdvisory.portfolio_manager import (
    slice_long_screenshot_for_ocr,
    fuzzy_match_fund_by_name,
    parse_smart_text_holdings,
    parse_batch_fund_text_input,
    PortfolioManager,
)
from AGY2_FundAdvisory.advisory_engine import ActiveRiskSentry

def test_adversarial_slicing():
    print("=== 1. Adversarial Slicing Tests ===")
    # Case 1: Empty bytes
    assert slice_long_screenshot_for_ocr(b"") == []
    print("Empty bytes: PASS")

    # Case 2: Corrupted bytes
    assert slice_long_screenshot_for_ocr(b"not an image") == []
    print("Corrupted bytes: PASS")

    # Case 3: 1x1 image
    img_1x1 = Image.new("RGB", (1, 1), (255, 255, 255))
    b = io.BytesIO()
    img_1x1.save(b, format="PNG")
    res_1x1 = slice_long_screenshot_for_ocr(b.getvalue(), target_height=1000, overlap=150)
    assert len(res_1x1) == 1
    assert res_1x1[0][0].size == (1, 1)
    print("1x1 image: PASS")

    # Case 4: RGBA image with alpha channel
    img_rgba = Image.new("RGBA", (1080, 2500), (255, 0, 0, 128))
    b = io.BytesIO()
    img_rgba.save(b, format="PNG")
    res_rgba = slice_long_screenshot_for_ocr(b.getvalue(), target_height=1000, overlap=150)
    assert len(res_rgba) == 3
    for s_img, _ in res_rgba:
        assert s_img.mode == "RGB"
        assert s_img.size[0] == 1080
    print("RGBA mode conversion: PASS")

    # Case 5: Grayscale L mode
    img_l = Image.new("L", (800, 1500), 128)
    b = io.BytesIO()
    img_l.save(b, format="PNG")
    res_l = slice_long_screenshot_for_ocr(b.getvalue(), target_height=1000, overlap=150)
    assert len(res_l) == 2
    for s_img, _ in res_l:
        assert s_img.mode == "RGB"
        assert s_img.size[0] == 800
    print("Grayscale L mode conversion: PASS")

    # Case 6: overlap >= target_height (potential infinite loop trap)
    img_loop = Image.new("RGB", (500, 2000), (0, 255, 0))
    b = io.BytesIO()
    img_loop.save(b, format="PNG")
    res_loop = slice_long_screenshot_for_ocr(b.getvalue(), target_height=1000, overlap=1200)
    # Should not hang because step = max(1, target_height // 2) = 500
    assert len(res_loop) > 1
    print("overlap >= target_height anti-infinite-loop: PASS")

    # Case 7: Extreme aspect ratio (1080 x 15000)
    img_huge = Image.new("RGB", (1080, 15000), (0, 0, 255))
    b = io.BytesIO()
    img_huge.save(b, format="PNG")
    res_huge = slice_long_screenshot_for_ocr(b.getvalue(), target_height=1000, overlap=150)
    # 15000 with step 850: 1 + ceil((15000-1000)/850) = 1 + 17 = 18 slices
    assert len(res_huge) == 18
    print("Extreme aspect ratio (1080x15000): PASS")


def test_adversarial_fuzzy_matching():
    print("\n=== 2. Adversarial Fuzzy Matching Tests ===")
    # Empty, whitespace, noise
    assert fuzzy_match_fund_by_name("") == {}
    assert fuzzy_match_fund_by_name("   \n\t  ") == {}
    assert fuzzy_match_fund_by_name("......") == {}
    assert fuzzy_match_fund_by_name("???！！！---") == {}
    print("Empty and noise inputs: PASS")

    # Complete gibberish
    gibberish = fuzzy_match_fund_by_name("火星超高频量化对冲超级阿尔法混合999号")
    assert gibberish.get("score", 0) < 0.65 or gibberish == {}
    print("Gibberish rejection: PASS")

    # Punctuation & Ellipsis robustness
    cases = [
        ("【招商】中证白酒...A", "161725"),
        ("（华夏）上证科创板50成份ETF联接C", "011613"),
        ("创金合信中证红利低波动指数A/类", "005561"),
        ("易方达裕祥回报债券(A类)", "002351"),
        ("富国中证红利指数增强A(100032)", "100032"),
        ("华安纳斯达克100ETF联接A...", "017436"),
    ]
    for text, code in cases:
        r = fuzzy_match_fund_by_name(text)
        assert r.get("fund_code") == code, f"Expected {code} for '{text}', got {r}"
    print("Punctuation & Ellipsis robustness: PASS")


def test_adversarial_accounting_and_parsing():
    print("\n=== 3. Adversarial Accounting & Parsing Tests ===")
    # 1. Negative pnl with comma and minus
    t1 = "易方达裕祥回报债券A 002351 持有金额 4,101.71 持有收益 -48.89"
    r1 = parse_smart_text_holdings(t1)
    assert len(r1) == 1
    assert r1[0]["market_value"] == 4101.71
    assert r1[0]["floating_pnl"] == -48.89
    assert abs(r1[0]["cost_basis"] - 4150.60) < 0.05
    print("Negative pnl and comma separation: PASS")

    # 2. Chinese keywords for loss
    t2 = "华夏上证科创板50成份ETF联接C 011613 持有金额 2072.52 亏损 428.48"
    r2 = parse_smart_text_holdings(t2)
    assert len(r2) == 1
    assert r2[0]["market_value"] == 2072.52
    assert r2[0]["floating_pnl"] == -428.48
    assert abs(r2[0]["cost_basis"] - 2501.00) < 0.05
    print("Chinese '亏损' keyword handling: PASS")

    # 3. Micro tail fund with tiny decimals
    t3 = "天弘中证500ETF联接C 001551 持有金额 0.59 亏损 0.41"
    r3 = parse_smart_text_holdings(t3)
    assert len(r3) == 1
    assert r3[0]["market_value"] == 0.59
    assert r3[0]["floating_pnl"] == -0.41
    assert abs(r3[0]["cost_basis"] - 1.00) < 0.05
    print("Micro tail fund (0.59 yuan) preservation: PASS")

    # 4. Zero floating pnl
    t4 = "易方达裕祥回报债券C 002352 持有金额 50.00 收益 0.00"
    r4 = parse_smart_text_holdings(t4)
    assert len(r4) == 1
    assert r4[0]["market_value"] == 50.00
    assert r4[0]["floating_pnl"] == 0.00
    assert r4[0]["cost_basis"] == 50.00
    print("Zero floating pnl handling: PASS")


def test_adversarial_sentry_dimension_13():
    print("\n=== 4. Adversarial ActiveRiskSentry Dimension 13 Tests ===")
    sentry = ActiveRiskSentry()

    # Case 1: Un-matured fund (A class, only 10 days) -> MUST NOT be flagged!
    unmatured_holdings = [
        {"fund_code": "001551", "fund_name": "天弘500A", "market_value": 50.0, "holding_days": 10, "share_class": "A"},
        {"fund_code": "005561", "fund_name": "创金红利A", "market_value": 50000.0, "holding_days": 400, "share_class": "A"},
    ]
    rep1 = sentry.inspect_portfolio(unmatured_holdings)
    tail1 = [a for a in rep1["alerts"] if a.get("dimension") == "碎片尾仓清理"]
    assert len(tail1) == 0, f"Unmatured A-class fund (10 days) must NOT be flagged as fee-free tail! Got: {tail1}"
    print("Unmatured fund (<365d for A) fee-protection: PASS")

    # Case 2: Un-matured C class (<30 days) -> MUST NOT be flagged!
    unmatured_c = [
        {"fund_code": "001551", "fund_name": "天弘500C", "market_value": 50.0, "holding_days": 15, "share_class": "C"},
        {"fund_code": "005561", "fund_name": "创金红利A", "market_value": 50000.0, "holding_days": 400, "share_class": "A"},
    ]
    rep2 = sentry.inspect_portfolio(unmatured_c)
    tail2 = [a for a in rep2["alerts"] if a.get("dimension") == "碎片尾仓清理"]
    assert len(tail2) == 0, f"Unmatured C-class fund (15 days) must NOT be flagged as fee-free tail! Got: {tail2}"
    print("Unmatured C-class fund (<30d for C) fee-protection: PASS")

    # Case 3: Empty portfolio
    rep3 = sentry.inspect_portfolio([])
    tail3 = [a for a in rep3["alerts"] if a.get("dimension") == "碎片尾仓清理"]
    assert len(tail3) == 0
    print("Empty portfolio robustness: PASS")

    # Case 4: Large core fund (5000 yuan) -> MUST NOT be flagged even if C class
    core_c = [
        {"fund_code": "011613", "fund_name": "华夏科创50C", "market_value": 5000.0, "holding_days": 400, "share_class": "C"},
        {"fund_code": "005561", "fund_name": "创金红利A", "market_value": 50000.0, "holding_days": 400, "share_class": "A"},
    ]
    rep4 = sentry.inspect_portfolio(core_c)
    tail4 = [a for a in rep4["alerts"] if a.get("dimension") == "碎片尾仓清理"]
    assert len(tail4) == 0
    print("Large C-class core fund protection: PASS")


if __name__ == "__main__":
    test_adversarial_slicing()
    test_adversarial_fuzzy_matching()
    test_adversarial_accounting_and_parsing()
    test_adversarial_sentry_dimension_13()
    print("\nALL ADVERSARIAL STRESS TESTS PASSED SUCCESSFULLY!")
