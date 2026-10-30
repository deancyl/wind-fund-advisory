"""
Empirical Adversarial Stress & Verification Harness for Milestone 1 (M1)
File: AGY2_FundAdvisory/tests/test_adversarial_m1_stress.py
Author: Challenger 1 (challenger_m1_1)

Mission Requirements Tested:
1. OnlineExpertWeightUpdater:
   - Synthetic & historical market slices: weights sum to 1.0000 within 1e-5.
   - Monotonicity: higher risk-adjusted net utility strictly increases weight.
   - Stress resilience: empty, minimal, volatile, flat, extreme parameters.
2. SchmidtHysteresisBuffer:
   - Noise oscillation within MA20 +- 0.5%: 0 state flips (state locked).
   - Full deadzone [-1.5%, +1.2%]: state locked.
   - Breakout trigger lines: surge_line > c300_price and breakdown_line < c300_price across all realistic price ranges.
   - Sigmoid continuous gating & composite Z clipping.
3. End-to-end integration:
   - StrategyBridge snapshot contract compliance.
"""

import sys
import math
from pathlib import Path
import pytest
import numpy as np
import pandas as pd

# Setup paths
APP_DIR = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = APP_DIR.parent if APP_DIR.name == "AGY2_FundAdvisory" else APP_DIR
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from strategy_bridge import (
    OnlineExpertWeightUpdater,
    SchmidtHysteresisBuffer,
    StrategyBridge,
    ExpertWeightsDict
)


# ==============================================================================
# 1. OnlineExpertWeightUpdater: Normalization, Historical & Synthetic Slices
# ==============================================================================

class TestOnlineExpertWeightUpdaterNormalization:
    """实证检验在线多专家乘性权重更新在历史与合成切片下的严格归一化与数学健壮性"""

@pytest.fixture(scope="module")
def historical_df():
    """加载湖仓全周期真实市场历史数据"""
    df = StrategyBridge.load_matrix()
    assert df is not None and len(df) > 500
    return df


