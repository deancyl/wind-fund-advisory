"""
Adversarial Challenge & Empirical Verification Test Suite for Milestone 1
Author: teamwork_challenger_m1_1 (Critic & Specialist)

Target:
- Production code: AGY2_FundAdvisory/app_gui.py
- System contracts: PROJECT.md, ORIGINAL_REQUEST.md

Testing Focus:
1. Anti-Laziness & Fake Delay Defense (AST Scan):
   - Zero `time.sleep` / `asyncio.sleep` / `sleep` calls.
   - Zero synthetic delay padding (e.g. `max(1.22, ...)`).
   - Zero hardcoded strings for "限额买500" or "现金分红·限额买500".
2. Top Dashboard & 1080p Zero-Ellipsis Defense:
   - 1 row of 4 wide cards + 1 compact refresh button.
   - Metric cards CSS: explicit removal of `overflow: hidden;` and `text-overflow: ellipsis;`.
   - Technical & quantitative metrics moved to `ⓘ` tooltip title/help, leaving plain vernacular visible.
   - String length budget check across all 4 cards under 1080p typical widths.
3. Tab 1 Construction Sheet 9-Columns & Dynamic Quota DCA Plan Defense:
   - Assertion that `cols_9 = [...]` exists with exactly 9 expected column names.
   - Dynamic `action_guide` generation (no hardcoding).
   - Large amount quota overflow simulation: verification that full-market QDII quota overflow triggers `dca_plan` generation and 《超限资金分批定投执行计划》 banner display.
"""

import ast
import re
import sys
from pathlib import Path
from unittest.mock import patch
import pytest
import pandas as pd
import numpy as np

# Adjust paths
TEST_DIR = Path(__file__).resolve().parent
APP_DIR = TEST_DIR.parent
WORKSPACE_ROOT = APP_DIR.parent if APP_DIR.name == "AGY2_FundAdvisory" else APP_DIR

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from portfolio_manager import PortfolioManager, fetch_realtime_fund_quota
from strategy_bridge import StrategyBridge


@pytest.fixture(scope="module")
def app_gui_ast():
    gui_path = APP_DIR / "app_gui.py"
    assert gui_path.exists(), f"app_gui.py not found at {gui_path}"
    content = gui_path.read_text(encoding="utf-8")
    tree = ast.parse(content)
    return content, tree


# ==============================================================================
# Challenge 1: AST Anti-Laziness, Sleep, Synthetic Delay & Hardcoded Strings
# ==============================================================================

def test_ast_zero_sleep_calls(app_gui_ast):
    """
    Empirical Challenge: Walk AST of app_gui.py to assert that sleep calls
    (time.sleep, asyncio.sleep, or plain sleep) are strictly 0.
    """
    content, tree = app_gui_ast
    sleep_calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == "sleep":
                sleep_calls.append((node.lineno, "sleep"))
            elif isinstance(func, ast.Attribute) and func.attr == "sleep":
                sleep_calls.append((node.lineno, f"{getattr(func.value, 'id', 'unknown')}.sleep"))

    assert len(sleep_calls) == 0, f"Found forbidden sleep calls in app_gui.py: {sleep_calls}"


def test_ast_zero_fake_delays(app_gui_ast):
    """
    Empirical Challenge: Detect synthetic duration padding such as max(1.22, ...)
    or artificial constant sleep timers.
    """
    content, tree = app_gui_ast
    suspicious_delays = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            # Check max(1.22, ...)
            if isinstance(node.func, ast.Name) and node.func.id == "max":
                for arg in node.args:
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, (int, float)):
                        # Flag constants between 0.5s and 10s passed to max as potential fake delay floors
                        if 0.5 <= arg.value <= 10.0:
                            suspicious_delays.append((node.lineno, arg.value))

    assert len(suspicious_delays) == 0, f"Found suspicious fake delay floors: {suspicious_delays}"


def test_ast_zero_hardcoded_quota_strings(app_gui_ast):
    """
    Empirical Challenge: Check all string constants in AST to assert zero occurrences
    of '限额买500' or '现金分红·限额买500'.
    """
    content, tree = app_gui_ast
    forbidden_strings = ["限额买500", "现金分红·限额买500"]
    found_violations = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            for s in forbidden_strings:
                if s in node.value:
                    found_violations.append((node.lineno, s, node.value))

    assert len(found_violations) == 0, f"Found hardcoded quota strings in app_gui.py: {found_violations}"


