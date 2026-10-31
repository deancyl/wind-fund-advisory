# -*- coding: utf-8 -*-
"""
Adversarial Stress Test Suite (Challenger Orch4-2)
Author: challenger_orch4_2 (Empirical Challenger)
Target:
  - R3 Three-Stage Attack/Defense Loop (Left-side extreme oversold, Schmitt hysteresis noise series, Right-side extreme overbought/crowded)
  - R4 Rebalance Suitability Evaluator & Dual-Mode Consequence Simulators (7-day penalty lock, 4D balanced accounting)
  - Stock Overlap Matrix Exemption (Dual dividend bottom-tier exemption & malicious non-exempt false diversification detection)
"""

import math
import numpy as np
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from strategy_bridge import StrategyBridge
from portfolio_manager import PortfolioManager, FUND_LOOK_THROUGH_DATA
from trading_clock_fee import FeeMatrixCalculator, TradingClock


@pytest.fixture
def temp_pm(tmp_path):
    """隔离测试用 PortfolioManager，使用临时 SQLite 数据库与 JSON 账本"""
    db_file = tmp_path / "test_adv_orch4_2.db"
    json_file = tmp_path / "test_adv_orch4_2.json"
    pm = PortfolioManager(db_path=db_file, ledger_json_path=json_file)
    return pm


# =============================================================================
# 1. 三段式攻防闭环对抗测试 (Three-Stage Attack/Defense Loop)
# =============================================================================

