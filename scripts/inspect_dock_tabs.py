with open(r"d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

def print_range(start, end):
    for idx in range(start - 1, min(end, len(lines))):
        print(f"{idx+1}: {lines[idx].rstrip()[:120]}")

print("=== 4640 - 5075 (Inside Tool Dock) ===")
# Let's inspect dock tabs and their line boundaries
for idx in range(4630, 5075):
    l = lines[idx]
    if "with dock_tab" in l or "dock_tab" in l or "# 步骤二" in l:
        print(f"{idx+1}: {l.strip()}")
