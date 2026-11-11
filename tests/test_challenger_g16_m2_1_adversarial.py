# -*- coding: utf-8 -*-
"""
Empirical Adversarial Verification Suite for Milestone 2 (M2):
"portfolio_manager.py 智能文本解析与模糊匹配对抗性验证"

Executed by: teamwork_challenger (instance: challenger_m2_1)
Target: AGY2_FundAdvisory/portfolio_manager.py

Test Dimensions:
1. 昨日收益干扰与高位截断对抗 (Yesterday Earnings Interference)
2. 多份额（A/C/E）及同名别名 100% 精准区分对抗
3. 畸形格式输入与零未捕获异常鲁棒性对抗 (Malformed & Stress Inputs)
4. 方法别名与类属性挂载完整性对抗 (Alias & Method Bindings)
5. 端到端会计恒等式平账校验 (Accounting Identity & Import)
6. 只读裁判文件物理安全红线审计 (Referee Integrity)
"""
import pytest
import re
import subprocess
from pathlib import Path
from typing import Dict, Any, List

from AGY2_FundAdvisory.portfolio_manager import (
    PortfolioManager,
    parse_smart_text_holdings,
    fuzzy_match_fund_by_name,
    parse_screenshot_ocr_holdings,
    parse_long_screenshot_holdings,
    search_funds_in_catalog,
)


# =========================================================================
# 1. 昨日收益干扰对抗 (Scenario 1)
# =========================================================================
class TestYesterdayEarningsInterference:
    """验证包含多位数、正负号、千分位及不同标签的昨日收益文本绝不干扰基金识别与金额"""

    def test_yesterday_earnings_with_explicit_holding_amount(self):
        """1.1 明确持有金额 1000 与昨日收益 +0.05 34.50 共存，昨日收益不被截断且不被误认为代码"""
        text = "南方中证新能源ETF联接C \n 昨日收益 +0.05 34.50 \n 持有收益 -15.50 持有金额 1000.00"
        res = parse_smart_text_holdings(text)
        assert len(res) == 1, f"Expected 1 item, got {len(res)}"
        item = res[0]
        assert item["fund_code"] == "012832"
        assert item["share_class"] == "C"
        assert abs(item["market_value"] - 1000.00) < 0.01
        assert abs(item["floating_pnl"] - (-15.50)) < 0.01

    def test_yesterday_earnings_tail_fragment_value_preserved(self):
        """1.2 尾部零头市值 34.50 与昨日收益 +0.05 共存，数值不被截断，成本满足平账"""
        text = "南方中证新能源ETF联接C \n 昨日收益 +0.05  34.50 \n 持有收益 -15.50  持有金额"
        res = parse_smart_text_holdings(text)
        assert len(res) == 1
        item = res[0]
        assert item["fund_code"] == "012832"
        assert item["share_class"] == "C"
        assert abs(item["market_value"] - 34.50) < 0.01
        assert abs(item["floating_pnl"] - (-15.50)) < 0.01
        assert abs(item["cost_basis"] - 50.00) < 0.01

    def test_yesterday_earnings_negative_multi_digit(self):
        """1.3 负昨日收益 -123.45 与市值 395.73，精准匹配华安黄金C (000217)"""
        text = "华安黄金ETF联接C 昨日收益 -123.45 市值 395.73 持有收益 +16.93"
        res = parse_smart_text_holdings(text)
        assert len(res) == 1
        item = res[0]
        assert item["fund_code"] == "000217"
        assert item["share_class"] == "C"
        assert abs(item["market_value"] - 395.73) < 0.01
        assert abs(item["floating_pnl"] - 16.93) < 0.01

    def test_yesterday_earnings_five_digits_large_number(self):
        """1.4 五位数大额昨日收益 (+12345.67) 不被误认为基金代码"""
        text = "易方达裕祥回报债券A 昨日收益 +12345.67 持有金额 50000.00 盈利 1500.00"
        res = parse_smart_text_holdings(text)
        assert len(res) == 1
        item = res[0]
        assert item["fund_code"] == "002351"
        assert item["share_class"] == "A"
        assert abs(item["market_value"] - 50000.00) < 0.01
        assert abs(item["floating_pnl"] - 1500.00) < 0.01

    def test_yesterday_earnings_with_commas_and_colons(self):
        """1.5 千分位昨日收益 +1,234.56 与千分位资产 20,000.00"""
        text = "华夏科创50C 昨日收益: +1,234.56 持有资产 20,000.00 亏损 500.00"
        res = parse_smart_text_holdings(text)
        assert len(res) == 1
        item = res[0]
        assert item["fund_code"] == "011613"
        assert item["share_class"] == "C"
        assert abs(item["market_value"] - 20000.00) < 0.01
        assert abs(item["floating_pnl"] - (-500.00)) < 0.01

    def test_yesterday_earnings_label_variants(self):
        """1.6 别名标签 '昨日盈亏' 与 '日收益' 均被彻底剥离"""
        text_a = "富国中证红利C 昨日盈亏 -88.88 市值 10000.00 浮盈 500.00"
        res_a = parse_smart_text_holdings(text_a)
        assert len(res_a) == 1
        assert res_a[0]["fund_code"] == "008682"
        assert res_a[0]["share_class"] == "C"
        assert abs(res_a[0]["market_value"] - 10000.00) < 0.01
        assert abs(res_a[0]["floating_pnl"] - 500.00) < 0.01

        text_b = "博时标普500ETF联接A 日收益 +12.34 金额 5000.00 收益 250.00"
        res_b = parse_smart_text_holdings(text_b)
        assert len(res_b) == 1
        assert res_b[0]["fund_code"] == "050025"
        assert res_b[0]["share_class"] == "A"
        assert abs(res_b[0]["market_value"] - 5000.00) < 0.01
        assert abs(res_b[0]["floating_pnl"] - 250.00) < 0.01

    def test_yesterday_earnings_inline_adjacent_no_newline(self):
        """1.7 昨日收益与市值紧贴连写无换行"""
        text = "华安黄金ETF联接C 昨日收益 +0.50 395.73 持有收益 +16.93"
        res = parse_smart_text_holdings(text)
        assert len(res) == 1
        assert res[0]["fund_code"] == "000217"
        assert abs(res[0]["market_value"] - 395.73) < 0.01
        assert abs(res[0]["floating_pnl"] - 16.93) < 0.01


