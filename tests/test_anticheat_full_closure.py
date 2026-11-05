# -*- coding: utf-8 -*-
"""
tests/test_anticheat_full_closure.py
反迎合作弊彻底整改、真数据链路闭环、7大模型与黑天鹅前端挂载、止盈与深套Alpha剥离诊断及三步建仓账本同步全套测试。

严格验证：
1. 测试 1：直接加载 pm.load_demo_portfolio() 真实的 pm.holdings (Dict[str, HoldingItem])，
   调用 ActiveRiskSentry().inspect_portfolio(pm.holdings, snapshot)，
   断言返回 alerts 中必须同时包含：
   - 011612 的未满 7 天锁仓红牌
   - 011613 的距 30 天免赎仅差 2 天黄牌
   - 013841 的浮亏 -16.19% 深套诊断预警及 Alpha/Beta 剥离建议
2. 测试 2：
   - 验证 StrategyBridge.compute_n_funds_model_portfolio 调度全部 7 大机构级模型均能成功求解，权重和严格为 1.0；
   - 验证 simulate_black_swan_stress 精准精算 2018 贸易摩擦熊市、2022 杀估值熊市、2024 微盘流动性危机三大极端场景；
   - 验证 AppTest 中 Tab 1 机构模型下拉框包含全部 7 个模型，且页面挂载黑天鹅测试卡；
3. 测试 3：验证在步骤三选择「稳健三步分批建仓」并点击「设为初始持仓」后，
   pm.holdings 总市值等于 50% 本金，且 pm.available_cash 严格等于剩余 50% 本金，资金绝对守恒；
4. 测试 4：验证主动风控哨「锁定调仓下界」与「阶梯止盈」与 Tab 2 调仓引擎的物理闭环联动，
   以及「调仓净效用门禁 (Net Utility Gate)」对差 2 天满 30 天免赎标的（011613）的暂缓减免。
"""

import os
import sys
from pathlib import Path
import pytest
import pandas as pd
import numpy as np

# 确保环境路径包含 AGY2_FundAdvisory
CURRENT_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = CURRENT_DIR.parent if CURRENT_DIR.name == "tests" else CURRENT_DIR
AGY2_DIR = WORKSPACE_ROOT / "AGY2_FundAdvisory"

if str(AGY2_DIR) not in sys.path:
    sys.path.insert(0, str(AGY2_DIR))
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from advisory_engine import ActiveRiskSentry, RADAR_SECTOR_CATALOG, SmartExecutionDCAEngine
from portfolio_manager import PortfolioManager
from strategy_bridge import StrategyBridge
from portfolio_optimizer import QUANT_MODELS_CATALOG
from winrate_engine import simulate_black_swan_stress


