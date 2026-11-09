import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import pandas as pd
import numpy as np
from AGY2_FundAdvisory.strategy_bridge import StrategyBridge

def test_tiers_and_weekends():
    print("=== Testing All Tiers (C1~C5) at 2024-09-18 ===")
    for tier in ["C1", "C2", "C3", "C4", "C5"]:
        res = StrategyBridge.run_historical_time_machine_backtest(target_date="2024-09-18", tier=tier, capital=50000.0)
        c_df = res["curve_df"]
        nan_cnt = c_df.isna().sum().sum()
        kpi_all = res["kpi_all"]
        print(f"Tier {tier}: rows={len(c_df)}, NaNs={nan_cnt}, weights={res['weights_at_t']}")
        print(f"         ret={kpi_all['net_return_pct']:+.2f}%, h300={kpi_all['h300_return_pct']:+.2f}%, alpha={kpi_all['alpha_vs_h300']:+.2f}%")
        assert nan_cnt == 0, f"NaNs found in Tier {tier}"

    print("\n=== Testing Weekend & Holiday Dates ===")
    # 2024-09-15 was Sunday (Mid-Autumn Festival weekend)
    res_sun = StrategyBridge.run_historical_time_machine_backtest(target_date="2024-09-15", tier="C3")
    print(f"Sunday 2024-09-15: start_date in curve={res_sun['curve_df']['date'].iloc[0]}, rows={len(res_sun['curve_df'])}")
    assert res_sun["curve_df"].isna().sum().sum() == 0

    # 2021-02-14 was Sunday (Spring Festival Golden Week)
    res_hol = StrategyBridge.run_historical_time_machine_backtest(target_date="2021-02-14", tier="C3")
    print(f"Spring Festival 2021-02-14: start_date in curve={res_hol['curve_df']['date'].iloc[0]}, rows={len(res_hol['curve_df'])}")
    assert res_hol["curve_df"].isna().sum().sum() == 0

    print("\n=== Testing Capital Extremes ===")
    for cap in [10.0, 500.0, 10000000.0]:
        res_cap = StrategyBridge.run_historical_time_machine_backtest(target_date="2024-09-18", tier="C3", capital=cap)
        assert res_cap["capital"] == cap
        assert res_cap["curve_df"].isna().sum().sum() == 0

    print("\n[SUCCESS] Tiers, weekends, and capital extremes passed.")

if __name__ == "__main__":
    test_tiers_and_weekends()
