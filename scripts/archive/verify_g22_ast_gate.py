"""
G22 AST Static Validation & Contract Enforcement Gate
=====================================================
Performs strict static AST inspection, reflection checks, and dynamic invariants
specified in G22 Task 5.
"""

import ast
import json
import os
import sys
from pathlib import Path

WORKSPACE_ROOT = Path(r"d:\Google\Workspace\Wind")
CORE_DIR = WORKSPACE_ROOT / "AGY2_FundAdvisory"

sys.path.insert(0, str(CORE_DIR))
sys.path.insert(0, str(WORKSPACE_ROOT))

CORE_14_FILES = [
    "advisory_engine.py",
    "app_gui.py",
    "cache_manager.py",
    "data_loader.py",
    "holdout_vault.py",
    "judge_engine.py",
    "market_screener.py",
    "multi_ledger_manager.py",
    "portfolio_manager.py",
    "portfolio_optimizer.py",
    "simple_rotation_strategy.py",
    "strategy_bridge.py",
    "trading_clock_fee.py",
    "winrate_engine.py"
]

BANNED_STRINGS = [
    "add_holding_from_snapshot",
    "refresh_realtime_quotes",
    "profit_loss_pct",
    "generate_daily_chief_advisor_memo",
    "rad_tab2_scenario_mode_key",
    "1.2 bps"
]

REQUIRED_CALLS = [
    "parse_screenshot_ocr_holdings",
    "parse_smart_text_holdings",
    "import_from_smart_text",
    "search_funds_in_catalog",
    "calculate_vwap_execution_slippage",
    "sync_holdings_live_nav",
    "undo"
]

def check_step1():
    errors = []
    print("\n--- [Step 1] Check ast.parse on all 14 core Python files ---")
    for filename in CORE_14_FILES:
        filepath = CORE_DIR / filename
        if not filepath.exists():
            errors.append(f"File not found: {filename}")
            continue
        content = filepath.read_text(encoding="utf-8")
        try:
            ast.parse(content, filename=str(filepath))
            print(f"  ✓ {filename} ({len(content)} chars) parsed successfully.")
        except SyntaxError as e:
            errors.append(f"Syntax error in {filename}: {e}")
    return errors

def check_step2():
    errors = []
    print("\n--- [Step 2] AST Walk app_gui.py for pm & mlm_inst accesses & Banned Strings ---")
    app_gui_path = CORE_DIR / "app_gui.py"
    source = app_gui_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename="app_gui.py")

    from portfolio_manager import PortfolioManager
    from multi_ledger_manager import MultiLedgerManager

    pm_dummy = PortfolioManager()
    mlm_dummy = MultiLedgerManager()

    pm_attrs = set()
    mlm_attrs = set()

    class AttributeVisitor(ast.NodeVisitor):
        def visit_Attribute(self, node):
            if isinstance(node.value, ast.Name):
                if node.value.id == "pm":
                    if not node.attr.startswith("_"):
                        pm_attrs.add(node.attr)
                elif node.value.id in ("mlm_inst", "mlm"):
                    if not node.attr.startswith("_"):
                        mlm_attrs.add(node.attr)
            self.generic_visit(node)

    visitor = AttributeVisitor()
    visitor.visit(tree)

    missing_pm = []
    for attr in sorted(pm_attrs):
        has = hasattr(pm_dummy, attr) or hasattr(PortfolioManager, attr)
        if not has:
            missing_pm.append(attr)

    missing_mlm = []
    for attr in sorted(mlm_attrs):
        has = hasattr(mlm_dummy, attr) or hasattr(MultiLedgerManager, attr)
        if not has:
            missing_mlm.append(attr)

    if missing_pm:
        errors.append(f"app_gui.py accesses non-existent attributes on pm (PortfolioManager): {missing_pm}")
    else:
        print(f"  ✓ All {len(pm_attrs)} pm attributes exist on PortfolioManager.")

    if missing_mlm:
        errors.append(f"app_gui.py accesses non-existent attributes on mlm_inst (MultiLedgerManager): {missing_mlm}")
    else:
        print(f"  ✓ All {len(mlm_attrs)} mlm attributes exist on MultiLedgerManager.")

    # Check banned strings
    found_banned = []
    for b in BANNED_STRINGS:
        cnt = source.count(b)
        if cnt > 0:
            found_banned.append((b, cnt))
    if found_banned:
        errors.append(f"Banned strings found in app_gui.py: {found_banned}")
    else:
        print("  ✓ All banned strings are absent from app_gui.py.")

    return errors

