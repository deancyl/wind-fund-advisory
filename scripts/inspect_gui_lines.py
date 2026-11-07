import sys
from pathlib import Path

content = Path("AGY2_FundAdvisory/app_gui.py").read_text(encoding="utf-8")
lines = content.splitlines()

for i, l in enumerate(lines):
    if "def render_radar_and_sentry_wing" in l:
        print(f"render_radar_and_sentry_wing starts at line {i+1}")
    if "def render_tab2_holdings_content" in l:
        print(f"render_tab2_holdings_content starts at line {i+1}")
    if "def render_tab4_toolbox_content" in l:
        print(f"render_tab4_toolbox_content starts at line {i+1}")
    if "with st.expander(\"🛠️ 账本工具坞" in l:
        print(f"dock expander at line {i+1}")
    if "核心标的五维深度研判" in l:
        print(f"5D diagnosis at line {i+1}")
