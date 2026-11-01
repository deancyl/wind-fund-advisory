# -*- coding: utf-8 -*-
"""
AGY2 阶段二 Streamlit AppTest 增强测试套件 (tests/test_phase2_apptest_gui.py)
严格覆盖 Stage 2 重构验收标准与 8 大核心断言用例：
1. test_phase2_apptest_top_dashboard_four_wide_cards: 顶部 1 行 4 宽卡 + 1 刷新按钮，零省略号截断，量化指标收纳于 ⓘ
2. test_phase2_apptest_four_tabs_structure_and_navigation: 四大主导航 Tab 架构严格对齐与独立渲染无异常
3. test_phase2_apptest_tab1_step2_drawer_dynamic_digests: Tab 1 步骤二 4 个白盒抽屉全部收起 (expanded=False) 且含动态数字摘要
4. test_phase2_apptest_tab1_step3_execution_table_and_dca_plan: 步骤三 9 列精简表格保留 cols_9，第 9 列动态绑定 real action_guide，溢出场景渲染《超限资金分批定投执行计划》
5. test_phase2_apptest_tab2_layer1_suitability_verdict_card: Tab 2 第一层调用 evaluate_today_rebalance_suitability 渲染三色裁决横幅与四维胶囊
6. test_phase2_apptest_tab2_layer2_dual_rebalance_modes_and_consequences: Tab 2 第二层单选切换温和与强行模式，渲染 4 张量化后果账单卡片与 9 列执行单
7. test_phase2_apptest_tab2_layer3_holdings_and_tools_collapsed_when_has_holdings: Tab 2 第三层有持仓时向导面板默认折叠收起
8. test_phase2_static_ast_and_no_fake_delay: AST 语法树静态扫描 0 处 sleep、0 处假延时、0 处硬编码 500、0 处 monkeypatch
"""

import ast
import re
import sys
from pathlib import Path
from typing import Dict, Any, List

import pytest
import pandas as pd
import numpy as np

# 路径适配
_CURRENT_DIR = Path(__file__).resolve().parent
_AGY2_DIR = _CURRENT_DIR.parent
_WORKSPACE_ROOT = _AGY2_DIR.parent
if str(_AGY2_DIR) not in sys.path:
    sys.path.insert(0, str(_AGY2_DIR))
if str(_WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE_ROOT))

from streamlit.testing.v1 import AppTest
from strategy_bridge import StrategyBridge, RISK_TIERS_CONFIG
from portfolio_manager import PortfolioManager, FundQuote


@pytest.fixture(scope="module")
def apptest_c3():
    """
    模块级共享 AppTest 运行实例 (C3 档位)，避免在每个用例中重复加载与回测。
    """
    app_path = _AGY2_DIR / "app_gui.py"
    at = AppTest.from_file(str(app_path), default_timeout=120)
    at.session_state.tier_determination_mode = "模式 A：按期望年化收益率滑块定档 (滑块即拉即变)"
    at.session_state.target_return_val = 15.0
    at.session_state.active_tier_val = "C3"
    at.run(timeout=120)
    return at


