import sys
from pathlib import Path
import math
import numpy as np
import pandas as pd

app_dir = Path("d:/Google/Workspace/Wind/AGY2_FundAdvisory")
workspace_dir = Path("d:/Google/Workspace/Wind")
if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))
if str(workspace_dir) not in sys.path:
    sys.path.insert(0, str(workspace_dir))

from strategy_bridge import (
    OnlineExpertWeightUpdater,
    ExpertWeightsDict,
    SchmidtHysteresisBuffer,
    StrategyBridge
)

def test_schmidt_transitions():
    print("--- [Test Group 1] Schmidt Hysteresis Transitions ---")
    buf = SchmidtHysteresisBuffer()

    # 1. From defense:
    # 1a. Noise zone [-1.5%, 1.2%) with Z < 0.60
    for b in [-1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.199]:
        for z in [-2.0, 0.0, 0.3, 0.599]:
            is_atk, reason = buf.evaluate_state_transition(b, z, is_currently_attack=False)
            assert not is_atk, f"Expected defense at b={b}, z={z}, got attack"
            assert "维持防守" in reason or "锁定非进攻" in reason or "防假突破" in reason or "承压" in reason

    # 1b. Breakout by bias >= 1.2%
    is_atk, reason = buf.evaluate_state_transition(1.20, 0.0, is_currently_attack=False)
    assert is_atk and "有效突破施密特迟滞上轨" in reason

    # 1c. Breakout by Z >= 0.60
    is_atk, reason = buf.evaluate_state_transition(0.0, 0.60, is_currently_attack=False)
    assert is_atk and "有效突破施密特迟滞上轨" in reason

    # 2. From attack:
    # 2a. Noise zone (-1.5%, 1.2%] with Z >= 0.20
    for b in [1.2, 0.8, 0.0, -0.5, -1.0, -1.499]:
        for z in [0.20, 0.5, 1.0, 2.0]:
            is_atk, reason = buf.evaluate_state_transition(b, z, is_currently_attack=True)
            assert is_atk, f"Expected attack at b={b}, z={z}, got defense"
            assert "持续站稳" in reason or "死区" in reason or "锁定进攻" in reason

    # 2b. Breakdown by bias <= -1.5%
    is_atk, reason = buf.evaluate_state_transition(-1.50, 0.5, is_currently_attack=True)
    assert not is_atk and "有效跌破施密特迟滞下轨" in reason

    # 2c. Breakdown by Z < 0.20
    is_atk, reason = buf.evaluate_state_transition(0.0, 0.199, is_currently_attack=True)
    assert not is_atk and "有效跌破施密特迟滞下轨" in reason

    # 3. Oscillating noise inside [-1.4%, +1.1%] with neutral Z=0.40
    state_d = False
    state_a = True
    transitions_d = 0
    transitions_a = 0
    np.random.seed(42)
    for _ in range(100):
        noise = float(np.random.uniform(-1.4, 1.1))
        new_d, _ = buf.evaluate_state_transition(noise, 0.40, is_currently_attack=state_d)
        new_a, _ = buf.evaluate_state_transition(noise, 0.40, is_currently_attack=state_a)
        if new_d != state_d:
            transitions_d += 1
            state_d = new_d
        if new_a != state_a:
            transitions_a += 1
            state_a = new_a

    assert transitions_d == 0, f"Noise caused {transitions_d} transitions from defense!"
    assert transitions_a == 0, f"Noise caused {transitions_a} transitions from attack!"
    print("✓ Schmidt Hysteresis Transitions: PASS (Noise immunity verified)")

