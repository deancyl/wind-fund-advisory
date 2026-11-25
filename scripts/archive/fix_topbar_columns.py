# -*- coding: utf-8 -*-
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP_GUI = ROOT / "app_gui.py"
APP_GUI_MIRROR = ROOT / "AGY2_FundAdvisory" / "app_gui.py"

with open(APP_GUI, "r", encoding="utf-8") as f:
    text = f.read()

old_cols = "col_sel_ld, col_pop_in, col_pop_ops, col_pop_info = st.columns([5.2, 1.6, 1.6, 1.6])"
new_cols = "col_sel_ld, col_pop_in, col_pop_ops, col_pop_info, col_pop_rv = st.columns([4.0, 1.5, 1.5, 1.5, 1.5])"

if old_cols in text:
    text = text.replace(old_cols, new_cols)
    print("Replaced with 5 topbar columns including col_pop_rv")
else:
    print("old_cols not found")

ast.parse(text)
print("AST parsed successfully!")

with open(APP_GUI, "w", encoding="utf-8") as f:
    f.write(text)

with open(APP_GUI_MIRROR, "w", encoding="utf-8") as f:
    f.write(text)

print("Saved and mirrored to AGY2_FundAdvisory/app_gui.py!")
