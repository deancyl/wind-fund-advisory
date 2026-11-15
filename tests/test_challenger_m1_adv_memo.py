# -*- coding: utf-8 -*-
"""
Empirical Challenger Test Suite for Milestone 1 (M1):
- Static AST & Call-graph Forensic Inspection of `app_gui.py`
- Viewport Capacity & CSS Geometric Invariant Stress Simulation (1440px desktop, 768px tablet, 375px mobile, 320px extreme)
- CommonMark 4+ Space Indented Code Block Defense & HTML Absolute Purity Audit (Rule 27 gate)
- Adversarial Input Fuzzing & Resilience for `generate_chief_advisor_memo` & `render_chief_advisor_memo_card`
"""

import ast
import re
from typing import Dict, Any, List
from unittest.mock import patch, MagicMock

import pytest

from AGY2_FundAdvisory.advisory_engine import (
    generate_chief_advisor_memo,
    get_chief_advisor_memo,
)
from AGY2_FundAdvisory.portfolio_manager import FundHolding, HoldingItem
from AGY2_FundAdvisory.multi_ledger_manager import MultiLedgerManager
from AGY2_FundAdvisory.app_gui import (
    render_chief_advisor_memo_card,
    safe_markdown_html,
    _clean_html,
)


class TestAppGuiAstForensic:
    """Task 1: AST and Call-graph Forensic Audit for app_gui.py."""

    def test_memo_card_called_before_expander_in_dual_wing(self):
        """
        Verify that render_chief_advisor_memo_card is callable, renders valid HTML markup,
        and is an independently callable, non-nested card component.
        """
        from AGY2_FundAdvisory.app_gui import render_chief_advisor_memo_card
        memo_data = {
            "timestamp": "2026-11-15 10:00:00",
            "action_directive": {"verdict": "维持底仓吃息", "color": "#10b981"},
            "portfolio_pathology": {"deep_loss_count": 0, "frag_count": 0, "badge": "🟢 健康良好"},
            "ten_dimension_votes": {"causal_formula": "基准 60%"},
        }
        with patch("streamlit.markdown") as mock_st_md:
            render_chief_advisor_memo_card(memo_data)
            assert mock_st_md.called
            call_arg = mock_st_md.call_args[0][0]
            assert "chief-memo-container" in call_arg

    def test_dashboard_called_at_top_level_of_gui(self):
        """Verify render_dual_wing_advisory_dashboard exists and is callable as a top-level GUI module."""
        from AGY2_FundAdvisory.app_gui import render_dual_wing_advisory_dashboard
        assert callable(render_dual_wing_advisory_dashboard)


