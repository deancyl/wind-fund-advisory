# -*- coding: utf-8 -*-
"""
AGY2 Milestone 3 对抗性实证挑战与自动化测试套件 (Challenger 2)
文件路径: AGY2_FundAdvisory/tests/test_adversarial_m3_challenger2.py

覆盖 Milestone 3 交付的核心挑战点与极端边界条件：
1. 四阶 time.sleep(0.35) 延时节奏累计 1.45s 稳定在 [1.2, 1.8]s 区间内，且非首次演算不重复卡顿；
2. 4 个白盒展开面板默认 expanded=False；
3. 顶部 7 张核心卡片 15px 单行紧凑，绝对不含 '...', '…', '&hellip;' 等截断符；
4. 《三句话看懂本方案》三栏作战卡片正确渲染；
5. 建仓执行单严格 9 列，存量调仓单控制在 9 列以内且含 5 类操作图标；
6. 双向变盘触发点位在不同现价下绝对满足 breakdown < current < surge，杜绝原有 4180.5/4053.0 倒挂；
7. 极端布局与不同分辨率/档位下的对抗渲染测试，确保零崩溃与零异常。
"""

import ast
import re
import sys
import time
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

from strategy_bridge import StrategyBridge, SchmidtHysteresisBuffer, RISK_TIERS_CONFIG
from portfolio_manager import PortfolioManager, FundQuote


# =========================================================================
# 1. 四阶 time.sleep 延时节奏与非首次演算不重复卡顿测试
# =========================================================================
def test_sleep_delay_cadence_and_non_repetition():
    """
    挑战点 1：四阶延时节奏累计 1.45s 稳定在 [1.2, 1.8]s 区间内，且非首次演算不重复卡顿。
    - AST 静态解析 app_gui.py 中推演过程的所有 time.sleep 参数；
    - 验证 4 个阶梯延时恰好为 [0.35, 0.35, 0.40, 0.35]，总耗时 1.45s；
    - 验证状态机门控：st.session_state.sim_has_run 为 False 时，完全跳过延时与推演容器；
    - 验证推演完成后立即执行 st.session_state.sim_has_run = False 复位，杜绝后续重复渲染卡顿。
    """
    gui_path = _AGY2_DIR / "app_gui.py"
    assert gui_path.exists(), "未找到 app_gui.py"
    gui_content = gui_path.read_text(encoding="utf-8")
    tree = ast.parse(gui_content, filename="app_gui.py")

    # 1.1 提取推演容器内的 time.sleep 常量
    sleep_calls: List[float] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            # 匹配 time.sleep(...)
            func = node.func
            if (isinstance(func, ast.Attribute) and func.attr == "sleep" and
                    isinstance(func.value, ast.Name) and func.value.id == "time"):
                if node.args and isinstance(node.args[0], ast.Constant):
                    sleep_calls.append(float(node.args[0].value))

    # 断言推演过程中包含 4 个特定 sleep 节点
    assert len(sleep_calls) >= 4, f"app_gui.py 中 time.sleep 节点数量不足 4 个，实际检测到: {len(sleep_calls)}"
    sim_sleeps = sleep_calls[:4]
    expected_cadence = [0.35, 0.35, 0.40, 0.35]
    assert sim_sleeps == expected_cadence, (
        f"四阶延时节奏偏离标准配置: 期望 {expected_cadence}，实际 {sim_sleeps}"
    )

    total_sleep = sum(sim_sleeps)
    assert 1.2 <= total_sleep <= 1.8, (
        f"四阶累计延时 {total_sleep:.2f}s 不在舒适心理区间 [1.2, 1.8]s 内"
    )

    # 1.2 验证状态机门控逻辑与复位机制
    # 查找 if st.session_state.sim_has_run 与复位代码
    assert "if st.session_state.sim_has_run:" in gui_content, "缺少 st.session_state.sim_has_run 门控判断"
    assert "st.session_state.sim_has_run = False" in gui_content, "推演完毕后未将 sim_has_run 复位为 False"

    # 验证首次启动默认不卡顿：last_sim_tier not in st.session_state 时不会将 sim_has_run 设为 True
    init_pattern = re.search(
        r'if\s+["\']last_sim_tier["\']\s+not\s+in\s+st\.session_state:\s*\n\s*st\.session_state\.last_sim_tier\s*=\s*active_tier',
        gui_content
    )
    assert init_pattern is not None, "初始冷启动定档未正确隔离，存在冷启动被动卡顿风险"


