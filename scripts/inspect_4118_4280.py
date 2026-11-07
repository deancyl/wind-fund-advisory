with open(r"d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

def print_range(start, end):
    for idx in range(start - 1, min(end, len(lines))):
        print(f"{idx+1}: {lines[idx].rstrip()[:120]}")

print("=== 4118 - 4280 ===")
print_range(4118, 4280)
