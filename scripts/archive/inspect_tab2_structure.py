import re

with open(r"d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

print(f"Total lines in app_gui.py: {len(lines)}")

tab2_start = 3894 # 1-based index 3895
tab2_end = 5766   # 1-based index 5766

print("Scanning Tab 2 structure...")
for idx in range(tab2_start - 1, tab2_end):
    line = lines[idx]
    line_no = idx + 1
    # Check for comments, subheaders, expanders, markdown headers, buttons, etc.
    stripped = line.strip()
    if stripped.startswith("# ") or stripped.startswith("## ") or stripped.startswith("### "):
        print(f"{line_no}: COMMENT {stripped}")
    elif "st.subheader(" in stripped or "st.markdown(" in stripped and ("###" in stripped or "####" in stripped or "h3" in stripped or "h4" in stripped):
        print(f"{line_no}: HEADER {stripped[:100]}")
    elif "st.expander(" in stripped:
        print(f"{line_no}: EXPANDER {stripped[:100]}")
    elif "st.form(" in stripped:
        print(f"{line_no}: FORM {stripped[:100]}")
    elif "with col" in stripped or "with st." in stripped:
        if "expander" not in stripped and "form" not in stripped:
            pass
