import duckdb
from pathlib import Path

workspace = Path(r"d:\Google\Workspace\Wind")
con = duckdb.connect(str(workspace / "data/storage.duckdb"), read_only=True)
res = con.execute("SELECT MIN(date), MAX(date), COUNT(*) FROM v_indices WHERE index_code = '000922.SH'").fetchall()
print("v_indices 000922.SH date range:", res)
con.close()
