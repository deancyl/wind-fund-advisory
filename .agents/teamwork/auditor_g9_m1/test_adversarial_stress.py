import sys
import os
from pathlib import Path
import numpy as np

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent.parent
AGY2_DIR = WORKSPACE_ROOT / "AGY2_FundAdvisory"
if str(AGY2_DIR) not in sys.path:
    sys.path.insert(0, str(AGY2_DIR))
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from advisory_engine import OnlineHeuristicFactorEvolver, ActiveRiskSentry, OpportunityRadarEngine, RADAR_SECTOR_CATALOG
from data_loader import fetch_realtime_market_news_and_catalysts, DataLoader

def test_stress_evolver():
    print("Testing OnlineHeuristicFactorEvolver...")
    evolver = OnlineHeuristicFactorEvolver(population_size=16, generations=5, random_seed=42)
    res = evolver.get_60d_rolling_nav_and_trajectory()
    
    assert "nav_dynamic" in res
    assert "nav_static" in res
    assert "trajectory" in res
    assert len(res["nav_dynamic"]) == 60, f"Expected 60 points, got {len(res['nav_dynamic'])}"
    assert len(res["nav_static"]) == 60, f"Expected 60 points, got {len(res['nav_static'])}"
    assert len(res["trajectory"]) == 60, f"Expected 60 points in trajectory, got {len(res['trajectory'])}"
    
    # Check that trajectory weights are not identical linear increments
    traj = res["trajectory"]
    w_vals = [t["valuation"] for t in traj]
    # In old code: lam = (t+1)/60, so weights were linear with constant second difference = 0
    diffs = np.diff(w_vals)
    unique_diffs = len(np.unique(np.round(diffs, 5)))
    print(f"Trajectory unique weight step diffs: {unique_diffs}")
    assert unique_diffs > 1, "Trajectory appears artificially linear!"

    # Check weights satisfy constraints
    for t in traj:
        w = [t["valuation"], t["momentum"], t["snr"], t["anti_crowding"]]
        assert all(x >= 0.0499 for x in w), f"Weight constraint violated: {w}"
        assert abs(sum(w) - 1.0) < 1e-3, f"Sum of weights != 1: {sum(w)}"

    print("[PASS] OnlineHeuristicFactorEvolver stress test passed.")

def test_stress_sentry():
    print("Testing ActiveRiskSentry...")
    sentry = ActiveRiskSentry()

    # 1. Unknown AUM fund
    snapshot_unknown = {
        "holdings": [
            {"code": "999999", "name": "未知代码迷你基", "shares": 10000, "nav": 1.0, "market_value": 10000.0, "category": "其他权益资产"}
        ],
        "available_cash": 0.0,
        "portfolio_pnl_pct": 0.0,
        "target_risk_tier": "C3"
    }
    rep_unknown = sentry.inspect_portfolio(snapshot_unknown["holdings"], snapshot=snapshot_unknown, fund_metadata={})
    verification_alerts = [a for a in rep_unknown["alerts"] if a.get("aum_status") == "PENDING_VERIFICATION"]
    assert len(verification_alerts) == 1, "Expected PENDING_VERIFICATION alert for unknown fund"
    assert verification_alerts[0]["level"] == "yellow"
    assert "规模待核验" in verification_alerts[0]["title"]
    print("[PASS] ActiveRiskSentry PENDING_VERIFICATION verified.")

    # 2. Liquidation danger AUM (<0.50亿)
    snapshot_mini = {
        "holdings": [
            {"code": "888888", "name": "微型基", "shares": 10000, "nav": 1.0, "market_value": 10000.0, "category": "其他权益资产"}
        ],
        "available_cash": 0.0,
        "portfolio_pnl_pct": 0.0,
        "target_risk_tier": "C3"
    }
    rep_mini = sentry.inspect_portfolio(snapshot_mini["holdings"], snapshot=snapshot_mini, fund_metadata={"888888": {"aum_billion": 0.25}})
    danger_alerts = [a for a in rep_mini["alerts"] if a.get("aum_status") == "LIQUIDATION_DANGER"]
    assert len(danger_alerts) == 1, "Expected LIQUIDATION_DANGER alert for mini fund"
    assert danger_alerts[0]["level"] == "red"
    assert "清盘警戒线" in danger_alerts[0]["title"]
    print("[PASS] ActiveRiskSentry LIQUIDATION_DANGER verified.")

    # 3. Investor suitability: C1 Conservative holding high equity
    snapshot_c1 = {
        "holdings": [
            {"code": "008888", "name": "华夏芯片", "shares": 50000, "nav": 1.0, "market_value": 50000.0, "category": "科技成长进攻"}
        ],
        "available_cash": 10000.0,
        "portfolio_pnl_pct": 0.0,
        "investor_risk_tier": "C1"
    }
    rep_c1 = sentry.inspect_portfolio(snapshot_c1["holdings"], snapshot=snapshot_c1, investor_risk_tier="C1")
    suitability_alerts = [a for a in rep_c1["alerts"] if a.get("dimension") == "投资者适当性"]
    assert len(suitability_alerts) >= 1, "Expected suitability alert for C1 over-equity"
    print("[PASS] ActiveRiskSentry Suitability over-equity verified.")

    # 4. Intraday cushion shock
    snapshot_shock = {
        "holdings": [
            {"code": "008888", "name": "华夏芯片", "shares": 50000, "nav": 1.0, "market_value": 50000.0, "category": "科技成长进攻", "pnl_pct": 10.0}
        ],
        "available_cash": 10000.0,
        "portfolio_pnl_pct": 5.0,
        "cushion_yuan": 5000.0,
        "fund_quotes": {
            "008888": {"gszzl": -3.5}
        },
        "target_risk_tier": "C3"
    }
    rep_shock = sentry.inspect_portfolio(snapshot_shock["holdings"], snapshot=snapshot_shock)
    cushion_alerts = [a for a in rep_shock["alerts"] if a.get("dimension") == "盘中异动安全垫传导"]
    assert len(cushion_alerts) >= 1, "Expected cushion shock alert"
    print("[PASS] ActiveRiskSentry Intraday cushion shock verified.")

def test_stress_radar():
    print("Testing OpportunityRadarEngine...")
    radar = OpportunityRadarEngine()
    meta = RADAR_SECTOR_CATALOG.get("semiconductor", {})
    ev = radar.evaluate_sector("semiconductor", meta, realtime_quotes={"semiconductor": {"change_pct": 2.5, "point": 1250.0}})
    
    assert "core_logic" in ev
    assert "量化因果链" in ev["core_logic"]
    assert "vol_20" in ev
    assert "mdd_20" in ev
    assert "sub_scores" in ev
    print(f"Radar evaluation: core_logic={ev['core_logic']}, vol_20={ev['vol_20']}, mdd_20={ev['mdd_20']}")
    print("[PASS] OpportunityRadarEngine stress test passed.")

def test_stress_news_timestamp():
    print("Testing news timestamp protection...")
    news_res = fetch_realtime_market_news_and_catalysts(force_refresh=False)
    assert "is_realtime" in news_res
    assert "source_type" in news_res
    assert "updated_at" in news_res
    print(f"News fetch: is_realtime={news_res['is_realtime']}, source_type={news_res['source_type']}, updated_at={news_res['updated_at']}")
    print("[PASS] News timestamp verification passed.")

if __name__ == '__main__':
    test_stress_evolver()
    test_stress_sentry()
    test_stress_radar()
    test_stress_news_timestamp()
    print("=== ALL ADVERSARIAL STRESS TESTS COMPLETED SUCCESSFULLY ===")
