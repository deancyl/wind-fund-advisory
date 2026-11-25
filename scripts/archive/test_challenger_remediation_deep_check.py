# -*- coding: utf-8 -*-
"""
scripts/test_challenger_remediation_deep_check.py
Adversarial Empirical Verification by Challenger Remediation R8-M1.

Exhaustively verifies:
1. Rule 16 Invariant: 000922 points in offline/fallback mode strictly in [5000.0, 6500.0].
2. ETF Proportionality: ETF daily change amounts ('chg') strictly proportional to ETF price ('pt * chg_pct / 100').
3. No Flat 0.00% Rows: Zero flat 0.00% rows exist across all corridor items in offline calculations.
4. Adversarial robustness: Hostile inputs, mock corruptions, extreme boundary conditions.
"""

import sys
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))
if str(WORKSPACE_ROOT / "AGY2_FundAdvisory") not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT / "AGY2_FundAdvisory"))

from AGY2_FundAdvisory.data_loader import (
    calc_offline_2day_return,
    fetch_custom_realtime_indices,
    fetch_batch_realtime_indices,
    get_index_corridor_metrics,
    EXPANDED_INDEX_CATALOG,
    _REALTIME_CORRIDOR_CACHE,
    IndexValuationEngine
)


def run_deep_check():
    passed = 0
    failed = 0
    findings = []

    def check(cond, msg):
        nonlocal passed, failed
        if cond:
            passed += 1
            print(f"  [PASS] {msg}")
        else:
            failed += 1
            findings.append(msg)
            print(f"  [FAIL] {msg}")

    print("======================================================================")
    print("CHALLENGER REMEDIATION R8-M1: DEEP EMPIRICAL ADVERSARIAL VERIFICATION")
    print("======================================================================")

    # --------------------------------------------------------------------------
    # Focus Area 1: Rule 16 Invariant for 000922
    # --------------------------------------------------------------------------
    print("\n--- FOCUS 1: 000922 Rule 16 Points Invariant [5000.0, 6500.0] ---")
    
    # 1.1 Direct offline return
    res_922 = calc_offline_2day_return("000922")
    check(res_922 is not None, "calc_offline_2day_return('000922') is not None")
    if res_922:
        pt, chg, chg_pct = res_922
        check(5000.0 <= pt <= 6500.0, f"000922 offline point {pt} strictly in [5000.0, 6500.0] (observed: {pt})")
        check(pt != 12189.99, f"000922 point is decoupled from H00922 (not 12189.99)")
        check(pt != 3248.31, f"000922 point is decoupled from 000015 (not 3248.31)")
        check(abs(chg - round(pt * chg_pct / 100.0, 2)) < 0.02, f"000922 offline chg ({chg}) matches pt * chg_pct / 100 ({round(pt * chg_pct / 100.0, 2)})")

    # 1.2 Offline simulation with complete network blackout
    _REALTIME_CORRIDOR_CACHE.clear()
    with patch("urllib.request.urlopen", side_effect=Exception("Total network blackout")):
        corridor = fetch_custom_realtime_indices(["000922"], use_cache=False)
        check(len(corridor) == 1, "fetch_custom_realtime_indices returns 1 item under blackout")
        c_pt = corridor[0]["point"]
        check(5000.0 <= c_pt <= 6500.0, f"Blackout: 000922 point {c_pt} strictly in [5000.0, 6500.0]")

    # 1.3 Hostile injection: Network returns out-of-bounds point for 000922 (e.g., 3300.0 or 12189.99)
    # The guardrail in fetch_custom_realtime_indices lines 1746-1749 must clamp it back to fb_point!
    _REALTIME_CORRIDOR_CACHE.clear()
    hostile_resp = {
        "data": {
            "diff": [
                {"f12": "000922", "f14": "中证红利", "f2": 330000, "f3": 120, "f4": 3960}
            ]
        }
    }
    m = MagicMock()
    m.read.return_value = json.dumps(hostile_resp).encode("utf-8")
    m.__enter__.return_value = m
    with patch("urllib.request.urlopen", return_value=m):
        corridor_hostile = fetch_custom_realtime_indices(["000922"], use_cache=False)
        h_pt = corridor_hostile[0]["point"]
        check(5000.0 <= h_pt <= 6500.0, f"Hostile network point 3300.0 clamped by Rule 16 guardrail to {h_pt}")

    # --------------------------------------------------------------------------
    # Focus Area 2: ETF Proportionality (Eliminating +40.33 on 8.43 ETF)
    # --------------------------------------------------------------------------
    print("\n--- FOCUS 2: ETF Daily Change Proportionality ---")

    # 2.1 518880 Gold ETF direct offline check
    res_518880 = calc_offline_2day_return("518880")
    check(res_518880 is not None, "calc_offline_2day_return('518880') is not None")
    if res_518880:
        pt, chg, chg_pct = res_518880
        check(5.0 <= pt <= 15.0, f"518880 price {pt} in realistic ETF range [5.0, 15.0] (not AU9999 spot ~1465)")
        expected_chg = round(pt * (chg_pct / 100.0), 3)
        check(abs(chg - expected_chg) < 0.005, f"518880 chg={chg} matches pt * chg_pct / 100={expected_chg} (diff={abs(chg - expected_chg):.4f})")
        check(chg < 1.0, f"518880 chg={chg} is proportional (< 1.0 yuan, NOT +40.33 yuan)")

    # 2.2 518880 Weekend flat mock (Eastmoney returns f2=8434, f3=0, f4=0)
    _REALTIME_CORRIDOR_CACHE.clear()
    mock_gold_flat = {
        "data": {
            "diff": [
                {"f12": "518880", "f14": "黄金ETF", "f2": 8434, "f3": 0, "f4": 0}
            ]
        }
    }
    m_gold = MagicMock()
    m_gold.read.return_value = json.dumps(mock_gold_flat).encode("utf-8")
    m_gold.__enter__.return_value = m_gold
    with patch("urllib.request.urlopen", return_value=m_gold):
        res_flat = fetch_custom_realtime_indices(["518880"], use_cache=False)
        item = res_flat[0]
        f_pt = item["point"]
        f_chg = item["change"]
        f_pct = item["change_pct"]
        check(abs(f_pct) > 0.001, f"Weekend flat 518880 replaced with offline pct: {f_pct:+.2f}%")
        expected_f_chg = round(f_pt * (f_pct / 100.0), 3)
        check(abs(f_chg - expected_f_chg) < 0.01, f"Weekend flat 518880 chg={f_chg} proportional to pt={f_pt} (expected={expected_f_chg})")
        check(f_chg < 1.0, f"Weekend flat 518880 chg={f_chg} is eliminated from +40.33 spot contamination")

    # 2.3 513500 S&P 500 ETF check
    res_513500 = calc_offline_2day_return("513500")
    check(res_513500 is not None, "calc_offline_2day_return('513500') is not None")
    if res_513500:
        pt, chg, chg_pct = res_513500
        check(1.0 <= pt <= 10.0, f"513500 price {pt} in ETF range [1.0, 10.0] (not SPX ~5000+)")
        expected_chg = round(pt * (chg_pct / 100.0), 3)
        check(abs(chg - expected_chg) < 0.005, f"513500 chg={chg} matches pt * chg_pct / 100={expected_chg}")

    # 2.4 Exhaustive ETF proportionality test across ALL ETFs in catalog
    print("\n--- Comprehensive ETF Proportionality Audit ---")
    etf_codes = [c for c, m in EXPANDED_INDEX_CATALOG.items() if str(c).startswith(('5', '1')) or m.get("asset_type") in ("etf", "commodity", "qdii", "bond")]
    check(len(etf_codes) >= 20, f"Found {len(etf_codes)} ETFs/commodities/bonds in catalog")
    
    etf_disproportional = []
    for code in etf_codes:
        off = calc_offline_2day_return(code)
        if off:
            pt, chg, chg_pct = off
            expected_chg = round(pt * (chg_pct / 100.0), 3 if pt < 100.0 else 2)
            diff = abs(chg - expected_chg)
            if diff > 0.02:
                etf_disproportional.append((code, pt, chg, chg_pct, expected_chg, diff))
    check(len(etf_disproportional) == 0, f"All {len(etf_codes)} ETFs satisfy proportionality: disproportional count = {len(etf_disproportional)}")
    if etf_disproportional:
        for item in etf_disproportional:
            print(f"    DISPROPORTIONAL: {item}")

    # --------------------------------------------------------------------------
    # Focus Area 3: Zero Flat 0.00% Rows
    # --------------------------------------------------------------------------
    print("\n--- FOCUS 3: Zero Flat 0.00% Rows Invariant ---")

    # 3.1 All items in EXPANDED_INDEX_CATALOG under offline blackout
    _REALTIME_CORRIDOR_CACHE.clear()
    all_codes = list(EXPANDED_INDEX_CATALOG.keys())
    with patch("urllib.request.urlopen", side_effect=Exception("Network blackout")):
        all_corridor = fetch_custom_realtime_indices(all_codes, use_cache=False)
        check(len(all_corridor) == len(all_codes), f"Blackout returned all {len(all_codes)} items")
        
        flat_items = []
        for item in all_corridor:
            code = item["code"]
            pct = item["change_pct"]
            pt = item["point"]
            if abs(pct) < 1e-6:
                flat_items.append((code, item["name"], pct, pt))
        check(len(flat_items) == 0, f"ZERO items have flat 0.00% return under offline blackout (flat count = {len(flat_items)})")
        if flat_items:
            for f in flat_items:
                print(f"    FLAT ITEM: {f}")

    # 3.2 Micro-return ETF (511360 短融ETF) precision check
    res_511360 = calc_offline_2day_return("511360")
    check(res_511360 is not None, "calc_offline_2day_return('511360') is not None")
    if res_511360:
        pt, chg, chg_pct = res_511360
        check(abs(chg_pct) > 0, f"511360 micro-return is non-zero: {chg_pct}% (not rounded to 0.00%)")

    # --------------------------------------------------------------------------
    # Focus Area 4: Boundary & Stress Invariants
    # --------------------------------------------------------------------------
    print("\n--- FOCUS 4: Boundary & Extreme Stress Testing ---")

    # 4.1 Empty / None inputs to get_index_corridor_metrics
    m_zero = get_index_corridor_metrics("000300", latest_pt=0.0)
    check(m_zero["ma20"] > 0, "get_index_corridor_metrics handles latest_pt=0.0")
    check(abs(m_zero["bias_20"]) < 50.0, f"get_index_corridor_metrics returns sane historical bias_20 ({m_zero['bias_20']:.2f}%) when pt=0.0 (graceful fallback to s_last)")

    m_none = get_index_corridor_metrics("000300", latest_pt=None)
    check(m_none["ma20"] > 0, "get_index_corridor_metrics handles latest_pt=None")

    # 4.2 Single Source of Truth consistency check: IndexValuationEngine staticmethods
    check(IndexValuationEngine.calc_offline_2day_return == calc_offline_2day_return, "IndexValuationEngine.calc_offline_2day_return is bound")
    check(IndexValuationEngine.fetch_custom_realtime_indices == fetch_custom_realtime_indices, "IndexValuationEngine.fetch_custom_realtime_indices is bound")
    check(IndexValuationEngine.fetch_batch_realtime_indices == fetch_batch_realtime_indices, "IndexValuationEngine.fetch_batch_realtime_indices is bound")

    print("\n======================================================================")
    print(f"SUMMARY: {passed} PASSED, {failed} FAILED")
    print("======================================================================")

    if failed > 0:
        print("FAILURES DETECTED:")
        for f in findings:
            print(f"  - {f}")
        return False
    else:
        print("ALL DEEP EMPIRICAL CHECKS PASSED WITH ZERO DEFECTS.")
        return True


if __name__ == "__main__":
    success = run_deep_check()
    sys.exit(0 if success else 1)
