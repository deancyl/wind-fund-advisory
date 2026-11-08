"""
Verification script for Milestone 2: Tab 2 Three-Block Refactoring.
Verifies all AST, regex, widget key, and regression contracts.
"""
import ast
import re
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
TARGET_FILE = WORKSPACE / "AGY2_FundAdvisory" / "app_gui.py"

def test_milestone2_static_contracts():
    code = TARGET_FILE.read_text(encoding="utf-8")
    
    # 1. Tab 2 section extraction
    assert "with tab_holdings_and_rebalance:" in code
    t2_section = code.split("with tab_holdings_and_rebalance:")[1].split("def render_tab3")[0]
    
    # 2. Noise Elimination checks
    assert "render_workflow_step_indicator" not in t2_section, "Step indicator must be removed from Tab 2!"
    assert "步骤一：" not in t2_section, "步骤一 header must be removed!"
    assert "步骤二：" not in t2_section, "步骤二 header must be removed!"
    assert "步骤三：" not in t2_section, "步骤三 header must be removed!"
    print("PASS: Noise elimination verified (no step indicators or step 1/2/3 headers)")

    # 3. Slider uniqueness & compatibility comment
    slider_keys = re.findall(r'key=["\']tab2_rebal_buf_slider["\']', code)
    assert len(slider_keys) == 1, f"tab2_rebal_buf_slider must appear exactly once globally, found {len(slider_keys)}"
    assert "# tab2_rebal_buf_slider_bot" in code, "Missing '# tab2_rebal_buf_slider_bot' compatibility comment"
    print("PASS: Single slider and compatibility comment verified")

    # 4. AST verification of dual-view branch isolation
    tree = ast.parse(code, filename=str(TARGET_FILE))
    t2_if_node = None
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            test_unparsed = ast.unparse(node.test) if hasattr(ast, "unparse") else ""
            if "is_t2_main_mode" in test_unparsed:
                t2_if_node = node
                break

    assert t2_if_node is not None, "Missing 'if is_t2_main_mode:' branch!"
    assert len(t2_if_node.orelse) > 0, "Missing 'else:' branch for dock tabs!"
    
    else_code = ast.unparse(t2_if_node.orelse) if hasattr(ast, "unparse") else ""
    assert "dock_tab1" in else_code, "dock_tab1 must be in else: branch!"
    assert "dock_tab6" in else_code, "dock_tab6 must be in else: branch!"
    
    body_code = ast.unparse(t2_if_node.body) if hasattr(ast, "unparse") else ""
    assert "dock_tab1, dock_tab2" not in body_code, "dock_tabs must not be in main mode body!"
    print("PASS: AST dual-view branch isolation verified")

    # 5. Widget key contracts
    required_keys = [
        "rad_tab2_view_mode",
        "btn_tab2_sync",
        "btn_bar_add_holding",
        "btn_confirm_cash_pop_tb",
        "btn_sync_holdings_tab2",
        "btn_pop_del_confirm_tab2",
        "btn_tab2_diagnose",
        "btn_tab2_all",
        "btn_confirm_follow_rebalance_tab2",
        "sel_tab2_vwap_schedule_item",
        "btn_tab2_load_demo",
        "btn_tab2_undo",
        "tab2_rebal_buf_slider",
    ]
    for k in required_keys:
        assert k in code, f"Missing required widget key/contract: {k}"
    print(f"PASS: All {len(required_keys)} critical widget keys and hooks verified")

    # 6. Check elimination of 3 Net Utility Gate blue boxes
    net_util_matches = re.findall(r"买方投顾调仓净效用门禁|Net Utility Gate", t2_section)
    assert len(net_util_matches) == 0, f"Found remaining Net Utility Gate boxes: {net_util_matches}"
    print("PASS: 3 repetitive Net Utility Gate blue boxes eliminated")

if __name__ == "__main__":
    test_milestone2_static_contracts()
    print("ALL MILESTONE 2 STATIC CONTRACTS PASSED PERFECTLY!")
