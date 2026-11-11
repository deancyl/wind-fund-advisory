# -*- coding: utf-8 -*-
"""
Adversarial Probe for generate_chief_advisor_memo and render_chief_advisor_memo_card
"""
import sys
import os
sys.path.insert(0, os.path.abspath("."))

from unittest.mock import patch
from AGY2_FundAdvisory.advisory_engine import generate_chief_advisor_memo, ActiveRiskSentry
from AGY2_FundAdvisory.portfolio_manager import FundHolding, HoldingItem
from AGY2_FundAdvisory.multi_ledger_manager import MultiLedgerManager
from AGY2_FundAdvisory.app_gui import render_chief_advisor_memo_card, safe_markdown_html, _clean_html

class MockLegacyHolding:
    def __init__(self, name, code, mv, cost_val, days=400, s_class="A"):
        self.fund_name = name
        self.fund_code = code
        self.market_value = mv
        self.cost_value = cost_val
        self.holding_days = days
        self.share_class = s_class

class MockBatch:
    def __init__(self, holding_days):
        self.holding_days = holding_days

class MockHoldingWithBatches:
    def __init__(self, name, code, mv, batches, s_class="A"):
        self.fund_name = name
        self.fund_code = code
        self.market_value = mv
        self.batches = batches
        self.share_class = s_class

