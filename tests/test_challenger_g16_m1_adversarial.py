# -*- coding: utf-8 -*-
"""
Challenger Adversarial Test Suite for G16 Milestone 1 (M1):
Deep verification of `generate_chief_advisor_memo` and `render_chief_advisor_memo_card`.

Adversarial Stress Scenarios:
1. Real 29-fund combat ledger: deep loss >= 3, specifically naming 011613, 100032, 161725.
2. Tab 1 target weights dictionary: 6-fund, 10-fund, 0.999 sum, 1.001 sum; zero fragments, no ¥1.00 anomaly.
3. Extreme & boundary inputs: None, [], {}, invalid types, zero cost, zero shares, negative mv, extreme pnl (-99.9%, +500%).
4. Object & dict hybrid holdings: FundHolding, HoldingItem, MockLegacyHolding, dicts, batch holding days.
5. Exact fragment boundary and fee-free calculation: 005827 (¥124.14) excluded, 19 fragments exactly ¥442.70.
6. GUI 1-row-5-col responsive grid rendering & CommonMark 4-space markdown safety.
"""

import pytest
from unittest.mock import patch
from typing import Dict, Any, List

from AGY2_FundAdvisory.advisory_engine import (
    generate_chief_advisor_memo,
    get_chief_advisor_memo,
    ActiveRiskSentry,
)
from AGY2_FundAdvisory.portfolio_manager import FundHolding, HoldingItem
from AGY2_FundAdvisory.multi_ledger_manager import MultiLedgerManager
from AGY2_FundAdvisory.app_gui import (
    render_chief_advisor_memo_card,
    safe_markdown_html,
    _clean_html,
)


class MockLegacyCostValueHolding:
    """Legacy mock object using cost_value attribute instead of cost_basis."""
    def __init__(self, name: str, code: str, mv: float, cost_val: float, days: int = 400, s_class: str = "A"):
        self.fund_name = name
        self.fund_code = code
        self.market_value = mv
        self.cost_value = cost_val
        self.holding_days = days
        self.share_class = s_class


class MockBatchItem:
    """Mock batch item for holding days resolution."""
    def __init__(self, holding_days: int):
        self.holding_days = holding_days


class MockBatchedHolding:
    """Mock holding object whose holding days are resolved via batches."""
    def __init__(self, name: str, code: str, mv: float, batches: list, s_class: str = "A"):
        self.fund_name = name
        self.fund_code = code
        self.market_value = mv
        self.batches = batches
        self.share_class = s_class