# =========================================================================
# 测试 1: 真实持仓对象上的六维预警哨与 Alpha/Beta 深套剥离诊断
# =========================================================================
def test_demo_portfolio_active_risk_sentry_real_objects():
    """
    测试 1：直接加载 pm.load_demo_portfolio() 真实的 pm.holdings（Dict[str, HoldingItem]），
    调用 ActiveRiskSentry().inspect_portfolio(pm.holdings, snapshot)，
    断言返回的 alerts 中必须同时包含：
    - 011612 的未满7天锁仓红牌
    - 011613 的距30天免赎仅差2天黄牌
    - 013841 的浮亏 -16.19% 深套诊断预警
    """
    pm = PortfolioManager()
    demo_res = pm.load_demo_portfolio()
    assert len(pm.holdings) >= 4, "演示持仓必须包含足够的标的"

    # 验证 RADAR_SECTOR_CATALOG 中 semiconductor 的 matrix_col 不再是 930609 纯债
    semi_catalog = RADAR_SECTOR_CATALOG.get("semiconductor", {})
    assert semi_catalog.get("matrix_col") != "930609", "semiconductor 不能映射为纯债 930609 指数"
    assert semi_catalog.get("matrix_col") == "STAR50_STITCH", "semiconductor 必须映射为 STAR50_STITCH"

    snapshot = StrategyBridge.get_latest_market_snapshot()
    sentry = ActiveRiskSentry()
    report = sentry.inspect_portfolio(pm.holdings, market_snapshot=snapshot)

    assert not report.get("all_passed"), "演示持仓包含高风险与锁仓标的，不应全部通过"
    alerts = report.get("alerts", [])
    assert len(alerts) >= 3, f"应该至少触发 3 项预警，当前: {len(alerts)}"

    alert_codes = [a.get("fund_code") for a in alerts]
    alert_types = [a.get("action_type") for a in alerts]
    alert_titles = [a.get("title", "") for a in alerts]
    alert_descs = [a.get("desc", "") for a in alerts]

    # 1. 011612 未满7天锁仓红牌
    has_011612 = any(
        a.get("fund_code") == "011612" and (
            a.get("action_type") == "lock_shares" or "7" in a.get("desc", "") or "锁仓" in a.get("dimension", "")
        )
        for a in alerts
    )
    assert has_011612, f"未触发 011612 的未满7天锁仓红牌，当前预警: {alerts}"

    # 2. 011613 距30天免赎仅差2天黄牌
    has_011613 = any(
        a.get("fund_code") == "011613" and ("30天" in a.get("title", "") or "30天" in a.get("desc", "") or "2天" in a.get("desc", ""))
        for a in alerts
    )
    assert has_011613, f"未触发 011613 距30天免赎仅差2天黄牌，当前预警: {alerts}"

    # 3. 013841 浮亏 -16.19% 深套诊断预警
    deep_loss_alert = next((a for a in alerts if a.get("fund_code") == "013841" and a.get("action_type") == "deep_loss_rebalance"), None)
    assert deep_loss_alert is not None, f"未触发 013841 深套诊断预警，当前预警列表: {alerts}"
    assert "深套" in deep_loss_alert.get("title", "") or "浮亏" in deep_loss_alert.get("title", ""), f"013841 预警标题不符合: {deep_loss_alert}"
    # 验证病根剥离诊断建议（科创50重叠或顺周期磨底）
    action_text = deep_loss_alert.get("action", "")
    assert "同质化重叠" in action_text or "置换" in action_text or "磨底" in action_text, f"013841 必须包含深套病根剥离诊断建议: {action_text}"

    # 4. 专项验证：非科技赛道深套标的（如医药/白酒）不得被误判为“与科创50同质化重叠”
    from portfolio_manager import FundHolding, HoldingBatch
    pharma_fund = FundHolding(
        fund_code="000933",
        fund_name="中证主要消费/医药健康指数A",
        share_class="A",
        shares=10000.0,
        cost_price=2.00,
        current_nav=1.60, # 浮亏 -20.0%
        market_value=16000.0,
        cost_basis=20000.0,
        floating_pnl=-4000.0,
        floating_pnl_pct=-20.0,
        batches=[HoldingBatch(
            batch_id="batch_pharma_1",
            buy_date="2026-09-01",
            shares=10000.0,
            cost_nav=2.00,
            holding_days=45
        )]
    )
    test_mixed_holdings = dict(pm.holdings)
    test_mixed_holdings["000933"] = pharma_fund
    rep_mixed = sentry.inspect_portfolio(test_mixed_holdings, market_snapshot=snapshot)
    pharma_alert = next((a for a in rep_mixed.get("alerts", []) if a.get("fund_code") == "000933"), None)
    assert pharma_alert is not None, "000933 浮亏 -20% 必须触发深套预警"
    assert "科创" not in pharma_alert.get("desc", ""), f"医药基金绝不能被误报与科创50同质化重叠: {pharma_alert['desc']}"
    assert "磨底" in pharma_alert.get("action", "") or "定投" in pharma_alert.get("action", ""), f"低估磨底医药标的应提示顺周期磨底/定投: {pharma_alert['action']}"

    # 5. 边缘用例：持仓对象 floating_pnl_pct 为 None 时安全降级，不抛 TypeError
    class HoldingWithNonePnl:
        fund_code = "005561"
        fund_name = "创金合信红利低波A"
        share_class = "A"
        shares = 1000.0
        cost_price = 0.0
        current_nav = 0.0
        market_value = 1000.0
        floating_pnl_pct = None
        batches = []

    none_pnl_holdings = {"005561": HoldingWithNonePnl()}
    rep_none = sentry.inspect_portfolio(none_pnl_holdings, market_snapshot=snapshot)
    assert isinstance(rep_none, dict) and "alerts" in rep_none


