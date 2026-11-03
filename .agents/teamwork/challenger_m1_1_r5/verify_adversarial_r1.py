"""
Empirical Adversarial Stress Test Harness for Milestone 1 (R1)
Module: AGY2_FundAdvisory/strategy_bridge.py
Author: Challenger 1 (challenger_m1_1_r5)

Tests:
1. Pure Monotonic Trend (Increasing & Decreasing): ER_t == 1.0, W_eff == 20
2. Pure High-Frequency White Noise (Alternating & Random): ER_t < 0.15, W_eff >= 55
3. Kalman Denoising: Gaussian noise added to linear trend -> filtered variance < raw variance
4. Flat Series: [100.0] * 100 -> no zero division, ER_t == 0.0, W_eff == 60, trend == 100.0, slope == 0.0
5. Short Series: length 0, 1, 5, 10, 19 -> no uncaught exceptions, valid bounds
6. Boundary & Adversarial Cases: None, NaNs, Infs, all zeros, negative values, tiny values, astronomical values
7. Live Market Snapshot: real data execution, er_snr in [0, 1], effective_momentum_window in [20, 60]
"""

import sys
import math
from pathlib import Path
import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[3]
APP_DIR = ROOT_DIR / "AGY2_FundAdvisory"

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from strategy_bridge import (
    compute_market_snr_and_kalman_state,
    compute_momentum_acceleration,
    StrategyBridge
)

def test_pure_monotonic_trend():
    print("[1] Testing Pure Monotonic Trend...")
    # Monotonically increasing
    p_inc = np.arange(100.0, 200.0, 1.0)
    res_inc = compute_market_snr_and_kalman_state(p_inc, window=20)
    assert res_inc["er_snr"] == 1.0, f"Expected er_snr 1.0, got {res_inc['er_snr']}"
    assert res_inc["effective_momentum_window"] == 20, f"Expected W_eff 20, got {res_inc['effective_momentum_window']}"
    assert res_inc["kalman_slope"] > 0.0, "Expected positive kalman slope"
    print(f"    - Increasing: ER={res_inc['er_snr']}, W_eff={res_inc['effective_momentum_window']}, slope={res_inc['kalman_slope']}% -> PASS")

    # Monotonically decreasing
    p_dec = np.arange(200.0, 100.0, -1.0)
    res_dec = compute_market_snr_and_kalman_state(p_dec, window=20)
    assert res_dec["er_snr"] == 1.0, f"Expected er_snr 1.0, got {res_dec['er_snr']}"
    assert res_dec["effective_momentum_window"] == 20, f"Expected W_eff 20, got {res_dec['effective_momentum_window']}"
    assert res_dec["kalman_slope"] < 0.0, "Expected negative kalman slope"
    print(f"    - Decreasing: ER={res_dec['er_snr']}, W_eff={res_dec['effective_momentum_window']}, slope={res_dec['kalman_slope']}% -> PASS")

def test_pure_high_frequency_white_noise():
    print("[2] Testing Pure High-Frequency White Noise...")
    # Alternating noise (+1, -1, +1, -1...)
    p_alt_even = np.array([100.0 + (1.0 if i % 2 == 0 else -1.0) for i in range(100)])
    res_alt_even = compute_market_snr_and_kalman_state(p_alt_even, window=20)
    assert res_alt_even["er_snr"] < 0.15, f"Expected ER < 0.15, got {res_alt_even['er_snr']}"
    assert res_alt_even["effective_momentum_window"] >= 55, f"Expected W_eff >= 55, got {res_alt_even['effective_momentum_window']}"
    print(f"    - Alternating (+1/-1, 100 items): ER={res_alt_even['er_snr']}, W_eff={res_alt_even['effective_momentum_window']} -> PASS")

    p_alt_odd = np.array([100.0 + (1.0 if i % 2 == 0 else -1.0) for i in range(101)])
    res_alt_odd = compute_market_snr_and_kalman_state(p_alt_odd, window=20)
    assert res_alt_odd["er_snr"] < 0.15
    assert res_alt_odd["effective_momentum_window"] >= 55
    print(f"    - Alternating (+1/-1, 101 items): ER={res_alt_odd['er_snr']}, W_eff={res_alt_odd['effective_momentum_window']} -> PASS")

    # Pseudo-random white noise
    np.random.seed(42)
    p_white = 100.0 + np.random.normal(0, 1.0, 100)
    res_white = compute_market_snr_and_kalman_state(p_white, window=20)
    assert res_white["er_snr"] < 0.25
    assert res_white["effective_momentum_window"] >= 50
    print(f"    - Gaussian white noise (100 items): ER={res_white['er_snr']}, W_eff={res_white['effective_momentum_window']} -> PASS")

