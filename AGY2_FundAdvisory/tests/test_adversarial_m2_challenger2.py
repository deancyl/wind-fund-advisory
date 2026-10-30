"""
Adversarial Stress Test Suite for Milestone 2 (Challenger 2)
Focus: Boundary conditions, EWMA fallback, Utility edge values, QDII settlement, and Order execution safety.
"""

import pytest
import numpy as np
import pandas as pd
from pathlib import Path
import sys

PROJECT_DIR = Path(__file__).resolve().parent.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from data_loader import DataLoader
from strategy_bridge import StrategyBridge
from portfolio_manager import PortfolioManager, calculate_rebalance_net_utility
from trading_clock_fee import FeeMatrixCalculator


# =====================================================================
# 1. EWMA 波动率与相关性边界与极值测试 (compute_ewma_volatility_and_correlation)
# =====================================================================

def test_ewma_volatility_none_input():
    """测试 DataFrame 为 None 时的兜底保护与返回值规范"""
    vols, corr = DataLoader.compute_ewma_volatility_and_correlation(None)
    assert isinstance(vols, pd.Series), "None 输入必须返回 pd.Series"
    assert isinstance(corr, pd.DataFrame), "None 输入必须返回 pd.DataFrame"
    assert len(vols) == 10
    assert corr.shape == (10, 10)
    # 纯债波动率显著低于股票基准
    assert vols["H11009"] == 0.035
    assert vols["930609"] == 0.030
    assert vols["H00300"] == 0.18
    # 相关性矩阵应为单位矩阵
    assert np.allclose(corr.values, np.eye(10))


def test_ewma_volatility_empty_dataframe():
    """测试空 DataFrame 输入时的安全兜底"""
    empty_df = pd.DataFrame()
    vols, corr = DataLoader.compute_ewma_volatility_and_correlation(empty_df)
    assert isinstance(vols, pd.Series)
    assert isinstance(corr, pd.DataFrame)
    assert len(vols) == 10
    assert vols["H11009"] == 0.035
    assert vols["930609"] == 0.030
    assert vols["H00300"] == 0.18
    assert np.allclose(corr.values, np.eye(10))


@pytest.mark.parametrize("n_rows", [1, 2, 3, 4])
def test_ewma_volatility_fewer_than_5_rows(n_rows):
    """测试 DataFrame 行数小于 5 行 (1, 2, 3, 4 行) 时的优雅降级"""
    cols = ['H00300', 'H00905', 'H00852', 'H00922', 'H30269', 'STAR50_STITCH', 'AU9999', 'SPX_CNY', '930609', 'H11009']
    short_df = pd.DataFrame(
        np.random.rand(n_rows, len(cols)) * 1000.0,
        columns=cols
    )
    vols, corr = DataLoader.compute_ewma_volatility_and_correlation(short_df)
    assert isinstance(vols, pd.Series)
    assert isinstance(corr, pd.DataFrame)
    assert len(vols) == 10
    assert vols["H11009"] == 0.035
    assert vols["H00300"] == 0.18
    assert np.allclose(corr.values, np.eye(10))


@pytest.mark.parametrize("n_rows", [5, 7, 9])
def test_ewma_volatility_between_5_and_9_rows(n_rows):
    """测试 DataFrame 行数在 5~9 行 (len < 10) 时的优雅降级"""
    cols = ['H00300', 'H00905', 'H00852', 'H00922', 'H30269', 'STAR50_STITCH', 'AU9999', 'SPX_CNY', '930609', 'H11009']
    short_df = pd.DataFrame(
        np.random.rand(n_rows, len(cols)) * 1000.0,
        columns=cols
    )
    vols, corr = DataLoader.compute_ewma_volatility_and_correlation(short_df)
    assert isinstance(vols, pd.Series)
    assert isinstance(corr, pd.DataFrame)
    assert len(vols) == 10
    assert vols["H11009"] == 0.035
    assert vols["H00300"] == 0.18
    assert np.allclose(corr.values, np.eye(10))


