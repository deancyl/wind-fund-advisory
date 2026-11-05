import sys
from pathlib import Path

root = Path(".").resolve()
sys.path.insert(0, str(root / "AGY2_FundAdvisory"))
sys.path.insert(0, str(root))

from AGY2_FundAdvisory.multi_ledger_manager import MultiLedgerManager

print("=== ADVERSARIAL STRESS TEST ===")
mlm = MultiLedgerManager(workspace_root=root)

# Edge Case 1: Path traversal attempt in name
print("1. Path traversal attempt in name...")
bad_name = "../../../etc/passwd"
lid = mlm.create_ledger(name=bad_name)
meta = mlm.get_ledger_meta(lid)
assert lid.startswith("sandbox_"), f"Unexpected lid: {lid}"
# File must be strictly inside data/ledgers/
file_path = root / meta["file"]
assert file_path.parent == (root / "data" / "ledgers"), f"Path escaped! {file_path}"
print(f"PASSED: File stayed confined in data/ledgers/: {file_path}")
mlm.delete_ledger(lid)

# Edge Case 2: Non-existent ledger deletion
print("\n2. Non-existent ledger deletion...")
res = mlm.delete_ledger("non_existent_123456")
assert res is False, f"Expected False, got {res}"
print("PASSED: Handled gracefully, returned False.")

# Edge Case 3: Non-existent ledger renaming
print("\n3. Non-existent ledger renaming...")
res = mlm.rename_ledger("non_existent_123456", "New Name")
assert res is False, f"Expected False, got {res}"
print("PASSED: Handled gracefully, returned False.")

# Edge Case 4: Non-existent get_pm fallback
print("\n4. Non-existent get_pm fallback...")
pm = mlm.get_pm("non_existent_ledger_999")
assert pm is not None
assert pm.ledger_id == "main_live", f"Expected fallback to main_live, got {pm.ledger_id}"
print("PASSED: Gracefully fell back to main_live.")

# Edge Case 5: Empty ledger name
print("\n5. Empty ledger name...")
lid2 = mlm.create_ledger(name="   ")
meta2 = mlm.get_ledger_meta(lid2)
assert meta2["name"].startswith("未命名账本_"), f"Expected default name, got {meta2['name']}"
print(f"PASSED: Auto-named as {meta2['name']}")
mlm.delete_ledger(lid2)

# Edge Case 6: Clone non-existent ledger
print("\n6. Clone non-existent ledger...")
try:
    mlm.clone_ledger("non_existent_id", "Target")
    print("FAILED: Should have raised KeyError")
    sys.exit(1)
except KeyError as e:
    print(f"PASSED: Correctly raised KeyError: {e}")

print("\n=== ALL ADVERSARIAL TESTS PASSED ===")
