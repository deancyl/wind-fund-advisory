"""
Challenger G13 Milestone 2 Empirical Adversarial Stress Test Suite
(tests/test_challenger_g13_m2.py)
"""

import ast
import re
import subprocess
import pytest
from pathlib import Path
from streamlit.testing.v1 import AppTest

GUI_PATH = (Path(__file__).parent.parent / "AGY2_FundAdvisory" / "app_gui.py").resolve()

def test_ast_validity_and_syntax():
    """Verify that app_gui.py has 100% valid Python AST without syntax errors."""
    code = GUI_PATH.read_text(encoding="utf-8")
    tree = ast.parse(code, filename=str(GUI_PATH))
    assert tree is not None
    assert len(tree.body) > 0


def test_zero_prohibited_buttons_and_col_wing():
    """Adversarially search for any leftover prohibited buttons or columns."""
    code = GUI_PATH.read_text(encoding="utf-8")
    
    prohibited_keys = [
        "btn_master_action_switch",
        "btn_batch_lock_all_7d",
        "btn_add_radar_pool_",
        "btn_sentry_act_",
        "btn_sentry_evid_",
        "col_wing_btn",
    ]
    
    for key in prohibited_keys:
        matches = [idx + 1 for idx, line in enumerate(code.splitlines()) if key in line]
        assert len(matches) == 0, f"Prohibited key '{key}' found at lines {matches}"


def test_zero_duplicate_tab_subheaders():
    """Verify that all duplicate subheaders in Tab 1, 2, 3, 4 are absent."""
    code = GUI_PATH.read_text(encoding="utf-8")
    lines = code.splitlines()
    
    prohibited_subheaders = [
        "🌱 新资建仓",
        "💼 持仓调仓",
        "📈 组合回测",
        "🔍 穿透工具",
    ]
    
    for sub in prohibited_subheaders:
        regex = rf'st\.subheader\s*\(\s*["\'].*{re.escape(sub)}.*["\']\s*\)'
        matches = [idx + 1 for idx, l in enumerate(lines) if re.search(regex, l)]
        assert len(matches) == 0, f"Found duplicate subheader '{sub}' at lines {matches}"


def test_css_navigation_segmented_pill_bar_and_isolation():
    """Verify full-width segmented pill bar CSS rules and secondary tab isolation."""
    code = GUI_PATH.read_text(encoding="utf-8")
    
    # 1. Grid 4 columns
    assert "grid-template-columns: repeat(4, 1fr) !important;" in code
    
    # 2. Tab button dimensions & styles
    assert "height: 46px !important;" in code
    assert "font-size: 16px !important;" in code
    assert "font-weight: 700 !important;" in code
    
    # 3. Active state
    assert "var(--accent-primary)" in code
    assert "box-shadow: 0 4px 12px rgba(29, 78, 216, 0.25) !important;" in code
    
    # 4. Strict isolation for Tab 4 sub-tabs
    assert ':not([data-testid="stTabContent"]' in code
    assert '[data-testid="stTabContent"] [data-testid="stTabs"]' in code


def test_tab3_backtest_figure_legend_and_bias_defense():
    """Verify Tab 3 Plotly chart legend floating and survivor bias warning card."""
    code = GUI_PATH.read_text(encoding="utf-8")
    
    # Legend floating outside chart area
    assert "y=1.06" in code
    assert "t=75" in code
    
    # Survivor bias warning card and OOS benchmark switch
    assert "当前持仓静态权重历史回溯（含历史后视镜权重效应" in code
    assert "tgl_compare_oos_dynamic" in code


def test_tab4_top_columns_merger_and_six_subtabs():
    """Verify Tab 4 compact top columns and 6 sub-tabs."""
    code = GUI_PATH.read_text(encoding="utf-8")
    
    assert "col_top_sel, col_top_badges = st.columns([3.8, 6.2])" in code
    assert "box_tab1, box_tab2, box_tab3, box_tab4, box_tab5, box_tab6 = st.tabs" in code


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
    import importlib
    import AGY2_FundAdvisory.app_gui
    assert AGY2_FundAdvisory.app_gui is not None
