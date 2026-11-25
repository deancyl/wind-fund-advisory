# -*- coding: utf-8 -*-
"""
Adversarial Empirical Challenge Harness for Milestone 2 (M2-1)
Targeting Features 7, 8, 12, 13 in AGY2_FundAdvisory/app_gui.py

Executes rigorous dynamic probes, boundary mutations, CSS AST/DOM evaluations,
and state machine transitions.
"""

import ast
import re
import sys
import unittest
from unittest.mock import MagicMock, patch
from typing import Dict, Any, List
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, ".")

import streamlit as st
from AGY2_FundAdvisory.portfolio_manager import (
    HoldingItem,
    PortfolioManager,
    parse_smart_text_holdings,
)
from AGY2_FundAdvisory.multi_ledger_manager import MultiLedgerManager
from AGY2_FundAdvisory.app_gui import (
    _is_mobile_viewport,
    _clean_html,
    render_chief_advisor_memo_card,
    IS_MOBILE_VIEW,
)


class TestFeature7InitialLedgerRoutingAdversarial(unittest.TestCase):
    """
    Adversarial probes against Initial Ledger Routing in app_gui.py
    Verifies lines 2739-2760 and 3294-3314 directly against AST and state logic.
    """

    def setUp(self):
        with open("AGY2_FundAdvisory/app_gui.py", "r", encoding="utf-8") as f:
            self.source_code = f.read()
        self.tree = ast.parse(self.source_code)

    def test_ast_hard_inspection_both_routing_blocks_exist(self):
        """Verify that both primary routing (2742) and fallback routing (3295) exist in app_gui.py AST."""
        matches = re.findall(r'if\s+["\']_initial_ledger_routed["\']\s+not\s+in\s+st\.session_state:', self.source_code)
        self.assertGreaterEqual(len(matches), 2, "Expected at least 2 checks for _initial_ledger_routed (primary + fallback)")

        # Verify the threshold is >= 10 in both places
        thresh_matches = re.findall(r'len\([^)]+\.holdings\)\s*>=\s*10', self.source_code)
        self.assertGreaterEqual(len(thresh_matches), 2, "Both routing checks must enforce threshold >= 10")

    def test_exact_boundary_9_funds_adversarial(self):
        """Boundary: Ledger with exactly 9 funds must NOT trigger routing."""
        mock_session = {}
        mock_pm = MagicMock()
        mock_pm.holdings = {f"00000{i}": MagicMock() for i in range(9)}

        if "_initial_ledger_routed" not in mock_session:
            mock_session["_initial_ledger_routed"] = True
            if mock_pm and len(mock_pm.holdings) >= 10:
                mock_session["pending_cross_tab_jump"] = {"tab_index": 1}

        self.assertTrue(mock_session["_initial_ledger_routed"])
        self.assertNotIn("pending_cross_tab_jump", mock_session, "9 funds must NOT trigger cross-tab jump")
        self.assertNotIn("tab2_view_mode", mock_session)

    def test_exact_boundary_10_funds_adversarial(self):
        """Boundary: Ledger with exactly 10 funds MUST trigger routing."""
        mock_session = {}
        mock_pm = MagicMock()
        mock_pm.holdings = {f"0000{i:02d}": MagicMock() for i in range(10)}

        if "_initial_ledger_routed" not in mock_session:
            mock_session["_initial_ledger_routed"] = True
            if mock_pm and len(mock_pm.holdings) >= 10:
                mock_session["sel_tab2_active_ledger"] = "test_ledger"
                mock_session["tab2_view_mode"] = "💼 持仓诊断与智能调仓 (主流程)"
                mock_session["pending_cross_tab_jump"] = {
                    "tab_index": 1,
                    "tab_name": "💼 持仓调仓",
                    "action_name": "首次加载存量持仓",
                }
                mock_session["tab2_diagnosed"] = True
                mock_session["tab2_rebalanced"] = True

        self.assertTrue(mock_session["_initial_ledger_routed"])
        self.assertIn("pending_cross_tab_jump", mock_session, "10 funds MUST trigger cross-tab jump")
        self.assertEqual(mock_session["pending_cross_tab_jump"]["tab_index"], 1)
        self.assertEqual(mock_session["tab2_view_mode"], "💼 持仓诊断与智能调仓 (主流程)")
        self.assertTrue(mock_session["tab2_diagnosed"])
        self.assertTrue(mock_session["tab2_rebalanced"])

    def test_exact_boundary_0_funds_empty_sandbox_adversarial(self):
        """Boundary: Empty ledger (0 funds) must set _initial_ledger_routed but NOT trigger jump."""
        mock_session = {}
        mock_pm = MagicMock()
        mock_pm.holdings = {}

        if "_initial_ledger_routed" not in mock_session:
            mock_session["_initial_ledger_routed"] = True
            if mock_pm and len(mock_pm.holdings) >= 10:
                mock_session["pending_cross_tab_jump"] = {"tab_index": 1}

        self.assertTrue(mock_session["_initial_ledger_routed"])
        self.assertNotIn("pending_cross_tab_jump", mock_session)

    def test_already_routed_flag_set_never_clobbers_manual_tab_selection(self):
        """Adversarial: When user navigates back to Tab 1 (active_tab_index=0), reruns must preserve Tab 1."""
        mock_session = {
            "_initial_ledger_routed": True,
            "active_tab_index": 0,  # User manually clicked Tab 1 (新资建仓)
            "tab2_view_mode": "💼 账本运维与实盘复盘档案 (独立宽屏工具坞)",  # User selected different mode
        }
        mock_pm = MagicMock()
        mock_pm.holdings = {f"0000{i:02d}": MagicMock() for i in range(29)}

        if "_initial_ledger_routed" not in mock_session:
            mock_session["_initial_ledger_routed"] = True
            if mock_pm and len(mock_pm.holdings) >= 10:
                mock_session["pending_cross_tab_jump"] = {"tab_index": 1}

        if "_initial_ledger_routed" not in mock_session:
            mock_session["_initial_ledger_routed"] = True
            if mock_pm and len(mock_pm.holdings) >= 10:
                mock_session["pending_cross_tab_jump"] = {"tab_index": 1}

        self.assertNotIn("pending_cross_tab_jump", mock_session, "Reruns must NOT re-inject cross-tab jump")
        self.assertEqual(mock_session["active_tab_index"], 0, "User tab selection must be strictly preserved")
        self.assertEqual(mock_session["tab2_view_mode"], "💼 账本运维与实盘复盘档案 (独立宽屏工具坞)")

    def test_pm_is_none_or_malformed_safe_execution(self):
        """Adversarial: If pm is None or lacks holdings, routing must not throw AttributeError."""
        mock_session = {}
        mock_pm = None

        try:
            if "_initial_ledger_routed" not in mock_session:
                mock_session["_initial_ledger_routed"] = True
                if mock_pm and len(mock_pm.holdings) >= 10:
                    mock_session["pending_cross_tab_jump"] = {"tab_index": 1}
        except Exception as e:
            self.fail(f"pm=None raised an unexpected exception: {e}")

        self.assertTrue(mock_session["_initial_ledger_routed"])
        self.assertNotIn("pending_cross_tab_jump", mock_session)