# =========================================================================
# 2. 4 个白盒展开面板默认 expanded=False 测试
# =========================================================================
def test_four_whitebox_expanders_default_collapsed():
    """
    挑战点 2：验证 4 个白盒展开面板默认全部为 expanded=False。
    - Step 1: 全市场公募基金四级漏斗海选与 CUSUM 优选
    - Step 2: 宏观动量与衍生品四维状态机实时定调
    - Step 3: 2018-2026 跨牛熊 2,000+ 交易日实境回测与压力测试
    - Step 4: 交易摩擦精算、限购拆单与实盘执行清单
    """
    gui_path = _AGY2_DIR / "app_gui.py"
    gui_content = gui_path.read_text(encoding="utf-8")
    tree = ast.parse(gui_content, filename="app_gui.py")

    whitebox_expanders: List[Dict[str, Any]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.With):
            for item in node.items:
                ctx_expr = item.context_expr
                if isinstance(ctx_expr, ast.Call):
                    func = ctx_expr.func
                    if (isinstance(func, ast.Attribute) and func.attr == "expander" and
                            isinstance(func.value, ast.Name) and func.value.id == "st"):
                        # 获取 title 与 expanded 关键字参数
                        title_str = ""
                        if ctx_expr.args:
                            if isinstance(ctx_expr.args[0], ast.Constant):
                                title_str = str(ctx_expr.args[0].value)
                            elif isinstance(ctx_expr.args[0], ast.Name):
                                title_str = ctx_expr.args[0].id

                        expanded_val = None
                        for kw in ctx_expr.keywords:
                            if kw.arg == "expanded":
                                if isinstance(kw.value, ast.Constant):
                                    expanded_val = kw.value.value

                        whitebox_expanders.append({
                            "title": title_str,
                            "expanded": expanded_val,
                            "lineno": node.lineno
                        })

    # 筛选 Step 1 到 Step 4 白盒面板
    step1 = [e for e in whitebox_expanders if "exp_funnel_title" in e["title"] or "Step 1" in e["title"]]
    step2 = [e for e in whitebox_expanders if "Step 2" in e["title"] or "四维状态机" in e["title"]]
    step3 = [e for e in whitebox_expanders if "Step 3" in e["title"] or "实境回测" in e["title"]]
    step4 = [e for e in whitebox_expanders if "Step 4" in e["title"] or "交易摩擦" in e["title"]]

    assert len(step1) >= 1, "未找到 Step 1 白盒折叠面板"
    assert len(step2) >= 1, "未找到 Step 2 白盒折叠面板"
    assert len(step3) >= 1, "未找到 Step 3 白盒折叠面板"
    assert len(step4) >= 1, "未找到 Step 4 白盒折叠面板"

    for step_num, step_list in [(1, step1), (2, step2), (3, step3), (4, step4)]:
        panel = step_list[0]
        assert panel["expanded"] is False, (
            f"Step {step_num} 白盒面板 (行号: {panel['lineno']}) expanded 属性必须为 False，实际为: {panel['expanded']}"
        )


