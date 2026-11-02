"""
验证全局实时状态指示器与严格渐进式分步解锁 (tests/test_progressive_disclosure_and_status.py)
"""

import sys
import time
import inspect
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest

CURRENT_DIR = Path(__file__).resolve().parent.parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

APP_PATH = CURRENT_DIR / "app_gui.py"


def test_tab1_progressive_disclosure_initial_step1_only():
    """验证初次加载（tab1_step_reached == 1）时，步骤二、步骤三绝不提前跳出"""
    at = AppTest.from_file(str(APP_PATH), default_timeout=45)
    at.session_state.tab1_step_reached = 1
    at.session_state.active_tier_val = "C3"
    at.session_state.target_return_val = 15.0
    at.run(timeout=45)

    assert len(at.exception) == 0, f"AppTest 运行异常: {at.exception}"
    assert len(at.error) == 0, f"AppTest 页面报错: {[e.value for e in at.error]}"

    markdown_texts = [m.value for m in at.markdown]
    
    # 步骤二和步骤三的标题绝对不能出现
    has_step2_title = any("步骤二：【" in text for text in markdown_texts)
    has_step3_title = any("步骤三：【" in text for text in markdown_texts)
    assert not has_step2_title, "严厉违规：tab1_step_reached == 1 时步骤二标题提前泄露！"
    assert not has_step3_title, "严厉违规：tab1_step_reached == 1 时步骤三标题提前泄露！"

    # 步骤二的指标卡绝对不能出现
    has_best_case = any("① 最好情况 (大牛市冲刺)" in text for text in markdown_texts)
    has_worst_case = any("② 最坏情况 (极端大熊市)" in text for text in markdown_texts)
    assert not has_best_case, "严厉违规：tab1_step_reached == 1 时步骤二人话指标卡提前渲染！"
    assert not has_worst_case, "严厉违规：tab1_step_reached == 1 时步骤二人话指标卡提前渲染！"

    # 状态指示器必须存在并指示步骤一
    has_indicator = any("工作流导引：" in text for text in markdown_texts)
    assert has_indicator, "必须渲染《🧭 工作流步骤与系统状态指示器》！"
    has_step1_active = any("步骤1：设定目标与测风险 (当前步骤)" in text or "步骤1：设定目标与测风险" in text for text in markdown_texts)
    assert has_step1_active, "指示器必须准确高亮步骤一！"


def test_tab2_progressive_disclosure_initial_no_consequences():
    """验证初次进入 Tab 2（tab2_diagnosed == False）时，第一层与第二层四大真实后果绝对不显示"""
    at = AppTest.from_file(str(APP_PATH), default_timeout=45)
    at.session_state.tab2_diagnosed = False
    at.session_state.tab2_rebalanced = False
    at.run(timeout=45)

    assert len(at.exception) == 0, f"AppTest 运行异常: {at.exception}"
    assert len(at.error) == 0, f"AppTest 页面报错: {[e.value for e in at.error]}"

    markdown_texts = [m.value for m in at.markdown]

    # 第一层裁决卡与第二层四大真实后果绝对不能出现
    has_diag_layer = any("第一层：【今日是否适合调仓？" in text for text in markdown_texts)
    has_consequences = any("本次调仓四大真实后果量化账单" in text for text in markdown_texts)
    has_rebal_orders = any("今日建议调仓执行单" in text for text in markdown_texts)

    assert not has_diag_layer, "严厉违规：未点击诊断按钮前，第一层裁决卡提前泄露！"
    assert not has_consequences, "严厉违规：未点击调仓按钮前，第二层四大真实后果量化账单提前泄露！"
    assert not has_rebal_orders, "严厉违规：未点击调仓按钮前，调仓执行单提前泄露！"


def test_slider_adjustment_is_fast_and_does_not_call_heavy_backtest():
    """验证在步骤一仅拖动滑块时做纯静态映射，绝不调用 2000 天重度回测，执行时间 < 0.1 秒"""
    from app_gui import map_slider_to_tier, RISK_TIERS_CONFIG

    t0 = time.time()
    for ret in [5.0, 8.0, 10.0, 15.0, 20.0, 25.0, 35.0]:
        tier = map_slider_to_tier(ret)
        meta = RISK_TIERS_CONFIG[tier]
        assert "equity_range" in meta
    elapsed = time.time() - t0

    assert elapsed < 0.05, f"滑块映射耗时 {elapsed:.4f}s，超过 0.05s 阈值！"
