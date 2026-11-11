# -*- coding: utf-8 -*-
"""
Deep Adversarial Testing Script for Milestone 2:
portfolio_manager.py smart text parsing, regex sanitization, fuzzy matching, and alias bindings.
"""
import sys
import re
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from AGY2_FundAdvisory.portfolio_manager import (
    PortfolioManager,
    parse_smart_text_holdings,
    fuzzy_match_fund_by_name,
    parse_screenshot_ocr_holdings,
    parse_long_screenshot_holdings,
)


def run_all_adversarial_tests():
    total_passed = 0
    total_failed = 0
    failures = []

    def check(desc: str, condition: bool, err_msg: str = ""):
        nonlocal total_passed, total_failed
        if condition:
            total_passed += 1
            print(f"  [PASS] {desc}")
        else:
            total_failed += 1
            full_err = f"{desc} -> {err_msg}"
            failures.append(full_err)
            print(f"  [FAIL] {full_err}")

    print("=" * 70)
    print("STARTING DEEP ADVERSARIAL VERIFICATION SUITE FOR MILESTONE 2")
    print("=" * 70)

    # =========================================================================
    # SCENARIO 1: 昨日收益干扰与高位截断对抗 (Yesterday Earnings Interference)
    # =========================================================================
    print("\n[Scenario 1] 昨日收益干扰与高位截断对抗")

    # 1.1 南方中证新能源C + 昨日收益 +0.05 34.50 + 持有收益 -15.50 + 持有金额 1000.00
    t1_1 = "南方中证新能源ETF联接C \n 昨日收益 +0.05 34.50 \n 持有收益 -15.50 持有金额 1000.00"
    r1_1 = parse_smart_text_holdings(t1_1)
    check("1.1 明确持有金额1000与昨日收益+0.05共存",
          len(r1_1) == 1 and r1_1[0]["fund_code"] == "012832" and r1_1[0]["share_class"] == "C" and abs(r1_1[0]["market_value"] - 1000.0) < 0.01 and abs(r1_1[0]["floating_pnl"] - (-15.5)) < 0.01,
          f"got: {r1_1}")

    # 1.2 尾部零头无持有金额标签: 34.50 作为纯数字金额，昨日收益 +0.05
    t1_2 = "南方中证新能源ETF联接C \n 昨日收益 +0.05  34.50 \n 持有收益 -15.50  持有金额"
    r1_2 = parse_smart_text_holdings(t1_2)
    check("1.2 零头市值34.50与昨日收益+0.05未截断",
          len(r1_2) == 1 and r1_2[0]["fund_code"] == "012832" and r1_2[0]["share_class"] == "C" and abs(r1_2[0]["market_value"] - 34.50) < 0.01 and abs(r1_2[0]["floating_pnl"] - (-15.50)) < 0.01 and abs(r1_2[0]["cost_basis"] - 50.00) < 0.01,
          f"got: {r1_2}")

    # 1.3 华安黄金C + 昨日收益负数多位数 (-123.45) + 市值 395.73 + 持有收益
    t1_3 = "华安黄金ETF联接C 昨日收益 -123.45 市值 395.73 持有收益 +16.93"
    r1_3 = parse_smart_text_holdings(t1_3)
    check("1.3 负昨日收益-123.45与市值395.73",
          len(r1_3) == 1 and r1_3[0]["fund_code"] == "000217" and r1_3[0]["share_class"] == "C" and abs(r1_3[0]["market_value"] - 395.73) < 0.01 and abs(r1_3[0]["floating_pnl"] - 16.93) < 0.01,
          f"got: {r1_3}")

    # 1.4 五位数大额昨日收益 (+12345.67)
    t1_4 = "易方达裕祥回报债券A 昨日收益 +12345.67 持有金额 50000.00 盈利 1500.00"
    r1_4 = parse_smart_text_holdings(t1_4)
    check("1.4 5位数大额昨日收益未破坏基金匹配与市值",
          len(r1_4) == 1 and r1_4[0]["fund_code"] == "002351" and r1_4[0]["share_class"] == "A" and abs(r1_4[0]["market_value"] - 50000.0) < 0.01 and abs(r1_4[0]["floating_pnl"] - 1500.0) < 0.01,
          f"got: {r1_4}")

    # 1.5 昨日收益带千分位与冒号 (+1,234.56)
    t1_5 = "华夏科创50C 昨日收益: +1,234.56 持有资产 20,000.00 亏损 500.00"
    r1_5 = parse_smart_text_holdings(t1_5)
    check("1.5 千分位昨日收益+1,234.56与千分位资产20,000.00",
          len(r1_5) == 1 and r1_5[0]["fund_code"] == "011613" and r1_5[0]["share_class"] == "C" and abs(r1_5[0]["market_value"] - 20000.0) < 0.01 and abs(r1_5[0]["floating_pnl"] - (-500.0)) < 0.01,
          f"got: {r1_5}")

    # 1.6 别名标签: "昨日盈亏" 与 "日收益"
    t1_6a = "富国中证红利C 昨日盈亏 -88.88 市值 10000.00 浮盈 500.00"
    r1_6a = parse_smart_text_holdings(t1_6a)
    check("1.6a 昨日盈亏标签剥离",
          len(r1_6a) == 1 and r1_6a[0]["fund_code"] == "008682" and r1_6a[0]["share_class"] == "C" and abs(r1_6a[0]["market_value"] - 10000.0) < 0.01 and abs(r1_6a[0]["floating_pnl"] - 500.0) < 0.01,
          f"got: {r1_6a}")

    t1_6b = "博时标普500ETF联接A 日收益 +12.34 金额 5000.00 收益 250.00"
    r1_6b = parse_smart_text_holdings(t1_6b)
    check("1.6b 日收益标签剥离",
          len(r1_6b) == 1 and r1_6b[0]["fund_code"] == "050025" and r1_6b[0]["share_class"] == "A" and abs(r1_6b[0]["market_value"] - 5000.0) < 0.01 and abs(r1_6b[0]["floating_pnl"] - 250.0) < 0.01,
          f"got: {r1_6b}")

    # 1.7 昨日收益与市值紧贴连写无换行
    t1_7 = "华安黄金ETF联接C 昨日收益 +0.50 395.73 持有收益 +16.93"
    r1_7 = parse_smart_text_holdings(t1_7)
    check("1.7 昨日收益与市值紧贴连写",
          len(r1_7) == 1 and r1_7[0]["fund_code"] == "000217" and abs(r1_7[0]["market_value"] - 395.73) < 0.01 and abs(r1_7[0]["floating_pnl"] - 16.93) < 0.01,
          f"got: {r1_7}")

    # =========================================================================
    # SCENARIO 2: 多份额与同名别名对抗 (Multi-Class & Homonymous Aliases)
    # =========================================================================
    print("\n[Scenario 2] 多份额与同名别名对抗")

    pairs = [
        ("华安黄金ETF联接A", "000216", "A", "华安黄金ETF联接C", "000217", "C"),
        ("易方达沪深300ETF联接A", "110020", "A", "易方达沪深300ETF联接C", "007339", "C"),
        ("富国中证红利指数增强A", "100032", "A", "富国中证红利指数增强C", "008682", "C"),
        ("华夏科创50ETF联接A", "011612", "A", "华夏科创50ETF联接C", "011613", "C"),
        ("南方中证新能源ETF联接A", "012831", "A", "南方中证新能源ETF联接C", "012832", "C"),
        ("银华集成电路混合A", "013840", "A", "银华集成电路混合C", "013841", "C"),
        ("富国中证1000ETF联接A", "016633", "A", "富国中证1000ETF联接C", "016634", "C"),
        ("华夏中证500ETF联接A", "001052", "A", "华夏中证500ETF联接C", "001053", "C"),
        ("华夏中证红利质量A", "016440", "A", "华夏中证红利质量C", "016441", "C"),
        ("华夏中证动漫游戏A", "012768", "A", "华夏中证动漫游戏C", "012769", "C"),
        ("博时黄金ETF联接A", "002610", "A", "博时黄金ETF联接C", "002611", "C"),
        ("招商中证红利A", "018756", "A", "招商中证红利C", "018757", "C"),
    ]

    for a_name, a_code, a_cls, c_name, c_code, c_cls in pairs:
        res_a = fuzzy_match_fund_by_name(a_name)
        res_c = fuzzy_match_fund_by_name(c_name)
        check(f"2.x 区分对: {a_name} ({a_code}) vs {c_name} ({c_code})",
              res_a.get("fund_code") == a_code and res_a.get("share_class") == a_cls and
              res_c.get("fund_code") == c_code and res_c.get("share_class") == c_cls,
              f"got A: {res_a}, got C: {res_c}")

    # 2.13 短别名混合 A/C 区分
    res_gold_short_a = fuzzy_match_fund_by_name("黄金A")
    res_gold_short_c = fuzzy_match_fund_by_name("黄金C")
    check("2.13 短别名 '黄金A' -> 000216, '黄金C' -> 000217",
          res_gold_short_a.get("fund_code") == "000216" and res_gold_short_c.get("fund_code") == "000217",
          f"got A: {res_gold_short_a}, C: {res_gold_short_c}")

    # 2.14 同屏多行同时包含 A 类与 C 类
    t2_multi = """
    华安黄金ETF联接A 1000.00元 盈利50.00
    华安黄金ETF联接C 500.00元 亏损20.00
    """
    r2_multi = parse_smart_text_holdings(t2_multi)
    check("2.14 同屏解析 A 类与 C 类双份合同",
          len(r2_multi) == 2 and
          r2_multi[0]["fund_code"] == "000216" and r2_multi[0]["share_class"] == "A" and
          r2_multi[1]["fund_code"] == "000217" and r2_multi[1]["share_class"] == "C",
          f"got: {r2_multi}")

    # =========================================================================
    # SCENARIO 3: 畸形格式对抗 (Malformed Inputs & Extreme Formatting)
    # =========================================================================
    print("\n[Scenario 3] 畸形格式对抗")

    # 3.1 大额千分位与货币符号
    t3_1 = "易方达裕祥回报债券A 市值: ¥1,234,567.89 持有收益: +¥123,456.78"
    r3_1 = parse_smart_text_holdings(t3_1)
    check("3.1 百万级大额千分位与人民币符号¥",
          len(r3_1) == 1 and abs(r3_1[0]["market_value"] - 1234567.89) < 0.01 and abs(r3_1[0]["floating_pnl"] - 123456.78) < 0.01,
          f"got: {r3_1}")

    # 3.2 负收益多种表达: -¥953.40, 亏损 -500, 浮亏 1234.50
    t3_2a = "华夏科创50C 20000 收益: -¥953.40"
    r3_2a = parse_smart_text_holdings(t3_2a)
    check("3.2a 负收益 '-¥953.40'",
          len(r3_2a) == 1 and abs(r3_2a[0]["floating_pnl"] - (-953.40)) < 0.01,
          f"got: {r3_2a}")

    t3_2b = "华夏科创50C 20000 亏损 -500.00"
    r3_2b = parse_smart_text_holdings(t3_2b)
    check("3.2b 双重负号 '亏损 -500.00' 正确识别为 -500.00",
          len(r3_2b) == 1 and abs(r3_2b[0]["floating_pnl"] - (-500.00)) < 0.01,
          f"got: {r3_2b}")

    t3_2c = "华夏科创50C 20000 浮亏 1,234.50"
    r3_2c = parse_smart_text_holdings(t3_2c)
    check("3.2c 浮亏千分位 '浮亏 1,234.50' 正确识别为 -1234.50",
          len(r3_2c) == 1 and abs(r3_2c[0]["floating_pnl"] - (-1234.50)) < 0.01,
          f"got: {r3_2c}")

    # 3.3 纯数字文本行（无未捕获异常）
    pure_digit_cases = ["123456", "999999", "0.05 34.50", "123", "88888888", "000000"]
    for pdc in pure_digit_cases:
        try:
            res_pd = parse_smart_text_holdings(pdc)
            check(f"3.3 纯数字输入 '{pdc}' 无异常", isinstance(res_pd, list))
        except Exception as e:
            check(f"3.3 纯数字输入 '{pdc}' 抛出未捕获异常", False, str(e))

    # 3.4 换行混乱与破碎块
    t3_4 = "华夏科创50C\n\n\n20000元\n\n亏损\n500元"
    r3_4 = parse_smart_text_holdings(t3_4)
    check("3.4 多换行断裂聚合",
          len(r3_4) == 1 and r3_4[0]["fund_code"] == "011613" and abs(r3_4[0]["market_value"] - 20000.0) < 0.01,
          f"got: {r3_4}")

    # 3.5 复杂特殊标点与表情符号
    t3_5 = "【华夏科创50C】--- 持有金额: 20000.00; 浮盈亏: -500.00 (持有45天)"
    r3_5 = parse_smart_text_holdings(t3_5)
    check("3.5 标点括号干扰识别",
          len(r3_5) == 1 and r3_5[0]["fund_code"] == "011613" and abs(r3_5[0]["market_value"] - 20000.0) < 0.01 and r3_5[0]["holding_days"] == 45,
          f"got: {r3_5}")

    # 3.6 空值与纯标点鲁棒性
    check("3.6a 空字符串安全返回空列表", parse_smart_text_holdings("") == [])
    check("3.6b 纯空格安全返回空列表", parse_smart_text_holdings("   \n\t  ") == [])
    check("3.6c None 安全返回空列表", parse_smart_text_holdings(None) == [])
    check("3.6d 纯分号安全返回空列表", parse_smart_text_holdings(";;;;;；；；") == [])

    # =========================================================================
    # SCENARIO 4: 方法别名与类属性挂载完整性对抗 (Method & Alias Bindings)
    # =========================================================================
    print("\n[Scenario 4] 方法别名与类属性挂载完整性对抗")

    pm = PortfolioManager()
    check("4.1 hasattr(PortfolioManager, 'parse_long_screenshot_holdings')",
          hasattr(PortfolioManager, "parse_long_screenshot_holdings"))
    check("4.2 hasattr(PortfolioManager, 'parse_screenshot_ocr_holdings')",
          hasattr(PortfolioManager, "parse_screenshot_ocr_holdings"))
    check("4.3 callable(pm.parse_long_screenshot_holdings)",
          callable(pm.parse_long_screenshot_holdings))
    check("4.4 callable(pm.parse_screenshot_ocr_holdings)",
          callable(pm.parse_screenshot_ocr_holdings))
    check("4.5 pm.parse_long_screenshot_holdings(b'') == []",
          pm.parse_long_screenshot_holdings(b"") == [])
    check("4.6 parse_long_screenshot_holdings is parse_screenshot_ocr_holdings (module level)",
          parse_long_screenshot_holdings is parse_screenshot_ocr_holdings)

    # =========================================================================
    # SCENARIO 5: 真实多源手机长截图 OCR 模拟文本端到端对抗 (Full Pipeline End-to-End)
    # =========================================================================
    print("\n[Scenario 5] 真实多源手机长截图 OCR 模拟文本端到端对抗")

    ocr_multiline_text = """
    14:30  5G 100%
    我的资产 > 基金持仓
    总资产 26,615.10
    昨日收益 +12.34
    华安黄金ETF联接C
    000217
    昨日收益 +0.50
    持有金额 395.73  持有收益 +16.93
    交易规则  历史业绩
    南方中证新能源ETF联接C
    012832
    昨日收益 -0.05
    持有金额 34.50  持有收益 -15.50
    加自选  去定投
    易方达裕祥回报债券A
    002351
    市值 4,101.71  持有收益 -48.89
    首页  行情  自选  我的
    """
    r5 = parse_smart_text_holdings(ocr_multiline_text)
    check("5.1 复杂多源长截图杂乱文本解析出 3 只基金",
          len(r5) == 3, f"got {len(r5)} items: {[x['fund_code'] for x in r5]}")

    if len(r5) == 3:
        c1, c2, c3 = r5[0], r5[1], r5[2]
        check("5.2 基金1 华安黄金C 代码000217, 市值395.73, 浮盈16.93",
              c1["fund_code"] == "000217" and abs(c1["market_value"] - 395.73) < 0.01 and abs(c1["floating_pnl"] - 16.93) < 0.01)
        check("5.3 基金2 南方新能源C 代码012832, 市值34.50, 浮亏-15.50, 成本50.00",
              c2["fund_code"] == "012832" and abs(c2["market_value"] - 34.50) < 0.01 and abs(c2["floating_pnl"] - (-15.50)) < 0.01 and abs(c2["cost_basis"] - 50.00) < 0.01)
        check("5.4 基金3 裕祥纯债A 代码002351, 市值4101.71, 浮亏-48.89",
              c3["fund_code"] == "002351" and abs(c3["market_value"] - 4101.71) < 0.01 and abs(c3["floating_pnl"] - (-48.89)) < 0.01)

    # =========================================================================
    # SCENARIO 6: 会计恒等式与账本导入一致性对抗 (Accounting Identity & Import)
    # =========================================================================
    print("\n[Scenario 6] 会计恒等式与账本导入一致性对抗")

    import_test_text = """
    005561 创金合信红利低波A 5681.55 收益112.88
    011613 华夏科创50C 2072.52 亏损428.48
    """
    res_import = pm.import_from_smart_text(import_test_text, replace_existing=False)
    check("6.1 import_from_smart_text 导入状态为 SUCCESS",
          res_import.get("status") == "SUCCESS", f"got: {res_import.get('status')}")

    # 验证会话内所有持仓满足 cost_basis = market_value - floating_pnl
    for item in pm.holdings:
        mv = getattr(item, "market_value", getattr(item, "current_value", 0.0))
        cb = getattr(item, "cost_basis", getattr(item, "cost_value", 0.0))
        pnl = getattr(item, "floating_pnl", 0.0)
        # 会计恒等式容差 0.05
        diff = abs(cb - (mv - pnl))
        check(f"6.2 标的 {getattr(item, 'fund_code', '')} 会计恒等式 cost ({cb:.2f}) == mv ({mv:.2f}) - pnl ({pnl:.2f})",
              diff < 0.05, f"diff={diff}")

    print("\n" + "=" * 70)
    print(f"VERIFICATION SUMMARY: {total_passed} PASSED, {total_failed} FAILED")
    if failures:
        print("FAILURES:")
        for f in failures:
            print(f"  - {f}")
    print("=" * 70)

    return total_failed == 0


if __name__ == "__main__":
    success = run_all_adversarial_tests()
    sys.exit(0 if success else 1)