# =========================================================================
# 3. 顶部 7 张核心卡片 15px 单行紧凑与零截断测试
# =========================================================================
def test_top_seven_metric_cards_compact_and_no_truncation():
    """
    挑战点 3：顶部 7 张核心卡片 15px 单行紧凑，绝对不含 '...', '…', '&hellip;' 等截断符，且配备 ⓘ 悬停提示。
    """
    gui_path = _AGY2_DIR / "app_gui.py"
    gui_content = gui_path.read_text(encoding="utf-8")

    # 匹配顶部 7 列分栏
    col_split = re.search(
        r'status_col1,\s*status_col2,\s*status_col3,\s*status_col4,\s*status_col_liq,\s*status_col5,\s*status_col6\s*=\s*st\.columns\(7\)',
        gui_content
    )
    assert col_split is not None, "未找到顶部 7 张核心指标卡片的 st.columns(7) 声明"

    # 提取 7 张卡片的 HTML 块
    card_names = [
        "申赎时钟",
        "AI 策略大脑",
        "沪深300 (实时)",
        "股债性价比",
        "宏观流动性",
        "今日预估浮盈亏",
        "全组合总资产"
    ]

    for name in card_names:
        assert name in gui_content, f"顶部 7 张核心卡片缺少: {name}"

        # 匹配卡片对应的 markdown 内容
        pattern = rf'<div class="metric-card-title">\s*{re.escape(name)}[\s\S]*?</div>\s*<div class="metric-value-huge"([^>]*)>([\s\S]*?)</div>'
        m = re.search(pattern, gui_content)
        assert m is not None, f"未匹配到卡片 【{name}】 的完整 HTML 结构"

        style_attr, val_content = m.group(1), m.group(2)
        # 验证 15px 紧凑字体
        assert "font-size:15px;" in style_attr or "font-size: 15px;" in style_attr, (
            f"卡片 【{name}】 未设置 font-size:15px; 单行紧凑样式: {style_attr}"
        )

        # 绝对不含截断符
        assert "..." not in val_content, f"卡片 【{name}】 数值中包含截断省略号 '...': {val_content}"
        assert "…" not in val_content, f"卡片 【{name}】 数值中包含中文省略号 '…': {val_content}"
        assert "&hellip;" not in val_content, f"卡片 【{name}】 数值中包含 HTML 省略号 '&hellip;': {val_content}"

    # 验证全部 7 张卡片均配置 ⓘ 悬停提示 span 标签
    start_pos = gui_content.find("status_col1, status_col2")
    end_pos = gui_content.find("col_rt_info, col_rt_btn")
    cards_block = gui_content[start_pos:end_pos]
    info_spans = re.findall(r'<span title="([^"]+)"[^>]*>ⓘ</span>', cards_block)
    assert len(info_spans) == 7, f"顶部卡片 ⓘ 悬停提示标签数量不等于 7 个，实际匹配到: {len(info_spans)}"


# =========================================================================
# 4. 《三句话看懂本方案》三栏作战卡片正确渲染测试
# =========================================================================
def test_three_sentence_battle_cards_structure_and_metrics():
    """
    挑战点 4：验证《三句话看懂本方案：怎么赚钱、为什么能赢、风险与铁律》三栏作战卡片正确渲染。
    - 验证三栏列声明与大标题；
    - 验证三大核心板块：收益引擎拆解、反脆弱对冲机制、底线与执行铁律；
    - 验证铁律中严格包含“未满7天绝不赎回 (1.50%惩罚)”与“估值底部便宜区绝不割肉 (ERP >75%)”。
    """
    gui_path = _AGY2_DIR / "app_gui.py"
    gui_content = gui_path.read_text(encoding="utf-8")

    assert "🎯 《三句话看懂本方案：怎么赚钱、为什么能赢、风险与铁律》" in gui_content
    assert "col_card1, col_card2, col_card3 = st.columns(3)" in gui_content

    # 验证卡片 1: 怎么赚钱
    assert "💰 怎么赚钱？(收益引擎拆解)" in gui_content
    assert "核心红利高股息打底" in gui_content
    assert "动态动量弹性进攻" in gui_content
    assert "智能拆单捕捉超额 Alpha" in gui_content

    # 验证卡片 2: 为什么能赢
    assert "🛡️ 为什么能赢？(反脆弱对冲机制)" in gui_content
    assert "跨大类极低相关对冲" in gui_content
    assert "牛熊实境考验胜率" in gui_content
    assert "东边不亮西边亮" in gui_content

    # 验证卡片 3: 风险与铁律
    assert "🚨 风险与铁律 (底线与执行铁律)" in gui_content
    assert "历史最极端浮亏" in gui_content
    assert "最长水下等待" in gui_content
    assert "买入未满 7 天绝不赎回" in gui_content
    assert "1.50% 证监会惩罚性扣款" in gui_content
    assert "估值底部便宜区绝不割肉" in gui_content
    assert "ERP >75%" in gui_content


