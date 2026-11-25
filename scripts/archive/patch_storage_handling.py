# -*- coding: utf-8 -*-
with open("AGY2_FundAdvisory/portfolio_manager.py", "r", encoding="utf-8") as f:
    code = f.read()

target = """        if ledger_file is not None:
            ledger_json_path = ledger_file
        elif storage_file is not None and str(ledger_json_path) == "portfolio_ledger.json":
            ledger_json_path = Path(storage_file).with_suffix(".json")
        if storage_file is not None:
            db_path = storage_file"""

replacement = """        if ledger_file is not None:
            ledger_json_path = ledger_file
        elif storage_file is not None and str(storage_file).endswith(".json"):
            ledger_json_path = storage_file
            if db_path is None or str(db_path) == "portfolio_state.db":
                db_path = Path(storage_file).with_suffix(".db")
        elif storage_file is not None and str(ledger_json_path) == "portfolio_ledger.json":
            ledger_json_path = Path(storage_file).with_suffix(".json")

        if storage_file is not None and not str(storage_file).endswith(".json"):
            db_path = storage_file"""

if target in code:
    code = code.replace(target, replacement, 1)
    with open("AGY2_FundAdvisory/portfolio_manager.py", "w", encoding="utf-8") as f:
        f.write(code)
    print("Patched storage_file handling successfully")
else:
    print("Target not found")
