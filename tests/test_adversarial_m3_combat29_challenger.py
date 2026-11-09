"""
Adversarial Empirical Verification Suite for G15 Phase 3
Focus Areas:
1. combat_29_funds ledger in MultiLedgerManager: exact 29 holdings, market value balance (26,615.10 yuan, 0.00 discrepancy), 400 days holding preset.
2. ActiveRiskSentry Dimension 13 tail cleaner: exact 19 tail funds, 442.70 yuan recoverable cash, protection of waist/core funds.
3. Deep loss sources (#5 100032 -332.54, #6 011613 -428.48, #8 161725 -175.76 totaling -936.78 floating loss).
4. Adversarial rebalance pathways and FIFO penalty-free properties.
"""

import json
from pathlib import Path
import pytest
from AGY2_FundAdvisory.multi_ledger_manager import MultiLedgerManager
from AGY2_FundAdvisory.advisory_engine import ActiveRiskSentry
from AGY2_FundAdvisory.portfolio_manager import PortfolioManager


@pytest.fixture
def combat_pm():
    """获取 combat_29_funds 组合管理器实例"""
    mlm = MultiLedgerManager.get_instance()
    return mlm.get_pm("combat_29_funds")


@pytest.fixture
def combat_json():
    """读取 combat_29_funds 底层持久化 JSON 数据"""
    json_path = Path("data/ledgers/combat_29_funds.json")
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_combat_29_ledger_meta_and_holdings_count(combat_pm, combat_json):
    """验证 combat_29_funds 元数据与持仓总数严格为 29 只"""
    mlm = MultiLedgerManager.get_instance()
    meta = mlm.get_ledger_meta("combat_29_funds")
    assert meta is not None, "combat_29_funds 元数据必须已注册于 ledgers_index.json"
    assert meta.get("default_tier") == "C3", "默认风险等级应为 C3"

    assert len(combat_pm.holdings) == 29, f"PM 持仓必须严格为 29 只基金，实际为 {len(combat_pm.holdings)}"
    assert len(combat_json["holdings"]) == 29, f"JSON 持仓必须严格为 29 只基金，实际为 {len(combat_json['holdings'])}"


def test_combat_29_funds_exact_market_value_accounting(combat_pm, combat_json):
    """
    实证核验账本市值分厘平账：
    总市值必须严格等于 26,615.10 元，误差为 0.00 元。
    7 大核心持仓 = 25,128.29 元
    3 只腰部持仓 = 1,044.11 元
    19 只碎片尾仓 = 442.70 元
    """
    # 1. 验证 PM 运行时
    total_mv = round(sum(h.market_value for h in combat_pm.holdings.values()), 2)
    assert total_mv == 26615.10, f"PM 实际总市值 {total_mv} != 预期 26615.10 元"
    assert abs(combat_pm.total_market_value - 26615.10) < 1e-4, f"pm.total_market_value 误差不为0: {combat_pm.total_market_value}"

    # 2. 验证 JSON 持久化
    json_mv = round(sum(h["market_value"] for h in combat_json["holdings"]), 2)
    assert json_mv == 26615.10, f"JSON 实际总市值 {json_mv} != 预期 26615.10 元"

    core_codes = ["005561", "110020", "017436", "002351", "100032", "011613", "000216"]
    waist_codes = ["161725", "000217", "005827"]
    tail_codes = [
        "016634", "001053", "050025", "002352", "016441", "013841", "012832", "012769",
        "008682", "011612", "002611", "019260", "000086", "018757", "001071", "006113",
        "004854", "001595", "001551"
    ]

    assert len(core_codes) == 7
    assert len(waist_codes) == 3
    assert len(tail_codes) == 19
    all_codes = set(core_codes + waist_codes + tail_codes)
    assert len(all_codes) == 29, "三组代码并集必须无重叠且正好 29 只"
    assert set(combat_pm.holdings.keys()) == all_codes, "持仓代码集合与预期 29 只完全吻合"

    core_sum = round(sum(combat_pm.holdings[c].market_value for c in core_codes), 2)
    waist_sum = round(sum(combat_pm.holdings[c].market_value for c in waist_codes), 2)
    tail_sum = round(sum(combat_pm.holdings[c].market_value for c in tail_codes), 2)

    assert core_sum == 25128.29, f"核心仓位合计 {core_sum} != 25128.29"
    assert waist_sum == 1044.11, f"腰部仓位合计 {waist_sum} != 1044.11"
    assert tail_sum == 442.70, f"尾部仓位合计 {tail_sum} != 442.70"

    assert round(core_sum + waist_sum + tail_sum, 2) == 26615.10, "分项加总必须严格等于 26615.10"