# =========================================================================
# 测试 2: 7 大机构定权模型与黑天鹅压力测试物理闭环
# =========================================================================
def test_all_seven_quant_models_and_black_swan_stress():
    """
    测试 2：
    1. 验证 QUANT_MODELS_CATALOG 完整包含全部 7 大模型；
    2. 切换每个模型调用 StrategyBridge.compute_n_funds_model_portfolio 均能成功求解，权重和严格为 1.0；
    3. 验证 simulate_black_swan_stress 准确输出三大历史熊市极端情景与超额防御数据。
    """
    required_models = [
        "hrp_cvar",
        "core_satellite",
        "all_weather",
        "black_litterman",
        "cond_winrate",
        "min_cvar",
        "kelly_momentum"
    ]

    for m in required_models:
        assert m in QUANT_MODELS_CATALOG, f"QUANT_MODELS_CATALOG 必须包含模型: {m}"

    # 求解每个模型的组合
    for m in required_models:
        res = StrategyBridge.compute_n_funds_model_portfolio(
            tier="C3",
            target_return_pct=12.0,
            num_funds=6,
            model_type=m,
            capital=100000.0
        )
        assert res is not None, f"模型 {m} 求解失败返回 None"
        opt_w = res.get("optimal_weights", {})
        assert len(opt_w) >= 3, f"模型 {m} 求解得到的标的数不足: {len(opt_w)}"
        w_sum = sum(opt_w.values())
        assert abs(w_sum - 1.0) < 1e-3, f"模型 {m} 权重和不等于 1.0: {w_sum}"
        for c, w in opt_w.items():
            assert not np.isnan(w) and w > 0, f"模型 {m} 包含非法权重: {c}={w}"

    # 验证黑天鹅极端行情压力测试器
    stress = simulate_black_swan_stress(
        holdings={"005561": 0.35, "100032": 0.20, "000216": 0.20, "017436": 0.15, "011613": 0.10},
        total_capital=100000.0
    )
    assert "scenarios" in stress, "压力测试必须返回 scenarios"
    scenarios = stress["scenarios"]
    assert len(scenarios) == 3, f"压力测试必须包含三大历史黑天鹅极端场景，当前: {len(scenarios)}"

    s_ids = [s["id"] for s in scenarios]
    assert "2018_trade_war" in s_ids
    assert "2022_valuation_kill" in s_ids
    assert "2024_micro_liquidity" in s_ids

    for sc in scenarios:
        assert sc["max_dd_pct"] > 0, f"场景 {sc['id']} 最大回撤必须 > 0"
        assert sc["max_loss_amt"] > 0, f"场景 {sc['id']} 最大亏损金额必须 > 0"
        assert "recovery_str" in sc, f"场景 {sc['id']} 必须包含回本时间"
        assert "excess_defense_pct" in sc, f"场景 {sc['id']} 必须包含超额防御"


# =========================================================================
# 测试 3: 步骤三稳健三步建仓账本守恒与可用现金池严格闭环
# =========================================================================
def test_step3_staged_deployment_ledger_conservation():
    """
    测试 3：验证在步骤三选择「稳健三步分批建仓」并点击「设为初始持仓」后，
    pm.holdings 总市值等于 50% 本金，且 pm.available_cash 严格等于剩余 50% 本金。
    """
    pm = PortfolioManager()
    total_capital = 100000.0
    blueprint = StrategyBridge.generate_zero_start_blueprint(
        total_capital=total_capital,
        tier="C3"
    )

    alloc_list = [
        {"code": it["fund_code"], "name": it["fund_name"], "weight": float(it.get("target_weight_pct", 20.0)) / 100.0}
        for it in blueprint.get("items", [])
    ]
    three_step_plan = SmartExecutionDCAEngine.plan_three_step_batches(
        total_capital=total_capital,
        allocations=alloc_list
    )

    # 1. 测试稳健三步分批建仓
    res = pm.apply_zero_start_blueprint(
        blueprint,
        cap_deployment_mode="稳健三步分批建仓",
        deployment_plan=three_step_plan
    )

    assert abs(pm.total_market_value - 50000.0) < 50.0, f"底仓市值应约为 50% 本金 (50,000)，当前: {pm.total_market_value}"
    assert abs(pm.available_cash - 50000.0) < 50.0, f"可用现金池应严格保留 50% 准备金 (50,000)，当前: {pm.available_cash}"
    assert abs(pm.total_equity - 100000.0) < 1.0, f"账户总权益必须严格等于总本金 100,000，当前: {pm.total_equity}"
    assert len(pm.staged_batch_plans) == 2, f"必须保留第 2 步与第 3 步分批预案，当前: {len(pm.staged_batch_plans)}"

    # 验证 staged_batch_plans 状态持久化与快照还原
    st_dict = pm._export_state_dict()
    assert "staged_batch_plans" in st_dict
    assert len(st_dict["staged_batch_plans"]) == 2
    pm_reload = PortfolioManager(db_path=":memory:")
    pm_reload._import_state_dict(st_dict)
    assert len(pm_reload.staged_batch_plans) == 2, "重新导入状态后 staged_batch_plans 必须完整保留"

    # 2. 测试一次性全额建仓
    pm_once = PortfolioManager(db_path=":memory:")
    res_once = pm_once.apply_zero_start_blueprint(
        blueprint,
        cap_deployment_mode="一次性建仓"
    )
    assert abs(pm_once.total_market_value - 100000.0) < 50.0, f"一次性建仓总市值应为 100,000，当前: {pm_once.total_market_value}"
    assert abs(pm_once.available_cash - 0.0) < 1.0, f"一次性建仓可用现金应为 0，当前: {pm_once.available_cash}"


