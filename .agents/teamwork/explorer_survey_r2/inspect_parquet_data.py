import pandas as pd
from pathlib import Path

root = Path("d:/Google/Workspace/Wind")

fx_p = root / "data/global/fx_rates.parquet"
if fx_p.exists():
    df_fx = pd.read_parquet(fx_p)
    print("=== fx_rates.parquet columns ===")
    print(df_fx.columns.tolist())
    print("Shape:", df_fx.shape)
    print("Tail 5:")
    print(df_fx.tail(5))
    if 'date' in df_fx.columns:
        print("Date range:", df_fx['date'].min(), "to", df_fx['date'].max())
    if 'usd_cnh' in df_fx.columns:
        print("Latest non-null usd_cnh:")
        valid = df_fx.dropna(subset=['usd_cnh'])
        if not valid.empty:
            print(valid[['date', 'usd_cnh']].tail(5))
else:
    print("fx_rates.parquet not found!")

rate_p = root / "data/macro/bond_zh_us_rate.parquet"
if rate_p.exists():
    df_rate = pd.read_parquet(rate_p)
    print("\n=== bond_zh_us_rate.parquet columns ===")
    print(df_rate.columns.tolist())
    print("Shape:", df_rate.shape)
    print("Tail 5:")
    print(df_rate.tail(5))
    if 'date' in df_rate.columns:
        print("Date range:", df_rate['date'].min(), "to", df_rate['date'].max())
    print("Non-null counts:")
    print(df_rate.notna().sum())
    print("Latest rows with cn_yield_10y & us_yield_10y:")
    cols = [c for c in ['date', 'cn_yield_10y', 'us_yield_10y', 'spread_10y'] if c in df_rate.columns]
    print(df_rate[cols].tail(10))
else:
    print("bond_zh_us_rate.parquet not found!")
