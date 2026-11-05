import duckdb
from pathlib import Path

workspace = Path(r"d:\Google\Workspace\Wind")
db_p = workspace / "data/storage.duckdb"

if db_p.exists():
    con = duckdb.connect(str(db_p), read_only=True)
    tables = con.execute("SHOW TABLES").fetchall()
    print("DuckDB tables:", tables)
    for t in tables:
        t_name = t[0]
        try:
            sample = con.execute(f"SELECT * FROM {t_name} LIMIT 3").df()
            print(f"Table {t_name} sample columns:", sample.columns.tolist())
            # check if 000922 or H30269 in there
            for col in sample.columns:
                if "code" in col.lower() or "symbol" in col.lower():
                    matches = con.execute(f"SELECT DISTINCT {col} FROM {t_name} WHERE {col} LIKE '%922%' OR {col} LIKE '%30269%'").fetchall()
                    if matches:
                        print(f"  In {t_name}.{col}: matches:", matches)
        except Exception as e:
            print(f"  Error reading {t_name}: {e}")
    con.close()
else:
    print("storage.duckdb not found")