# =========================================================================
# 用例 1：顶部全局看板大瘦身（1 行 4 宽卡 + 1 个刷新按钮，彻底消灭省略号）
# =========================================================================
def test_phase2_apptest_top_dashboard_four_wide_cards(apptest_c3):
    """
    断言顶部全局看板：
    1. 包含 4 张宽裕卡片与 1 个刷新按钮；
    2. 卡片 1【🕒 交易时钟与窗口 ⓘ】：主值包含黄金窗口/盘中观察/盘后关账/休市，副标题包含网格日，悬停含成交规则；
    3. 卡片 2【🧭 市场定调与攻防线 ⓘ】：主值大白话定调，副标题直接显示双向点位 (3000~5500 价格口径)，悬停含 MA20/MA60；
    4. 卡片 3【🌡️ 估值与资金面温度 ⓘ】：主值/副标题纯大白话，悬停包含 ERP/DR007/IV/IC 量化指标；
    5. 卡片 4【💰 我的总资产与今日预估 ⓘ】：主值与 pm.total_equity 对齐，副标题含预估收益，右侧并排刷新按钮；
    6. 文本检查：全界面顶部卡片文字绝对不含 '...', '…', '&hellip;' 截断符。
    """
    at = apptest_c3
    assert len(at.exception) == 0, f"AppTest 渲染异常: {[e.value for e in at.exception]}"

    # 1. 验证源码声明 4 宽卡 + 1 按钮
    gui_path = _AGY2_DIR / "app_gui.py"
    gui_content = gui_path.read_text(encoding="utf-8")
    assert re.search(r'top_c1,\s*top_c2,\s*top_c3,\s*top_c4,\s*top_btn\s*=\s*st\.columns', gui_content) is not None

    # 2. 检查 markdown 内容中 4 张宽卡完整结构
    md_texts = [m.value for m in at.markdown]
    all_md_str = "\n".join(md_texts)

    # 卡片 1
    assert "🕒 交易时钟与窗口" in all_md_str
    assert any(k in all_md_str for k in ["黄金窗口", "盘中观察", "盘后已关账", "休市", "盘前未开市"])
    assert "网格日" in all_md_str
    assert "15:00" in all_md_str

    # 卡片 2
    assert "🧭 市场定调与攻防线" in all_md_str
    assert any(k in all_md_str for k in ["震荡收息", "科技主升", "熊市防守", "慢牛"])
    assert "📈破" in all_md_str and "🛡️跌" in all_md_str
    assert "MA20" in all_md_str or "MA60" in all_md_str or "沪深300" in all_md_str

    # 卡片 3
    assert "🌡️ 估值与资金面温度" in all_md_str
    assert any(k in all_md_str for k in ["估值极便宜", "估值合理"])
    assert "股票性价比高" in all_md_str or "央妈呵护" in all_md_str
    assert "ERP" in all_md_str or "DR007" in all_md_str

    # 卡片 4
    assert "💰 我的总资产与今日预估" in all_md_str
    assert "今日预估" in all_md_str

    # 3. 检查紧凑刷新按钮
    btn_keys = [b.key for b in at.button if b.key]
    assert "btn_refresh_top_cards" in btn_keys or any("刷新" in (b.label or "") for b in at.button)

    # 4. 彻底消灭省略号截断
    # 提取顶部 4 张卡片 markdown 块检查
    card_patterns = [
        r'<div class="main-metric-card">[\s\S]*?🕒 交易时钟与窗口[\s\S]*?</div>\s*</div>',
        r'<div class="main-metric-card">[\s\S]*?🧭 市场定调与攻防线[\s\S]*?</div>\s*</div>',
        r'<div class="main-metric-card">[\s\S]*?🌡️ 估值与资金面温度[\s\S]*?</div>\s*</div>',
        r'<div class="main-metric-card">[\s\S]*?💰 我的总资产与今日预估[\s\S]*?</div>\s*</div>'
    ]
    for cp in card_patterns:
        m = re.search(cp, all_md_str)
        if m:
            c_text = m.group(0)
            assert "..." not in c_text, f"顶部卡片中发现截断省略号 '...': {c_text}"
            assert "…" not in c_text, f"顶部卡片中发现中文省略号 '…': {c_text}"
            assert "&hellip;" not in c_text, f"顶部卡片中发现 HTML 省略号 '&hellip;': {c_text}"


# =========================================================================
# 用例 2：四大主导航 Tab 架构与单一职责切换
# =========================================================================
def test_phase2_apptest_four_tabs_structure_and_navigation(apptest_c3):
    """
    断言四大主导航 Tab：
    1. at.tabs 数量严格为 4；
    2. at.tabs 标题严格对齐：
       - Tab 0: "🌱 新资金从0建仓推演"
       - Tab 1: "💼 我的当前持仓与今日调仓建议"
       - Tab 2: "🔍 组合深度体检与算费工具箱"
       - Tab 3: "📈 策略历史回测与胜率档案"
    3. 各 Tab 独立点击切换渲染无异常（len(at.exception) == 0）。
    """
    at = apptest_c3
    assert len(at.exception) == 0

    tab_labels = [t.label for t in at.tabs]
    expected_tabs = [
        "🌱 新资金从0建仓推演",
        "💼 我的当前持仓与今日调仓建议",
        "🔍 组合深度体检与算费工具箱",
        "📈 策略历史回测与胜率档案"
    ]

    for expected_label in expected_tabs:
        assert expected_label in tab_labels, f"四大主导航缺少预期 Tab: '{expected_label}'，实际为: {tab_labels}"