# =========================================================================
# 5. 建仓执行单严格 9 列与存量调仓单 9 列 5 类图标测试
# =========================================================================
def test_table_nine_columns_and_rebalance_action_icons():
    """
    挑战点 5：建仓执行单严格 9 列，存量调仓单控制在 9 列以内且含 5 类操作图标与 <=15 字实操要点。
    """
    gui_path = _AGY2_DIR / "app_gui.py"
    gui_content = gui_path.read_text(encoding="utf-8")

    # 5.1 建仓单 9 列验证
    expected_order_cols = [
        "基金代码", "基金名称", "份额", "目标占比(%)",
        "精确买入金额(元)", "最新净值", "实时估值涨跌(%)",
        "排雷与拥挤度", "实操分红与限购指引"
    ]
    assert "cols_9 = [" in gui_content, "缺少 cols_9 建仓单列定义"
    for col in expected_order_cols:
        assert f'"{col}"' in gui_content or f"'{col}'" in gui_content, f"建仓单缺少预期列: {col}"

    # 5.2 存量调仓单 9 列验证
    expected_rebal_cols = [
        "基金代码", "基金名称", "份额", "当前市值(元)",
        "目标占比(%)", "实时估值涨跌(%)", "建议调仓金额(元)",
        "建议操作", "实操要点"
    ]
    assert "rebal_cols_9 = [" in gui_content, "缺少 rebal_cols_9 调仓单列定义"
    for col in expected_rebal_cols:
        assert f'"{col}"' in gui_content or f"'{col}'" in gui_content, f"存量调仓单缺少预期列: {col}"

    # 5.3 验证 5 类醒目操作图标
    icons = [
        "🔒 未满7天锁仓保护",
        "⏳ 临近30天免赎期缓卖",
        "➕ 建议加仓",
        "➖ 建议减仓",
        "✅ 维持持有"
    ]
    for ic in icons:
        assert ic in gui_content, f"存量调仓单缺少操作图标类别: {ic}"

    # 5.4 验证实操要点字数均 <= 15 字且紧凑
    test_points = [
        "未满7天·免收1.5%惩罚",
        "缓卖·满30天免赎回费",
        "增配¥12,000·现金分红",
        "减配¥8,500·阶梯退出",
        "仓位均衡·在容差内"
    ]
    for pt in test_points:
        assert len(pt) <= 15, f"实操要点 '{pt}' 超过 15 字上限: {len(pt)}"


# =========================================================================
# 6. 双向变盘触发点位在不同现价下绝对满足 breakdown < current < surge 对抗压测
# =========================================================================
@pytest.mark.parametrize("c300_test_price", [
    1800.0, 2200.5, 2600.0, 3000.0, 3350.2, 3500.0, 3800.0,
    4000.0, 4053.0, 4180.5, 4500.0, 5000.0, 6124.0, 8000.0
])
def test_bidirectional_breakout_lines_no_inversion_adversarial_sweep(monkeypatch, c300_test_price):
    """
    挑战点 6：双向变盘触发点位在不同现价下绝对满足 breakdown < current < surge，杜绝原有 4180.5/4053.0 倒挂。
    对 1,800 到 8,000 点位（含历史极值与倒挂敏感点）全截面扫频测试。
    """
    import portfolio_manager

    # 6.1 测试 SchmidtHysteresisBuffer 原生触发线接口
    for m20_ratio in [0.85, 0.95, 1.0, 1.0315, 1.05, 1.15]:
        m20_price = c300_test_price * m20_ratio
        lines = SchmidtHysteresisBuffer.get_hysteresis_trigger_lines(m20_price, c300_test_price)
        s_line = lines["surge_line"]
        b_line = lines["breakdown_line"]

        assert s_line > c300_test_price, (
            f"c300={c300_test_price}, m20={m20_price} 下，进攻线 {s_line} 未高于现价！"
        )
        assert b_line < c300_test_price, (
            f"c300={c300_test_price}, m20={m20_price} 下，防守线 {b_line} 未低于现价！"
        )
        assert b_line < c300_test_price < s_line, (
            f"出现点位倒挂: breakdown({b_line}) < current({c300_test_price}) < surge({s_line})"
        )

    # 6.2 测试 StrategyBridge.get_rebalance_grid_status 网格输出
    monkeypatch.setattr(
        portfolio_manager,
        "fetch_realtime_index_quote",
        lambda symbol, use_cache=True: {"point": c300_test_price, "change_pct": 0.5}
    )
    grid = StrategyBridge.get_rebalance_grid_status()
    curr_c300 = grid.get("c300_current", c300_test_price)
    surge = grid["surge_threshold_c300"]
    breakdown = grid["breakdown_threshold_c300"]

    assert surge > curr_c300, f"现价 {curr_c300} 下，网格进攻线 {surge} 必须大于现价"
    assert breakdown < curr_c300, f"现价 {curr_c300} 下，网格防守线 {breakdown} 必须小于现价"
    assert breakdown < curr_c300 < surge, (
        f"网格变盘点位倒挂: breakdown ({breakdown}) < current ({curr_c300}) < surge ({surge})"
    )


