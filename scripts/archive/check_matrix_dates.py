import pandas as pd
from pathlib import Path

p = Path("data/mart/aligned_matrix_total_return.parquet")
if p.exists():
    df = pd.read_parquet(p)
    print("Columns:", list(df.columns))
    print("Start date:", df['date'].min())
    print("End date:", df['date'].max())
    print("Total rows:", len(df))
else:
    print("File not found:", p)
