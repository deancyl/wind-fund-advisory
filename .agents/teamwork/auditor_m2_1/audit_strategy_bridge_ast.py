import ast
import os
import sys

def audit_strategy_bridge(file_path):
    print("=== Auditing StrategyBridge AST ===")
    with open(file_path, "r", encoding="utf-8") as f:
        source = f.read()

    tree = ast.parse(source, filename=file_path)

    # 1. Search for calculate_mutual_fund_friction_bill and calculate_rolling_dca_3y_backtest
    target_functions = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in [
            "calculate_mutual_fund_friction_bill",
            "calculate_rolling_dca_3y_backtest",
            "get_combat_29_vs_reconstructed_6_preset",
            "run_historical_time_machine_backtest"
        ]:
            target_functions[node.name] = node

    print(f"Found functions: {list(target_functions.keys())}")
    assert "calculate_mutual_fund_friction_bill" in target_functions, "Missing calculate_mutual_fund_friction_bill"
    assert "calculate_rolling_dca_3y_backtest" in target_functions, "Missing calculate_rolling_dca_3y_backtest"

    # 2. Check for banned hardcoded constants in calculate_mutual_fund_friction_bill
    banned_constants = [16.85, -16.76, 3.42, 394, -4.52, -6.24]
    f_bill_node = target_functions["calculate_mutual_fund_friction_bill"]
    found_constants = []
    has_load_matrix = False

    for node in ast.walk(f_bill_node):
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                for bc in banned_constants:
                    if abs(node.value - bc) < 1e-4:
                        found_constants.append(node.value)
        elif isinstance(node, ast.Call):
            # Check for cls.load_matrix() or StrategyBridge.load_matrix() or similar
            if isinstance(node.func, ast.Attribute) and node.func.attr == "load_matrix":
                has_load_matrix = True

    print(f"calculate_mutual_fund_friction_bill banned constants found: {found_constants}")
    print(f"calculate_mutual_fund_friction_bill has load_matrix call: {has_load_matrix}")

    assert len(found_constants) == 0, f"Found banned constants in calculate_mutual_fund_friction_bill: {found_constants}"
    assert has_load_matrix, "calculate_mutual_fund_friction_bill must call load_matrix to load real prices"

    # 3. Check calculate_rolling_dca_3y_backtest for genuine rolling backtest and zero lookahead
    rolling_node = target_functions["calculate_rolling_dca_3y_backtest"]
    rolling_has_for_loop = False
    rolling_has_lookahead_check = False
    rolling_has_fee_deduction = False

    # Check AST for loops and operations
    for node in ast.walk(rolling_node):
        if isinstance(node, (ast.For, ast.While)):
            rolling_has_for_loop = True

    # Let's inspect source of calculate_rolling_dca_3y_backtest
    rolling_src = ast.get_source_segment(source, rolling_node)
    
    # Check for Point-in-Time slicing
    if "iloc" in rolling_src or "loc" in rolling_src or "<=" in rolling_src or "slice" in rolling_src:
        rolling_has_lookahead_check = True

    # Check for management fee deduction (0.75% / 250)
    if "0.0075" in rolling_src or "0.75" in rolling_src:
        rolling_has_fee_deduction = True

    print(f"calculate_rolling_dca_3y_backtest has for loop: {rolling_has_for_loop}")
    print(f"calculate_rolling_dca_3y_backtest has slicing/PIT: {rolling_has_lookahead_check}")
    print(f"calculate_rolling_dca_3y_backtest has fee deduction: {rolling_has_fee_deduction}")

    assert rolling_has_for_loop, "calculate_rolling_dca_3y_backtest must contain a loop iterating over periods"
    assert rolling_has_fee_deduction, "calculate_rolling_dca_3y_backtest must deduct genuine fees"

    # 4. Check run_historical_time_machine_backtest for daily management custody fee
    if "run_historical_time_machine_backtest" in target_functions:
        tm_src = ast.get_source_segment(source, target_functions["run_historical_time_machine_backtest"])
        has_tm_fee = ("0.0075" in tm_src or "mgmt_custody_fee_daily" in tm_src)
        print(f"run_historical_time_machine_backtest has mgmt/custody fee: {has_tm_fee}")

    print("=== StrategyBridge AST Audit PASSED ===")

if __name__ == "__main__":
    audit_strategy_bridge("AGY2_FundAdvisory/strategy_bridge.py")