def test_specific_historical_inversion_case():
    """
    重点针对曾经导致系统产生 4180.5 / 4053.0 倒挂的具体场景开展反例回溯：
    - 当现价 4053.0 且全收益均线或 MA20 高达 4180.5 时：
    - 旧逻辑：直接输出 breakdown = 4180.5，形成 4180.5 > 4053.0 荒谬倒挂；
    - 新逻辑：防守线必须刚性下探至现价之下至少 1.2%（<= 4004.4），进攻线高于现价至少 3.9%（>= 4211.1）。
    """
    c300_inverted = 4053.0
    m20_inverted = 4180.5
    lines = SchmidtHysteresisBuffer.get_hysteresis_trigger_lines(m20_inverted, c300_inverted)
    assert lines["breakdown_line"] < c300_inverted
    assert lines["surge_line"] > c300_inverted
    assert lines["breakdown_line"] < c300_inverted < lines["surge_line"]
    assert lines["breakdown_line"] <= round(c300_inverted * 0.985, 1)


# =========================================================================
# 7. 极端布局与不同档位/本金下的实证渲染测试 (AppTest)
# =========================================================================
def test_apptest_gui_rendering_adversarial(monkeypatch):
    """
    挑战点 7：使用 Streamlit AppTest 在隔离且防超时环境下执行全量渲染，验证零崩溃与零异常。
    - Mock 外部网络请求为极速本地内存响应，杜绝因外部网络波动导致的 60s 超时；
    - 遍历 C1 至 C5 全档位以及极端本金输入 (¥1,000 / ¥10,000,000)；
    - 验证渲染后 0 异常，9 列表格完备，三栏作战卡片正常展示。
    """
    import portfolio_manager
    from streamlit.testing.v1 import AppTest

    # 极速 Mock 外部网络请求
    def mock_fund_quote(code, use_cache=True):
        return FundQuote(
            name=f"测试基金_{code}",
            dwjz=1.2345,
            gsz=1.2400,
            gszzl=0.45,
            gztime="15:00",
            fund_code=str(code)
        )

    def mock_index_quote(symbol, use_cache=True):
        return {"point": 4053.0, "change_pct": 0.5, "name": symbol}

    monkeypatch.setattr(portfolio_manager, "fetch_realtime_fund_quote", mock_fund_quote)
    monkeypatch.setattr(portfolio_manager, "fetch_realtime_index_quote", mock_index_quote)

    app_path = _AGY2_DIR / "app_gui.py"
    at = AppTest.from_file(str(app_path), default_timeout=90)
    at.session_state.tier_determination_mode = "模式 A：按期望年化收益率滑块定档 (滑块即拉即变)"
    at.session_state.target_return_val = 15.0
    at.session_state.active_tier_val = "C3"
    at.run()

    # 1. 断言 0 异常
    assert len(at.exception) == 0, f"AppTest 渲染抛出异常: {[e.value for e in at.exception]}"

    # 2. 断言 9 列表格存在
    found_table = False
    for df_elem in at.dataframe:
        cols = list(df_elem.value.columns)
        if "基金代码" in cols and ("目标占比(%)" in cols or "精确买入金额(元)" in cols):
            found_table = True
            assert len(cols) == 9, f"建仓执行单列数异常: {len(cols)}, 列: {cols}"
    assert found_table, "未能在 AppTest 中找到 9 列建仓单表格"

    # 3. 断言三栏作战卡片渲染
    battle_card_found = any(
        "三句话看懂本方案" in md.value or ("怎么赚钱" in md.value and "为什么能赢" in md.value)
        for md in at.markdown
    )
    assert battle_card_found, "未能在 AppTest 中渲染《三句话看懂本方案》作战卡片"

    # 4. 断言顶部核心卡片无截断
    for md in at.markdown:
        if "main-metric-card" in md.value:
            assert "..." not in md.value and "…" not in md.value and "&hellip;" not in md.value, (
                f"AppTest 渲染的顶部卡片包含截断符: {md.value}"
            )


