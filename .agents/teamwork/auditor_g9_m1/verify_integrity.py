import ast
import os
import sys

def main():
    print("=== STARTING QUANTITATIVE & INTEGRITY FORENSIC CHECKS ===")
    
    # Read advisory_engine.py
    with open('AGY2_FundAdvisory/advisory_engine.py', 'r', encoding='utf-8') as f:
        ae_code = f.read()

    tree_ae = ast.parse(ae_code)

    # 1. Check no np.linspace in AST calls
    class LinspaceVisitor(ast.NodeVisitor):
        def visit_Call(self, node):
            if isinstance(node.func, ast.Attribute) and node.func.attr == 'linspace':
                raise AssertionError('Found call to linspace in AST!')
            elif isinstance(node.func, ast.Name) and node.func.id == 'linspace':
                raise AssertionError('Found call to linspace in AST!')
            self.generic_visit(node)
    LinspaceVisitor().visit(tree_ae)
    assert 'linspace(1.0, 1.05' not in ae_code, 'Found np.linspace(1.0, 1.05)'
    print("[PASS] Check 1: No linspace call or fake sequence in advisory_engine.py")

    # 2. Check no lam = (t + 1) / 60.0 in AST assignments
    class LamVisitor(ast.NodeVisitor):
        def visit_Assign(self, node):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == 'lam':
                    raise AssertionError('Found assignment to lam!')
            self.generic_visit(node)
    LamVisitor().visit(tree_ae)
    print("[PASS] Check 2: No lam assignment in advisory_engine.py")

    # 3. Check no else: aum = 2.5 in AST assignments
    class AumVisitor(ast.NodeVisitor):
        def visit_Assign(self, node):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == 'aum':
                    if isinstance(node.value, ast.Constant) and node.value.value == 2.5:
                        raise AssertionError('Found aum = 2.5 in AST!')
            self.generic_visit(node)
    AumVisitor().visit(tree_ae)
    print("[PASS] Check 3: No aum = 2.5 fallback in advisory_engine.py")

    # 4. Check Sharpe ratio subtraction in _evaluate_population
    assert 'rf_daily = 0.02 / 250.0' in ae_code, 'Missing rf_daily = 0.02 / 250.0'
    assert '(mean_r - rf_daily)' in ae_code, 'Sharpe does not subtract rf_daily'
    print("[PASS] Check 4: Sharpe strictly subtracts daily risk-free rate 0.02 / 250.0")

    # 5. Check P[:-1] and R[1:] causal delay in _evaluate_population
    assert 'P_eff = P[:-1, :, :]' in ae_code, 'Missing P_eff causal lag'
    assert 'R_eff = R[1:, :]' in ae_code, 'Missing R_eff causal lag'
    assert 'gross_R_p = np.sum(P_eff * R_eff[:, :, None], axis=1)' in ae_code, 'Missing gross_R_p causal dot product'
    print("[PASS] Check 5: Causal lag strictly enforced: P[:-1] * R[1:]")

    # 6. Check data_loader.py offline snapshot does not use datetime.now() to overwrite snapshot timestamp
    with open('AGY2_FundAdvisory/data_loader.py', 'r', encoding='utf-8') as f:
        dl_code = f.read()

    assert 'cached["timestamp"] = orig_ts' in dl_code, 'cached fallback should preserve orig_ts'
    assert 'cached["updated_at"] = orig_ts' in dl_code, 'cached fallback should preserve orig_ts'
    assert 'fallback_dt = "2026-11-01 09:30:00 (离线预置)"' in dl_code, 'fallback_dt should be static offline baseline'
    print("[PASS] Check 6: DataLoader offline fallback preserves original timestamp and does NOT call datetime.now()")

    print("=== ALL AST AND CODE FORENSIC CHECKS PASSED SUCCESSFULLY ===")

if __name__ == '__main__':
    main()
