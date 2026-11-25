# -*- coding: utf-8 -*-
"""
Milestone 2 Reviewer Independent Verification & Adversarial Stress-Test Script
"""
import sys
import os

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

import json
import pandas as pd
import subprocess

def test_parquet_data_lake():
    print("=== [1] Verifying Parquet Data Lake Cutoff Dates ===")
    bond_path = os.path.join(WORKSPACE_ROOT, "data", "macro", "bond_zh_us_rate.parquet")
    assert os.path.exists(bond_path), f"File not found: {bond_path}"
    df_bond = pd.read_parquet(bond_path)
    latest_bond = df_bond.iloc[-1]
    print(f"Bond parquet latest row:\n{latest_bond[['date', 'cn_yield_10y', 'us_yield_10y', 'cn_us_spread_10y']]}")
    assert str(latest_bond['date']) == "2026-11-13", f"Expected date 2026-11-13, got {latest_bond['date']}"
    assert 1.50 <= float(latest_bond['cn_yield_10y']) <= 1.70, f"Expected 10Y ~1.61%, got {latest_bond['cn_yield_10y']}"
    assert 5.00 <= float(latest_bond['us_yield_10y']) <= 5.30, f"Expected US 10Y ~5.15%, got {latest_bond['us_yield_10y']}"
    print("[PASS] Bond yield parquet verified.")

    fx_path = os.path.join(WORKSPACE_ROOT, "data", "global", "fx_rates.parquet")
    assert os.path.exists(fx_path), f"File not found: {fx_path}"
    df_fx = pd.read_parquet(fx_path)
    latest_fx = df_fx.iloc[-1]
    print(f"FX parquet latest row:\n{latest_fx[['date', 'usd_cnh', 'usd_cny', 'cnh_cny_spread']]}")
    assert str(latest_fx['date']) == "2026-11-14", f"Expected date 2026-11-14, got {latest_fx['date']}"
    assert 6.50 <= float(latest_fx['usd_cnh']) <= 6.80, f"Expected USD/CNH ~6.6746, got {latest_fx['usd_cnh']}"
    print("[PASS] FX rates parquet verified.")

def test_three_step_chain():
    print("\n=== [2] Verifying 3-Step Information Chain ===")
    from AGY2_FundAdvisory.advisory_engine import generate_chief_advisor_memo
    memo = generate_chief_advisor_memo()
    assert "key_information_insights" in memo, "Missing key_information_insights in memo!"
    insights = memo["key_information_insights"]
    print(f"Number of insights: {len(insights)}")
    assert 3 <= len(insights) <= 5, f"Expected 3-5 items, got {len(insights)}"

    for idx, item in enumerate(insights, 1):
        print(f"\n--- Item {idx}: {item.get('category')} ({item.get('badge')}) ---")
        fact = item.get("key_information", "")
        reasoning = item.get("deep_understanding", "")
        action = item.get("action_taken", "")

        print(f"  [Fact]: {fact}")
        print(f"  [Understanding]: {reasoning}")
        print(f"  [Action]: {action}")

        assert fact, f"Item {idx} missing key_information"
        assert reasoning, f"Item {idx} missing deep_understanding"
        assert action, f"Item {idx} missing action_taken"

        # Check that there are no remaining placeholder or fake constant references
        assert "7.2385" not in fact and "7.2385" not in reasoning and "7.2385" not in action
        assert "4.4200" not in fact and "4.4200" not in reasoning and "4.4200" not in action

    print("\n[PASS] 3-Step Information Chain verified.")

def test_static_fake_constants():
    print("\n=== [3] Checking for Fake Constants in Codebase ===")
    proc = subprocess.run([sys.executable, os.path.join(WORKSPACE_ROOT, "scripts", "find_fake_constants.py")],
                          capture_output=True, text=True)
    print(proc.stdout)
    assert proc.returncode == 0, f"Script failed with code {proc.returncode}"
    assert "SUCCESS: ZERO occurrences of fake constants in all modified files!" in proc.stdout
    print("[PASS] Zero fake constants verified.")

def main():
    try:
        test_parquet_data_lake()
        test_three_step_chain()
        test_static_fake_constants()
        print("\n>>> ALL M2 VERIFICATION CHECKS PASSED <<<")
    except Exception as e:
        print(f"\n[FAIL] Verification error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
