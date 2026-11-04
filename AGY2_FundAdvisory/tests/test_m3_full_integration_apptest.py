# -*- coding: utf-8 -*-
"""
AGY2_FundAdvisory/tests/test_m3_full_integration_apptest.py
Milestone 3 投顾业务与双翼看板的全链路集成与 Streamlit AppTest 回归测试
"""

import os
import json
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest

CURRENT_DIR = Path(__file__).resolve().parent
GUI_FILE = str(CURRENT_DIR.parent / "app_gui.py")


def test_static_m3_features_in_app_gui():
    """静态 AST/字符串审查：断言 Milestone 3 三大投顾业务已全部绑定且无静态假数据"""
    with open(GUI_FILE, "r", encoding="utf-8") as f:
        gui_text = f.read()

    # 1. 验证三大投顾模块导入与调用
    assert "from advisory_engine import" in gui_text
    assert "OpportunityRadarEngine" in gui_text
    assert "ActiveRiskSentry" in gui_text
    assert "SmartExecutionDCAEngine" in gui_text
    assert "render_dual_wing_advisory_dashboard" in gui_text

    # 2. 验证双翼看板核心展示项
    assert "全市场机会雷达 · Top 3 机会甄选" in gui_text
    assert "主动风险预警哨 · 四维巡检" in gui_text
    assert "btn_add_radar_pool_" in gui_text

    # 3. 验证步骤三三种资金建仓模式
    assert "radio_capital_deployment_mode" in gui_text
    assert "⚡ 一次性建仓" in gui_text
    assert "🌊 稳健三步分批建仓" in gui_text
    assert "📅 估值自适应智能定投" in gui_text
    assert "plan_three_step_batches" in gui_text
    assert "plan_smart_dca" in gui_text

    # 4. 严格断言假数据彻底清零
    assert "INDEX_PE_METAS" not in gui_text
    assert "3210" not in gui_text
    assert "1780" not in gui_text
    assert "fetch_intraday_sparkline_svg" not in gui_text


def test_apptest_gui_with_advisory_dashboard():
    """AppTest 无头运行：断言包含双翼看板在内的完整 GUI 首屏渲染 0 异常 0 报错"""
    at = AppTest.from_file(GUI_FILE, default_timeout=35)
    at.run()
    assert not at.exception, f"GUI 加载双翼看板抛出异常: {at.exception}"
    assert len(at.error) == 0, f"GUI 报告了界面错误: {[e.value for e in at.error]}"


def test_watchdog_persistence_file():
    """验证主动风险预警哨本地持久化文件是否正常可读"""
    watchdog_path = "data/portfolio_watchdog.json"
    if os.path.exists(watchdog_path):
        with open(watchdog_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "timestamp" in data
        assert "all_passed" in data
        assert "alerts" in data
