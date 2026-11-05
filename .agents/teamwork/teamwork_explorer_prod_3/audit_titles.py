import re
from pathlib import Path

gui_path = Path("AGY2_FundAdvisory/app_gui.py")
text = gui_path.read_text(encoding="utf-8")

def count_chinese(s: str) -> int:
    return len(re.findall(r'[\u4e00-\u9fff]', s))

def clean_title(s: str) -> str:
    # remove markdown symbols, icons, etc
    s = re.sub(r'^[#\s\d\.\-\(\)《》【】\[\]\*\:\：\+]+', '', s)
    return s.strip()

print("=== 1. TABS ===")
for m in re.finditer(r'st\.tabs\(\s*\[(.*?)\]', text, re.DOTALL):
    tab_list = m.group(1).split(",")
    for t in tab_list:
        t_clean = t.strip().strip("'\"")
        cn = count_chinese(t_clean)
        print(f"Tab: '{t_clean}' (Chinese: {cn})")

print("\n=== 2. HEADERS (markdown #, ##, ###, ####, #####) ===")
header_matches = re.finditer(r'st\.(?:markdown|title|header|subheader)\(\s*f?(["\']{1,3})(#{1,5}\s+[^\n"\']+)\1', text)
for m in header_matches:
    line = m.group(2).strip()
    cn = count_chinese(line)
    if cn > 7:
        print(f"Header ({cn} chars > 7): {line}")

print("\n=== 3. EXPANDERS ===")
expander_matches = re.finditer(r'st\.expander\(\s*f?(["\'])(.*?)\1', text)
for m in expander_matches:
    line = m.group(2).strip()
    cn = count_chinese(line)
    if cn > 7:
        print(f"Expander ({cn} chars > 7): {line}")

print("\n=== 4. HTML CARD & COMPONENT TITLES ===")
html_titles = re.finditer(r'class="[^"]*(?:title|card-title|pill-name|decision-title)[^"]*"[^>]*>(.*?)<', text)
for m in html_titles:
    line = m.group(1).strip()
    cn = count_chinese(line)
    if cn > 7:
        print(f"HTML Title ({cn} chars > 7): {line}")