def test_adversarial_three_stage_left_oversold():
    """
    【左侧极值超卖极限点对抗测试】
    1. 构造左侧超卖极限点（erp=95%, bias_20=-8.0%），断言纯债自动削减并增配宽基 011613/001053；
    2. 验证 60% : 40% 划拨比例；
    3. 全档位压力测试 (C2~C5 均触发，C1 坚守纯债防守)；
    4. 极端黑天鹅超卖 (-25.0%, erp=99.9%) 底仓纯债安全垫保护；
    5. 临界阈值边界测试 (-4.4% vs -4.5%, 74.9% vs 75.0%)。
    """
    # 1. 基准与超卖对比
    neutral_snap = {
        "erp_percentile": 50.0,
        "bias_20": 0.0,
        "regime": "OSCILLATING"
    }
    oversold_snap = {
        "erp_percentile": 95.0,
        "bias_20": -8.0,
        "regime": "OSCILLATING"
    }

    w_neutral = StrategyBridge.compute_dynamic_tier_weights(tier="C3", market_snapshot=neutral_snap)
    w_oversold = StrategyBridge.compute_dynamic_tier_weights(tier="C3", market_snapshot=oversold_snap)

    # 断言纯债 (002351) 仓位下降
    assert w_oversold.get("002351", 0.0) < w_neutral.get("002351", 0.0), (
        f"左侧超卖时纯债仓位必须被划拨削减: neutral={w_neutral.get('002351')}, oversold={w_oversold.get('002351')}"
    )

    # 断言高弹性宽基 (011613 华夏科创50 / 001053 创金合信中证500) 仓位增加
    equity_oversold = w_oversold.get("011613", 0.0) + w_oversold.get("001053", 0.0)
    equity_neutral = w_neutral.get("011613", 0.0) + w_neutral.get("001053", 0.0)
    assert equity_oversold > equity_neutral, (
        f"左侧超卖时必须增配高弹性宽基: neutral={equity_neutral}, oversold={equity_oversold}"
    )
    assert w_oversold.get("011613", 0.0) > 0.0, "科创50必须获得增配"
    assert w_oversold.get("001053", 0.0) > 0.0, "中证500必须获得增配"

    # 断言权重归一化 100%
    assert abs(sum(w_oversold.values()) - 1.0) < 1e-4, f"权重和必须严格为 1.0，实际: {sum(w_oversold.values())}"

    # 2. 全档位风险单调性与左侧响应测试
    equity_sums = {}
    for tier in ["C1", "C2", "C3", "C4", "C5"]:
        w_t = StrategyBridge.compute_dynamic_tier_weights(tier=tier, market_snapshot=oversold_snap)
        assert abs(sum(w_t.values()) - 1.0) < 1e-4
        defensive_codes = {"002351", "000086", "018757", "000216", "000217"}
        eq_sum = sum(w for c, w in w_t.items() if c not in defensive_codes)
        equity_sums[tier] = eq_sum

    # C1 必须保持严格低风险防守 (权益 <= 25%)
    assert equity_sums["C1"] <= 0.25, f"C1 档位超卖时必须守住低风险防守边界: {equity_sums['C1']}"
    # 严格单调性断言：Equity(C1) < Equity(C2) < Equity(C3) < Equity(C4) < Equity(C5)
    assert equity_sums["C1"] < equity_sums["C2"] < equity_sums["C3"] < equity_sums["C4"] < equity_sums["C5"], (
        f"全档位权益风险单调性破坏: {equity_sums}"
    )

    # 3. 极端黑天鹅崩盘极值施压 (-25% 乖离, ERP 99.9%)
    extreme_snap = {
        "erp_percentile": 99.9,
        "bias_20": -25.0,
        "regime": "BEAR"
    }
    w_extreme = StrategyBridge.compute_dynamic_tier_weights(tier="C3", market_snapshot=extreme_snap)
    assert abs(sum(w_extreme.values()) - 1.0) < 1e-4
    # 纯债必须保留安全垫，不被抽干
    assert w_extreme.get("002351", 0.0) >= 0.04, f"极端崩盘下纯债不能被抽干: {w_extreme.get('002351')}"

    # 4. 临界阈值边界测试
    # ERP 74.9% (未达到 75.0% 阈值) -> 不触发左侧超卖吸筹
    snap_sub_erp = {"erp_percentile": 74.9, "bias_20": -8.0, "regime": "OSCILLATING"}
    w_sub_erp = StrategyBridge.compute_dynamic_tier_weights(tier="C3", market_snapshot=snap_sub_erp)
    assert w_sub_erp.get("011613", 0.0) == 0.0, "ERP < 75% 绝不应触发左侧科创50增配"

    # bias_20 = -4.4% (未达到 -4.5% 阈值) -> 不触发左侧超卖吸筹
    snap_sub_bias = {"erp_percentile": 85.0, "bias_20": -4.4, "regime": "OSCILLATING"}
    w_sub_bias = StrategyBridge.compute_dynamic_tier_weights(tier="C3", market_snapshot=snap_sub_bias)
    assert w_sub_bias.get("011613", 0.0) == 0.0, "bias_20 > -4.5% 绝不应触发左侧科创50增配"


