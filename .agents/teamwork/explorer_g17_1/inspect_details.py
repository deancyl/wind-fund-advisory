import pandas as pd
from pathlib import Path

root = Path("d:/Google/Workspace/Wind")

# Check bond_zh_us_rate.parquet tail
df_rate = pd.read_parquet(root / "data/macro/bond_zh_us_rate.parquet")
print("=== bond_zh_us_rate.parquet tail 5 ===")
print(df_rate[['date', 'cn_yield_10y', 'us_yield_10y', 'cn_us_spread_10y']].tail(5))
# Calculate 20-day bp change
cn_10y_cur = df_rate['cn_yield_10y'].iloc[-1]
cn_10y_20d = df_rate['cn_yield_10y'].iloc[-21]
cn_20d_bp = (cn_10y_cur - cn_10y_20d) * 100.0
us_10y_cur = df_rate['us_yield_10y'].iloc[-1]
us_10y_20d = df_rate['us_yield_10y'].iloc[-21]
us_20d_bp = (us_10y_cur - us_10y_20d) * 100.0
spread_cur = df_rate['cn_us_spread_10y'].iloc[-1]
print(f"cn_yield_10y latest: {cn_10y_cur}%, 20d change: {cn_20d_bp:+.1f} bp")
print(f"us_yield_10y latest: {us_10y_cur}%, 20d change: {us_20d_bp:+.1f} bp")
print(f"cn_us_spread_10y: {spread_cur} ({spread_cur*100.0:+.1f} bp)")

# Check global_indices.parquet unique codes
df_global = pd.read_parquet(root / "data/global/global_indices.parquet")
print("\n=== global_indices.parquet unique index_code / index_name ===")
print(df_global[['index_code', 'index_name']].drop_duplicates())

# Check NASDAQ or SPX in global_indices
for code in ['IXIC', 'NDX', 'SPX', 'HSI', 'HSTECH']:
    sub = df_global[df_global['index_code'] == code]
    if not sub.empty:
        print(f"\nFound {code} in global_indices: latest date {sub['date'].max()}, close {sub['close'].iloc[-1]}, daily_return {sub['daily_return'].iloc[-1]}")

# Check AU9999 and SPX_CNY in aligned_matrix_total_return.parquet
df_mat = pd.read_parquet(root / "data/processed/aligned_matrix_total_return.parquet")
print("\n=== aligned_matrix_total_return.parquet tail 5 ===")
print(df_mat[['date', 'AU9999', 'SPX_CNY', 'H00300', 'STAR50_STITCH', 'H00922']].tail(5))
