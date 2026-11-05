import os
import sys
import json
import pytest

sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.abspath("AGY2_FundAdvisory"))

from advisory_engine import ActiveRiskSentry
from portfolio_manager import PortfolioManager, FundHolding, HoldingBatch

def test_dim1_min_days_variants():
    sentry = ActiveRiskSentry()
    # 1. min_days = 3 (<=3)
    r1 = sentry.inspect_portfolio([{"code": "001", "name": "测试A", "holding_days": 3, "market_value": 1000}])
    alerts = [a for a in r1["alerts"] if a["dimension"] == "未满7天锁仓"]
    assert len(alerts) == 1
    assert alerts[0]["level"] == "red"
    assert "≤3天" in alerts[0]["title"]
    assert alerts[0]["action_type"] == "lock_shares"

    # 2. min_days = 5 (4..6)
    r2 = sentry.inspect_portfolio([{"code": "001", "name": "测试A", "holding_days": 5, "market_value": 1000}])
    alerts = [a for a in r2["alerts"] if a["dimension"] == "未满7天锁仓"]
    assert len(alerts) == 1
    assert alerts[0]["level"] == "red"
    assert "未满7天红牌" in alerts[0]["title"]
    assert alerts[0]["action_type"] == "lock_shares"

    # 3. min_days = 7 (7..9)
    r3 = sentry.inspect_portfolio([{"code": "001", "name": "测试A", "holding_days": 7, "market_value": 1000}])
    alerts = [a for a in r3["alerts"] if a["dimension"] == "未满7天锁仓"]
    assert len(alerts) == 1
    assert alerts[0]["level"] == "green_notice"
    assert "已满 7 天" in alerts[0]["title"]
    assert alerts[0]["action_type"] == "rebalance_normal"

    # 4. min_days = 15 (>=10)
    r4 = sentry.inspect_portfolio([{"code": "001", "name": "测试A", "holding_days": 15, "market_value": 1000}])
    alerts = [a for a in r4["alerts"] if a["dimension"] == "未满7天锁仓"]
    assert len(alerts) == 0

def test_dim2_and_dim3_c_class():
    sentry = ActiveRiskSentry()
    # C class 28 days -> Dim 2 countdown
    r1 = sentry.inspect_portfolio([{"code": "011613", "name": "科创C", "share_class": "c", "holding_days": 28, "market_value": 1000}])
    d2 = [a for a in r1["alerts"] if a["dimension"] == "临免赎期倒计时"]
    assert len(d2) == 1
    assert d2[0]["level"] == "yellow"
    assert "差 2 天" in d2[0]["title"]
    assert d2[0]["action_type"] == "countdown_hold"

    # C class 35 days -> Dim 3 zero fee switch
    r2 = sentry.inspect_portfolio([{"code": "011613", "name": "科创C", "share_class": "C", "holding_days": 35, "market_value": 1000}])
    d3 = [a for a in r2["alerts"] if a["dimension"] == "C类零费率置换"]
    assert len(d3) == 1
    assert d3[0]["level"] == "yellow"
    assert "C类份额已满 30 天" in d3[0]["title"]
    assert d3[0]["action_type"] == "switch_a_class"

    # A class 28 days or 35 days -> neither Dim 2 nor Dim 3
    r3 = sentry.inspect_portfolio([{"code": "011612", "name": "科创A", "share_class": "A", "holding_days": 28, "market_value": 1000}])
    assert len([a for a in r3["alerts"] if a["dimension"] in ("临免赎期倒计时", "C类零费率置换")]) == 0

def test_dim4_profit_and_loss():
    sentry = ActiveRiskSentry()
    # Bias20 > 6%
    r1 = sentry.inspect_portfolio([{"code": "001", "name": "测试A", "bias_20": 7.5, "holding_days": 30, "market_value": 1000}])
    d4_overbought = [a for a in r1["alerts"] if a["dimension"] == "超买拥挤"]
    assert len(d4_overbought) == 1
    assert d4_overbought[0]["level"] == "red"
    assert "超买" in d4_overbought[0]["title"]
    assert d4_overbought[0]["action_type"] == "take_profit"

    # pnl >= 15% and bias_20 > 5%
    r2 = sentry.inspect_portfolio([{"code": "001", "name": "测试A", "floating_pnl_pct": 18.0, "bias_20": 5.5, "holding_days": 30, "market_value": 1000}])
    d4_tp = [a for a in r2["alerts"] if a["dimension"] == "阶梯止盈"]
    assert len(d4_tp) == 1
    assert d4_tp[0]["level"] == "yellow"
    assert d4_tp[0]["action_type"] == "take_profit"

    # pnl <= -12%
    r3 = sentry.inspect_portfolio([{"code": "013841", "name": "银华", "floating_pnl_pct": -16.19, "holding_days": 30, "market_value": 1000}])
    d4_loss = [a for a in r3["alerts"] if a["dimension"] == "深套诊断"]
    assert len(d4_loss) == 1
    assert d4_loss[0]["level"] == "yellow"
    assert d4_loss[0]["action_type"] == "deep_loss_rebalance"
    assert "深套诊断" in d4_loss[0]["title"]

