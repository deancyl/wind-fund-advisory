import ast
import re

GUI_PATH = r"d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py"

with open(GUI_PATH, "r", encoding="utf-8") as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")

# Search for session_state initialization
print("\n--- Searching for session_state initialization ---")
for i, line in enumerate(lines[:500]):
    if "session_state" in line:
        print(f"{i+1}: {line.strip()[:100]}")

# Search for tab creation
print("\n--- Searching for tab creation ---")
for i, line in enumerate(lines):
    if "st.tabs(" in line:
        print(f"{i+1}: {line.strip()[:100]}")

# Search for snapshot, pm, ai_orders_res
print("\n--- Searching for snapshot, pm, ai_orders_res ---")
for i, line in enumerate(lines):
    if any(k in line for k in ["ai_orders_res =", "ai_orders_res=", "get_snapshot", "get_current_snapshot", "current_snapshot", "portfolio_manager", "active_ledger", "selected_ledger"]):
        if i < 3000:  # focus on first 3000 lines
            print(f"{i+1}: {line.strip()[:120]}")
