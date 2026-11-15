import sys
import os

sys.path.insert(0, r"d:\Google\Workspace\Wind\AGY2_FundAdvisory")
from multi_ledger_manager import MultiLedgerManager

mlm = MultiLedgerManager.get_instance()
print("Active ledger ID:", mlm.get_active_ledger_id())
ledgers = mlm.list_ledgers()
print("Ledgers count:", len(ledgers))
for l in ledgers:
    lid = l.get("id")
    lname = l.get("name")
    pm = mlm.get_pm(lid)
    print(f"  ID: {lid}, Name: {lname}, Holdings: {len(pm.holdings)}")
