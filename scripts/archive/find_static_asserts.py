import os
import glob
import re

tests_dir = r"d:\Google\Workspace\Wind\tests"
py_files = glob.glob(os.path.join(tests_dir, "*.py"))

print("All static string assertions on app_gui.py across test files:")
for pf in py_files:
    fname = os.path.basename(pf)
    with open(pf, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    if "app_gui.py" in content or "gui_file" in content or "gui_p" in content:
        # Search for assert lines containing "in "
        lines = content.split("\n")
        for i, l in enumerate(lines):
            stripped = l.strip()
            if stripped.startswith("assert ") and ("in " in stripped or "count" in stripped):
                print(f"{fname}:{i+1} -> {stripped}")