# =========================================================================
# 2. 多份额与同名别名对抗 (Scenario 2)
# =========================================================================
class TestShareClassDiscrimination:
    """检验 A/C/E 份额及同名同源基金是否 100% 区分正确"""

    @pytest.mark.parametrize("a_name,a_code,c_name,c_code", [
        ("华安黄金ETF联接A", "000216", "华安黄金ETF联接C", "000217"),
        ("易方达沪深300ETF联接A", "110020", "易方达沪深300ETF联接C", "007339"),
        ("富国中证红利指数增强A", "100032", "富国中证红利指数增强C", "008682"),
        ("华夏科创50ETF联接A", "011612", "华夏科创50ETF联接C", "011613"),
        ("南方中证新能源ETF联接A", "012831", "南方中证新能源ETF联接C", "012832"),
        ("银华集成电路混合A", "013840", "银华集成电路混合C", "013841"),
        ("富国中证1000ETF联接A", "016633", "富国中证1000ETF联接C", "016634"),
        ("华夏中证500ETF联接A", "001052", "华夏中证500ETF联接C", "001053"),
        ("华夏中证红利质量A", "016440", "华夏中证红利质量C", "016441"),
        ("华夏中证动漫游戏A", "012768", "华夏中证动漫游戏C", "012769"),
        ("招商中证红利A", "018756", "招商中证红利C", "018757"),
        ("易方达裕祥A", "002351", "易方达裕祥C", "002352"),
    ])
    def test_ac_pairs_discrimination(self, a_name, a_code, c_name, c_code):
        """核心策略池与实战存量 A/C 对 100% 精确区分"""
        res_a = fuzzy_match_fund_by_name(a_name)
        res_c = fuzzy_match_fund_by_name(c_name)
        assert res_a.get("fund_code") == a_code, f"Failed for {a_name}: got {res_a}"
        assert res_a.get("share_class") == "A"
        assert res_c.get("fund_code") == c_code, f"Failed for {c_name}: got {res_c}"
        assert res_c.get("share_class") == "C"

    def test_short_alias_gold_ac(self):
        """短别名 '黄金A' 与 '黄金C' 区分"""
        res_a = fuzzy_match_fund_by_name("黄金A")
        res_c = fuzzy_match_fund_by_name("黄金C")
        assert res_a.get("fund_code") == "000216"
        assert res_a.get("share_class") == "A"
        assert res_c.get("fund_code") == "000217"
        assert res_c.get("share_class") == "C"

    def test_dual_contract_same_screen_parsing(self):
        """同屏多行同时包含同一基金的 A 类与 C 类持仓"""
        text = """
        华安黄金ETF联接A 1000.00元 盈利50.00
        华安黄金ETF联接C 500.00元 亏损20.00
        """
        res = parse_smart_text_holdings(text)
        assert len(res) == 2
        assert res[0]["fund_code"] == "000216"
        assert res[0]["share_class"] == "A"
        assert abs(res[0]["market_value"] - 1000.00) < 0.01

        assert res[1]["fund_code"] == "000217"
        assert res[1]["share_class"] == "C"
        assert abs(res[1]["market_value"] - 500.00) < 0.01

    def test_e_share_or_general_catalog_funds_non_crashing(self):
        """E 类份额或全量库基金输入不抛出异常"""
        e_names = ["天弘中证500指数E", "广发中证500E", "易方达沪深300ETF联接E"]
        for en in e_names:
            res = fuzzy_match_fund_by_name(en)
            assert isinstance(res, dict)