def test_dim5_concentration_and_overlap():
    sentry = ActiveRiskSentry()
    holdings = [
        {"code": "001", "name": "红利1", "market_value": 4000, "category": "红利高股息", "holding_days": 30},
        {"code": "002", "name": "红利2", "market_value": 4000, "category": "红利高股息", "holding_days": 30},
        {"code": "003", "name": "固收", "market_value": 2000, "category": "纯债固收", "holding_days": 30},
    ]
    r = sentry.inspect_portfolio(holdings)
    conc = [a for a in r["alerts"] if a["dimension"] == "赛道集中度"]
    assert len(conc) == 1
    assert "80.0%" in conc[0]["title"]
    assert conc[0]["action_type"] == "rebalance_sector"

    # Overlap: 2 STAR funds
    holdings2 = [
        {"code": "011612", "name": "华夏科创50A", "market_value": 3000, "holding_days": 30},
        {"code": "011613", "name": "华夏科创50C", "market_value": 3000, "holding_days": 30},
        {"code": "001071", "name": "标普500", "market_value": 4000, "holding_days": 30},
    ]
    r2 = sentry.inspect_portfolio(holdings2)
    overlap = [a for a in r2["alerts"] if a["dimension"] == "重仓股重叠"]
    assert len(overlap) == 1
    assert overlap[0]["action_type"] == "switch_a_class"

def test_dim6_mini_fund_and_market_lines():
    sentry = ActiveRiskSentry()
    meta = {"009999": {"aum_billion": 0.28}}
    r1 = sentry.inspect_portfolio(
        [{"code": "009999", "name": "微小微基金", "holding_days": 30, "market_value": 1000}],
        fund_metadata=meta
    )
    mini = [a for a in r1["alerts"] if a["dimension"] == "本体排雷"]
    assert len(mini) == 1
    assert mini[0]["level"] == "red"
    assert "清盘警戒线" in mini[0]["title"]
    assert mini[0]["action_type"] == "replace_fund"

    # Market breakdown line
    snap_down = {"c300_point": 3950.0, "trigger_lines": {"surge_line": 4200.0, "breakdown_line": 4050.0}}
    r2 = sentry.inspect_portfolio([{"code": "001", "name": "基金A", "holding_days": 30, "market_value": 1000}], market_snapshot=snap_down)
    down = [a for a in r2["alerts"] if a["dimension"] == "大盘攻防线"]
    assert len(down) == 1
    assert down[0]["level"] == "red"
    assert "跌破防守底线" in down[0]["title"]
    assert down[0]["action_type"] == "defense_mode"

    # Market surge line
    snap_up = {"c300_point": 4250.0, "trigger_lines": {"surge_line": 4200.0, "breakdown_line": 4050.0}}
    r3 = sentry.inspect_portfolio([{"code": "001", "name": "基金A", "holding_days": 30, "market_value": 1000}], market_snapshot=snap_up)
    up = [a for a in r3["alerts"] if a["dimension"] == "大盘攻防线"]
    assert len(up) == 1
    assert up[0]["level"] == "green_notice"
    assert "突破进攻线" in up[0]["title"]
    assert up[0]["action_type"] == "offense_mode"

def test_robustness_with_weird_inputs():
    sentry = ActiveRiskSentry()
    # Empty holdings
    r_empty = sentry.inspect_portfolio([])
    assert r_empty["all_passed"] is True
    assert len(r_empty["alerts"]) == 0

    # Malformed objects
    weird = [
        {"code": "", "name": "", "market_value": "not_a_number"},
        {"code": "002", "batches": [{"holding_days": "invalid"}]},
        {"code": "003", "batches": [None, "str"]},
    ]
    r_weird = sentry.inspect_portfolio(weird)
    assert isinstance(r_weird, dict)
    assert "alerts" in r_weird

if __name__ == "__main__":
    test_dim1_min_days_variants()
    test_dim2_and_dim3_c_class()
    test_dim4_profit_and_loss()
    test_dim5_concentration_and_overlap()
    test_dim6_mini_fund_and_market_lines()
    test_robustness_with_weird_inputs()
    print("ALL ADVERSARIAL SENTRY TESTS PASSED!")