def test_sigmoid_gating():
    print("--- [Test Group 2] Sigmoid Continuous Gating ---")
    buf = SchmidtHysteresisBuffer()

    # Center value
    assert abs(buf.compute_sigmoid_gating(0.0) - 0.5) < 1e-7

    # Bounds & Extreme values (overflow resistance)
    assert buf.compute_sigmoid_gating(-1e6) == 0.0 or buf.compute_sigmoid_gating(-1e6) < 1e-12
    assert buf.compute_sigmoid_gating(1e6) == 1.0 or buf.compute_sigmoid_gating(1e6) > 1.0 - 1e-12

    # Monotonicity
    z_grid = np.linspace(-4.0, 4.0, 200)
    vals = [buf.compute_sigmoid_gating(z) for z in z_grid]
    for i in range(len(vals) - 1):
        assert vals[i] <= vals[i+1], f"Non-monotonic at z={z_grid[i]}"

    # Composite Z calculation
    z_comp = buf.compute_composite_z(trend_slope=1.5, diff_star_div=4.0, erp_percentile=80.0, option_iv=18.0, bias_20=1.0)
    assert isinstance(z_comp, float)
    assert -3.0 <= z_comp <= 3.0
    print("✓ Sigmoid Continuous Gating: PASS")

def test_trigger_lines_invariant():
    print("--- [Test Group 3] Trigger Lines Anti-Inversion Invariant ---")
    buf = SchmidtHysteresisBuffer()

    cases = [
        (4000.0, 4000.0), # Exact match
        (4000.0, 4500.0), # Far above
        (4000.0, 3500.0), # Far below
        (4000.0, 4048.0), # At +1.2% boundary
        (4000.0, 3940.0), # At -1.5% boundary
        (800.0, 800.0),   # Historical minimum index level
        (100000.0, 100000.0), # Macro value
    ]
    for m20, c300 in cases:
        lines = buf.get_hysteresis_trigger_lines(m20, c300)
        assert lines["surge_line"] > c300, f"surge_line {lines['surge_line']} <= c300 {c300}"
        assert lines["breakdown_line"] < c300, f"breakdown_line {lines['breakdown_line']} >= c300 {c300}"
        assert lines["dist_to_surge_pct"] > 0.0
        assert lines["dist_to_breakdown_pct"] < 0.0
    print("✓ Trigger Lines Invariant: PASS (breakdown < c300 < surge verified for index scale)")

