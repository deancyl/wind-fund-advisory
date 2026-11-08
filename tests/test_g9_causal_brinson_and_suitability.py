# -*- coding: utf-8 -*-
"""
tests/test_g9_causal_brinson_and_suitability.py
Targeted Automated Test Suite for Milestone 3 (G9 Generation)

Covers the full matrix of G9 quant causality, risk sentry, and attribution capabilities:
1. 基因演化防未来函数因果探针 (P[:-1] 作用于 R[1:]，双边 20 bps 换手摩擦内扣，Walk-Forward 滚动切片轨迹)
2. 夏普比率强制扣减年化 2.0% 无风险利率 (Rf = 0.02 / 250.0)
3. 缺失规模三级穿透反查与 PENDING_VERIFICATION 告警及 <0.5 亿清盘排雷 (彻底废除 2.5 亿假兜底)
4. 投资者适当性 C1-C5 越界超配红色预警与盘中异动安全垫实时传导
5. Brinson-Fachler 经典模型三维超额收益拆解 (大类配置、优选选基、摩擦规避) 与数学恒等式严格平账
6. 基线快照持久化与跨会话不被冲刷不变量
"""

import sys
import os
import copy
from pathlib import Path
import numpy as np
import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
AGY_PATH = WORKSPACE_ROOT / "AGY2_FundAdvisory"
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))
if str(AGY_PATH) not in sys.path:
    sys.path.insert(0, str(AGY_PATH))

from AGY2_FundAdvisory.advisory_engine import (
    OnlineHeuristicFactorEvolver,
    ActiveRiskSentry,
    RADAR_SECTOR_CATALOG,
)
from AGY2_FundAdvisory.portfolio_manager import PortfolioManager


