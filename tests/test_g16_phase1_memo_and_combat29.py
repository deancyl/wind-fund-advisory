# -*- coding: utf-8 -*-
"""
G16 Milestone 1 (M1) Comprehensive Verification Suite:
- Chief Advisor Memo (`generate_chief_advisor_memo`) multi-field cost and deep-loss compatibility
- 29-fund combat ledger (`combat_29_funds`) deep loss >= 3 (011613, 100032, 161725) and 19 fragments (¥442.70)
- Tab 1 target weights dictionary protection (0 fragments, no ¥1.00 anomaly, structural check)
- Chief Advisor Memo Card GUI (`render_chief_advisor_memo_card`) 1-row-5-col responsive grid & CommonMark 4-space safety
"""

import pytest
from unittest.mock import patch
from typing import Dict, Any

from AGY2_FundAdvisory.advisory_engine import (
    generate_chief_advisor_memo,
    get_chief_advisor_memo,
    ActiveRiskSentry,
    OpportunityRadarEngine,
)
from AGY2_FundAdvisory.portfolio_manager import FundHolding, HoldingItem
from AGY2_FundAdvisory.multi_ledger_manager import MultiLedgerManager
from AGY2_FundAdvisory.app_gui import (
    render_chief_advisor_memo_card,
    safe_markdown_html,
    _clean_html,
)


class TestG16M1ChiefAdvisorMemo:
    """M1 Unit Tests for Chief Advisor Memo Engine."""

    def test_fund_holding_objects_deep_loss_detection(self):
        """Verify HoldingItem / FundHolding objects with cost_basis & floating_pnl_pct identify deep losses."""
        h1 = HoldingItem(
            fund_code="011613",
            fund_name="华夏上证科创板50成份ETF联接C",
            share_class="C",
            shares=2000.0,
            cost_price=1.2505,
            current_nav=1.0363,
            market_value=2072.52,
            cost_basis=2501.00,
            floating_pnl=-428.48,
            floating_pnl_pct=-17.13,
        )
        h1.holding_days = 400

        h2 = HoldingItem(
            fund_code="100032",
            fund_name="富国中证红利指数增强A",
            share_class="A",
            shares=2400.0,
            cost_price=1.1523,
            current_nav=1.0137,
            market_value=2432.90,
            cost_basis=2765.44,
            floating_pnl=-332.54,
            floating_pnl_pct=-12.02,
        )
        h2.holding_days = 400

        h3 = HoldingItem(
            fund_code="161725",
            fund_name="招商中证白酒指数(LOF)A",
            share_class="A",
            shares=500.0,
            cost_price=1.4000,
            current_nav=1.0485,
            market_value=524.24,
            cost_basis=700.00,
            floating_pnl=-175.76,
            floating_pnl_pct=-25.11,
        )
        h3.holding_days = 400

        h4 = HoldingItem(
            fund_code="005561",
            fund_name="创金合信中证红利低波动指数A",
            share_class="A",
            shares=5000.0,
            cost_price=1.1137,
            current_nav=1.1363,
            market_value=5681.55,
            cost_basis=5568.49,
            floating_pnl=113.06,
            floating_pnl_pct=2.03,
        )
        h4.holding_days = 400

        holdings = [h1, h2, h3, h4]

        memo = generate_chief_advisor_memo(holdings=holdings)
        pathology = memo["portfolio_pathology"]

        assert pathology["deep_loss_count"] >= 3
        assert "核心亏损拖累源" in pathology["content"]
        assert "华夏上证科创板50成份ETF联接C" in pathology["content"]
        assert "富国中证红利指数增强A" in pathology["content"]
        assert "招商中证白酒指数(LOF)A" in pathology["content"]
        assert "浮亏 -17.1%" in pathology["content"]
        assert pathology["frag_count"] == 0

    def test_combat_29_funds_real_ledger_full_inspection(self):
        """Verify real combat 29-fund ledger detects deep_loss_count >= 3 and exactly 19 fee-free fragments (¥442.70)."""
        mlm = MultiLedgerManager()
        pm = mlm.get_pm("combat_29_funds")
        assert len(pm.holdings) == 29

        memo = generate_chief_advisor_memo(holdings=pm.holdings)
        pathology = memo["portfolio_pathology"]

        # 1. Deep loss count >= 3
        assert pathology["deep_loss_count"] >= 3
        assert "核心亏损拖累源" in pathology["content"]
        assert "华夏上证科创板50成份ETF联接C" in pathology["content"]
        assert "富国中证红利指数增强A" in pathology["content"]
        assert "招商中证白酒指数(LOF)A" in pathology["content"]

        # 2. 19 fee-free fragments totaling ¥442.70 (excluding #10 005827 易方达蓝筹 ¥124.14)
        assert pathology["frag_count"] == 19
        assert abs(pathology["frag_amt"] - 442.70) < 0.01
        assert "长尾碎片尾仓" in pathology["content"]
        assert "检测到 19 只" in pathology["content"]
        assert "¥442.70" in pathology["content"]

    def test_tab1_opt_weights_dict_protection(self):
        """Verify Tab 1 target weights dictionary is recognized as construction verification with 0 fragments."""
        opt_weights = {
            "005561": 0.35,
            "002351": 0.20,
            "110020": 0.15,
            "011613": 0.15,
            "017436": 0.10,
            "000216": 0.05,
        }

        memo = generate_chief_advisor_memo(
            holdings=opt_weights,
            total_capital=100000.0,
        )
        pathology = memo["portfolio_pathology"]

        # Must NOT report fragments or deep loss
        assert pathology["deep_loss_count"] == 0
        assert pathology["frag_count"] == 0
        assert pathology["frag_amt"] == 0.0

        # Must NOT contain the ridiculous ¥1.00 text
        assert "¥1.00" not in pathology["content"]
        assert "碎片/羊毛基" not in pathology["content"]

        # Must contain construction structure information
        assert "建仓标的" in pathology["content"]
        assert "共精选 <b>6</b> 只核心标的" in pathology["content"]
        assert "攻防配比" in pathology["content"]
        assert "分散度" in pathology["content"]
        assert "持仓结构优良" in pathology["content"]
        assert pathology["title"] == "📐 拟建仓组合结构校验"
        assert pathology["badge"] == "🟢 结构均衡"

    def test_international_fx_and_cgb_us_spread(self):
        """Verify international FX dimension calculates Sino-US 10Y yield spread."""
        snapshot = {
            "treasury_10y": 1.6258,
            "us_treasury_10y": 4.40,
            "spot_usdcnh": 7.2450,
        }

        memo = generate_chief_advisor_memo(snapshot=snapshot)
        intl = memo["international_fx"]

        assert "usdcnh_rate" in intl
        assert "中美 10Y 国债利差" in intl["content"]
        assert "中债 1.63% vs 美债 4.40%" in intl["content"]
        assert "跨市场风险提示" in intl["content"]