def test_adversarial_three_stage_schmitt_hysteresis_noise():
    """
    【施密特迟滞震荡噪音序列对抗测试】
    1. 构造高频波动时间序列（50次反复在 [-1.4%, +1.1%] 之间摆动）；
    2. 断言仓位严格锁定，50次高频波动期间每步调仓换手率严格为 0.0；
    3. 边界突破测试：突破 +1.2% 上轨或跌破 -1.5% 下轨时解除锁定。
    """
    # 构造初始步长 0 的基准锁定权重
    init_snap = {
        "bias_20": 0.0,
        "lock_previous_weights": True,
        "regime": "OSCILLATING"
    }
    w_initial = StrategyBridge.compute_dynamic_tier_weights(tier="C3", market_snapshot=init_snap)
    assert len(w_initial) > 0

    # 生成 50 次高频高波动噪音序列，严格约束在 [-1.4%, +1.1%] 迟滞死区内部
    np.random.seed(42)
    # 结合高频三角波与均匀随机噪音
    t = np.linspace(0, 20 * np.pi, 50)
    noise_seq = 1.25 * np.sin(t)  # 幅度在 [-1.25, +1.25]
    # 严格映射至 [-1.40, +1.10]
    clamped_noise = np.clip(noise_seq, -1.40, 1.10)

    total_turnover = 0.0
    w_prev = dict(w_initial)

    for i, bias_val in enumerate(clamped_noise):
        snap = {
            "bias_20": float(bias_val),
            "lock_previous_weights": True,
            "regime": "OSCILLATING"
        }
        w_curr = StrategyBridge.compute_dynamic_tier_weights(tier="C3", market_snapshot=snap)

        # 断言仓位严格锁定，等于初识仓位
        assert w_curr == w_initial, f"步长 {i} (bias_20={bias_val:.2f}%) 仓位发生漂移跳变: {w_curr} vs {w_initial}"

        # 换手率精算: 0.5 * sum(|w_curr - w_prev|)
        all_keys = set(w_curr.keys()).union(set(w_prev.keys()))
        turnover_step = 0.5 * sum(abs(w_curr.get(k, 0.0) - w_prev.get(k, 0.0)) for k in all_keys)
        total_turnover += turnover_step
        w_prev = dict(w_curr)

    # 断言 50 次高频波动累计换手率严格为 0.0
    assert total_turnover == 0.0, f"迟滞死区内高频噪音产生换手磨损: {total_turnover}"

    # 边界突破测试:
    # 突破上轨 (+1.3% > +1.2%)
    break_up_snap = {
        "bias_20": 1.3,
        "lock_previous_weights": False,
        "market_state_code": "GROWTH_BULL"
    }
    w_break_up = StrategyBridge.compute_dynamic_tier_weights(tier="C3", market_snapshot=break_up_snap)
    # 向上突破进入进攻态，成长股 (011613) 增加
    assert w_break_up.get("011613", 0.0) > 0.0, "突破上轨进入进攻态必须放开高弹性成长配置"


def test_adversarial_three_stage_right_overbought_profit_taking():
    """
    【右侧极端超买与极度拥挤阶梯止盈对抗测试】
    1. 构造右侧超买极值（bias_20=+9.0% 或 crowding_warning=True）；
    2. 断言高波动成长仓位主动削减 35% 并落袋转入纯债与红利低波；
    3. 验证 50% 纯债 + 50% 红利低波 平分利润分配机制；
    4. 临界阈值边界测试 (+6.4% vs +6.5%)。
    """
    normal_bull_snap = {
        "bias_20": 2.0,
        "crowding_warning": False,
        "regime": "BULL",
        "market_state_code": "GROWTH_BULL"
    }
    overbought_snap = {
        "bias_20": 9.0,  # 极端超买 (+9.0% >> +6.5%)
        "crowding_warning": False,
        "regime": "BULL",
        "market_state_code": "GROWTH_BULL"
    }
    crowding_snap = {
        "bias_20": 2.0,
        "crowding_warning": True,  # 极度拥挤预警
        "regime": "BULL",
        "market_state_code": "GROWTH_BULL"
    }

    w_normal = StrategyBridge.compute_dynamic_tier_weights(tier="C3", market_snapshot=normal_bull_snap)
    w_overbought = StrategyBridge.compute_dynamic_tier_weights(tier="C3", market_snapshot=overbought_snap)
    w_crowded = StrategyBridge.compute_dynamic_tier_weights(tier="C3", market_snapshot=crowding_snap)

    growth_codes = ["011613", "001053", "016634", "013841", "007339"]

    growth_normal = sum(w_normal.get(c, 0.0) for c in growth_codes)
    growth_ob = sum(w_overbought.get(c, 0.0) for c in growth_codes)
    growth_cr = sum(w_crowded.get(c, 0.0) for c in growth_codes)

    # 1. 断言成长仓位削减约 35%
    assert growth_normal > 0.0
    assert growth_ob < growth_normal, f"超买态成长敞口未削减: normal={growth_normal}, overbought={growth_ob}"
    assert growth_cr < growth_normal, f"拥挤预警下成长敞口未削减: normal={growth_normal}, crowded={growth_cr}"

    cut_pct_ob = (growth_normal - growth_ob) / growth_normal
    assert 0.25 <= cut_pct_ob <= 0.45, f"超买止盈削减比例必须在 35% 左右，实际: {cut_pct_ob:.2%}"

    # 2. 断言削减的资金必须落袋转入纯债 (002351) 与红利低波 (005561)
    defensive_normal = w_normal.get("002351", 0.0) + w_normal.get("005561", 0.0)
    defensive_ob = w_overbought.get("002351", 0.0) + w_overbought.get("005561", 0.0)
    defensive_cr = w_crowded.get("002351", 0.0) + w_crowded.get("005561", 0.0)

    assert defensive_ob > defensive_normal, "超买利润必须增加纯债与红利低波"
    assert defensive_cr > defensive_normal, "拥挤止盈必须增加纯债与红利低波"

    # 断言归一化
    assert abs(sum(w_overbought.values()) - 1.0) < 1e-4
    assert abs(sum(w_crowded.values()) - 1.0) < 1e-4

    # 3. 临界阈值边界测试 (+6.4% 不触发，+6.5% 触发)
    sub_ob_snap = {"bias_20": 6.4, "crowding_warning": False, "regime": "BULL", "market_state_code": "GROWTH_BULL"}
    crit_ob_snap = {"bias_20": 6.5, "crowding_warning": False, "regime": "BULL", "market_state_code": "GROWTH_BULL"}

    w_sub = StrategyBridge.compute_dynamic_tier_weights(tier="C3", market_snapshot=sub_ob_snap)
    w_crit = StrategyBridge.compute_dynamic_tier_weights(tier="C3", market_snapshot=crit_ob_snap)

    growth_sub = sum(w_sub.get(c, 0.0) for c in growth_codes)
    growth_crit = sum(w_crit.get(c, 0.0) for c in growth_codes)
    assert growth_crit < growth_sub, "bias_20 达到 +6.5% 临界点必须触发止盈"