def test_combat_29_batch_holding_days_fifo_penalty_free(combat_pm, combat_json):
    """
    实证核验持仓天数与批次：
    1. 底层 JSON 账本中全部 29 只基金批次 holding_days 均显式预置为 400 天 (>365天免赎)；
    2. PM 运行态按建仓日期 (2024-01-05) 动态重算持有天数 (>= 1000 天)，完全超越 365 天门槛；
    3. 全组合 29 只基金免惩罚可赎份额 100% 释放，safety_lock 均为 False。
    """
    # 验证底层 JSON 账本预置数据
    for h_d in combat_json["holdings"]:
        code = h_d["fund_code"]
        assert len(h_d["batches"]) >= 1
        for b in h_d["batches"]:
            assert b["holding_days"] == 400, f"JSON 中标的 {code} 预置持有天数 {b['holding_days']} != 400"
            assert b["holding_days"] >= 365, f"JSON 中标的 {code} 预置天数必须 >= 365"
            assert not b["safety_lock"]

    # 验证 PM 运行时批次与免惩罚份额
    for code, h in combat_pm.holdings.items():
        assert len(h.batches) >= 1
        for b in h.batches:
            assert b.holding_days >= 365, f"PM 标的 {code} 批次持有天数 {b.holding_days} 必须 >= 365 天"
            assert not b.safety_lock, f"PM 标的 {code} 安全锁必须为 False"

        free_sh = combat_pm.get_penalty_free_redeemable_shares(code)
        assert abs(free_sh - h.shares) < 1e-4, f"标的 {code} 可免赎份额 {free_sh} != 持有份额 {h.shares}"


def test_deep_loss_sources_exact_accounting(combat_pm, combat_json):
    """
    实证核验 3 大深套亏损源会计数据：
    #5: 100032 (富国中证红利指数增强A) 浮亏 -332.54 元
    #6: 011613 (华夏上证科创板50ETF联接C) 浮亏 -428.48 元
    #8: 161725 (招商中证白酒指数A) 浮亏 -175.76 元
    合计深套浮亏严格等于 -936.78 元。
    """
    # 1. 验证底层 JSON 原始账本（分厘不差严格等于 -936.78）
    json_targets = {h["fund_code"]: h for h in combat_json["holdings"] if h["fund_code"] in ["100032", "011613", "161725"]}
    assert json_targets["100032"]["market_value"] == 2432.90
    assert json_targets["100032"]["floating_pnl"] == -332.54
    assert json_targets["100032"]["cost_basis"] == 2765.44

    assert json_targets["011613"]["market_value"] == 2072.52
    assert json_targets["011613"]["floating_pnl"] == -428.48
    assert json_targets["011613"]["cost_basis"] == 2501.00

    assert json_targets["161725"]["market_value"] == 524.24
    assert json_targets["161725"]["floating_pnl"] == -175.76
    assert json_targets["161725"]["cost_basis"] == 700.00

    json_deep_loss_sum = round(
        json_targets["100032"]["floating_pnl"] +
        json_targets["011613"]["floating_pnl"] +
        json_targets["161725"]["floating_pnl"],
        2
    )
    assert json_deep_loss_sum == -936.78, f"JSON 账本三大深套亏损源总和 {json_deep_loss_sum} != -936.78"

    # 2. 验证 PM 运行时（经过成本单价4位小数反算重算，误差在 0.05 元以内）
    h_100032 = combat_pm.holdings["100032"]
    h_011613 = combat_pm.holdings["011613"]
    h_161725 = combat_pm.holdings["161725"]

    assert abs(h_100032.floating_pnl - (-332.54)) < 0.05
    assert abs(h_011613.floating_pnl - (-428.48)) < 0.10
    assert abs(h_161725.floating_pnl - (-175.76)) < 0.05

    pm_deep_loss_sum = round(h_100032.floating_pnl + h_011613.floating_pnl + h_161725.floating_pnl, 2)
    assert abs(pm_deep_loss_sum - (-936.78)) < 0.05, f"PM 运行时三大深套亏损源总和 {pm_deep_loss_sum} 偏离 -936.78 超过 0.05 元"


