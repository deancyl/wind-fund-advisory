import re
from pathlib import Path

gui_path = Path("AGY2_FundAdvisory/app_gui.py")
lines = gui_path.read_text(encoding="utf-8").splitlines()

def count_chinese(s: str) -> int:
    return len(re.findall(r'[\u4e00-\u9fff]', s))

violations = []

for idx, line in enumerate(lines, 1):
    # Check st.markdown / st.title / st.header / st.subheader with # headers
    m_head = re.search(r'st\.(?:markdown|title|header|subheader)\(\s*f?(["\']{1,3})(#{1,5}\s+[^\n"\']+)\1', line)
    if m_head:
        title = m_head.group(2).strip()
        # strip markdown # and symbols
        clean = re.sub(r'^[#\s]+', '', title)
        cn = count_chinese(clean)
        if cn > 7:
            violations.append((idx, "Markdown Header", clean, cn))

    # Check st.expander
    m_exp = re.search(r'st\.expander\(\s*f?(["\'])(.*?)\1', line)
    if m_exp:
        title = m_exp.group(2).strip()
        cn = count_chinese(title)
        if cn > 7:
            violations.append((idx, "Expander", title, cn))

    # Check metric-card-title / kpi-card-title / decision-title
    m_card = re.search(r'class="[^"]*(?:metric-card-title|kpi-card-title|decision-title)[^"]*"[^>]*>(.*)', line)
    if m_card:
        title = m_card.group(1).strip()
        # strip tags
        clean = re.sub(r'<[^>]+>', '', title)
        cn = count_chinese(clean)
        if cn > 7:
            violations.append((idx, "Card Title", clean, cn))

for v in violations:
    print(f"L{v[0]}: [{v[1]}] ({v[3]}汉字): {v[2]}")
