# -*- coding: utf-8 -*-
import traceback
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

with open(ROOT / "app_gui.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

sub_lines = lines[6424:7743] # includes except
dedented_lines = []
for l in sub_lines:
    if l.startswith("    "):
        dedented_lines.append(l[4:])
    else:
        dedented_lines.append(l)

code = "".join(dedented_lines)

import app_gui
ns = app_gui.__dict__.copy()

print("Executing tab_holdings_and_rebalance block...")
try:
    exec(code, ns)
    print("Execution completed with NO exception!")
except Exception as e:
    print(f"EXCEPTION CAUGHT: {type(e).__name__}: {e}")
    traceback.print_exc()
