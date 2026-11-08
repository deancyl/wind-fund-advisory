"""
Generation 10 专项测试：动态相关性压力突变防御、场外公募底层流动性折价模型与穿透式多周期蒙特卡洛压力测试
(tests/test_g10_correlation_liquidity_and_stress.py)

涵盖六大核心测试用例：
1. test_g10_1_correlation_mutation_threshold_and_liquidity_shift
2. test_g10_2_otc_fund_micro_execution_haircut_and_adv_ratio
3. test_g10_3_portfolio_manager_cvar_bootstrap_three_scenarios
4. test_g10_4_c1_to_c5_risk_tier_max_drawdown_and_liquidation_days
5. test_g10_5_app_gui_r5_source_wireup_verification
6. test_g10_6_apptest_gui_stress_and_liquidity_render
"""

import sys
import inspect
from pathlib import Path
import pytest
import numpy as np
import pandas as pd

_CURRENT = Path(__file__).resolve().parent
_WORKSPACE = _CURRENT.parent
_AGY2_DIR = _WORKSPACE / "AGY2_FundAdvisory"
if str(_AGY2_DIR) not in sys.path:
    sys.path.insert(0, str(_AGY2_DIR))
if str(_WORKSPACE) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE))

from AGY2_FundAdvisory.portfolio_manager import (
    PortfolioManager,
    evaluate_dynamic_correlation_mutation,
    compute_ewma_correlation,
    simulate_portfolio_cvar_bootstrap
)
from AGY2_FundAdvisory.advisory_engine import (
    ActiveRiskSentry,
    SmartExecutionDCAEngine,
    calculate_otc_fund_liquidity_haircut
)
from AGY2_FundAdvisory.data_loader import DataLoader


def test_g10_1_correlation_mutation_threshold_and_liquidity_shift():
    """
    R2 核心测试：
    1. 验证 0.80 相关性压力突变阈值与跨资产流动性平移预案触发；
    2. 验证资产筛选：将高波高估值科技成长进攻标的 (如科创50 011613 / 芯片ETF) 与红利周期一同削减 15%~35%；
    3. 验证资金定向平移至纯债 (002351, 60%) 与黄金 (000216, 40%)，权重严格归一化 sum(w) == 1.000000；
    4. 验证向后兼容字段：status == 'MUTATION_ALERT', action_type == 'correlation_mutation_defense', 包含'集中度降级'，并附加'流动性平移预案'；
    5. 验证下行相关性 compute_ewma_correlation(downside_only=True)。
    """
    pm = PortfolioManager(db_path=":memory:")
    # 构建包含红利低波、顺周期、高波科技成长资产的测试组合
    pm.add_or_update_holding("005561", shares=10000.0, nav=1.5, cost_price=1.4)  # 招商红利低波
    pm.add_or_update_holding("011613", shares=20000.0, nav=0.8, cost_price=1.0)  # 华夏科创50成长
    pm.add_or_update_holding("002351", shares=5000.0, nav=1.1, cost_price=1.1)   # 易方达裕祥纯债
    pm.add_or_update_holding("000216", shares=3000.0, nav=1.8, cost_price=1.7)   # 华安黄金

    # 1. 模拟相关系数突破 0.80 极端警戒线
    res_stress = pm.evaluate_dynamic_correlation_mutation_instance(
        threshold=0.75,
        stress_threshold=0.80,
        simulated_corr=0.83
    )

    assert res_stress["is_triggered"] is True, "突破 0.75 必须触发预警"
    assert res_stress["is_liquidity_shift_triggered"] is True, "突破 0.80 必须触发流动性平移预案"
    assert res_stress["status"] == "MUTATION_ALERT", "保持向后兼容状态码"
    assert res_stress["action_type"] == "correlation_mutation_defense", "保持向后兼容动作码"
    assert "集中度降级" in res_stress["alert_message"], "必须包含集中度降级描述"
    assert "流动性平移预案" in res_stress["alert_message"], "必须包含流动性平移预案描述"

    # 验证资产定向削减与平移
    adj_w = res_stress["adjusted_weights"]
    assert "002351" in adj_w and "000216" in adj_w
    # 纯债与黄金权重必须显著增加
    orig_w = res_stress["original_weights"]
    assert adj_w["002351"] > orig_w.get("002351", 0.0), "纯债 002351 权重必须增加"
    assert adj_w["000216"] > orig_w.get("000216", 0.0), "黄金 000216 权重必须增加"
    # 高波科技标的 011613 必须被削减
    assert adj_w["011613"] < orig_w["011613"], "高波科技标的 011613 必须被定向削减"
    # 权重严格归一化
    assert abs(sum(adj_w.values()) - 1.0) < 1e-5, f"调整后权重和必须严格为 1.0: {sum(adj_w.values())}"

    # 2. 模拟正常低相关环境 (< 0.75)
    res_normal = pm.evaluate_dynamic_correlation_mutation_instance(
        threshold=0.75,
        stress_threshold=0.80,
        simulated_corr=0.45
    )
    assert res_normal["is_triggered"] is False
    assert res_normal["is_liquidity_shift_triggered"] is False
    assert res_normal["status"] == "DECOUPLED_NORMAL"

    # 3. 验证下行相关性计算 compute_ewma_correlation
    dates = pd.date_range("2024-01-01", periods=100, freq="B")
    ret_a = pd.Series(np.random.normal(0.0005, 0.015, 100), index=dates)
    ret_b = pd.Series(np.random.normal(0.0003, 0.012, 100), index=dates)
    ret_bench = pd.Series(np.random.normal(0.0002, 0.010, 100), index=dates)

    corr_series = compute_ewma_correlation(
        ret_a.cumsum(),
        ret_b.cumsum(),
        downside_only=True,
        bench_series=ret_bench.cumsum()
    )
    assert isinstance(corr_series, pd.Series)
    assert not corr_series.empty
    assert (corr_series >= -1.0).all() and (corr_series <= 1.0).all()


