import pandas as pd
import duckdb
from pathlib import Path

print("=== CBA00101.CS.parquet ===")
p_cba = Path("data/processed/indices/CBA00101.CS.parquet")
if p_cba.exists():
    df_cba = pd.read_parquet(p_cba)
    date_col = "date" if "date" in df_cba.columns else df_cba.columns[0]
    print(f"CBA00101: rows={len(df_cba)}, cols={list(df_cba.columns)}, range={df_cba[date_col].min()} to {df_cba[date_col].max()}")
else:
    print("CBA00101 NOT found")

print("\n=== v_winrate in DuckDB ===")
con = duckdb.connect("data/storage.duckdb", read_only=True)
df_win = con.execute("SELECT * FROM v_winrate LIMIT 10").fetchdf()
print("v_winrate count:", con.execute("SELECT count(*) FROM v_winrate").fetchone()[0])
print(df_win.head(5))
con.close()
