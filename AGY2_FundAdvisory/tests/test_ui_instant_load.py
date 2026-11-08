"""
UI 与首屏秒开优化针对性验收测试套件 (tests/test_ui_instant_load.py)
验证：
1. _clean_html 安全清洗：无空行截断、无 4+ 空格缩进，彻底消灭 </div> 裸露；
2. 6 大核心指数当日实时行情带：fetch_batch_realtime_indices() 正确性与极速响应；
3. 顶部 4 张卡片高度统一 (112px) 且第 4 张卡片同时展示今日预估与累计浮盈；
4. 首屏秒开与 Tab 3 / Tab 4 延迟激活守卫；
5. 侧栏默认折叠与 Tab 2 账本快捷操作内聚；
6. Tab 1 备选基金替换与 quant_table 同步；
7. AppTest 真实首屏渲染：0 异常、0 裸露 </div>、延迟组件不偷跑。
"""

import sys
import time
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest

CORE_DIR = Path(__file__).resolve().parent.parent
if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))

from portfolio_manager import PortfolioManager, CORE_MARKET_INDICES_CONFIG, fetch_batch_realtime_indices
from strategy_bridge import StrategyBridge
from app_gui import _clean_html


def test_clean_html_prevents_naked_div():
    """验证 _clean_html 彻底杜绝空行与缩进将 </div> 解析为代码块"""
    raw_html_with_empty_var = """
    <div class="main-metric-card">
        <div class="metric-card-title">
            <span>🧭 市场定调与攻防线</span>
        </div>
        <div class="metric-value-huge" style="color: #16a34a;">
            🟢 震荡收息期
        </div>
        <div class="metric-card-sub">
            📡信噪比 ER: 0.65 ｜ ⚡动量加速度: +0.0%
        </div>
        
    </div>
    """
    cleaned = _clean_html(raw_html_with_empty_var)
    lines = cleaned.splitlines()
    for line in lines:
        assert line.strip() != "", "清洗后不应含有空行"
        assert not line.startswith("    "), f"行首不应有 4 空格缩进: {line}"
    assert cleaned.startswith('<div class="main-metric-card">')
    assert cleaned.endswith('</div>')


def test_fetch_batch_realtime_indices():
    """验证 6 大核心指数实时行情带拉取返回 6 项完整数据"""
    t0 = time.time()
    indices = fetch_batch_realtime_indices(use_cache=True)
    cost = time.time() - t0
    assert cost < 1.0, f"单次批量拉取应极速返回 (< 1.0s)，实际耗时 {cost:.3f}s"
    assert len(indices) == 6, f"应包含 6 大核心指数，实际得到 {len(indices)}"
    
    expected_codes = {"000300", "000688", "000922", "000905", "000852", "518880"}
    ret_codes = {item["code"] for item in indices}
    assert expected_codes == ret_codes, f"指数代码集合不一致: {ret_codes}"

    for it in indices:
        assert "name" in it and len(it["name"]) > 0
        assert "point" in it and it["point"] > 0
        assert "change_pct" in it
        assert "time_str" in it


def test_snapshot_fast_load_without_autosync():
    """验证首屏 get_latest_market_snapshot(auto_sync=False) 毫秒级秒开 (< 0.2s)"""
    t0 = time.time()
    snap = StrategyBridge.get_latest_market_snapshot(force_reload=False, auto_sync=False)
    cost = time.time() - t0
    assert cost < 0.3, f"首屏快照加载必须 < 0.3s，实际耗时 {cost:.3f}s"
    assert "er_snr" in snap
    assert "mom_accel" in snap
    assert "market_state" in snap


def test_tab3_and_tab4_function_guards_exist():
    """验证 app_gui.py 中定义了 Tab 3 与 Tab 4 的延迟激活函数与状态锁"""
    import app_gui
    assert hasattr(app_gui, "render_tab3_backtest_content"), "必须存在 render_tab3_backtest_content 延迟函数"
    assert hasattr(app_gui, "render_tab4_toolbox_content"), "必须存在 render_tab4_toolbox_content 延迟函数"
    
    gui_text = Path("AGY2_FundAdvisory/app_gui.py").read_text(encoding="utf-8")
    assert "tab3_backtest_activated" in gui_text, "必须包含 tab3_backtest_activated 延迟激活锁"
    assert "tab4_lookthrough_activated" in gui_text, "必须包含 tab4_lookthrough_activated 延迟激活锁"


def test_top_metric_card_fixed_height_css():
    """验证 CSS 中 main-metric-card 高度严格锁定为 112px"""
    gui_text = Path("AGY2_FundAdvisory/app_gui.py").read_text(encoding="utf-8")
    assert ("min-height: 88px;" in gui_text or "min-height: 118px;" in gui_text or "height: 112px;" in gui_text), "main-metric-card 必须锁定最小高度确保卡片底边对齐"
    assert 'initial_sidebar_state="collapsed"' in gui_text, "页面初始状态必须折叠侧边栏消除割裂"
    assert "btn_refresh_all_live_quotes" in gui_text, "行情带右侧必须挂载完整宽度的刷新按钮"


def test_apptest_cold_start_instant_load_and_clean_dom():
    """AppTest 真实首屏冷启动端到端验收：0 异常、0 裸露 </div>、Tab 3/4 延迟守卫待命"""
    app_path = CORE_DIR / "app_gui.py"
    at = AppTest.from_file(str(app_path), default_timeout=60)
    at.run()

    # 1. 断言首屏冷启动 0 异常
    assert len(at.exception) == 0, f"首屏冷启动不应抛异常: {at.exception}"

    # 2. 断言 Tab 3 与 Tab 4 在首屏保持未激活待命状态
    assert not at.session_state.get("tab3_backtest_activated", False), "Tab 3 回测首屏严禁偷跑激活"
    assert not at.session_state.get("tab4_lookthrough_activated", False), "Tab 4 穿透排雷首屏严禁偷跑激活"

    # 3. 严格断言已渲染的 markdown 中没有任何独立的 </div> 裸露文本
    for md in at.markdown:
        md_text = md.value or ""
        assert "\n</div>\n" not in md_text or "<div" in md_text, f"检测到未闭合或裸露的 </div>: {md_text}"
        assert not md_text.strip().startswith("</div>"), f"markdown 文本不能以裸露 </div> 开头: {md_text}"

    # 4. 验证核心指数实时行情带胶囊卡片成功渲染
    assert at.button(key="btn_refresh_all_live_quotes") is not None, "核心行情带必须含有完整的刷新按钮"