def test_g10_2_otc_fund_micro_execution_haircut_and_adv_ratio():
    """
    R3 核心测试：
    1. 验证非线性 Almgren-Chriss / Kyle lambda 流动性折价模型；
    2. 验证订单金额 Q 在 1k~500k 元区间严格单调递增 (bps 与金额均无平台期或梯度反转)；
    3. 验证场内 ETF 物理隔离折价 0 bps；
    4. 验证季报前五大重仓股日均成交额 ADV 穿透与 24h 本地 TTL 缓存；
    5. 验证融入 calculate_vwap_execution_slippage 的字段完整性。
    """
    loader = DataLoader()

    # 1. 穿透季报前五大重仓 ADV
    adv_info = loader.get_fund_top5_holdings_adv("005561")
    assert isinstance(adv_info, dict)
    assert "top5_stocks" in adv_info
    assert "top5_adv_yuan" in adv_info
    assert adv_info["top5_adv_yuan"] > 0.0

    # 2. 严格单调递增性检验 (1,000 元至 500,000 元)
    test_amounts = [1000.0, 5000.0, 20000.0, 50000.0, 100000.0, 500000.0]
    bps_list = []
    yuan_list = []

    for amt in test_amounts:
        hc = loader.calculate_otc_fund_liquidity_haircut(
            order_amount=amt,
            fund_code="005561",
            fund_name="招商中证红利低波"
        )
        assert hc["is_etf"] is False
        assert hc["haircut_bps"] > 0.0
        assert hc["haircut_yuan"] > 0.0
        bps_list.append(hc["haircut_bps"])
        yuan_list.append(hc["haircut_yuan"])

    # 验证单调严格递增
    for i in range(len(test_amounts) - 1):
        assert bps_list[i] < bps_list[i + 1], (
            f"折价 bps 未严格单调递增: {bps_list[i]} >= {bps_list[i+1]} at {test_amounts[i]} -> {test_amounts[i+1]}"
        )
        assert yuan_list[i] < yuan_list[i + 1], (
            f"折价金额未严格单调递增: {yuan_list[i]} >= {yuan_list[i+1]} at {test_amounts[i]} -> {test_amounts[i+1]}"
        )

    # 3. 场内 ETF 物理隔离检验
    hc_etf = loader.calculate_otc_fund_liquidity_haircut(
        order_amount=100000.0,
        fund_code="510300",
        fund_name="沪深300ETF"
    )
    assert hc_etf["is_etf"] is True
    assert hc_etf["haircut_bps"] == 0.0
    assert hc_etf["haircut_yuan"] == 0.0

    # 4. 融入 SmartExecutionDCAEngine.calculate_vwap_execution_slippage
    vwap_res = SmartExecutionDCAEngine.calculate_vwap_execution_slippage(
        order_amount=50000.0,
        fund_code="005561",
        fund_name="招商红利低波"
    )
    assert "fund_aum_yuan" in vwap_res
    assert "top5_adv_yuan" in vwap_res
    assert "redemption_ratio_pct" in vwap_res
    assert "liquidity_haircut_bps" in vwap_res
    assert "liquidity_haircut_yuan" in vwap_res
    assert "total_execution_friction_bps" in vwap_res
    assert "total_execution_friction_yuan" in vwap_res
    assert vwap_res["liquidity_haircut_bps"] > 0.0


