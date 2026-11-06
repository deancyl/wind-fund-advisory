import duckdb
from pathlib import Path
ws = Path(__file__).resolve().parent.parent.parent.parent
db_path = ws / "data" / "storage.duckdb"
con = duckdb.connect(str(db_path), read_only=True)

symbols = con.execute("SELECT DISTINCT symbol, fund_name FROM v_funds LIMIT 20").fetchall()
print("Sample v_funds:", symbols)

# Check specific funds like 005561, 011613, 002351, 000216
for code in ['005561', '011613', '002351', '000216', '510300']:
    res = con.execute("SELECT count(*) FROM v_funds WHERE symbol LIKE ? OR fund_code LIKE ?", (f"%{code}%", f"%{code}%")).fetchone()[0]
    print(f"Fund {code} in v_funds: {res} rows")

# Also check v_market_temperature
temp = con.execute("SELECT * FROM v_market_temperature").df()
print("Market temperature:")
print(temp.T)
