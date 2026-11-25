import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from holdout_vault import HoldoutVault
from data_loader import DataLoader
import islands.island_ensemble as ensemble_mod
import pandas as pd

def run_final_holdout():
    vault = HoldoutVault()
    curr_attempts = vault.get_holdout_attempts()
    print(f"当前盲测金库已用次数: {curr_attempts}/3 (剩余: {3 - curr_attempts})")
    
    # 策略与参数
    strat_fn = ensemble_mod.strategy_fn
    params = ensemble_mod.PARAMS
    
    # 执行第 3 次也是最后一次盲测
    print("\n🚀 正在申请执行第 3/3 次终极盲测评估 (2025-07-01 至今)...")
    res = vault.evaluate_holdout(strat_fn, params, trial_id=29)
    print("\n================== 盲测金库评测结果 ==================")
    for k, v in res.items():
        print(f"{k}: {v}")
        
    # 计算盲测区间 50/50 基准收益进行对标
    dl = DataLoader()
    df_full = dl.load_total_return_matrix()
    df_h = df_full[df_full['date'] >= pd.to_datetime('2025-07-01')].copy().reset_index(drop=True)
    bench_nav_start = df_h['BENCHMARK_50_50'].iloc[0]
    bench_nav_end = df_h['BENCHMARK_50_50'].iloc[-1]
    bench_cum = (bench_nav_end / bench_nav_start - 1.0) * 100.0
    strat_cum = (res['final_nav'] - 1.0) * 100.0
    excess = strat_cum - bench_cum
    print(f"\n盲测区间策略累计收益: {strat_cum:.2f}%")
    print(f"盲测区间 50/50 基准收益: {bench_cum:.2f}%")
    print(f"盲测区间相对超额 Alpha: {excess:+.2f}%")
    print("====================================================")

if __name__ == '__main__':
    run_final_holdout()