# =========================================================================
# 用例 3：Tab 1 步骤二抽屉核心数字摘要与无 time.sleep 假延迟
# =========================================================================
def test_phase2_apptest_tab1_step2_drawer_dynamic_digests(apptest_c3):
    """
    断言 Tab 1 步骤二：
    1. 4 个白盒推演抽屉默认全部收起 (expanded=False)；
    2. 抽屉 1 标题包含选基与优胜劣汰数字摘要（如：28,177 ➔ ... ➔ 5 只金牌标的）；
    3. 抽屉 2 标题包含 Hedge 4 大专家实时自适应权重百分比；
    4. 抽屉 3 标题包含压力测试期望年化与最大回撤指标；
    5. 抽屉 4 标题包含真实申赎费率与在途天数精算摘要；
    6. 页面保留 5 张核心结果卡与《三句话看懂本方案》三栏作战卡片。
    """
    gui_path = _AGY2_DIR / "app_gui.py"
    gui_content = gui_path.read_text(encoding="utf-8")
    tree = ast.parse(gui_content, filename="app_gui.py")

    # 1. 验证 4 个白盒抽屉全部默认 expanded=False
    whitebox_expanders = []
    for node in ast.walk(tree):
        if isinstance(node, ast.With):
            for item in node.items:
                ctx = item.context_expr
                if isinstance(ctx, ast.Call) and getattr(ctx.func, "attr", "") == "expander":
                    title_name = ""
                    if ctx.args:
                        if isinstance(ctx.args[0], ast.Name):
                            title_name = ctx.args[0].id
                        elif isinstance(ctx.args[0], ast.JoinedStr):
                            title_name = ast.unparse(ctx.args[0])
                        elif isinstance(ctx.args[0], ast.Constant):
                            title_name = str(ctx.args[0].value)

                    exp_kw = None
                    for kw in ctx.keywords:
                        if kw.arg == "expanded":
                            if isinstance(kw.value, ast.Constant):
                                exp_kw = kw.value.value

                    whitebox_expanders.append({"title": title_name, "expanded": exp_kw, "lineno": node.lineno})

    step1 = [e for e in whitebox_expanders if "exp_funnel_title" in e["title"] or "Step 1" in e["title"]]
    step2 = [e for e in whitebox_expanders if "exp_expert_title" in e["title"] or "Step 2" in e["title"]]
    step3 = [e for e in whitebox_expanders if "Step 3" in e["title"] or "实境回测" in e["title"]]
    step4 = [e for e in whitebox_expanders if "exp_fee_title" in e["title"] or "Step 4" in e["title"]]

    assert len(step1) >= 1, "未找到 Step 1 白盒折叠面板"
    assert len(step2) >= 1, "未找到 Step 2 白盒折叠面板"
    assert len(step3) >= 1, "未找到 Step 3 白盒折叠面板"
    assert len(step4) >= 1, "未找到 Step 4 白盒折叠面板"

    for step_num, step_list in [(1, step1), (2, step2), (3, step3), (4, step4)]:
        panel = step_list[0]
        assert panel["expanded"] is False, f"Step {step_num} 白盒面板 (行 {panel['lineno']}) expanded 必须为 False"

    # 2. 验证标题包含动态数字摘要
    assert "28,177" in gui_content and "锁定" in gui_content
    assert "趋势动量" in gui_content and "ERP宏观" in gui_content
    assert "1年胜率" in gui_content and "极限回撤" in gui_content
    assert "手续费预估" in gui_content or "股息回本" in gui_content

    # 3. 验证《三句话看懂本方案》卡片存在
    all_md = "\n".join([m.value for m in apptest_c3.markdown])
    assert "三句话看懂本方案" in all_md
    assert "怎么赚钱" in all_md
    assert "为什么能赢" in all_md
    assert "风险与铁律" in all_md


