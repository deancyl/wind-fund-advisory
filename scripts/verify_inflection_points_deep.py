import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import json
import pandas as pd
import numpy as np

from AGY2_FundAdvisory.strategy_bridge import StrategyBridge

def run_deep_check():
    dates = ["2021-02-18", "2022-04-26", "2024-09-18"]
    all_res = {}
    for d in dates:
        print(f"\n==================== DATE: {d} ====================")
        res = StrategyBridge.run_historical_time_machine_backtest(target_date=d, tier="C3", capital=100000.0)
        curve_df = res["curve_df"]
        print(f"Target Date: {res['target_date']}, Capital: {res['capital']}, Tier: {res['tier']}")
        print(f"Weights at T: {res['weights_at_t']}")
        print(f"Curve rows: {len(curve_df)}, start={curve_df['date'].iloc[0]}, end={curve_df['date'].iloc[-1]}")
        
        # Check for NaN / inf / null
        nan_counts = curve_df.isna().sum().to_dict()
        inf_counts = {col: int(np.isinf(curve_df[col]).sum()) for col in ["strategy_net_nav", "h300_nav", "benchmark_nav"]}
        print(f"NaN counts: {nan_counts}")
        print(f"Inf counts: {inf_counts}")
        assert sum(nan_counts.values()) == 0, f"Found NaNs: {nan_counts}"
        assert sum(inf_counts.values()) == 0, f"Found Infs: {inf_counts}"
        
        # Check initial nav deduction
        init_nav = curve_df["strategy_net_nav"].iloc[0]
        print(f"Initial Strategy NAV: {init_nav:.6f} (Expected 0.998800 after 12 bps subscription fee)")
        assert abs(init_nav - 0.9988) < 1e-4, f"Initial nav mismatch: {init_nav}"
        
        # Check KPIs
        for k in ["kpi_3m", "kpi_6m", "kpi_1y", "kpi_all"]:
            kpi = res.get(k)
            if kpi:
                print(f"  [{k}] days={kpi['days']}, trade_days={kpi['trade_days']}")
                print(f"       strategy_net_ret={kpi['net_return_pct']:+.2f}%, h300_ret={kpi['h300_return_pct']:+.2f}%, bm_ret={kpi['bm_return_pct']:+.2f}%")
                print(f"       alpha_vs_h300={kpi['alpha_vs_h300']:+.2f}%, strategy_mdd={kpi['mdd_pct']:.2f}%, h300_mdd={kpi['h300_mdd_pct']:.2f}%")
                print(f"       red_fee={kpi['red_fee_pct']:.2f}%, verdict={kpi['verdict']}")
            else:
                print(f"  [{k}] None")
        all_res[d] = res
    print("\n[SUCCESS] Deep inflection point check completed.")
    return all_res

if __name__ == "__main__":
    run_deep_check()