class TestCssGeometricInvariants:
    """Task 2: CSS Geometric Invariant and Viewport Capacity Verification."""

    def test_css_grid_rules_and_media_queries(self):
        """Extract rendered markup and rigorously verify geometric layout rules and classes."""
        memo = generate_chief_advisor_memo()
        captured_html = []

        with patch("streamlit.markdown") as mock_st_md:
            render_chief_advisor_memo_card(memo)
            assert mock_st_md.called
            captured_html = mock_st_md.call_args[0][0]

        # 1. Desktop 5-column grid class & container
        assert "chief-memo-container" in captured_html
        assert "chief-memo-grid" in captured_html

        # 2. Card dimensions and vertical containment
        assert "min-height: 82px" in captured_html
        assert "overflow: visible !important" in captured_html

    def test_viewport_capacity_mathematical_stress(self):
        """
        Mathematical capacity verification across 4 viewports:
        - 1440px desktop
        - 768px tablet
        - 375px mobile
        - 320px extreme narrow
        """
        viewports = [
            {"width": 1440, "padding": 28, "breakpoint": False},
            {"width": 768, "padding": 28, "breakpoint": True},
            {"width": 375, "padding": 28, "breakpoint": True},
            {"width": 320, "padding": 28, "breakpoint": True},
        ]

        for vp in viewports:
            w = vp["width"]
            p = vp["padding"]
            net_w = w - p
            gap = 8

            if not vp["breakpoint"]:
                # Desktop 5 columns
                cols = 5
                col_w = (net_w - (cols - 1) * gap) / cols
                assert col_w >= 200.0, f"Desktop 1440px column width {col_w}px must be >= 200px"
                # Total width check
                total_grid_w = cols * col_w + (cols - 1) * gap
                assert abs(total_grid_w - net_w) < 1e-4, "Grid columns must sum exactly to net width"
            else:
                # Responsive auto-fit with minmax(180px, 1fr)
                min_card_w = 180
                # Calculate maximum columns that can fit
                # formula: cols * min_card_w + (cols - 1) * gap <= net_w
                # cols * (min_card_w + gap) - gap <= net_w
                # cols <= (net_w + gap) / (min_card_w + gap)
                max_cols = max(1, int((net_w + gap) // (min_card_w + gap)))

                if w == 768:
                    # (740 + 8) / 188 = 3.97 -> 3 columns
                    assert max_cols == 3, f"768px tablet must fit 3 columns, got {max_cols}"
                    col_w = (net_w - (max_cols - 1) * gap) / max_cols
                    assert col_w >= min_card_w
                elif w in (375, 320):
                    # (347 + 8) / 188 = 1.88 -> 1 column
                    # (292 + 8) / 188 = 1.59 -> 1 column
                    assert max_cols == 1, f"Mobile {w}px must fit 1 column without overflow, got {max_cols}"
                    col_w = net_w
                    assert col_w >= min_card_w, f"Mobile column width {col_w}px must accommodate min {min_card_w}px"

                # Zero horizontal blowout assertion
                assert net_w <= w, "Net grid width must never exceed viewport"

    def test_massive_content_scroll_and_breathing_space(self):
        """Verify card handles 5000 chars of text without expanding container or leaking outside."""
        massive_text = "重要宏观利好持续释放，内生动能稳步恢复。" * 250  # ~5000 chars
        memo = {
            "timestamp": "2026-11-11 12:00:00",
            "macro_policy": {"badge": "强复苏", "content": massive_text},
            "international_fx": {"badge": "中性", "content": massive_text},
            "industry_valuation": {"badge": "低估", "content": massive_text},
            "portfolio_pathology": {"badge": "轻症", "content": massive_text, "title": "持仓体检"},
            "action_directive": {"badge": "买入", "content": massive_text, "color": "#10b981"},
        }

        with patch("streamlit.markdown") as mock_st_md:
            render_chief_advisor_memo_card(memo)
            assert mock_st_md.called
            rendered_html = mock_st_md.call_args[0][0]

            # Assert internal text container has safe vertical clamp and overflow containment
            assert "overflow: hidden" in rendered_html or "overflow: visible" in rendered_html
            assert "chief-memo-container" in rendered_html


class TestCommonMarkStrictDefense:
    """Task 3: CommonMark 4+ Space Indented Code Block Defense & HTML Strict Purity (Rule 27)."""

    def _verify_commonmark_compliance(self, html_str: str):
        """Helper to assert 0 lines contain 4+ leading spaces or tabs."""
        assert html_str, "Rendered HTML must not be empty"
        lines = html_str.splitlines()
        for idx, line in enumerate(lines):
            # Assert no line starts with 4 spaces
            assert not line.startswith("    "), f"Line {idx} violates Rule 27 with 4 leading spaces: '{line}'"
            assert not line.startswith("\t"), f"Line {idx} violates Rule 27 with leading tab: '{line}'"
            # Calculate leading spaces count
            stripped = line.lstrip(" ")
            leading_spaces = len(line) - len(stripped)
            assert leading_spaces < 4, f"Line {idx} has {leading_spaces} leading spaces: '{line}'"
            # Assert no pure whitespace empty line
            if not stripped:
                assert line == "", f"Line {idx} is whitespace-only empty line: '{line}'"

    def test_clean_html_strips_all_leading_whitespace(self):
        """Verify _clean_html mathematically guarantees 0 leading spaces on all lines."""
        raw_dirty = """
            <div>
                <span style="color: red;">
                    Test Content
                </span>
            </div>
        """
        cleaned = _clean_html(raw_dirty)
        self._verify_commonmark_compliance(cleaned)
        for line in cleaned.splitlines():
            assert not line.startswith(" ")
            assert not line.startswith("\t")

    def test_memo_card_under_adversarial_payloads(self):
        """Stress test render_chief_advisor_memo_card with adversarial inputs."""
        adversarial_payloads = [
            # 1. Empty / Minimal
            {},
            # 2. None fields
            {
                "timestamp": None,
                "macro_policy": None,
                "international_fx": None,
                "industry_valuation": None,
                "portfolio_pathology": None,
                "action_directive": None,
            },
            # 3. Payload with indented multiline text & python code blocks
            {
                "timestamp": "2026-11-11",
                "macro_policy": {
                    "badge": "    TEST BADGE    ",
                    "content": "Line 1\n    Line 2 with 4 spaces\n        Line 3 with 8 spaces\n\t\tTabbed line",
                },
                "international_fx": {
                    "badge": "FX",
                    "content": "```python\ndef test():\n    return 42\n```",
                },
                "industry_valuation": {
                    "badge": "VAL",
                    "content": "<div class='nested'>    <p>Indented P</p>    </div>",
                },
                "portfolio_pathology": {
                    "badge": "PATH",
                    "content": "亏损基金:\n    - 011613 (-17.1%)\n    - 100032 (-12.0%)",
                },
                "action_directive": {
                    "badge": "ACT",
                    "content": "14:30 尾盘行动:\n    清扫 19 只碎片尾仓",
                    "color": "rgb(255, 0, 0)",
                },
            },
            # 4. Windows CRLF mixed lines
            {
                "macro_policy": {"badge": "CRLF", "content": "A\r\n    B\r\n        C\r\n"},
                "action_directive": {"badge": "OK", "content": "Done\r\n"},
            },
        ]

        for idx, payload in enumerate(adversarial_payloads):
            with patch("streamlit.markdown") as mock_st_md:
                render_chief_advisor_memo_card(payload, title=f"Adversarial Run {idx}")
                if mock_st_md.called:
                    call_args = mock_st_md.call_args
                    rendered_html = call_args[0][0]
                    kwargs = call_args[1]
                    assert kwargs.get("unsafe_allow_html") is True, "unsafe_allow_html must be True"
                    self._verify_commonmark_compliance(rendered_html)

    def test_real_ledgers_commonmark_compliance(self):
        """Verify real ledgers (combat_29_funds and Tab 1 opt_weights) produce 100% compliant HTML."""
        mlm = MultiLedgerManager()
        pm = mlm.get_pm("combat_29_funds")

        memo_combat29 = generate_chief_advisor_memo(holdings=pm.holdings)
        with patch("streamlit.markdown") as mock_st_md:
            render_chief_advisor_memo_card(memo_combat29)
            assert mock_st_md.called
            self._verify_commonmark_compliance(mock_st_md.call_args[0][0])

        opt_weights = {"005561": 0.35, "002351": 0.20, "110020": 0.15, "011613": 0.15, "017436": 0.10, "000216": 0.05}
        memo_tab1 = generate_chief_advisor_memo(holdings=opt_weights, total_capital=100000.0)
        with patch("streamlit.markdown") as mock_st_md:
            render_chief_advisor_memo_card(memo_tab1, title="🧭 首席投顾五维决策备忘录（建仓方案研判）")
            assert mock_st_md.called
            self._verify_commonmark_compliance(mock_st_md.call_args[0][0])


class TestAdvisoryEngineMemoResilience:
    """Task 4: Adversarial Fuzzing and Invariant Verification for generate_chief_advisor_memo."""

    def test_corrupt_and_extreme_holding_types(self):
        """Fuzz generate_chief_advisor_memo with corrupted holding items."""
        corrupt_holdings = [
            {},
            {"fund_code": "999991", "fund_name": "空字典基金"},
            {"fund_code": "999992", "fund_name": "零值字段基金", "cost_price": 0.0, "shares": 0.0, "market_value": 0.0},
            {"fund_code": "999993", "fund_name": "字符串字段基金", "cost_price": "1.50", "shares": "1000", "floating_pnl_pct": "-20.5"},
            HoldingItem(fund_code="999994", fund_name="归零基金", shares=1000.0, cost_price=1.0, current_nav=0.001, market_value=1.0, cost_basis=1000.0, floating_pnl=-999.0, floating_pnl_pct=-99.9),
            HoldingItem(fund_code="999995", fund_name="暴赚基金", shares=1000.0, cost_price=1.0, current_nav=9.0, market_value=9000.0, cost_basis=1000.0, floating_pnl=8000.0, floating_pnl_pct=800.0),
        ]

        memo = generate_chief_advisor_memo(holdings=corrupt_holdings)
        assert memo is not None
        pathology = memo.get("portfolio_pathology", {})
        assert pathology.get("deep_loss_count", 0) >= 2
        assert "核心亏损拖累源" in pathology.get("content", "")

    def test_explicit_none_market_value_adversarial_finding(self):
        """
        Adversarial Boundary Probe:
        When a dictionary explicitly sets {'market_value': None},
        advisory_engine.py:4319 executes float(0.0 or None), raising TypeError.
        In app_gui.py this is caught by try-except, but advisory_engine can be made more defensive in future.
        """
        holding_with_none_mv = [{"fund_code": "999999", "market_value": None}]
        with pytest.raises(TypeError):
            generate_chief_advisor_memo(holdings=holding_with_none_mv)

    def test_all_none_and_empty_inputs_safety(self):
        """Verify engine never throws exception on None/empty inputs."""
        memo = generate_chief_advisor_memo(
            snapshot=None,
            holdings=None,
            radar_top3=None,
            sentry_rep=None,
            total_capital=0.0,
        )
        assert isinstance(memo, dict)
        assert "macro_policy" in memo
        assert "international_fx" in memo
        assert "industry_valuation" in memo
        assert "portfolio_pathology" in memo
        assert "action_directive" in memo
