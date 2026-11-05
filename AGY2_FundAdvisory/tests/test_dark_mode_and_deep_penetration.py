# -*- coding: utf-8 -*-
"""
AGY2_FundAdvisory/tests/test_dark_mode_and_deep_penetration.py
验证深色模式全组件修复与原生穿透：
1. THEME_PRESETS 中 is_dark 布尔标志
2. 深浅色高对比度明度提升 (亮红 #f87171, 亮绿 #4ade80)
3. Glide Data Grid CSS 变量穿透
4. 原生文本、表单、指标卡、输入框、下拉框、次级按钮与弹窗的深色绑定
5. Plotly title_font_color 适配
6. AppTest 在 5 大主题下全屏渲染 0 异常
"""

from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest
import sys

CURRENT_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = CURRENT_DIR.parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))
if str(CURRENT_DIR.parent) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR.parent))

from app_gui import THEME_PRESETS, COLOR_PRESETS, apply_theme_to_plotly_figure
import plotly.graph_objects as go

GUI_FILE = str(CURRENT_DIR.parent / "app_gui.py")


def test_theme_presets_is_dark_flag():
    """验证每个主题具有 is_dark 字段，且暗色主题准确标记"""
    for key in ["light_slate", "dark_terminal", "nordic_paper", "deep_titanium", "nordic_frost"]:
        assert key in THEME_PRESETS, f"Theme {key} missing in THEME_PRESETS"
        assert "is_dark" in THEME_PRESETS[key], f"is_dark flag missing in theme {key}"
        assert isinstance(THEME_PRESETS[key]["is_dark"], bool)

    assert THEME_PRESETS["dark_terminal"]["is_dark"] is True
    assert THEME_PRESETS["deep_titanium"]["is_dark"] is True
    assert THEME_PRESETS["light_slate"]["is_dark"] is False
    assert THEME_PRESETS["nordic_paper"]["is_dark"] is False
    assert THEME_PRESETS["nordic_frost"]["is_dark"] is False

    # 验证深海钛金主强调色为高明度亮金黄
    assert THEME_PRESETS["deep_titanium"]["accent_primary"] == "#fbbf24"


def test_high_contrast_color_mode_adaptation():
    """验证在暗色主题下文字明度自动提高"""
    with open(GUI_FILE, "r", encoding="utf-8") as f:
        gui_text = f.read()

    # 验证包含高明度亮红与亮绿的动态切换逻辑
    assert "#f87171" in gui_text
    assert "#4ade80" in gui_text
    assert "is_dark_active" in gui_text


def test_glide_data_grid_and_native_css_penetration():
    """验证 Glide Data Grid 变量与原生组件深色样式全覆盖"""
    with open(GUI_FILE, "r", encoding="utf-8") as f:
        gui_text = f.read()

    # Glide Data Grid 官方变量
    gdg_vars = [
        "--gdg-bg-cell",
        "--gdg-bg-header",
        "--gdg-text-dark",
        "--gdg-text-medium",
        "--gdg-text-header",
        "--gdg-border-color"
    ]
    for gv in gdg_vars:
        assert gv in gui_text, f"Missing GDG variable '{gv}'"

    # 原生组件选择器覆盖
    native_selectors = [
        '[data-testid="stDataFrame"]',
        '[data-testid="stWidgetLabel"]',
        '[data-testid="stMetricLabel"]',
        '[data-testid="stMetricValue"]',
        'div[data-baseweb="select"]',
        'div[data-baseweb="input"]',
        '[data-testid="stNumberInputContainer"]',
        'button[kind="secondary"]',
        '[data-testid="stPopover"]',
        'div[data-baseweb="popover"]'
    ]
    for sel in native_selectors:
        assert sel in gui_text, f"Missing native selector '{sel}' in CSS"


def test_plotly_theme_title_font_color():
    """验证 Plotly 主题应用已注入 title_font_color"""
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[1, 2], y=[3, 4], name="Test"))
    fig.update_layout(title="Test Chart")

    # 应用深色主题
    fig_themed = apply_theme_to_plotly_figure(fig, theme_mode="dark_terminal")
    assert fig_themed.layout.paper_bgcolor == THEME_PRESETS["dark_terminal"]["bg_surface"]
    assert fig_themed.layout.title.font.color == THEME_PRESETS["dark_terminal"]["text_primary"]

    # 应用浅色主题
    fig_light = apply_theme_to_plotly_figure(fig, theme_mode="light_slate")
    assert fig_light.layout.paper_bgcolor == THEME_PRESETS["light_slate"]["bg_surface"]
    assert fig_light.layout.title.font.color == THEME_PRESETS["light_slate"]["text_primary"]


@pytest.mark.parametrize("theme_key", ["light_slate", "dark_terminal", "nordic_paper", "deep_titanium", "nordic_frost"])
def test_apptest_all_five_themes_zero_exception(theme_key):
    """Streamlit AppTest 运行：在全套 5 种主题下全屏渲染 0 异常"""
    at = AppTest.from_file(GUI_FILE, default_timeout=35)
    at.session_state["app_theme_mode"] = theme_key
    at.run()
    assert not at.exception, f"Theme '{theme_key}' failed with exception: {at.exception}"
    assert len(at.error) == 0, f"Theme '{theme_key}' reported errors: {[e.value for e in at.error]}"