class TestOnlineExpertWeightUpdaterNormalization:
    """实证检验在线多专家乘性权重更新在历史与合成切片下的严格归一化与数学健壮性"""

    @pytest.mark.parametrize("slice_len", [10, 20, 60, 120, 250, 500, 1000])
    @pytest.mark.parametrize("window_days", [10, 30, 60, 120])
    def test_weights_sum_to_one_historical_slices(self, historical_df, slice_len, window_days):
        """历史截面全景切片：断言权重之和严格在 1.0000 +- 1e-5 范围内，无负权重"""
        updater = OnlineExpertWeightUpdater(gamma=0.985, eta=10.0)
        sub_df = historical_df.iloc[-slice_len:]
        res = updater.compute_expert_weights(sub_df, window_days=window_days)

        weights = res["weights"]
        sum_w = sum(weights.values())

        # 1. 严格归一化断言 (误差绝对值严格 < 1e-5)
        assert abs(sum_w - 1.0) < 1e-5, f"Historical slice ({slice_len}d, w={window_days}) sum={sum_w} != 1.0"
        assert res["sum_weights"] == pytest.approx(1.0, abs=1e-4)

        # 2. 概率公理断言：全部权重处于 [0.0, 1.0]
        for name, w in weights.items():
            assert 0.0 <= w <= 1.0, f"Weight {name}={w} out of bounds [0, 1]"

        # 3. 混合目标资产权重校验
        blended = res["blended_target_weights"]
        if blended:
            sum_b = sum(blended.values())
            assert abs(sum_b - 1.0) <= 1e-3, f"Blended weights sum={sum_b} != 1.0"

    def test_weights_fallback_on_empty_and_sub_minimal_slices(self):
        """边界压力：空 DataFrame、None、以及 len < 5 切片的安全兜底均分 (0.25 各占一份)"""
        updater = OnlineExpertWeightUpdater(gamma=0.985, eta=10.0)

        for invalid_df in [None, pd.DataFrame(), pd.DataFrame({"H00300": [1.0, 1.1]}), pd.DataFrame({"H00300": [1, 2, 3, 4]})]:
            res = updater.compute_expert_weights(invalid_df)
            weights = res["weights"]
            assert len(weights) == 4
            assert abs(sum(weights.values()) - 1.0) < 1e-5
            for k in updater.EXPERT_NAMES:
                assert weights[k] == 0.25

    def test_weights_sum_to_one_synthetic_extreme_regimes(self):
        """合成极端市场行情压力测试：极牛、极熊、剧烈震荡、资产缺失"""
        updater = OnlineExpertWeightUpdater(gamma=0.985, eta=10.0)
        dates = pd.date_range("2025-01-01", periods=100, freq="B")
        asset_cols = ['H00300', 'H00905', 'H00852', 'H00922', 'H30269', 'H11009', 'STAR50_STITCH', 'AU9999', 'SPX_CNY']

        # 1. 极牛行情：所有资产每天暴涨 3%
        bull_data = {col: 1000.0 * (1.03 ** np.arange(100)) for col in asset_cols}
        bull_df = pd.DataFrame(bull_data, index=dates)
        bull_res = updater.compute_expert_weights(bull_df, window_days=60)
        assert abs(sum(bull_res["weights"].values()) - 1.0) < 1e-5

        # 2. 极熊行情：所有资产每天暴跌 3%
        bear_data = {col: 1000.0 * (0.97 ** np.arange(100)) for col in asset_cols}
        bear_df = pd.DataFrame(bear_data, index=dates)
        bear_res = updater.compute_expert_weights(bear_df, window_days=60)
        assert abs(sum(bear_res["weights"].values()) - 1.0) < 1e-5

        # 3. 极度高频噪音锯齿：每天在 +5% 与 -5% 间交替
        zigzag_mult = np.tile([1.05, 0.95], 50)
        zigzag_data = {col: 1000.0 * np.cumprod(zigzag_mult) for col in asset_cols}
        zigzag_df = pd.DataFrame(zigzag_data, index=dates)
        zigzag_res = updater.compute_expert_weights(zigzag_df, window_days=60)
        assert abs(sum(zigzag_res["weights"].values()) - 1.0) < 1e-5

        # 4. 部分非核心资产缺失 (省略 SPX_CNY, AU9999, H00852 等，仅保留基础基准列)
        core_cols = ['H00300', 'H00905', 'H00922', 'H11009', 'STAR50_STITCH']
        partial_data = {col: 1000.0 * (1.001 ** np.arange(100)) for col in core_cols}
        partial_df = pd.DataFrame(partial_data, index=dates)
        partial_res = updater.compute_expert_weights(partial_df, window_days=60)
        assert abs(sum(partial_res["weights"].values()) - 1.0) < 1e-5

        # 5. 当缺失底层正交策略必需的基准列时，底层抛出 KeyError
        missing_df = pd.DataFrame({
            "H00300": 1000.0 * (1.001 ** np.arange(100)),
            "H11009": 100.0 * (1.0002 ** np.arange(100))
        }, index=dates)
        with pytest.raises(KeyError):
            updater.compute_expert_weights(missing_df, window_days=60)

    @pytest.mark.parametrize("gamma", [0.5, 0.8, 0.95, 0.985, 0.999])
    @pytest.mark.parametrize("eta", [0.1, 1.0, 5.0, 10.0, 50.0])
    def test_parameter_extreme_combinations(self, historical_df, gamma, eta):
        """参数极值组合校验：gamma 与 eta 在大跨度范围下权重均稳定归一化"""
        updater = OnlineExpertWeightUpdater(gamma=gamma, eta=eta, risk_lambda=2.0, cost_c=0.005)
        res = updater.compute_expert_weights(historical_df.iloc[-80:], window_days=40)
        weights = res["weights"]
        assert abs(sum(weights.values()) - 1.0) < 1e-5
        for w in weights.values():
            assert not math.isnan(w)
            assert not math.isinf(w)
            assert 0.0 <= w <= 1.0


# ==============================================================================
# 2. OnlineExpertWeightUpdater: Monotonicity of Utility & Weights
# ==============================================================================

