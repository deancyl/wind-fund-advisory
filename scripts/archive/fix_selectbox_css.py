import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

for target in [ROOT / "app_gui.py", ROOT / "AGY2_FundAdvisory" / "app_gui.py"]:
    if not target.exists():
        continue
    content = target.read_text(encoding="utf-8")

    old_sel_css = """        /* 侧边栏账本下拉框：彻底消灭刺眼白框，改为深墨融合质感 + 亮白字 */
        [data-testid="stSidebar"] div[data-baseweb="select"],
        [data-testid="stSidebar"] div[data-baseweb="select"] > div {{
            background-color: #182942 !important;
            border: 1px solid rgba(255, 255, 255, 0.18) !important;
            border-radius: 7px !important;
            color: #F8FAFC !important;
            min-height: 34px !important;
        }}
        [data-testid="stSidebar"] div[data-baseweb="select"] span,
        [data-testid="stSidebar"] div[data-baseweb="select"] div {{
            color: #F8FAFC !important;
            font-size: 12px !important;
        }}
        [data-testid="stSidebar"] div[data-baseweb="select"] svg {{
            color: #CBD5E1 !important;
            fill: #CBD5E1 !important;
        }}"""

    new_sel_css = """        /* 侧边栏账本下拉框：全面覆盖 BaseWeb 与 React Aria 两种 DOM 结构（彻底消灭刺眼白底） */
        [data-testid="stSidebar"] div[data-baseweb="select"],
        [data-testid="stSidebar"] div[data-baseweb="select"] > div,
        [data-testid="stSidebar"] [data-testid="stSelectbox"] div[role="group"],
        [data-testid="stSidebar"] div.react-aria-ComboBox,
        [data-testid="stSidebar"] [data-testid="stSelectbox"] div:has(> input[role="combobox"]) {{
            background-color: #182942 !important;
            background: #182942 !important;
            border: 1px solid rgba(255, 255, 255, 0.18) !important;
            border-radius: 7px !important;
            color: #F8FAFC !important;
            min-height: 34px !important;
        }}
        [data-testid="stSidebar"] [data-testid="stSelectbox"] input[role="combobox"] {{
            background: transparent !important;
            background-color: transparent !important;
            color: #F8FAFC !important;
            border: none !important;
            font-size: 12px !important;
        }}
        [data-testid="stSidebar"] div[data-baseweb="select"] span,
        [data-testid="stSidebar"] div[data-baseweb="select"] div,
        [data-testid="stSidebar"] [data-testid="stSelectbox"] span,
        [data-testid="stSidebar"] [data-testid="stSelectbox"] div {{
            color: #F8FAFC !important;
            font-size: 12px !important;
        }}
        [data-testid="stSidebar"] div[data-baseweb="select"] svg,
        [data-testid="stSidebar"] [data-testid="stSelectbox"] svg {{
            color: #CBD5E1 !important;
            fill: #CBD5E1 !important;
        }}"""

    assert old_sel_css in content, f"old_sel_css not found in {target}"
    content = content.replace(old_sel_css, new_sel_css)
    ast.parse(content, filename=str(target))
    target.write_text(content, encoding="utf-8")
    print(f"[OK] Upgraded selectbox css in {target}")
