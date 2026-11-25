import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

OLD_RADIO_CSS = """    /* 全局消灭 Streamlit 原生红色 radio 圆点 (#FF4B4B) */
    /* 1. 主区横向单选：改造成精致分段胶囊条 (Segmented Control) */
    .main div[role="radiogroup"] {{
        display: inline-flex !important;
        background: #E2E8F0 !important;
        padding: 3px !important;
        border-radius: 8px !important;
        gap: 3px !important;
        border: 1px solid #DCE3ED !important;
    }}
    .main div[role="radiogroup"] > label {{
        background: transparent !important;
        padding: 4px 12px !important;
        border-radius: 6px !important;
        margin: 0 !important;
        cursor: pointer !important;
        transition: all 0.15s ease !important;
    }}
    .main div[role="radiogroup"] > label:hover {{
        background: rgba(255, 255, 255, 0.6) !important;
    }}
    .main div[role="radiogroup"] > label > div:first-child {{
        display: none !important;
    }}
    .main div[role="radiogroup"] > label:has(input:checked) {{
        background: #FFFFFF !important;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08) !important;
    }}
    .main div[role="radiogroup"] > label:has(input:checked) p {{
        color: #1B365D !important;
        font-weight: 700 !important;
    }}

    /* 2. 侧边栏主导航：深海曜石蓝专属菜单项 (选中带哑光金左指示条) */
    [data-testid="stSidebar"] div[role="radiogroup"] {{
        gap: 4px !important;
    }}
    [data-testid="stSidebar"] div[role="radiogroup"] > label {{
        background: transparent !important;
        border-radius: 7px !important;
        padding: 7px 10px !important;
        margin: 0 !important;
        border-left: 3px solid transparent !important;
        transition: background 0.15s ease !important;
        cursor: pointer !important;
    }}
    [data-testid="stSidebar"] div[role="radiogroup"] > label:hover {{
        background: rgba(255, 255, 255, 0.06) !important;
    }}
    [data-testid="stSidebar"] div[role="radiogroup"] > label > div:first-child {{
        display: none !important;
    }}
    [data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) {{
        background: rgba(194, 150, 72, 0.14) !important;
        border-left: 3px solid #C29648 !important;
    }}
    [data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) p {{
        color: #FFFFFF !important;
        font-weight: 700 !important;
    }}"""

NEW_RADIO_CSS = """    /* 全局消灭 Streamlit 原生红色 radio 圆点 (#FF4B4B) */
    /* 1. 彻底隐藏所有 radio 选项的原生圆点指示器 */
    [data-testid="stRadioOption"] > div > div:first-child,
    div[role="radiogroup"] label > div:first-child,
    [data-testid="stRadioOption"] svg,
    div[role="radiogroup"] svg {{
        display: none !important;
    }}

    /* 2. 主区横向单选：精致分段胶囊条 (Segmented Control) */
    .main [data-testid="stRadioGroup"][aria-orientation="horizontal"],
    .main div[role="radiogroup"] {{
        display: inline-flex !important;
        background: #E2E8F0 !important;
        padding: 3px !important;
        border-radius: 8px !important;
        gap: 3px !important;
        border: 1px solid #DCE3ED !important;
    }}
    .main [data-testid="stRadioOption"],
    .main div[role="radiogroup"] label {{
        background: transparent !important;
        padding: 4px 12px !important;
        border-radius: 6px !important;
        margin: 0 !important;
        cursor: pointer !important;
        transition: all 0.15s ease !important;
        display: flex !important;
        align-items: center !important;
    }}
    .main [data-testid="stRadioOption"]:hover,
    .main div[role="radiogroup"] label:hover {{
        background: rgba(255, 255, 255, 0.6) !important;
    }}
    .main [data-testid="stRadioOption"][data-selected="true"],
    .main div[role="radiogroup"] label:has(input:checked) {{
        background: #FFFFFF !important;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08) !important;
    }}
    .main [data-testid="stRadioOption"] p,
    .main div[role="radiogroup"] label p {{
        color: #475569 !important;
        font-size: 12px !important;
        font-weight: 500 !important;
        margin: 0 !important;
    }}
    .main [data-testid="stRadioOption"][data-selected="true"] p,
    .main div[role="radiogroup"] label:has(input:checked) p {{
        color: #1B365D !important;
        font-weight: 700 !important;
    }}

    /* 3. 侧边栏主导航：深海曜石蓝专属菜单项 (选中带哑光金左指示条) */
    [data-testid="stSidebar"] [data-testid="stRadioGroup"],
    [data-testid="stSidebar"] div[role="radiogroup"] {{
        gap: 4px !important;
    }}
    [data-testid="stSidebar"] [data-testid="stRadioOption"],
    [data-testid="stSidebar"] div[role="radiogroup"] label {{
        background: transparent !important;
        border-radius: 7px !important;
        padding: 7px 10px !important;
        margin: 0 !important;
        border-left: 3px solid transparent !important;
        transition: background 0.15s ease !important;
        cursor: pointer !important;
        display: flex !important;
        align-items: center !important;
        width: 100% !important;
    }}
    [data-testid="stSidebar"] [data-testid="stRadioOption"]:hover,
    [data-testid="stSidebar"] div[role="radiogroup"] label:hover {{
        background: rgba(255, 255, 255, 0.08) !important;
    }}
    [data-testid="stSidebar"] [data-testid="stRadioOption"] p,
    [data-testid="stSidebar"] div[role="radiogroup"] label p {{
        color: #94A3B8 !important;
        font-size: 12.5px !important;
        font-weight: 500 !important;
        margin: 0 !important;
    }}
    [data-testid="stSidebar"] [data-testid="stRadioOption"]:hover p,
    [data-testid="stSidebar"] div[role="radiogroup"] label:hover p {{
        color: #E2E8F0 !important;
    }}
    [data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"],
    [data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {{
        background: rgba(194, 150, 72, 0.18) !important;
        border-left: 3px solid #C29648 !important;
    }}
    [data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] p,
    [data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) p {{
        color: #FFFFFF !important;
        font-weight: 700 !important;
    }}"""

targets = [ROOT / "app_gui.py", ROOT / "AGY2_FundAdvisory" / "app_gui.py"]

for target in targets:
    if not target.exists():
        continue
    content = target.read_text(encoding="utf-8")
    assert OLD_RADIO_CSS in content, f"OLD_RADIO_CSS not found in {target}"
    content = content.replace(OLD_RADIO_CSS, NEW_RADIO_CSS)
    ast.parse(content, filename=str(target))
    target.write_text(content, encoding="utf-8")
    print(f"Successfully updated radio styles in {target}")