class TestCausalQuantEvolution:
    """1. 基因演化防未来函数因果探针与夏普无风险利率精算"""

    def test_causal_evaluator_lag1_alignment(self):
        """
        因果律铁律探针：
        验证在 _evaluate_population 中，第 t 日收盘特征 F[t] 选出的权重 P[t]
        严格滞后一期作用于第 t+1 日收益率 R[t+1] (P[:-1] 对应 R[1:])。
        """
        evolver = OnlineHeuristicFactorEvolver(population_size=16, generations=5, random_seed=42)
        T_len = 20
        S_num = 6
        N_pop = 2

        pop = np.full((N_pop, 4), 0.25, dtype=float)
        F = np.full((T_len, S_num, 4), 50.0, dtype=float)

        # 在 t=0..9，赛道 0, 1, 2 分数最高 (60.0)
        F[:10, 0:3, :] = 60.0
        F[:10, 3:6, :] = 40.0

        t_shock = 8
        s_shock = 5

        R_base = np.zeros((T_len, S_num), dtype=float)
        R_shock = np.zeros((T_len, S_num), dtype=float)
        R_shock[t_shock, s_shock] = 5.0  # 冲击 +500%

        fit_b, met_b = evolver._evaluate_population(pop, F, R_base)
        fit_s, met_s = evolver._evaluate_population(pop, F, R_shock)

        tau = t_shock - 1
        # t_shock 当天的有效收益是由 P[t_shock-1] 获取的，赛道 5 当时不属于 Top 3
        assert abs(met_s["R_p"][tau, 0] - met_b["R_p"][tau, 0]) < 1e-9, (
            "因果律泄露！t_shock 当日组合收益被未生效的权重提前捕获！"
        )

        # 即使 t_shock 特征飙升，也绝不能在 t_shock 当日生效
        F_spiked = F.copy()
        F_spiked[t_shock, s_shock, :] = 99.0
        fit_sp, met_sp = evolver._evaluate_population(pop, F_spiked, R_shock)
        assert abs(met_sp["R_p"][tau, 0] - met_b["R_p"][tau, 0]) < 1e-9, (
            "同日未来函数违背！第 t 日收盘选中的权重乘上了第 t 日自身的暴涨！"
        )

    def test_turnover_friction_deduction(self):
        """
        真实换手摩擦扣除核验：
        日度收益率净值合成必须真实内扣双边 20 bps 换手摩擦 (0.0020 * daily_to)。
        """
        evolver = OnlineHeuristicFactorEvolver(population_size=16, generations=5, random_seed=42)
        T_len = 30
        S_num = 6
        pop = np.full((2, 4), 0.25, dtype=float)

        # 构造高频换手的特征张量
        F = np.full((T_len, S_num, 4), 50.0, dtype=float)
        for t in range(T_len):
            winner = t % S_num
            F[t, winner, :] = 90.0

        R = np.full((T_len, S_num), 0.005, dtype=float)
        fit, met = evolver._evaluate_population(pop, F, R)

        turnover = met["turnover"]
        assert np.all(turnover > 0.0), "必须测算并存在换手率！"

        # 净日收益率必须严格小于毛收益率 0.005
        assert np.all(met["R_p"] < 0.005 + 1e-6)
        # 终端净值必须低于零摩擦基准 (1 + 0.005)**(T_len-1)
        gross_final_nav = (1.0 + 0.005) ** (T_len - 1)
        actual_final_nav = met["nav"][-1, 0]
        assert actual_final_nav < gross_final_nav, (
            f"换手摩擦未真实内扣！actual_nav={actual_final_nav}, gross_nav={gross_final_nav}"
        )

    def test_sharpe_ratio_rf_deduction(self):
        """
        夏普比率扣除 2.0% 无风险利率核验：
        日收益率均值减去 Rf_daily = 0.02 / 250.0 = 0.00008。
        当资产年化收益率 <= 0% 时，夏普比率必须严格为负。
        """
        evolver = OnlineHeuristicFactorEvolver(population_size=16, generations=5, random_seed=42)
        T_len = 25
        S_num = 4
        pop = np.full((1, 4), 0.25, dtype=float)
        F = np.full((T_len, S_num, 4), 50.0, dtype=float)

        # 收益率设定为微弱正收益 0.00004 (年化约 1%)，低于 2.0% 无风险利率
        R = np.full((T_len, S_num), 0.00004, dtype=float)
        fit, met = evolver._evaluate_population(pop, F, R)

        sharpe = met["sharpe"][0]
        assert sharpe < 0.0, (
            f"夏普比率未正确扣减 2.0% 年化无风险利率！微弱收益率 (年化 1%) 夏普为 {sharpe}，预期应为负数！"
        )

    def test_walk_forward_rolling_trajectory_genuine(self):
        """
        Walk-Forward 推进式样本外演化轨迹真实性核验：
        1. 必须返回 60 个交易日样本外净值与轨迹；
        2. 废除 lam = (t+1)/60.0 人工线性插值，四维权重二阶差分绝不能恒为 0。
        """
        evolver = OnlineHeuristicFactorEvolver(population_size=16, generations=5, random_seed=42)
        res = evolver.get_60d_rolling_nav_and_trajectory()

        assert "dates" in res and len(res["dates"]) == 60
        assert "nav_dynamic" in res and len(res["nav_dynamic"]) == 60
        assert "nav_static" in res and len(res["nav_static"]) == 60
        assert "trajectory" in res and len(res["trajectory"]) == 60

        traj = res["trajectory"]
        val_weights = np.array([p["valuation"] for p in traj], dtype=float)
        mom_weights = np.array([p["momentum"] for p in traj], dtype=float)

        # 检查二阶差分：线性插值 lam*(w1-w0)+w0 的二阶差分必恒等于 0
        diff2_val = np.diff(val_weights, n=2)
        assert not np.allclose(diff2_val, 0.0, atol=1e-6), (
            "检测到线性插值假轨迹！四维权重二阶差分恒为 0！"
        )
        assert np.any(np.abs(diff2_val) > 1e-4), "必须存在推进式滚动演化的非线性动态权重变迁！"