class TestG16M1ChiefAdvisorMemoGui:
    """M1 GUI Rendering & CommonMark Verification Tests."""

    def test_memo_card_grid_layout_and_clean_html(self):
        """Verify render_chief_advisor_memo_card renders 1-row-5-col responsive grid without CommonMark code block leaks."""
        memo = generate_chief_advisor_memo()

        with patch("streamlit.markdown") as mock_st_md:
            render_chief_advisor_memo_card(memo, title="🧭 首席投顾五维全息决策备忘录")
            assert mock_st_md.called
            call_arg = mock_st_md.call_args[0][0]

            # 1. Verify CommonMark 4-space rule (no line starts with 4 spaces)
            for idx, line in enumerate(call_arg.splitlines()):
                assert not line.startswith("    "), f"Line {idx} starts with 4 spaces: {line}"
                assert not line.startswith("\t"), f"Line {idx} starts with a tab: {line}"

            # 2. Verify 1-row-5-col responsive grid style
            assert "grid-template-columns: repeat(5, minmax(0, 1fr));" in call_arg
            assert "chief-memo-grid" in call_arg
            assert "@media (max-width: 768px)" in call_arg

            # 3. Verify all 5 dimension cards are rendered
            assert "🏛️ 宏观与政策面" in call_arg
            assert "🌐 国际与汇率面" in call_arg
            assert "📈 产业与估值面" in call_arg
            assert "🩺 存量持仓病灶" in call_arg
            assert "🎯 今日行动准则" in call_arg

    def test_memo_card_with_tab1_construction_mode(self):
        """Verify render_chief_advisor_memo_card renders construction mode title correctly."""
        opt_weights = {"005561": 0.40, "002351": 0.35, "000216": 0.25}
        memo = generate_chief_advisor_memo(holdings=opt_weights, total_capital=100000.0)

        with patch("streamlit.markdown") as mock_st_md:
            render_chief_advisor_memo_card(memo, title="🧭 首席投顾五维决策备忘录（建仓方案研判）")
            assert mock_st_md.called
            call_arg = mock_st_md.call_args[0][0]

            assert "📐 拟建仓组合结构校验" in call_arg
            assert "🟢 结构均衡" in call_arg
            assert "建仓标的" in call_arg
            assert "¥1.00" not in call_arg
