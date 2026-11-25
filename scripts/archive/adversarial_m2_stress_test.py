# -*- coding: utf-8 -*-
"""
Adversarial Stress Test Suite for Milestone 2
Tests failure modes, edge cases, integrity attacks, and degraded environments.
"""
import sys
import os
from unittest.mock import patch, MagicMock

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

def run_stress_tests():
    print("=== [Adversarial Stress Test 1] Extreme Exchange Rates & Corrupted Inputs ===")
    from AGY2_FundAdvisory.data_loader import DataLoader
    from AGY2_FundAdvisory.advisory_engine import generate_chief_advisor_memo, compute_ten_dimension_votes

    # Attack 1.1: Extreme rate < 5.0 (e.g. 0.0, 1.2, negative)
    with patch("urllib.request.urlopen", side_effect=Exception("Network down")):
        with patch("pandas.read_parquet", side_effect=Exception("Parquet corrupt")):
            res = DataLoader.fetch_realtime_usdcnh_fx(use_cache=False)
            print(f"Fallback on complete corruption/offline: rate={res['rate']}, source={res['source']}")
            assert 5.0 <= res["rate"] <= 9.0, f"Rate should fall back safely, got {res['rate']}"
            assert res["rate"] != 7.2385, "Must not fall back to fake constant 7.2385"

    # Attack 1.2: Sina returns malformed string (e.g. non-numeric or out-of-range)
    malformed_resp = MagicMock()
    malformed_resp.read.return_value = 'var hq_str_fx_susdcnh="USDCNH,99.99,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,2026-11-14";'.encode("gbk")
    with patch("urllib.request.urlopen", return_value=malformed_resp):
        res = DataLoader.fetch_realtime_usdcnh_fx(use_cache=False)
        print(f"Attack with 99.99: rate={res['rate']}, source={res['source']}")
        assert res["rate"] != 99.99, "Extreme out-of-bounds rate (99.99) should be intercepted!"
        assert 5.0 <= res["rate"] <= 9.0, f"Intercepted rate should be in valid range [5.0, 9.0], got {res['rate']}"

    # Attack 1.3: Sina returns zero or negative rate
    malformed_resp.read.return_value = 'var hq_str_fx_susdcnh="USDCNH,-1.5,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,2026-11-14";'.encode("gbk")
    with patch("urllib.request.urlopen", return_value=malformed_resp):
        res = DataLoader.fetch_realtime_usdcnh_fx(use_cache=False)
        print(f"Attack with -1.5: rate={res['rate']}, source={res['source']}")
        assert res["rate"] > 0, "Negative rate should be intercepted!"

    print("[PASS] Extreme exchange rates successfully defended.")

    print("\n=== [Adversarial Stress Test 2] AkShare Network Failure in sync_macro_and_fx_parquet_if_stale ===")
    # Attack 2.1: AkShare raises TimeoutError / ConnectionError
    with patch("akshare.bond_zh_us_rate", side_effect=TimeoutError("Connection timed out")):
        sync_res = DataLoader.sync_macro_and_fx_parquet_if_stale(force=True)
        print(f"Sync result during network timeout: {sync_res['details']['bond']}")
        assert "fallback" in sync_res["details"]["bond"], "Should gracefully fall back"
        assert sync_res["treasury_date"] == "2026-11-13", f"Should retain existing parquet date, got {sync_res['treasury_date']}"

    print("[PASS] AkShare failure graceful degradation verified.")

    print("\n=== [Adversarial Stress Test 3] generate_chief_advisor_memo Under Empty/Adversarial Inputs ===")
    # Attack 3.1: Completely empty snapshot
    memo_empty = generate_chief_advisor_memo(snapshot={})
    assert "key_information_insights" in memo_empty
    insights = memo_empty["key_information_insights"]
    assert len(insights) >= 3
    for it in insights:
        assert it["key_information"] and it["deep_understanding"] and it["action_taken"]
    print(f"Memo generated {len(insights)} valid insights with empty snapshot.")

    # Attack 3.2: Numerical boundary snapshot with None, extreme numbers
    malformed_snapshot = {
        "spot_usdcnh": None,
        "us_treasury_10y": None,
        "cgb_10y": 0.0,
        "erp_percentile": -999.0
    }
    memo_malformed = generate_chief_advisor_memo(snapshot=malformed_snapshot)
    assert "key_information_insights" in memo_malformed
    insights_mal = memo_malformed["key_information_insights"]
    assert len(insights_mal) >= 3
    print(f"Memo generated {len(insights_mal)} valid insights with boundary snapshot.")

    print("\n=== [Adversarial Stress Test 4] Parquet Data Lake Integrity & Non-corruption ===")
    # Verify file sizes, schema, non-empty, and monotonic dates
    import pandas as pd
    bond_df = pd.read_parquet(os.path.join(WORKSPACE_ROOT, "data", "macro", "bond_zh_us_rate.parquet"))
    assert "date" in bond_df.columns
    assert "cn_yield_10y" in bond_df.columns
    assert "us_yield_10y" in bond_df.columns
    assert len(bond_df) > 9000, f"Expected >9000 rows, got {len(bond_df)}"
    assert bond_df["date"].tail(50).is_monotonic_increasing

    fx_df = pd.read_parquet(os.path.join(WORKSPACE_ROOT, "data", "global", "fx_rates.parquet"))
    assert "date" in fx_df.columns
    assert "usd_cnh" in fx_df.columns
    assert len(fx_df) > 3000, f"Expected >3000 rows, got {len(fx_df)}"
    assert fx_df["date"].tail(50).is_monotonic_increasing
    print("[PASS] Parquet integrity and monotonic ordering verified.")

    print("\n=== [Adversarial Stress Test 5] Check for Hidden Shortcuts & Fabrication ===")
    code_files = [
        "AGY2_FundAdvisory/data_loader.py",
        "AGY2_FundAdvisory/advisory_engine.py",
        "AGY2_FundAdvisory/strategy_bridge.py",
        "AGY2_FundAdvisory/portfolio_manager.py",
        "AGY2_FundAdvisory/app_gui.py",
    ]
    for rel_path in code_files:
        full_path = os.path.join(WORKSPACE_ROOT, rel_path)
        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
            src = f.read()
            assert "7.2385" not in src, f"Violation in {rel_path}: 7.2385 found!"
            assert "4.4200" not in src, f"Violation in {rel_path}: 4.4200 found!"
            assert "278.2" not in src, f"Violation in {rel_path}: 278.2 found!"

    print("[PASS] No hidden shortcuts or fake constants found.")

    print("\n>>> ALL ADVERSARIAL STRESS TESTS PASSED SUCCESSFULLY <<<")

if __name__ == "__main__":
    run_stress_tests()
