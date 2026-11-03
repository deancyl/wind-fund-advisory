"""
AGY2 智能投顾交互连续性与状态闭环集成测试 (test_interactive_continuity.py)
验证 4 大收官交互逻辑断层修复：
1. 模式 B 问卷测评定档正常切换与评定结论；
2. 步骤一重新推演时自动收起步骤三并清空旧建仓缓存；
3. Tab 2 调仓目标池切换联动与持仓变更缓存失效；
4. Tab 2 盘中观察期防冲动执行锁。
"""

import sys
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest

# 路径对齐
WORKSPACE_DIR = Path(__file__).resolve().parent.parent.parent
AGY2_DIR = WORKSPACE_DIR / "AGY2_FundAdvisory"
if str(AGY2_DIR) not in sys.path:
    sys.path.insert(0, str(AGY2_DIR))

import portfolio_manager
from portfolio_manager import PortfolioManager, FundQuote
import strategy_bridge
from strategy_bridge import StrategyBridge, evaluate_questionnaire_risk_tier


@pytest.fixture(autouse=True)
def mock_network_and_quotes(monkeypatch):
    """全局 Mock 行情与网络，实现毫秒级纯本地离线测试"""
    def mock_fund_quote(code, use_cache=True):
        return FundQuote(
            name=f"测试基金_{code}",
            dwjz=1.2345,
            gsz=1.2400,
            gszzl=0.45,
            gztime="14:45",
            fund_code=str(code)
        )

    def mock_index_quote(symbol, use_cache=True):
        return {"point": 4050.0, "change_pct": 0.5, "name": symbol}

    monkeypatch.setattr(portfolio_manager, "fetch_realtime_fund_quote", mock_fund_quote)
    monkeypatch.setattr(portfolio_manager, "fetch_realtime_index_quote", mock_index_quote)


def test_mode_b_questionnaire_apptest():
    """测试 1: 模式 B 问卷测评定档分支与自动映射"""
    app_path = AGY2_DIR / "app_gui.py"
    at = AppTest.from_file(str(app_path), default_timeout=60)
    
    # 初始化为模式 B
    at.session_state.tier_determination_mode = "模式 B：30秒风险承受力测评定档"
    at.session_state.q1_risk_test = "E. 哪怕腰斩 -30% 也无所谓，求翻倍 (4分)"
    at.session_state.q2_risk_test = "E. 5年以上闲钱 (4分)"
    at.session_state.q3_risk_test = "E. 兴奋狂喜，大举逆势加仓 (4分)"
    at.run()

    assert len(at.exception) == 0, f"模式 B 渲染异常: {[e.value for e in at.exception]}"
    # 满分 12 分应评定为 C5 档位，默认目标收益为 50.0%
    assert at.session_state.active_tier_val == "C5"
    assert at.session_state.target_return_val == 50.0


def test_step1_re_simulation_collapses_step3():
    """测试 2: 在步骤三时点击步骤一推演按钮，自动收起步骤三并清空旧缓存"""
    app_path = AGY2_DIR / "app_gui.py"
    at = AppTest.from_file(str(app_path), default_timeout=60)

    # 模拟用户此前已经算到了步骤三
    at.session_state.tab1_step_reached = 3
    at.session_state.tab1_step3_cache = {"blueprint": {"orders": []}}
    at.session_state.tab1_sim_cache = {"optimal_weights": {"100032": 0.5, "005561": 0.5}}
    at.session_state.target_return_val = 20.0
    at.run()

    assert len(at.exception) == 0
    assert at.session_state.tab1_step_reached == 3

    # 点击步骤一的【▶️ 确认目标参数，进入步骤二：开始现场推演】按钮
    btn = at.button(key="btn_run_simulation_now")
    btn.click()
    at.run()

    assert len(at.exception) == 0
    # 核心断言：步骤状态必须回退收起到步骤 2，旧的步骤 3 缓存必须被清空
    assert at.session_state.tab1_step_reached == 2
    assert at.session_state.tab1_step3_cache is None


def test_tab2_target_pool_selection_and_cache_invalidation():
    """测试 3: Tab 2 调仓目标池选择与持仓修改自动失效旧诊断缓存"""
    app_path = AGY2_DIR / "app_gui.py"
    at = AppTest.from_file(str(app_path), default_timeout=60)

    # 设置当前处于调仓步骤三
    at.session_state.tab2_diagnosed = True
    at.session_state.tab2_rebalanced = True
    at.session_state.tab1_sim_cache = {
        "optimal_weights": {"100032": 0.4, "005561": 0.3, "000216": 0.3}
    }
    at.run()

    assert len(at.exception) == 0

    # 验证单选框存在
    rad = at.radio(key="rad_tab2_target_pool")
    assert rad is not None
    assert "新资建仓" in rad.options[0]
    assert "核心指数全天候策略池" in rad.options[1]

    # 测试持仓重置：点击“加载演示组合”后，旧的诊断与调仓缓存应被清空
    at.session_state.tab2_diag_cache = {"health": "mock"}
    at.session_state.tab2_rebal_cache = {"rebal": "mock"}
    
    # 触发彻底删除或重置
    btn_demo = at.sidebar.button[0] # 加载演示组合
    btn_demo.click()
    at.run()

    assert len(at.exception) == 0
    assert at.session_state.tab2_diag_cache is None
    assert at.session_state.tab2_rebal_cache is None
    assert at.session_state.tab2_diagnosed is False
    assert at.session_state.tab2_rebalanced is False


def test_observation_window_lock():
    """测试 4: 盘中观察期防冲动执行锁逻辑验证"""
    from datetime import datetime
    from trading_clock_fee import TradingClock
    clock = TradingClock()

    base_day = datetime(2026, 11, 3) # 周二工作日

    # 验证在盘中观察期（如 10:00）状态为 OBSERVATION
    dt_obs = base_day.replace(hour=10, minute=0, second=0)
    stage_obs = clock.get_action_guidance_for_window(dt_obs)["stage"]
    assert stage_obs == "OBSERVATION"

    # 验证在尾盘黄金窗口（14:40）状态为 GOLDEN_WINDOW
    dt_gold = base_day.replace(hour=14, minute=40, second=0)
    stage_gold = clock.get_action_guidance_for_window(dt_gold)["stage"]
    assert stage_gold == "GOLDEN_WINDOW"

    # 验证在盘后（15:10）状态为 POST_MARKET
    dt_post = base_day.replace(hour=15, minute=10, second=0)
    stage_post = clock.get_action_guidance_for_window(dt_post)["stage"]
    assert stage_post == "POST_MARKET"
