# -*- coding: utf-8 -*-
with open("tests/test_g8_ux_and_realtime_fusion.py", "r", encoding="utf-8") as f:
    code = f.read()

target = 'pm = PortfolioManager(storage_file="data/test_g8_undo_pm.json")'
replacement = 'pm = PortfolioManager(ledger_file="data/test_g8_undo_pm.json", storage_file="data/test_g8_undo_pm.db")'

if target in code:
    code = code.replace(target, replacement, 1)
    with open("tests/test_g8_ux_and_realtime_fusion.py", "w", encoding="utf-8") as f:
        f.write(code)
    print("Patched test_g8_ux_and_realtime_fusion.py successfully")
else:
    print("Target not found!")
