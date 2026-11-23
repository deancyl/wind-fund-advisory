# -*- coding: utf-8 -*-
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP_GUI = ROOT / "app_gui.py"
APP_GUI_MIRROR = ROOT / "AGY2_FundAdvisory" / "app_gui.py"

with open(APP_GUI, "r", encoding="utf-8") as f:
    text = f.read()

helper_def = """def _fmt_topbar_ledger(lid: str) -> str:
    m = mlm_inst.get_ledger_meta(lid) or {}
    tag = "[实盘]" if m.get("type") == "live" else ("[沙盒]" if m.get("type") == "sandbox" else "[家庭]")
    name_str = str(m.get("name", lid))
    if "¥" in name_str:
        return f"{tag} {name_str}"
    try:
        eq = float(mlm_inst.get_pm(lid).total_equity)
    except Exception:
        eq = 0.0
    return f"{tag} {name_str} (¥{eq:,.0f})"
"""

target = "# =============================================================================\n# 🧭 方案 B：专业桌面端左侧主领航台"
if target in text:
    text = text.replace(target, helper_def + "\n\n" + target)
    print("Added _fmt_topbar_ledger before sidebar")

ast.parse(text)
print("AST parsed successfully!")

with open(APP_GUI, "w", encoding="utf-8") as f:
    f.write(text)

with open(APP_GUI_MIRROR, "w", encoding="utf-8") as f:
    f.write(text)

print("Saved and mirrored to AGY2_FundAdvisory/app_gui.py!")
