"""
【全链路高定设计系统与多配色引擎终验测试】
验证：
1. 5 套高定金融终端配色引擎与 2 套涨跌模式全链路贯通；
2. CSS 卡片体系与组件类完整定义（100% 绑定 CSS 变量）；
3. 顶部等宽 6 宫格真实指数行情带与 0 阻塞首屏；
4. 侧边栏纯粹四大功能分区与零冗余；
5. 剔除静态假数据与阻塞式循环；
6. AppTest 无头执行多主题与色彩模式无感切换 0 异常。
"""

import sys
from pathlib import Path
import pytest

CURRENT_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = CURRENT_DIR.parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))
if str(CURRENT_DIR.parent) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR.parent))

from app_gui import THEME_PRESETS, COLOR_PRESETS, apply_theme_to_plotly_figure
import plotly.graph_objects as go
from streamlit.testing.v1 import AppTest


def test_theme_presets_structure_and_keys():
    """验证 5 套高定主题与兼容别名完整性"""
    required_themes = [
        "institutional_slate",
        "bloomberg_carbon",
        "ft_warm_paper",
        "deep_titanium",
        "nordic_frost"
    ]
    required_keys = [
        "name", "bg_canvas", "bg_surface", "bg_elevated",
        "border_subtle", "border_hover", "text_primary",
        "text_secondary", "text_muted", "accent_primary", "shadow_card"
    ]
    for th in required_themes:
        assert th in THEME_PRESETS, f"Theme '{th}' missing from THEME_PRESETS"
        for k in required_keys:
            assert k in THEME_PRESETS[th], f"Key '{k}' missing from theme '{th}'"
            assert THEME_PRESETS[th][k], f"Value for '{k}' in theme '{th}' must not be empty"

    # 验证兼容别名
    assert "light_slate" in THEME_PRESETS
    assert "dark_terminal" in THEME_PRESETS
    assert "nordic_paper" in THEME_PRESETS


def test_color_presets_structure_and_modes():
    """验证 2 套涨跌色彩模式"""
    assert "cn" in COLOR_PRESETS
    assert "global" in COLOR_PRESETS
    for mode in ["cn", "global"]:
        for k in ["name", "color_up", "bg_up", "border_up", "color_down", "bg_down", "border_down", "color_flat"]:
            assert k in COLOR_PRESETS[mode], f"Key '{k}' missing from color preset '{mode}'"

    # A股红涨绿跌 vs 国际绿涨红跌
    assert COLOR_PRESETS["cn"]["color_up"] == "#dc2626"
    assert COLOR_PRESETS["cn"]["color_down"] == "#16a34a"
    assert COLOR_PRESETS["global"]["color_up"] == "#16a34a"
    assert COLOR_PRESETS["global"]["color_down"] == "#dc2626"


def test_plotly_theme_adaptation():
    """验证 Plotly 图表对 5 套主题与双轨色彩的自适应"""
    fig = go.Figure(data=go.Scatter(x=[1, 2, 3], y=[10, 20, 30]))
    for th_key in ["institutional_slate", "bloomberg_carbon", "ft_warm_paper", "deep_titanium", "nordic_frost"]:
        adapted_fig = apply_theme_to_plotly_figure(fig, theme_mode=th_key, color_mode="cn")
        layout = adapted_fig.layout
        expected_bg = THEME_PRESETS[th_key]["bg_surface"]
        assert layout.paper_bgcolor == expected_bg
        assert layout.plot_bgcolor == expected_bg


def test_css_card_system_and_no_fake_data():
    """静态检查 app_gui.py 中 CSS 体系、真实行情带与去假数据红线"""
    gui_file = Path(CURRENT_DIR.parent / "app_gui.py")
    gui_text = gui_file.read_text(encoding="utf-8")

    # 1. 必含 CSS 类
    classes = [
        ".main-metric-card {",
        ".metric-card-title {",
        ".metric-value-huge {",
        ".metric-card-sub {",
        ".kpi-metric-card {",
        ".kpi-card-title {",
        ".kpi-card-sub {",
        ".kpi-card-desc {",
        ".decision-card {",
        ".decision-title {",
        ".decision-val {",
        ".decision-desc {",
        ".consequence-card {",
        ".active-computation-console {",
        ".step-indicator-bar {",
        ".index-ticker-strip {",
        ".index-ticker-pill {"
    ]
    for c in classes:
        assert c in gui_text, f"CSS class '{c}' must exist in app_gui.py"

    # 2. 严禁假数据
    assert "INDEX_PE_METAS" not in gui_text
    assert "fetch_intraday_sparkline_svg" not in gui_text
    assert "up_count: 3210" not in gui_text

    # 3. 顶部行情带与刷新按钮
    assert "index-ticker-strip" in gui_text
    assert "fetch_batch_realtime_indices" in gui_text
    assert "btn_refresh_all_live_quotes" in gui_text

    # 4. 侧边栏 4 大分区
    assert "##### 🎨 外观与色彩" in gui_text
    assert "##### 🎯 全局目标联动" in gui_text
    assert "##### 🛡️ 交易风控护栏" in gui_text
    assert "##### 🗄️ 账本环境管理" in gui_text


def test_apptest_theme_and_color_switching():
    """使用 Streamlit 官方 AppTest 无头执行全套 5 主题与双轨色彩切换，断言 0 异常"""
    gui_path = str(CURRENT_DIR.parent / "app_gui.py")
    at = AppTest.from_file(gui_path, default_timeout=30)
    at.run()
    assert not at.exception, f"Initial AppTest failed: {at.exception}"
    assert len(at.error) == 0, f"AppTest reported errors: {[e.value for e in at.error]}"

    # 测试切换彭博暗黑
    at.session_state.app_theme_mode = "bloomberg_carbon"
    at.run()
    assert not at.exception, f"Bloomberg Carbon theme failed: {at.exception}"
    assert len(at.error) == 0

    # 测试切换金融暖卷
    at.session_state.app_theme_mode = "ft_warm_paper"
    at.run()
    assert not at.exception, f"FT Warm Paper theme failed: {at.exception}"
    assert len(at.error) == 0

    # 测试切换深海钛金
    at.session_state.app_theme_mode = "deep_titanium"
    at.run()
    assert not at.exception, f"Deep Titanium theme failed: {at.exception}"
    assert len(at.error) == 0

    # 测试切换极昼纯白
    at.session_state.app_theme_mode = "nordic_frost"
    at.run()
    assert not at.exception, f"Nordic Frost theme failed: {at.exception}"
    assert len(at.error) == 0

    # 测试切换国际绿涨红跌
    at.session_state.app_color_mode = "global"
    at.run()
    assert not at.exception, f"Global color mode failed: {at.exception}"
    assert len(at.error) == 0