# =========================================================================
# 测试 4: 预警哨一键处置联动与 Tab 2 调仓净效用门禁
# =========================================================================
def test_tab2_risk_sentry_linkage_and_net_utility_gate():
    """
    测试 4：
    1. 预警哨「锁定调仓下界」写入 locked_funds 时，调仓单强制禁卖；
    2. 预警哨「阶梯止盈」pending_take_profit 时，目标权重下调 40% 并增配纯债/红利底仓；
    3. 温和免伤模式下，对持有 28 天的 C 类标的（011613）自动暂缓赎回，提示节省赎回费。
    """
    pm = PortfolioManager()
    pm.load_demo_portfolio()

    target_weights = {
        "005561": 0.25,
        "100032": 0.25,
        "002351": 0.20,
        "011613": 0.30
    }

    # 1. 验证 locked_funds 锁定调仓下界禁卖
    orders_locked = StrategyBridge.generate_ai_rebalance_orders(
        current_holdings=pm.holdings,
        available_cash=pm.available_cash,
        target_weights_funds=target_weights,
        locked_funds=["011612", "013841"],
        mode="forced"
    )
    item_013841 = next((it for it in orders_locked["items"] if it["fund_code"] == "013841"), None)
    if item_013841:
        assert item_013841["action"] == "HOLD", "已锁定标的 action 必须为 HOLD"
        assert "手动锁定" in item_013841["action_text"], f"操作状态必须包含已手动锁定禁卖: {item_013841['action_text']}"
        assert item_013841["diff_amount"] == 0.0, f"已锁定标的减仓金额必须被清零: {item_013841['diff_amount']}"

    # 2. 验证阶梯止盈 pending_take_profit
    orig_tw_011613 = target_weights["011613"]
    orders_tp = StrategyBridge.generate_ai_rebalance_orders(
        current_holdings=pm.holdings,
        available_cash=pm.available_cash,
        target_weights_funds=target_weights,
        pending_take_profit={"fund_code": "011613", "ratio": 0.40},
        mode="forced"
    )
    new_tw = orders_tp["target_weights_funds"]
    expected_tw = round(orig_tw_011613 * 0.60, 4)
    assert abs(new_tw["011613"] - expected_tw) < 1e-4, f"止盈标的目标权重必须下调 40%: 当前 {new_tw['011613']}, 期望 {expected_tw}"
    # 验证增配给纯债 002351
    assert new_tw["002351"] > target_weights["002351"], "下调权重必须转配至纯债或红利低波"

    # 3. 验证温和免伤调仓模式下对 011613 (持有28天) 的净效用门禁暂缓赎回
    target_weights_cut = {
        "005561": 0.40,
        "100032": 0.40,
        "002351": 0.20,
        "011613": 0.0  # 建议全部卖出 011613
    }
    orders_gentle = StrategyBridge.generate_ai_rebalance_orders(
        current_holdings=pm.holdings,
        available_cash=pm.available_cash,
        target_weights_funds=target_weights_cut,
        mode="gentle"
    )
    it_011613 = next((it for it in orders_gentle["items"] if it["fund_code"] == "011613"), None)
    assert it_011613 is not None, "011613 必须出现在调仓单中"
    assert it_011613["action"] == "HOLD", "在温和模式下，持有28天的C类标的必须被暂缓赎回 (HOLD)"
    assert "暂缓赎回" in it_011613["action_text"], f"操作状态必须提示暂缓赎回: {it_011613['action_text']}"
    assert "立省" in it_011613["action_text"] or "免赎" in it_011613["action_text"], f"必须包含省费提示: {it_011613['action_text']}"

    # 4. 验证 simulate_rebalance_modes_and_consequences 中返回 imminent_fee_savings
    sim_res = StrategyBridge.simulate_rebalance_modes_and_consequences(
        pm=pm,
        active_tier="C3",
        target_weights=target_weights_cut,
        locked_funds=["011612"]
    )
    assert "imminent_fee_savings" in sim_res, "推演结果必须包含 imminent_fee_savings"
    imm = sim_res["imminent_fee_savings"]
    assert any(x["fund_code"] == "011613" and x["days_left"] == 2 for x in imm), f"必须识别出 011613 仅差 2 天免赎: {imm}"

    # 5. 验证 C类零费率置换指令 (c_replace) 真实消费闭环
    orders_creplace = StrategyBridge.generate_ai_rebalance_orders(
        current_holdings=pm.holdings,
        available_cash=pm.available_cash,
        target_weights_funds=target_weights,
        c_replace="011613",
        mode="forced"
    )
    tw_creplace = orders_creplace["target_weights_funds"]
    assert tw_creplace.get("011613", 0.0) == 0.0, "C类标的权重应已清空"
    assert tw_creplace.get("011612", 0.0) >= 0.30, f"对应 A 类标的应承接 C 类权重: {tw_creplace}"
    it_c = next((it for it in orders_creplace["items"] if it["fund_code"] == "011613"), None)
    assert it_c is not None and "C转A" in it_c["action_text"], f"操作清单必须标明 C转A置换: {it_c}"

    # 验证当 C 类标的原先未在目标组合时，权重依然严格守恒为 1.0
    tw_no_c = {"005561": 0.50, "100032": 0.50}
    orders_no_c = StrategyBridge.generate_ai_rebalance_orders(
        current_holdings=pm.holdings,
        available_cash=pm.available_cash,
        target_weights_funds=tw_no_c,
        c_replace="011613",
        mode="forced"
    )
    tw_res = orders_no_c["target_weights_funds"]
    assert abs(sum(tw_res.values()) - 1.0) < 1e-3, f"C类置换后权重和必须严格为 1.0: {tw_res}"


