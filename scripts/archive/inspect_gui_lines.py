GUI_PATH = r"d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py"

with open(GUI_PATH, "r", encoding="utf-8") as f:
    lines = f.readlines()

def print_section(start, end):
    for i in range(start - 1, min(end, len(lines))):
        print(f"{i+1:4d}: {lines[i].rstrip()}")

print("=== Lines 3520 to 3565 ===")
print_section(3520, 3565)