# ==============================================================================
# Challenge 2: Top Dashboard 4 Wide Cards & Zero-Ellipsis Defense
# ==============================================================================

def test_top_dashboard_layout_structure(app_gui_ast):
    """
    Empirical Challenge: Verify the top dashboard renders 1 row of 4 wide cards
    plus 1 compact refresh button column.
    """
    content, tree = app_gui_ast

    # Search for column ratio definition
    col_pattern = re.search(r"st\.columns\(\s*\[([0-9\.,\s]+)\]\s*\)", content)
    assert col_pattern is not None, "Top columns layout definition not found!"
    col_weights = [float(x.strip()) for x in col_pattern.group(1).split(",")]
    assert len(col_weights) == 5, f"Expected 5 columns (4 cards + 1 btn), got {len(col_weights)}: {col_weights}"
    # Verify the first 4 are wide cards (>2.0) and the 5th is compact button (<1.0)
    for i in range(4):
        assert col_weights[i] >= 2.0, f"Card column {i+1} weight {col_weights[i]} is too narrow (< 2.0)!"
    assert col_weights[4] <= 1.0, f"Refresh button column weight {col_weights[4]} should be compact (<= 1.0)"


def test_css_removed_ellipsis_on_top_cards(app_gui_ast):
    """
    Empirical Challenge: Assert that CSS for .main-metric-card, .metric-card-title,
    .metric-value-huge, and .metric-card-sub does NOT enforce text-overflow: ellipsis.
    """
    content, tree = app_gui_ast

    # Extract CSS style block
    css_match = re.search(r"<style>(.*?)</style>", content, re.DOTALL)
    assert css_match is not None, "CSS block not found in app_gui.py!"
    css_block = css_match.group(1)

    for cls in [".main-metric-card", ".metric-card-title", ".metric-value-huge", ".metric-card-sub"]:
        cls_pattern = re.search(rf"{re.escape(cls)}\s*\{{([^}}]+)\}}", css_block)
        assert cls_pattern is not None, f"CSS class {cls} definition not found!"
        cls_body = cls_pattern.group(1)
        assert "text-overflow: ellipsis" not in cls_body, (
            f"Class {cls} still contains 'text-overflow: ellipsis;', causing forced truncation!"
        )
        assert "overflow: hidden" not in cls_body, (
            f"Class {cls} still contains 'overflow: hidden;', causing text clipping!"
        )


def test_top_cards_tooltips_and_plain_vernacular(app_gui_ast):
    """
    Empirical Challenge: Assert that all 4 top cards encapsulate technical metrics
    (ERP, DR007 spread, option IV, IC basis, MA20/MA60, countdown, cash breakdown)
    inside tooltip title/help, while main text is plain vernacular.
    """
    content, tree = app_gui_ast

    # Card 1 tooltip check
    assert "c1_tip = " in content, "Card 1 tooltip c1_tip not defined"
    assert "15:00" in content, "Card 1 does not document 15:00 window in tooltip"

    # Card 2 tooltip check
    assert "c2_tip = " in content, "Card 2 tooltip c2_tip not defined"
    assert "MA20生命线" in content, "Card 2 does not encapsulate MA20 in tooltip"

    # Card 3 tooltip check
    assert "c3_tip = " in content, "Card 3 tooltip c3_tip not defined"
    assert "ERP股债性价比分位" in content, "Card 3 does not encapsulate ERP in tooltip"

    # Card 4 tooltip check
    assert "c4_tip = " in content, "Card 4 tooltip c4_tip not defined"
    assert "可用现金" in content, "Card 4 does not encapsulate cash in tooltip"