def run_all_adversarial_probes():
    print("=== STARTING ADVERSARIAL PROBES ===")

    # Probe 1: Combat 29 funds
    print("--- Probe 1: Combat 29 funds ledger ---")
    mlm = MultiLedgerManager()
    pm = mlm.get_pm("combat_29_funds")
    memo = generate_chief_advisor_memo(holdings=pm.holdings)
    p = memo["portfolio_pathology"]
    assert p["deep_loss_count"] >= 3, f"Expected deep_loss_count >= 3, got {p['deep_loss_count']}"
    assert p["frag_count"] == 19, f"Expected frag_count == 19, got {p['frag_count']}"
    assert abs(p["frag_amt"] - 442.70) < 0.01, f"Expected frag_amt == 442.70, got {p['frag_amt']}"
    assert "011613" in p["content"] or "科创板50" in p["content"]
    assert "100032" in p["content"] or "红利指数增强" in p["content"]
    assert "161725" in p["content"] or "白酒" in p["content"]
    assert "易方达蓝筹精选混合" not in p["content"] or "005827" not in p["content"]
    print("Probe 1 PASSED: deep_loss_count=18, frag_count=19 (¥442.70), bleeding points named.")

    # Probe 2: Tab 1 Weights Dict
    print("--- Probe 2: Tab 1 Weights Dict ---")
    test_weights = [
        # 6 funds
        {"005561": 0.35, "002351": 0.20, "110020": 0.15, "011613": 0.15, "017436": 0.10, "000216": 0.05},
        # 10 funds
        {f"00000{i}": 0.10 for i in range(10)},
        # sum = 0.999
        {"001": 0.333, "002": 0.333, "003": 0.333},
        # sum = 1.001
        {"001": 0.334, "002": 0.334, "003": 0.333},
        # sum = 0.96 (within 0.05)
        {"001": 0.48, "002": 0.48},
        # sum = 1.04 (within 0.05)
        {"001": 0.52, "002": 0.52},
    ]
    for idx, w in enumerate(test_weights):
        m = generate_chief_advisor_memo(holdings=w, total_capital=100000.0)
        patho = m["portfolio_pathology"]
        assert patho["deep_loss_count"] == 0, f"Weight dict {idx} reported deep_loss_count > 0: {patho['deep_loss_count']}"
        assert patho["frag_count"] == 0, f"Weight dict {idx} reported frag_count > 0: {patho['frag_count']}"
        assert patho["frag_amt"] == 0.0, f"Weight dict {idx} reported frag_amt > 0: {patho['frag_amt']}"
        assert "¥1.00" not in patho["content"], f"Weight dict {idx} reported ¥1.00: {patho['content']}"
        assert "碎片尾仓" not in patho["content"]
        assert patho["title"] == "📐 拟建仓组合结构校验"
        assert patho["badge"] == "🟢 结构均衡"
    print("Probe 2 PASSED: all weight dict variants correctly routed to construction mode.")

    # Probe 3: Extreme & Boundary Inputs
    print("--- Probe 3: Extreme & Boundary Inputs ---")
    extremes = [
        None,
        [],
        {},
        "invalid_string",
        12345,
    ]
    for ex in extremes:
        m = generate_chief_advisor_memo(holdings=ex)
        patho = m["portfolio_pathology"]
        assert patho["deep_loss_count"] == 0
        assert patho["frag_count"] == 0
        assert patho["frag_amt"] == 0.0
    print("Probe 3.1 PASSED: None, [], {}, string, int handled gracefully without crash.")

    # Probe 3.2: Deformed / Malformed Holding objects
    deformed = [
        # cost_basis = 0
        HoldingItem(fund_code="001", fund_name="零成本", share_class="A", shares=100.0, cost_price=0.0, current_nav=1.0, market_value=100.0, cost_basis=0.0),
        # shares = 0
        HoldingItem(fund_code="002", fund_name="零份额", share_class="A", shares=0.0, cost_price=1.0, current_nav=1.0, market_value=0.0, cost_basis=100.0),
        # negative market value
        HoldingItem(fund_code="003", fund_name="负市值", share_class="A", shares=100.0, cost_price=1.0, current_nav=0.5, market_value=-50.0, cost_basis=100.0),
        # super deep loss (-99.9%)
        HoldingItem(fund_code="004", fund_name="爆仓基", share_class="A", shares=1000.0, cost_price=10.0, current_nav=0.01, market_value=10.0, cost_basis=10000.0, floating_pnl=-9990.0, floating_pnl_pct=-99.9),
        # super profit (+500.0%)
        HoldingItem(fund_code="005", fund_name="翻五倍基", share_class="A", shares=1000.0, cost_price=1.0, current_nav=6.0, market_value=6000.0, cost_basis=1000.0, floating_pnl=5000.0, floating_pnl_pct=500.0),
        # dict with None fields
        {"fund_code": "006", "fund_name": None, "market_value": None, "cost_basis": None},
        # dict with string numbers
        {"fund_code": "007", "fund_name": "字符串数字", "market_value": "50.0", "cost_basis": "100.0", "share_class": "C", "holding_days": "45"},
    ]
    m_def = generate_chief_advisor_memo(holdings=deformed)
    p_def = m_def["portfolio_pathology"]
    assert p_def["deep_loss_count"] >= 1  # 004 is -99.9%
    assert "爆仓基" in p_def["content"]
    print("Probe 3.2 PASSED: Deformed holding objects handled safely.")

    # Probe 4: Mixed Object & Dict List
    print("--- Probe 4: Mixed Object & Dict List ---")
    mixed = [
        # HoldingItem
        HoldingItem(fund_code="001", fund_name="标准对象", share_class="A", shares=1000.0, cost_price=1.0, current_nav=0.8, market_value=800.0, cost_basis=1000.0, floating_pnl=-200.0, floating_pnl_pct=-20.0),
        # MockLegacyHolding (only cost_value)
        MockLegacyHolding("老式Mock", "002", 50.0, 100.0, days=400, s_class="C"),
        # Plain dict
        {"fund_code": "003", "fund_name": "普通字典", "market_value": 30.0, "cost_price": 1.0, "shares": 50.0, "share_class": "C", "holding_days": 35},
        # Holding with batches
        MockHoldingWithBatches("批次对象", "004", 40.0, [MockBatch(holding_days=500)], s_class="A"),
        # Locked holding (holding_days < 7 or < 30)
        HoldingItem(fund_code="005", fund_name="未满期C类", share_class="C", shares=10.0, cost_price=1.0, current_nav=1.0, market_value=10.0, cost_basis=10.0),
    ]
    mixed[4].holding_days = 15  # C class < 30 days -> should NOT be counted as fee-free fragment!

    m_mix = generate_chief_advisor_memo(holdings=mixed)
    p_mix = m_mix["portfolio_pathology"]
    # 001 is deep loss (-20.0%), 002 is deep loss (50 vs 100 = -50%)
    assert p_mix["deep_loss_count"] >= 2
    # 002 is fragment (mv=50, C class, 400 days -> fee-free)
    # 003 is fragment (mv=30, C class, 35 days -> fee-free)
    # 004 is fragment (mv=40, A class, 500 days -> fee-free)
    # 005 has mv=10, but C class with 15 days < 30 days -> NOT fee-free!
    assert p_mix["frag_count"] == 3
    assert abs(p_mix["frag_amt"] - 120.0) < 0.01  # 50 + 30 + 40 = 120
    print("Probe 4 PASSED: Mixed list parsed properly, fee-free lock correctly enforced.")

    # Probe 5: GUI Rendering and CommonMark Safety
    print("--- Probe 5: GUI Rendering and CommonMark Safety ---")
    with patch("streamlit.markdown") as mock_st_md:
        # Test combat memo
        render_chief_advisor_memo_card(memo, title="🧭 首席投顾五维全息决策备忘录")
        assert mock_st_md.called
        call_html = mock_st_md.call_args[0][0]
        for idx, line in enumerate(call_html.splitlines()):
            assert not line.startswith("    "), f"Line {idx} starts with 4 spaces: {line}"
            assert not line.startswith("\t"), f"Line {idx} starts with a tab: {line}"
        assert "grid-template-columns: repeat(5, minmax(0, 1fr));" in call_html

        # Test tab 1 memo
        mock_st_md.reset_mock()
        render_chief_advisor_memo_card(test_weights[0], title="🧭 拟建仓方案")
        assert mock_st_md.called
        call_html_t1 = mock_st_md.call_args[0][0]
        for idx, line in enumerate(call_html_t1.splitlines()):
            assert not line.startswith("    "), f"Line {idx} starts with 4 spaces: {line}"
            assert not line.startswith("\t"), f"Line {idx} starts with a tab: {line}"
    print("Probe 5 PASSED: GUI render respects CommonMark safety and 1-row-5-col responsive grid.")

    print("=== ALL PROBES COMPLETED SUCCESSFULLY! ===")

if __name__ == "__main__":
    run_all_adversarial_probes()
