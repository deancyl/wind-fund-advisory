import re
from pathlib import Path

gui_path = Path("AGY2_FundAdvisory/app_gui.py")
text = gui_path.read_text(encoding="utf-8")
lines = text.splitlines()

print("=== 1. BUTTONS ===")
btn_matches = []
for i, line in enumerate(lines, 1):
    m = re.search(r'st\.button\((.*?)\)', line)
    if m:
        btn_matches.append((i, m.group(1).strip()))
    elif 'st.button(' in line:
        btn_matches.append((i, line.strip()))

for i, b in btn_matches:
    print(f"L{i:04d}: {b}")

print("\n=== 2. MARKDOWN HEADERS ===")
for i, line in enumerate(lines, 1):
    m = re.search(r'st\.markdown\([f"\']*([#]{1,5}\s+[^"\']+)[f"\']*', line)
    if m:
        hdr = m.group(1).strip()
        print(f"L{i:04d} (len={len(hdr.split(None, 1)[-1]) if len(hdr.split(None, 1))>1 else len(hdr)}): {hdr}")

print("\n=== 3. EXPANDER TITLES ===")
for i, line in enumerate(lines, 1):
    m = re.search(r'st\.expander\([f"\']([^"\']+)[f"\']', line)
    if m:
        print(f"L{i:04d}: {m.group(1)}")