def test_activerisksentry_dimension_13_exact_detection(combat_pm):
    """
    实证核验 ActiveRiskSentry 维度 13 碎片尾仓清理预警器：
    - 精准命中 19 只碎片尾仓
    - 可回收资金精确为 442.70 元
    - 7 核心与 3 腰部（005827 124.14元, 161725 524.24元, 000217 395.73元）受保护，绝不误杀
    """
    sentry = ActiveRiskSentry()
    rep = sentry.inspect_portfolio(combat_pm.holdings)

    tail_alerts = [a for a in rep["alerts"] if a.get("dimension") == "碎片尾仓清理"]
    assert len(tail_alerts) == 1, f"必须触发且仅触发 1 项碎片尾仓清理预警，实际触发 {len(tail_alerts)}"

    alert = tail_alerts[0]
    assert alert.get("action_type") == "sweep_tail_funds"
    assert alert.get("tail_count") == 19, f"预期 19 只碎片尾仓，实际检测到 {alert.get('tail_count')}"
    assert abs(alert.get("recoverable_cash") - 442.70) < 1e-4, f"预期回收资金 442.70，实际为 {alert.get('recoverable_cash')}"

    tail_detected_codes = set(alert.get("tail_codes", []))
    assert len(tail_detected_codes) == 19

    # 腰部仓位绝对排除
    for waist_code in ["161725", "000217", "005827"]:
        assert waist_code not in tail_detected_codes, f"腰部仓位 {waist_code} 被错误标记为碎片尾仓！"

    # 核心仓位绝对排除
    for core_code in ["005561", "110020", "017436", "002351", "100032", "011613", "000216"]:
        assert core_code not in tail_detected_codes, f"核心仓位 {core_code} 被错误标记为碎片尾仓！"


def test_adversarial_holding_days_protection_in_tail_cleaner():
    """
    对抗性压力测试：
    1. 若某尾仓持有仅 20 天（未满 C类30天 或 A类365天），必须因非免赎期而被排除在 sweep_tail 之外，避免产生赎回费！
    2. 若某尾仓持有仅 3 天（<=3天），必须触发维度 1 未满7天锁仓红牌！
    """
    sentry = ActiveRiskSentry()

    # 构造未满期尾仓：001551 (C类，仅持有 20 天 < 30天)
    premature_holdings = [
        {"fund_code": "001551", "fund_name": "天弘中证500C", "market_value": 0.59, "holding_days": 20, "share_class": "C"},
        {"fund_code": "005561", "fund_name": "创金合信红利低波A", "market_value": 50000.0, "holding_days": 400, "share_class": "A"},
    ]
    rep = sentry.inspect_portfolio(premature_holdings)
    tail_alerts = [a for a in rep["alerts"] if a.get("dimension") == "碎片尾仓清理"]
    assert len(tail_alerts) == 0, "未满 30 天的 C 类尾仓严禁纳入免赎清理预警！"

    # 构造极端未满 7 天尾仓：001551 (仅持有 3 天)
    punish_holdings = [
        {"fund_code": "001551", "fund_name": "天弘中证500C", "market_value": 0.59, "holding_days": 3, "share_class": "C"},
        {"fund_code": "005561", "fund_name": "创金合信红利低波A", "market_value": 50000.0, "holding_days": 400, "share_class": "A"},
    ]
    rep_punish = sentry.inspect_portfolio(punish_holdings)
    lock_alerts = [a for a in rep_punish["alerts"] if a.get("dimension") == "未满7天锁仓"]
    assert len(lock_alerts) == 1, "持有 3 天的标的必须触发未满7天惩罚锁仓红牌！"
    tail_alerts_punish = [a for a in rep_punish["alerts"] if a.get("dimension") == "碎片尾仓清理"]
    assert len(tail_alerts_punish) == 0, "触发惩罚锁仓的标的绝不可被列入免赎清理！"


