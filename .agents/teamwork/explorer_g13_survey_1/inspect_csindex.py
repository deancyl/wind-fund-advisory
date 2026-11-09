import os
import pandas as pd

for p in [
    "data/processed/csindex_H30269.parquet",
    "data/processed/csindex_H11009.parquet",
    "data/processed/csindex_H00922.parquet",
    "data/processed/csindex_H00300.parquet"
]:
    if os.path.exists(p):
        df = pd.read_parquet(p)
        print(f"File {p}: shape {df.shape}, cols: {df.columns.tolist()}")
        print(df.head(2))
        print(df.tail(2))
    else:
        print(f"File {p} does NOT exist.")
