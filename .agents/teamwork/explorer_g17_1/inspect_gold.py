import pandas as pd
from pathlib import Path

root = Path("d:/Google/Workspace/Wind")

df_comm = pd.read_parquet(root / "data/global/commodities.parquet")
print("=== commodities.parquet unique codes ===")
print(df_comm[['commodity_code', 'commodity_name']].drop_duplicates())

gold_rows = df_comm[df_comm['commodity_code'].str.contains('GC|AU|GOLD', case=False, na=False) | df_comm['commodity_name'].str.contains('金', na=False)]
print("\n=== Gold in commodities ===")
print(gold_rows.tail(5))

# Also check AU9999.SGE.parquet
df_au = pd.read_parquet(root / "data/processed/indices/AU9999.SGE.parquet")
print("\n=== AU9999.SGE tail 5 ===")
print(df_au.tail(5))
