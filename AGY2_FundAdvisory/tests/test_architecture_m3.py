# -*- coding: utf-8 -*-
"""
AGY2 架构级进化与通用量化重构红队验收测试套件 (tests/test_architecture_m3.py)
Covering Architecture Red Team Acceptance Criteria:
1. AST 静态代码反硬编码审计 (test_ast_audit_no_hardcoded_stock_codes_and_no_cat_map)
   - 遍历 app_gui.py, portfolio_manager.py, strategy_bridge.py 抽象语法树
   - 严禁存在手写静态 cat_map
   - 严禁存在针对特定 6 位股票代码的排雷豁免分支或 77 只金融机构硬编码白名单集合
   - 验证统一大类资产分类解析器 classify_fund_asset_class 与三层动态排雷
2. C1 至 C5 动态风险预算单调性与攻防状态机自适应测试 (test_dynamic_risk_budget_monotonicity_and_regime_adaptation)
   - 针对牛市进攻、震荡收息、熊市破位三组市场输入
   - 验证动态适应市场攻防状态（牛市放大弹性、震荡倾斜红利、熊市降仓避险切换纯债黄金）
   - 严格断言全截面单调性: Equity(C1) < Equity(C2) < Equity(C3) < Equity(C4) < Equity(C5)
3. 双向变盘触发点位逻辑校验测试 (test_bidirectional_breakout_points_no_inversion)
   - 针对不同市场点位输入调用 get_rebalance_grid_status()
   - 严格断言在任意行情下: surge > current 且 breakdown < current，彻底验证消除 4180.5/4053.0 倒挂
4. 9 列与无截断 AppTest 端到端渲染测试 (test_gui_step3_table_9_cols_and_no_truncation)
   - 使用 Streamlit AppTest 端到端渲染
   - 断言步骤三建仓执行单严格 9 列
   - 存量调仓单控制在 9 列以内且包含规范操作图标
   - 顶部 7 张核心卡片无省略号截断
   - 三栏作战卡片《三句话看懂本方案》正确渲染
"""

import ast
import re
import sys
from pathlib import Path
import pytest
import pandas as pd
import numpy as np

# 确保 AGY2 模块位于 sys.path
_CURRENT_DIR = Path(__file__).resolve().parent
_AGY2_DIR = _CURRENT_DIR.parent
_WORKSPACE_ROOT = _AGY2_DIR.parent
if str(_AGY2_DIR) not in sys.path:
    sys.path.insert(0, str(_AGY2_DIR))
if str(_WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE_ROOT))


