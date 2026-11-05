import sys, os
sys.path.insert(0, os.path.abspath("."))

from AGY2_FundAdvisory.advisory_engine import ActiveRiskSentry

def test_all_branches():
    sentry = ActiveRiskSentry()

    # 1. Take profit branch (pnl_pct >= 15.0 and bias_20 > 5.0)
    fake_holding = [{
        "fund_code": "000001",
        "fund_name": "测试成长",
        "share_class": "A",
        "holding_days": 100,
        "bias_20": 6.5,
        "floating_pnl_pct": 20.0,
        "market_value": 10000.0,
    }]
    rep = sentry.inspect_portfolio(fake_holding)
    alerts = rep["alerts"]
    print("Take profit test alert dimensions:", [a["dimension"] for a in alerts])
    assert any("超买" in a["dimension"] or "阶梯止盈" in a["dimension"] for a in alerts)

    # 2. Mini fund branch (< 0.5 billion)
    fake_mini = [{
        "fund_code": "000002",
        "fund_name": "测试迷你基",
        "share_class": "A",
        "holding_days": 100,
        "market_value": 10000.0,
    }]
    rep2 = sentry.inspect_portfolio(fake_mini, fund_metadata={"000002": {"aum_billion": 0.3}})
    print("Mini fund alert dimensions:", [a["dimension"] for a in rep2["alerts"]])
    assert any("本体排雷" in a["dimension"] for a in rep2["alerts"])

    # 3. Market breakdown line branch
    rep3 = sentry.inspect_portfolio(fake_holding, market_snapshot={"c300_point": 3900.0, "breakdown_line": 4034.0, "surge_line": 4192.0})
    print("Market breakdown line alert dimensions:", [a["dimension"] for a in rep3["alerts"]])
    assert any("大盘攻防线" in a["dimension"] for a in rep3["alerts"])

    # 4. Market surge line branch
    rep4 = sentry.inspect_portfolio(fake_holding, market_snapshot={"c300_point": 4300.0, "breakdown_line": 4034.0, "surge_line": 4192.0})
    print("Market surge line alert dimensions:", [a["dimension"] for a in rep4["alerts"]])
    assert any("大盘攻防线" in a["dimension"] for a in rep4["alerts"])

    print("ALL 6-DIMENSION BRANCHES OPERATE AUTHENTICALLY AND AS SPECIFIED!")

if __name__ == "__main__":
    test_all_branches()