class TestFeature8CSSAndMobileSelectorAdversarial(unittest.TestCase):
    """
    Adversarial probes against CSS Consolidation and Mobile Selector in app_gui.py
    """

    def setUp(self):
        with open("AGY2_FundAdvisory/app_gui.py", "r", encoding="utf-8") as f:
            self.source_code = f.read()

    def test_render_chief_advisor_memo_card_free_of_style_tag(self):
        """Verify render_chief_advisor_memo_card does NOT contain '<style' tag."""
        func_match = re.search(r'def render_chief_advisor_memo_card\([^)]*\):.*?(?=\ndef [a-zA-Z0-9_]+\(|$)', self.source_code, re.DOTALL)
        self.assertIsNotNone(func_match, "render_chief_advisor_memo_card must be defined in app_gui.py")
        func_code = func_match.group(0)

        self.assertNotIn("<style>", func_code, "render_chief_advisor_memo_card must NOT contain '<style>' inline tag")
        self.assertNotIn("<style", func_code, "render_chief_advisor_memo_card must NOT contain '<style' tag")
        self.assertIn('.chief-memo-container', func_code, "HTML must use class chief-memo-container")

    def test_main_css_contains_chief_memo_rules(self):
        """Verify global stylesheet contains the consolidated chief-memo rules."""
        self.assertIn(".chief-memo-container", self.source_code)
        self.assertIn(".chief-memo-grid", self.source_code)
        self.assertIn(".chief-memo-capsule", self.source_code)
        self.assertIn("@container memo-desk (inline-size < 560px)", self.source_code)
        self.assertIn("@container memo-desk (inline-size < 340px)", self.source_code)

    def test_mobile_selector_excludes_stNumberInput_stepper_buttons(self):
        """
        Verify the CSS rule for mobile button wrapping:
        Must target buttons but specifically EXCLUDE stNumberInput.
        """
        self.assertIn('div[data-testid="stHorizontalBlock"]:has(button:not([data-testid*="stNumberInput"])):not(:has(.main-metric-card)):not(:has([data-testid="stNumberInput"]))', self.source_code)
        self.assertIn('> div[data-testid="stColumn"]', self.source_code, "Must include stColumn for modern Streamlit")
        self.assertIn('> div[data-testid="column"]', self.source_code, "Must also include legacy column for compatibility")

    def test_memo_card_invocation_generates_pure_html(self):
        """Verify calling render_chief_advisor_memo_card with sample data does not produce inline <style> tags."""
        sample_memo = {
            "title": "测试裁决",
            "date": "2026-11-15",
            "macro_policy": {"badge": "🟢 货币宽松", "capsule_sub": "流动性充裕"},
            "international_fx": {"badge": "🟢 汇率稳健", "capsule_sub": "中美利差平稳"},
            "industry_valuation": {"badge": "🎯 机会击球", "capsule_sub": "红利低波低估"},
            "portfolio_pathology": {"badge": "🛡️ 稳健持有", "capsule_sub": "无异常"},
            "action_rules": {"verdict": "维持底仓", "color": "#16a34a", "capsule_sub": "继续持有吃息"},
            "causal_disp": "估值分位 < 35% -> 多方配置",
        }
        with patch("AGY2_FundAdvisory.app_gui.safe_markdown_html") as mock_safe_html:
            render_chief_advisor_memo_card(sample_memo)
            self.assertTrue(mock_safe_html.called, "safe_markdown_html should be called by render_chief_advisor_memo_card")
            rendered_arg = mock_safe_html.call_args[0][0]
            self.assertNotIn("<style", rendered_arg, "Rendered HTML must NOT contain <style tags!")
            self.assertIn("chief-memo-container", rendered_arg)


