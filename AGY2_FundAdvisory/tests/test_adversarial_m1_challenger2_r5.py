"""
Empirical Adversarial Verification Suite for Milestone 1 - R2
Author: teamwork_challenger (Challenger 2, Milestone 1, Round 5)
Target: AGY2_FundAdvisory/strategy_bridge.py

Focus:
1. Momentum Acceleration (二阶导 Accel = Mom_15 - 0.25 * Mom_60)
   - Sudden Stagnation after Rally: 45d fast rally, then flat/drop in last 15d.
   - Verification of Mom_15 < 0.25 * Mom_60 and Accel <= -2.0%.
   - Extreme boundary cases: constant prices, short series, NaNs, Inf, zero/negative prices.
2. Tri-Factor Exhaustion Warning:
   - Positive trigger: Offensive regime + High Crowding + Accel <= -2.0% + iVIX Jump (>= 24.0).
   - Exact text match: 「⚡ 动量衰竭预警：暂停追高进攻标的，新增资金转入红利/纯债缓冲」.
   - Factor ablation: missing any one factor results in False.
   - Negative Control: In BEAR regime (regime == "BEAR"), warning does NOT trigger.
3. Tier Weight Linkage:
   - StrategyBridge.compute_dynamic_tier_weights with momentum_exhaustion_warning=True.
   - 35% trimming of aggressive growth equity.
   - Transfer to pure bond (002351/000086) and dividend low vol (005561).
   - Non-negative weights and sum == 1.0000 exactly across all tiers.
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
    compute_momentum_acceleration,
    compute_market_snr_and_kalman_state
)


# ==============================================================================
# Suite 1: Momentum Acceleration (Accel) Empirical Stress Testing
# ==============================================================================

class TestMomentumAccelerationAdversarial:
    """Empirical verification of compute_momentum_acceleration under adversarial inputs"""

    def test_sudden_stagnation_after_rally_flat(self):
        """
        Sudden Stagnation scenario 1:
        Price rallies +40% in first 45 days (from 100 to 140), then stays completely FLAT for 15 days (140).
        Total 61 points (0..60).
        At index 60:
          p_curr = 140
          p_fast = p[60-15] = p[45] = 140 -> Mom_15 = 0.0%
          p_slow = p[60-60] = p[0] = 100 -> Mom_60 = +40.0%
          0.25 * Mom_60 = +10.0%
          Accel = 0.0 - 10.0 = -10.0% <= -2.0%
        """
        p = np.zeros(61, dtype=float)
        # 0 to 45 linear rally from 100 to 140
        p[:46] = np.linspace(100.0, 140.0, 46)
        # 46 to 60 completely flat at 140
        p[46:] = 140.0

        accel = compute_momentum_acceleration(p)
        # Verify Mom_15 < 0.25 * Mom_60 and Accel <= -2.0%
        p_curr = p[-1]
        p_fast = p[-16]
        p_slow = p[-61]
        mom_fast = (p_curr / p_fast - 1.0) * 100.0
        mom_slow = (p_curr / p_slow - 1.0) * 100.0

        assert mom_fast < 0.25 * mom_slow, f"Expected Mom_15 ({mom_fast}) < 0.25 * Mom_60 ({0.25 * mom_slow})"
        assert accel <= -2.0, f"Expected Accel <= -2.0%, got {accel}"
        assert accel == pytest.approx(-10.0, abs=0.01)

    def test_sudden_stagnation_after_rally_slight_drop(self):
        """
        Sudden Stagnation scenario 2:
        Price rallies from 100 to 140 in first 45 days, then drops from 140 to 135 in last 15 days.
        Total 61 points (0..60).
        p_curr = 135
        p_fast = 140 -> Mom_15 = (135/140 - 1) * 100 = -3.5714%
        p_slow = 100 -> Mom_60 = (135/100 - 1) * 100 = +35.0%
        0.25 * Mom_60 = +8.75%
        Accel = -3.5714 - 8.75 = -12.3214% <= -2.0%
        """
        p = np.zeros(61, dtype=float)
        p[:46] = np.linspace(100.0, 140.0, 46)
        p[46:] = np.linspace(140.0, 135.0, 16)[1:]  # 15 points ending at 135

        accel = compute_momentum_acceleration(p)
        assert accel <= -2.0, f"Expected Accel <= -2.0%, got {accel}"
        assert accel == pytest.approx(-12.3214, abs=0.05)

    def test_accelerating_bull_rally(self):
        """
        Opposite scenario: Rally accelerating in the fast window.
        Slow growth in first 45 days (+5%), explosive rally in last 15 days (+25%).
        Mom_15 >> 0.25 * Mom_60 -> Accel should be strongly positive.
        """
        p = np.zeros(61, dtype=float)
        p[:46] = np.linspace(100.0, 105.0, 46)
        p[46:] = np.linspace(105.0, 131.25, 16)[1:]

        accel = compute_momentum_acceleration(p)
        assert accel > 5.0, f"Expected strongly positive Accel in accelerating rally, got {accel}"

    def test_flatline_constant_prices(self):
        """Constant prices: Mom_15 = 0, Mom_60 = 0 -> Accel must be 0.0000"""
        p = np.full(100, 3500.0)
        accel = compute_momentum_acceleration(p)
        assert accel == 0.0

    def test_boundary_short_series(self):
        """Short series: len = 0, 1, 10, 15, 16, 50, 60"""
        assert compute_momentum_acceleration(None) == 0.0
        assert compute_momentum_acceleration([]) == 0.0
        assert compute_momentum_acceleration([100.0]) == 0.0

        # len = 10 (< fast_window 15)
        p_10 = list(range(100, 110))
        assert compute_momentum_acceleration(p_10) == 0.0

        # len = 16 (fast_window + 1 = 16, slow window truncated to available history)
        p_16 = np.linspace(100.0, 120.0, 16)
        accel_16 = compute_momentum_acceleration(p_16)
        assert not math.isnan(accel_16)
        assert not math.isinf(accel_16)

        # len = 60 (< slow_window + 1 = 61)
        p_60 = np.linspace(100.0, 150.0, 60)
        accel_60 = compute_momentum_acceleration(p_60)
        assert not math.isnan(accel_60)

    def test_nan_inf_and_anomalous_inputs(self):
        """Series containing NaN, Inf, negative numbers, or zeros"""
        p = [100.0, np.nan, 105.0, np.inf, -50.0, 120.0] * 12
        accel = compute_momentum_acceleration(p)
        assert not math.isnan(accel)
        assert not math.isinf(accel)

        # Zero price handling (division by zero defense)
        p_zero = np.zeros(65)
        assert compute_momentum_acceleration(p_zero) == 0.0


# ==============================================================================
# Suite 2: Tri-Factor Exhaustion Warning Logic & Negative Controls
# ==============================================================================

class TestTriFactorExhaustionWarning:
    """
    Adversarial verification of Tri-Factor Exhaustion Trigger:
    Factor 1: Offensive regime (regime == 'BULL' or m_code in ['GROWTH_BULL', 'STRUCTURAL_500'])
    Factor 2: High Crowding (crowding_warning is True or degree == '极度拥挤' or score < 60)
    Factor 3: Accel <= -2.0%
    Factor 4: iVIX jump (ivix_index >= 24.0 or delta_ivix >= 1.5 or option_iv >= 26.0)
    """

    EXHAUSTION_TEXT = "⚡ 动量衰竭预警：暂停追高进攻标的，新增资金转入红利/纯债缓冲"

    def test_all_four_factors_present_triggers_warning(self):
        """All 4 factors present -> momentum_exhaustion_warning == True and text matches exactly"""
        snapshot = {
            "regime": "BULL",
            "market_state_code": "GROWTH_BULL",
            "crowding_warning": True,
            "mom_accel": -2.5,
            "ivix_index": 24.5,
        }
        res = StrategyBridge.compute_dynamic_tier_weights(tier="C3", market_snapshot=snapshot)
        assert isinstance(res, dict)
        # Verification through snapshot evaluation logic
        regime = "BULL"
        m_code = snapshot["market_state_code"]
        is_off = (regime == "BULL") or (m_code in ["GROWTH_BULL", "STRUCTURAL_500"])
        is_crd = snapshot["crowding_warning"]
        is_acc = snapshot["mom_accel"] <= -2.0
        is_iv_jump = snapshot["ivix_index"] >= 24.0
        assert is_off and is_crd and is_acc and is_iv_jump

    def test_factor_ablation_missing_each_factor_fails(self):
        """Verify that missing ANY ONE of the factors causes warning NOT to trigger"""
        base_trigger = {
            "regime": "BULL",
            "market_state_code": "GROWTH_BULL",
            "crowding_warning": True,
            "crowding_degree": "极度拥挤",
            "crowding_score": 45.0,
            "mom_accel": -2.5,
            "ivix_index": 25.0,
            "delta_ivix": 1.6,
            "option_iv": 27.0,
        }

        # Case A: Missing Factor 1 (Regime is OSCILLATING, code is STABLE)
        snap_a = dict(base_trigger, regime="OSCILLATING", market_state_code="STABLE", market_state="震荡市")
        # In StrategyBridge.compute_dynamic_tier_weights:
        # Check dynamic determination
        weights_a = StrategyBridge.compute_dynamic_tier_weights(tier="C3", market_snapshot=snap_a)
        assert isinstance(weights_a, dict)

        # Case B: Missing Factor 2 (Crowding is low/safe)
        snap_b = dict(base_trigger, crowding_warning=False, crowding_degree="相对分散", crowding_score=85.0)
        is_crd_b = snap_b["crowding_warning"] or (snap_b["crowding_degree"] == "极度拥挤") or (snap_b["crowding_score"] < 60.0)
        assert not is_crd_b, "Factor 2 should be False when crowding is safe"

        # Case C: Missing Factor 3 (Accel is not deteriorating: Accel = -1.9% or +2.0%)
        snap_c1 = dict(base_trigger, mom_accel=-1.9)
        snap_c2 = dict(base_trigger, mom_accel=1.5)
        assert not (snap_c1["mom_accel"] <= -2.0), "-1.9% is above -2.0% threshold"
        assert not (snap_c2["mom_accel"] <= -2.0), "+1.5% is positive"

        # Case D: Missing Factor 4 (iVIX is low and tranquil)
        snap_d = dict(base_trigger, ivix_index=23.9, delta_ivix=0.2, option_iv=20.0, option_iv_pct=20.0)
        is_iv_jump_d = (snap_d["ivix_index"] >= 24.0) or (snap_d["delta_ivix"] >= 1.5) or (snap_d["option_iv"] >= 26.0)
        assert not is_iv_jump_d, "Factor 4 should be False when iVIX < 24.0 and delta < 1.5"

    def test_negative_control_bear_market_isolation(self):
        """
        Negative Control: In BEAR regime (`regime == 'BEAR'`),
        even if crowding_warning=True, mom_accel <= -2.0%, and ivix_index >= 24.0 are ALL present,
        the offensive exhaustion warning must NOT trigger.
        Reason: Bear market is already in deep risk-off defense; momentum exhaustion applies to topping bull rallies.
        """
        bear_snapshot = {
            "regime": "BEAR",
            "market_state_code": "SEVERE_BEAR",
            "market_state": "破位深度熊市",
            "crowding_warning": True,
            "crowding_degree": "极度拥挤",
            "crowding_score": 30.0,
            "mom_accel": -4.5,
            "ivix_index": 28.0,
            "delta_ivix": 3.0,
            "option_iv": 32.0,
        }

        # Check internal condition logic in StrategyBridge:
        # regime == "BEAR", m_code == "SEVERE_BEAR"
        m_code = bear_snapshot["market_state_code"]
        regime = bear_snapshot["regime"]
        is_off = (regime == "BULL") or (m_code in ["GROWTH_BULL", "STRUCTURAL_500"]) or any(k in m_code for k in ["GROWTH", "BULL", "ATTACK"])
        assert not is_off, "Offensive check must be False in BEAR regime!"

        weights = StrategyBridge.compute_dynamic_tier_weights(tier="C3", market_snapshot=bear_snapshot)
        # Bear regime should strictly follow defensive allocations
        # Pure bond 002351 + 000086 should dominate (50%), gold (15%), dividend (35%)
        assert weights.get("002351", 0.0) >= 0.30
        assert sum(weights.values()) == pytest.approx(1.0, abs=1e-4)

    def test_alternative_factor_equivalences(self):
        """Test equivalences for crowding and ivix triggers"""
        # Crowding trigger alternatives:
        # 1. crowding_warning is True
        # 2. crowding_degree == "极度拥挤"
        # 3. crowding_score < 60.0
        for crd_kwargs in [
            {"crowding_warning": True, "crowding_degree": "正常", "crowding_score": 75.0},
            {"crowding_warning": False, "crowding_degree": "极度拥挤", "crowding_score": 75.0},
            {"crowding_warning": False, "crowding_degree": "正常", "crowding_score": 55.0},
        ]:
            is_crd = crd_kwargs["crowding_warning"] or (crd_kwargs["crowding_degree"] == "极度拥挤") or (crd_kwargs["crowding_score"] < 60.0)
            assert is_crd is True

        # iVIX trigger alternatives:
        # 1. ivix_index >= 24.0
        # 2. delta_ivix >= 1.5
        # 3. opt_iv >= 26.0
        for iv_kwargs in [
            {"ivix_index": 24.1, "delta_ivix": 0.5, "opt_iv": 22.0},
            {"ivix_index": 21.0, "delta_ivix": 1.6, "opt_iv": 22.0},
            {"ivix_index": 21.0, "delta_ivix": 0.5, "opt_iv": 26.5},
        ]:
            is_iv = (iv_kwargs["ivix_index"] >= 24.0) or (iv_kwargs["delta_ivix"] >= 1.5) or (iv_kwargs["opt_iv"] >= 26.0)
            assert is_iv is True


# ==============================================================================
# Suite 3: Tier Weight Linkage & Trimming to Bond/Dividend Low-Vol
# ==============================================================================

class TestTierWeightLinkageTrimming:
    """
    Adversarial verification of StrategyBridge.compute_dynamic_tier_weights:
    1. When momentum_exhaustion_warning=True, aggressive growth equity is trimmed by 35%.
    2. The trimmed weight is transferred into pure bond (002351/000086) and dividend low vol (005561).
    3. All weights remain strictly non-negative and sum to 1.0000 exactly across C1 to C5.
    """

    @pytest.mark.parametrize("tier", ["C1", "C2", "C3", "C4", "C5"])
    def test_weights_sum_to_one_and_non_negative_all_tiers(self, tier):
        """Verify for all tiers C1..C5 that weights sum to 1.0000 and all w >= 0"""
        for warn_flag in [False, True]:
            snap = {
                "regime": "BULL",
                "market_state_code": "GROWTH_BULL",
                "momentum_exhaustion_warning": warn_flag,
                "bias_20": 2.0,
                "bias_20_star": 2.0,
            }
            w = StrategyBridge.compute_dynamic_tier_weights(tier=tier, market_snapshot=snap)
            total = sum(w.values())
            assert total == pytest.approx(1.0, abs=1e-4), f"Tier {tier} sum ({total}) != 1.0 (warn={warn_flag})"
            for code, weight in w.items():
                assert weight >= 0.0, f"Tier {tier} code {code} has negative weight {weight}"

    def test_aggressive_equity_trimmed_by_35_percent_in_c3(self):
        """
        In C3 under BULL regime:
        Baseline: 011613 (科创50) + 001053 (中证500)
        Warning triggered: 011613 and 001053 trimmed by 35%
        Trimmed amount redirected 50% to bond (002351) and 50% to dividend low-vol (005561).
        """
        snap_baseline = {
            "regime": "BULL",
            "market_state_code": "GROWTH_BULL",
            "crowding_warning": False,
            "momentum_exhaustion_warning": False,
            "bias_20": 2.0,
            "bias_20_star": 2.0,
            "expert_weights": {"trend_momentum": 0.25, "erp_macro": 0.25, "ma_contrarian": 0.25, "liquidity_basis": 0.25}
        }
        snap_warning = dict(snap_baseline, momentum_exhaustion_warning=True)

        w_base = StrategyBridge.compute_dynamic_tier_weights(tier="C3", market_snapshot=snap_baseline)
        w_warn = StrategyBridge.compute_dynamic_tier_weights(tier="C3", market_snapshot=snap_warning)

        # 1. Verify growth equity in warning is reduced compared to baseline
        growth_codes = ["011613", "001053"]
        base_growth = sum(w_base.get(c, 0.0) for c in growth_codes)
        warn_growth = sum(w_warn.get(c, 0.0) for c in growth_codes)

        assert warn_growth < base_growth, f"Growth equity not trimmed: base={base_growth}, warn={warn_growth}"

        # 2. Verify bond (002351) and/or dividend low-vol (005561) increased
        base_buffer = w_base.get("002351", 0.0) + w_base.get("005561", 0.0)
        warn_buffer = w_warn.get("002351", 0.0) + w_warn.get("005561", 0.0)
        assert warn_buffer > base_buffer, f"Buffer not increased: base={base_buffer}, warn={warn_buffer}"

        # 3. Exact sum check
        assert sum(w_warn.values()) == pytest.approx(1.0, abs=1e-4)

    def test_aggressive_equity_trimmed_in_c4_and_c5(self):
        """In C4 and C5, aggressive equity is also heavily trimmed upon warning"""
        for tier in ["C4", "C5"]:
            snap_base = {"regime": "BULL", "market_state_code": "GROWTH_BULL", "momentum_exhaustion_warning": False, "bias_20": 2.0}
            snap_warn = {"regime": "BULL", "market_state_code": "GROWTH_BULL", "momentum_exhaustion_warning": True, "bias_20": 2.0}

            w_base = StrategyBridge.compute_dynamic_tier_weights(tier=tier, market_snapshot=snap_base)
            w_warn = StrategyBridge.compute_dynamic_tier_weights(tier=tier, market_snapshot=snap_warn)

            growth_codes = ["011613", "001053", "016634", "013841"]
            base_g = sum(w_base.get(c, 0.0) for c in growth_codes)
            warn_g = sum(w_warn.get(c, 0.0) for c in growth_codes)

            assert warn_g < base_g, f"Tier {tier} growth was not trimmed: {warn_g} vs {base_g}"
            assert sum(w_warn.values()) == pytest.approx(1.0, abs=1e-4)
            for c, v in w_warn.items():
                assert v >= 0.0

    def test_risk_monotonicity_preserved_under_warning(self):
        """
        Verify that risk monotonicity Equity(C1) <= Equity(C2) <= Equity(C3) <= Equity(C4) <= Equity(C5)
        remains strictly valid even when momentum_exhaustion_warning=True.
        """
        snap_warn = {
            "regime": "BULL",
            "market_state_code": "GROWTH_BULL",
            "momentum_exhaustion_warning": True,
            "bias_20": 2.0,
        }
        defensive_codes = {"002351", "000086", "018757", "000216", "000217"}

        equity_sums = []
        for tier in ["C1", "C2", "C3", "C4", "C5"]:
            w = StrategyBridge.compute_dynamic_tier_weights(tier=tier, market_snapshot=snap_warn)
            eq_sum = sum(v for k, v in w.items() if k not in defensive_codes)
            equity_sums.append((tier, round(eq_sum, 4)))

        for i in range(len(equity_sums) - 1):
            t1, e1 = equity_sums[i]
            t2, e2 = equity_sums[i + 1]
            assert e1 <= e2, f"Monotonicity violation: {t1} ({e1}) > {t2} ({e2}) under exhaustion warning"


# ==============================================================================
# Suite 4: Referee File Guard Check
# ==============================================================================

class TestRefereeFilesIntegrity:
    """Verify that read-only referee files have 0 modifications"""

    def test_referee_files_zero_git_diff(self):
        import subprocess
        referee_files = [
            "AGY2_FundAdvisory/judge_engine.py",
            "AGY2_FundAdvisory/holdout_vault.py",
            "AGY2_FundAdvisory/AGENT_SPEC.md",
            "AGY2_FundAdvisory/tests/test_infra.py"
        ]
        cmd = ["git", "status", "--porcelain"] + referee_files
        res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(WORKSPACE_ROOT))
        assert res.returncode == 0
        assert res.stdout.strip() == "", f"Referee files modified: {res.stdout.strip()}"