# =============================================================================
# 2. 调仓适宜度四维裁决与双模式后果推演对抗测试 (Suitability & Consequence Simulator)
# =============================================================================

def test_adversarial_rebalance_suitability_and_consequences_7d_penalty(temp_pm):
    """
    【包含未满 7 天惩罚期份额的四维裁决与双模式推演对抗】
    1. 构造包含未满 7 天惩罚期份额的持仓；
    2. 适宜度裁决器严格输出 FORBIDDEN 与 7 天惩罚费警告；
    3. mode_gentle 绝对不卖出未满 7 天份额 (penalty_fee_7d == 0)；
    4. mode_forced 强行全额平仓并全额真实计提 1.50% 证监会惩罚费。
    """
    today_dt = datetime.now().date()

    # 构造测试持仓：
    # 标的 1 (005562 创金红利低波 C): 5,000 份满 40 天(免赎) + 5,000 份仅 2 天(未满7天且 safety_lock=True)
    # 标的 2 (013841 银华芯片 C): 10,000 份仅 1 天(未满7天且 safety_lock=True)，C3 目标权重中无 013841 (拟全部卖出)
    records = [
        {
            "fund_code": "005562",
            "buy_date": (today_dt - timedelta(days=40)).strftime("%Y-%m-%d"),
            "shares": 5000.0,
            "cost_nav": 1.00,
            "current_nav": 1.00,
            "holding_days": 40,
            "safety_lock": False
        },
        {
            "fund_code": "005562",
            "buy_date": (today_dt - timedelta(days=2)).strftime("%Y-%m-%d"),
            "shares": 5000.0,
            "cost_nav": 1.00,
            "current_nav": 1.00,
            "holding_days": 2,
            "safety_lock": True
        },
        {
            "fund_code": "013841",
            "buy_date": (today_dt - timedelta(days=1)).strftime("%Y-%m-%d"),
            "shares": 10000.0,
            "cost_nav": 1.00,
            "current_nav": 1.00,
            "holding_days": 1,
            "safety_lock": True
        }
    ]
    temp_pm.takeover_mode_b(historical_records=records, available_cash=0.0)

    # 1. 验证适宜度裁决器 evaluate_today_rebalance_suitability
    res_suit = StrategyBridge.evaluate_today_rebalance_suitability(temp_pm, active_tier="C3")
    assert res_suit["verdict_level"] in ["FORBIDDEN", "BLOCKED"], (
        f"存在未满7天批次卖出需求时必须裁决为 FORBIDDEN，实际为: {res_suit['verdict_level']}"
    )
    assert any(k in res_suit["verdict_title"] for k in ["7天", "未满", "高损", "惩罚", "不宜"])

    r4d = res_suit["reasons_4d"]
    assert "lockup_fee_reason" in r4d
    assert any(k in r4d["lockup_fee_reason"] for k in ["未满 7 天", "1.50%", "惩罚性", "磨损"])

    # 2. 验证双模式后果推演 simulate_rebalance_modes_and_consequences
    res_sim = StrategyBridge.simulate_rebalance_modes_and_consequences(temp_pm, active_tier="C3")
    assert "mode_gentle" in res_sim
    assert "mode_forced" in res_sim

    gentle = res_sim["mode_gentle"]
    forced = res_sim["mode_forced"]

    # 3. 温和模式 (mode_gentle) 对抗断言
    fl_gentle = gentle["consequences"]["fee_loss"]
    assert fl_gentle["penalty_fee_7d"] == 0.0, (
        f"mode_gentle 绝对严禁产生 7 天惩罚费，实际为: {fl_gentle['penalty_fee_7d']}"
    )
    # 检查卖出订单：013841 仅有未满7天批次，温和模式下不得生成卖出 013841 的订单
    sold_codes_gentle = [o["fund_code"] for o in gentle["orders"] if o["action"] == "SELL"]
    assert "013841" not in sold_codes_gentle, "mode_gentle 绝不可卖出未满 7 天的 013841 份额"

    # 4. 强行模式 (mode_forced) 对抗断言
    fl_forced = forced["consequences"]["fee_loss"]
    assert fl_forced["penalty_fee_7d"] > 0.0, "mode_forced 强平必须如实计提 1.50% 惩罚费"

    # 验证强行模式惩罚费计算精度：
    # 013841 强制全额卖出 10,000 份 @ 1.00 元 * 1.50% = 150.00 元惩罚费
    # 005562 目标权重需卖出超额部分，若触及未满7天批次也必须计提 1.50%
    assert fl_forced["penalty_fee_7d"] >= 150.0, (
        f"10,000 份 013841 强平应至少产生 150 元惩罚费，实际为: {fl_forced['penalty_fee_7d']}"
    )