# =========================================================================
# 3. 畸形格式对抗 (Scenario 3)
# =========================================================================
class TestMalformedFormatAndStressInputs:
    """输入大额千分位、负收益、纯数字、破碎换行，验证系统 0 未捕获异常"""

    def test_large_number_with_commas(self):
        """百万级大额千分位数字"""
        text = "易方达裕祥回报债券A 市值: 1,234,567.89 持有收益: 123,456.78"
        res = parse_smart_text_holdings(text)
        assert len(res) == 1
        assert abs(res[0]["market_value"] - 1234567.89) < 0.01
        assert abs(res[0]["floating_pnl"] - 123456.78) < 0.01

    def test_negative_profits_expressions(self):
        """负收益各种表达: 亏损 -500.00, 浮亏 1,234.50"""
        t1 = "华夏科创50C 20000 亏损 -500.00"
        r1 = parse_smart_text_holdings(t1)
        assert len(r1) == 1
        assert abs(r1[0]["floating_pnl"] - (-500.00)) < 0.01

        t2 = "华夏科创50C 20000 浮亏 1,234.50"
        r2 = parse_smart_text_holdings(t2)
        assert len(r2) == 1
        assert abs(r2[0]["floating_pnl"] - (-1234.50)) < 0.01

    def test_pure_numeric_inputs_safety(self):
        """纯数字文本行输入不抛出任何未捕获异常"""
        cases = ["123456", "999999", "0.05 34.50", "123", "88888888", "000000", "0.0"]
        for c in cases:
            res = parse_smart_text_holdings(c)
            assert isinstance(res, list)

    def test_punctuation_and_emojis(self):
        """特殊符号与标点干扰"""
        text = "【华夏科创50C】--- 持有金额: 20000.00; 浮盈亏: -500.00 (持有45天)"
        res = parse_smart_text_holdings(text)
        assert len(res) == 1
        assert res[0]["fund_code"] == "011613"
        assert abs(res[0]["market_value"] - 20000.00) < 0.01
        assert res[0]["holding_days"] == 45

    def test_empty_and_whitespace_inputs(self):
        """空值、纯空格、None、纯标点安全兜底"""
        assert parse_smart_text_holdings("") == []
        assert parse_smart_text_holdings("   \n\t  ") == []
        assert parse_smart_text_holdings(None) == []
        assert parse_smart_text_holdings(";;;;;；；；") == []
        assert parse_smart_text_holdings("？？？！！！") == []


# =========================================================================
# 4. 方法别名与类属性挂载完整性对抗 (Scenario 4)
# =========================================================================
class TestMethodAndAliasBindings:
    """验证 parse_long_screenshot_holdings 方法别名挂载与调用安全性"""

    def test_portfolio_manager_has_alias(self):
        pm = PortfolioManager()
        assert hasattr(PortfolioManager, "parse_long_screenshot_holdings"), "PortfolioManager must have parse_long_screenshot_holdings"
        assert hasattr(PortfolioManager, "parse_screenshot_ocr_holdings"), "PortfolioManager must have parse_screenshot_ocr_holdings"
        assert callable(pm.parse_long_screenshot_holdings)
        assert callable(pm.parse_screenshot_ocr_holdings)
        assert pm.parse_long_screenshot_holdings(b"") == []

    def test_module_level_alias(self):
        assert parse_long_screenshot_holdings is parse_screenshot_ocr_holdings
        assert parse_long_screenshot_holdings(b"") == []


# =========================================================================
# 5. 端到端会计恒等式与入库校验 (Scenario 5)
# =========================================================================
class TestAccountingIdentityAndImport:
    """验证识别结果满足会计恒等式 cost_basis = market_value - floating_pnl"""

    def test_accounting_identity_on_import(self, tmp_path):
        ledger_temp = tmp_path / "temp_ledger.json"
        db_temp = tmp_path / "temp.db"
        pm = PortfolioManager(db_path=str(db_temp), ledger_file=str(ledger_temp))
        text = """
        005561 创金合信红利低波A 5681.55 收益112.88
        011613 华夏科创50C 2072.52 亏损428.48
        000217 华安黄金C 395.73 盈利16.93
        """
        import_res = pm.import_from_smart_text(text, replace_existing=True)
        assert import_res.get("status") == "SUCCESS"
        assert len(pm.holdings) == 3

        for h in pm.holdings:
            mv = getattr(h, "market_value", getattr(h, "current_value", 0.0))
            cb = getattr(h, "cost_basis", getattr(h, "cost_value", 0.0))
            pnl = getattr(h, "floating_pnl", 0.0)
            assert abs(cb - (mv - pnl)) < 0.05, f"Accounting identity failed for {h.fund_code}: cb={cb}, mv={mv}, pnl={pnl}"


# =========================================================================
# 6. 只读裁判文件物理安全红线审计 (Scenario 6)
# =========================================================================
class TestRefereeIntegrity:
    """物理只读红线审计：4 个裁判文件严禁被修改"""

    def test_referee_files_untouched(self):
        cmd = ["git", "status", "--porcelain", "judge_engine.py", "holdout_vault.py", "AGENT_SPEC.md", "tests/test_infra.py"]
        res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(Path(__file__).parent.parent))
        assert res.returncode == 0
        assert res.stdout.strip() == "", f"Referee files modified: {res.stdout}"
