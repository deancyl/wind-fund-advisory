import os
import sys
import json
import sqlite3
import hashlib
from pathlib import Path

# Setup paths
root = Path(".").resolve()
sys.path.insert(0, str(root / "AGY2_FundAdvisory"))
sys.path.insert(0, str(root))

from AGY2_FundAdvisory.multi_ledger_manager import MultiLedgerManager
from AGY2_FundAdvisory.portfolio_manager import PortfolioManager

print("=== EMPIRICAL INTEGRITY TEST ON LIVE DISK & SQLITE ===")

# 1. Main live snapshot
main_json = root / "portfolio_ledger.json"
main_db = root / "portfolio_state.db"

main_json_bytes = main_json.read_bytes() if main_json.exists() else b""
main_json_hash = hashlib.sha256(main_json_bytes).hexdigest()

main_db_holdings = []
if main_db.exists():
    conn = sqlite3.connect(main_db)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT fund_code, shares, market_value FROM holdings")
        main_db_holdings = cursor.fetchall()
    except Exception as e:
        main_db_holdings = str(e)
    conn.close()

print(f"Main JSON hash before test: {main_json_hash}")
print(f"Main DB holdings before test: {len(main_db_holdings)} rows: {main_db_holdings}")

mlm = MultiLedgerManager(workspace_root=root)

# 2. Test main_live deletion protection
print("\nTesting delete protection on main_live...")
try:
    mlm.delete_ledger("main_live")
    print("FAILED: main_live deletion did NOT raise PermissionError!")
    sys.exit(1)
except PermissionError as e:
    print(f"PASSED: main_live delete blocked with: {e}")

# 3. Create a test sandbox ledger
print("\nCreating test sandbox ledger...")
test_id = mlm.create_ledger(
    name="Auditor_Empirical_Test_Ledger",
    base_cash=88888.88,
    ledger_type="sandbox",
    default_tier="C4"
)
print(f"Created ledger ID: {test_id}")

test_json = root / "data" / "ledgers" / f"{test_id}.json"
test_db = root / "data" / "ledgers" / f"{test_id}.db"

assert test_json.exists(), f"Test JSON not created at {test_json}"
print(f"PASSED: Test JSON exists at {test_json}")

# 4. Modify test ledger and save
print("\nModifying test ledger holdings and invoking save_state()...")
test_pm = mlm.get_pm(test_id)
test_pm.add_or_update_holding(
    fund_code="005561",
    shares=10000.0,
    nav=1.25,
    cost_price=1.20,
    holding_days=15,
    fund_name="创金合信红利低波A"
)
test_pm.save_state(record_snapshot=True)

# 5. Verify test DB exists and has the row
assert test_db.exists(), f"Test DB not created at {test_db}"
conn = sqlite3.connect(test_db)
cursor = conn.cursor()
cursor.execute("SELECT fund_code, shares, market_value FROM holdings")
test_rows = cursor.fetchall()
conn.close()
print(f"Test DB holdings rows: {test_rows}")
assert len(test_rows) == 1 and test_rows[0][0] == "005561", "Test DB holdings missing or incorrect!"
print("PASSED: Test DB has correct holdings row.")

# 6. Check main live JSON and main DB are 100% UNTOUCHED
print("\nVerifying Main Live JSON & DB isolation...")
new_main_json_bytes = main_json.read_bytes() if main_json.exists() else b""
new_main_json_hash = hashlib.sha256(new_main_json_bytes).hexdigest()
assert new_main_json_hash == main_json_hash, "CRITICAL ERROR: Main live JSON was modified by sandbox save!"

if main_db.exists():
    conn = sqlite3.connect(main_db)
    cursor = conn.cursor()
    cursor.execute("SELECT fund_code, shares, market_value FROM holdings")
    new_main_db_holdings = cursor.fetchall()
    conn.close()
    assert new_main_db_holdings == main_db_holdings, "CRITICAL ERROR: Main live DB was modified by sandbox save!"
print("PASSED: Main live JSON and DB are completely untouched.")

# 7. Test Clone
print("\nTesting Clone...")
clone_id = mlm.clone_ledger(test_id, "Auditor_Clone_Test")
clone_json = root / "data" / "ledgers" / f"{clone_id}.json"
clone_db = root / "data" / "ledgers" / f"{clone_id}.db"
assert clone_json.exists(), "Clone JSON does not exist!"
clone_pm = mlm.get_pm(clone_id)
assert "005561" in clone_pm.holdings
print(f"PASSED: Clone {clone_id} created with correct cloned holdings.")

# 8. Test Summary Calculation
print("\nTesting get_all_ledgers_summary()...")
summary = mlm.get_all_ledgers_summary()
print(f"Total assets: {summary['total_assets']}, Total funds: {summary['total_funds']}")
assert summary['total_assets'] > 0
assert summary['total_funds'] >= 2
assert summary['df'] is not None
print("PASSED: Summary calculated successfully.")

# 9. Clean up test ledgers
print("\nCleaning up test ledgers...")
mlm.delete_ledger(test_id)
mlm.delete_ledger(clone_id)
assert not test_json.exists(), f"Test JSON not deleted: {test_json}"
assert not test_db.exists(), f"Test DB not deleted: {test_db}"
assert not clone_json.exists(), f"Clone JSON not deleted: {clone_json}"
print("PASSED: Test ledgers and DBs cleanly deleted.")

print("\n=== ALL EMPIRICAL INTEGRITY TESTS PASSED SUCCESSFULLY ===")
