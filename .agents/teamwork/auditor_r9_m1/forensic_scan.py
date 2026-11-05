import ast
import re
from pathlib import Path

files_to_scan = [
    "AGY2_FundAdvisory/multi_ledger_manager.py",
    "AGY2_FundAdvisory/portfolio_manager.py",
    "AGY2_FundAdvisory/app_gui.py"
]

print("=== FORENSIC STATIC ANALYSIS ===")

for rel_path in files_to_scan:
    p = Path(rel_path)
    if not p.exists():
        print(f"File {rel_path} does not exist!")
        continue

    content = p.read_text(encoding="utf-8")
    tree = ast.parse(content, filename=rel_path)

    # 1. Scan for empty functions or pass-only functions
    empty_funcs = []
    constant_only_funcs = []
    
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Check if function body is just 'pass'
            if len(node.body) == 1:
                if isinstance(node.body[0], ast.Pass):
                    empty_funcs.append((node.name, node.lineno, "pass only"))
                elif isinstance(node.body[0], ast.Return) and isinstance(node.body[0].value, ast.Constant):
                    # Flag constant returns in significant functions (ignore property getters or trivial defaults if reasonable)
                    constant_only_funcs.append((node.name, node.lineno, f"return {node.body[0].value.value}"))

    print(f"\n--- {rel_path} ---")
    print(f"Total lines: {len(content.splitlines())}")
    print(f"Empty pass functions count: {len(empty_funcs)}")
    if empty_funcs:
        for f in empty_funcs[:10]:
            print(f"  Empty pass: {f[0]} at line {f[1]}")
    
    # In multi_ledger_manager.py, check specifically
    if rel_path == "AGY2_FundAdvisory/multi_ledger_manager.py":
        print(f"Constant-only functions count: {len(constant_only_funcs)}")
        for f in constant_only_funcs:
            print(f"  Constant-only: {f[0]} at line {f[1]}: {f[2]}")

print("\n=== SCAN COMPLETED ===")