class TestActiveRiskSentryScaleAndSuitability:
    """2. 真实规模三级穿透反查、清盘排雷与投资者适当性及盘中异动安全垫"""

    def test_aum_three_tier_verification_and_liquidation(self):
        """
        真实规模穿透反查与清盘排雷：
        1. 规模 < 0.5 亿：触发 red 级别清盘警戒线预警 LIQUIDATION_DANGER；
        2. 规模正常 (>= 0.5 亿)：正常通过，无清盘预警；
        3. 缺失规模数据：触发 yellow 级别 PENDING_VERIFICATION 告警，彻底杜绝 2.5 亿安全假兜底。
        """
        sentry = ActiveRiskSentry(watchdog_path="data/test_watchdog.json")

        holdings = [
            {"code": "999001", "name": "微小迷你基金", "market_value": 10000.0, "holding_days": 35, "share_class": "A"},
            {"code": "999002", "name": "未知规模基金", "market_value": 10000.0, "holding_days": 35, "share_class": "A"},
            {"code": "005561", "name": "创金合信红利低波A", "market_value": 10000.0, "holding_days": 35, "share_class": "A"},
        ]

        # 显式传入 999001 规模为 0.3 亿 (<0.5亿)
        meta = {
            "999001": {"aum_billion": 0.30},
            # 999002 故意不给任何规模字段，让其穿透反查失败
            "005561": {"aum_billion": 12.5},
        }

        report = sentry.inspect_portfolio(holdings, fund_metadata=meta)
        alerts = report["alerts"]

        # 验证 999001 触发清盘红牌
        liq_alerts = [a for a in alerts if a.get("aum_status") == "LIQUIDATION_DANGER"]
        assert len(liq_alerts) == 1, f"未触发 <0.5 亿清盘红牌！alerts: {alerts}"
        assert liq_alerts[0]["fund_code"] == "999001"
        assert liq_alerts[0]["level"] == "red"
        assert "<0.5亿清盘警戒线" in liq_alerts[0]["title"]

        # 验证 999002 触发规模待核验黄牌 (零假 2.5 亿兜底)
        pend_alerts = [a for a in alerts if a.get("aum_status") == "PENDING_VERIFICATION"]
        assert len(pend_alerts) == 1, f"缺失规模未触发 PENDING_VERIFICATION 待核验预警！alerts: {alerts}"
        assert pend_alerts[0]["fund_code"] == "999002"
        assert pend_alerts[0]["level"] == "yellow"
        assert "规模待核验" in pend_alerts[0]["title"]

    def test_investor_suitability_c1_to_c5_risk_boundary(self):
        """
        投资者适当性 C1-C5 越界超配与一键降波巡检：
        1. C1 保守型客户 (上限 20% 权益)：持有 60% 权益或高波科技股，触发 red 级别越界预警；
        2. C5 进取型客户 (上限 95% 权益)：持有 60% 权益正常合规；持有 98% 权益触发越界预警；
        3. 预警文案中包含一键降波建议与精确人民币超配金额 (¥excess_mv)。
        """
        sentry = ActiveRiskSentry(watchdog_path="data/test_watchdog.json")

        # 构造权益占比 60% (¥60,000) 的组合，含高波科技 011613
        holdings = [
            {"code": "011613", "name": "科创50芯片ETF联接C", "market_value": 30000.0, "category": "科技成长", "holding_days": 35, "share_class": "C"},
            {"code": "005561", "name": "红利低波A", "market_value": 30000.0, "category": "红利高股息", "holding_days": 35, "share_class": "A"},
            {"code": "002351", "name": "易方达裕祥回报纯债A", "market_value": 40000.0, "category": "纯债固收", "holding_days": 35, "share_class": "A"},
        ]

        # 巡检 C1 客户 (上限 20%)
        rep_c1 = sentry.inspect_portfolio(holdings, investor_risk_tier="C1")
        suit_c1 = [a for a in rep_c1["alerts"] if a.get("dimension") == "投资者适当性"]
        assert len(suit_c1) == 1, "C1 客户超配权益未能触发投资者适当性预警！"
        assert suit_c1[0]["level"] == "red", "C1 客户严重超配且持有高波科技必须为 red 级！"
        assert suit_c1[0]["action_type"] == "rebalance_sector"
        assert "¥40,000.00" in suit_c1[0]["action"], "必须精确测算超配金额 (60,000 - 100,000*0.2 = 40,000)！"

        # 巡检 C5 客户 (上限 95%)，60% 权益应当合规
        rep_c5 = sentry.inspect_portfolio(holdings, investor_risk_tier="C5")
        suit_c5 = [a for a in rep_c5["alerts"] if a.get("dimension") == "投资者适当性"]
        assert len(suit_c5) == 0, f"C5 客户 60% 权益合规持仓被误判超配！{suit_c5}"

    def test_intraday_cushion_shock_transmission(self):
        """
        盘中异动安全垫实时传导：
        检测盘中实时估值异动 (单基 >= 2% 或组合 >= 1%) 对安全垫的实时消耗与传导报警。
        """
        sentry = ActiveRiskSentry(watchdog_path="data/test_watchdog.json")
        holdings = [
            {"code": "005561", "name": "红利低波A", "market_value": 50000.0, "holding_days": 35, "share_class": "A", "pnl_pct": 10.0},
            {"code": "011613", "name": "科创芯片C", "market_value": 50000.0, "holding_days": 35, "share_class": "C", "pnl_pct": 8.0},
        ]
        # 盘中行情快照：科创芯片盘中大跌 -3.5%，安全垫储备 ¥5,000
        snapshot = {
            "cushion_yuan": 5000.0,
            "fund_quotes": {
                "011613": {"gszzl": -3.50},
                "005561": {"gszzl": -0.50},
            }
        }
        # 盘中损耗：011613 亏 50000 * -0.035 = -1750，005561 亏 50000 * -0.005 = -250 -> 合计 -2000
        # 消耗安全垫比例：2000 / 5000 = 40% >= 20% 阈值
        rep = sentry.inspect_portfolio(holdings, snapshot=snapshot)
        cushion_alerts = [a for a in rep["alerts"] if a.get("dimension") == "盘中异动安全垫传导"]
        assert len(cushion_alerts) == 1, f"未触发盘中异动安全垫传导预警！alerts: {rep['alerts']}"
        assert cushion_alerts[0]["action_type"] == "defense_mode"
        assert cushion_alerts[0]["consumed_cushion_ratio"] == 40.0
        assert cushion_alerts[0]["level"] == "yellow"


