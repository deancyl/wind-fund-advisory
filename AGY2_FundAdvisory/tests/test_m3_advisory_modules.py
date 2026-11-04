# -*- coding: utf-8 -*-
"""
AGY2_FundAdvisory/tests/test_m3_advisory_modules.py
针对 Milestone 3 三大投顾核心业务模块的自动化单元测试：
1. 【🔭 全市场机会雷达】四维量化精算、14赛道覆盖、Top 3 甄选与反超买均值回归约束
2. 【🚨 主动风险预警哨】四维巡检 (FIFO <=3d / 7d / C类30d, 迷你基, 攻防线, 全通徽章)
3. 【🌊 分批建仓与智能定投算子】金额守恒不变量 (C1 + C2 + C3 == total_capital) 与定投乘数有界性
"""

import pytest
from AGY2_FundAdvisory.advisory_engine import (
    OpportunityRadarEngine,
    ActiveRiskSentry,
    SmartExecutionDCAEngine,
    RADAR_SECTOR_CATALOG,
)


def test_opportunity_radar_14_sectors_and_top3():
    """验证 14 大赛道全景扫描与 Top 3 机会甄选"""
    radar = OpportunityRadarEngine()
    assert len(RADAR_SECTOR_CATALOG) == 14, "赛道字典必须完整覆盖 14 大核心赛道"

    all_sectors = radar.scan_all_sectors()
    assert len(all_sectors) == 14, "扫描结果必须包含 14 个赛道评分"

    # 验证各项打分在合理区间 [0, 100]
    for s in all_sectors:
        assert 0.0 <= s["s_val"] <= 100.0
        assert 0.0 <= s["s_er"] <= 100.0
        assert 0.0 <= s["s_mom"] <= 100.0
        assert 0.0 <= s["s_crowd"] <= 100.0
        assert 0.0 <= s["total_score"] <= 100.0
        assert "fund" in s
        assert "code" in s["fund"]

    top3 = radar.get_top_opportunities(3)
    assert len(top3) == 3, "必须返回 Top 3 机会赛道"
    assert top3[0]["total_score"] >= top3[1]["total_score"] >= top3[2]["total_score"], "Top 3 必须降序排列"


def test_radar_anti_overbought_rule():
    """验证 GEMINI.md 规则 8：当 Bias20 > +6.0% 时触发均值回归超买折价惩罚"""
    radar = OpportunityRadarEngine()
    
    # 模拟正常状态
    meta_normal = {
        "name": "测试赛道A",
        "category": "成长",
        "index_code": "TEST",
        "default_fund": {"code": "000001", "name": "测试基金"},
        "base_val_pct": 50.0,
        "er_20": 0.5,
        "bias_20": 3.0,
        "slope_20": 10.0,
        "crowding_score": 80.0,
    }
    score_normal = radar.evaluate_sector("test_a", meta_normal)

    # 模拟短期暴涨超买状态 (Bias20 = +10.0% > +6.0%)
    meta_overbought = dict(meta_normal)
    meta_overbought["bias_20"] = 10.0
    score_overbought = radar.evaluate_sector("test_b", meta_overbought)

    # 动量得分必须被均值回归折价惩罚大幅压低
    assert score_overbought["s_mom"] < score_normal["s_mom"]
    assert score_overbought["s_mom"] <= 40.0, "暴涨超买必须受到惩罚"


def test_risk_sentry_four_dimensions():
    """验证主动风险哨四维巡检：FIFO <=3d 红色警报、7d 绿灯解锁、C类30d黄灯、迷你基排雷"""
    sentry = ActiveRiskSentry()

    holdings = [
        # 1. 持有仅 2 天的标的 (触发 <=3d 红色惩罚报警)
        {
            "code": "001184",
            "name": "易方达新益A",
            "holding_days": 2,
            "share_class": "A",
            "bias_20": 1.0,
            "batches": [{"holding_days": 2, "shares": 1000}],
        },
        # 2. 刚满 7 天脱离惩罚的标的 (触发 7d 绿灯提示)
        {
            "code": "005561",
            "name": "创金合信红利低波A",
            "holding_days": 8,
            "share_class": "A",
            "bias_20": 0.5,
            "batches": [{"holding_days": 8, "shares": 2000}],
        },
        # 3. C 类刚满 30 天 0 赎回费标的 (触发 30d 黄灯提示)
        {
            "code": "011613",
            "name": "华夏科创50联接C",
            "holding_days": 32,
            "share_class": "C",
            "bias_20": 2.0,
            "batches": [{"holding_days": 32, "shares": 3000}],
        },
        # 4. 短期暴涨超买标的 (Bias20 > +6.0%)
        {
            "code": "013841",
            "name": "银华集成电路C",
            "holding_days": 40,
            "share_class": "C",
            "bias_20": 8.5,
            "batches": [{"holding_days": 40, "shares": 1000}],
        },
    ]

    fund_metadata = {
        # 5. 迷你基清盘风险 (<0.5亿)
        "001184": {"aum_billion": 0.32},
        "005561": {"aum_billion": 15.6},
        "011613": {"aum_billion": 22.1},
        "013841": {"aum_billion": 8.0},
    }

    snapshot = {
        "c300_point": 4101.34,
        "trigger_lines": {"surge_line": 4192.0, "breakdown_line": 4034.0},
    }

    report = sentry.inspect_portfolio(holdings, snapshot, fund_metadata)
    assert not report["all_passed"], "存在风险时 all_passed 必须为 False"
    assert report["has_danger"], "存在 <=3d 和迷你基，has_danger 必须为 True"

    alert_titles = " ".join(a["title"] for a in report["alerts"])
    assert "≤3天" in alert_titles, "必须识别 <=3天 锁仓禁卖"
    assert "已满 7 天" in alert_titles, "必须识别 7天 解锁提示"
    assert "C类份额已满 30 天" in alert_titles, "必须识别 C类 30天 0赎回费"
    assert "超买" in alert_titles, "必须识别超买"
    assert "清盘警戒线" in alert_titles, "必须识别迷你基清盘风险"


