import pandas as pd
from pathlib import Path

print("=== csindex_*.parquet in data/processed ===")
for p in sorted(Path("data/processed").glob("csindex_*.parquet")):
    df = pd.read_parquet(p)
    date_col = "date" if "date" in df.columns else df.columns[0]
    print(f"  {p.name}: rows={len(df)}, columns={list(df.columns)}, range={df[date_col].min()} to {df[date_col].max()}")

print("\n=== data/cache/fund_*.OF.csv ===")
fund_csvs = list(Path("data/cache").glob("fund_*.OF.csv"))
print(f"Total fund CSVs in data/cache: {len(fund_csvs)}")
if fund_csvs:
    sample_df = pd.read_csv(fund_csvs[0])
    print(f"  Sample {fund_csvs[0].name}: rows={len(sample_df)}, cols={list(sample_df.columns)}, range={sample_df['date'].min()} to {sample_df['date'].max()}")

print("\n=== data/mart/ ===")
for p in Path("data/mart").glob("*.parquet"):
    df = pd.read_parquet(p)
    print(f"  {p.name}: rows={len(df)}, cols={list(df.columns)}")

print("\n=== data/raw/ and data/master/ ===")
for d in ["data/raw", "data/master", "data/macro", "data/global", "data/derivatives"]:
    files = list(Path(d).glob("*.*"))
    print(f"  {d}: {len(files)} files -> {[f.name for f in files[:5]]}")
