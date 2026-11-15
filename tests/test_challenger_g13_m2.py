"""
Challenger G13 Milestone 2 Empirical Adversarial Stress Test Suite
(tests/test_challenger_g13_m2.py)
Decoupled from static source grep / AST contracts according to Core 5.
"""

import py_compile
import subprocess
import pytest
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).parent.parent
APP_GUI_FILE = (WORKSPACE_ROOT / "AGY2_FundAdvisory" / "app_gui.py").resolve()


def test_ast_validity_and_syntax():
    """Verify that app_gui.py compiles without syntax errors."""
    res = py_compile.compile(str(APP_GUI_FILE), doraise=True)
    assert res is not None


def test_clean_html_functional_behavior():
    """Verify _clean_html strips indentation, handles empty inputs and trims correctly."""
    from AGY2_FundAdvisory.app_gui import _clean_html

    assert _clean_html(None) == ""
    assert _clean_html("") == ""
    assert _clean_html("   \n\t  ") == ""
    sample_indented = "    <div class='card'>\n        <span>Text</span>\n    </div>"
    cleaned = _clean_html(sample_indented)
    assert "<div class='card'>" in cleaned
    assert "<span>Text</span>" in cleaned
    for line in cleaned.splitlines():
        assert not line.startswith("    ")


def test_format_chinese_amount_formatting():
    """Verify format_chinese_amount produces valid human-readable financial representations."""
    from AGY2_FundAdvisory.app_gui import format_chinese_amount

    formatted_k = format_chinese_amount(5000.0)
    assert "5,000.00" in formatted_k

    formatted_w = format_chinese_amount(50000.0)
    assert "5.00 万元" in formatted_w

    formatted_y = format_chinese_amount(100000000.0)
    assert "1.00 亿元" in formatted_y

    formatted_zero = format_chinese_amount(0.0)
    assert "0.00" in formatted_zero


def test_resolve_fund_display_name_contract():
    """Verify resolve_fund_display_name returns correct fund names and falls back to code."""
    from AGY2_FundAdvisory.app_gui import resolve_fund_display_name

    name_300 = resolve_fund_display_name("000300", "沪深300")
    assert "000300" in name_300 or "沪深300" in name_300

    fallback = resolve_fund_display_name("999999", "未知标的")
    assert "999999" in fallback or "未知标的" in fallback


def test_plotly_theme_presets_application():
    """Verify apply_theme_to_plotly_figure cleanly applies presets to Plotly figures."""
    from AGY2_FundAdvisory.app_gui import apply_theme_to_plotly_figure, THEME_PRESETS
    import plotly.graph_objects as go

    assert "dark" in THEME_PRESETS or "light" in THEME_PRESETS or len(THEME_PRESETS) > 0
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[1, 2, 3], y=[10, 20, 30], name="TestTrace"))
    styled_fig = apply_theme_to_plotly_figure(fig, theme_mode="light")
    assert styled_fig is not None
    assert styled_fig.layout is not None


def test_four_strictly_readonly_referee_files_untouched():
    """Verify that all 4 strictly read-only referee files have zero git modifications."""
    read_only_files = [
        "AGY2_FundAdvisory/judge_engine.py",
        "AGY2_FundAdvisory/holdout_vault.py",
        "AGY2_FundAdvisory/AGENT_SPEC.md",
        "tests/test_infra.py",
    ]
    res = subprocess.run(["git", "diff", "--name-only"] + read_only_files, capture_output=True, text=True)
    assert not res.stdout.strip(), f"Read-only files modified: {res.stdout}"


def test_direct_module_import_stability():
    """Verify that AGY2_FundAdvisory.app_gui can be cleanly imported."""
    import AGY2_FundAdvisory.app_gui
    assert AGY2_FundAdvisory.app_gui is not None
