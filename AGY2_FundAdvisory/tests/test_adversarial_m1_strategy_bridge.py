"""
Adversarial Stress Test & Empirical Verification Suite for Milestone 1
Target Module: strategy_bridge.py (R2 OnlineExpertWeightUpdater & R3 SchmidtHysteresisBuffer)
Author: Challenger 2 (challenger_m1_2)

Coverage:
1. Boundary & Corner Cases (Extreme Sigmoid inputs, short/empty history dfs, Schmidt transitions)
2. Mathematical Invariants (Dead zone noise locking, exact threshold boundaries, weight sums)
3. Interface Conformance (StrategyBridge.get_online_expert_weights, get_latest_market_snapshot)
4. Empirical Defect Mining (NaN/None propagation, zero-price data corruption, missing column crashes)
"""

import math
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

TEST_DIR = Path(__file__).resolve().parent
APP_DIR = TEST_DIR.parent
WORKSPACE_ROOT = APP_DIR.parent if APP_DIR.name == "AGY2_FundAdvisory" else APP_DIR

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from strategy_bridge import (
    StrategyBridge,
    SchmidtHysteresisBuffer,
    OnlineExpertWeightUpdater,
    ExpertWeightsDict
)


# ==============================================================================
# 1. Boundary & Corner Cases: Sigmoid Continuous Gating
# ==============================================================================

class TestSigmoidContinuousGating:
    """Adversarial stress-testing of SchmidtHysteresisBuffer.compute_sigmoid_gating"""

    def test_sigmoid_extreme_positive_1000(self):
        """Z = +1000 -> outputs in [0, 1], no overflow, saturates to 1.0"""
        val = SchmidtHysteresisBuffer.compute_sigmoid_gating(1000.0)
        assert not math.isnan(val)
        assert not math.isinf(val)
        assert 0.0 <= val <= 1.0
        assert val == pytest.approx(1.0, abs=1e-6)

    def test_sigmoid_extreme_negative_1000(self):
        """Z = -1000 -> outputs in [0, 1], no underflow crash, saturates near 0.0"""
        val = SchmidtHysteresisBuffer.compute_sigmoid_gating(-1000.0)
        assert not math.isnan(val)
        assert not math.isinf(val)
        assert 0.0 <= val <= 1.0
        assert val == pytest.approx(0.0, abs=1e-6)

    def test_sigmoid_extreme_inf_and_neg_inf(self):
        """Z = +inf, -inf -> handled cleanly without uncaught exception"""
        val_pos_inf = SchmidtHysteresisBuffer.compute_sigmoid_gating(float("inf"))
        assert 0.0 <= val_pos_inf <= 1.0
        assert val_pos_inf == pytest.approx(1.0, abs=1e-6)

        val_neg_inf = SchmidtHysteresisBuffer.compute_sigmoid_gating(float("-inf"))
        assert 0.0 <= val_neg_inf <= 1.0
        assert val_neg_inf == pytest.approx(0.0, abs=1e-6)

    def test_sigmoid_zero_neutral(self):
        """Z = 0.0 -> exact neutral gating 0.50"""
        val = SchmidtHysteresisBuffer.compute_sigmoid_gating(0.0)
        assert val == pytest.approx(0.5, abs=1e-6)

    def test_sigmoid_monotonicity(self):
        """Sigmoid curve must be strictly monotonically increasing"""
        z_range = np.linspace(-10.0, 10.0, 100)
        outputs = [SchmidtHysteresisBuffer.compute_sigmoid_gating(z) for z in z_range]
        for i in range(len(outputs) - 1):
            assert outputs[i] <= outputs[i + 1]

    def test_sigmoid_nan_behavior(self):
        """
        Adversarial Finding: Z = NaN behavior documentation.
        np.clip(nan) returns nan, exp(nan) returns nan, float(1/(1+nan)) returns nan.
        Document whether NaN crashes (it does not crash) vs whether it stays in [0, 1].
        """
        val = SchmidtHysteresisBuffer.compute_sigmoid_gating(float("nan"))
        # Documented behavior: returns nan without crashing.
        # But math.isnan(val) is True, meaning downstream consumers must guard against NaN.
        assert math.isnan(val), f"Expected NaN return for NaN input, got {val}"


# ==============================================================================
# 2. Boundary & Corner Cases: OnlineExpertWeightUpdater
# ==============================================================================

