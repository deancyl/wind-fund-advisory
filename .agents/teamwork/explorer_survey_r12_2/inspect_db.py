import duckdb
from pathlib import Path
import pandas as pd

ws = Path(__file__).resolve().parent.parent.parent.parent
db_path = ws / "data" / "storage.duckdb"
print("DB exists:", db_path.exists())
if db_path.exists():
    con = duckdb.connect(str(db_path), read_only=True)
    tables = con.execute("SHOW TABLES").fetchall()
    print("Tables:", tables)
    for t in tables:
        tname = t[0]
        cnt = con.execute(f"SELECT count(*) FROM {tname}").fetchone()[0]
        print(f"Table {tname}: {cnt} rows")
        cols = con.execute(f"DESCRIBE {tname}").fetchall()
        print(f"  Columns: {[c[0] for c in cols]}")

mat_p = ws / "data" / "processed" / "aligned_matrix_total_return.parquet"
if mat_p.exists():
    df_mat = pd.read_parquet(mat_p)
    print("Matrix shape:", df_mat.shape)
    print("Matrix columns:", list(df_mat.columns))
    print("Matrix head date:", df_mat['date'].iloc[0], "tail date:", df_mat['date'].iloc[-1])
