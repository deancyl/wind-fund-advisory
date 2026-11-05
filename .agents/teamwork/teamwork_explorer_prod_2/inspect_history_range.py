import pandas as pd
from pathlib import Path

print("=== 399006.SZ.parquet ===")
p_cyb = Path("data/processed/indices/399006.SZ.parquet")
if p_cyb.exists():
    df_cyb = pd.read_parquet(p_cyb)
    date_col = "date" if "date" in df_cyb.columns else df_cyb.columns[0]
    print(f"399006: rows={len(df_cyb)}, cols={list(df_cyb.columns)}, range={df_cyb[date_col].min()} to {df_cyb[date_col].max()}")

print("\n=== global_indices.parquet ===")
p_glob = Path("data/global/global_indices.parquet")
if p_glob.exists():
    df_glob = pd.read_parquet(p_glob)
    print("global_indices indices:", df_glob['index_code'].unique())
    spx = df_glob[df_glob['index_code'] == 'SPX']
    print(f"SPX: rows={len(spx)}, range={spx['date'].min()} to {spx['date'].max()}")

print("\n=== fx_rates.parquet ===")
p_fx = Path("data/global/fx_rates.parquet")
if p_fx.exists():
    df_fx = pd.read_parquet(p_fx)
    print(f"fx_rates: rows={len(df_fx)}, range={df_fx['date'].min()} to {df_fx['date'].max()}")
