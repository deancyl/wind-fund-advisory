import sys, os
sys.path.insert(0, os.path.abspath("."))

from AGY2_FundAdvisory.advisory_engine import ActiveRiskSentry
from AGY2_FundAdvisory.portfolio_manager import PortfolioManager

def test_sentry_behavior():
    pm = PortfolioManager()
    pm.load_demo_portfolio()
    sentry = ActiveRiskSentry()
    report = sentry.inspect_portfolio(pm.holdings)

    alerts = report.get("alerts", [])
    print(f"Total alerts generated: {len(alerts)}")
    dimensions = set()
    targeted_funds = set()

    for a in alerts:
        dim = a.get("dimension")
        fcode = a.get("fund_code")
        title = a.get("title")
        act = a.get("action_type")
        dimensions.add(dim)
        if fcode:
            targeted_funds.add(fcode)
        print(f"  [{a.get('level').upper()}] Dim: {dim} | Fund: {fcode} | Action: {act} | Title: {title}")

    # Check 011612
    assert "011612" in targeted_funds, "011612 was not targeted by sentry"
    alert_011612 = [a for a in alerts if a.get("fund_code") == "011612"]
    assert any("未满7天" in a.get("dimension", "") for a in alert_011612), "011612 did not get dimension 1 alert"

    # Check 011613
    assert "011613" in targeted_funds, "011613 was not targeted by sentry"
    alert_011613 = [a for a in alerts if a.get("fund_code") == "011613"]
    assert any("免赎" in a.get("dimension", "") for a in alert_011613), "011613 did not get dimension 2 alert"

    # Check 013841
    assert "013841" in targeted_funds, "013841 was not targeted by sentry"
    alert_013841 = [a for a in alerts if a.get("fund_code") == "013841"]
    assert any("深套" in a.get("dimension", "") for a in alert_013841), "013841 did not get dimension 4 alert"

    print("\nTargeted funds check: PASSED!")
    print(f"Unique dimensions covered: {dimensions}")
    assert len(dimensions) >= 4, f"Expected at least 4 dimensions triggered on demo portfolio, got {len(dimensions)}"
    print("PASS: ActiveRiskSentry behavior verified empirically on demo portfolio.")

if __name__ == "__main__":
    test_sentry_behavior()
