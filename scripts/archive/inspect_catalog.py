import pandas as pd

df = pd.read_parquet("data/master/fund_catalog.parquet")
print(f"Shape: {df.shape}")
print("Columns:", df.columns.tolist())
print(df.head(5))