class TestOnlineExpertWeightUpdaterBoundary:
    """Stress test OnlineExpertWeightUpdater under empty/short/anomalous history DataFrames"""

    @pytest.fixture
    def updater(self):
        return OnlineExpertWeightUpdater(gamma=0.985, eta=10.0)

    def test_none_dataframe_fallback(self, updater):
        """None history_df -> graceful fallback to equal 0.25 weights without crash"""
        res = updater.compute_expert_weights(None)
        assert isinstance(res, dict)
        assert "weights" in res
        weights = res["weights"]
        assert len(weights) == 4
        for k, v in weights.items():
            assert v == pytest.approx(0.25, abs=1e-4)
        assert res["sum_weights"] == pytest.approx(1.0, abs=1e-5)

    def test_empty_dataframe_fallback(self, updater):
        """Empty pd.DataFrame() -> graceful fallback to equal 0.25 weights without crash"""
        res = updater.compute_expert_weights(pd.DataFrame())
        assert isinstance(res, dict)
        weights = res["weights"]
        for k, v in weights.items():
            assert v == pytest.approx(0.25, abs=1e-4)
        assert res["sum_weights"] == pytest.approx(1.0, abs=1e-5)

    @pytest.mark.parametrize("row_count", [1, 2, 3, 4])
    def test_short_dataframe_under_5_rows(self, updater, row_count):
        """DataFrame with 1 to 4 rows (< 5 rows) -> graceful fallback to equal weights"""
        cols = ['H00300', 'H00905', 'H00852', 'H00922', 'H30269', 'H11009', 'STAR50_STITCH', 'AU9999', 'SPX_CNY', 'date']
        data = {c: [100.0 + i for i in range(row_count)] for c in cols if c != 'date'}
        data['date'] = pd.date_range('2025-01-01', periods=row_count).strftime('%Y-%m-%d').tolist()
        df = pd.DataFrame(data)

        res = updater.compute_expert_weights(df)
        assert res["sum_weights"] == pytest.approx(1.0, abs=1e-5)
        for v in res["weights"].values():
            assert v == pytest.approx(0.25, abs=1e-4)

    @pytest.mark.parametrize("row_count", [5, 6, 10, 20, 60])
    def test_valid_short_dataframe_5_or_more_rows(self, updater, row_count):
        """DataFrame with >= 5 rows -> successfully executes update without crash, weights sum to 1.0"""
        cols = ['H00300', 'H00905', 'H00852', 'H00922', 'H30269', 'H11009', 'STAR50_STITCH', 'AU9999', 'SPX_CNY', 'date']
        data = {c: [100.0 + i for i in range(row_count)] for c in cols if c != 'date'}
        data['date'] = pd.date_range('2025-01-01', periods=row_count).strftime('%Y-%m-%d').tolist()
        df = pd.DataFrame(data)

        res = updater.compute_expert_weights(df)
        assert "weights" in res
        weights = res["weights"]
        assert len(weights) == 4
        assert abs(sum(weights.values()) - 1.0) < 1e-4
        for k, v in weights.items():
            assert v >= 0.0

    def test_real_matrix_expert_updater(self, updater):
        """Test on actual production market matrix from StrategyBridge.load_matrix()"""
        matrix = StrategyBridge.load_matrix()
        assert matrix is not None
        assert len(matrix) >= 1000

        res = updater.compute_expert_weights(matrix, window_days=60)
        weights = res["weights"]
        assert len(weights) == 4
        expected_experts = {"trend_momentum", "erp_macro", "ma_contrarian", "liquidity_basis"}
        assert set(weights.keys()) == expected_experts

        total_weight = sum(weights.values())
        assert abs(total_weight - 1.0) < 1e-4

        # Verify all weights are non-trivial positive numbers
        for name, w in weights.items():
            assert 0.02 <= w <= 0.80, f"Expert {name} weight {w} outside reasonable range"

        # Verify details
        details = res["details"]
        assert "recent_utilities" in details
        assert "gamma" in details
        assert details["gamma"] == pytest.approx(0.985, abs=1e-4)
        assert "eta" in details
        assert details["eta"] == pytest.approx(10.0, abs=1e-4)
        assert "top_expert" in details
        assert details["top_expert"] in expected_experts


# ==============================================================================
# 3. Schmidt Hysteresis Boundary Transitions & Noise Locking
# ==============================================================================

