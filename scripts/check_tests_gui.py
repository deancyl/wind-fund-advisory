import os
import glob

tests_dir = r"d:\Google\Workspace\Wind\tests"
py_files = glob.glob(os.path.join(tests_dir, "*.py"))

print("Files importing app_gui or using AppTest:")
for pf in py_files:
    fname = os.path.basename(pf)
    with open(pf, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    if "app_gui" in content or "AppTest" in content:
        print(f"\n--- {fname} ---")
        lines = content.split("\n")
        for i, l in enumerate(lines):
            if any(term in l for term in ["app_gui", "AppTest", "from_file", "tab2", "btn_tab2", "sel_tab2"]):
                print(f"  Line {i+1}: {l.strip()[:100]}")
