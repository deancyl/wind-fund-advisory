with open(r"d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for idx in range(5030, 5075):
    print(f"{idx+1}: {lines[idx].rstrip()[:120]}")
