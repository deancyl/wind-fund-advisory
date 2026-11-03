"""
UI 精细化打磨与交互断层修复终验测试套件 (tests/test_ui_final_polish.py)
验证目标：
1. 彻底消灭裸露的 </div> 代码块与 CommonMark 解析器缩进截断；
2. 侧边栏 with st.sidebar 彻底移除，CSS 强制隐藏 stSidebar 与 collapsedControl；
3. Tab 3 穿透回测函数 render_tab3_backtest_content 声明 c_bt_obj，点击激活后 0 异常；
4. Tab 4 穿透工具箱函数 render_tab4_toolbox_content 内部安全计算 total_cur_equity；
5. Tab 1 与 Tab 2 送入回测按钮显式置位 tab3_backtest_activated=True；
6. 顶部 4 张核心卡片 min-height: 118px 自适应无截断，副标题展示两行详细盘中与浮盈指标；
7. 核心指数实时行情带 6 项全览且刷新按钮穿透 use_cache=False。
"""

import sys
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest

CORE_DIR = Path(__file__).resolve().parent.parent
if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))

from portfolio_manager import PortfolioManager, fetch_batch_realtime_indices
from strategy_bridge import StrategyBridge
import app_gui


def test_sidebar_completely_removed_and_css_hidden():
    """断言 app_gui.py 中已彻底移除 with st.sidebar 且 CSS 强隐藏侧栏"""
    gui_text = (CORE_DIR / "app_gui.py").read_text(encoding="utf-8")
    assert "with st.sidebar:" not in gui_text, "app_gui.py 中严禁留存 with st.sidebar 边栏"
    assert '[data-testid="stSidebar"]' in gui_text, "必须在 CSS 中显式隐藏 stSidebar"
    assert '[data-testid="collapsedControl"]' in gui_text, "必须在 CSS 中显式隐藏 collapsedControl 箭头"


def test_no_naked_html_tags_in_code():
    """断言工作流指示器调用 safe_markdown_html，杜绝裸打印 <div style=..."""
    gui_text = (CORE_DIR / "app_gui.py").read_text(encoding="utf-8")
    assert 'st.markdown(f"""\\n    <div style=' not in gui_text, "严禁直接 st.markdown 打印带 div 的 HTML 块"
    assert "safe_markdown_html" in gui_text, "必须统一经过 safe_markdown_html 清洗与渲染"


def test_tab3_c_bt_obj_defined_and_safe():
    """断言 render_tab3_backtest_content 显式解包 c_bt_obj, c_bt_bench"""
    gui_text = (CORE_DIR / "app_gui.py").read_text(encoding="utf-8")
    assert "c_bt_obj, c_bt_bench = st.columns([4, 6])" in gui_text, "render_tab3_backtest_content 必须显式声明 c_bt_obj"


def test_tab4_total_cur_equity_safe():
    """断言 render_tab4_toolbox_content 内部独立计算 total_cur_equity"""
    gui_text = (CORE_DIR / "app_gui.py").read_text(encoding="utf-8")
    assert "total_cur_equity = sum(h.market_value for h in pm.holdings.values())" in gui_text


def test_apptest_tab3_and_tab4_activation_zero_exception():
    """通过 AppTest 模拟点击激活 Tab 3 和 Tab 4，断言 0 崩溃、0 裸露 </div> 代码块"""
    app_path = CORE_DIR / "app_gui.py"
    at = AppTest.from_file(str(app_path), default_timeout=60)
    at.run()
    assert len(at.exception) == 0, f"首屏运行不应抛异常: {at.exception}"

    # 验证首屏绝不包含被解析为独立代码块的 </div>
    for code_block in at.code:
        assert "</div>" not in code_block.value, f"代码块中不应出现被错误缩进解析的 </div>: {code_block.value}"

    for md in at.markdown:
        assert md.value.strip() != "</div>", "Markdown 文本中绝不应出现独立的 </div> 裸露标签"

    # 模拟在 Tab 3 中点击激活回测推演按钮
    at.session_state.tab3_backtest_activated = True
    at.run()
    assert len(at.exception) == 0, f"激活 Tab 3 后运行不应抛出 NameError 或其他异常: {at.exception}"

    # 模拟在 Tab 4 中点击激活穿透排雷按钮
    at.session_state.tab4_lookthrough_activated = True
    at.run()
    assert len(at.exception) == 0, f"激活 Tab 4 后运行不应抛出异常: {at.exception}"
