import ast

def audit_test_file(file_path):
    print(f"=== Auditing Test File AST: {file_path} ===")
    with open(file_path, "r", encoding="utf-8") as f:
        source = f.read()

    tree = ast.parse(source, filename=file_path)

    test_classes = []
    test_functions = []
    suspicious_asserts = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            test_classes.append(node.name)
        elif isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            test_functions.append(node.name)
            # check body for empty or trivial assertions
            if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                suspicious_asserts.append((node.name, "Only pass"))
            for subnode in ast.walk(node):
                if isinstance(subnode, ast.Assert):
                    if isinstance(subnode.test, ast.Constant) and subnode.test.value is True:
                        suspicious_asserts.append((node.name, "assert True"))

    print(f"Found {len(test_classes)} test classes: {test_classes}")
    print(f"Found {len(test_functions)} test functions")
    print(f"Suspicious assertions/bodies: {suspicious_asserts}")

    assert len(test_functions) >= 80, f"Expected at least 80 test functions, found {len(test_functions)}"
    assert len(suspicious_asserts) == 0, f"Found suspicious assertions: {suspicious_asserts}"
    print("=== Test AST Audit PASSED ===")

if __name__ == "__main__":
    audit_test_file("tests/test_g19_m2_routing_and_rolling_dca.py")