def check_step3():
    errors = []
    print("\n--- [Step 3] Check required calls present in app_gui.py ---")
    app_gui_path = CORE_DIR / "app_gui.py"
    source = app_gui_path.read_text(encoding="utf-8")

    missing_calls = []
    for req in REQUIRED_CALLS:
        cnt = source.count(req)
        if cnt == 0:
            missing_calls.append(req)
        else:
            print(f"  ✓ Required call '{req}' present ({cnt} occurrences)")
    if missing_calls:
        errors.append(f"Required calls missing from app_gui.py: {missing_calls}")
    return errors

def check_step4():
    errors = []
    print("\n--- [Step 4] Check render_causal_intelligence_card uses st.expander(expanded=False) ---")
    app_gui_path = CORE_DIR / "app_gui.py"
    source = app_gui_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename="app_gui.py")

    target_func = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "render_causal_intelligence_card":
            target_func = node
            break

    if target_func is None:
        errors.append("render_causal_intelligence_card function not found in app_gui.py!")
        return errors

    has_expander = False
    expanded_is_false = False

    for child in ast.walk(target_func):
        if isinstance(child, ast.Call):
            if isinstance(child.func, ast.Attribute) and child.func.attr == "expander":
                has_expander = True
                for kw in child.keywords:
                    if kw.arg == "expanded":
                        if isinstance(kw.value, ast.Constant) and kw.value.value is False:
                            expanded_is_false = True

    if not has_expander:
        errors.append("render_causal_intelligence_card does not use st.expander!")
    elif not expanded_is_false:
        errors.append("render_causal_intelligence_card st.expander does not have expanded=False!")
    else:
        print("  ✓ render_causal_intelligence_card correctly uses st.expander(expanded=False).")

    return errors

def check_step5():
    errors = []
    print("\n--- [Step 5] Verify 29-fund portfolio deep loss count == 18 & fuzzy matching ---")
    from portfolio_manager import PortfolioManager, fuzzy_match_fund_by_name
    from multi_ledger_manager import MultiLedgerManager

    # Fuzzy matching tests
    test_cases = [
        ("华泰柏瑞红利低波ETF联接A", "007466"),
        ("招商中证红利ETF联接A", "012643"),
        ("博时黄金ETF联接C", "002611")
    ]
    for query_name, expected_code in test_cases:
        res = fuzzy_match_fund_by_name(query_name)
        matched_code = res.get("fund_code") if isinstance(res, dict) else res
        if matched_code != expected_code:
            errors.append(f"Fuzzy match failed for '{query_name}': expected {expected_code}, got {matched_code}")
        else:
            print(f"  ✓ Fuzzy matched '{query_name}' -> {matched_code}")

    # 29-fund deep loss verification
    mlm = MultiLedgerManager.get_instance()
    pm_combat = mlm.get_pm("combat_29_funds")

    if len(pm_combat.holdings) != 29:
        errors.append(f"combat_29_funds holdings count is {len(pm_combat.holdings)} (expected 29). Note: working tree combat_29_funds.json may have uncommitted modifications!")
    else:
        deep_loss_funds = [
            c for c, h in pm_combat.holdings.items()
            if float(getattr(h, "floating_pnl_pct", getattr(h, "pnl_pct", 0.0))) < -10.0
        ]
        if len(deep_loss_funds) != 18:
            errors.append(f"Deep loss funds count is {len(deep_loss_funds)} (expected 18).")
        else:
            print(f"  ✓ 29-fund portfolio deep loss count == 18 ({len(deep_loss_funds)} detected).")

    return errors

def main():
    print("=================================================================")
    print("       G22 AST Static Validation & Release Gate Verification      ")
    print("=================================================================")
    all_errors = {}
    all_errors["Step 1"] = check_step1()
    all_errors["Step 2"] = check_step2()
    all_errors["Step 3"] = check_step3()
    all_errors["Step 4"] = check_step4()
    all_errors["Step 5"] = check_step5()

    print("\n=================================================================")
    print("                       GATE REPORT SUMMARY                       ")
    print("=================================================================")
    total_failures = sum(len(errs) for errs in all_errors.values())
    for step, errs in all_errors.items():
        if not errs:
            print(f"{step}: PASSED ✓")
        else:
            print(f"{step}: FAILED ✗ ({len(errs)} issues)")
            for e in errs:
                print(f"    - {e}")

    if total_failures == 0:
        print("\n🎉 ALL 5 G22 VALIDATION GATES PASSED 100%!")
        sys.exit(0)
    else:
        print(f"\n⚠️ Total failures: {total_failures}. Release gate blocked until fixed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