class TestSchmidtHysteresisBufferTransitions:
    """Stress test SchmidtHysteresisBuffer state transitions, dead-zone locking and trigger lines"""

    @pytest.fixture
    def buffer(self):
        return SchmidtHysteresisBuffer(
            upper_threshold=1.2,
            lower_threshold=-1.5,
            z_upper=0.60,
            z_lower=0.20
        )

    def test_sudden_jump_defense_to_attack(self, buffer):
        """
        Sudden transition: jump from -2.0% to +2.0%
        Starting state: False (defense)
        Ending state: True (attack)
        """
        # Step 1: at -2.0%, state is defense
        st0, r0 = buffer.evaluate_state_transition(bias_20=-2.0, composite_z=0.0, is_currently_attack=False)
        assert st0 is False
        assert "防守" in r0 or "承压" in r0

        # Step 2: sudden jump to +2.0%
        st1, r1 = buffer.evaluate_state_transition(bias_20=+2.0, composite_z=0.0, is_currently_attack=False)
        assert st1 is True
        assert "突破施密特迟滞上轨" in r1
        assert "进攻态" in r1

    def test_sudden_jump_attack_to_defense(self, buffer):
        """
        Sudden transition: jump from +2.0% to -2.0%
        Starting state: True (attack)
        Ending state: False (defense)
        """
        # Step 1: at +2.0%, state is attack
        st0, r0 = buffer.evaluate_state_transition(bias_20=+2.0, composite_z=0.5, is_currently_attack=True)
        assert st0 is True
        assert "持续站稳" in r0 or "维持多头进攻" in r0

        # Step 2: sudden drop to -2.0%
        st1, r1 = buffer.evaluate_state_transition(bias_20=-2.0, composite_z=0.5, is_currently_attack=True)
        assert st1 is False
        assert "跌破施密特迟滞下轨" in r1
        assert "防御" in r1

    def test_dead_zone_noise_locking_from_defense(self, buffer):
        """
        Noise oscillation in [-1.5%, +1.2%) starting from defense:
        Must strictly remain False throughout the entire dead zone
        """
        noise_sequence = [-1.49, -1.0, -0.5, 0.0, 0.5, 1.0, 1.15, 1.19]
        for bias in noise_sequence:
            st, reason = buffer.evaluate_state_transition(bias_20=bias, composite_z=0.30, is_currently_attack=False)
            assert st is False, f"Premature attack transition at bias={bias}%! Reason: {reason}"
            assert "防假突破" in reason or "锁定非进攻态" in reason or "承压" in reason

    def test_dead_zone_noise_locking_from_attack(self, buffer):
        """
        Noise pullback in (-1.5%, +1.2%] starting from attack:
        Must strictly remain True throughout the entire dead zone to prevent whipsaw
        """
        pullback_sequence = [1.19, 1.0, 0.5, 0.0, -0.5, -1.0, -1.40, -1.49]
        for bias in pullback_sequence:
            st, reason = buffer.evaluate_state_transition(bias_20=bias, composite_z=0.30, is_currently_attack=True)
            assert st is True, f"Premature defense exit at bias={bias}%! Reason: {reason}"
            assert "容差死区" in reason or "锁定进攻态防打脸" in reason or "持续站稳" in reason

    def test_exact_boundary_threshold_edges(self, buffer):
        """Exact boundary tests at +1.20% and -1.50%"""
        # Just below upper (+1.199%) vs exact (+1.200%)
        st_below, _ = buffer.evaluate_state_transition(bias_20=1.199, composite_z=0.0, is_currently_attack=False)
        assert st_below is False
        st_exact_up, _ = buffer.evaluate_state_transition(bias_20=1.200, composite_z=0.0, is_currently_attack=False)
        assert st_exact_up is True

        # Just above lower (-1.499%) vs exact (-1.500%)
        st_above, _ = buffer.evaluate_state_transition(bias_20=-1.499, composite_z=0.3, is_currently_attack=True)
        assert st_above is True
        st_exact_down, _ = buffer.evaluate_state_transition(bias_20=-1.500, composite_z=0.3, is_currently_attack=True)
        assert st_exact_down is False

    def test_composite_z_dual_trigger(self, buffer):
        """Composite Z can trigger state transitions independently of MA20 bias"""
        # Z >= 0.60 triggers attack even if bias_20 is flat (0.0%)
        st_z_up, r_z_up = buffer.evaluate_state_transition(bias_20=0.0, composite_z=0.61, is_currently_attack=False)
        assert st_z_up is True
        assert "Z=" in r_z_up

        # Z < 0.20 triggers defense even if bias_20 is flat (0.0%)
        st_z_down, r_z_down = buffer.evaluate_state_transition(bias_20=0.0, composite_z=0.19, is_currently_attack=True)
        assert st_z_down is False
        assert "Z=" in r_z_down

    def test_hysteresis_trigger_lines_geometry(self, buffer):
        """
        Verify that surge_line > c300_price and breakdown_line < c300_price across all realistic price scenarios
        """
        scenarios = [
            (4000.0, 4200.0),  # Bull: c300 > m20
            (4000.0, 3800.0),  # Bear: c300 < m20
            (4000.0, 4000.0),  # Flat: c300 == m20
            (3000.0, 3500.0),
            (5000.0, 4800.0),
        ]
        for m20, c300 in scenarios:
            lines = buffer.get_hysteresis_trigger_lines(m20_price=m20, c300_price=c300)
            assert lines["surge_line"] > c300, f"surge_line {lines['surge_line']} not > c300 {c300}"
            assert lines["breakdown_line"] < c300, f"breakdown_line {lines['breakdown_line']} not < c300 {c300}"
            assert lines["dist_to_surge_pct"] > 0.0
            assert lines["dist_to_breakdown_pct"] < 0.0