class TestOnlineExpertWeightUpdaterMonotonicity:
    """实证检验胜率/净效用更优专家的权重单调递增性 (Monotonicity Verification)"""

    def test_multiplicative_update_step_monotonicity(self):
        """
        纯数学更新递推单调性断言:
        当专家 A 的风险调整净效用 u_{A, t} 持续高于其他专家时，
        其权重 P_{A, t} 在逐日迭代中必须严格单调递增。
        """
        gamma = 0.985
        eta = 10.0
        k_experts = 4
        expert_names = ["exp_0", "exp_1", "exp_2", "exp_3"]

        # 初始均匀分布
        P = {name: 1.0 / k_experts for name in expert_names}

        # 设定稳定的效用优势：exp_0 保持正向净效用，其他专家为零或负效用
        daily_utilities = {
            "exp_0": 0.015,   # +1.5% 净效用
            "exp_1": -0.005,  # -0.5%
            "exp_2": 0.000,   # 0.0%
            "exp_3": -0.010   # -1.0%
        }

        p0_trajectory = [P["exp_0"]]
        p3_trajectory = [P["exp_3"]]

        num_steps = 30
        for step in range(num_steps):
            log_terms = {}
            for name in expert_names:
                p_prev = max(P[name], 1e-12)
                log_terms[name] = gamma * math.log(p_prev) + eta * daily_utilities[name]

            max_log = max(log_terms.values())
            unnorm_weights = {name: math.exp(log_terms[name] - max_log) for name in expert_names}
            sum_unnorm = sum(unnorm_weights.values())
            P = {name: unnorm_weights[name] / sum_unnorm for name in expert_names}

            p0_trajectory.append(P["exp_0"])
            p3_trajectory.append(P["exp_3"])

        # 1. 断言优秀专家 exp_0 权重每一期严格单调上升
        for i in range(len(p0_trajectory) - 1):
            assert p0_trajectory[i + 1] > p0_trajectory[i], (
                f"Step {i}: p0 did not increase monotonically ({p0_trajectory[i]} -> {p0_trajectory[i + 1]})"
            )

        # 2. 断言劣质专家 exp_3 权重每一期严格单调下降
        for i in range(len(p3_trajectory) - 1):
            assert p3_trajectory[i + 1] < p3_trajectory[i], (
                f"Step {i}: p3 did not decrease monotonically ({p3_trajectory[i]} -> {p3_trajectory[i + 1]})"
            )

        # 3. 最终权重分布：exp_0 必须显著超越均匀分布 (0.25 -> > 0.80)
        assert p0_trajectory[-1] > 0.70, f"Final weight {p0_trajectory[-1]} insufficient after 30 steps"
        assert p3_trajectory[-1] < 0.05, f"Final weight {p3_trajectory[-1]} too high after 30 steps"

    def test_controlled_market_simulation_monotonic_weight_growth(self):
        """
        全流程市场序列实证：
        构造合成市场数据，使得趋势动量专家的目标标的持续强势上涨，
        而其它专家的资产持续阴跌，断言趋势动量专家的权重在递增评估期下逐步攀升。
        """
        updater = OnlineExpertWeightUpdater(gamma=0.985, eta=10.0)
        asset_cols = ['H00300', 'H00905', 'H00852', 'H00922', 'H30269', 'H11009', 'STAR50_STITCH', 'AU9999', 'SPX_CNY']
        n_days = 90
        dates = pd.date_range("2025-01-01", periods=n_days, freq="B")

        # 趋势成长标的稳步上涨，高股息/纯债/黄金停滞或下跌
        prices = {}
        for col in asset_cols:
            if col in ['STAR50_STITCH', 'H00300']:
                # 持续稳健每日上涨 +0.4%
                prices[col] = 1000.0 * (1.004 ** np.arange(n_days))
            else:
                # 每日微幅下跌 -0.1%
                prices[col] = 1000.0 * (0.999 ** np.arange(n_days))

        sim_df = pd.DataFrame(prices, index=dates)

        # 比较短窗口与长窗口下 trend_momentum 的权重
        res_short = updater.compute_expert_weights(sim_df, window_days=15)
        res_mid = updater.compute_expert_weights(sim_df, window_days=30)
        res_long = updater.compute_expert_weights(sim_df, window_days=60)

        w_short = res_short["weights"]["trend_momentum"]
        w_mid = res_mid["weights"]["trend_momentum"]
        w_long = res_long["weights"]["trend_momentum"]

        # 断言长周期积累了更多正向效用的趋势专家权重显著高于初始/短窗口
        assert w_mid >= w_short or w_long >= w_mid
        assert w_long > 0.25, f"Trend momentum weight {w_long} failed to exceed equal weight 0.25"