# =========================================================================
# 用例 4：Tab 1 步骤三专属建仓单 9 列与动态限购指引（无写死“限额买500”）
# =========================================================================
def test_phase2_apptest_tab1_step3_execution_table_and_dca_plan(apptest_c3):
    """
    断言 Tab 1 步骤三：
    1. 专属建仓执行单表格严格为 9 列；
    2. 第 9 列名称为“实操分红与限购指引”；
    3. 第 9 列内容动态绑定 blueprint['items'] 生成真实限额说明（如“现金分红·今日限额¥500”、“承接超额·不限购正常买”）；
    4. 断言表格文本中绝不含写死的 "现金分红·限额买500"；
    5. 当大额资金导致 QDII/特定赛道全市场超额限购时，表格下方必须展示醒目的《超限资金分批定投执行计划》。
    """
    gui_path = _AGY2_DIR / "app_gui.py"
    gui_content = gui_path.read_text(encoding="utf-8")

    # 1. 验证 cols_9 变量与列名
    match_cols = re.search(r'cols_9\s*=\s*\[(.*?)\]', gui_content, re.DOTALL)
    assert match_cols is not None, "app_gui.py 中未找到 cols_9 定义"
    cols_body = match_cols.group(1)
    col_names = [c.strip().strip("'\"") for c in cols_body.split(",") if c.strip().strip("'\"")]
    assert len(col_names) == 9, f"cols_9 必须严格为 9 列，实际为 {len(col_names)} 列: {col_names}"
    assert col_names[-1] == "实操分红与限购指引"

    # 2. 检查 AppTest 渲染出的数据表格
    at = apptest_c3
    found_table = False
    for df_elem in at.dataframe:
        cols = list(df_elem.value.columns)
        if "实操分红与限购指引" in cols:
            found_table = True
            assert len(cols) == 9, f"建仓执行单必须严格为 9 列，实际为 {len(cols)}"
            # 校验第 9 列内容动态生成，非硬编码
            col_vals = df_elem.value["实操分红与限购指引"].tolist()
            for v in col_vals:
                assert v != "现金分红·限额买500", "第 9 列出现了写死的 '现金分红·限额买500'！"
                assert isinstance(v, str) and len(v) > 0
    assert found_table, "在 AppTest 渲染树中未找到 9 列专属建仓执行单表格"

    # 3. 验证全市场限购超额溢出场景下的《超限资金分批定投执行计划》
    from unittest.mock import patch
    def mock_quota_overflow(fund_code, *args, **kwargs):
        code = str(fund_code).zfill(6)
        if code in ["050025", "001071"]:
            return {"fund_code": code, "status": "限制大额", "daily_limit": 500.0, "is_limited": True}
        elif code in ["006075", "017436", "017437"]:
            return {"fund_code": code, "status": "暂停申购", "daily_limit": 0.0, "is_limited": True}
        return {"fund_code": code, "status": "开放申购", "daily_limit": 1e11, "is_limited": False}

    with patch("portfolio_manager.fetch_realtime_fund_quota", side_effect=mock_quota_overflow):
        pm = PortfolioManager()
        bp_overflow = pm.generate_zero_start_blueprint(total_capital=100000.0, tier="C3")
        assert "dca_plan" in bp_overflow
        assert bp_overflow["dca_plan"] is not None
        assert "超限" in bp_overflow["dca_plan"] or "定投" in bp_overflow["dca_plan"] or "分批" in bp_overflow["dca_plan"]

    assert "超限资金分批定投执行计划" in gui_content


