import pandas as pd
from pathlib import Path

print("=== data/processed/funds/*.parquet ===")
for p in sorted(Path("data/processed/funds").glob("*.parquet")):
    df = pd.read_parquet(p)
    date_col = "date" if "date" in df.columns else df.columns[0]
    print(f"  {p.name}: rows={len(df)}, columns={list(df.columns)}, range={df[date_col].min()} to {df[date_col].max()}")
