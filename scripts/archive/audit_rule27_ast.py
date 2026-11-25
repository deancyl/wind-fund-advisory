# -*- coding: utf-8 -*-
import ast
import re
from pathlib import Path

gui_path = Path("AGY2_FundAdvisory/app_gui.py")
code = gui_path.read_text(encoding="utf-8")
tree = ast.parse(code, filename=str(gui_path))

violations = []
for node in ast.walk(tree):
    if not isinstance(node, ast.Call):
        continue

    func_name = None
    if isinstance(node.func, ast.Name):
        func_name = node.func.id
    elif isinstance(node.func, ast.Attribute):
        func_name = node.func.attr

    if func_name == "markdown":
        has_unsafe = any(
            kw.arg == "unsafe_allow_html" and getattr(kw.value, "value", None) is True
            for kw in node.keywords
        )
        if has_unsafe:
            line_no = getattr(node, "lineno", 0)
            # safe_markdown_html definition range
            if 200 <= line_no <= 210:
                continue

            is_cleaned = False
            if node.args:
                first_arg = node.args[0]
                if isinstance(first_arg, ast.Call):
                    arg_func = getattr(first_arg.func, "id", getattr(first_arg.func, "attr", None))
                    if arg_func == "_clean_html":
                        is_cleaned = True
            if not is_cleaned:
                violations.append((line_no, ast.unparse(node) if hasattr(ast, "unparse") else f"Line {line_no}"))

print(f"AST Scan: {len(violations)} violations found in app_gui.py for Rule 27 HTML purification.")
if violations:
    for line, snippet in violations:
        print(f"Line {line}: {snippet}")
    raise SystemExit(1)
else:
    print("ALL OK: app_gui.py AST has 0 unsafe markdown violations!")