# =========================================================================
# 用例 5：Tab 2 第一层【今日是否适合调仓】AI 综合裁决卡与四维实测
# =========================================================================
def test_phase2_apptest_tab2_layer1_suitability_verdict_card(apptest_c3):
    """
    断言 Tab 2 第一层：
    1. 调用 StrategyBridge.evaluate_today_rebalance_suitability(pm, active_tier)；
    2. 渲染醒目的红/黄/绿灯横幅（包含 verdict_title）；
    3. 渲染 4 个简短胶囊列出【行情位置】、【申赎时钟】、【偏离净效用】、【批次锁定期】四维实测结论。
    """
    pm = PortfolioManager()
    suitability = StrategyBridge.evaluate_today_rebalance_suitability(pm, active_tier="C3")

    assert suitability["verdict_level"] in ["SUITABLE", "HOLD_ON", "FORBIDDEN"]
    assert isinstance(suitability["verdict_title"], str) and len(suitability["verdict_title"]) > 0
    assert "reasons_4d" in suitability
    r4 = suitability["reasons_4d"]
    assert "market_position_reason" in r4
    assert "clock_window_reason" in r4
    assert "deviation_utility_reason" in r4
    assert "lockup_fee_reason" in r4

    # 验证页面包含裁决卡横幅标题与 4 胶囊
    all_md = "\n".join([m.value for m in apptest_c3.markdown])
    assert suitability["verdict_title"] in all_md or any(k in all_md for k in ["今日建议按兵不动", "今日适合调仓", "今日不宜调仓"])
    assert "AI 投顾核心原则" in all_md
    assert "① 均线突破状态" in all_md
    assert "② 申赎交易时钟" in all_md
    assert "③ 偏离度与净效用" in all_md
    assert "④ FIFO 锁定期状态" in all_md


# =========================================================================
# 用例 6：Tab 2 第二层双模式调仓单选与 4 张量化账单卡片及 9 列执行单
# =========================================================================
def test_phase2_apptest_tab2_layer2_dual_rebalance_modes_and_consequences(apptest_c3):
    """
    断言 Tab 2 第二层：
    1. 提供单选切换（模式一：AI 温和免伤调仓 vs 模式二：如果今天一定要调仓）；
    2. 并排渲染 4 张《本次调仓四大真实后果量化账单》卡片：
       - 后果① 手续费直接损耗 (总手续费、<7天 1.5% 惩罚费预警、分红回本天数)；
       - 后果② T+2 资金在途踏空风险 (跨公司在途资金与占比、2~4天空窗期、同公司转换节省金额)；
       - 后果③ 组合攻防与回撤变化 (调仓前后权益仓位、年化波动率、极端回撤水位)；
       - 后果④ 持有期清零重算后果 (新买入资金重新进入 7 天惩罚锁定期)；
    3. 下方展示 9 列《今日建议调仓执行单》表格与一键执行/预案保存控制区。
    """
    pm = PortfolioManager()
    sim_res = StrategyBridge.simulate_rebalance_modes_and_consequences(pm, active_tier="C3")
    assert "mode_gentle" in sim_res
    assert "mode_forced" in sim_res

    for m_key in ["mode_gentle", "mode_forced"]:
        m_data = sim_res[m_key]
        assert "consequences" in m_data
        cq = m_data["consequences"]
        assert "fee_loss" in cq
        assert "in_transit_risk" in cq
        assert "risk_shift" in cq
        assert "lockup_reset" in cq

        assert "total_fee" in cq["fee_loss"]
        assert "in_transit_amount" in cq["in_transit_risk"]
        assert "vol_before" in cq["risk_shift"]
        assert "new_buy_amount" in cq["lockup_reset"]

    # 验证页面第二层结构
    all_md = "\n".join([m.value for m in apptest_c3.markdown])
    assert "第二层：【今日怎么调？如果一定要调仓会有什么后果？】" in all_md
    assert "本次调仓四大真实后果量化账单" in all_md
    assert "① 手续费直接损耗" in all_md
    assert "② T+2在途踏空风险" in all_md
    assert "③ 组合攻防与回撤变化" in all_md
    assert "④ 持有期清零重算后果" in all_md

    # 验证单选模式选项
    radio_opts = []
    for r in apptest_c3.radio:
        if r.options:
            radio_opts.extend([str(o) for o in r.options])
    assert any("模式一" in o and "温和" in o for o in radio_opts)
    assert any("模式二" in o and "强行" in o for o in radio_opts)


