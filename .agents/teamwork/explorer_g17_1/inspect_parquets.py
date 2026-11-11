import pandas as pd
from pathlib import Path

root = Path("d:/Google/Workspace/Wind")

files_to_check = [
    "data/macro/bond_zh_us_rate.parquet",
    "data/macro/chinabond_yield_curve.parquet",
    "data/global/fx_rates.parquet",
    "data/global/global_indices.parquet",
    "data/global/commodities.parquet",
    "data/processed/indices/AU9999.SGE.parquet",
    "data/processed/aligned_matrix_total_return.parquet",
    "data/macro/interbank_rates.parquet",
    "data/derivatives/option_volatility.parquet"
]

print("=== PARQUET INSPECTION ===")
for rel_path in files_to_check:
    p = root / rel_path
    if not p.exists():
        print(f"\n[NOT FOUND] {rel_path}")
        continue
    try:
        df = pd.read_parquet(p)
        print(f"\n--- {rel_path} ---")
        print(f"Shape: {df.shape}")
        print(f"Columns: {list(df.columns)}")
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            print(f"Date range: {df['date'].min()} to {df['date'].max()}")
        elif isinstance(df.index, pd.DatetimeIndex):
            print(f"Index Datetime range: {df.index.min()} to {df.index.max()}")
        print("Tail 3:")
        print(df.tail(3))
    except Exception as e:
        print(f"Error reading {rel_path}: {e}")