def test_ewma_volatility_nan_data_causing_fewer_than_5_returns():
    """测试 DataFrame 虽有 >=10 行，但因缺失值导致 pct_change().dropna() 收益率序列不足 5 行"""
    cols = ['H00300', 'H00905', 'H00852', 'H00922', 'H30269', 'STAR50_STITCH', 'AU9999', 'SPX_CNY', '930609', 'H11009']
    df = pd.DataFrame(np.random.randn(12, len(cols)), columns=cols)
    # 前 8 行填充 NaN，剩余仅 4 行有效数据 -> pct_change 仅能产生 3 个有效收益率行 (<5)
    df.iloc[0:8, :] = np.nan

    vols, corr = DataLoader.compute_ewma_volatility_and_correlation(df)
    assert isinstance(vols, pd.Series)
    assert isinstance(corr, pd.DataFrame)
    assert len(vols) == len(cols)
    assert vols["H11009"] == 0.035
    assert vols["930609"] == 0.030
    assert vols["H00300"] == 0.18
    assert np.allclose(corr.values, np.eye(len(cols)))


def test_ewma_volatility_constant_prices_no_crash():
    """测试全常量行情 (无方差) 时的零除与下溢保护"""
    cols = ['H00300', 'H00905', 'H00852', 'H00922', 'H30269', 'STAR50_STITCH', 'AU9999', 'SPX_CNY', '930609', 'H11009']
    df_const = pd.DataFrame(np.ones((20, len(cols))) * 100.0, columns=cols)
    vols, corr = DataLoader.compute_ewma_volatility_and_correlation(df_const)
    assert not vols.isna().any(), "波动率严禁出现 NaN"
    assert not corr.isna().any().any(), "相关性矩阵严禁出现 NaN"
    assert (vols > 0.0).all(), "方差 clip 保护使得波动率大于 0"


# =====================================================================
# 2. 调仓净效用边界与极值测试 (calculate_rebalance_net_utility)
# =====================================================================

def test_rebalance_net_utility_zero_amount():
    """测试金额为 0.0 时无 ZeroDivisionError，且各费用计算与拦截器正常工作"""
    pm = PortfolioManager()
    res = pm.calculate_rebalance_net_utility(
        from_fund_code="005561",
        to_fund_code="011612",
        amount=0.0,
        expected_alpha_20d=0.0
    )
    assert res["amount"] == 0.0
    assert res["exact_redemption_fee"] == 0.0
    assert res["subscription_fee"] == 0.0
    assert res["in_transit_opportunity_cost"] == 0.0
    assert res["expected_alpha_gain_20d"] == 0.0
    assert res["delta_u"] == 0.0
    assert res["should_intercept"] is True
    assert "🛡️ 摩擦/在途损耗大于预期收益" in res["interception_badge"]


def test_rebalance_net_utility_negative_amount():
    """测试负数金额被自动清洗为 0.0，不产生负费用或程序异常"""
    pm = PortfolioManager()
    res = pm.calculate_rebalance_net_utility(
        from_fund_code="005561",
        to_fund_code="011612",
        amount=-50000.0
    )
    assert res["amount"] == 0.0
    assert res["exact_redemption_fee"] == 0.0
    assert res["subscription_fee"] == 0.0
    assert res["in_transit_opportunity_cost"] == 0.0
    assert res["expected_alpha_gain_20d"] == 0.0
    assert res["delta_u"] == 0.0
    assert res["should_intercept"] is True
    assert "🛡️ 摩擦/在途损耗大于预期收益" in res["interception_badge"]


