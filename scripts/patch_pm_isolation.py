# -*- coding: utf-8 -*-
with open("AGY2_FundAdvisory/portfolio_manager.py", "r", encoding="utf-8") as f:
    code = f.read()

# Fix 1: Storage file isolation
target1 = """        if ledger_file is not None:
            ledger_json_path = ledger_file
        if storage_file is not None:
            db_path = storage_file"""

replacement1 = """        if ledger_file is not None:
            ledger_json_path = ledger_file
        elif storage_file is not None and str(ledger_json_path) == "portfolio_ledger.json":
            ledger_json_path = Path(storage_file).with_suffix(".json")
        if storage_file is not None:
            db_path = storage_file"""

# Fix 2: max_total_overlap when active_funds < 2
target2 = """                "pending_external_funds": pending_external_funds,
                "max_non_diag_unexcused": 0.0
            }"""

replacement2 = """                "pending_external_funds": pending_external_funds,
                "max_non_diag_unexcused": 0.0,
                "max_total_overlap": 0.0
            }"""

if target1 in code:
    code = code.replace(target1, replacement1, 1)
    print("Fix 1 applied successfully")
else:
    print("Fix 1 target not found")

if target2 in code:
    code = code.replace(target2, replacement2, 1)
    print("Fix 2 applied successfully")
else:
    print("Fix 2 target not found")

with open("AGY2_FundAdvisory/portfolio_manager.py", "w", encoding="utf-8") as f:
    f.write(code)
