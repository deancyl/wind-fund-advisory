import pandas as pd
from pathlib import Path

indices = {
    "HS300": "data/processed/indices/000300.SH.parquet",
    "ZZ500": "data/processed/indices/000905.SH.parquet",
    "ZZ1000": "data/processed/indices/000852.SH.parquet",
    "DIVIDEND": "data/processed/indices/000015.SH.parquet",
    "CYB": "data/processed/indices/399006.SZ.parquet",
    "STAR50": "data/processed/indices/000688.SH.parquet",
    "BOND_CBA": "data/processed/indices/CBA00101.CS.parquet",
    "GOLD_AU": "data/processed/indices/AU9999.SGE.parquet",
}

print("=== Date ranges of core indices ===")
dfs = {}
for k, path in indices.items():
    p = Path(path)
    if p.exists():
        df = pd.read_parquet(p)
        date_col = "date" if "date" in df.columns else df.columns[0]
        df['date'] = pd.to_datetime(df[date_col])
        dfs[k] = df
        print(f"{k:10s}: {len(df)} rows, from {df['date'].min().strftime('%Y-%m-%d')} to {df['date'].max().strftime('%Y-%m-%d')}")

# Check overlap starting from 2005
dates_2005 = dfs["HS300"][dfs["HS300"]["date"] >= "2005-01-04"]["date"]
print(f"\nTrading days since 2005-01-04 for HS300: {len(dates_2005)}")

# Check overlap starting from 2010
dates_2010 = dfs["HS300"][dfs["HS300"]["date"] >= "2010-01-04"]["date"]
print(f"Trading days since 2010-01-04 for HS300: {len(dates_2010)}")

# Check overlap starting from 2015
dates_2015 = dfs["HS300"][dfs["HS300"]["date"] >= "2015-01-05"]["date"]
print(f"Trading days since 2015-01-05 for HS300: {len(dates_2015)}")

# Check current matrix
df_mat = pd.read_parquet("data/processed/aligned_matrix_total_return.parquet")
print(f"Current aligned_matrix (2018-2026): {len(df_mat)} trading days")