def test_risk_sentry_all_passed():
    """验证健康投资组合巡检全通时，输出 all_passed=True"""
    sentry = ActiveRiskSentry()

    safe_holdings = [
        {
            "code": "005561",
            "name": "创金合信红利低波A",
            "holding_days": 60,
            "share_class": "A",
            "bias_20": 1.2,
            "batches": [{"holding_days": 60, "shares": 2000}],
        },
        {
            "code": "002351",
            "name": "易方达裕祥回报债券A",
            "holding_days": 90,
            "share_class": "A",
            "bias_20": 0.2,
            "batches": [{"holding_days": 90, "shares": 5000}],
        },
    ]

    fund_metadata = {
        "005561": {"aum_billion": 15.6},
        "002351": {"aum_billion": 280.0},
    }

    snapshot = {
        "c300_point": 4101.34,
        "trigger_lines": {"surge_line": 4192.0, "breakdown_line": 4034.0},
    }

    report = sentry.inspect_portfolio(safe_holdings, snapshot, fund_metadata)
    assert report["all_passed"] is True, "安全组合必须全通"
    assert report["has_danger"] is False
    assert report["summary"] == "主动风控巡检全通"


@pytest.mark.parametrize("total_capital", [10000.0, 191445.0, 333333.33, 500000.0, 1000000.0])
def test_smart_execution_three_step_capital_conservation(total_capital):
    """
    数学不变量测试：
    验证模式二稳健三步分批建仓算法中，三批资金之和与用户总本金严格分厘守恒！
    batch_1 + batch_2 + batch_3 == total_capital
    """
    allocations = [
        {"code": "005561", "name": "创金合信红利低波A", "weight": 0.35},
        {"code": "011612", "name": "华夏科创50A", "weight": 0.25},
        {"code": "002351", "name": "易方达裕祥回报A", "weight": 0.25},
        {"code": "000216", "name": "华安黄金易A", "weight": 0.15},
    ]

    plan = SmartExecutionDCAEngine.plan_three_step_batches(total_capital, allocations)
    batches = plan["batches"]
    assert len(batches) == 3, "必须产生三批交割规划"

    b1_amt = batches[0]["amount"]
    b2_amt = batches[1]["amount"]
    b3_amt = batches[2]["amount"]

    # 1. 批次总额守恒
    assert round(b1_amt + b2_amt + b3_amt, 2) == round(total_capital, 2), "三批总金额必须严格等于输入本金"

    # 2. 订单内部金额守恒
    for b in batches:
        sum_orders = round(sum(o["amount"] for o in b["orders"]), 2)
        assert abs(sum_orders - b["amount"]) < 1e-4, f"批次内部订单之和必须等于批次金额: {sum_orders} != {b['amount']}"


def test_smart_dca_multiplier_bounds():
    """验证模式三智能定投扣款乘数在 [0.0, 2.0] 区间内根据 ERP 和 Bias20 正确浮动"""
    allocations = [
        {"code": "005561", "name": "创金合信红利低波A", "weight": 0.50},
        {"code": "002351", "name": "易方达裕祥回报A", "weight": 0.50},
    ]

    # 1. 极度低估水下超跌期 (ERP=85%, Bias=-3.0%) -> 乘数加速吸筹 (1.5x ~ 2.0x)
    dca_low = SmartExecutionDCAEngine.plan_smart_dca(
        total_capital=120000.0,
        allocations=allocations,
        erp_percentile=85.0,
        bias_20=-3.0,
        periods=12
    )
    assert 1.50 <= dca_low["multiplier"] <= 2.00, f"极度低估超跌乘数应在 1.5~2.0，实际: {dca_low['multiplier']}"
    assert dca_low["actual_deduction"] > dca_low["base_per_period"]

    # 2. 估值适中中性期 (ERP=50%, Bias=0.0%) -> 乘数标准定投 (1.0x)
    dca_mid = SmartExecutionDCAEngine.plan_smart_dca(
        total_capital=120000.0,
        allocations=allocations,
        erp_percentile=50.0,
        bias_20=0.0,
        periods=12
    )
    assert dca_mid["multiplier"] == 1.00
    assert dca_mid["actual_deduction"] == dca_mid["base_per_period"]

    # 3. 高估过热超买期 (ERP=20%, Bias=+8.0%) -> 乘数防守微扣/暂停 (0.0x ~ 0.5x)
    dca_high = SmartExecutionDCAEngine.plan_smart_dca(
        total_capital=120000.0,
        allocations=allocations,
        erp_percentile=20.0,
        bias_20=8.0,
        periods=12
    )
    assert 0.00 <= dca_high["multiplier"] <= 0.50, f"高估超买乘数应在 0.0~0.5，实际: {dca_high['multiplier']}"
    assert dca_high["actual_deduction"] < dca_high["base_per_period"]
