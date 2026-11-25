import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

for target in [ROOT / "app_gui.py", ROOT / "AGY2_FundAdvisory" / "app_gui.py"]:
    if not target.exists():
        continue
    content = target.read_text(encoding="utf-8")

    old_sentry = """                            <div style="display:flex;align-items:center;gap:6px;font-size:12px;font-weight:700;color:#0F172A;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
                                <span style="flex-shrink:0;width:6px;height:6px;border-radius:50%;background:{_a_dot};"></span>
                                <span style="overflow:hidden;text-overflow:ellipsis;">{_clean_title}</span>
                            </div>"""

    new_sentry = """                            <div style="display:flex;align-items:flex-start;gap:6px;font-size:12px;font-weight:700;color:#0F172A;line-height:1.35;">
                                <span style="flex-shrink:0;width:6px;height:6px;border-radius:50%;background:{_a_dot};margin-top:4px;"></span>
                                <span style="word-break:break-all;">{_clean_title}</span>
                            </div>"""

    assert old_sentry in content, f"old_sentry not found in {target}"
    content = content.replace(old_sentry, new_sentry)
    ast.parse(content, filename=str(target))
    target.write_text(content, encoding="utf-8")
    print(f"[OK] Enhanced sentry card multi-line title in {target}")
