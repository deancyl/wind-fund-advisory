with open(r"d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

def print_range(start, end, max_lines=40):
    count = 0
    for idx in range(start - 1, min(end, len(lines))):
        print(f"{idx+1}: {lines[idx].rstrip()[:120]}")
        count += 1
        if count >= max_lines:
            print(f"... (truncated, {end - start + 1 - max_lines} more lines)")
            break

print("=== 4070 - 4180 (Multi-ledger bar) ===")
print_range(4070, 4180, 50)