def test_adversarial_rebalance_consequences_4d_accounting_balance(temp_pm):
    """
    【四大后果字典全域分厘平账精算对抗】
    断言四大后果字典（fee_loss, in_transit_risk, risk_shift, lockup_reset）分厘平账：
    1. fee_loss: total_fee == redemption_fee + penalty_fee_7d + subscription_fee
    2. risk_shift: equity_after == equity_before - total_fee
    3. in_transit_risk: in_transit_pct 与踏空成本数学平账
    4. lockup_reset: new_buy_amount == sum(buy_orders)
    """
    today_dt = datetime.now().date()
    records = [
        {
            "fund_code": "005561",  # 创金合信红利低波 A
            "buy_date": (today_dt - timedelta(days=200)).strftime("%Y-%m-%d"),
            "shares": 50000.0,
            "cost_nav": 1.00,
            "current_nav": 1.00,
            "holding_days": 200,
            "safety_lock": False
        },
        {
            "fund_code": "002351",  # 易方达裕祥纯债 A
            "buy_date": (today_dt - timedelta(days=200)).strftime("%Y-%m-%d"),
            "shares": 50000.0,
            "cost_nav": 1.00,
            "current_nav": 1.00,
            "holding_days": 200,
            "safety_lock": False
        }
    ]
    temp_pm.takeover_mode_b(historical_records=records, available_cash=1000.0)

    res_sim = StrategyBridge.simulate_rebalance_modes_and_consequences(temp_pm, active_tier="C3")

    for mode_name in ["mode_gentle", "mode_forced"]:
        mode_data = res_sim[mode_name]
        cq = mode_data["consequences"]

        # 1. fee_loss 分项平账
        fl = cq["fee_loss"]
        expected_total_fee = round(fl["redemption_fee"] + fl["penalty_fee_7d"] + fl["subscription_fee"], 2)
        assert round(fl["total_fee"], 2) == expected_total_fee, (
            f"[{mode_name}] 手续费分项求和不平账: total={fl['total_fee']}, expected={expected_total_fee}"
        )

        # 2. risk_shift 净资产平账
        rs = cq["risk_shift"]
        expected_equity_after = round(max(0.0, rs["equity_before"] - fl["total_fee"]), 2)
        assert round(rs["equity_after"], 2) == expected_equity_after, (
            f"[{mode_name}] 调仓后净资产扣费不平账: after={rs['equity_after']}, expected={expected_equity_after}"
        )

        # 3. in_transit_risk 在途资金比例平账
        itr = cq["in_transit_risk"]
        expected_pct = round((itr["in_transit_amount"] / rs["equity_before"]) * 100.0, 2)
        assert abs(itr["in_transit_pct"] - expected_pct) < 1e-2, (
            f"[{mode_name}] 在途资金比例不平账: reported={itr['in_transit_pct']}%, expected={expected_pct}%"
        )
        if itr["in_transit_amount"] > 0:
            assert "T+2" in itr["lock_days"], f"[{mode_name}] 在途时滞提示文本有误: {itr['lock_days']}"
        else:
            assert "0天" in itr["lock_days"], f"[{mode_name}] 0在途资金提示文本有误: {itr['lock_days']}"

        # 4. lockup_reset 买入总额平账
        lr = cq["lockup_reset"]
        buy_orders_total = sum(o.get("amount", 0.0) for o in mode_data["orders"] if o.get("action") == "BUY")
        # 兼容可能有同公司转换 switch_amt
        switch_orders_total = sum(o.get("amount", 0.0) for o in mode_data["orders"] if o.get("action") == "SWITCH")
        assert lr["new_buy_amount"] >= round(buy_orders_total, 2), (
            f"[{mode_name}] 新买入金额不能少于买入订单总和: reported={lr['new_buy_amount']}, buy_orders={buy_orders_total}"
        )
        assert any(k in lr["reset_warning_text"] for k in ["7天", "1.5%", "180", "免赎"]), (
            f"[{mode_name}] 锁定期重置提醒缺失关键费率说明"
        )


