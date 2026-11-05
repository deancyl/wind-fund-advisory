# -*- coding: utf-8 -*-
"""
AGY2_FundAdvisory/tests/test_sidebar_remodel_and_bugfixes.py
自动化回归测试：
1. 侧边栏重构：只保留外观与色彩 + 市场状态底座 + 核心指数行情走廊，彻底移除全局目标/风控/账本管理
2. 控件归位：全局目标归位 Tab 1，风控护栏归位 Tab 1/2，账本管理归位 Tab 2 步骤一
3. 移除主界面顶部横向 index-ticker-strip
4. 步骤三 target_weight KeyError 修复与表格/小抄联动
5. 风险预警哨真实数据接入无异常
6. 暗黑模式内联写死颜色彻底清除
"""

import os
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest

CURRENT_DIR = Path(__file__).resolve().parent
GUI_FILE = str(CURRENT_DIR.parent / "app_gui.py")


def test_sidebar_and_main_layout_decoupling():
    """验证侧边栏去重与主界面横向行情条移除"""
    with open(GUI_FILE, "r", encoding="utf-8") as f:
        gui_text = f.read()

    # 1. 侧边栏必须包含三大核心模块
    assert "##### 🎨 外观与色彩" in gui_text
    assert "##### 🕒 市场状态与底座" in gui_text
    assert "##### 📊 核心指数行情走廊" in gui_text or "📊 核心指数走廊" in gui_text

    # 2. 侧边栏严禁出现这三组重复模块
    # 在 with st.sidebar: 块内不应再有这些 section 标题
    sidebar_idx = gui_text.find("with st.sidebar:")
    top_dashboard_idx = gui_text.find("顶部全局看板", sidebar_idx)
    sidebar_code = gui_text[sidebar_idx:top_dashboard_idx]

    assert "##### 🎯 全局目标联动" not in sidebar_code, "侧边栏严禁保留全局目标联动"
    assert "##### 🛡️ 交易风控护栏" not in sidebar_code, "侧边栏严禁保留交易风控护栏"
    assert "##### 🗄️ 账本环境管理" not in sidebar_code, "侧边栏严禁保留账本环境管理"

    # 3. 主界面顶部横向 strip 必须移除（已移入侧边栏）
    assert "strip_col_ticker, strip_col_btn = st.columns([8.4, 1.6])" not in gui_text, "主界面横向行情带必须移除"

    # 4. 控件必须归位到右侧主工作区
    assert "风险策略档位" in gui_text
    assert "定权模型：" in gui_text
    assert "资产基线：" in gui_text
    assert "btn_tab2_load_demo" in gui_text or "载入演示组合" in gui_text


def test_no_hardcoded_dark_hex_colors():
    """验证宏观横幅、模型卡片与账本基线中无残留的硬编码暗色 hex 颜色"""
    with open(GUI_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # 排除 THEME_PRESETS 定义区 (前 300 行)
    code_body = "".join(lines[300:])
    # 查找容易导致暗黑主题下文字失真的写死深色
    for forbidden in ['color: #1e293b', 'color: #334155', 'color: #475569']:
        assert forbidden not in code_body, f"Found hardcoded text color '{forbidden}' in code body"


def test_target_weight_keyerror_fix():
    """验证 Tab 1 步骤三已支持 target_weight_pct 安全取值，绝不发生 KeyError"""
    with open(GUI_FILE, "r", encoding="utf-8") as f:
        gui_text = f.read()

    assert 'it["target_weight"]' not in gui_text, "必须使用 it.get 安全获取 target_weight"
    assert 'it.get("target_weight_pct"' in gui_text or 'it.get("target_weight"' in gui_text
    assert 'snapshot.get("bias_20"' in gui_text


def test_apptest_full_gui_remodel():
    """Streamlit AppTest 运行：全屏渲染 0 异常，侧边栏与四大 Tab 交互健康"""
    at = AppTest.from_file(GUI_FILE, default_timeout=35)
    at.run()
    assert not at.exception, f"AppTest 发生异常: {at.exception}"
    assert len(at.error) == 0, f"AppTest 报告了错误: {[e.value for e in at.error]}"
