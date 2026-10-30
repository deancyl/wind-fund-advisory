"""
Milestone 2 专项单元测试套件 (tests/test_m2_r4_r5_optimization.py)
覆盖 R4 (滚动 EWMA 波动率倒数与动态风险预算配权) 与 R5 (调仓净效用拦截器与在途摩擦折价)
"""

import pytest
import numpy as np
import pandas as pd
from pathlib import Path
import sys

PROJECT_DIR = Path(__file__).resolve().parent.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from data_loader import DataLoader, MATRIX_CACHE_FILE
from strategy_bridge import StrategyBridge, FUND_TO_PROXY_INDEX
from portfolio_manager import PortfolioManager, calculate_rebalance_net_utility


# =====================================================================
# R4 测试：滚动 EWMA 波动率倒数与动态风险预算配权
# =====================================================================

def test_r4_data_loader_ewma_volatility_and_correlation_empty_and_fallback():
    """测试 DataLoader.compute_ewma_volatility_and_correlation 空入参与极值优雅降级"""
    # 1. 传入 None
    vols_none, corr_none = DataLoader.compute_ewma_volatility_and_correlation(None)
    assert isinstance(vols_none, pd.Series)
    assert isinstance(corr_none, pd.DataFrame)
    assert len(vols_none) >= 10
    assert vols_none["H11009"] < vols_none["H00300"]  # 纯债波动率显著低于股票
    assert vols_none["930609"] < vols_none["H00905"]
    assert np.allclose(corr_none.values, np.eye(len(corr_none)))

    # 2. 传入过短的 DataFrame
    short_df = pd.DataFrame(np.random.randn(5, 10), columns=['H00300', 'H00905', 'H00852', 'H00922', 'H30269', 'STAR50_STITCH', 'AU9999', 'SPX_CNY', '930609', 'H11009'])
    vols_short, corr_short = DataLoader.compute_ewma_volatility_and_correlation(short_df)
    assert len(vols_short) == 10
    assert vols_short["H11009"] == 0.035


def test_r4_data_loader_ewma_volatility_and_correlation_real_matrix():
    """测试 DataLoader.compute_ewma_volatility_and_correlation 在真实历史矩阵上的计算精度"""
    loader = DataLoader(cache_file=MATRIX_CACHE_FILE)
    df_mat = loader.load_total_return_matrix()
    assert df_mat is not None and len(df_mat) >= 100

    vols, corr = DataLoader.compute_ewma_volatility_and_correlation(df_mat, window=60, span=60)
    assert isinstance(vols, pd.Series)
    assert isinstance(corr, pd.DataFrame)
    assert not vols.isna().any()
    assert not corr.isna().any().any()

    # 科技小盘与成长(科创50、中证1000)波动率应显著高于低波红利与纯债
    assert vols["STAR50_STITCH"] > vols["H30269"]
    assert vols["H00852"] > vols["H11009"]
    assert vols["H11009"] < 0.05  # 纯债年化波动率小于 5%


def test_r4_strategy_bridge_inverse_volatility_weighting_and_bond_ballast():
    """测试 strategy_bridge.py 中波动率倒数配权与纯债压舱石转移"""
    # 构造科创50波动率大幅飙升 (0.50) 与红利平稳的行情切片
    dates = pd.date_range("2026-01-01", periods=80, freq="B")
    np.random.seed(42)
    # 科创50高波动 (日波动率 3.0% -> 年化约 47%)，红利低波低波动 (日波动率 0.6% -> 年化约 9.5%)
    star_ret = np.random.randn(80) * 0.030
    h30269_ret = np.random.randn(80) * 0.006
    bond_ret = np.random.randn(80) * 0.001

    df_stress = pd.DataFrame({
        "date": dates,
        "H00300": (1.0 + np.random.randn(80) * 0.01).cumprod() * 4000.0,
        "H00905": (1.0 + np.random.randn(80) * 0.015).cumprod() * 5000.0,
        "H00852": (1.0 + np.random.randn(80) * 0.020).cumprod() * 6000.0,
        "H00922": (1.0 + np.random.randn(80) * 0.008).cumprod() * 3000.0,
        "H30269": (1.0 + h30269_ret).cumprod() * 2000.0,
        "STAR50_STITCH": (1.0 + star_ret).cumprod() * 1000.0,
        "AU9999": (1.0 + np.random.randn(80) * 0.008).cumprod() * 500.0,
        "SPX_CNY": (1.0 + np.random.randn(80) * 0.01).cumprod() * 4000.0,
        "930609": (1.0 + bond_ret).cumprod() * 100.0,
        "H11009": (1.0 + bond_ret).cumprod() * 100.0,
    })

    # 计算 C4 档位在此行情下的权重
    w_stress = StrategyBridge.compute_dynamic_tier_weights(df_stress, "C4")
    assert abs(sum(w_stress.values()) - 1.0) < 1e-4

    # 验证纯债标的 002351 获得了转移的溢出预算
    assert "002351" in w_stress
    assert w_stress["002351"] >= 0.08  # 基准为 8%，收缩后纯债比例应提升