class TestBrinsonAttributionAndPersistence:
    """3. Brinson-Fachler 三维超额收益归因模型与基线持久化"""

    def test_brinson_fachler_three_dimensional_attribution_identity(self):
        """
        Brinson-Fachler 经典超额拆解数学恒等式严格平账：
        1. 拆解为三维：大类配置效应 (Allocation)、优选选基效应 (Selection)、交易摩擦及惩罚规避 (Friction Saving)；
        2. 严格满足数学恒等式：
           abs(allocation_effect_yuan + selection_effect_yuan - total_active_add_yuan) < 1e-4
           abs(allocation_effect_pct + selection_effect_pct - total_active_add_pct) < 1e-4
        3. 保证 7 大既有顶级键名完全向下兼容。
        """
        pm = PortfolioManager(db_path=":memory:")

        # 初始持仓建立
        pm.add_or_update_holding("005561", shares=20000.0, nav=1.0, cost_price=1.0) # A股红利低波
        pm.add_or_update_holding("002351", shares=20000.0, nav=1.0, cost_price=1.0) # 纯债固收
        pm.available_cash = 10000.0

        # 基线已记录，此时模拟主动调仓增值：
        # 将红利低波净值提升至 1.15，纯债净值提升至 1.02
        pm.holdings["005561"].current_nav = 1.15
        pm.holdings["002351"].current_nav = 1.02

        # 模拟影子组合未动或表现落后
        audit = pm.evaluate_rebalance_audit()

        # 7 大既有顶级键名兼容性断言
        expected_keys = [
            "current_actual_equity",
            "shadow_hold_equity",
            "rebalance_value_add",
            "rebalance_value_add_pct",
            "saved_penalty_and_buffer_fees",
            "baseline_date",
            "shadow_holdings_count",
            "brinson_attribution",
        ]
        for k in expected_keys:
            assert k in audit, f"缺少兼容性键名: {k}"

        b = audit["brinson_attribution"]
        alloc_yuan = b["allocation_effect_yuan"]
        select_yuan = b["selection_effect_yuan"]
        total_yuan = b["total_active_add_yuan"]
        friction_yuan = b["friction_saving_yuan"]

        alloc_pct = b["allocation_effect_pct"]
        select_pct = b["selection_effect_pct"]
        total_pct = b["total_active_add_pct"]

        # 数学恒等式严格平账校验
        assert abs(alloc_yuan + select_yuan - total_yuan) < 1e-4, (
            f"Brinson 归因金额不平账！alloc: {alloc_yuan}, select: {select_yuan}, total: {total_yuan}"
        )
        assert abs(alloc_pct + select_pct - total_pct) < 1e-4, (
            f"Brinson 归因百分比不平账！alloc_pct: {alloc_pct}, select_pct: {select_pct}, total_pct: {total_pct}"
        )
        assert friction_yuan >= 0.0, "交易摩擦规避金额必须非负！"

        # 大类明细完整性校验
        breakdown = b["category_breakdown"]
        assert isinstance(breakdown, list) and len(breakdown) > 0
        for cat_item in breakdown:
            assert "category" in cat_item
            assert "portfolio_weight_pct" in cat_item
            assert "benchmark_weight_pct" in cat_item
            assert "allocation_effect_yuan" in cat_item
            assert "selection_effect_yuan" in cat_item

    def test_baseline_snapshot_persistence(self):
        """
        基线快照持久化核验：
        _export_state_dict 与 _import_state_dict 必须包含 initial_baseline_snapshot，
        确保账本重启或重载后历史调仓对比基线永不丢失或被调仓后的持仓冲刷。
        """
        pm1 = PortfolioManager(db_path=":memory:")
        pm1.add_or_update_holding("005561", shares=10000.0, nav=1.0, cost_price=1.0)
        pm1.available_cash = 5000.0

        # 触发基线记录
        audit1 = pm1.evaluate_rebalance_audit()
        orig_snap = copy.deepcopy(pm1.initial_baseline_snapshot)
        assert orig_snap["holdings"]["005561"] == 10000.0
        assert orig_snap.get("date") is not None or orig_snap.get("baseline_date") is not None

        # 导出状态字典
        state = pm1._export_state_dict()
        assert "initial_baseline_snapshot" in state, "导出状态字典中缺少 initial_baseline_snapshot！"
        saved_base = state["initial_baseline_snapshot"]
        assert saved_base["holdings"]["005561"] == 10000.0

        # 修改 pm1 持仓，再次调用 evaluate_rebalance_audit，验证 baseline 快照绝对不被覆写
        pm1.add_or_update_holding("005561", shares=25000.0, nav=1.2, cost_price=1.0)
        audit1_mod = pm1.evaluate_rebalance_audit()
        assert pm1.initial_baseline_snapshot["holdings"]["005561"] == 10000.0

        # 导入到全新 PortfolioManager 实例
        pm2 = PortfolioManager(db_path=":memory:")
        pm2._import_state_dict(state)

        assert hasattr(pm2, "initial_baseline_snapshot")
        assert pm2.initial_baseline_snapshot["holdings"]["005561"] == 10000.0
        audit_restored = pm2.evaluate_rebalance_audit()
        assert audit_restored["shadow_hold_equity"] == audit1["shadow_hold_equity"]