def test_online_expert_weight_updater():
    print("--- [Test Group 4] Online Expert Weight Updater Math & Convergence ---")
    df = StrategyBridge.load_matrix()

    # 1. Base run on real data
    updater = OnlineExpertWeightUpdater(gamma=0.985, eta=10.0, risk_lambda=1.0, cost_c=0.0015)
    res = updater.compute_expert_weights(df, window_days=60)

    weights = res["weights"]
    sum_w = res["sum_weights"]
    details = res["details"]
    blended = res["blended_target_weights"]

    assert len(weights) == 4, f"Expected 4 experts, got {len(weights)}"
    assert set(weights.keys()) == set(updater.EXPERT_NAMES)
    assert abs(sum_w - 1.0) < 1e-5, f"Weights sum {sum_w} != 1.0"
    assert sum(weights.values()) == 1.0000 or abs(sum(weights.values()) - 1.0) < 1e-4

    for k, v in weights.items():
        assert 0.0 <= v <= 1.0, f"Weight {k}={v} out of bounds"

    assert details["gamma"] == 0.985
    assert details["eta"] == 10.0
    assert details["window_days"] == 60
    assert details["top_expert"] in updater.EXPERT_NAMES
    assert details["top_expert_name"] == updater.EXPERT_DISPLAY_NAMES[details["top_expert"]]

    # 2. Mathematical Learning Rate & Gamma Sensitivity Test:
    # 2a. When eta=0 (no learning), weights must remain uniform 0.25!
    updater_no_learn = OnlineExpertWeightUpdater(gamma=0.985, eta=0.0)
    res_no_learn = updater_no_learn.compute_expert_weights(df, window_days=60)
    for k, v in res_no_learn["weights"].items():
        assert abs(v - 0.25) < 1e-3, f"eta=0 should produce uniform weights, got {k}={v}"

    # 2b. When eta increases, top expert weight should increase (higher sensitivity)!
    updater_high_learn = OnlineExpertWeightUpdater(gamma=0.985, eta=30.0)
    res_high_learn = updater_high_learn.compute_expert_weights(df, window_days=60)
    top_expert = details["top_expert"]
    assert res_high_learn["weights"][top_expert] >= weights[top_expert], (
        f"Higher eta should amplify top expert weight: {res_high_learn['weights'][top_expert]} vs {weights[top_expert]}"
    )

    # 3. Edge Cases: Empty df, tiny df
    res_empty = updater.compute_expert_weights(pd.DataFrame())
    assert res_empty["weights"] == {k: 0.25 for k in updater.EXPERT_NAMES}

    res_tiny = updater.compute_expert_weights(df.iloc[:4])
    assert res_tiny["weights"] == {k: 0.25 for k in updater.EXPERT_NAMES}

    # 4. Controlled Dynamic Learning Simulation:
    # Subclass updater to inject controlled expert returns to strictly verify multiplicative update formula
    class ControlledUpdater(OnlineExpertWeightUpdater):
        def get_orthogonal_expert_streams(self, history_df):
            # Expert 0 holds H00300 (100%), others hold H11009 (100%)
            return {
                "trend_momentum": {"H00300": 1.0},
                "erp_macro": {"H11009": 1.0},
                "ma_contrarian": {"H11009": 1.0},
                "liquidity_basis": {"H11009": 1.0}
            }

    ctrl_updater = ControlledUpdater(gamma=0.985, eta=20.0)
    # Test on a period where H00300 drastically outperformed H11009 (2020 bull market)
    bull_df = df[(df['date'] >= '2020-05-01') & (df['date'] <= '2020-07-31')].copy()
    ctrl_res = ctrl_updater.compute_expert_weights(bull_df, window_days=60)
    ctrl_w = ctrl_res["weights"]
    print("Controlled test weights (H00300 bull):", ctrl_w)
    assert ctrl_w["trend_momentum"] > ctrl_w["erp_macro"], (
        f"Outperforming expert should gain weight: {ctrl_w['trend_momentum']} <= {ctrl_w['erp_macro']}"
    )

    print("✓ Online Expert Weight Updater: PASS (Causal update & learning verified)")

def test_strategy_bridge_integration():
    print("--- [Test Group 5] StrategyBridge Integration & Snapshot Interface ---")
    df = StrategyBridge.load_matrix()

    # 1. get_online_expert_weights
    w_dict = StrategyBridge.get_online_expert_weights(df, force_reload=True)
    assert isinstance(w_dict, ExpertWeightsDict)
    assert isinstance(w_dict.details, dict)
    assert isinstance(w_dict.blended_target_weights, dict)
    assert abs(w_dict.sum_weights - 1.0) < 1e-4

    # Dict access & attribute access
    assert w_dict["trend_momentum"] == w_dict.weights["trend_momentum"]
    assert "trend_momentum" in w_dict

    # 2. get_latest_market_snapshot
    snap = StrategyBridge.get_latest_market_snapshot(force_reload=True)
    required_keys = [
        "expert_weights",
        "expert_details",
        "blended_expert_weights",
        "composite_z",
        "sigmoid_gate",
        "trigger_lines",
        "surge_line",
        "breakdown_line"
    ]
    for k in required_keys:
        assert k in snap, f"Snapshot missing key: {k}"

    assert abs(sum(snap["expert_weights"].values()) - 1.0) < 1e-4
    assert 0.0 <= snap["sigmoid_gate"] <= 1.0
    assert snap["surge_line"] > snap["c300_price"]
    assert snap["breakdown_line"] < snap["c300_price"]

    print("✓ StrategyBridge Integration & Snapshot Interface: PASS")

if __name__ == "__main__":
    test_schmidt_transitions()
    test_sigmoid_gating()
    test_trigger_lines_invariant()
    test_online_expert_weight_updater()
    test_strategy_bridge_integration()
    print("\n=======================================================")
    print("🎯 ALL 5 ADVERSARIAL STRESS TEST GROUPS PASSED 100%!")
    print("=======================================================")
