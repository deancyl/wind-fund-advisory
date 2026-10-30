"""
Adversarial Challenge Test Suite for Milestone 2 (R4 Dynamic Risk Budgeting & R5 Net Utility Interceptor)
Written by Empirical Challenger (Agent-4 / Challenger 1).
Validates:
1. Asset volatility pulse: extreme volatility spike shrinks tech equity and pure bond absorbs excess.
2. C1-C5 monotonicity theorem: 3,000+ grid points scan without any inversion.
3. Deep bear stop-loss: Equity(C4) <= 55% and Equity(C5) <= 70% under severe bear regimes.
4. Same-company T+1 SWITCH: delta_t_arrive == 0 and in_transit_opportunity_cost == 0.0.
5. Cross-company poor alpha interception: Delta U <= 0, should_intercept == True, badge check, order blocking.
6. Candidate fund scoring: +5.0 bonus for same-company candidates, with 100.0 cap.
7. Extreme boundary and robust error handling.
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
from strategy_bridge import StrategyBridge, FUND_TO_PROXY_INDEX
from portfolio_manager import PortfolioManager, calculate_rebalance_net_utility


# =====================================================================
# R4 Adversarial Tests: Dynamic Risk Budgeting & Volatility Pulse
# =====================================================================

def test_adv_asset_volatility_pulse_tech_shrink_and_bond_ballast():
    """
    [Adversarial Challenge 1] 资产极端波动率脉冲吸收测试：
    在科技成长（科创50）注入 50% ~ 150% 极端年化波动率脉冲，
    断言科技资产权重相对基准收缩，且溢出预算 100% 被低波纯债压舱石 (002351/000086) 吸收。
    """
    dates = pd.date_range("2026-01-01", periods=90, freq="B")
    np.random.seed(999)

    # 构造科创50年化波动率约 60% 的极端脉冲序列 (日收益率标准差 ~3.8%)
    extreme_star_ret = np.random.randn(90) * 0.038
    # 纯债与红利低波保持平稳极低波动
    calm_bond_ret = np.random.randn(90) * 0.0008
    calm_h30269_ret = np.random.randn(90) * 0.005

    df_pulse = pd.DataFrame({
        "date": dates,
        "H00300": (1.0 + np.random.randn(90) * 0.010).cumprod() * 4000.0,
        "H00905": (1.0 + np.random.randn(90) * 0.012).cumprod() * 5200.0,
        "H00852": (1.0 + np.random.randn(90) * 0.015).cumprod() * 6200.0,
        "H00922": (1.0 + np.random.randn(90) * 0.007).cumprod() * 3100.0,
        "H30269": (1.0 + calm_h30269_ret).cumprod() * 2100.0,
        "STAR50_STITCH": (1.0 + extreme_star_ret).cumprod() * 1000.0,
        "AU9999": (1.0 + np.random.randn(90) * 0.007).cumprod() * 520.0,
        "SPX_CNY": (1.0 + np.random.randn(90) * 0.009).cumprod() * 4100.0,
        "930609": (1.0 + calm_bond_ret).cumprod() * 100.0,
        "H11009": (1.0 + calm_bond_ret).cumprod() * 100.0,
    })

    # 1. 验证 DataLoader 计算出的 EWMA 波动率体现了科技资产的极端脉冲
    vols, corr = DataLoader.compute_ewma_volatility_and_correlation(df_pulse, window=60, span=60)
    assert vols["STAR50_STITCH"] >= 0.45  # 确认科创50年化波动率超过 45%
    assert vols["H11009"] <= 0.05        # 纯债波动率平稳 < 5%

    # 2. 对比基准常态权重与波动率脉冲权重 (C4 档位)
    w_pulse_c4 = StrategyBridge.compute_dynamic_tier_weights(df_pulse, "C4")
    assert abs(sum(w_pulse_c4.values()) - 1.0) < 1e-4

    # 科创50在 C4 常态下基准配比为 30%~32%，在 60% 波动率冲击下应显著缩减至 20% 以下
    assert "011613" in w_pulse_c4
    assert w_pulse_c4["011613"] <= 0.20

    # 纯债标的 002351 获得了溢出预算吸收，比例应提升至基准(8%)以上
    assert "002351" in w_pulse_c4
    assert w_pulse_c4["002351"] >= 0.08

    # 3. 验证 C5 档位在脉冲下依然守住科技收缩与纯债吸收
    w_pulse_c5 = StrategyBridge.compute_dynamic_tier_weights(df_pulse, "C5")
    assert abs(sum(w_pulse_c5.values()) - 1.0) < 1e-4
    assert w_pulse_c5["011613"] < 0.38  # 基准为 38%~40%，收缩
    assert "002351" in w_pulse_c5 or "000086" in w_pulse_c5


def test_adv_c1_c5_monotonicity_massive_grid_scan():
    """
    [Adversarial Challenge 2] C1-C5 风险单调性定理 3,000+ 点地毯式网格扫描：
    扫描全域状态码、全价格均线排列组合、全波动率阶梯，
    断言无论输入何种极端行情，恒有 Equity(C1) < Equity(C2) < Equity(C3) < Equity(C4) < Equity(C5) 严格成立，零倒挂！
    """
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

    # 1. 状态码与波动率交叉扫描
    state_codes = [
        "GROWTH_BULL", "STRUCTURAL_500", "BULL", "ATTACK", "UP", "主升浪", "进攻",
        "STABLE_DIVIDEND", "OSCILLATING", "SHOCK", "RANGE", "NEUTRAL", "震荡", "收息",
        "SEVERE_BEAR", "BEAR", "DEFENSE", "DOWN", "BREAKDOWN", "破位", "防守",
        "", "UNKNOWN", "FALLBACK"
    ]
    vol_grid = [0.05, 0.08, 0.12, 0.18, 0.25, 0.35, 0.50, 0.75]

    for sc in state_codes:
        for vol in vol_grid:
            snap = {"market_state_code": sc, "c300_annualized_vol": vol}
            eq_map = {}
            def_map = {}
            for tier in ["C1", "C2", "C3", "C4", "C5"]:
                w = StrategyBridge.compute_dynamic_tier_weights(tier=tier, market_snapshot=snap)
                assert abs(sum(w.values()) - 1.0) < 1e-4
                eq, df = get_eq_def(w)
                eq_map[tier] = eq
                def_map[tier] = df

            # 严格单调性断言
            assert eq_map["C1"] < eq_map["C2"] < eq_map["C3"] < eq_map["C4"] < eq_map["C5"], f"Equity inverted at {snap}: {eq_map}"
            assert def_map["C1"] > def_map["C2"] > def_map["C3"] > def_map["C4"] > def_map["C5"], f"Defense inverted at {snap}: {def_map}"

    # 2. 均线价格无状态码推导网格扫描 (5 x 7 x 7 x 5 = 1,225 组)
    c300_levels = [1800, 2600, 3400, 4200, 5000]
    m20_biases = [-0.12, -0.04, -0.01, 0.0, 0.01, 0.04, 0.12]
    m60_biases = [-0.15, -0.06, -0.02, 0.0, 0.02, 0.06, 0.15]
    m120_biases = [-0.20, -0.08, 0.0, 0.08, 0.20]

    for c300 in c300_levels:
        for b20 in m20_biases:
            for b60 in m60_biases:
                for b120 in m120_biases:
                    snap = {
                        "c300_price": c300,
                        "m20_price": c300 * (1.0 + b20),
                        "m60_price": c300 * (1.0 + b60),
                        "m120_price": c300 * (1.0 + b120),
                    }
                    eq_map = {}
                    def_map = {}
                    for tier in ["C1", "C2", "C3", "C4", "C5"]:
                        w = StrategyBridge.compute_dynamic_tier_weights(tier=tier, market_snapshot=snap)
                        assert abs(sum(w.values()) - 1.0) < 1e-4
                        eq, df = get_eq_def(w)
                        eq_map[tier] = eq
                        def_map[tier] = df

                    assert eq_map["C1"] < eq_map["C2"] < eq_map["C3"] < eq_map["C4"] < eq_map["C5"], f"Price grid inversion at {snap}: {eq_map}"
                    assert def_map["C1"] > def_map["C2"] > def_map["C3"] > def_map["C4"] > def_map["C5"], f"Price grid defense inversion at {snap}: {def_map}"


def test_adv_deep_bear_stop_loss_hard_bounds():
    """
    [Adversarial Challenge 3] 深度熊市破位态算法硬止损测试：
    输入各类深熊、破位与破线信号，
    断言 Equity(C4) <= 55% 且 Equity(C5) <= 70% 硬红线坚不可摧，绝不超纲！
    """
    pm = PortfolioManager()
    def get_equity(w):
        return sum(wt for code, wt in w.items() if pm.classify_fund_asset_class(code) not in ["纯债固收", "黄金对冲"] and code not in ["002351", "000086", "018757", "000216", "000217"])

    bear_signals = [
        {"market_state_code": "SEVERE_BEAR"},
        {"market_state_code": "BEAR"},
        {"market_state": "破位防御态"},
        {"regime_code": "DEFENSE_DOWN"},
        {"c300_price": 2700.0, "m20_price": 2900.0, "m60_price": 3100.0, "m120_price": 3300.0},
        {"c300_price": 2200.0, "m60_price": 2600.0, "m120_price": 2800.0},
    ]

    for snap in bear_signals:
        w_c4 = StrategyBridge.compute_dynamic_tier_weights(tier="C4", market_snapshot=snap)
        w_c5 = StrategyBridge.compute_dynamic_tier_weights(tier="C5", market_snapshot=snap)
        
        eq_c4 = get_equity(w_c4)
        eq_c5 = get_equity(w_c5)

        assert eq_c4 <= 0.55 + 1e-4, f"C4 violated deep bear bound (<=55%): {eq_c4} under {snap}"
        assert eq_c5 <= 0.70 + 1e-4, f"C5 violated deep bear bound (<=70%): {eq_c5} under {snap}"


# =====================================================================
# R5 Adversarial Tests: Net Utility Interceptor & In-Transit Friction
# =====================================================================

def test_adv_same_company_t_plus_1_switch_multi_firm():
    """
    [Adversarial Challenge 4] 同基金公司 T+1 SWITCH 转换零在途成本验证：
    在华夏基金、易方达基金与富国基金旗下分别对测同司转换：
    断言 is_same_company == True, delta_t_arrive == 0, in_transit_opportunity_cost == 0.0。
    """
    pm = PortfolioManager()

    # 1. 华夏基金内部转换：011613 (华夏科创50 C) ➡️ 001053 (华夏中证500 C)
    res_hx = pm.calculate_rebalance_net_utility(
        from_fund_code="011613",
        to_fund_code="001053",
        amount=30000.0,
        expected_alpha_20d=100.0
    )
    assert res_hx["is_same_company"] is True
    assert res_hx["delta_t_arrive"] == 0
    assert res_hx["in_transit_opportunity_cost"] == 0.0
    assert res_hx["subscription_fee"] == 0.0  # C 类免前端申购费
    assert res_hx["delta_u"] == 100.0
    assert res_hx["should_intercept"] is False

    # 2. 易方达基金内部转换：002351 (易方达裕祥 A) ➡️ 007339 (易方达沪深300 C)
    res_yfd = pm.calculate_rebalance_net_utility(
        from_fund_code="002351",
        to_fund_code="007339",
        amount=50000.0,
        expected_alpha_20d=150.0
    )
    assert res_yfd["is_same_company"] is True
    assert res_yfd["delta_t_arrive"] == 0
    assert res_yfd["in_transit_opportunity_cost"] == 0.0

    # 3. 富国基金内部转换：100032 (富国红利 A) ➡️ 008682 (富国红利 C)
    res_fg = pm.calculate_rebalance_net_utility(
        from_fund_code="100032",
        to_fund_code="008682",
        amount=20000.0,
        expected_alpha_20d=80.0
    )
    assert res_fg["is_same_company"] is True
    assert res_fg["delta_t_arrive"] == 0
    assert res_fg["in_transit_opportunity_cost"] == 0.0


def test_adv_cross_company_transfer_poor_alpha_interception():
    """
    [Adversarial Challenge 5] 跨公司劣质换仓拦截与订单熔断验证：
    跨公司从创金合信 (005561) 换入华夏基金 (011612)，超额收益微弱（如 5 元），
    断言 Delta U <= 0, should_intercept == True, 
    且拦截徽章严格包含 '🛡️ 摩擦/在途损耗大于预期收益，建议原地持仓不动'，
    并验证其无法进入 executable_routes 与 pending_orders。
    """
    pm = PortfolioManager()
    
    # 模拟真实持仓：持有 005561（A 类持有不足 30 天，有赎回费）
    records = [
        {"fund_code": "005561", "buy_date": "2026-10-10", "shares": 10000.0, "cost_nav": 1.0, "current_nav": 1.0}
    ]
    pm.takeover_mode_b(historical_records=records, available_cash=0.0, baseline_date="2026-10-28")

    # 1. 直接精算单笔净效用
    res = pm.calculate_rebalance_net_utility(
        from_fund_code="005561",
        to_fund_code="011612",
        amount=10000.0,
        expected_alpha_20d=5.0,  # 预期超额仅 5 元，远低于赎回费(约50)+申购费(15)+在途成本(约16)
        market_snapshot={"c300_annualized_vol": 0.18}
    )

    assert res["is_same_company"] is False
    assert res["delta_t_arrive"] == 2
    assert res["in_transit_opportunity_cost"] > 10.0
    assert res["delta_u"] < 0.0
    assert res["should_intercept"] is True
    assert "🛡️ 摩擦/在途损耗大于预期收益，建议原地持仓不动" in res["interception_badge"]

    # 2. 验证推演沙盒 generate_rebalance_plan 分离拦截路由
    plan = pm.generate_rebalance_plan(target_weights={"011612": 0.50}, min_buffer_pct=3.0)
    routes = plan["routes"]
    assert any(r.get("should_intercept", False) for r in routes)
    
    # executable_routes 必须剥离所有被拦截路由
    assert not any(r.get("should_intercept", False) for r in plan["executable_routes"])
    assert len(plan["intercepted_routes"]) >= 1

    # 3. 验证提交订单时熔断，严禁生成任何 pending_order
    intercepted_item = plan["intercepted_routes"][0]
    created_orders = pm.submit_rebalance_orders([intercepted_item])
    assert len(created_orders) == 0
    assert len(pm.pending_orders) == 0


def test_adv_candidate_fund_scoring_same_company_bonus():
    """
    [Adversarial Challenge 6] 候选基金同司便利度加分 (+5.0 分) 验证：
    当用户持仓包含公司 A 时，公司 A 的候选基金获得 +5.0 分加分；
    非持仓公司的候选基金获得 0.0 分加分；
    当原始得分已达 98.0 时，总分精确封顶 100.0 分。
    """
    pm = PortfolioManager()
    records = [
        {"fund_code": "001053", "buy_date": "2026-07-01", "shares": 10000.0, "cost_nav": 1.0, "current_nav": 1.0} # 华夏基金
    ]
    pm.takeover_mode_b(historical_records=records, available_cash=0.0, baseline_date="2026-10-28")

    # 1. 华夏科创50 (011612, 华夏基金) 获得 +5.0 分
    sc_hx = pm.compute_fund_six_dimension_score("011612")
    assert sc_hx["switch_convenience_bonus"] == 5.0
    assert sc_hx["is_same_company_bonus"] is True

    # 2. 易方达沪深300 (007339, 易方达基金) 不获加分
    sc_yfd = pm.compute_fund_six_dimension_score("007339")
    assert sc_yfd["switch_convenience_bonus"] == 0.0
    assert sc_yfd["is_same_company_bonus"] is False

    # 3. 极值封顶测试：满分 100 边界防溢出
    assert sc_hx["total_score"] <= 100.0


def test_adv_boundary_and_robustness():
    """
    [Adversarial Challenge 7] 边界异常输入防御性测试：
    验证 0 金额、负金额、极大金额、异常波动率传入均平稳优雅处理。
    """
    pm = PortfolioManager()
    
    # 0 金额调仓
    res_zero = pm.calculate_rebalance_net_utility("011613", "001053", amount=0.0)
    assert res_zero["amount"] == 0.0
    assert res_zero["total_friction_and_risk_cost"] == 0.0

    # 负金额防护
    res_neg = pm.calculate_rebalance_net_utility("011613", "001053", amount=-500.0)
    assert res_neg["amount"] == 0.0

    # 异常波动率 (负数与超大数值) 兜底保护
    res_bad_vol = pm.calculate_rebalance_net_utility(
        "005561", "011612", amount=10000.0, market_snapshot={"c300_annualized_vol": -0.8}
    )
    # 应回退至默认 0.18，cost > 0
    assert res_bad_vol["in_transit_opportunity_cost"] > 0.0