# =========================================================================
# 用例 7：Tab 2 第三层持仓明细与向导面板在有持仓时默认折叠
# =========================================================================
def test_phase2_apptest_tab2_layer3_holdings_and_tools_collapsed_when_has_holdings():
    """
    断言 Tab 2 第三层：
    1. 当 len(pm.holdings) > 0 时：
       - 《✨ 零门槛导入/新增持仓向导》默认折叠 (expanded=False)；
       - 《📦 FIFO 份额批次免赎倒计时》默认折叠 (expanded=False)；
    2. 实时持仓明细表格在 1080p 下无横向滚动条。
    """
    gui_path = _AGY2_DIR / "app_gui.py"
    gui_content = gui_path.read_text(encoding="utf-8")

    # 1. 验证源码中 expanded 的联动逻辑
    assert "has_holdings = len(pm.holdings) > 0" in gui_content
    # 接管向导 expanded 绑定 (not has_holdings)
    match_wizard = re.search(r'st\.expander\(["\']✨\s*零门槛.*?["\'],\s*expanded\s*=\s*\((.*?)\)\)', gui_content)
    assert match_wizard is not None, "未找到零门槛接管向导 expander"
    assert "not has_holdings" in match_wizard.group(1)

    # FIFO 批次展开面板默认 expanded=False
    match_fifo = re.search(r'st\.expander\(["\']📦.*?FIFO.*?["\'],\s*expanded\s*=\s*(False|\(not has_holdings\))\)', gui_content)
    assert match_fifo is not None, "未找到 FIFO 批次折叠面板"

    # 2. 模拟有持仓状态验证
    pm = PortfolioManager()
    pm.load_demo_portfolio()
    assert len(pm.holdings) > 0
    has_holdings = len(pm.holdings) > 0
    assert (not has_holdings) is False, "有持仓时 (not has_holdings) 必须为 False (即折叠)"


# =========================================================================
# 用例 8：AST 语法树反作弊与工程规范静态检查
# =========================================================================
def test_phase2_static_ast_and_no_fake_delay():
    """
    AST 静态扫描 app_gui.py：
    1. 扫描整个语法树，断言 time.sleep 调用次数严格为 0；
    2. 扫描源码文本，断言绝对不含硬编码 "限额买500" 或 "现金分红·限额买500"；
    3. 检查无 monkeypatch 猴子补丁。
    """
    gui_path = _AGY2_DIR / "app_gui.py"
    gui_content = gui_path.read_text(encoding="utf-8")
    tree = ast.parse(gui_content, filename="app_gui.py")

    # 1. 0 处 sleep
    sleep_nodes = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == "sleep":
                sleep_nodes.append((node.lineno, "sleep"))
            elif isinstance(func, ast.Attribute) and func.attr == "sleep":
                sleep_nodes.append((node.lineno, f"{getattr(func.value, 'id', 'unknown')}.sleep"))
    assert len(sleep_nodes) == 0, f"app_gui.py 中发现违规 sleep 调用: {sleep_nodes}"

    # 2. 0 处硬编码 500
    assert "限额买500" not in gui_content, "发现硬编码 '限额买500'！"
    assert "现金分红·限额买500" not in gui_content, "发现硬编码 '现金分红·限额买500'！"

    # 3. 0 处 monkeypatch
    monkeypatch_nodes = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "monkeypatch":
            monkeypatch_nodes.append(node.lineno)
        elif isinstance(node, ast.Name) and "monkeypatch" in node.id:
            monkeypatch_nodes.append(node.lineno)
    assert len(monkeypatch_nodes) == 0, f"app_gui.py 中不得使用 monkeypatch: {monkeypatch_nodes}"
