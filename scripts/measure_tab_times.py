import sys
import time
from pathlib import Path

# 我们用 AST 或正则分析每个 Tab 里面包含了哪些函数调用
sys.path.insert(0, str(Path("AGY2_FundAdvisory").resolve()))

with open("AGY2_FundAdvisory/app_gui.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

tab_indices = {}
for i, l in enumerate(lines):
    if "with tab_zero_start:" in l:
        tab_indices["Tab 1 (新资建仓)"] = i
    elif "with tab_holdings_and_rebalance:" in l:
        tab_indices["Tab 2 (持仓调仓)"] = i
    elif "with tab_backtest:" in l:
        tab_indices["Tab 3 (组合回测)"] = i
    elif "with tab_toolbox:" in l:
        tab_indices["Tab 4 (穿透工具)"] = i

print("Tab line ranges:")
sorted_tabs = sorted(tab_indices.items(), key=lambda x: x[1])
for idx, (name, line_no) in enumerate(sorted_tabs):
    next_line = sorted_tabs[idx+1][1] if idx+1 < len(sorted_tabs) else len(lines)
    print(f"  {name}: L{line_no+1} ~ L{next_line} ({next_line - line_no} lines)")
