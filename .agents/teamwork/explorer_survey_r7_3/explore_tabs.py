import sys
from pathlib import Path

app_path = Path("AGY2_FundAdvisory/app_gui.py")
content = app_path.read_text(encoding="utf-8", errors="ignore")
print(f"app_gui.py total lines: {len(content.splitlines())}")

# Search for tab-related lines
lines = content.splitlines()
for i, line in enumerate(lines):
    if any(k in line for k in ["selected_tab", "tabs", "tab1", "Tab 1", "新资建仓", "持仓调仓", "st.tabs"]):
        print(f"{i+1}: {line[:100]}")