class TestChallengerG16M1Adversarial:
    """Adversarial stress and boundary test suite for Chief Advisor Memo."""

    def test_01_combat_29_funds_deep_loss_and_fragments(self):
        """Scenario 1: Real 29-fund ledger assertion.
        - deep_loss_count >= 3 (actual 18)
        - Bleeding points explicitly name 011613, 100032, 161725
        - Exact 19 fee-free fragments totaling ¥442.70 (005827 excluded)
        """
        mlm = MultiLedgerManager()
        pm = mlm.get_pm("combat_29_funds")
        assert len(pm.holdings) == 29

        memo = generate_chief_advisor_memo(holdings=pm.holdings)
        pathology = memo["portfolio_pathology"]

        # Deep loss check
        assert pathology["deep_loss_count"] >= 3
        content = pathology["content"]
        assert "核心亏损拖累源" in content
        # Check top 3 bleeding points by name or code
        assert ("011613" in content or "科创板50" in content)
        assert ("100032" in content or "红利指数增强" in content)
        assert ("161725" in content or "白酒" in content)

        # 19 fragments totaling ¥442.70
        assert pathology["frag_count"] == 19
        assert abs(pathology["frag_amt"] - 442.70) < 0.001
        assert "长尾碎片尾仓" in content
        assert "¥442.70" in content

        # Verify #10 005827 易方达蓝筹精选混合 (¥124.14, A class) is NOT included in fragments
        # 124.14 is between 100 and 200, but is A class and active equity -> excluded
        all_tail_sum = pathology["frag_amt"]
        assert abs(all_tail_sum - (442.70 + 124.14)) > 50.0  # definitely does not include 124.14

    def test_02_tab1_target_weights_dict_adversarial_suite(self):
        """Scenario 2: Tab 1 Target Weights Dict variations.
        - 6 funds (standard)
        - 10 funds
        - sum = 0.999 (float truncation)
        - sum = 1.001 (float excess)
        - sum = 0.96 and sum = 1.04 (within 0.05 tolerance)
        Assert:
        - deep_loss_count == 0
        - frag_count == 0, frag_amt == 0.0
        - No '¥1.00' or '合计 ¥1.00' text
        - No '长尾碎片尾仓' or '碎片/羊毛基' bullet points
        - Title is '📐 拟建仓组合结构校验', badge is '🟢 结构均衡'
        """
        weight_cases = [
            # Standard 6-fund allocation
            {"005561": 0.35, "002351": 0.20, "110020": 0.15, "011613": 0.15, "017436": 0.10, "000216": 0.05},
            # 10-fund equal weight allocation
            {f"00000{i}": 0.10 for i in range(10)},
            # 3-fund sum = 0.999
            {"001": 0.333, "002": 0.333, "003": 0.333},
            # 3-fund sum = 1.001
            {"001": 0.334, "002": 0.334, "003": 0.333},
            # 2-fund sum = 0.96 (tolerance edge)
            {"001": 0.48, "002": 0.48},
            # 2-fund sum = 1.04 (tolerance edge)
            {"001": 0.52, "002": 0.52},
        ]

        for idx, weights in enumerate(weight_cases):
            memo = generate_chief_advisor_memo(holdings=weights, total_capital=100000.0)
            p = memo["portfolio_pathology"]

            assert p["deep_loss_count"] == 0, f"Case {idx} reported deep_loss_count={p['deep_loss_count']}"
            assert p["frag_count"] == 0, f"Case {idx} reported frag_count={p['frag_count']}"
            assert p["frag_amt"] == 0.0, f"Case {idx} reported frag_amt={p['frag_amt']}"

            # Must never contain ridiculous ¥1.00 text
            assert "¥1.00" not in p["content"], f"Case {idx} contained ¥1.00"
            assert "合计 ¥1.00" not in p["content"], f"Case {idx} contained 合计 ¥1.00"
            assert "长尾碎片尾仓" not in p["content"], f"Case {idx} contained 长尾碎片尾仓"
            assert "碎片/羊毛基" not in p["content"], f"Case {idx} contained 碎片/羊毛基"

            # Must contain construction mode markers
            assert p["title"] == "📐 拟建仓组合结构校验"
            assert p["badge"] == "🟢 结构均衡"
            assert "建仓标的" in p["content"]
            assert "攻防配比" in p["content"]
            assert "分散度" in p["content"]

    def test_03_empty_and_null_boundary_inputs(self):
        """Scenario 3: Null, empty, and invalid type inputs without crashing."""
        test_inputs = [
            None,
            [],
            {},
            "invalid_string_input",
            123456,
            [None],
        ]

        for inp in test_inputs:
            memo = generate_chief_advisor_memo(holdings=inp)
            assert isinstance(memo, dict)
            assert "portfolio_pathology" in memo
            p = memo["portfolio_pathology"]
            assert p["deep_loss_count"] == 0
            assert p["frag_count"] == 0
            assert p["frag_amt"] == 0.0
            assert p["badge"] == "🟢 健康良好"
            assert "持仓结构优良" in p["content"]

    def test_04_deformed_holding_values_resilience(self):
        """Scenario 4: Malformed and boundary holding values:
        - cost_basis = 0
        - shares = 0
        - negative market value
        - zero market value
        - extreme drawdown (-99.9%)
        - extreme gain (+500.0%)
        - cost reverse-engineering from mv & floating_pnl_pct
        """
        deformed_items = [
            # 1. Zero cost basis
            HoldingItem(fund_code="001", fund_name="零成本基", share_class="A", shares=100.0, cost_price=0.0, current_nav=1.0, market_value=100.0, cost_basis=0.0),
            # 2. Zero shares
            HoldingItem(fund_code="002", fund_name="零份额基", share_class="A", shares=0.0, cost_price=1.0, current_nav=1.0, market_value=0.0, cost_basis=100.0),
            # 3. Negative market value
            HoldingItem(fund_code="003", fund_name="负市值基", share_class="A", shares=100.0, cost_price=1.0, current_nav=0.5, market_value=-50.0, cost_basis=100.0),
            # 4. Deep collapse (-99.9%)
            HoldingItem(fund_code="004", fund_name="深度爆仓基", share_class="A", shares=1000.0, cost_price=10.0, current_nav=0.01, market_value=10.0, cost_basis=10000.0, floating_pnl=-9990.0, floating_pnl_pct=-99.9),
            # 5. Huge profit (+500.0%)
            HoldingItem(fund_code="005", fund_name="翻五倍牛基", share_class="A", shares=1000.0, cost_price=1.0, current_nav=6.0, market_value=6000.0, cost_basis=1000.0, floating_pnl=5000.0, floating_pnl_pct=500.0),
            # 6. Reverse-engineered cost: cost_basis=0, but mv=800 and floating_pnl_pct=-20.0%, floating_pnl=-200.0
            HoldingItem(fund_code="006", fund_name="反推成本基", share_class="A", shares=1000.0, cost_price=0.0, current_nav=0.8, market_value=800.0, cost_basis=0.0, floating_pnl=-200.0, floating_pnl_pct=-20.0),
        ]

        memo = generate_chief_advisor_memo(holdings=deformed_items)
        p = memo["portfolio_pathology"]

        # 004 (-99.9%) and 006 (-20.0%) must be detected as deep losses
        assert p["deep_loss_count"] >= 2
        assert "深度爆仓基" in p["content"]
        assert "反推成本基" in p["content"]
        assert "翻五倍牛基" not in p["content"]  # profitable fund must not be in loss list

    def test_05_hybrid_object_and_dict_holdings_list(self):
        """Scenario 5: Mixed types in a single holdings list:
        - HoldingItem instance
        - MockLegacyCostValueHolding (cost_value only)
        - Plain dict with cost_price and shares
        - Batched holding with min(batch.holding_days)
        - Locked C-class holding (15 days < 30 days) -> excluded from fee-free fragments
        - Fee-free C-class holding (35 days >= 30 days) -> included in fee-free fragments
        - Locked A-class holding (200 days < 365 days) -> excluded
        - Fee-free A-class holding (400 days >= 365 days) -> included
        """
        h_locked_c = HoldingItem(fund_code="001", fund_name="锁定C类尾仓", share_class="C", shares=10.0, cost_price=1.0, current_nav=1.0, market_value=10.0, cost_basis=10.0)
        h_locked_c.holding_days = 15  # < 30 days

        h_freed_c = HoldingItem(fund_code="002", fund_name="免赎C类尾仓", share_class="C", shares=20.0, cost_price=1.0, current_nav=1.0, market_value=20.0, cost_basis=20.0)
        h_freed_c.holding_days = 35   # >= 30 days

        h_locked_a = HoldingItem(fund_code="003", fund_name="锁定A类尾仓", share_class="A", shares=30.0, cost_price=1.0, current_nav=1.0, market_value=30.0, cost_basis=30.0)
        h_locked_a.holding_days = 200  # < 365 days

        h_freed_a = HoldingItem(fund_code="004", fund_name="免赎A类尾仓", share_class="A", shares=40.0, cost_price=1.0, current_nav=1.0, market_value=40.0, cost_basis=40.0)
        h_freed_a.holding_days = 400  # >= 365 days

        h_legacy_deep = MockLegacyCostValueHolding("老式深套基", "005", mv=100.0, cost_val=200.0, days=400, s_class="A")  # -50% deep loss

        h_dict_fragment = {
            "fund_code": "006",
            "fund_name": "字典免赎尾仓",
            "market_value": 50.0,
            "cost_price": 1.0,
            "shares": 50.0,
            "share_class": "C",
            "holding_days": 60,
        }

        h_batched = MockBatchedHolding(
            name="批次免赎尾仓",
            code="007",
            mv=60.0,
            batches=[MockBatchItem(holding_days=500), MockBatchItem(holding_days=450)],
            s_class="A"
        )

        holdings_list = [
            h_locked_c, h_freed_c, h_locked_a, h_freed_a,
            h_legacy_deep, h_dict_fragment, h_batched
        ]

        memo = generate_chief_advisor_memo(holdings=holdings_list)
        p = memo["portfolio_pathology"]

        # Deep loss check: h_legacy_deep (mv 100 vs cost 200 = -50%)
        assert p["deep_loss_count"] >= 1
        assert "老式深套基" in p["content"]

        # Fragment check:
        # h_freed_c: 20.0
        # h_freed_a: 40.0
        # h_dict_fragment: 50.0
        # h_batched: 60.0
        # Locked ones (h_locked_c: 10, h_locked_a: 30) must be EXCLUDED!
        # Legacy deep (mv=100, A class, active name, >= 100) -> excluded
        expected_frag_count = 4
        expected_frag_amt = 20.0 + 40.0 + 50.0 + 60.0  # 170.0
        assert p["frag_count"] == expected_frag_count
        assert abs(p["frag_amt"] - expected_frag_amt) < 0.01

    def test_06_fragment_exclusion_rules_boundary_matrix(self):
        """Scenario 6: Precise testing of fragment identification boundary:
        - mv < 100: any fund name, any share class -> fragment
        - 100 <= mv < 200:
          * C class -> fragment
          * A class with keyword ('联接', 'ETF', '指数', '红包', '体验', '尾仓', '碎片') -> fragment
          * A class active equity (e.g. '005827 易方达蓝筹精选混合') -> NOT fragment
        - mv >= 200: never fragment
        """
        cases = [
            # mv < 100: unconditionally fragment
            (HoldingItem("001", "某主动混合A", "A", 10.0, 1.0, 1.0, 99.9, 100.0), 400, True),
            # 100 <= mv < 200, C class: fragment
            (HoldingItem("002", "某主动混合C", "C", 100.0, 1.0, 1.0, 150.0, 150.0), 40, True),
            # 100 <= mv < 200, A class with '联接': fragment
            (HoldingItem("003", "易方达沪深300ETF联接A", "A", 100.0, 1.0, 1.0, 120.0, 120.0), 400, True),
            # 100 <= mv < 200, A class with '指数': fragment
            (HoldingItem("004", "富国中证红利指数A", "A", 100.0, 1.0, 1.0, 130.0, 130.0), 400, True),
            # 100 <= mv < 200, A class active equity WITHOUT keywords: NOT fragment (like 005827)
            (HoldingItem("005827", "易方达蓝筹精选混合", "A", 100.0, 1.0, 1.0, 124.14, 148.0), 400, False),
            # mv == 200.0 boundary: NOT fragment
            (HoldingItem("005", "测试边界200", "C", 100.0, 1.0, 1.0, 200.0, 200.0), 400, False),
            # mv == 200.01: NOT fragment
            (HoldingItem("006", "测试超额200", "C", 100.0, 1.0, 1.0, 200.01, 200.0), 400, False),
        ]

        for item, days, expected_frag in cases:
            item.holding_days = days
            memo = generate_chief_advisor_memo(holdings=[item])
            p = memo["portfolio_pathology"]
            if expected_frag:
                assert p["frag_count"] == 1, f"Failed for {item.fund_name} (mv={item.market_value}): expected fragment"
            else:
                assert p["frag_count"] == 0, f"Failed for {item.fund_name} (mv={item.market_value}): expected NOT fragment"

    def test_07_macro_intl_action_dimensions_and_us_spread(self):
        """Scenario 7: Full 5-dimension coverage under diverse market snapshot conditions."""
        # 1. High liquidity tightness & high ERP
        snap_tight = {
            "treasury_10y": 1.65,
            "us_treasury_10y": 4.45,
            "dr007": 1.85,
            "dr007_spread_bp": 45.0,  # > 35 bp -> tight
            "erp_percentile": 82.5,   # > 75% -> gold strike zone
            "erp_val": 6.80,
            "bias_20": -2.5,          # negative bias
            "spot_usdcnh": 7.2550,
        }
        memo_tight = generate_chief_advisor_memo(snapshot=snap_tight)
        assert memo_tight["macro_policy"]["badge"] == "🔴 资金边际收紧"
        assert "极高性价比黄金击球区" in memo_tight["macro_policy"]["content"]
        assert "逆向定投吸筹" in memo_tight["action_directive"]["verdict"]

        # 2. Easy liquidity & low ERP (overbought)
        snap_easy = {
            "treasury_10y": 1.55,
            "us_treasury_10y": 4.30,
            "dr007": 1.30,
            "dr007_spread_bp": 5.0,   # <= 15 bp -> easy
            "erp_percentile": 25.0,   # <= 35% -> cautious
            "erp_val": 3.20,
            "bias_20": 6.8,           # > 5.0 -> overbought
            "spot_usdcnh": 7.2300,
        }
        memo_easy = generate_chief_advisor_memo(snapshot=snap_easy)
        assert memo_easy["macro_policy"]["badge"] == "🟢 货币宽松充裕"
        assert "高估谨慎区" in memo_easy["macro_policy"]["content"]
        assert "逢高适度止盈" in memo_easy["action_directive"]["verdict"]

        # 3. Sino-US yield spread verification
        intl = memo_tight["international_fx"]
        assert "中美 10Y 国债利差深度倒挂" in intl["content"]
        assert "-280.0 bp" in intl["content"] or "中债 1.65% vs 美债 4.45%" in intl["content"]

    def test_08_gui_rendering_and_commonmark_safety_stress(self):
        """Scenario 8: GUI rendering of memo cards under combat and construction modes:
        - CommonMark 4-space markdown safety (Rule 27 compliance)
        - 1-row-5-col responsive grid styles
        - Zero exceptions during rendering
        """
        mlm = MultiLedgerManager()
        pm = mlm.get_pm("combat_29_funds")
        memo_combat = generate_chief_advisor_memo(holdings=pm.holdings)

        # 1. Test combat memo rendering
        with patch("streamlit.markdown") as mock_st_md:
            render_chief_advisor_memo_card(memo_combat, title="🧭 首席投顾五维全息决策备忘录")
            assert mock_st_md.called
            call_html = mock_st_md.call_args[0][0]

            # CommonMark safety verification
            for line_idx, line in enumerate(call_html.splitlines()):
                assert not line.startswith("    "), f"Combat HTML line {line_idx} starts with 4 spaces: {line}"
                assert not line.startswith("\t"), f"Combat HTML line {line_idx} starts with tab: {line}"

            # 1-row-5-col responsive grid verification
            assert "grid-template-columns: repeat(5, minmax(0, 1fr));" in call_html
            assert "@media (max-width: 768px)" in call_html
            assert "repeat(auto-fit, minmax(180px, 1fr))" in call_html

            # Verify all 5 cards present
            assert "🏛️ 宏观与政策面" in call_html
            assert "🌐 国际与汇率面" in call_html
            assert "📈 产业与估值面" in call_html
            assert "🩺 存量持仓病灶" in call_html
            assert "🎯 今日行动准则" in call_html

        # 2. Test Tab 1 construction mode memo rendering
        opt_weights = {"005561": 0.35, "002351": 0.20, "110020": 0.15, "011613": 0.15, "017436": 0.10, "000216": 0.05}
        memo_t1 = generate_chief_advisor_memo(holdings=opt_weights, total_capital=100000.0)

        with patch("streamlit.markdown") as mock_st_md:
            render_chief_advisor_memo_card(memo_t1, title="🧭 拟建仓方案研判")
            assert mock_st_md.called
            call_html_t1 = mock_st_md.call_args[0][0]

            for line_idx, line in enumerate(call_html_t1.splitlines()):
                assert not line.startswith("    "), f"T1 HTML line {line_idx} starts with 4 spaces: {line}"
                assert not line.startswith("\t"), f"T1 HTML line {line_idx} starts with tab: {line}"

            assert "📐 拟建仓组合结构校验" in call_html_t1
            assert "🟢 结构均衡" in call_html_t1
            assert "建仓标的" in call_html_t1
            assert "¥1.00" not in call_html_t1
            assert "合计 ¥1.00" not in call_html_t1