# ==============================================================================
# 4. Interface Conformance & Snapshot Contract
# ==============================================================================

class TestInterfaceConformance:
    """Verify StrategyBridge classmethods and market snapshot contracts"""

    def test_get_online_expert_weights_interface(self):
        """Call StrategyBridge.get_online_expert_weights() and verify keys and types"""
        exp_w = StrategyBridge.get_online_expert_weights(force_reload=True)

        assert isinstance(exp_w, ExpertWeightsDict)
        assert isinstance(exp_w, dict)

        # 4 required expert keys
        required_keys = ["trend_momentum", "erp_macro", "ma_contrarian", "liquidity_basis"]
        for k in required_keys:
            assert k in exp_w, f"Missing expert key {k} in get_online_expert_weights"
            assert isinstance(exp_w[k], float)
            assert 0.0 < exp_w[k] < 1.0

        # Weights sum to 1.0000
        assert sum(exp_w.values()) == pytest.approx(1.0, abs=1e-4)

        # Attributes
        assert hasattr(exp_w, "details")
        assert isinstance(exp_w.details, dict)
        assert "expert_weights" in exp_w.details
        assert "expert_display_names" in exp_w.details

        assert hasattr(exp_w, "blended_target_weights")
        assert isinstance(exp_w.blended_target_weights, dict)

        # return_details=True call
        det = StrategyBridge.get_online_expert_weights(return_details=True)
        assert isinstance(det, dict)
        assert "weights" in det
        assert "sum_weights" in det
        assert "blended_target_weights" in det
        assert "details" in det

    def test_get_latest_market_snapshot_m1_contract(self):
        """
        Call StrategyBridge.get_latest_market_snapshot()
        Verify all M1 required keys and valid types
        """
        snapshot = StrategyBridge.get_latest_market_snapshot(force_reload=True)
        assert isinstance(snapshot, dict)

        # M1 required keys
        m1_required_keys = [
            "expert_weights",
            "expert_details",
            "blended_expert_weights",
            "composite_z",
            "sigmoid_gate",
            "trigger_lines",
            "surge_line",
            "breakdown_line",
            "bias_20",
            "c300_price",
            "m20_price",
            "market_state"
        ]

        for k in m1_required_keys:
            assert k in snapshot, f"Snapshot missing M1 required key: {k}"

        # Value and type checks
        assert isinstance(snapshot["expert_weights"], dict)
        assert len(snapshot["expert_weights"]) == 4
        assert sum(snapshot["expert_weights"].values()) == pytest.approx(1.0, abs=1e-4)

        assert isinstance(snapshot["expert_details"], dict)
        assert "top_expert" in snapshot["expert_details"]

        assert isinstance(snapshot["blended_expert_weights"], dict)

        assert isinstance(snapshot["composite_z"], float)
        assert -3.0 <= snapshot["composite_z"] <= 3.0

        assert isinstance(snapshot["sigmoid_gate"], float)
        assert 0.0 <= snapshot["sigmoid_gate"] <= 1.0

        assert isinstance(snapshot["trigger_lines"], dict)
        assert snapshot["surge_line"] > snapshot["c300_price"]
        assert snapshot["breakdown_line"] < snapshot["c300_price"]