# =========================================================================
# 1. AST 静态代码反硬编码审计
# =========================================================================
def test_ast_audit_no_hardcoded_stock_codes_and_no_cat_map():
    """
    AST 静态代码反硬编码审计：
    - 严密扫描 app_gui.py、portfolio_manager.py 与 strategy_bridge.py；
    - 断言不存在针对特定股票代码（如 6 位数字代码 if/else 豁免分支或 77 只金融机构硬编码白名单集合）；
    - 断言不存在手写静态 cat_map；
    - 验证统一大类资产分类解析器 classify_fund_asset_class 真实生效。
    """
    base_dir = _AGY2_DIR

    # 1.1 审计 app_gui.py：严禁存在手写静态 cat_map 字典
    gui_file = base_dir / "app_gui.py"
    assert gui_file.exists(), f"未找到 {gui_file}"
    gui_tree = ast.parse(gui_file.read_text(encoding="utf-8"), filename="app_gui.py")
    for node in ast.walk(gui_tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "cat_map":
                    pytest.fail(
                        "app_gui.py 中仍存在静态赋值变量 cat_map！"
                        "必须彻底移除并调用 PortfolioManager.classify_fund_asset_class 统一分类解析器！"
                    )

    # 1.2 审计 portfolio_manager.py 与 strategy_bridge.py：严禁存在 77 只金融机构股票代码硬编码白名单集合
    pm_file = base_dir / "portfolio_manager.py"
    assert pm_file.exists(), f"未找到 {pm_file}"
    pm_tree = ast.parse(pm_file.read_text(encoding="utf-8"), filename="portfolio_manager.py")

    # 77 只典型金融机构个股代码（银行、证券、保险、多元金融）
    known_financial_stocks = {
        "600000", "600015", "600016", "600036", "600908", "600919", "600926", "600928", "601009",
        "601077", "601128", "601166", "601169", "601187", "601229", "601288", "601328", "601398",
        "601577", "601658", "601665", "601818", "601825", "601838", "601860", "601916", "601939",
        "601963", "601988", "601997", "601998", "603323", "000001", "002142", "002807", "002839",
        "002936", "002948", "002958", "002966", "001227", "001337", "601318", "601601", "601628",
        "601336", "601319", "601995", "600061", "000627", "000712", "000987", "600864", "600030",
        "601688", "600837", "601211", "000776", "600999", "000166", "601881", "601066", "601788",
        "600958", "601901", "601377", "601108", "601198", "002736", "601878", "000783", "600109",
        "600918", "601059", "601136", "601456", "002926", "002939", "002945", "601877", "601236",
        "601099"
    }

    # 检查 Assign 变量名
    for node in ast.walk(pm_tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    name_lower = target.id.lower()
                    if name_lower in ["financial_codes", "bank_codes", "bank_stock_codes", "financial_stock_codes"]:
                        pytest.fail(f"portfolio_manager.py 中仍存在硬编码金融股票集合变量: {target.id}！必须铲除！")

        # 检查 Set/List/Tuple 字面量是否包含金融股白名单
        if isinstance(node, (ast.Set, ast.List, ast.Tuple)):
            const_strs = {
                elt.value for elt in node.elts
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
            }
            overlap = const_strs & known_financial_stocks
            if len(overlap) >= 3:
                pytest.fail(
                    f"portfolio_manager.py 中发现包含 {len(overlap)} 只金融个股的硬编码集合: {list(overlap)[:5]}...！"
                    "必须基于申万行业分类与财务比率公式进行动态排雷识别！"
                )

        # 检查 Compare 比较表达式是否有针对特定个股的代码分支
        if isinstance(node, ast.Compare):
            for comp in node.comparators:
                if (
                    isinstance(comp, ast.Constant)
                    and isinstance(comp.value, str)
                    and comp.value in ["600036", "601398", "601288", "601939", "600000", "601166"]
                ):
                    pytest.fail(f"portfolio_manager.py 中发现针对特定金融个股 {comp.value} 的硬编码比较分支！")

    # 1.3 检查 strategy_bridge.py
    sb_file = base_dir / "strategy_bridge.py"
    assert sb_file.exists(), f"未找到 {sb_file}"
    sb_tree = ast.parse(sb_file.read_text(encoding="utf-8"), filename="strategy_bridge.py")
    for node in ast.walk(sb_tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "FUND_SIX_DIMENSION_PROFILE":
                    pytest.fail(
                        "strategy_bridge.py 中仍存在全局静态打分字典 FUND_SIX_DIMENSION_PROFILE！"
                        "必须彻底移除并委托至 PortfolioManager.compute_fund_six_dimension_score 真实多因子计算！"
                    )
        if isinstance(node, (ast.Set, ast.List, ast.Tuple)):
            const_strs = {
                elt.value for elt in node.elts
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
            }
            overlap = const_strs & known_financial_stocks
            if len(overlap) >= 3:
                pytest.fail(f"strategy_bridge.py 中发现包含 {len(overlap)} 只金融股的硬编码集合！")

    # 1.4 验证统一大类资产分类解析器 classify_fund_asset_class 真实存在并能够有效工作
    from portfolio_manager import PortfolioManager
    pm = PortfolioManager()
    assert hasattr(pm, "classify_fund_asset_class"), "PortfolioManager 缺少 classify_fund_asset_class 统一分类解析方法"

    assert pm.classify_fund_asset_class("002351") == "纯债固收"
    assert pm.classify_fund_asset_class("000216") == "黄金对冲"
    assert pm.classify_fund_asset_class("100032") == "A股红利高股息"
    assert pm.classify_fund_asset_class("005561") == "A股红利低波"
    assert pm.classify_fund_asset_class("011613") == "科技成长进攻"
    assert pm.classify_fund_asset_class("050025") == "美股海外对冲"
    assert pm.classify_fund_asset_class("001071") == "美股海外对冲"

    # 兜底测试：未知代码绝不输出已被废弃的“其他存量资产”
    fallback_res = pm.classify_fund_asset_class("999999", "未知测试标的")
    assert fallback_res != "其他存量资产", f"分类器不应返回已被废弃的'其他存量资产'，实际返回: {fallback_res}"


# =========================================================================
# 2. C1 至 C5 动态风险预算单调性与攻防状态机自适应测试
# =========================================================================
def test_dynamic_risk_budget_monotonicity_and_regime_adaptation():
    """
    C1 至 C5 动态风险预算单调性与攻防状态机自适应测试：
    - 针对牛市进攻（主升浪/结构牛）、震荡收息、熊市破位（跌破中长期均线且均线向下发散）三组市场输入；
    - 断言各档位动态适应市场状态（牛市放大进攻弹性资产、震荡向高股息防御倾斜、熊市全档位算法止损并向纯债黄金避险切换）；
    - 断言在所有截面下，目标权益仓位均严格满足单调性：Equity(C1) < Equity(C2) < Equity(C3) < Equity(C4) < Equity(C5)。
    """
    from strategy_bridge import StrategyBridge
    from portfolio_manager import PortfolioManager

    df_mat = StrategyBridge.load_matrix()
    pm = PortfolioManager()

    # 模拟三组具有显著差异的市场截面状态输入
    # 2.1 主升浪进攻态 (牛市)
    snapshot_bull = {
        "market_state": "主升浪进攻态",
        "market_state_code": "REGIME_BULL_ATTACK",
        "regime_code": "REGIME_BULL_ATTACK",
        "regime_name": "主升浪进攻态",
        "regime": "BULL",
        "c300_price": 4350.0,
        "m20_price": 4150.0,
        "m60_price": 4000.0,
        "m120_price": 3900.0,
        "bias_20": 4.82,
        "bias_60": 8.75,
        "bias_120": 11.54,
        "opt_iv_pct": 14.5,
        "im_basis_annual_pct": 2.5,  # 升水
        "dr007_val": 1.75,
        "erp_ratio": 65.0,
    }

    # 2.2 震荡收息态 (震荡市)
    snapshot_osc = {
        "market_state": "震荡收息态",
        "market_state_code": "REGIME_OSCILLATION_INCOME",
        "regime_code": "REGIME_OSCILLATION_INCOME",
        "regime_name": "震荡收息态",
        "regime": "OSCILLATING",
        "c300_price": 4053.0,
        "m20_price": 4060.0,
        "m60_price": 4020.0,
        "m120_price": 3950.0,
        "bias_20": -0.17,
        "bias_60": 0.82,
        "bias_120": 2.61,
        "opt_iv_pct": 17.0,
        "im_basis_annual_pct": -3.0,
        "dr007_val": 1.85,
        "erp_ratio": 78.5,  # 较高股债性价比
    }

    # 2.3 破位防御态 (熊市破位)
    snapshot_bear = {
        "market_state": "熊市破位态",
        "market_state_code": "REGIME_BEAR_BREAKDOWN",
        "regime_code": "REGIME_BEAR_BREAKDOWN",
        "regime_name": "熊市破位态",
        "regime": "BEAR",
        "c300_price": 3650.0,
        "m20_price": 3850.0,
        "m60_price": 3980.0,
        "m120_price": 4100.0,
        "bias_20": -5.19,
        "bias_60": -8.29,
        "bias_120": -10.98,
        "opt_iv_pct": 28.5,  # 恐慌性飙升
        "im_basis_annual_pct": -12.5,  # 深度贴水
        "dr007_val": 2.35,
        "erp_ratio": 88.0,
    }

    def get_tier_equity_and_defensive(weights_dict):
        """
        根据分类器动态聚合权益类与防御类资产占比
        纯债与黄金为避险防御资产，其余为权益类资产
        """
        defensive_w = 0.0
        equity_w = 0.0
        for code, w in weights_dict.items():
            cat = pm.classify_fund_asset_class(code) if hasattr(pm, "classify_fund_asset_class") else None
            if cat in ["纯债固收", "黄金对冲"] or code in ["002351", "000086", "018757", "000216", "000217"]:
                defensive_w += w
            else:
                equity_w += w
        return equity_w, defensive_w

    regimes = [
        ("牛市进攻态", snapshot_bull),
        ("震荡收息态", snapshot_osc),
        ("熊市破位态", snapshot_bear)
    ]

    results = {}

    for regime_name, snapshot in regimes:
        eq_weights = {}
        def_weights = {}
        tier_weights_map = {}
        for tier in ["C1", "C2", "C3", "C4", "C5"]:
            # 支持动态权重计算接口
            if hasattr(StrategyBridge, "compute_dynamic_tier_weights"):
                weights = StrategyBridge.compute_dynamic_tier_weights(df_mat, tier, snapshot)
            else:
                weights = StrategyBridge.get_tier_target_weights(tier)

            assert isinstance(weights, dict), f"{tier} 返回权重应为字典"
            # 权重归一化校验
            total_w = sum(weights.values())
            if total_w > 10.0:
                weights = {k: v / 100.0 for k, v in weights.items()}
                total_w = sum(weights.values())
            assert abs(total_w - 1.0) < 1e-3, f"{tier} 权重之和应为 1.0，实际为 {total_w}"

            tier_weights_map[tier] = weights
            eq_w, def_w = get_tier_equity_and_defensive(weights)
            eq_weights[tier] = round(eq_w, 4)
            def_weights[tier] = round(def_w, 4)

        results[regime_name] = (eq_weights, def_weights, tier_weights_map)

        # 核心断言 1: 在所有行情截面下，目标权益仓位必须严格满足单调递增性
        # Equity(C1) < Equity(C2) < Equity(C3) < Equity(C4) < Equity(C5)
        assert eq_weights["C1"] < eq_weights["C2"], (
            f"{regime_name} 下 C1 权益仓位 ({eq_weights['C1']}) 应严格小于 C2 ({eq_weights['C2']})"
        )
        assert eq_weights["C2"] < eq_weights["C3"], (
            f"{regime_name} 下 C2 权益仓位 ({eq_weights['C2']}) 应严格小于 C3 ({eq_weights['C3']})"
        )
        assert eq_weights["C3"] < eq_weights["C4"], (
            f"{regime_name} 下 C3 权益仓位 ({eq_weights['C3']}) 应严格小于 C4 ({eq_weights['C4']})"
        )
        assert eq_weights["C4"] < eq_weights["C5"], (
            f"{regime_name} 下 C4 权益仓位 ({eq_weights['C4']}) 应严格小于 C5 ({eq_weights['C5']})"
        )

    # 核心断言 2: 状态机攻防自适应
    bull_eq, bull_def, bull_map = results["牛市进攻态"]
    bear_eq, bear_def, bear_map = results["熊市破位态"]
    osc_eq, osc_def, osc_map = results["震荡收息态"]

    # 牛市进攻态下，高进取型 (C4, C5) 权益敞口显著放大，高于熊市破位态
    assert bull_eq["C5"] >= bear_eq["C5"], "牛市 C5 权益仓位应大于等于熊市 C5 权益仓位"
    assert bull_eq["C4"] >= bear_eq["C4"], "牛市 C4 权益仓位应大于等于熊市 C4 权益仓位"

    # 熊市破位态下，所有档位触发算法止损降仓与避险切换，纯债与黄金防御仓位增加
    assert bear_def["C5"] >= bull_def["C5"], "熊市 C5 防御避险仓位应大于等于牛市"
    assert bear_def["C4"] >= bull_def["C4"], "熊市 C4 防御避险仓位应大于等于牛市"
    assert bear_def["C3"] >= bull_def["C3"], "熊市 C3 防御避险仓位应大于等于牛市"

    # 牛市进攻态下，C4/C5 必须包含高弹性进攻资产（如 011613 科创50）
    assert "011613" in bull_map["C5"], "牛市 C5 必须配置 011613 华夏科创50C 等进攻标的"
    assert "011613" in bull_map["C4"], "牛市 C4 必须配置 011613 华夏科创50C 等进攻标的"


# =========================================================================
# 3. 双向变盘触发点位逻辑校验测试
# =========================================================================
def test_bidirectional_breakout_points_no_inversion(monkeypatch):
    """
    双向变盘触发点位逻辑校验测试：
    - 针对任意市场点位输入调用 get_rebalance_grid_status()；
    - 断言在任意行情下，向上进攻触发线点位严格大于当前现价（surge > current），
      向下防守破位触发线点位严格小于当前现价（breakdown < current），彻底验证消除 4180.5/4053.0 倒挂。
    """
    from strategy_bridge import StrategyBridge
    import portfolio_manager

    # 3.1 默认真实截面状态测试
    grid = StrategyBridge.get_rebalance_grid_status()
    curr_c300 = grid.get("c300_current", grid.get("c300_price", 4053.0))
    surge = grid["surge_threshold_c300"]
    breakdown = grid["breakdown_threshold_c300"]

    assert surge > curr_c300, (
        f"向上进攻触发线 ({surge}) 必须严格高于当前现价 ({curr_c300})"
    )
    assert breakdown < curr_c300, (
        f"向下防守破位线 ({breakdown}) 必须严格低于当前现价 ({curr_c300})，消除倒挂！"
    )

    # 3.2 模拟不同指数点位下的双向变盘触发线，验证无倒挂且严格包络
    test_price_points = [2800.0, 3200.0, 3500.0, 3800.0, 4000.0, 4053.0, 4180.5, 4500.0, 4800.0, 5200.0]
    for p in test_price_points:
        monkeypatch.setattr(
            portfolio_manager,
            "fetch_realtime_index_quote",
            lambda symbol, use_cache=True: {"point": p, "change_pct": 0.0}
        )
        grid_p = StrategyBridge.get_rebalance_grid_status()
        p_curr = grid_p.get("c300_current", grid_p.get("c300_price", p))
        p_surge = grid_p["surge_threshold_c300"]
        p_breakdown = grid_p["breakdown_threshold_c300"]

        assert p_surge > p, (
            f"点位 {p} 下，向上进攻线 {p_surge} 必须严格大于现价 {p}"
        )
        assert p_breakdown < p, (
            f"点位 {p} 下，向下防守线 {p_breakdown} 必须严格小于现价 {p}，消除原有 4180.5/4053.0 倒挂"
        )
        assert p_breakdown < p_curr < p_surge, (
            f"点位 {p} 下必须满足 breakdown ({p_breakdown}) < current ({p_curr}) < surge ({p_surge})"
        )


# =========================================================================
# 4. 9 列与无截断 AppTest 端到端渲染测试
# =========================================================================
def test_gui_step3_table_9_cols_and_no_truncation():
    """
    9 列与无截断 AppTest 端到端渲染测试：
    - 使用 Streamlit AppTest 断言步骤三建仓执行单保留 9 列，存量调仓单控制在 9 列以内且包含规范操作图标；
    - 断言顶部 7 张核心卡片无省略号截断，且三栏作战卡片正确渲染。
    """
    from streamlit.testing.v1 import AppTest
    from pathlib import Path

    app_path = _AGY2_DIR / "app_gui.py"
    at = AppTest.from_file(str(app_path), default_timeout=120)
    at.session_state.tier_determination_mode = "模式 A：按期望年化收益率滑块定档 (滑块即拉即变)"
    at.session_state.target_return_val = 15.0
    at.session_state.active_tier_val = "C3"
    at.run()

    assert len(at.exception) == 0, f"AppTest 渲染抛出异常: {[e.value for e in at.exception]}"

    # 4.1 步骤三建仓执行单保留严格 9 列
    expected_order_cols = [
        "基金代码", "基金名称", "份额", "目标占比(%)",
        "精确买入金额(元)", "最新净值", "实时估值涨跌(%)",
        "排雷与拥挤度", "实操分红与限购指引"
    ]
    found_order_df = False
    for df_elem in at.dataframe:
        df_val = df_elem.value
        cols = list(df_val.columns)
        if "基金代码" in cols and "精确买入金额(元)" in cols and "实操分红与限购指引" in cols:
            found_order_df = True
            assert len(cols) == 9, (
                f"步骤三建仓执行单应严格为 9 列，实际为 {len(cols)} 列: {cols}"
            )
            for exp_col in expected_order_cols:
                assert exp_col in cols, f"建仓执行单缺少预期列: {exp_col}"
    assert found_order_df, "未能在界面中捕获到步骤三建仓执行单 DataFrame"

    # 4.2 存量调仓单控制在 9 列以内且包含规范操作图标
    for df_elem in at.dataframe:
        df_val = df_elem.value
        cols = list(df_val.columns)
        if any(c in cols for c in ["建议调仓操作", "操作方向", "调仓建议", "操作指引"]):
            assert len(cols) <= 9, (
                f"存量调仓单列数必须控制在 9 列以内，实际为 {len(cols)} 列: {cols}"
            )

    # 4.3 顶部 7 张核心卡片无省略号截断
    found_card = False
    for md in at.markdown:
        val = md.value
        if "main-metric-card" in val:
            found_card = True
            assert "..." not in val and "…" not in val and "&hellip;" not in val, (
                f"顶部 7 张核心指标卡片中存在省略号截断: {val}"
            )
    assert found_card, "未在界面中匹配到顶部 7 张核心指标卡片"

    # 4.4 三栏作战卡片《三句话看懂本方案》正确渲染
    found_battle_card = False
    for md in at.markdown:
        val = md.value
        if "三句话看懂本方案" in val or ("怎么赚钱" in val and "为什么能赢" in val):
            found_battle_card = True
            break
    assert found_battle_card, "未能在界面中渲染《三句话看懂本方案》作战卡片"


# =========================================================================
# 5. AST 反硬编码审计与六维多因子真动态评分一致性测试
# =========================================================================
def test_ast_audit_no_hardcoded_fund_profiles_and_dynamic_scoring_parity():
    """
    AST 静态代码反硬编码审计与六维多因子打分一致性验证：
    1. 遍历 strategy_bridge.py AST，断言不存在 FUND_SIX_DIMENSION_PROFILE 静态打分字典定义；
    2. 验证 StrategyBridge.calculate_fund_six_dimension_score 与 PortfolioManager.compute_fund_six_dimension_score 动态打分 100% 对齐；
    3. 验证 overall_score 与 total_score 双向键名完备性。
    """
    base_dir = _AGY2_DIR
    sb_file = base_dir / "strategy_bridge.py"
    assert sb_file.exists(), f"未找到 {sb_file}"
    sb_tree = ast.parse(sb_file.read_text(encoding="utf-8"), filename="strategy_bridge.py")

    found_static_profile = False
    for node in ast.walk(sb_tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "FUND_SIX_DIMENSION_PROFILE":
                    found_static_profile = True
                    break
    assert not found_static_profile, "strategy_bridge.py 中绝对严禁存在 FUND_SIX_DIMENSION_PROFILE 静态打分表！"

    # 打分对齐验证
    from strategy_bridge import StrategyBridge
    from portfolio_manager import PortfolioManager
    pm = PortfolioManager()

    test_codes = ["002351", "000216", "100032", "005561", "011613", "050025"]
    for code in test_codes:
        s_bridge = StrategyBridge.calculate_fund_six_dimension_score(code)
        s_pm = pm.compute_fund_six_dimension_score(code)

        assert s_bridge["total_score"] == s_pm["total_score"], (
            f"基金 {code} 打分脱节: StrategyBridge={s_bridge['total_score']} vs PortfolioManager={s_pm['total_score']}"
        )
        assert s_bridge["overall_score"] == s_bridge["total_score"]
        assert s_pm["overall_score"] == s_pm["total_score"]
        assert 60.0 <= s_bridge["total_score"] <= 100.0

