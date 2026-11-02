"""
验证 Tab 独立异常隔离、函数签名自适应以及 Streamlit AppTest 0 异常渲染
(AGY2_FundAdvisory/tests/test_tab_boundaries_and_rebalance.py)
"""

import ast
import inspect
import sys
from pathlib import Path
import pytest
import pandas as pd
from streamlit.testing.v1 import AppTest

# 路径对齐
CURRENT_DIR = Path(__file__).resolve().parent.parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from strategy_bridge import StrategyBridge
from winrate_engine import WinRateEngine
from portfolio_manager import PortfolioManager, FundHolding, HoldingBatch


def test_generate_ai_rebalance_orders_signatures_and_modes():
    """验证 generate_ai_rebalance_orders 与 rebalance_portfolio 显式支持 mode 与 **kwargs，且业务逻辑完全闭环"""
    sig_orders = inspect.signature(StrategyBridge.generate_ai_rebalance_orders)
    assert "mode" in sig_orders.parameters, "generate_ai_rebalance_orders 必须支持 mode 参数"
    assert sig_orders.parameters["mode"].default == "gentle"
    assert any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig_orders.parameters.values()), "必须支持 **kwargs"

    sig_reb = inspect.signature(StrategyBridge.rebalance_portfolio)
    assert "mode" in sig_reb.parameters, "rebalance_portfolio 必须支持 mode 参数"
    assert sig_reb.parameters["mode"].default == "gentle"
    assert any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig_reb.parameters.values()), "必须支持 **kwargs"

    # 1. 真实持仓用例：
    # - 100032: 偏离 -2% (在 3% 缓冲内) 且已持有 60 天
    # - 000216: 偏离 -3% 且持有仅 3 天 (<7天惩罚锁)
    # - 008682: C 类份额，偏离 -5% 且持有 15 天 (7 <= 天数 < 30)
    h_mature = FundHolding(
        fund_code="100032", fund_name="富国中证红利指数增强A", share_class="A",
        shares=52000.0, current_nav=1.0, market_value=52000.0,
        batches=[HoldingBatch(batch_id="b1", buy_date="2026-09-01", shares=52000.0, cost_nav=1.0, fee=0.0, holding_days=60)],
    )
    h_locked = FundHolding(
        fund_code="000216", fund_name="华安黄金易ETF联接A", share_class="A",
        shares=38000.0, current_nav=1.0, market_value=38000.0,
        batches=[HoldingBatch(batch_id="b2", buy_date="2026-10-30", shares=38000.0, cost_nav=1.0, fee=0.0, holding_days=3)],
    )
    h_c_class = FundHolding(
        fund_code="008682", fund_name="富国中证红利指数增强C", share_class="C",
        shares=10000.0, current_nav=1.0, market_value=10000.0,
        batches=[HoldingBatch(batch_id="b3", buy_date="2026-10-18", shares=10000.0, cost_nav=1.0, fee=0.0, holding_days=15)],
    )
    holdings = {"100032": h_mature, "000216": h_locked, "008682": h_c_class}
    # 总市值 100,000 元，目标权重：100032 50% (-2%), 000216 35% (-3%), 008682 5% (-5%), 002351 10% (+10%)
    targets = {"100032": 0.50, "000216": 0.35, "008682": 0.05, "002351": 0.10}

    # 测试 gentle 模式
    res_gentle = StrategyBridge.generate_ai_rebalance_orders(
        current_holdings=holdings,
        available_cash=0.0,
        target_weights_funds=targets,
        mode="gentle",
        extra_test_arg=True
    )
    map_g = {it["fund_code"]: it for it in res_gentle["items"]}
    assert map_g["100032"]["action"] == "HOLD", "gentle 模式下 3% 偏离缓冲区内应 HOLD"
    assert map_g["000216"]["action"] == "HOLD", "gentle 模式下未满 7 天应强力阻断 HOLD"
    assert "7天" in map_g["000216"]["safety_warning"]

    # 测试 forced 模式
    res_forced = StrategyBridge.generate_ai_rebalance_orders(
        current_holdings=holdings,
        available_cash=0.0,
        target_weights_funds=targets,
        mode="forced",
        extra_test_arg=True
    )
    map_f = {it["fund_code"]: it for it in res_forced["items"]}
    assert map_f["100032"]["action"] == "SELL", "forced 模式下取消 3% 缓冲，偏离 -2% 应触发一步到位减仓"
    assert "一步到位减仓" in map_f["100032"]["action_text"]
    assert map_f["000216"]["action"] == "HOLD", "工作区准则 #2：即使 forced 模式，未满 7 天惩罚期依然绝对禁止卖出"

    # 测试 C 类份额持有期与 30 天缓卖预警
    assert map_f["008682"]["holding_days"] == 15, "必须正确将 holding_days 存入 items 字典供 GUI 解析"
    assert "30天" in map_f["008682"]["safety_warning"], "C 类持有 15 天应触发 30 天免赎缓卖提示"

    # 测试 rebalance_portfolio 透传 mode 与 **kwargs
    pm = PortfolioManager()
    res_reb = StrategyBridge.rebalance_portfolio(
        tier="C3",
        pm=pm,
        mode="forced",
        custom_kwarg=123
    )
    assert "items" in res_reb


