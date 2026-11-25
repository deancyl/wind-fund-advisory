import re

with open('AGY2_FundAdvisory/app_gui.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"Total lines in app_gui.py: {len(lines)}")

# Scan lines for direct st.markdown with unsafe_allow_html=True
direct_calls = []
for idx, line in enumerate(lines, 1):
    if 'st.markdown(' in line and 'unsafe_allow_html=True' in line:
        direct_calls.append((idx, line.strip()))

print(f"Found {len(direct_calls)} direct calls to st.markdown with unsafe_allow_html=True:")
for idx, l in direct_calls:
    print(f"  Line {idx}: {l}")

print("\nVerifying that newly added HTML blocks use safe_markdown_html:")
# Range for new top bar and mobile view is around line 2850 to 3280
for idx, l in direct_calls:
    if 2850 <= idx <= 3280:
        print(f"  [In M2 Scope] Line {idx}: {l}")

print("\n=== RULE 27 AUDIT COMPLETE ===")
