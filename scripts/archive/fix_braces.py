import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

for target in [ROOT / "app_gui.py", ROOT / "AGY2_FundAdvisory" / "app_gui.py"]:
    if not target.exists():
        continue
    content = target.read_text(encoding="utf-8")
    
    bad_block = """        /* 自选板块涨跌红绿语义色高亮 (G41) */
        .sec-chg-up, [data-testid="stSidebar"] .sec-chg-up {
            color: #F87171 !important;
        }
        .sec-chg-down, [data-testid="stSidebar"] .sec-chg-down {
            color: #4ADE80 !important;
        }
        .sec-chg-flat, [data-testid="stSidebar"] .sec-chg-flat {
            color: #94A3B8 !important;
        }"""
        
    good_block = """        /* 自选板块涨跌红绿语义色高亮 (G41) */
        .sec-chg-up, [data-testid="stSidebar"] .sec-chg-up {{
            color: #F87171 !important;
        }}
        .sec-chg-down, [data-testid="stSidebar"] .sec-chg-down {{
            color: #4ADE80 !important;
        }}
        .sec-chg-flat, [data-testid="stSidebar"] .sec-chg-flat {{
            color: #94A3B8 !important;
        }}"""

    if bad_block in content:
        content = content.replace(bad_block, good_block)
        ast.parse(content, filename=str(target))
        target.write_text(content, encoding="utf-8")
        print(f"[OK] Fixed double braces in {target}")