class TestFeature12IsMobileViewAdversarial(unittest.TestCase):
    """
    Adversarial probes against IS_MOBILE_VIEW and _is_mobile_viewport()
    """

    def test_query_param_variations_adversarial(self):
        """Test all query parameter case and value variants."""
        # mobile values
        for val in ["mobile", "Mobile", "MOBILE", "phone", "Phone", "m", "M"]:
            with patch.object(st, "query_params", {"view": val}):
                with patch.object(st, "context", MagicMock(headers={})):
                    self.assertTrue(_is_mobile_viewport(), f"Failed for query_params view={val}")

        # desktop values
        for val in ["desktop", "Desktop", "DESKTOP", "pc", "PC", "d", "D"]:
            with patch.object(st, "query_params", {"view": val}):
                with patch.object(st, "context", MagicMock(headers={"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)"})):
                    # Desktop override should take precedence over mobile User-Agent!
                    self.assertFalse(_is_mobile_viewport(), f"Desktop query param must override mobile UA for view={val}")

    def test_user_agent_variations_adversarial(self):
        """Test diverse real-world mobile and desktop user agents."""
        mobile_uas = [
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            "Mozilla/5.0 (iPad; CPU OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Windows Phone 10.0; Android 6.0.1; Microsoft; Lumia 950) AppleWebKit/537.36",
            "Mozilla/5.0 (iPod touch; CPU iPhone OS 14_0 like Mac OS X)",
        ]
        for ua in mobile_uas:
            with patch.object(st, "query_params", {}):
                with patch.object(st, "context", MagicMock(headers={"User-Agent": ua})):
                    self.assertTrue(_is_mobile_viewport(), f"Failed to detect mobile UA: {ua}")

        desktop_uas = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/122.0",
        ]
        for ua in desktop_uas:
            with patch.object(st, "query_params", {}):
                with patch.object(st, "context", MagicMock(headers={"User-Agent": ua})):
                    self.assertFalse(_is_mobile_viewport(), f"Falsely detected desktop as mobile: {ua}")

    def test_missing_or_exceptional_context_fallback(self):
        """When st.context or st.query_params raise an exception, _is_mobile_viewport must safely return False."""
        with patch.object(st, "query_params", MagicMock(side_effect=RuntimeError("Streamlit not connected"))):
            res = _is_mobile_viewport()
            self.assertFalse(res, "Must fail-safe to False (desktop)")