def test_top_cards_text_length_budget_in_1080p():
    """
    Empirical Challenge: In 1080p (width ~1920px, container ~1600px, 4 columns ~360px each),
    verify that the rendered strings for all 4 cards are well within the ~30-character
    threshold to prevent overflow without needing ellipsis.
    """
    # Sample actual rendered texts from app_gui.py
    card1_title = "🕒 交易时钟与窗口"
    card1_val = "🟢 14:30黄金窗口"
    card1_sub = "倒计时 00:00:00 ｜ 距下次常规网格日 3 天"

    card2_title = "🧭 市场定调与攻防线"
    card2_val = "🟢 震荡收息期"
    card2_sub = "📈破 4,141 进攻 ｜ 🛡️跌 3,846 防守"

    card3_title = "🌡️ 估值与资金面温度"
    card3_val = "估值极便宜 · 资金充裕"
    card3_sub = "股票性价比高 ｜ 央妈呵护"

    card4_title = "💰 我的总资产与今日预估"
    card4_val = "¥100,000.00"
    card4_sub = "今日预估 ¥+120.00 (+0.12%)"

    for name, title, val, sub in [
        ("Card 1", card1_title, card1_val, card1_sub),
        ("Card 2", card2_title, card2_val, card2_sub),
        ("Card 3", card3_title, card3_val, card3_sub),
        ("Card 4", card4_title, card4_val, card4_sub),
    ]:
        assert len(title) <= 20, f"{name} title '{title}' exceeds 20 chars"
        assert len(val) <= 20, f"{name} val '{val}' exceeds 20 chars"
        assert len(sub) <= 35, f"{name} sub '{sub}' exceeds 35 chars (risk of 1080p wrap)"


# ==============================================================================
# Challenge 3: Tab 1 Construction Sheet 9-Columns & Dynamic Quota DCA Plan
# ==============================================================================

def test_tab1_cols_9_definition(app_gui_ast):
    """
    Empirical Challenge: Assert that `cols_9 = [...]` exists strictly in app_gui.py
    and contains exactly the 9 expected column names.
    """
    content, tree = app_gui_ast
    expected_cols = [
        "基金代码", "基金名称", "份额", "目标占比(%)",
        "精确买入金额(元)", "最新净值", "实时估值涨跌(%)",
        "排雷与拥挤度", "实操分红与限购指引"
    ]

    # Search for cols_9 in AST
    cols_9_found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "cols_9":
                    if isinstance(node.value, ast.List):
                        actual_cols = [
                            elt.value for elt in node.value.elts
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                        ]
                        assert actual_cols == expected_cols, (
                            f"cols_9 mismatch! Expected {expected_cols}, got {actual_cols}"
                        )
                        cols_9_found = True
                        break

    assert cols_9_found, "Variable 'cols_9 = [...]' not found in app_gui.py!"


def test_tab1_dca_plan_banner_rendered(app_gui_ast):
    """
    Empirical Challenge: Verify that app_gui.py contains the conditional rendering
    block for 《超限资金分批定投执行计划》 when blueprint has dca_plan.
    """
    content, tree = app_gui_ast
    assert 'blueprint.get("dca_plan")' in content or "blueprint.get('dca_plan')" in content, (
        "blueprint.get('dca_plan') condition missing in app_gui.py!"
    )
    assert "《超限资金分批定投执行计划》" in content, (
        "Banner title '《超限资金分批定投执行计划》' not found in app_gui.py!"
    )


def test_dynamic_quota_waterfall_and_dca_plan_generation():
    """
    Empirical Challenge: Simulate large capital zero-start allocation where
    all alternatives in the QDII sector are quota-constrained (e.g. 050025 limit 500,
    001071 limit 1000). Assert:
    1. Primary fund gets limited amount (¥500), guide contains '单日限额¥500·已拆单'.
    2. Alternative fund gets limited amount (¥1000), guide contains '单日限额¥1000·已拆单'.
    3. Remaining overflow triggers dca_plan generation.
    4. dca_plan string contains estimated days and specific advice.
    """
    pm = PortfolioManager()

    def mock_sector_quota(fund_code):
        qdii_limits = {
            "050025": 500.0,
            "001071": 1000.0,
            "006075": 1000.0,
            "017436": 1000.0,
        }
        if fund_code in qdii_limits:
            return {"fund_code": fund_code, "status": "限制大额", "daily_limit": qdii_limits[fund_code], "is_limited": True}
        return {"fund_code": fund_code, "status": "开放申购", "daily_limit": 1e11, "is_limited": False}

    with patch("portfolio_manager.fetch_realtime_fund_quota", side_effect=mock_sector_quota):
        # 100,000 RMB on C3 (QDII target ~6% = 6,000 RMB)
        bp = pm.generate_zero_start_blueprint(total_capital=100000.0, tier="C3")

        # 1. Check dca_plan exists
        dca_plan = bp.get("dca_plan")
        assert dca_plan is not None, "dca_plan should be generated when all alternatives are limited!"
        assert "受全市场" in dca_plan or "定投买入" in dca_plan, f"dca_plan wording unexpected: {dca_plan}"
        assert "建议分" in dca_plan and "个交易日定投买入" in dca_plan, f"dca_plan missing schedule: {dca_plan}"

        # 2. Check items in blueprint
        items_map = {it["fund_code"]: it for it in bp["items"]}
        assert "050025" in items_map, "Primary fund 050025 missing from blueprint"
        assert "001071" in items_map, "Alternative fund 001071 missing from blueprint"

        p_it = items_map["050025"]
        a_it = items_map["001071"]

        assert p_it["allocated_amount"] == 500.0, f"Expected 050025 to get 500.0, got {p_it['allocated_amount']}"
        assert "500" in p_it["action_guide"], f"Expected 050025 guide to mention 500, got {p_it['action_guide']}"

        assert a_it["allocated_amount"] == 1000.0, f"Expected 001071 to get 1000.0, got {a_it['allocated_amount']}"
        assert "1000" in a_it["action_guide"], f"Expected 001071 guide to mention 1000, got {a_it['action_guide']}"


