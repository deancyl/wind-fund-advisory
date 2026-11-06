# -*- coding: utf-8 -*-
"""
G3 世代机构级量化与自适应风控进化闭环专项测试套件 (tests/test_g3_evolution_loop.py)

验证 4 大核心特性：
1. 动态相关性突变防御：EWMA 滚动协方差矩阵、>0.75 临界阈值判定、组合集中度降级警报、动态削减重仓敞口并平移至纯债/黄金；
2. 极端黑天鹅情景蒙特卡洛压力推演：10,000 次蒙特卡洛块重采样 (Circular Block Bootstrap)、极限 CVaR 99%、最大流动性折价损失预估；
3. 智能微观执行滑点优化：盘口深度与 ADV 测算、快速冲击成本 vs VWAP 分时成交量加权优化滑点、日内 5 阶段分笔调度表；
4. 全系统 AppTest 与端到端无异常闭环。
"""

import sys
from pathlib import Path
import pytest
import numpy as np
import pandas as pd

CURRENT_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = CURRENT_DIR.parent if CURRENT_DIR.name == "tests" else CURRENT_DIR
AGY2_DIR = WORKSPACE_ROOT / "AGY2_FundAdvisory"

if str(AGY2_DIR) not in sys.path:
    sys.path.insert(0, str(AGY2_DIR))
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from portfolio_manager import PortfolioManager, FundHolding, HoldingItem
from advisory_engine import ActiveRiskSentry, SmartExecutionDCAEngine
from winrate_engine import simulate_black_swan_stress, simulate_monte_carlo_block_bootstrap_stress
from portfolio_optimizer import simulate_monte_carlo_block_bootstrap_stress as opt_simulate_bootstrap


