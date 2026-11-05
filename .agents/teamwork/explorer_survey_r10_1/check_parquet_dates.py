import pandas as pd
from pathlib import Path

workspace = Path(r"d:\Google\Workspace\Wind")
for path in [
    "data/processed/indices/000685.SH.parquet",
    "data/processed/indices/000933.SH.parquet",
    "data/processed/indices/000932.SH.parquet",
    "data/processed/indices/399986.SZ.parquet",
    "data/processed/indices/000922.SH.parquet",
    "data/processed/csindex_H30269.parquet",
    "data/processed/csindex_H00922.parquet"
]:
    p = workspace / path
    if p.exists():
        df = pd.read_parquet(p)
        date_col = 'date' if 'date' in df.columns else ('日期' if '日期' in df.columns else None)
        min_d = df[date_col].min() if date_col else 'N/A'
        max_d = df[date_col].max() if date_col else 'N/A'
        print(f"{path}: shape={df.shape}, date_col={date_col}, range={min_d} to {max_d}")
    else:
        print(f"{path}: NOT FOUND")
