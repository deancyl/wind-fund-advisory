with open(r"d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

def print_headers(start, end):
    for idx in range(start - 1, min(end, len(lines))):
        line = lines[idx]
        stripped = line.strip()
        if stripped.startswith("# ") or stripped.startswith("## ") or stripped.startswith("### "):
            print(f"{idx+1}: {stripped}")
        elif "st.subheader(" in stripped or "st.markdown(" in stripped and ("###" in stripped or "####" in stripped or "h3" in stripped or "h4" in stripped):
            print(f"{idx+1}: HEADER {stripped[:100]}")
        elif "st.button(" in stripped:
            print(f"{idx+1}: BUTTON {stripped[:100]}")
        elif "st.radio(" in stripped:
            print(f"{idx+1}: RADIO {stripped[:100]}")

print("=== Step 2 & Step 3 (5072 - 5765) ===")
print_headers(5072, 5765)