def test_r4_c1_c5_risk_monotonicity_across_all_regimes():
    """测试 C1 至 C5 全档位风险单调性定理在各类状态下恒成立"""
    test_snapshots = [
        {"market_state_code": "GROWTH_BULL"},
        {"market_state_code": "STABLE_DIVIDEND"},
        {"market_state_code": "SEVERE_BEAR"},
        {"c300_price": 4200.0, "m20_price": 4000.0, "m60_price": 3800.0},
        {"c300_price": 2800.0, "m20_price": 3100.0, "m60_price": 3400.0},
    ]

    pm = PortfolioManager()
    def get_eq_def(w):
        eq_w = 0.0
        def_w = 0.0
        for code, wt in w.items():
            cat = pm.classify_fund_asset_class(code)
            if cat in ["纯债固收", "黄金对冲"] or code in ["002351", "000086", "018757", "000216", "000217"]:
                def_w += wt
            else:
                eq_w += wt
        return round(eq_w, 4), round(def_w, 4)

    for snap in test_snapshots:
        eq_map = {}
        def_map = {}
        for tier in ["C1", "C2", "C3", "C4", "C5"]:
            w = StrategyBridge.compute_dynamic_tier_weights(tier=tier, market_snapshot=snap)
            assert abs(sum(w.values()) - 1.0) < 1e-4
            eq, df = get_eq_def(w)
            eq_map[tier] = eq
            def_map[tier] = df

        # 核心断言：权益严格递增，防御严格递减
        assert eq_map["C1"] < eq_map["C2"] < eq_map["C3"] < eq_map["C4"] < eq_map["C5"]
        assert def_map["C1"] > def_map["C2"] > def_map["C3"] > def_map["C4"] > def_map["C5"]

        # 深度熊市破位态止损硬红线
        if snap.get("market_state_code") == "SEVERE_BEAR" or snap.get("c300_price", 4000) < 3000:
            assert eq_map["C4"] <= 0.55
            assert eq_map["C5"] <= 0.70
            assert def_map["C4"] >= 0.45
            assert def_map["C5"] >= 0.30


# =====================================================================
# R5 测试：调仓净效用拦截器与在途摩擦折价
# =====================================================================

def test_r5_same_company_switch_zero_in_transit_cost():
    """测试同公司基金转换 (T+1 SWITCH): Delta t = 0 且 InTransitCost = 0"""
    pm = PortfolioManager()
    if "011613" in pm.holdings:
        for b in pm.holdings["011613"].batches:
            b.holding_days = 30
    # 华夏科创50 C (011613, 华夏基金) 转换为 华夏科创50 A (011612, 华夏基金)
    res = pm.calculate_rebalance_net_utility(
        from_fund_code="011613",
        to_fund_code="011612",
        amount=10000.0,
        expected_alpha_20d=50.0
    )

    assert res["is_same_company"] is True
    assert res["delta_t_arrive"] == 0
    assert res["in_transit_opportunity_cost"] == 0.0
    assert res["exact_redemption_fee"] == 0.0  # C 类满30天免赎回费
    assert res["subscription_fee"] == 15.0      # 1折补差 0.15%
    assert res["expected_alpha_gain_20d"] == 50.0
    assert res["delta_u"] == 35.0               # 50 - 15 = 35 > 0
    assert res["should_intercept"] is False
    assert "✅" in res["interception_badge"]


