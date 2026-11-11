import pandas as pd
import numpy as np
from AGY2_FundAdvisory.strategy_bridge import StrategyBridge, strategy_fn_for_tier

df = StrategyBridge.load_matrix()
target_date = "2024-09-18"
tier = "C3"

dt_target = pd.to_datetime(target_date)
df_dates = pd.to_datetime(df['date'])
hist_slice = df[df_dates <= dt_target].copy()
start_idx = len(hist_slice)

fwd_slice = df[df_dates >= dt_target].copy().reset_index(drop=True)
n_fwd = len(fwd_slice)

sub_fee_rate = 0.0012
init_nav = 1.0 * (1.0 - sub_fee_rate)

c_sales_fee_daily = 0.0040 / 250.0
cash_ret_daily = 0.018 / 250.0

# Initial weights at t=0
weights_0 = strategy_fn_for_tier(df.iloc[:start_idx], tier=tier)
asset_cols_0 = [c for c in weights_0.keys() if c in fwd_slice.columns]
curr_held_w = {c: float(weights_0[c]) for c in asset_cols_0}
w_sum = sum(curr_held_w.values())
if w_sum > 0:
    curr_held_w = {k: v / w_sum for k, v in curr_held_w.items()}

daily_navs = [init_nav]
h300_navs = [1.0]

for t in range(1, n_fwd):
    # day_ret from t-1 to t with curr_held_w
    day_ret = 0.0
    for a, w in curr_held_w.items():
        p_prev = float(fwd_slice[a].iloc[t - 1])
        p_curr = float(fwd_slice[a].iloc[t])
        r_a = (p_curr / p_prev - 1.0) if p_prev > 0 else 0.0
        day_ret += w * r_a

    eff_day_ret = 0.95 * day_ret + 0.05 * cash_ret_daily - (0.5 * c_sales_fee_daily)
    next_nav = daily_navs[-1] * (1.0 + eff_day_ret)

    # Next target weights generated at end of day t-1 or t
    # T+1 delay: at day t-1, we generate target weights that take effect at t? Or at day t we generate target weights that take effect at t+1?
    # Strict T+1: target weights evaluated at date t-1 take effect on day t.
    # At t, we evaluate target weights for t+1:
    tgt_weights = strategy_fn_for_tier(df.iloc[:start_idx + t], tier=tier)
    asset_cols = [c for c in tgt_weights.keys() if c in fwd_slice.columns]
    next_w = {c: float(tgt_weights[c]) for c in asset_cols}
    w_sum = sum(next_w.values())
    if w_sum > 0:
        next_w = {k: v / w_sum for k, v in next_w.items()}

    # Turnover friction (10 bps on turnover)
    all_keys = set(curr_held_w.keys()) | set(next_w.keys())
    turnover = sum(abs(next_w.get(k, 0.0) - curr_held_w.get(k, 0.0)) for k in all_keys) / 2.0
    friction = turnover * 0.0010 # 10 bps
    next_nav *= (1.0 - friction)

    daily_navs.append(next_nav)
    curr_held_w = next_w

    h300_prev = float(fwd_slice['H00300'].iloc[t - 1])
    h300_curr = float(fwd_slice['H00300'].iloc[t])
    h300_r = (h300_curr / h300_prev - 1.0) if h300_prev > 0 else 0.0
    h300_navs.append(h300_navs[-1] * (1.0 + h300_r))

# 3M (min(63, n_fwd-1))
idx_63 = min(63, n_fwd - 1)
cal_days = (pd.to_datetime(fwd_slice['date'].iloc[idx_63]) - dt_target).days
red_fee = 0.0035 if cal_days < 180 else 0.0015
to_pocket = daily_navs[idx_63] * (1.0 - red_fee)
ret_3m = (to_pocket - 1.0) * 100.0
h300_3m = (h300_navs[idx_63] - 1.0) * 100.0
print(f"3M Net Return: {ret_3m:.2f}%, H300: {h300_3m:.2f}%, Alpha: {ret_3m - h300_3m:.2f}%")
print(f"All Net Return: {(daily_navs[-1] - 1.0)*100.0:.2f}%, H300: {(h300_navs[-1] - 1.0)*100.0:.2f}%")
