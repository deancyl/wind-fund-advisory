import re
from pathlib import Path

gui_path = Path("AGY2_FundAdvisory/app_gui.py")
content = gui_path.read_text(encoding="utf-8")
lines = content.splitlines(keepends=True)

print(f"Total lines in app_gui.py: {len(lines)}")

dock_start = -1
dock_end = -1
step1_bot_start = -1
step2_start = -1
step3_end = -1

for i, line in enumerate(lines):
    if "dock_tab1, dock_tab2, dock_tab3, dock_tab4, dock_tab5, dock_tab6 = st.tabs([" in line:
        dock_start = i
    if "btn_apply_adaptive_div" in line:
        # dock_tab6 ends a few lines after this
        dock_end = i + 5
    if "col_t2_btn1, col_t2_buf_bot, col_t2_btn2 = st.columns([3.5, 4.0, 2.5])" in line:
        step1_bot_start = i
    if "步骤二：【🚦 调仓时机裁决】" in line:
        step2_start = i
    if "btn_confirm_follow_rebalance_tab2" in line:
        step3_end = i + 15

print(f"dock_start: {dock_start+1}")
print(f"dock_end: {dock_end+1}")
print(f"step1_bot_start: {step1_bot_start+1}")
print(f"step2_start: {step2_start+1}")
print(f"step3_end: {step3_end+1}")