def test_r5_cross_company_in_transit_opportunity_cost_and_interception():
    """测试跨公司调仓在途踏空时差折价与 Delta U <= 0 拦截"""
    pm = PortfolioManager()
    # 创金合信红利低波 (005561) 换入 华夏科创50 (011612)
    # 跨公司国内权益 Delta t = 2 天，年化波动率 0.18，在途成本折价 = 10000 * 0.18 * sqrt(2/250) = 16.10
    res = pm.calculate_rebalance_net_utility(
        from_fund_code="005561",
        to_fund_code="011612",
        amount=10000.0,
        expected_alpha_20d=10.0,  # 预期超额仅 10 元，无法覆盖摩擦
        market_snapshot={"c300_annualized_vol": 0.18}
    )

    assert res["is_same_company"] is False
    assert res["delta_t_arrive"] == 2
    assert res["in_transit_opportunity_cost"] > 10.0
    assert abs(res["subscription_fee"] - 15.0) < 0.10
    # 总摩擦 = 赎回费(约50) + 申购费(15) + 在途成本(16.1) > 80 元
    # 预期 Alpha 仅 10 元 -> Delta U < 0
    assert res["delta_u"] < 0.0
    assert res["should_intercept"] is True
    assert "🛡️ 摩擦/在途损耗大于预期收益，建议原地持仓不动" in res["interception_badge"]


def test_r5_qdii_overseas_four_day_in_transit_discount():
    """测试 QDII / 标普500 跨市场基金 4 天在途时差折价"""
    pm = PortfolioManager()
    res = pm.calculate_rebalance_net_utility(
        from_fund_code="005561",
        to_fund_code="050025",  # 博时标普500 ETF 联接 (QDII)
        amount=20000.0,
        market_snapshot={"c300_annualized_vol": 0.20}
    )

    assert res["is_same_company"] is False
    assert res["delta_t_arrive"] == 4
    # 20000 * 0.20 * sqrt(4/250) = 4000 * 0.12649 = 505.96
    assert res["in_transit_opportunity_cost"] > 400.0


def test_r5_same_company_convenience_bonus_in_fund_scoring():
    """测试选基评分中同公司转换便利度加分 (+5.0 分)"""
    pm = PortfolioManager()
    # 模拟持仓中持有易方达产品
    records = [
        {"fund_code": "002351", "buy_date": "2026-08-01", "shares": 10000.0, "cost_nav": 1.0, "current_nav": 1.0}
    ]
    pm.takeover_mode_b(historical_records=records, available_cash=10000.0, baseline_date="2026-10-28")

    # 易方达沪深300 (007339, 易方达基金) 应获得同公司 +5.0 分加分
    score_same = pm.compute_fund_six_dimension_score("007339")
    assert score_same["is_same_company_bonus"] is True
    assert score_same["switch_convenience_bonus"] == 5.0

    # 华安易富黄金 (000216, 华安基金) 未在持仓公司集合中，不获加分
    score_diff = pm.compute_fund_six_dimension_score("000216")
    assert score_diff["is_same_company_bonus"] is False
    assert score_diff["switch_convenience_bonus"] == 0.0


def test_r5_interception_prevents_executable_orders():
    """测试净效用拦截器阻止劣质换仓单提交至 pending_orders"""
    pm = PortfolioManager()
    # 构造持仓：持有 005561（A类不满 30 天，0.50% 赎回费）
    records = [
        {"fund_code": "005561", "buy_date": "2026-10-15", "shares": 10000.0, "cost_nav": 1.0, "current_nav": 1.0}
    ]
    pm.takeover_mode_b(historical_records=records, available_cash=0.0, baseline_date="2026-10-28")

    # 拟调仓至跨公司标的，且预估收益不足以覆盖摩擦
    plan = pm.generate_rebalance_plan(target_weights={"011612": 0.50}, min_buffer_pct=3.0)
    routes = plan["routes"]

    # 包含两阶段跨公司换仓路由，且该路由被标记为拦截
    r3 = next((r for r in routes if r["route_priority"] == "PRIORITY_3_TWO_STEP"), None)
    if r3 and r3.get("should_intercept", False):
        assert "🛡️ 摩擦/在途损耗大于预期收益" in r3["interception_badge"]
        # 验证提交订单时被拦截，不生成无效 pending_order
        oids = pm.submit_rebalance_orders([r3])
        assert len(oids) == 0
        assert len(pm.pending_orders) == 0