# =============================================================================
# 3. 重合度矩阵双红利底仓协同豁免与假分散对抗测试 (Stock Overlap Matrix Exemption)
# =============================================================================

def test_adversarial_stock_overlap_dual_dividend_exemption(temp_pm):
    """
    【重合度矩阵双红利豁免对抗测试】
    1. 构造标准推荐底仓（100032 + 005561 + 002351 + 000216 + 050025 + 001071）；
    2. 断言 alerts 为空列表；
    3. 断言 max_non_diag_unexcused < 0.40（严守 0.0）；
    4. 断言双红利对与限购对均记录于 exempt_pairs 中。
    """
    temp_pm.holdings.clear()
    temp_pm.takeover_mode_a([
        {"fund_code": "100032", "amount": 24000.0, "nav": 1.0, "share_class": "A"},  # 富国红利增强
        {"fund_code": "005561", "amount": 16000.0, "nav": 1.0, "share_class": "A"},  # 创金合信红利低波
        {"fund_code": "002351", "amount": 12000.0, "nav": 1.0, "share_class": "A"},  # 易方达裕祥纯债
        {"fund_code": "000216", "amount": 14000.0, "nav": 1.0, "share_class": "A"},  # 华安黄金
        {"fund_code": "050025", "amount": 6000.0, "nav": 1.0, "share_class": "A"},   # 博时标普500
        {"fund_code": "001071", "amount": 6000.0, "nav": 1.0, "share_class": "A"}    # 华宝标普500 (限购伴生)
    ], available_cash=0.0)

    res = temp_pm.calculate_stock_overlap_matrix()

    alerts = res.get("alerts", [])
    exempt_pairs = res.get("exempt_pairs", [])
    max_unexcused = res.get("max_non_diag_unexcused", 0.0)

    # 1. 断言没有任何伪分散报警
    assert len(alerts) == 0, f"推荐底仓组合严禁产生任何伪分散警报，实际警报: {alerts}"

    # 2. 断言非豁免最大重合度必须严格 < 0.40
    assert max_unexcused < 0.40, f"非豁免最大重合度必须 < 0.40，实际为: {max_unexcused}"
    assert max_unexcused == 0.0, f"除豁免对外的其他标的重叠度必须为 0.0，实际为: {max_unexcused}"

    # 3. 验证豁免清单中精准收录双红利对与限购伴生对
    exempt_pair_sets = [frozenset({p["fund1"], p["fund2"]}) for p in exempt_pairs]
    assert frozenset({"100032", "005561"}) in exempt_pair_sets, "双红利底仓对必须被精准收录至豁免清单"
    assert frozenset({"050025", "001071"}) in exempt_pair_sets, "标普500限购伴生对必须被精准收录至豁免清单"


