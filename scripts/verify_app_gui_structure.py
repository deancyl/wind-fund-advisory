# -*- coding: utf-8 -*-
from pathlib import Path
import re

app_gui_path = Path("AGY2_FundAdvisory/app_gui.py")
src = app_gui_path.read_text(encoding="utf-8")
lines = src.splitlines()

print(f"Total lines in app_gui.py: {len(lines)}")

# 1. Check reimport branch around line 148
print("\n=== Check 1: FundHolding, HoldingItem in reimport branch ===")
for i in range(130, 160):
    if i < len(lines):
        if "FundHolding" in lines[i] or "HoldingItem" in lines[i]:
            print(f"Line {i+1}: {lines[i]}")

# 2. Check _commit_edited_holdings_table
print("\n=== Check 2: _commit_edited_holdings_table search ===")
for i, line in enumerate(lines):
    if "_commit_edited_holdings_table" in line or "edited_table" in line:
        print(f"Line {i+1}: {line}")

# 3. Check @st.fragment usage
print("\n=== Check 3: @st.fragment usage ===")
for i, line in enumerate(lines):
    if "fragment" in line.lower():
        print(f"Line {i+1}: {line}")

# 4. Check QDII funds excluded from Tab 2 same-company switch dock
print("\n=== Check 4: QDII in same-company switch dock ===")
for i, line in enumerate(lines):
    if "同公司" in line or "低摩擦转换" in line or "同公司基金" in line:
        print(f"Line {i+1}: {line}")
        # print next 25 lines
        for j in range(i, min(i + 35, len(lines))):
            if any(k in lines[j] for k in ["QDII", "050025", "过滤", "排除", "is_qdii", "交割规则说明"]):
                print(f"  Line {j+1}: {lines[j]}")