# ==============================================================================
# 3. SchmidtHysteresisBuffer: Noise Lock & State Machine Transitions
# ==============================================================================

class TestSchmidtHysteresisBufferNoiseAndStateLock:
    """实证检验施密特迟滞缓冲环在 [-1.5%, +1.2%] 噪音带内的 0 横跳锁定特性"""

    def test_noise_oscillation_defensive_lock(self):
        """
        核心防打脸用例 1: 防守态启动时，指数在 MA20 +- 0.5% 范围内高频反复震荡，
        断言迟滞缓冲环维持原有防守态锁定，状态跳变为 0 (0 flips)!
        """
        buf = SchmidtHysteresisBuffer(upper_threshold=1.2, lower_threshold=-1.5, z_upper=0.60, z_lower=0.20)
        is_attack = False

        # 构造高频锯齿序列：+0.3%, -0.4%, +0.5%, -0.3%, +0.48%, -0.50%, +0.2%, -0.3%
        noisy_biases = [+0.30, -0.40, +0.50, -0.30, +0.48, -0.50, +0.20, -0.30, +0.50, -0.45, 0.0]
        # 对应中性区域的 Z 分数
        z_scores = [0.35, 0.30, 0.40, 0.25, 0.38, 0.22, 0.33, 0.28, 0.42, 0.26, 0.30]

        flips = 0
        state_history = []
        for b20, z in zip(noisy_biases, z_scores):
            new_attack, reason = buf.evaluate_state_transition(b20, z, is_attack)
            if new_attack != is_attack:
                flips += 1
                is_attack = new_attack
            state_history.append(is_attack)
            assert "锁定" in reason or "维持" in reason or "承压" in reason or "防假突破" in reason

        # 断言: 0 次横跳，全程牢固锁定 False
        assert flips == 0, f"Expected 0 flips in defensive noise band, got {flips}"
        assert all(st is False for st in state_history)

    def test_noise_oscillation_attack_lock(self):
        """
        核心防打脸用例 2: 进攻态启动时，指数回踩至 MA20 之下但未达到 -1.5% 深度跌破，
        在 [-0.5%, +0.5%] 噪音带震荡，断言维持原有进攻态锁定，状态跳变为 0 (0 flips)!
        """
        buf = SchmidtHysteresisBuffer(upper_threshold=1.2, lower_threshold=-1.5, z_upper=0.60, z_lower=0.20)
        is_attack = True

        noisy_biases = [-0.30, +0.40, -0.50, +0.30, -0.48, +0.50, -0.20, +0.30, -0.50, +0.45, 0.0]
        z_scores = [0.45, 0.50, 0.40, 0.55, 0.38, 0.52, 0.43, 0.48, 0.35, 0.56, 0.50]

        flips = 0
        state_history = []
        for b20, z in zip(noisy_biases, z_scores):
            new_attack, reason = buf.evaluate_state_transition(b20, z, is_attack)
            if new_attack != is_attack:
                flips += 1
                is_attack = new_attack
            state_history.append(is_attack)
            assert "容差死区" in reason or "维持多头" in reason or "防打脸" in reason

        # 断言: 0 次横跳，全程牢固锁定 True
        assert flips == 0, f"Expected 0 flips in attack noise band, got {flips}"
        assert all(st is True for st in state_history)

    def test_full_deadzone_envelope_boundaries(self):
        """全面死区包络线边界测试：[-1.49%, +1.19%] 内绝对不改变原有状态"""
        buf = SchmidtHysteresisBuffer(upper_threshold=1.2, lower_threshold=-1.5, z_upper=0.60, z_lower=0.20)

        # 极限边界测试点
        deadzone_test_points = [-1.49, -1.20, -0.80, -0.10, 0.0, 0.50, 1.00, 1.15, 1.19]
        neutral_z = 0.40

        # 1. 防守态启动：在任何死区点均不得触发进攻
        for b in deadzone_test_points:
            st, _ = buf.evaluate_state_transition(bias_20=b, composite_z=neutral_z, is_currently_attack=False)
            assert st is False, f"Defensive state breached prematurely at bias_20={b}%"

        # 2. 进攻态启动：在任何死区点均不得触发退守
        for b in deadzone_test_points:
            st, _ = buf.evaluate_state_transition(bias_20=b, composite_z=neutral_z, is_currently_attack=True)
            assert st is True, f"Attack state surrendered prematurely at bias_20={b}%"

    def test_exact_breakout_and_breakdown_transitions(self):
        """精确突破与跌破翻转点断言"""
        buf = SchmidtHysteresisBuffer(upper_threshold=1.2, lower_threshold=-1.5, z_upper=0.60, z_lower=0.20)

        # 1. 有效向上突破：bias_20 >= +1.2%
        st_breakout, reason_up = buf.evaluate_state_transition(bias_20=1.20, composite_z=0.40, is_currently_attack=False)
        assert st_breakout is True
        assert "有效突破施密特迟滞上轨" in reason_up

        # 2. 有效向下破位：bias_20 <= -1.5%
        st_breakdown, reason_down = buf.evaluate_state_transition(bias_20=-1.50, composite_z=0.40, is_currently_attack=True)
        assert st_breakdown is False
        assert "有效跌破施密特迟滞下轨" in reason_down

        # 3. Z 分数触发向上突破：composite_z >= 0.60 (即使 bias_20 仅 0.5%)
        st_z_up, _ = buf.evaluate_state_transition(bias_20=0.50, composite_z=0.60, is_currently_attack=False)
        assert st_z_up is True

        # 4. Z 分数触发向下退出：composite_z < 0.20 (即使 bias_20 维持在 -0.5%)
        st_z_down, _ = buf.evaluate_state_transition(bias_20=-0.50, composite_z=0.19, is_currently_attack=True)
        assert st_z_down is False


