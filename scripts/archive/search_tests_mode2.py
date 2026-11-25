import os
import glob

tests_dir = r"d:\Google\Workspace\Wind\tests"
py_files = glob.glob(os.path.join(tests_dir, "*.py"))

keywords = ["dock", "tool_dock", "账本工具坞", "批次", "在途", "对账", "同公司", "自适应分红", "tab2_view_mode"]

found = {}
for pf in py_files:
    fname = os.path.basename(pf)
    with open(pf, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    for kw in keywords:
        if kw in content:
            if fname not in found:
                found[fname] = []
            found[fname].append(kw)

for fname, kws in found.items():
    print(f"{fname}: {list(set(kws))}")