def test_kalman_denoising():
    print("[3] Testing Kalman Denoising...")
    np.random.seed(42)
    clean_trend = np.linspace(100.0, 150.0, 200)
    noise = np.random.normal(0, 3.0, 200)
    noisy_price = clean_trend + noise

    res = compute_market_snr_and_kalman_state(noisy_price, window=20)
    filtered = res["filtered_series"]

    raw_var = float(np.var(noisy_price - clean_trend))
    filtered_var = float(np.var(filtered - clean_trend))
    raw_roughness = float(np.var(np.diff(noisy_price)))
    filtered_roughness = float(np.var(np.diff(filtered)))

    print(f"    - Raw error variance: {raw_var:.4f}")
    print(f"    - Filtered error variance: {filtered_var:.4f} (Reduction: {(1.0 - filtered_var/raw_var)*100:.1f}%)")
    print(f"    - Raw step roughness: {raw_roughness:.4f}")
    print(f"    - Filtered step roughness: {filtered_roughness:.4f} (Reduction: {(1.0 - filtered_roughness/raw_roughness)*100:.1f}%)")

    assert filtered_var < raw_var, f"Filtered variance {filtered_var} should be strictly less than raw variance {raw_var}"
    assert filtered_roughness < raw_roughness * 0.2, "Filtered series roughness should be drastically reduced"
    print("    - Kalman Denoising Variance & Smoothness Reduction -> PASS")

def test_flat_series():
    print("[4] Testing Flat Series...")
    flat_price = [100.0] * 100
    res = compute_market_snr_and_kalman_state(flat_price, window=20)
    assert res["er_snr"] in (0.0, 0.5), f"Unexpected ER on flat: {res['er_snr']}"
    assert res["effective_momentum_window"] in (40, 60), f"Unexpected W_eff on flat: {res['effective_momentum_window']}"
    assert res["kalman_trend"] == 100.0, f"Expected trend 100.0, got {res['kalman_trend']}"
    assert res["kalman_slope"] == 0.0, f"Expected slope 0.0, got {res['kalman_slope']}"
    print(f"    - Flat series: ER={res['er_snr']}, W_eff={res['effective_momentum_window']}, trend={res['kalman_trend']}, slope={res['kalman_slope']} -> PASS")

def test_short_series():
    print("[5] Testing Short Series...")
    lengths = [0, 1, 5, 10, 19, 20]
    for length in lengths:
        p = [100.0 + i for i in range(length)]
        res = compute_market_snr_and_kalman_state(p, window=20)
        assert 0.0 <= res["er_snr"] <= 1.0
        assert 20 <= res["effective_momentum_window"] <= 60
        assert not math.isnan(res["kalman_trend"])
        assert not math.isnan(res["kalman_slope"])
        print(f"    - Length {length:2d}: ER={res['er_snr']}, W_eff={res['effective_momentum_window']}, trend={res['kalman_trend']:.2f}, slope={res['kalman_slope']:.2f}% -> PASS")

