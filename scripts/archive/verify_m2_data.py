import pandas as pd
import os
import sys

def main():
    print("=== 1. Checking data/macro/bond_zh_us_rate.parquet ===")
    bond_path = "data/macro/bond_zh_us_rate.parquet"
    if os.path.exists(bond_path):
        df_b = pd.read_parquet(bond_path)
        print(f"Shape: {df_b.shape}")
        print("Columns:", list(df_b.columns))
        print("Tail 3 rows:")
        print(df_b.tail(3)[["date", "cn_yield_10y", "us_yield_10y", "cn_us_spread_10y"]])
        last_date = df_b["date"].iloc[-1]
        print(f"Latest bond date: {last_date}")
    else:
        print("bond_zh_us_rate.parquet NOT FOUND")

    print("\n=== 2. Checking data/global/fx_rates.parquet ===")
    fx_path = "data/global/fx_rates.parquet"
    if os.path.exists(fx_path):
        df_f = pd.read_parquet(fx_path)
        print(f"Shape: {df_f.shape}")
        print("Columns:", list(df_f.columns))
        print("Tail 3 rows:")
        print(df_f.tail(3)[["date", "usd_cnh", "usd_cny", "cnh_cny_spread"]])
        last_fx_date = df_f["date"].iloc[-1]
        print(f"Latest fx date: {last_fx_date}")
    else:
        print("fx_rates.parquet NOT FOUND")

if __name__ == "__main__":
    main()