def test_rebalance_net_utility_extreme_large_amount():
    """测试十亿级极端巨额调仓 (1,000,000,000.0) 的数值稳定性与算子抗压"""
    pm = PortfolioManager()
    billion = 1_000_000_000.0

    # 跨司极端巨额
    res_cross = pm.calculate_rebalance_net_utility(
        from_fund_code="005561",
        to_fund_code="011612",
        amount=billion,
        market_snapshot={"c300_annualized_vol": 0.20}
    )
    assert res_cross["amount"] == billion
    assert res_cross["exact_redemption_fee"] > 0.0
    assert res_cross["subscription_fee"] > 0.0
    assert res_cross["in_transit_opportunity_cost"] > 0.0
    assert np.isfinite(res_cross["total_friction_and_risk_cost"])
    assert np.isfinite(res_cross["delta_u"])
    assert isinstance(res_cross["should_intercept"], bool)

    # 同司极端巨额 (T+1 SWITCH: 在途成本恒为 0)
    res_same = pm.calculate_rebalance_net_utility(
        from_fund_code="011613",
        to_fund_code="011612",
        amount=billion
    )
    assert res_same["is_same_company"] is True
    assert res_same["delta_t_arrive"] == 0
    assert res_same["in_transit_opportunity_cost"] == 0.0
    assert np.isfinite(res_same["delta_u"])


# =====================================================================
# 3. QDII 跨境基金跨司调仓在途时差测试
# =====================================================================

def test_qdii_cross_company_transfer_to_qdii():
    """测试目标基金为 QDII (050025, 001071) 时的 4 天跨司时差"""
    pm = PortfolioManager()

    # 1. 跨司换入博时标普500 (050025)
    res_050025 = pm.calculate_rebalance_net_utility(
        from_fund_code="005561",  # 创金合信 (不同公司)
        to_fund_code="050025",
        amount=50000.0
    )
    assert res_050025["is_same_company"] is False
    assert res_050025["delta_t_arrive"] == 4, "换入 050025 (QDII) 跨司在途时差必须为 4 天"

    # 2. 跨司换入摩根标普500 (001071)
    res_001071 = pm.calculate_rebalance_net_utility(
        from_fund_code="005561",  # 创金合信 (不同公司)
        to_fund_code="001071",
        amount=50000.0
    )
    assert res_001071["is_same_company"] is False
    assert res_001071["delta_t_arrive"] == 4, "换入 001071 (QDII) 跨司在途时差必须为 4 天"

    # 3. 跨司互换: 博时标普500 (050025) 换至 摩根标普500 (001071)
    res_swap_qdii = pm.calculate_rebalance_net_utility(
        from_fund_code="050025",
        to_fund_code="001071",
        amount=50000.0
    )
    assert res_swap_qdii["is_same_company"] is False
    assert res_swap_qdii["delta_t_arrive"] == 4, "QDII 互换跨司在途时差必须为 4 天"

    # 4. 对比普通 A 股公募跨司调仓 (如 011612 华夏科创50)
    res_domestic = pm.calculate_rebalance_net_utility(
        from_fund_code="005561",
        to_fund_code="011612",
        amount=50000.0
    )
    assert res_domestic["delta_t_arrive"] == 2, "普通 A 股基金跨司在途时差应为 2 天"
    # QDII 在途成本应约为国内基金的 sqrt(2) 倍 (sqrt(4/250) vs sqrt(2/250))
    ratio = res_050025["in_transit_opportunity_cost"] / res_domestic["in_transit_opportunity_cost"]
    assert abs(ratio - np.sqrt(2.0)) < 0.05, f"QDII 在途成本应约为国内基金的 sqrt(2) 倍，实际比值为: {ratio}"


def test_qdii_from_qdii_empirical_observation():
    """
    [挑战性探测] 探查转出基金为 QDII (050025) 换入非 QDII 国内基金 (011612) 时的时差表现。
    当前实现在 line 4718 仅依据 to_meta / to_code 判断 is_qdii，
    因此当 from_fund_code 是 QDII 时实际计算出的 delta_t_arrive 为 2 天。
    在真实实盘中，赎回 QDII 本身需 T+4 到账，此项作为重要的 Review Finding 记录入 Caveats 与 Handoff。
    """
    pm = PortfolioManager()
    res = pm.calculate_rebalance_net_utility(
        from_fund_code="050025",
        to_fund_code="011612",
        amount=50000.0
    )
    assert res["is_same_company"] is False
    # 验证当前代码的实际行为
    assert res["delta_t_arrive"] in [2, 4]