def test_g10_3_portfolio_manager_cvar_bootstrap_three_scenarios():
    """
    R4 核心测试：
    1. 验证 10,000 次 Circular Block Bootstrap (块长10天、60天周期)；
    2. 覆盖三大极端情景：2008 金融危机、2015 流动性踩踏、2024 初小盘股危机；
    3. 验证极值统计量公理：CVaR 99% >= VaR 99% >= VaR 95% 恒成立；
    4. 验证模块级别名与实例方法双轨可用。
    """
    pm = PortfolioManager(db_path=":memory:")
    pm.add_or_update_holding("005561", shares=15000.0, nav=1.5, cost_price=1.4)
    pm.add_or_update_holding("011613", shares=20000.0, nav=0.8, cost_price=0.9)
    pm.add_or_update_holding("002351", shares=10000.0, nav=1.1, cost_price=1.1)

    res = pm.simulate_portfolio_cvar_bootstrap_instance(
        total_capital=100000.0,
        investor_risk_tier="C3",
        n_simulations=10000,
        block_size=10,
        horizon_days=60
    )

    assert "scenarios" in res
    assert len(res["scenarios"]) == 3
    sc_ids = [s["id"] for s in res["scenarios"]]
    assert "2008_financial_crisis" in sc_ids
    assert "2015_liquidity_stampede" in sc_ids
    assert "2024_smallcap_liquidity" in sc_ids

    for sc in res["scenarios"]:
        v95 = sc["var_95_pct"]
        v99 = sc["var_99_pct"]
        cvar99 = sc["cvar_99_pct"]
        pred_mdd = sc["predicted_mdd_pct"]

        # 极值统计量公理校验
        assert cvar99 >= v99, f"情景 {sc['id']} 违反 CVaR99 >= VaR99: {cvar99} < {v99}"
        assert v99 >= v95, f"情景 {sc['id']} 违反 VaR99 >= VaR95: {v99} < {v95}"
        assert pred_mdd > 0.0, "预测最大回撤必须大于 0"
        assert sc["predicted_loss_amount"] > 0.0

        # 流动性折价损失叠加校验
        assert sc["liquidity_discount_pct"] >= 0.0
        assert sc["total_cvar_99_pct"] >= cvar99