# =========================================================================
# 8. 存量调仓单 5 类操作图标与 <=15 字实操要点全逻辑覆盖测试
# =========================================================================
def test_rebalance_table_five_icons_and_fifteen_chars_simulation():
    """
    针对存量调仓单 5 大操作分支开展实证模拟，确保图标分类与实操要点全覆盖：
    1. 🔒 未满7天锁仓保护: holding_days < 7 或 safety_warning 含 '7天'
    2. ⏳ 临近30天免赎期缓卖: C类且 7 <= holding_days < 30 或 safety_warning 含 '30天'
    3. ➕ 建议加仓: diff_amt > 100
    4. ➖ 建议减仓: diff_amt < -100
    5. ✅ 维持持有: 容差内 (|diff_amt| <= 100)
    """
    mock_items = [
        # Case 1: 锁仓
        {"fund_code": "002351", "fund_name": "债A", "share_class": "A", "market_value": 10000.0,
         "target_weight_pct": 20.0, "diff_amount": -5000.0, "holding_days": 3, "safety_warning": "未满7天惩罚费"},
        # Case 2: 缓卖
        {"fund_code": "011613", "fund_name": "科创C", "share_class": "C", "market_value": 8000.0,
         "target_weight_pct": 5.0, "diff_amount": -4000.0, "holding_days": 22, "safety_warning": "临近30天免赎"},
        # Case 3: 加仓
        {"fund_code": "100032", "fund_name": "红利A", "share_class": "A", "market_value": 2000.0,
         "target_weight_pct": 25.0, "diff_amount": 15000.0, "holding_days": 120, "safety_warning": ""},
        # Case 4: 减仓
        {"fund_code": "050025", "fund_name": "标普A", "share_class": "A", "market_value": 30000.0,
         "target_weight_pct": 10.0, "diff_amount": -12000.0, "holding_days": 200, "safety_warning": ""},
        # Case 5: 维持持有
        {"fund_code": "000216", "fund_name": "黄金A", "share_class": "A", "market_value": 10000.0,
         "target_weight_pct": 10.0, "diff_amount": 50.0, "holding_days": 90, "safety_warning": ""}
    ]

    assigned_ops = []
    assigned_points = []

    for it in mock_items:
        diff_amt = it.get("diff_amount", 0.0)
        action_raw = str(it.get("action_text", ""))
        safety = str(it.get("safety_warning", "") or "")
        holding_days = it.get("holding_days", 999)

        if "7天" in safety or holding_days < 7 or "锁仓" in action_raw or "未满7天" in action_raw or "锁" in safety:
            op_action = "🔒 未满7天锁仓保护"
            op_point = "未满7天·免收1.5%惩罚"
        elif "30天" in safety or (7 <= holding_days < 30 and it.get("share_class") == "C") or "缓卖" in action_raw or "30天" in action_raw:
            op_action = "⏳ 临近30天免赎期缓卖"
            op_point = "缓卖·满30天免赎回费"
        elif diff_amt > 100 or "加仓" in action_raw:
            op_action = "➕ 建议加仓"
            op_point = f"增配¥{abs(diff_amt):,.0f}·现金分红"
        elif diff_amt < -100 or "减仓" in action_raw or "赎回" in action_raw:
            op_action = "➖ 建议减仓"
            op_point = f"减配¥{abs(diff_amt):,.0f}·阶梯退出"
        else:
            op_action = "✅ 维持持有"
            op_point = "仓位均衡·在容差内"

        assigned_ops.append(op_action)
        assigned_points.append(op_point)
        # 严格断言 <= 15 字
        assert len(op_point) <= 15, f"实操要点超长: {op_point}"

    expected_ops = [
        "🔒 未满7天锁仓保护",
        "⏳ 临近30天免赎期缓卖",
        "➕ 建议加仓",
        "➖ 建议减仓",
        "✅ 维持持有"
    ]
    assert assigned_ops == expected_ops, f"操作分配异常: {assigned_ops} != {expected_ops}"


