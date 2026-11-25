import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

for target in [ROOT / "app_gui.py", ROOT / "AGY2_FundAdvisory" / "app_gui.py"]:
    if not target.exists():
        continue
    content = target.read_text(encoding="utf-8")
    content = content.replace("color: #94A3B8 !important;\n        font-size: 12.5px !important;", "color: #CBD5E1 !important;\n        font-size: 13px !important;")
    content = content.replace("display: inline-flex !important;\n        background: #E2E8F0 !important;", "display: inline-flex !important;\n        flex-wrap: nowrap !important;\n        background: #E2E8F0 !important;")
    ast.parse(content, filename=str(target))
    target.write_text(content, encoding="utf-8")
    print(f"Refined styles in {target}")