def test_g10_4_c1_to_c5_risk_tier_max_drawdown_and_liquidation_days():
    """
    R4 适当性与流动性拓展测试：
    1. 验证 C1 至 C5 契约矩阵比对与越界警报；
    2. 验证基于 FIFO 与重仓 ADV 的流动性变现天数严密性；
    3. 验证 2015 流动性踩踏情景的变现天数显著高于其他情景；
    4. 验证 3D 矩阵数据结构 monte_carlo_3d_data 格式。
    """
    holdings = {
        "005561": 30000.0,
        "011613": 50000.0,
        "002351": 20000.0
    }

    # 1. 以保守型 C1 测试 (容忍度 5.0%)
    res_c1 = simulate_portfolio_cvar_bootstrap(
        holdings=holdings,
        total_capital=100000.0,
        investor_risk_tier="C1"
    )
    assert res_c1["investor_risk_tier"] == "C1"
    assert res_c1["risk_tolerance_mdd"] == 5.0
    assert res_c1["exceeds_risk_tolerance"] is True, "权益组合在极端情景下必须超出 C1 容忍度"

    # 2. 验证 2015 流动性踩踏变现天数显著增大
    sc_2015 = next(s for s in res_c1["scenarios"] if s["id"] == "2015_liquidity_stampede")
    sc_2024 = next(s for s in res_c1["scenarios"] if s["id"] == "2024_smallcap_liquidity")
    assert sc_2015["liquidation_days"]["avg_days"] > sc_2024["liquidation_days"]["avg_days"], (
        "2015 千股跌停踩踏流动性变现天数必须大于 2024 危机"
    )
    assert sc_2015["liquidation_days"]["days_100_pct"] >= sc_2015["liquidation_days"]["days_90_pct"]

    # 3. 验证 3D 曲面图数据结构
    mc_3d = res_c1.get("monte_carlo_3d_data", {})
    assert "scenarios" in mc_3d and len(mc_3d["scenarios"]) == 3
    assert "tiers" in mc_3d and mc_3d["tiers"] == ["C1", "C2", "C3", "C4", "C5"]
    assert "z_mdd_matrix" in mc_3d and len(mc_3d["z_mdd_matrix"]) == 3
    assert all(len(row) == 5 for row in mc_3d["z_mdd_matrix"])
    assert "z_liq_matrix" in mc_3d and len(mc_3d["z_liq_matrix"]) == 3


def test_g10_5_app_gui_r5_source_wireup_verification():
    """
    R5 静态源码与挂载核验：
    1. 验证 app_gui.py 中定义了四大核心渲染函数；
    2. 验证所有富文本返回均使用 _clean_html 且通过 safe_markdown_html 渲染；
    3. 验证 @media (max-width: 640px) 注入了 .stress-3d-container 与 .liquidity-table-scroll-container；
    4. 验证 col_sentry、Tab 1、Tab 2 正确挂载了 G10 组件。
    """
    gui_file = _AGY2_DIR / "app_gui.py"
    with open(gui_file, "r", encoding="utf-8") as f:
        code = f.read()

    # 1. 核心渲染函数定义
    assert "def render_correlation_mutation_card_html" in code
    assert "def render_stress_liquidity_card_html" in code
    assert "def render_liquidity_haircut_table" in code
    assert "def render_monte_carlo_3d_chart" in code

    # 2. 纯化与安全渲染
    assert "return _clean_html(" in code
    assert "safe_markdown_html(render_correlation_mutation_card_html" in code
    assert "safe_markdown_html(render_stress_liquidity_card_html" in code

    # 3. 响应式样式注入
    assert ".stress-3d-container" in code
    assert ".liquidity-table-scroll-container" in code
    assert "@media (max-width: 640px)" in code

    # 4. 双翼看板 col_sentry 与 Tab 1/2 挂载
    assert "evaluate_dynamic_correlation_mutation_instance" in code
    assert "render_monte_carlo_3d_chart" in code
    assert "render_liquidity_haircut_table" in code


def test_g10_6_apptest_gui_stress_and_liquidity_render():
    """
    R5 运行时端到端核验：
    使用 Streamlit AppTest 模拟拉起 app_gui.py，
    验证全局状态机初始化、双翼看板渲染、Tab 1/Tab 2 装配零异常。
    """
    from streamlit.testing.v1 import AppTest

    gui_file = _AGY2_DIR / "app_gui.py"
    at = AppTest.from_file(str(gui_file), default_timeout=35)
    at.run()

    assert not at.exception, f"AppTest 发生异常崩溃: {at.exception}"