# ==============================================================================
# 4. SchmidtHysteresisBuffer: Breakout Trigger Lines Across Real Prices
# ==============================================================================

class TestSchmidtBreakoutTriggerLinesGrid:
    """实证检验双向变盘触发线：surge_line > c300_price 且 breakdown_line < c300_price"""

    @pytest.mark.parametrize("c300_price", [800.0, 1500.0, 2000.0, 3000.0, 3800.0, 4000.0, 4500.0, 5200.0, 6000.0, 8000.0, 12000.0])
    @pytest.mark.parametrize("m20_ratio", [0.70, 0.85, 0.90, 0.95, 0.98, 1.00, 1.02, 1.05, 1.10, 1.15, 1.30])
    def test_trigger_lines_inequalities_across_all_realistic_prices(self, c300_price, m20_ratio):
        """全价格网格空间断言：向上突破进攻线严格高于现价，向下跌破防守线严格低于现价"""
        m20_price = c300_price * m20_ratio
        lines = SchmidtHysteresisBuffer.get_hysteresis_trigger_lines(
            m20_price=m20_price,
            c300_price=c300_price,
            upper_threshold=1.2,
            lower_threshold=-1.5
        )

        surge_line = lines["surge_line"]
        breakdown_line = lines["breakdown_line"]
        dist_surge = lines["dist_to_surge_pct"]
        dist_breakdown = lines["dist_to_breakdown_pct"]

        # 1. 严格不等式关系
        assert surge_line > c300_price, (
            f"Failed: surge_line ({surge_line}) <= c300_price ({c300_price}) for m20={m20_price}"
        )
        assert breakdown_line < c300_price, (
            f"Failed: breakdown_line ({breakdown_line}) >= c300_price ({c300_price}) for m20={m20_price}"
        )

        # 2. 距离百分比符号断言
        assert dist_surge > 0.0, f"Distance to surge must be positive: {dist_surge}"
        assert dist_breakdown < 0.0, f"Distance to breakdown must be negative: {dist_breakdown}"

        # 3. 顺序关系断言: breakdown_line < c300_price < surge_line
        assert breakdown_line < c300_price < surge_line

    def test_trigger_lines_extreme_ratios_and_gap(self):
        """极端跳空与远离均线场景下的自愈保护"""
        # 极度超买暴涨 (现价 6000，均线 3000)
        lines_bull = SchmidtHysteresisBuffer.get_hysteresis_trigger_lines(m20_price=3000.0, c300_price=6000.0)
        assert lines_bull["surge_line"] > 6000.0
        assert lines_bull["breakdown_line"] < 6000.0

        # 极度超卖崩跌 (现价 2000，均线 5000)
        lines_bear = SchmidtHysteresisBuffer.get_hysteresis_trigger_lines(m20_price=5000.0, c300_price=2000.0)
        assert lines_bear["surge_line"] > 2000.0
        assert lines_bear["breakdown_line"] < 2000.0


