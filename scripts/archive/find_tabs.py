with open(r"d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if "tabs(" in l or "st.tabs" in l or "tab1" in l.lower() or "tab2" in l.lower() or "持仓调仓" in l:
        print(f"{i+1}: {l.strip()[:100]}")
