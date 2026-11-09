import pandas as pd
import numpy as np
import glob

print("--- Searching for parquet files containing H30269 or dividend ---")
files = glob.glob("data/**/*.parquet", recursive=True) + glob.glob("AGY2_FundAdvisory/data/**/*.parquet", recursive=True)
for f in files:
    try:
        df = pd.read_parquet(f)
        cols = [c for c in df.columns if any(k in str(c) for k in ["H30269", "30269", "H00922", "000922", "H11009", "11009"])]
        if cols:
            print(f"File: {f}, matched cols: {cols}, shape: {df.shape}")
    except Exception:
        pass

# Also inspect csindex_H30269 or similar
mat = pd.read_parquet("data/processed/aligned_matrix_total_return.parquet")
print("\n--- aligned_matrix_total_return.parquet details ---")
for col in ["H30269", "H00922", "H11009"]:
    if col in mat.columns:
        s = mat[col].dropna()
        print(f"Col: {col}")
        print(f"  First 5:\n{mat[['date', col]].head(5)}")
        print(f"  Last 5:\n{mat[['date', col]].tail(5)}")
        print(f"  Min: {s.min()}, Max: {s.max()}, start: {s.iloc[0]}, end: {s.iloc[-1]}")