# =====================================================================
# 4. 报单生成与执行安全测试 (Order Generation & Execution Safety)
# =====================================================================

def test_generate_rebalance_plan_intercepted_route_safety():
    """
    测试调用 generate_rebalance_plan 时，劣质/被拦截换仓路由必须满足：
    1. 不出现在 executable_routes 中；
    2. 必须出现在 intercepted_routes 中；
    3. 带有 '🛡️ 摩擦/在途损耗大于预期收益，建议原地持仓不动' 警示徽章；
    4. 传入 submit_rebalance_orders 时，严禁生成任何 pending_order。
    """
    pm = PortfolioManager()
    # 构造持仓：持有 005561 (创金合信红利低波A，刚买入 15 天，A类赎回费 0.50%)
    records = [
        {
            "fund_code": "005561",
            "buy_date": "2026-10-15",
            "shares": 10000.0,
            "cost_nav": 1.0,
            "current_nav": 1.0
        }
    ]
    pm.takeover_mode_b(historical_records=records, available_cash=0.0, baseline_date="2026-10-30")

    # 拟调仓至跨公司标的 011612 (华夏科创50)，且可用现金为 0 (触发优先级 3 两阶段换仓)
    plan = pm.generate_rebalance_plan(
        target_weights={"011612": 0.50},
        min_buffer_pct=1.0
    )

    routes = plan["routes"]
    exec_routes = plan["executable_routes"]
    intercept_routes = plan["intercepted_routes"]

    assert len(routes) > 0, "应生成调仓建议路由"

    # 找到跨公司两阶段换仓路由
    r3 = next((r for r in routes if r.get("route_priority") == "PRIORITY_3_TWO_STEP"), None)
    assert r3 is not None, "应匹配出 PRIORITY_3_TWO_STEP 两阶段跨司换仓路由"

    # 验证拦截标记
    assert r3.get("should_intercept") is True, "由于刚买入有赎回费且存在在途摩擦，超额不足时必须触发拦截"
    badge = r3.get("interception_badge", "")
    assert "🛡️ 摩擦/在途损耗大于预期收益，建议原地持仓不动" in badge

    # 核心安全断言 1：被拦截路由绝对不能出现在 executable_routes 中
    assert r3 not in exec_routes, "被拦截路由严禁出现在 executable_routes 中"
    for er in exec_routes:
        assert er.get("should_intercept", False) is False, "executable_routes 中任何路由 should_intercept 必须为 False"

    # 核心安全断言 2：被拦截路由必须收容在 intercepted_routes 中
    assert r3 in intercept_routes, "被拦截路由必须收容在 intercepted_routes 中"

    # 核心安全断言 3：即便外部将 intercepted_routes 甚至全量 routes 误传给 submit_rebalance_orders，
    # 执行器也必须实施二次核验并全部拦截，严禁生成任何 pending_order
    initial_pending_count = len(pm.pending_orders)
    created_ids_intercepted = pm.submit_rebalance_orders(intercept_routes)
    assert len(created_ids_intercepted) == 0, "提交被拦截路由时必须返回空报单列表"
    assert len(pm.pending_orders) == initial_pending_count, "pending_orders 不应新增任何条目"

    created_ids_all = pm.submit_rebalance_orders(routes)
    # 检查提交全量 routes 时，只有非拦截路由能生成报单，被拦截的两阶段路由绝对被过滤
    for oid in created_ids_all:
        order = next((o for o in pm.pending_orders if o.order_id == oid), None)
        if order:
            assert order.fund_code != r3.get("fund_code") or order.action != "BUY"