def test_sweep_tail_and_c_class_rebalance_path(combat_pm):
    """
    实证核验调仓推演路径：
    场景：sweep_tail_and_c_class，目标锚定底仓 002351
    - 卖出操作严格为 19 笔
    - 卖出总金额严格等于 442.70 元
    - 赎回费严格等于 0.00 元
    - 申购底仓（002351）金额严格等于 442.70 元，资金 100% 守恒无泄漏
    - 腰部与核心仓位零卖出
    """
    plan = combat_pm.generate_scenario_rebalance_plan({}, scenario_mode="sweep_tail_and_c_class", core_anchor_code="002351")

    assert plan["scenario_mode"] == "sweep_tail_and_c_class"
    assert len(plan["sell_actions"]) == 19, f"卖出标的数量必须严格为 19，实际为 {len(plan['sell_actions'])}"
    assert round(plan["total_sell_amount"], 2) == 442.70, f"卖出总金额必须为 442.70，实际为 {plan['total_sell_amount']}"
    assert plan["total_redemption_fee"] == 0.0, f"赎回费必须严格为 0.00 元，实际为 {plan['total_redemption_fee']}"

    # 验证买入操作
    assert len(plan["buy_actions"]) == 1, f"买入操作必须严格为 1 笔底仓增持，实际为 {len(plan['buy_actions'])}"
    buy_item = plan["buy_actions"][0]
    assert buy_item["fund_code"] == "002351", f"买入标的必须为 002351，实际为 {buy_item['fund_code']}"
    assert round(buy_item["amount"], 2) == 442.70, f"买入金额必须为 442.70，实际为 {buy_item['amount']}"

    # 资金完全守恒
    assert round(plan["total_sell_amount"], 2) == round(plan["total_buy_amount"], 2)

    # 验证卖出清单全部属于 19 只尾仓，绝无核心或腰部资产
    sell_codes = [s["fund_code"] for s in plan["sell_actions"]]
    for waist_c in ["161725", "000217", "005827"]:
        assert waist_c not in sell_codes, f"腰部资产 {waist_c} 绝不能被卖出！"
    for core_c in ["005561", "110020", "017436", "002351", "100032", "011613", "000216"]:
        assert core_c not in sell_codes, f"核心资产 {core_c} 绝不能被卖出！"


def test_adversarial_varied_anchor_sweep(combat_pm):
    """对抗性测试：改变 core_anchor_code 至 005561 或 110020，回收资金 442.70 必须准确流向指定底仓"""
    for test_anchor in ["005561", "110020"]:
        plan = combat_pm.generate_scenario_rebalance_plan({}, scenario_mode="sweep_tail_and_c_class", core_anchor_code=test_anchor)
        assert len(plan["sell_actions"]) == 19
        assert round(plan["total_sell_amount"], 2) == 442.70
        assert len(plan["buy_actions"]) == 1
        assert plan["buy_actions"][0]["fund_code"] == test_anchor
        assert round(plan["buy_actions"][0]["amount"], 2) == 442.70


def test_accounting_identity_invariance_across_all_29_funds(combat_pm):
    """
    实证核验全 29 只基金会计恒等式：
    cost_basis + floating_pnl == market_value (分厘误差 < 0.01)
    """
    total_calc_mv = 0.0
    for code, h in combat_pm.holdings.items():
        reconstructed_mv = round(h.cost_basis + h.floating_pnl, 2)
        assert abs(reconstructed_mv - round(h.market_value, 2)) <= 0.01, (
            f"标的 {code} 会计恒等式失真: cost({h.cost_basis}) + pnl({h.floating_pnl}) = {reconstructed_mv} != mv({h.market_value})"
        )
        total_calc_mv += h.market_value

    assert round(total_calc_mv, 2) == 26615.10