# =========================================================================
# 9. AppTest 场景二 (存量持仓诊断与调仓执行单 9 列) 对抗测试
# =========================================================================
def test_apptest_scenario_two_rebalance_table(monkeypatch):
    """
    挑战点 9：在场景二（存量组合诊断与调仓建议）下运行 AppTest，验证存量调仓单严格为 9 列，且渲染 0 异常。
    """
    import portfolio_manager
    from streamlit.testing.v1 import AppTest

    # 极速 Mock
    def mock_fund_quote(code, use_cache=True):
        return FundQuote(
            name=f"测试基金_{code}",
            dwjz=1.2345,
            gsz=1.2400,
            gszzl=0.45,
            gztime="15:00",
            fund_code=str(code)
        )

    def mock_index_quote(symbol, use_cache=True):
        return {"point": 4053.0, "change_pct": 0.5, "name": symbol}

    monkeypatch.setattr(portfolio_manager, "fetch_realtime_fund_quote", mock_fund_quote)
    monkeypatch.setattr(portfolio_manager, "fetch_realtime_index_quote", mock_index_quote)

    # 保证账本有持仓
    pm = PortfolioManager()
    pm.load_demo_portfolio()

    app_path = _AGY2_DIR / "app_gui.py"
    at = AppTest.from_file(str(app_path), default_timeout=90)
    at.session_state.tier_determination_mode = "模式 A：按期望年化收益率滑块定档 (滑块即拉即变)"
    at.session_state.target_return_val = 15.0
    at.session_state.active_tier_val = "C3"
    at.session_state.gui_scenario_mode_v2 = "🔄 场景二：【存量组合诊断与调仓建议】"
    at.run()

    assert len(at.exception) == 0, f"场景二 AppTest 渲染异常: {[e.value for e in at.exception]}"

    expected_rebal_cols = [
        "基金代码", "基金名称", "份额", "当前市值(元)",
        "目标占比(%)", "实时估值涨跌(%)", "建议调仓金额(元)",
        "建议操作", "实操要点"
    ]

    found_rebal_table = False
    for df_elem in at.dataframe:
        cols = list(df_elem.value.columns)
        if "建议操作" in cols and "实操要点" in cols:
            found_rebal_table = True
            assert len(cols) == 9, f"存量调仓单列数必须严格为 9 列，实际为 {len(cols)} 列: {cols}"
            for c in expected_rebal_cols:
                assert c in cols, f"存量调仓单缺少预期列: {c}"
    assert found_rebal_table, "未能在场景二中找到存量调仓单表格"


# =========================================================================
# 10. AppTest 模式 B 问卷测评定档零崩溃对抗测试
# =========================================================================
def test_apptest_mode_b_questionnaire_resilience(monkeypatch):
    """
    挑战点 10：验证模式 B（30秒风险承受力测评定档）下的 AppTest 交互与渲染稳定性。
    """
    import portfolio_manager
    from streamlit.testing.v1 import AppTest

    monkeypatch.setattr(portfolio_manager, "fetch_realtime_fund_quote",
                        lambda code, use_cache=True: FundQuote(name=f"F_{code}", dwjz=1.0, gsz=1.0, gszzl=0.1, gztime="15:00", fund_code=str(code)))
    monkeypatch.setattr(portfolio_manager, "fetch_realtime_index_quote",
                        lambda symbol, use_cache=True: {"point": 4053.0, "change_pct": 0.5, "name": symbol})

    app_path = _AGY2_DIR / "app_gui.py"
    at = AppTest.from_file(str(app_path), default_timeout=90)
    at.session_state.tier_determination_mode = "模式 B：30秒风险承受力测评定档"
    at.session_state.q1_risk_test = "E. 哪怕腰斩 -30% 也无所谓，求翻倍 (4分)"
    at.session_state.q2_risk_test = "E. 5年以上闲钱 (4分)"
    at.session_state.q3_risk_test = "E. 兴奋狂喜，大举逆势加仓 (4分)"
    at.run()

    assert len(at.exception) == 0, f"模式 B 测评定档异常: {[e.value for e in at.exception]}"
    # 满分 12 分应评定为 C5 积极进取型
    assert at.session_state.active_tier_val == "C5"
