import ast
import os
import sys

def check_file(path):
    print(f"Auditing AST of {path}...")
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()

    tree = ast.parse(src, filename=path)
    issues = []

    for node in ast.walk(tree):
        # Check for empty functions or functions only returning a constant
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Ignore __init__ or dunder or simple property getters if reasonable
            body = node.body
            if len(body) == 1:
                stmt = body[0]
                if isinstance(stmt, ast.Pass):
                    issues.append(f"Function {node.name} line {node.lineno}: empty body (pass)")
                elif isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Constant):
                    # Check if constant return is suspicious (e.g. return True or return "clean")
                    if node.name not in ["_resolve_cache_dir", "__repr__", "__str__"]:
                        # Property or trivial helper might be ok, report for manual inspection
                        issues.append(f"Function {node.name} line {node.lineno}: returns literal constant {stmt.value.value}")
                elif isinstance(stmt, ast.Raise) and isinstance(stmt.exc, ast.Name) and stmt.exc.id == "NotImplementedError":
                    issues.append(f"Function {node.name} line {node.lineno}: raises NotImplementedError")

    return issues

if __name__ == "__main__":
    targets = [
        "AGY2_FundAdvisory/advisory_engine.py",
        "AGY2_FundAdvisory/app_gui.py",
        "AGY2_FundAdvisory/data_loader.py",
    ]
    all_issues = []
    for t in targets:
        if os.path.exists(t):
            iss = check_file(t)
            all_issues.extend(iss)

    print("\nSummary of potential facade / constant returns:")
    for iss in all_issues:
        print(" -", iss)

    # Specific check for any fake test bypasses
    # e.g., if "test" in path or check in pytest
    print(f"\nTotal potential issues detected: {len(all_issues)}")
