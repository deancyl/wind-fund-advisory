import pandas as pd
from pathlib import Path

workspace = Path(r"d:\Google\Workspace\Wind")

# Check csindex_H30269.parquet
p_h30269 = workspace / "data/processed/csindex_H30269.parquet"
if p_h30269.exists():
    df = pd.read_parquet(p_h30269)
    print("csindex_H30269 columns:", df.columns.tolist())
    print("csindex_H30269 shape:", df.shape)
    print("csindex_H30269 tail 2:")
    print(df.tail(2))
else:
    print("csindex_H30269 does not exist")

# Check 000922.SH.parquet
p_000922 = workspace / "data/processed/indices/000922.SH.parquet"
if p_000922.exists():
    df = pd.read_parquet(p_000922)
    print("000922.SH columns:", df.columns.tolist())
    print("000922.SH shape:", df.shape)
    print("000922.SH tail 2:")
    print(df.tail(2))
else:
    print("000922.SH does not exist")

# Check csindex_H00922.parquet
p_h00922 = workspace / "data/processed/csindex_H00922.parquet"
if p_h00922.exists():
    df = pd.read_parquet(p_h00922)
    print("csindex_H00922 columns:", df.columns.tolist())
    print("csindex_H00922 shape:", df.shape)
    print("csindex_H00922 tail 2:")
    print(df.tail(2))

# Check aligned_matrix_total_return.parquet
p_mat = workspace / "data/processed/aligned_matrix_total_return.parquet"
if p_mat.exists():
    df = pd.read_parquet(p_mat)
    print("aligned_matrix_total_return columns:", df.columns.tolist()[:15])
    print("aligned_matrix_total_return shape:", df.shape)
    for c in ["H00922", "H30269", "000922"]:
        if c in df.columns:
            print(f"Col {c} in mat, tail:", df[c].tail(2).values)