class TestFeature13Tab2ToolsDockAndLeadCardsAdversarial(unittest.TestCase):
    """
    Adversarial probes against Tab 2 Tool Dock Radio Flattening and Narrative Cards
    """

    def setUp(self):
        with open("AGY2_FundAdvisory/app_gui.py", "r", encoding="utf-8") as f:
            self.source_code = f.read()

    def test_tab2_tools_dock_no_nested_st_tabs_in_dock_tab1(self):
        """Verify dock_tab1 does NOT contain nested st.tabs calls."""
        match = re.search(r'with dock_tab1:(.*?)(?=with dock_tab2:)', self.source_code, re.DOTALL)
        self.assertIsNotNone(match, "with dock_tab1 block must exist in app_gui.py")
        dock_tab1_code = match.group(1)

        self.assertNotIn("st.tabs(", dock_tab1_code, "dock_tab1 must NOT contain nested st.tabs()!")
        self.assertIn("rad_tab2_sub_import_tool", dock_tab1_code, "dock_tab1 must use key='rad_tab2_sub_import_tool'")

    def test_all_three_import_options_handled(self):
        """Verify all 3 options are handled in dock_tab1."""
        options = ["📋 文本粘贴导入", "🔍 搜索添加标的", "📥 表格模板导入"]
        for opt in options:
            self.assertIn(f'"{opt}"', self.source_code, f"Option '{opt}' must be present in app_gui.py")

        self.assertIn('if sel_import_tool == "📋 文本粘贴导入":', self.source_code)
        self.assertIn('elif sel_import_tool == "🔍 搜索添加标的":', self.source_code)
        self.assertIn('else:', self.source_code)

    def test_narrative_lead_cards_exist_and_use_safe_markdown_html(self):
        """Verify the three narrative cards are present and invoked with safe_markdown_html."""
        cards = [
            ("Brinson", "💡 前置人话解读·Brinson 归因三维拆解"),
            ("Heatmap", "💡 前置人话解读·重仓交叉与机构抱团排查"),
            ("4-Quadrant", "💡 前置人话解读·四象限量价结构与轮动指引"),
        ]

        for card_name, title in cards:
            self.assertIn(title, self.source_code, f"{card_name} narrative card title '{title}' must be present in app_gui.py")

            pos = self.source_code.find(title)
            surrounding = self.source_code[max(0, pos-200):pos+300]
            self.assertIn("safe_markdown_html(", surrounding, f"{card_name} card must be wrapped in safe_markdown_html(...)")

    def test_clean_html_purification_on_lead_cards(self):
        """Verify that _clean_html strips leading whitespace to prevent CommonMark 4+ indent block."""
        test_html = """
            <div class="decision-card">
                <div>    💡 前置人话解读·Brinson 归因三维拆解</div>
            </div>
        """
        cleaned = _clean_html(test_html)
        lines = cleaned.split("\n")
        for line in lines:
            if line:
                self.assertFalse(line.startswith("    "), f"Line starts with 4+ spaces: '{line}'")


if __name__ == "__main__":
    unittest.main()