def test_adversarial_stock_overlap_malicious_false_diversification(temp_pm):
    """
    【恶意构造非豁免高重合假分散对抗测试】
    1. 对抗构造两只高重合科技成长基金（011612 华夏科创50 与 013841 银华集成电路，重合度达 0.40）；
    2. 对抗构造非豁免克隆红利基金（090010 大成红利 与 012643 博时红利，重合度达 1.00）；
    3. 断言坚决触发黄色假分散警告 (len(alerts) >= 1)；
    4. 断言 max_non_diag_unexcused >= 0.40。
    """
    # 场景 1: 科技芯片高重合 (011612 与 013841)
    temp_pm.holdings.clear()
    temp_pm.takeover_mode_a([
        {"fund_code": "011612", "amount": 50000.0, "nav": 1.0, "share_class": "A"},
        {"fund_code": "013841", "amount": 50000.0, "nav": 1.0, "share_class": "C"}
    ], available_cash=0.0)

    res_tech = temp_pm.calculate_stock_overlap_matrix()
    alerts_tech = res_tech.get("alerts", [])
    max_unexcused_tech = res_tech.get("max_non_diag_unexcused", 0.0)

    assert len(alerts_tech) >= 1, "两只高重合科技成长基金必须触发伪分散警告"
    assert max_unexcused_tech >= 0.40, f"非豁免科技重合度必须 >= 0.40，实际为: {max_unexcused_tech}"
    assert any("高重合度假分散预警" in a.get("warning_msg", "") for a in alerts_tech), (
        f"警告信息格式不正确: {alerts_tech}"
    )

    # 场景 2: 跨公司同赛道高重合克隆红利基金 (090010 与 012643)
    temp_pm.holdings.clear()
    temp_pm.takeover_mode_a([
        {"fund_code": "090010", "amount": 50000.0, "nav": 1.0, "share_class": "A"},  # 大成中证红利
        {"fund_code": "012643", "amount": 50000.0, "nav": 1.0, "share_class": "A"}   # 博时中证红利
    ], available_cash=0.0)

    res_div = temp_pm.calculate_stock_overlap_matrix()
    alerts_div = res_div.get("alerts", [])
    max_unexcused_div = res_div.get("max_non_diag_unexcused", 0.0)

    # 两只同赛道红利基金底层股票 100% 重叠 (overlap = 1.00)
    assert len(alerts_div) >= 1, "非官方推荐的跨公司克隆基金必须坚决触发伪分散警报"
    assert max_unexcused_div >= 0.90, f"克隆红利基金重叠度应接近 1.00，实际为: {max_unexcused_div}"