# =========================================================================
# 测试 5: Streamlit AppTest 界面验证全部 7 模型下拉与黑天鹅测试卡挂载
# =========================================================================
def test_apptest_tab1_seven_models_and_black_swan_rendering():
    """
    在 Streamlit AppTest 中验证 Tab 1 的模型下拉框包含全部 7 个模型，
    验证步骤二页面中真实渲染了「历史黑天鹅极端承压测试」卡片。
    """
    from streamlit.testing.v1 import AppTest
    app_path = AGY2_DIR / "app_gui.py"
    at = AppTest.from_file(str(app_path), default_timeout=120)
    at.session_state.active_tier_val = "C3"
    at.session_state.target_return_val = 15.0
    at.session_state.tab1_step_reached = 2
    at.session_state.tab1_trigger_sim = True
    at.run(timeout=120)

    assert not at.exception, f"AppTest 运行异常: {at.exception}"

    # 验证模型下拉框中包含全部 7 个模型
    model_sel = at.selectbox(key="tab1_sel_model_type")
    assert model_sel is not None, "必须存在 tab1_sel_model_type 下拉框"
    expected_models = [
        "鲁棒双核HRP",
        "核心-卫星杠铃",
        "全天候风险平价",
        "BL主客观观点融合",
        "条件胜率最优",
        "尾部风控CVaR",
        "凯利动量增强"
    ]
    for em in expected_models:
        assert em in model_sel.options, f"模型下拉框必须包含 {em}，当前选项: {model_sel.options}"

    # 验证步骤二页面中真实渲染了「历史黑天鹅极端承压测试」
    all_html_text = " ".join([m.value for m in at.markdown])
    assert "历史黑天鹅极端承压测试" in all_html_text, "步骤二必须真实渲染「历史黑天鹅极端承压测试」"
    assert "2018 贸易摩擦熊市" in all_html_text, "必须包含 2018 贸易摩擦熊市"
    assert "2022 核心资产杀估值" in all_html_text, "必须包含 2022 核心资产杀估值"
    assert "2024 微盘流动性危机" in all_html_text, "必须包含 2024 微盘流动性危机"