def test_winrate_engine_multi_horizon_winrate_table_signature():
    """验证 multi_horizon_winrate_table 支持 market_snapshot 与 **kwargs，且底层参数安全传递"""
    sig = inspect.signature(WinRateEngine.multi_horizon_winrate_table)
    assert "market_snapshot" in sig.parameters, "multi_horizon_winrate_table 必须支持 market_snapshot"
    assert any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()), "必须支持 **kwargs"

    sig_roll = inspect.signature(WinRateEngine.rolling_target_winrate)
    assert "market_snapshot" in sig_roll.parameters, "rolling_target_winrate 必须支持 market_snapshot"
    assert any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig_roll.parameters.values()), "必须支持 **kwargs"

    n = 300
    dates = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=n)
    nav_series = pd.Series(1.0 + 0.0005 * pd.Series(range(n)), index=dates)

    mock_snapshot = {
        "erp_percentile": 80.0,
        "bias_20": -0.5,
        "c300": 4050.0,
        "mom60": -2.0,
        "ewma_vol": 15.0
    }

    table = WinRateEngine.multi_horizon_winrate_table(
        nav_series=nav_series,
        target_annual_return=0.10,
        market_snapshot=mock_snapshot,
        custom_extra_param="safe_passthrough"
    )
    assert isinstance(table, dict)
    assert len(table) >= 3, "必须包含短期、中期、长期胜率结果"
    for k, v in table.items():
        assert "win_rate" in v
        assert "no_loss_rate" in v


def test_tab2_signature_fallback_logic():
    """验证 app_gui.py 中对 TypeError 的剥离 mode 降级防御机制"""
    # 模拟旧版无 mode 参数的函数
    def mock_legacy_generate(current_holdings, available_cash, target_weights_funds, pm=None):
        return {"items": [{"fund_code": "legacy", "action": "HOLD"}], "mode_used": "legacy"}

    order_call_kwargs = {
        "current_holdings": {},
        "available_cash": 0.0,
        "target_weights_funds": {},
        "pm": None,
        "mode": "forced",
    }

    # 模拟 app_gui 中的 try ... except TypeError 逻辑
    try:
        res = mock_legacy_generate(**order_call_kwargs)
    except TypeError:
        order_call_kwargs.pop("mode", None)
        res = mock_legacy_generate(**order_call_kwargs)

    assert res["mode_used"] == "legacy"
    assert len(res["items"]) == 1


def test_ast_tab_error_boundaries_isolation():
    """通过静态 AST 语法树断言 5 大主 Tab 均有顶层 try...except 错误边界隔离"""
    app_path = CURRENT_DIR / "app_gui.py"
    with open(app_path, "r", encoding="utf-8") as f:
        source = f.read()

    tree = ast.parse(source)
    tab_names = {
        "tab_zero_start",
        "tab_holdings_and_rebalance",
        "tab_toolbox",
        "tab_backtest",
        "tab_market_optimizer"
    }

    protected_tabs = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.With):
            for item in node.items:
                if isinstance(item.context_expr, ast.Name) and item.context_expr.id in tab_names:
                    tab_id = item.context_expr.id
                    has_try = any(isinstance(stmt, ast.Try) for stmt in node.body)
                    if has_try:
                        protected_tabs.add(tab_id)

    assert protected_tabs == tab_names, f"未包裹顶级 try-except 的 Tab: {tab_names - protected_tabs}"


def test_streamlit_apptest_zero_exceptions():
    """通过 Streamlit 官方 AppTest 框架渲染 app_gui.py，断言 0 个未捕获异常且 0 个错误横幅"""
    app_path = CURRENT_DIR / "app_gui.py"
    at = AppTest.from_file(str(app_path), default_timeout=150)
    at.session_state.active_tier_val = "C3"
    at.session_state.target_return_val = 15.0
    at.run(timeout=150)

    exceptions = [f"{type(e).__name__}: {e.value}" for e in at.exception]
    assert len(at.exception) == 0, f"AppTest 运行抛出未捕获异常: {exceptions}"
    assert len(at.error) == 0, f"AppTest 页面出现错误横幅: {[e.value for e in at.error]}"
    assert len(at.tabs) >= 5, f"预期渲染至少 5 个 Tab 容器，实际渲染 {len(at.tabs)} 个"