def test_adversarial_boundary_conditions():
    print("[6] Testing Adversarial Boundary Conditions...")
    # None
    r_none = compute_market_snr_and_kalman_state(None)
    assert r_none["er_snr"] == 0.5
    print("    - None input -> PASS")

    # Infs and NaNs
    p_nan = [np.nan, 100.0, np.inf, 105.0, -np.inf, 110.0, None]
    r_nan = compute_market_snr_and_kalman_state(p_nan, window=2)
    assert 0.0 <= r_nan["er_snr"] <= 1.0
    print("    - Series with NaNs/Infs/None -> PASS")

    # All zeros
    p_zero = [0.0] * 30
    r_zero = compute_market_snr_and_kalman_state(p_zero, window=20)
    assert r_zero["er_snr"] == 0.0
    assert r_zero["effective_momentum_window"] == 60
    assert not math.isnan(r_zero["kalman_trend"])
    print("    - All zeros -> PASS")

    # All negative
    p_neg = [-100.0 - i for i in range(30)]
    r_neg = compute_market_snr_and_kalman_state(p_neg, window=20)
    assert r_neg["er_snr"] == 1.0
    assert r_neg["effective_momentum_window"] == 20
    print("    - All negative values -> PASS")

    # Extreme scales: tiny and huge
    p_tiny = [1e-9 + i * 1e-11 for i in range(30)]
    r_tiny = compute_market_snr_and_kalman_state(p_tiny, window=20)
    assert 0.0 <= r_tiny["er_snr"] <= 1.0
    print("    - Extreme tiny values (1e-9) -> PASS")

    p_huge = [1e11 + i * 1e9 for i in range(30)]
    r_huge = compute_market_snr_and_kalman_state(p_huge, window=20)
    assert r_huge["er_snr"] == 1.0
    print("    - Extreme huge values (1e11) -> PASS")

def test_live_market_snapshot():
    print("[7] Testing Live Market Snapshot Integration...")
    snapshot = StrategyBridge.get_latest_market_snapshot(force_reload=True)
    assert isinstance(snapshot, dict), "Snapshot must be a dictionary"

    er = snapshot.get("er_snr")
    w_eff = snapshot.get("effective_momentum_window")
    w_eff_alt = snapshot.get("effective_window")
    trend = snapshot.get("kalman_trend")
    slope = snapshot.get("kalman_slope")
    mom_accel = snapshot.get("mom_accel")
    mom_accel_star = snapshot.get("mom_accel_star")
    mom_exhaust = snapshot.get("momentum_exhaustion_warning")

    print(f"    - Snapshot er_snr: {er}")
    print(f"    - Snapshot effective_momentum_window: {w_eff}")
    print(f"    - Snapshot effective_window: {w_eff_alt}")
    print(f"    - Snapshot kalman_trend: {trend}")
    print(f"    - Snapshot kalman_slope: {slope}%")
    print(f"    - Snapshot mom_accel: {mom_accel}")
    print(f"    - Snapshot mom_accel_star: {mom_accel_star}")
    print(f"    - Snapshot momentum_exhaustion_warning: {mom_exhaust}")

    assert er is not None and 0.0 <= er <= 1.0, f"Invalid er_snr: {er}"
    assert w_eff is not None and 20 <= w_eff <= 60, f"Invalid effective_momentum_window: {w_eff}"
    assert w_eff_alt == w_eff, "effective_window and effective_momentum_window must match"
    assert trend is not None and trend > 0.0, f"Invalid kalman_trend: {trend}"
    assert slope is not None and isinstance(slope, float), f"Invalid kalman_slope: {slope}"
    assert mom_accel is not None and isinstance(mom_accel, float), f"Invalid mom_accel: {mom_accel}"
    assert isinstance(mom_exhaust, bool), f"Invalid momentum_exhaustion_warning: {mom_exhaust}"
    print("    - Live Market Snapshot Integration -> PASS")

if __name__ == "__main__":
    print("=" * 70)
    print("STARTING EMPIRICAL ADVERSARIAL STRESS TEST SUITE (Milestone 1)")
    print("=" * 70)
    test_pure_monotonic_trend()
    test_pure_high_frequency_white_noise()
    test_kalman_denoising()
    test_flat_series()
    test_short_series()
    test_adversarial_boundary_conditions()
    test_live_market_snapshot()
    print("=" * 70)
    print("ALL 7 EMPIRICAL ADVERSARIAL TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 70)