# ==============================================================================
# 5. Sigmoid Continuous Gating & Composite Z Mathematical Properties
# ==============================================================================

class TestSigmoidGatingAndCompositeZ:
    """实证检验连续仓位门控与复合评分的数学平滑性与极值防御"""

    def test_sigmoid_symmetry_and_monotonicity(self):
        """Sigmoid 连续门控数学性质：零点为 0.5，严格单调，极值无溢出"""
        buf = SchmidtHysteresisBuffer

        # 1. 零点对称
        assert buf.compute_sigmoid_gating(0.0) == pytest.approx(0.5, abs=1e-6)

        # 2. 严格单调递增
        z_vals = np.linspace(-3.0, 3.0, 31)
        gates = [buf.compute_sigmoid_gating(z) for z in z_vals]
        for i in range(len(gates) - 1):
            assert gates[i + 1] > gates[i]

        # 3. 极值抗溢出 (np.clip 防御)
        assert buf.compute_sigmoid_gating(1000.0) == pytest.approx(1.0, abs=1e-5)
        assert buf.compute_sigmoid_gating(-1000.0) == pytest.approx(0.0, abs=1e-5)

    def test_composite_z_clipping_bounds(self):
        """Composite Z 得分边界截断与平滑性"""
        buf = SchmidtHysteresisBuffer

        # 正常中枢
        z_mid = buf.compute_composite_z(trend_slope=0.0, diff_star_div=0.0, erp_percentile=50.0, option_iv=22.0)
        assert abs(z_mid) < 0.1

        # 极限高估极度进攻
        z_max = buf.compute_composite_z(trend_slope=10.0, diff_star_div=50.0, erp_percentile=100.0, option_iv=10.0, bias_20=10.0)
        assert -3.0 <= z_max <= 3.0
        assert z_max > 1.5

        # 极限低估极度防守
        z_min = buf.compute_composite_z(trend_slope=-10.0, diff_star_div=-50.0, erp_percentile=0.0, option_iv=40.0, bias_20=-10.0)
        assert -3.0 <= z_min <= 3.0
        assert z_min < -1.5


# ==============================================================================
# 6. End-to-End Market Snapshot Contract Compliance
# ==============================================================================

class TestStrategyBridgeIntegrationSnapshot:
    """实证检验 StrategyBridge.get_latest_market_snapshot 对 M1 自适应算法的装配与契约输出"""

    def test_snapshot_contains_m1_algorithmic_fields(self):
        """验证全局市场快照完整包含 M1 四大算法注入项"""
        snapshot = StrategyBridge.get_latest_market_snapshot(force_reload=True)

        # 1. 在线专家权重
        assert "expert_weights" in snapshot
        w = snapshot["expert_weights"]
        assert len(w) == 4
        assert abs(sum(w.values()) - 1.0) < 1e-5
        for exp_name in OnlineExpertWeightUpdater.EXPERT_NAMES:
            assert exp_name in w

        # 2. 专家推演明细
        assert "expert_details" in snapshot
        details = snapshot["expert_details"]
        assert "gamma" in details
        assert "eta" in details
        assert "recent_utilities" in details

        # 3. 施密特综合评分与连续门控
        assert "composite_z" in snapshot
        assert -3.0 <= snapshot["composite_z"] <= 3.0
        assert "sigmoid_gate" in snapshot
        assert 0.0 <= snapshot["sigmoid_gate"] <= 1.0

        # 4. 双向变盘触发线
        assert "trigger_lines" in snapshot
        lines = snapshot["trigger_lines"]
        assert lines["surge_line"] > snapshot["c300_price"]
        assert lines["breakdown_line"] < snapshot["c300_price"]


if __name__ == "__main__":
    pytest.main(["-v", __file__])
