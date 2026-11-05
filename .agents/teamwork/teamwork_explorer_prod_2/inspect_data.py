import duckdb
import sqlite3
import pandas as pd
from pathlib import Path

print("=== DuckDB (data/storage.duckdb) ===")
try:
    con = duckdb.connect("data/storage.duckdb", read_only=True)
    tables = con.execute("SHOW TABLES").fetchall()
    print("Tables:", tables)
    for t in tables:
        name = t[0]
        cnt = con.execute(f"SELECT count(*) FROM '{name}'").fetchone()[0]
        sample = con.execute(f"SELECT * FROM '{name}' LIMIT 2").fetchdf()
        print(f"  {name}: {cnt} rows. Columns: {list(sample.columns)}")
    con.close()
except Exception as e:
    print("DuckDB error:", e)

print("\n=== SQLite (data/wind_toolkit.db) ===")
try:
    scon = sqlite3.connect("data/wind_toolkit.db")
    cur = scon.cursor()
    stables = cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    print("Tables:", stables)
    for t in stables:
        name = t[0]
        cur.execute(f'SELECT count(*) FROM "{name}"')
        cnt = cur.fetchone()[0]
        print(f"  {name}: {cnt} rows")
    scon.close()
except Exception as e:
    print("SQLite error:", e)

print("\n=== AGY2 SQLite (AGY2_FundAdvisory/evolution.db) ===")
try:
    scon = sqlite3.connect("AGY2_FundAdvisory/evolution.db")
    cur = scon.cursor()
    stables = cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    print("Tables:", stables)
    for t in stables:
        name = t[0]
        cur.execute(f'SELECT count(*) FROM "{name}"')
        cnt = cur.fetchone()[0]
        print(f"  {name}: {cnt} rows")
    scon.close()
except Exception as e:
    print("AGY2 SQLite error:", e)

print("\n=== AGY2 SQLite (AGY2_FundAdvisory/portfolio_state.db) ===")
try:
    scon = sqlite3.connect("AGY2_FundAdvisory/portfolio_state.db")
    cur = scon.cursor()
    stables = cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    print("Tables:", stables)
    for t in stables:
        name = t[0]
        cur.execute(f'SELECT count(*) FROM "{name}"')
        cnt = cur.fetchone()[0]
        print(f"  {name}: {cnt} rows")
    scon.close()
except Exception as e:
    print("portfolio_state error:", e)

print("\n=== Matrix Parquet (data/processed/aligned_matrix_total_return.parquet) ===")
try:
    df_mat = pd.read_parquet("data/processed/aligned_matrix_total_return.parquet")
    print("Shape:", df_mat.shape)
    print("Columns:", list(df_mat.columns))
    print("Date range:", df_mat['date'].min(), "to", df_mat['date'].max())
    print("Head:\n", df_mat.head(2))
    print("Tail:\n", df_mat.tail(2))
except Exception as e:
    print("Matrix error:", e)

print("\n=== Check Indices in data/processed/indices/ ===")
indices_to_check = ["000300.SH", "000688.SH", "000905.SH", "000852.SH", "000922.SH", "518880.SH", "AU9999.SGE", "000001.SH"]
for idx in indices_to_check:
    p = Path(f"data/processed/indices/{idx}.parquet")
    if p.exists():
        df = pd.read_parquet(p)
        date_col = "date" if "date" in df.columns else df.columns[0]
        print(f"  {idx}: rows={len(df)}, columns={list(df.columns)}, range={df[date_col].min()} to {df[date_col].max()}")
    else:
        print(f"  {idx}: NOT FOUND")