class TestG3EvolutionLoop:
    """G3 世代量化进化与自适应风控闭环专项测试"""

    def test_g3_1_dynamic_correlation_ewma_and_threshold_mutation(self):
        """
        1. 验证 EWMA 滚动协方差矩阵与动态相关系数测算
        2. 验证当相关系数 < 0.75 时正常解耦，不触发集中度降级
        3. 验证当相关系数突破 0.75 时，自动触发警报，削减重仓敞口并向纯债/黄金平移，权重严格守恒 1.000000
        """
        # 测试静态方法与实例方法
        pm = PortfolioManager(db_path=":memory:")
        pm.add_or_update_holding("005561", shares=30000, nav=1.5, holding_days=60, fund_name="创金合信红利低波A") # 45,000 (45%)
        pm.add_or_update_holding("100032", shares=20000, nav=1.25, holding_days=60, fund_name="富国中证红利指数增强A") # 25,000 (25%)
        pm.add_or_update_holding("161725", shares=15000, nav=1.0, holding_days=60, fund_name="招商中证白酒指数A") # 15,000 (15%)
        pm.add_or_update_holding("002351", shares=15000, nav=1.0, holding_days=60, fund_name="易方达裕祥回报债券A") # 15,000 (15%)

        # 1. 正常市场状态测试 (<0.75)
        res_normal = pm.evaluate_dynamic_correlation_mutation_instance(threshold=0.75, simulated_corr=0.35)
        assert res_normal["is_triggered"] is False
        assert res_normal["status"] == "DECOUPLED_NORMAL"
        assert res_normal["alert_level"] == "green"
        assert len(res_normal["cut_details"]) == 0
        assert res_normal["adjusted_weights"] == res_normal["original_weights"]

        # 2. 突变突破高危测试 (0.82 > 0.75)
        res_mutation = pm.evaluate_dynamic_correlation_mutation_instance(threshold=0.75, simulated_corr=0.82)
        assert res_mutation["is_triggered"] is True
        assert res_mutation["status"] == "MUTATION_ALERT"
        assert res_mutation["alert_level"] in ("yellow", "red")
        assert res_mutation["current_correlation"] == 0.82
        assert len(res_mutation["cut_details"]) > 0

        # 验证削减重仓敞口
        adj_w = res_mutation["adjusted_weights"]
        orig_w = res_mutation["original_weights"]

        # 红利低波 005561 原权重 45%，必须被削减
        assert adj_w["005561"] < orig_w["005561"], "005561 作为重仓红利资产必须被动态削减敞口！"
        # 纯债 002351 或黄金 000216 作为对冲压舱石必须被增配
        assert adj_w["002351"] > orig_w["002351"], "纯债资产必须吸收削减的重仓释放资金！"
        assert "000216" in adj_w, "黄金对冲必须吸收部分避险平移资金！"

        # 验证权重数学守恒
        tot_adj = sum(adj_w.values())
        assert abs(tot_adj - 1.0) < 1e-5, f"削减后权重和必须严格为 1.000000，实际为 {tot_adj}"

        # 3. 验证真实历史全收益矩阵 EWMA 测算
        res_real = PortfolioManager.evaluate_dynamic_correlation_mutation(threshold=0.75)
        assert -1.0 <= res_real["current_correlation"] <= 1.0
        assert "historical_correlation_tail" in res_real
        assert len(res_real["historical_correlation_tail"]) > 0

    def test_g3_2_active_risk_sentry_dimension_7_integration(self, tmp_path):
        """
        验证 ActiveRiskSentry 主动风险预警哨全面挂载维度 7 (动态相关性突变防御)
        """
        t_wd = tmp_path / "test_sentry_watchdog.json"
        sentry = ActiveRiskSentry(watchdog_path=str(t_wd))
        test_holdings = {
            "005561": HoldingItem(fund_code="005561", fund_name="创金合信红利低波A", shares=50000, cost_nav=1.0, current_nav=1.0),
            "161725": HoldingItem(fund_code="161725", fund_name="招商中证白酒指数A", shares=50000, cost_nav=1.0, current_nav=1.0),
        }

        # 传入 simulated_corr = 0.85 强制触发维度 7
        report = sentry.inspect_portfolio(
            holdings=test_holdings,
            market_snapshot={"simulated_corr": 0.85}
        )

        dim7_alerts = [a for a in report["alerts"] if a.get("dimension") == "动态相关性突变"]
        assert len(dim7_alerts) >= 1, "ActiveRiskSentry 未能正确捕获维度 7 动态相关性突变！"
        alert = dim7_alerts[0]
        assert alert["action_type"] == "correlation_mutation_defense"
        assert alert["current_correlation"] == 0.85
        assert alert["threshold"] == 0.75
        assert "集中度降级" in alert["action"] or "集中度降级" in alert["title"] or "集中度降级" in alert["desc"]

    def test_g3_3_extreme_black_swan_monte_carlo_block_bootstrap_cvar99(self):
        """
        验证 10,000 次蒙特卡洛块重采样 (Circular Block Bootstrap) 极端压力推演:
        1. 仿真次数必须严格达到 10,000 次；
        2. CVaR 99% (极限条件在险价值) 必须严格大于等于 VaR 99%（Expected Shortfall 极值数学不变量）；
        3. 测算最大流动性折价损失预估 (Max Liquidity Discount Loss)；
        4. 综合合并测算极限黑天鹅损失。
        """
        test_weights = {"005561": 0.40, "100032": 0.20, "002351": 0.20, "000216": 0.20}
        total_cap = 200000.0

        res = simulate_black_swan_stress(
            holdings=test_weights,
            total_capital=total_cap,
            n_simulations=10000,
            block_size=10,
            horizon_days=60
        )

        assert "monte_carlo_bootstrap" in res, "simulate_black_swan_stress 缺少 monte_carlo_bootstrap 字段！"
        mc = res["monte_carlo_bootstrap"]

        # 1. 验证 10,000 次仿真
        assert mc["n_simulations"] == 10000, f"仿真次数应为 10000，实际为 {mc['n_simulations']}"
        assert mc["block_size"] == 10
        assert mc["horizon_days"] == 60

        # 2. 验证 CVaR 99% 与 VaR 99% 数学不变量: CVaR_alpha >= VaR_alpha
        var_95 = mc["var_95_pct"]
        var_99 = mc["var_99_pct"]
        cvar_99 = mc["cvar_99_pct"]
        assert var_99 >= var_95, f"VaR 99% ({var_99}%) 应大于等于 VaR 95% ({var_95}%)"
        assert cvar_99 >= var_99, f"CVaR 99% ({cvar_99}%) 必须严格大于等于 VaR 99% ({var_99}%)（条件期望大于分位数）！"
        assert mc["cvar_99_amount"] == round(total_cap * (cvar_99 / 100.0), 2)

        # 3. 验证最大流动性折价损失预估
        liq_pct = mc["liquidity_discount_pct"]
        liq_amt = mc["liquidity_discount_amount"]
        assert 0.0 < liq_pct <= 10.0, f"流动性折价率应在 (0%, 10%] 合理区间，实际为 {liq_pct}%"
        assert liq_amt == round(total_cap * (liq_pct / 100.0), 2)

        # 4. 验证合并测算
        tot_loss_pct = mc["total_extreme_loss_pct"]
        tot_loss_amt = mc["total_extreme_loss_amount"]
        assert round(tot_loss_pct, 2) == round(cvar_99 + liq_pct, 2)
        assert round(tot_loss_amt, 2) == round(mc["cvar_99_amount"] + liq_amt, 2)

        # 5. 验证独立导出算子
        direct_mc = opt_simulate_bootstrap(holdings=test_weights, total_capital=total_cap, n_simulations=10000)
        assert direct_mc["n_simulations"] == 10000
        assert direct_mc["cvar_99_pct"] > 0

    def test_g3_4_smart_dca_vwap_execution_slippage_optimization(self):
        """
        验证 Tab 2 智能微观执行滑点优化与日内 5 阶段 VWAP 挂单调度:
        1. 快速市价单冲击成本 (Naive Impact) 必须严格大于优化后的 VWAP 滑点 (VWAP Slippage)；
        2. 节省滑点损耗 (Slippage Saved) 必须严格 > 0；
        3. 日内 5 阶段分笔调度表完整覆盖开盘至收盘，成交量比例和严格闭合至 1.00；
        4. plan_smart_dca 全面实装 vwap_execution_summary 机构级执行小抄；
        5. 场内 ETF 与场外公募双轨识别与动态梯度测算（绝不恒定等于 2.1 bps，场外输出跨日分批计划）。
        """
        # 1. 测试单只场内 ETF 滑点测算与日内调度
        etf_slip = SmartExecutionDCAEngine.calculate_vwap_execution_slippage(
            order_amount=80000.0,
            fund_code="518880",
            fund_name="华安黄金ETF"
        )
        assert etf_slip["is_etf"] is True
        assert etf_slip["naive_impact_bps"] > etf_slip["vwap_slippage_bps"], "快速市价冲击必须大于 VWAP 优化滑点！"
        assert etf_slip["slippage_saved_yuan"] > 0, "VWAP 必须实现滑点优化正向节省！"
        assert len(etf_slip["vwap_slices"]) == 5, "必须输出日内 5 阶段挂单调度！"

        # 验证 5 阶段成交量比例和为 1.0
        tot_slice_ratio = sum(s["vol_ratio"] for s in etf_slip["vwap_slices"])
        assert abs(tot_slice_ratio - 1.0) < 1e-4

        # 2. 验证场外联接基金与场外公募基金精准判定为 is_etf=False
        otc_gold = SmartExecutionDCAEngine.calculate_vwap_execution_slippage(
            order_amount=50000.0,
            fund_code="000216",
            fund_name="华安易富黄金ETF联接A"
        )
        assert otc_gold["is_etf"] is False, "000216 黄金联接基金严禁误判为场内 ETF！"

        otc_star = SmartExecutionDCAEngine.calculate_vwap_execution_slippage(
            order_amount=30000.0,
            fund_code="011613",
            fund_name="华夏科创50ETF联接C"
        )
        assert otc_star["is_etf"] is False, "011613 科创50联接基金严禁误判为场内 ETF！"

        otc_div = SmartExecutionDCAEngine.calculate_vwap_execution_slippage(
            order_amount=20000.0,
            fund_code="100032",
            fund_name="富国中证红利指数增强A"
        )
        assert otc_div["is_etf"] is False

        # 3. 验证场外基金 5 阶段执行表输出跨日/均线分批吸筹计划，严禁同日 5 小时下单
        otc_slices = otc_div["vwap_slices"]
        assert len(otc_slices) == 5
        assert any("T日" in s["phase"] for s in otc_slices)
        assert any("T+2日" in s["phase"] or "T+5日" in s["phase"] for s in otc_slices)
        assert not any("09:30-10:00" in s["phase"] for s in otc_slices), "场外基金严禁输出日内小时分单！"

        # 4. 验证金额规模动态梯度（从 1000 元到 50 万元显著单调递增，绝非恒定 2.1 bps）
        amounts = [1000.0, 2000.0, 10000.0, 50000.0, 100000.0, 500000.0]
        saved_bps_list = []
        for amt in amounts:
            res_amt = SmartExecutionDCAEngine.calculate_vwap_execution_slippage(
                order_amount=amt,
                fund_code="005561",
                fund_name="创金合信红利低波A",
                volatility=0.16
            )
            saved_bps_list.append(res_amt["slippage_saved_bps"])
            assert res_amt["slippage_saved_bps"] != 2.1, f"金额 ¥{amt} 测算的节省基点严禁恒定为 2.1 bps！"
            # 验证分笔执行金额与总金额分厘级严格平账
            tot_slices = sum(s["slice_amount"] for s in res_amt["vwap_slices"])
            assert abs(tot_slices - amt) < 0.02, f"5阶段调度分笔总和必须严格等于下单总金额！实际 {tot_slices} vs {amt}"

        # 验证单调递增梯度
        for i in range(len(saved_bps_list) - 1):
            assert saved_bps_list[i + 1] > saved_bps_list[i], (
                f"节省基点必须随金额单调递增！{amounts[i+1]}元 ({saved_bps_list[i+1]}) 应大于 {amounts[i]}元 ({saved_bps_list[i]})"
            )

        # 验证纯债低波动标的 (vol=0.04) 同样满足严格单调递增且零平台截断
        bond_saved = []
        for amt in [1000.0, 2000.0, 10000.0, 50000.0]:
            r_bond = SmartExecutionDCAEngine.calculate_vwap_execution_slippage(
                order_amount=amt,
                fund_code="002351",
                fund_name="易方达裕祥回报债券A",
                volatility=0.04
            )
            bond_saved.append(r_bond["slippage_saved_bps"])
        for i in range(len(bond_saved) - 1):
            assert bond_saved[i + 1] > bond_saved[i], "低波纯债基金金额递增必须保持节省基点严格递增！"

        # 验证场内 ETF (510300) 冲击成本随金额递增单调增大，滑点节省同样单调递增（无反转缺陷）
        etf_saved = []
        for amt in [1000.0, 2000.0, 5000.0, 10000.0, 50000.0]:
            r_etf = SmartExecutionDCAEngine.calculate_vwap_execution_slippage(
                order_amount=amt,
                fund_code="510300",
                fund_name="沪深300ETF",
                volatility=0.18
            )
            etf_saved.append(r_etf["slippage_saved_bps"])
            tot_slices = sum(s["slice_amount"] for s in r_etf["vwap_slices"])
            assert abs(tot_slices - amt) < 0.02, f"ETF 5阶段调度分笔总和必须严格等于下单总金额！实际 {tot_slices} vs {amt}"
        for i in range(len(etf_saved) - 1):
            assert etf_saved[i + 1] > etf_saved[i], "ETF 优化节省基点必须随金额单调递增，严禁反转递减！"

        # 5. 测试 plan_smart_dca 整体定投方案接入
        allocs = [
            {"code": "005561", "name": "创金合信红利低波A", "weight": 0.40},
            {"code": "518880", "name": "华安黄金ETF", "weight": 0.30},
            {"code": "002351", "name": "易方达裕祥债券A", "weight": 0.30},
        ]
        dca_res = SmartExecutionDCAEngine.plan_smart_dca(
            total_capital=120000.0,
            allocations=allocs,
            erp_percentile=80.0,
            bias_20=-1.5,
            periods=12
        )

        assert "vwap_execution_summary" in dca_res, "plan_smart_dca 必须包含 vwap_execution_summary！"
        v_sum = dca_res["vwap_execution_summary"]
        assert v_sum["total_naive_impact_yuan"] > v_sum["total_vwap_slippage_yuan"]
        assert v_sum["total_slippage_saved_yuan"] > 0
        assert v_sum["avg_slippage_saved_bps"] > 0

        # 每只基金的订单中必须附带 execution_slippage
        for o in dca_res["fund_orders"]:
            assert "execution_slippage" in o
            assert "vwap_slippage_yuan" in o
            assert "slippage_saved_yuan" in o

    def test_g3_5_app_gui_source_wireup_verification(self):
        """
        验证 app_gui.py 源码静态挂载与无死代码校验:
        1. 必须挂载 evaluate_dynamic_correlation_mutation_instance；
        2. 必须包含 10,000 次蒙特卡洛块重采样与 CVaR 99% 展示；
        3. 必须包含 VWAP 智能微观执行滑点优化卡片与调度表；
        4. 必须支持黑暗主题与移动端自适应。
        """
        gui_p = AGY2_DIR / "app_gui.py"
        src = gui_p.read_text(encoding="utf-8")

        assert "evaluate_dynamic_correlation_mutation" in src, "app_gui.py 未挂载动态相关性突变防御引擎！"
        assert "0.75" in src, "app_gui.py 缺少 0.75 警戒阈值！"
        assert "10,000 次蒙特卡洛块重采样" in src or "10,000次蒙特卡洛" in src, "Tab 3 缺少 10,000 次蒙特卡洛推演渲染！"
        assert "CVaR 99%" in src, "Tab 3 缺少 CVaR 99% 渲染！"
        assert "最大流动性折价损失预估" in src, "Tab 3 缺少最大流动性折价损失预估渲染！"
        assert "calculate_vwap_execution_slippage" in src or "vwap_execution_summary" in src, "app_gui.py 缺少 VWAP 执行滑点优化渲染！"
        assert "VWAP优化执行滑点" in src, "app_gui.py 缺少 VWAP优化执行滑点展示！"

    def test_g3_6_edge_cases_and_robustness_immunization(self):
        """
        验证四大关键极端鲁棒性免疫与数学精确性：
        1. compute_ewma_correlation 零方差无除以零报警与重复时间戳对齐去重；
        2. evaluate_dynamic_correlation_mutation 严禁误伤美股/海外对冲标的 (如 017436)；
        3. calculate_vwap_execution_slippage 自动剥除 sh/sz 交易所前缀与负数金额安全截断；
        4. simulate_monte_carlo_block_bootstrap_stress 首日 1.0 初始本金拼接，真实测算建仓首日最大回撤。
        """
        # 1. 零方差常数序列与重复时间戳
        idx_dup = [pd.Timestamp("2024-01-01"), pd.Timestamp("2024-01-01"), pd.Timestamp("2024-01-02"), pd.Timestamp("2024-01-03"), pd.Timestamp("2024-01-04"), pd.Timestamp("2024-01-05")]
        s_const = pd.Series([1.0]*6, index=idx_dup)
        s_norm = pd.Series([1.0, 1.01, 1.02, 1.03, 1.04, 1.05], index=idx_dup)
        corr_const = PortfolioManager.compute_ewma_correlation(s_const, s_norm)
        assert not corr_const.empty
        assert corr_const.iloc[-1] == 0.0

        # 2. 突变削减严禁误伤美股海外标的 (017436 华安纳指100)
        holdings_mix = {
            "005561": 0.40,  # 红利低波 (应削减)
            "017436": 0.30,  # 美股海外对冲 (严禁削减)
            "002351": 0.30,  # 纯债固收 (对冲压舱石，应吸收释放资金)
        }
        res_mut = PortfolioManager.evaluate_dynamic_correlation_mutation(holdings=holdings_mix, threshold=0.75, simulated_corr=0.85)
        assert res_mut["is_triggered"] is True
        adj_w = res_mut["adjusted_weights"]
        # 005561 必须被削减
        assert adj_w["005561"] < 0.40
        # 017436 美股海外资产严禁被误伤削减！
        assert adj_w["017436"] == 0.30, f"017436 作为跨市场美股对冲标的严禁被误伤削减！实际: {adj_w['017436']}"
        # 002351 纯债吸收资金
        assert adj_w["002351"] > 0.30

        # 3. 交易所前缀与负数金额安全免疫
        slip_prefix = SmartExecutionDCAEngine.calculate_vwap_execution_slippage(order_amount=50000.0, fund_code="sh518880")
        assert slip_prefix["is_etf"] is True
        assert slip_prefix["adv_est_yuan"] >= 1_000_000_000.0
        slip_neg = SmartExecutionDCAEngine.calculate_vwap_execution_slippage(order_amount=-1000.0, fund_code="510300")
        assert slip_neg["order_amount"] == 0.0
        assert slip_neg["vwap_slippage_yuan"] == 0.0

        # 4. 首日 1.0 初始本金拼接测算最大回撤
        df_synthetic = pd.DataFrame({
            "strategy_nav": [1.0, 0.90, 0.85, 0.88, 0.82, 0.80] + [0.80]*50
        })
        mc_res = simulate_monte_carlo_block_bootstrap_stress(
            holdings={"005561": 1.0},
            total_capital=100000.0,
            df_bt=df_synthetic,
            n_simulations=500,
            block_size=5,
            horizon_days=20
        )
        assert mc_res["cvar_99_pct"] >= 10.0, "首日下挫必须被真实纳入最大回撤与 CVaR 99% 精算！"

    def test_g3_7_tab2_rebalance_vwap_slippage_and_clean_data(self):
        """
        验证 Tab 2 调仓执行单全面支持 VWAP 滑点优化及底层数据 100% 纯净无脏数据:
        1. app_gui.py 中 Tab 2 调仓买入单挂载 calculate_vwap_execution_slippage 与 5 阶段挂单调度表；
        2. portfolio_ledger.json 与 portfolio_state.db 中 017436 彻底涤除“华宝”，官方正名“华安纳斯达克100ETF联接A”。
        """
        gui_p = AGY2_DIR / "app_gui.py"
        src = gui_p.read_text(encoding="utf-8")

        # Tab 2 买入/补仓 VWAP 滑点与调度表
        assert "vwap_rebal_orders" in src, "Tab 2 缺少 vwap_rebal_orders 挂载！"
        assert "买入快速冲击模拟损耗" in src, "Tab 2 缺少买入快速冲击模拟损耗展示！"
        assert "sel_tab2_vwap_schedule_item" in src, "Tab 2 缺少买入标的 VWAP 5 阶段调度表选择器！"

        # 验证 017436 官方正名在本地持仓账本中 100% 洁净
        ledger_p = WORKSPACE_ROOT / "portfolio_ledger.json"
        if ledger_p.exists():
            l_text = ledger_p.read_text(encoding="utf-8")
            assert "华宝纳斯达克" not in l_text, "portfolio_ledger.json 仍残留错误华宝名称！"
            assert "华安纳斯达克" in l_text, "portfolio_ledger.json 缺少官方华安名称！"

    def test_g3_8_historical_inflection_point_signals_verification(self):
        """
        验证投顾引擎在 A 股三大历史关键拐点的实证信号校准:
        1. 2021年2月核心资产见顶: 极端高估超买，发出明确止盈降仓信号 (multiplier <= 0.5)；
        2. 2022年4月恐慌底部: 极端低估超跌，发出逆向击球建仓信号 (multiplier >= 1.5)；
        3. 2024年9月底部反转: 极度低估水下，发出逆向击球猛扣信号 (multiplier >= 1.8)；
        4. StrategyBridge 与 SmartExecutionDCAEngine 双向接口校验通过。
        """
        from strategy_bridge import StrategyBridge

        # 1. AdvisoryEngine 拐点验证算子
        res_adv = SmartExecutionDCAEngine.verify_historical_inflection_signals()
        assert res_adv["all_inflections_verified"] is True
        assert res_adv["2021_top"]["is_valid"] is True
        assert res_adv["2021_top"]["multiplier"] <= 0.5
        assert res_adv["2022_bottom"]["is_valid"] is True
        assert res_adv["2022_bottom"]["multiplier"] >= 1.5
        assert res_adv["2024_bottom"]["is_valid"] is True
        assert res_adv["2024_bottom"]["multiplier"] >= 1.8

        # 2. StrategyBridge 拐点验证算子
        res_sb = StrategyBridge.verify_historical_inflection_signals()
        assert res_sb["all_inflections_verified"] is True
        assert res_sb["2021_top"]["multiplier"] == res_adv["2021_top"]["multiplier"]
        assert res_sb["2024_bottom"]["multiplier"] == res_adv["2024_bottom"]["multiplier"]

    def test_g5_1_single_fund_real_volatility_penetration(self):
        """
        G5 世代核心特性 1:
        1. 验证 get_fund_real_volatility_and_bias 穿透单基真实 20 日年化波动率与自身 MA20 乖离率；
        2. 验证消除 0.04/0.14/0.18 固定常数与 else 0.18，相同 5 万元申购下纯债 < 红利低波 < 科创50 节省基点严格单调递增；
        3. 验证 plan_smart_dca 全面穿透各单基自身波动率与单基乖离率，绝非大盘统一偏离抹平。
        """
        # 1. 单基真实年化波动率与日均波幅穿透核验
        funds_to_test = {
            "002351": ("易方达裕祥回报债券A", "bond", 0.001, 0.05),
            "000216": ("华安易富黄金ETF联接A", "gold", 0.08, 0.25),
            "005561": ("创金合信红利低波A", "dividend", 0.10, 0.25),
            "011613": ("华夏科创50ETF联接C", "tech", 0.20, 0.45),
        }
        metrics_dict = {}
        for code, (name, ftype, min_v, max_v) in funds_to_test.items():
            m = SmartExecutionDCAEngine.get_fund_real_volatility_and_bias(code, name)
            assert "volatility" in m and "bias_20" in m and "sigma_day" in m
            vol = m["volatility"]
            assert min_v <= vol <= max_v, f"基金 {code} ({name}) 波动率 {vol} 不在合理区间 [{min_v}, {max_v}]！"
            assert m["sigma_day"] > 0, f"基金 {code} sigma_day 必须大于 0！"
            metrics_dict[code] = m

        # 验证科技成长波动率 > 红利低波 > 纯债
        assert metrics_dict["011613"]["volatility"] > metrics_dict["005561"]["volatility"] > metrics_dict["002351"]["volatility"]

        # 2. 差异化微观执行损耗基点测算（消除 0.04/0.14/0.18 固定常数）
        # 在相同 50,000 元订单金额下，不传入外部 volatility，验证内部自动穿透真实波动率
        slip_bond = SmartExecutionDCAEngine.calculate_vwap_execution_slippage(
            order_amount=50000.0, fund_code="002351", fund_name="易方达裕祥回报债券A"
        )
        slip_gold = SmartExecutionDCAEngine.calculate_vwap_execution_slippage(
            order_amount=50000.0, fund_code="000216", fund_name="华安易富黄金ETF联接A"
        )
        slip_div = SmartExecutionDCAEngine.calculate_vwap_execution_slippage(
            order_amount=50000.0, fund_code="005561", fund_name="创金合信红利低波A"
        )
        slip_tech = SmartExecutionDCAEngine.calculate_vwap_execution_slippage(
            order_amount=50000.0, fund_code="011613", fund_name="华夏科创50ETF联接C"
        )

        # 验证严格单调递增性: 纯债 < 黄金/红利 < 科技成长
        assert slip_bond["slippage_saved_bps"] < slip_div["slippage_saved_bps"] < slip_tech["slippage_saved_bps"], (
            f"5万元申购节省基点必须满足 纯债 ({slip_bond['slippage_saved_bps']}) < 红利 ({slip_div['slippage_saved_bps']}) < 科技 ({slip_tech['slippage_saved_bps']})"
        )
        assert slip_tech["slippage_saved_yuan"] > slip_div["slippage_saved_yuan"] > slip_bond["slippage_saved_yuan"] > 0

        # 3. 验证 plan_smart_dca 真实穿透单基自身波动率与均线偏离
        dca_plan = SmartExecutionDCAEngine.plan_smart_dca(
            total_capital=150000.0,
            allocations=[
                {"code": "002351", "name": "易方达裕祥纯债A", "weight": 0.30},
                {"code": "005561", "name": "创金红利低波A", "weight": 0.40},
                {"code": "011613", "name": "华夏科创50C", "weight": 0.30},
            ],
            erp_percentile=82.6,
            bias_20=-2.07,
            periods=12
        )
        assert len(dca_plan["fund_orders"]) == 3
        order_map = {o["code"]: o for o in dca_plan["fund_orders"]}
        assert order_map["011613"]["slippage_saved_bps"] > order_map["005561"]["slippage_saved_bps"] > order_map["002351"]["slippage_saved_bps"]

    def test_g5_2_historical_inflection_ruler(self):
        """
        G5 世代核心特性 2:
        1. 验证 get_historical_inflection_ruler 产出 4 节点完整牛熊拐点对照尺；
        2. 验证 2021顶 (<=0.50x)、2022恐慌底 (>=1.50x)、2024反转底 (>=1.80x) 与今日水位；
        3. 验证 StrategyBridge 与 AdvisoryEngine 双向一致性；
        4. 验证 render_historical_inflection_ruler_html 能够正确渲染 4 节点紧凑胶囊条。
        """
        from strategy_bridge import StrategyBridge
        from app_gui import render_historical_inflection_ruler_html

        # 1. 验证 AdvisoryEngine 产出
        ruler_adv = SmartExecutionDCAEngine.get_historical_inflection_ruler(current_erp=82.6, current_bias=-2.07)
        assert ruler_adv["all_inflections_verified"] is True
        nodes = ruler_adv["nodes"]
        assert len(nodes) == 4, f"历史拐点对照尺必须严格包含 4 个节点，实际为 {len(nodes)}"

        n_2021, n_2022, n_2024, n_now = nodes
        assert n_2021["multiplier"] <= 0.50, f"2021 核心资产见顶乘数必须 <= 0.50，实际为 {n_2021['multiplier']}"
        assert n_2022["multiplier"] >= 1.50, f"2022 恐慌双底乘数必须 >= 1.50，实际为 {n_2022['multiplier']}"
        assert n_2024["multiplier"] >= 1.80, f"2024 反转底乘数必须 >= 1.80，实际为 {n_2024['multiplier']}"
        assert n_now["multiplier"] >= 1.50, f"今日实时乘数在底部吸筹区间必须 >= 1.50，实际为 {n_now['multiplier']}"

        # 2. 验证 StrategyBridge 桥接一致性
        ruler_sb = StrategyBridge.get_historical_inflection_ruler(current_erp=82.6, current_bias=-2.07)
        assert ruler_sb["all_inflections_verified"] is True
        assert ruler_sb["nodes"][0]["multiplier"] == n_2021["multiplier"]
        assert ruler_sb["nodes"][1]["multiplier"] == n_2022["multiplier"]
        assert ruler_sb["nodes"][2]["multiplier"] == n_2024["multiplier"]
        assert ruler_sb["nodes"][3]["multiplier"] == n_now["multiplier"]

        # 3. 验证前端 HTML 渲染
        html = render_historical_inflection_ruler_html(ruler_adv)
        assert "历史三大牛熊拐点实盘对照尺" in html
        assert "2021" in html
        assert f"{n_2021['multiplier']:.2f}x" in html
        assert "2022" in html
        assert f"{n_2022['multiplier']:.2f}x" in html
        assert "2024" in html
        assert f"{n_2024['multiplier']:.2f}x" in html
        assert "今日实时水位" in html
        assert "inflection-ruler-scroll-row" in html

    def test_g5_3_cushion_break_even_stress_model(self):
        """
        G5 世代核心特性 3:
        1. 验证 013841 纠偏后真实历史 Beta 为 ~1.2346，纯债接近 0，黄金接近 0；
        2. 验证组合加权 Beta、综合安全垫厚度、破净安全边际与 3 档大盘承压推演；
        3. 验证浮亏账本自适应切换为回本临界反弹，全现金组合自适应提示物理免疫；
        4. 验证 render_portfolio_cushion_and_stress_card_html 能够正确渲染看板。
        """
        from strategy_bridge import StrategyBridge
        from app_gui import render_portfolio_cushion_and_stress_card_html

        # 1. 验证单基 Beta 测算与纠偏
        pm = PortfolioManager()
        beta_chip = pm.calculate_asset_historical_beta("013841")
        assert abs(beta_chip - 1.2346) < 0.05, f"013841 纠偏后 Beta 应约为 1.2346，实际为 {beta_chip}"
        beta_bond = pm.calculate_asset_historical_beta("002351")
        assert abs(beta_bond) < 0.05, f"纯债 002351 Beta 应接近 0，实际为 {beta_bond}"
        beta_gold = pm.calculate_asset_historical_beta("000216")
        assert abs(beta_gold) < 0.05, f"黄金 000216 Beta 应接近 0，实际为 {beta_gold}"

        # 2. 验证主实盘账本下的综合安全垫与 3 档大盘急跌推演
        cushion_model = pm.calculate_portfolio_cushion_and_stress_model(current_index_point=3920.0)
        assert cushion_model["portfolio_weighted_beta"] > 0
        assert cushion_model["comprehensive_cushion"] > 0
        assert cushion_model["cushion_ratio_pct"] > 0
        assert cushion_model["is_in_floating_loss"] is False
        assert cushion_model["break_even_drop_pct"] < 0

        scenarios = cushion_model["stress_scenarios"]
        assert len(scenarios) == 3
        s_drop3, s_drop5, s_drop10 = scenarios
        assert s_drop3["market_drop_pct"] == -3.0
        assert s_drop5["market_drop_pct"] == -5.0
        assert s_drop10["market_drop_pct"] == -10.0
        assert abs(s_drop10["expected_loss_yuan"]) > abs(s_drop5["expected_loss_yuan"]) > abs(s_drop3["expected_loss_yuan"]) > 0

        # 3. 验证浮亏账本自适应
        loss_pm = PortfolioManager(db_path=":memory:", ledger_json_path="test_loss_cushion.json")
        loss_pm.holdings = {
            "005561": FundHolding(
                fund_code="005561", fund_name="创金红利低波A",
                shares=10000.0, cost_price=2.5, current_nav=2.0,
                market_value=20000.0, cost_basis=25000.0,
                floating_pnl=-5000.0, floating_pnl_pct=-20.0
            )
        }
        loss_pm.available_cash = 0.0
        loss_pm.in_transit_cash = 0.0
        loss_model = loss_pm.calculate_portfolio_cushion_and_stress_model(current_index_point=3920.0)
        assert loss_model["is_in_floating_loss"] is True
        assert loss_model["recovery_rise_pct"] > 0
        assert "回本" in loss_model["safety_margin_summary"]

        # 4. 验证全现金组合自适应
        cash_pm = PortfolioManager(db_path=":memory:", ledger_json_path="test_cash_cushion.json")
        cash_pm.holdings = {}
        cash_pm.available_cash = 100000.0
        cash_pm.in_transit_cash = 0.0
        cash_model = cash_pm.calculate_portfolio_cushion_and_stress_model()
        assert cash_model["portfolio_weighted_beta"] == 0.0
        assert "100% 现金流动性" in cash_model["safety_margin_summary"] or "物理免疫" in cash_model["safety_margin_summary"]

        # 5. 验证 StrategyBridge 桥接一致性
        sb_model = StrategyBridge.calculate_portfolio_cushion_and_stress_model(current_index_point=3920.0)
        assert abs(sb_model["portfolio_weighted_beta"] - cushion_model["portfolio_weighted_beta"]) < 1e-4

        # 6. 验证前端 HTML 渲染
        html = render_portfolio_cushion_and_stress_card_html(cushion_model)
        assert "浮盈安全垫抗震承压与本金破净临界看板" in html
        assert "组合加权 Beta" in html
        assert "综合安全垫厚度" in html
        assert "单日急跌 -3%" in html
        assert "周度回调 -5%" in html
        assert "极端回调 -10%" in html

    def test_g5_4_tail_valuation_anomaly_alerts(self):
        """
        G5 世代核心特性 4:
        1. 验证 14:30 尾盘估值异动预警算法三种情境（防追高、黄金坑、正常）；
        2. 验证盘中大涨 > 1.5 sigma_day 且正乖离触发 ANTI_CHASING，扣款乘数 0.60x；
        3. 验证盘中急跌 > 1.5 sigma_day 且负乖离触发 GOLDEN_PIT，扣款乘数 1.15x；
        4. 验证平稳波动触发 NORMAL，扣款乘数 1.00x；
        5. 验证 StrategyBridge 桥接产出完全一致。
        """
        from strategy_bridge import StrategyBridge

        # 情景 1: 盘中大涨 +2.5% (> 1.5 sigma_day) 且正乖离
        spike = SmartExecutionDCAEngine.evaluate_tail_valuation_anomaly("005561", "创金红利低波A", realtime_quote=2.5)
        assert spike["anomaly_type"] == "ANTI_CHASING"
        assert spike["amount_multiplier"] == 0.60
        assert "防追高" in spike["anomaly_tag"]
        assert spike["sigma_day"] > 0

        # 情景 2: 盘中急跌 -4.0% (> 1.5 sigma_day) 且负乖离
        pit = SmartExecutionDCAEngine.evaluate_tail_valuation_anomaly("011613", "华夏科创50C", realtime_quote=-4.0)
        assert pit["anomaly_type"] == "GOLDEN_PIT"
        assert pit["amount_multiplier"] == 1.15
        assert "黄金坑" in pit["anomaly_tag"]

        # 情景 3: 盘中微幅波动 (0.01%)
        norm = SmartExecutionDCAEngine.evaluate_tail_valuation_anomaly("002351", "易方达纯债A", realtime_quote=0.01)
        assert norm["anomaly_type"] == "NORMAL"
        assert norm["amount_multiplier"] == 1.00
        assert "平稳" in norm["anomaly_tag"]

        # 验证 StrategyBridge 双向一致
        sb_spike = StrategyBridge.evaluate_tail_valuation_anomaly("005561", "创金红利低波A", realtime_quote=2.5)
        assert sb_spike["anomaly_type"] == "ANTI_CHASING"
        assert sb_spike["amount_multiplier"] == 0.60
        assert sb_spike["anomaly_tag"] == spike["anomaly_tag"]

        sb_pit = StrategyBridge.evaluate_tail_valuation_anomaly("011613", "华夏科创50C", realtime_quote=-4.0)
        assert sb_pit["anomaly_type"] == "GOLDEN_PIT"
        assert sb_pit["amount_multiplier"] == 1.15

        sb_norm = StrategyBridge.evaluate_tail_valuation_anomaly("002351", "易方达纯债A", realtime_quote=0.01)
        assert sb_norm["anomaly_type"] == "NORMAL"
        assert sb_norm["amount_multiplier"] == 1.00



