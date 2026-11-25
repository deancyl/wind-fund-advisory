import ast
from pathlib import Path

tests_dir = Path("tests")
violations_dispatch = []
for p in sorted(tests_dir.glob("*.py")):
    if p.name == "test_infra.py":
        continue
    content = p.read_text(encoding="utf-8", errors="ignore")
    for idx, line in enumerate(content.splitlines(), 1):
        if "app_gui.py" in line and any(k in line for k in ["read_text", "open(", ".read()", "code ="]):
            violations_dispatch.append(f"{p.name}:{idx} -> {line.strip()}")

print(f"Dispatch criteria violations count: {len(violations_dispatch)}")
for v in violations_dispatch:
    print("  ", v)

# Multiline check: any read_text / open / ast.parse on app_gui.py or variables referencing it
multiline_violations = []
for p in sorted(tests_dir.glob("*.py")):
    if p.name == "test_infra.py":
        continue
    content = p.read_text(encoding="utf-8", errors="ignore")
    lines = content.splitlines()
    for idx, line in enumerate(lines, 1):
        if any(needle in line for needle in ["app_gui.py", "GUI_PATH", "app_path", "gui_path", "app_file"]):
            ctx = "\n".join(lines[max(0, idx-4):min(len(lines), idx+4)])
            if any(k in ctx for k in ["read_text", "open(", ".read()", "ast.parse"]):
                multiline_violations.append(f"{p.name}:{idx} -> {line.strip()}")

print(f"\nMultiline criteria violations count: {len(multiline_violations)}")
for v in multiline_violations:
    print("  ", v)

assert len(violations_dispatch) == 0, f"Violations (dispatch): {violations_dispatch}"
assert len(multiline_violations) == 0, f"Violations (multiline): {multiline_violations}"
print("\n>>> ALL CHECKS PASSED WITH 0 VIOLATIONS! <<<")