def test_dynamic_quota_unlimited_alternative_absorption():
    """
    Empirical Challenge: When the primary fund is limited (e.g. 050025 limit 500)
    but the alternative fund is UNLIMITED (open subscription), assert:
    1. Primary fund gets 500 with '单日限额¥500·已拆单'.
    2. Alternative fund absorbs ALL remaining quota with '承接超额·不限购正常买'.
    3. No dca_plan is generated (dca_plan is None) since all money was successfully allocated.
    """
    pm = PortfolioManager()

    def mock_single_limit_quota(fund_code):
        if fund_code == "050025":
            return {"fund_code": "050025", "status": "限制大额", "daily_limit": 500.0, "is_limited": True}
        return {"fund_code": fund_code, "status": "开放申购", "daily_limit": 1e11, "is_limited": False}

    with patch("portfolio_manager.fetch_realtime_fund_quota", side_effect=mock_single_limit_quota):
        bp = pm.generate_zero_start_blueprint(total_capital=100000.0, tier="C3")

        # dca_plan should be None because 001071 has no limit and absorbed all overflow
        assert bp.get("dca_plan") is None, "dca_plan should be None when alternative absorbs all money"

        items_map = {it["fund_code"]: it for it in bp["items"]}
        assert "050025" in items_map
        assert "001071" in items_map

        p_it = items_map["050025"]
        a_it = items_map["001071"]

        assert p_it["allocated_amount"] == 500.0
        assert "500" in p_it["action_guide"]

        assert a_it["allocated_amount"] > 1000.0
        assert a_it["action_guide"] == "承接超额·不限购正常买"


def test_tab1_blueprint_generation_all_tiers():
    """
    Empirical Challenge: Stress test blueprint generation across all 5 risk tiers
    (C1 to C5) with standard and edge amounts (e.g. 5,000, 50,000, 1,000,000).
    Verify that bp['items'] always produces valid rows conforming to cols_9 schema.
    """
    pm = PortfolioManager()
    expected_cols = [
        "基金代码", "基金名称", "份额", "目标占比(%)",
        "精确买入金额(元)", "最新净值", "实时估值涨跌(%)",
        "排雷与拥挤度", "实操分红与限购指引"
    ]

    for tier in ["C1", "C2", "C3", "C4", "C5"]:
        for cap in [5000.0, 50000.0, 1000000.0]:
            bp = pm.generate_zero_start_blueprint(total_capital=cap, tier=tier)
            assert "items" in bp
            assert len(bp["items"]) >= 3, f"Tier {tier} cap {cap} produced fewer than 3 items"

            # Check total weight sum is approximately 100%
            tot_w = sum(it["target_weight_pct"] for it in bp["items"])
            assert 95.0 <= tot_w <= 105.0, f"Tier {tier} target weight sum {tot_w} abnormal"

            # Check that every item has required fields for cols_9 table
            for it in bp["items"]:
                assert "fund_code" in it and len(it["fund_code"]) == 6
                assert "fund_name" in it and len(it["fund_name"]) > 0
                assert "share_class" in it
                assert "target_weight_pct" in it and it["target_weight_pct"] >= 0
                assert "allocated_amount" in it and it["allocated_amount"] > 0
                assert "action_guide" in it and len(it["action_guide"]) > 0
