import pandas as pd
from pathlib import Path

for name in ["000015.SH", "399922.SZ", "000922.SH", "000852.SH", "000688.SH", "000016.SH", "399001.SZ", "399006.SZ"]:
    p = Path(f"data/processed/indices/{name}.parquet")
    if p.exists():
        df = pd.read_parquet(p)
        date_col = "date" if "date" in df.columns else df.columns[0]
        print(f"{name}: rows={len(df)}, range={df[date_col].min()} to {df[date_col].max()}")
    else:
        print(f"{name}: NOT FOUND")
