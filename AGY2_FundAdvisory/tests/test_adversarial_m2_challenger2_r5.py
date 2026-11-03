"""
Empirical Adversarial Stress Test Suite for Milestone 2 (Challenger 2 - R5)
Target: R4 Circular Block Bootstrap & Student-t Jump-Diffusion Stress Test in winrate_engine.py

Mandatory Focus Areas:
1. Volatility clustering test: verify Circular Block Bootstrap (block_size=10) preserves autocorrelation
   of squared returns significantly better than random shuffle.
2. Student-t (nu=5) Heavy-tail verification: verify paths contain fatter tails (kurtosis > 3.0) than normal.
3. 70% / 30% hybrid proportion verification.
4. 95% CVaR tail monotonicity test: verify cvar_95 <= ci_95[0] <= ci_90[0] <= median_return <= mean_return.
5. Idempotency / Seed determinism: verify identical seed produces identical results.
6. Backward compatibility: verify WinRateEngine.monte_carlo_simulation is callable and identical to monte_carlo_winrate.
7. Boundary conditions & Degenerate input safety.
"""

import sys
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest
from scipy.stats import kurtosis

PROJECT_DIR = Path(__file__).resolve().parent.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from winrate_engine import WinRateEngine


# =====================================================================
# 1. 波动率聚集测试 (Volatility Clustering Preservation: CBB vs Shuffle)
# =====================================================================

def test_volatility_clustering_cbb_preserves_autocorrelation():
    """
    [实证对抗检验 1] 波动率聚集保持测试
    构造低波动阶段 (std=0.003) 与极端高波动阶段 (std=0.035) 交替的真实聚集序列。
    断言: Circular Block Bootstrap (block_size=10) 能有效保留平方收益率的 1 阶自相关性，
    显著优于完全打乱的随机独立抽样 (Random Shuffle)。
    """
    rng = np.random.default_rng(2026)
    # 构造 240 个交易日的波动率聚集行情: 60天低波 + 20天高波 + 60天低波 + 20天高波 + 80天低波
    r_low1 = rng.normal(0.0002, 0.003, 60)
    r_high1 = rng.normal(-0.001, 0.035, 20)
    r_low2 = rng.normal(0.0003, 0.003, 60)
    r_high2 = rng.normal(0.002, 0.035, 20)
    r_low3 = rng.normal(0.0001, 0.003, 80)
    daily_returns = np.concatenate([r_low1, r_high1, r_low2, r_high2, r_low3])
    nav_series = pd.Series(100.0 * np.cumprod(1.0 + daily_returns))

    n = len(daily_returns)
    ret_sq = daily_returns ** 2
    orig_ac = np.corrcoef(ret_sq[:-1], ret_sq[1:])[0, 1]
    assert orig_ac > 0.15, f"原始聚集序列的平方收益率自相关性必须显著 (>0.15), 实际为: {orig_ac}"

    # 1. 模拟 CBB (block_size=10) 抽样
    holding_days = 60
    eff_block_size = 10
    n_blocks = int(np.ceil(holding_days / eff_block_size))
    actual_path_len = n_blocks * eff_block_size
    n_paths = 1000

    block_starts = rng.integers(0, n, size=(n_paths, n_blocks))
    d_indices = np.arange(eff_block_size)
    cbb_idx = (block_starts[:, :, None] + d_indices[None, None, :]) % n
    cbb_paths = daily_returns[cbb_idx.reshape(n_paths, actual_path_len)[:, :holding_days]]

    cbb_acs = [
        np.corrcoef((cbb_paths[i] ** 2)[:-1], (cbb_paths[i] ** 2)[1:])[0, 1]
        for i in range(n_paths)
    ]
    cbb_mean_ac = float(np.nanmean(cbb_acs))

    # 2. 模拟 i.i.d. 纯随机打乱抽样 (Random Shuffle, block_size=1)
    shuf_paths = rng.choice(daily_returns, size=(n_paths, holding_days), replace=True)
    shuf_acs = [
        np.corrcoef((shuf_paths[i] ** 2)[:-1], (shuf_paths[i] ** 2)[1:])[0, 1]
        for i in range(n_paths)
    ]
    shuf_mean_ac = float(np.nanmean(shuf_acs))

    # 核心实证断言:
    # CBB 均值自相关性应保留至少 > 0.10，且显著高于随机打乱 (差距 >= 0.10)
    assert cbb_mean_ac > 0.10, f"CBB 必须有效保留波动率聚集自相关性，实际为: {cbb_mean_ac}"
    assert shuf_mean_ac < 0.05, f"随机打乱序列自相关性应接近 0，实际为: {shuf_mean_ac}"
    assert cbb_mean_ac - shuf_mean_ac > 0.10, (
        f"CBB 自相关性 ({cbb_mean_ac:.4f}) 必须显著优于随机打乱 ({shuf_mean_ac:.4f})"
    )


# =====================================================================
# 2. Student-t (nu=5) 厚尾性质实证核验 (Heavy-tail Kurtosis > 3.0)
# =====================================================================

def test_student_t_heavy_tail_kurtosis():
    """
    [实证对抗检验 2] Student-t (nu=5) 厚尾性质实证核验
    理论上 nu=5 的 Student-t 峰度为 9.0 (超额峰度 6.0)，而标准正态分布峰度为 3.0。
    验证 monte_carlo_winrate 中 Student-t 扰动路径的样本峰度显著大于 3.0。
    """
    rng = np.random.default_rng(42)
    nav = pd.Series(100.0 * np.cumprod(1.0 + rng.standard_normal(250) * 0.01 + 0.0003))

    captured = {}
    orig_vstack = np.vstack

    def spy_vstack(tup):
        res = orig_vstack(tup)
        if len(tup) == 2 and isinstance(tup[0], np.ndarray) and isinstance(tup[1], np.ndarray):
            captured['cbb'] = tup[0]
            captured['student'] = tup[1]
        return res

    with patch('numpy.vstack', side_effect=spy_vstack):
        res = WinRateEngine.monte_carlo_winrate(
            nav, holding_days=60, target_annual_return=0.08, n_paths=10000, seed=42
        )

    assert 'student' in captured and 'cbb' in captured
    student_paths = captured['student']
    cbb_paths = captured['cbb']

    # 计算 Student-t 路径收益率的样本峰度 (fisher=False: 正态分布为 3.0)
    student_kurt = float(kurtosis(student_paths.flatten(), fisher=False))
    hybrid_kurt = float(kurtosis(np.vstack([cbb_paths, student_paths]).flatten(), fisher=False))

    # 断言 1: Student-t 路径的峰度必须显著厚尾 (峰度 >= 5.0，远超正态 3.0)
    assert student_kurt > 5.0, f"Student-t (nu=5) 路径必须呈厚尾特性 (kurtosis > 5.0), 实际为: {student_kurt}"

    # 断言 2: 70/30 混合路径整体峰度由于 Student-t 的注入，也必须显著大于 3.0
    assert hybrid_kurt > 3.5, f"混合扰动路径整体峰度必须大于 3.5, 实际为: {hybrid_kurt}"

    # 断言 3: 方差归一化因子 sqrt(5/3) 检验
    daily_ret = nav.values[1:] / nav.values[:-1] - 1.0
    expected_sigma = float(np.std(daily_ret, ddof=1))
    actual_student_sigma = float(np.std(student_paths))
    assert abs(actual_student_sigma - expected_sigma) / expected_sigma < 0.08, (
        f"Student-t 经 sqrt(5/3) 归一化后方差应精确对齐历史样本方差: "
        f"实际={actual_student_sigma:.6f}, 期望={expected_sigma:.6f}"
    )


# =====================================================================
# 3. 70% / 30% 混合路径比例严格验证 (Hybrid Proportion)
# =====================================================================

def test_hybrid_proportion_exact_path_count():
    """
    [实证对抗检验 3] 70% / 30% 路径分配比例验证
    断言: 无论 n_paths 如何变化，CBB 路径数与 Student-t 路径数均严格按 70% / 30% 划分。
    """
    rng = np.random.default_rng(101)
    nav = pd.Series(100.0 * np.cumprod(1.0 + rng.standard_normal(250) * 0.01))

    for n_paths in [500, 1000, 3333, 10000]:
        captured = {}
        orig_vstack = np.vstack

        def make_spy(cap):
            def spy_vstack(tup):
                res = orig_vstack(tup)
                if len(tup) == 2 and isinstance(tup[0], np.ndarray) and isinstance(tup[1], np.ndarray):
                    cap['cbb'] = tup[0]
                    cap['student'] = tup[1]
                return res
            return spy_vstack

        with patch('numpy.vstack', side_effect=make_spy(captured)):
            WinRateEngine.monte_carlo_winrate(nav, holding_days=30, target_annual_return=0.08, n_paths=n_paths, seed=42)

        cbb_n = captured['cbb'].shape[0]
        student_n = captured['student'].shape[0]
        expected_cbb_n = int(0.70 * n_paths)
        expected_student_n = n_paths - expected_cbb_n

        assert cbb_n == expected_cbb_n, f"CBB 路径数应为 {expected_cbb_n}, 实际为: {cbb_n}"
        assert student_n == expected_student_n, f"Student-t 路径数应为 {expected_student_n}, 实际为: {student_n}"
        assert cbb_n + student_n == n_paths


def test_hybrid_proportion_discrete_series_separation():
    """
    [实证对抗检验 3 延伸] 基于离散收益率序列的无入侵 70/30 分离验证
    构造交替 +/-1% 的离散历史收益率序列。
    CBB 抽样取值严格局限在离散集 {-0.01, +0.01} 内；
    Student-t 抽样取值为连续实数，落在有限离散集的测度为 0。
    直接通过路径取值统计验证 70% 离散与 30% 连续的精确拆分。
    """
    # 构造交替序列: 100 天, 日收益率交替 +0.01 与 -0.01
    rets = np.array([0.01 if i % 2 == 0 else -0.01 for i in range(100)])
    nav = pd.Series(100.0 * np.cumprod(1.0 + rets))

    n_paths = 5000
    holding_days = 20

    # 捕获堆叠路径
    captured = {}
    orig_vstack = np.vstack
    def spy(tup):
        res = orig_vstack(tup)
        if len(tup) == 2:
            captured['paths'] = res
        return res

    with patch('numpy.vstack', side_effect=spy):
        WinRateEngine.monte_carlo_winrate(nav, holding_days=holding_days, target_annual_return=0.08, n_paths=n_paths, seed=42)

    paths = captured['paths']
    assert paths.shape == (n_paths, holding_days)

    # 检查每条路径是否全部由 {-0.01, 0.01} 构成
    is_cbb_path = np.all(np.isclose(paths, 0.01) | np.isclose(paths, -0.01), axis=1)
    cbb_count = int(np.sum(is_cbb_path))
    student_count = n_paths - cbb_count

    expected_cbb = int(0.70 * n_paths)
    expected_student = n_paths - expected_cbb

    assert cbb_count == expected_cbb, f"离散验证 CBB 路径数必须为 {expected_cbb}, 实际为: {cbb_count}"
    assert student_count == expected_student, f"离散验证 Student-t 路径数必须为 {expected_student}, 实际为: {student_count}"


# =====================================================================
# 4. 95% CVaR 尾部单调性实证测试 (Tail Monotonicity Test)
# =====================================================================

def test_cvar_tail_monotonicity_across_horizons_and_classes():
    """
    [实证对抗检验 4] 95% CVaR 尾部单调性定理检验
    数学不变量:
    cvar_95 (最差 5% 条件在险均值) <= ci_95[0] (2.5% 分位数) <= ci_90[0] (5.0% 分位数) <= median_return <= mean_return
    在短、中、长期持有期及 A/C 份额与交易摩擦全场景下恒成立。
    """
    rng = np.random.default_rng(888)
    # 模拟真实 A 股中证800 风格偏股基金净值走势
    daily_ret = rng.normal(0.0004, 0.012, 350)
    nav = pd.Series(100.0 * np.cumprod(1.0 + daily_ret))

    test_horizons = [20, 60, 125, 250]
    test_classes = ["A", "C"]
    test_frictions = [True, False]

    for days in test_horizons:
        for ft in test_classes:
            for friction in test_frictions:
                res = WinRateEngine.monte_carlo_winrate(
                    nav_series=nav,
                    holding_days=days,
                    target_annual_return=0.08,
                    n_paths=3000,
                    include_friction=friction,
                    fund_type=ft,
                    seed=42,
                )

                cvar_95 = res["cvar_95"]
                ci_95_lo = res["ci_95"][0]
                ci_90_lo = res["ci_90"][0]
                median_ret = res["median_return"]
                mean_ret = res["mean_return"]

                # 核心单调性链条断言
                assert cvar_95 <= ci_95_lo + 1e-6, (
                    f"CVaR 95% ({cvar_95}) 必须 <= 2.5% 分位数 ({ci_95_lo}) [days={days}, ft={ft}]"
                )
                assert ci_95_lo <= ci_90_lo + 1e-6, (
                    f"2.5% 分位数 ({ci_95_lo}) 必须 <= 5% 分位数 ({ci_90_lo}) [days={days}, ft={ft}]"
                )
                assert ci_90_lo <= median_ret, (
                    f"5% 分位数 ({ci_90_lo}) 必须 <= 中位数 ({median_ret}) [days={days}, ft={ft}]"
                )
                assert median_ret <= mean_ret, (
                    f"几何复利正偏偏度下中位数 ({median_ret}) 必须 <= 均值 ({mean_ret}) [days={days}, ft={ft}]"
                )

                # 确认年化与非年化别名字段一致性
                assert res["cvar_95"] == res["cvar_95_annualized"]


# =====================================================================
# 5. 随机数种子幂等性与确定性测试 (Idempotency / Seed Determinism)
# =====================================================================

def test_monte_carlo_seed_determinism_and_entropy():
    """
    [实证对抗检验 5] 随机数种子幂等性与熵验证
    1. 相同 seed 输入下，两次运行返回的所有数值必须 100% 逐比特全同；
    2. 不同 seed 输入下，结果必须产生真随机波动，杜绝虚假 Mock/硬编码。
    """
    rng = np.random.default_rng(42)
    nav = pd.Series(100.0 * np.cumprod(1.0 + rng.standard_normal(200) * 0.01))

    # 1. 相同种子完全幂等
    run1 = WinRateEngine.monte_carlo_winrate(nav, holding_days=60, target_annual_return=0.08, n_paths=2000, seed=12345)
    run2 = WinRateEngine.monte_carlo_winrate(nav, holding_days=60, target_annual_return=0.08, n_paths=2000, seed=12345)

    assert run1["prob_reach_target"] == run2["prob_reach_target"]
    assert run1["prob_no_loss"] == run2["prob_no_loss"]
    assert run1["ci_90"] == run2["ci_90"]
    assert run1["ci_95"] == run2["ci_95"]
    assert run1["mean_return"] == run2["mean_return"]
    assert run1["median_return"] == run2["median_return"]
    assert run1["cvar_95"] == run2["cvar_95"]
    assert run1["distribution_percentiles"] == run2["distribution_percentiles"]

    # 2. 不同种子产生有效随机波动
    run3 = WinRateEngine.monte_carlo_winrate(nav, holding_days=60, target_annual_return=0.08, n_paths=2000, seed=99999)
    assert run1["mean_return"] != run3["mean_return"], "不同 seed 必须产生不同的随机路径结果"
    assert run1["cvar_95"] != run3["cvar_95"]


# =====================================================================
# 6. 向后兼容性测试 (Backward Compatibility: monte_carlo_simulation)
# =====================================================================

def test_backward_compatibility_simulation_alias():
    """
    [实证对抗检验 6] 向后兼容性检验
    验证 WinRateEngine.monte_carlo_simulation 别名完全保留，
    可被正常调用且产生与 monte_carlo_winrate 100% 全同的结果。
    """
    assert hasattr(WinRateEngine, "monte_carlo_simulation"), "必须保留 monte_carlo_simulation 别名"
    assert callable(WinRateEngine.monte_carlo_simulation), "monte_carlo_simulation 必须为可调用对象"
    assert WinRateEngine.monte_carlo_simulation == WinRateEngine.monte_carlo_winrate, (
        "monte_carlo_simulation 必须直接指向 monte_carlo_winrate"
    )

    rng = np.random.default_rng(7)
    nav = pd.Series(100.0 * np.cumprod(1.0 + rng.standard_normal(150) * 0.01))

    res_old = WinRateEngine.monte_carlo_simulation(nav, holding_days=45, target_annual_return=0.06, n_paths=1500, seed=77)
    res_new = WinRateEngine.monte_carlo_winrate(nav, holding_days=45, target_annual_return=0.06, n_paths=1500, seed=77)

    assert res_old == res_new
    assert "cvar_95" in res_old
    assert "cvar_95_annualized" in res_old


# =====================================================================
# 7. 极端与退化边界条件测试 (Boundary Conditions & Stress Hardening)
# =====================================================================

def test_adversarial_boundary_conditions_and_zero_variance():
    """
    [实证对抗检验 7] 极端退化输入与边界安全性
    覆盖: 样本数 < 5, holding_days <= 0, n_paths <= 0, 零方差平盘净值, 极端 block_size。
    """
    # 1. 样本数过少 (< 5)
    res_short = WinRateEngine.monte_carlo_winrate(pd.Series([1.0, 1.01, 1.02]), 60, 0.08)
    assert res_short["cvar_95"] == 0.0
    assert res_short["prob_reach_target"] == 0.0

    # 2. holding_days <= 0
    res_zero_days = WinRateEngine.monte_carlo_winrate(pd.Series(range(10, 30)), 0, 0.08)
    assert res_zero_days["cvar_95"] == 0.0
    assert res_zero_days["prob_no_loss"] == 0.0

    # 3. n_paths <= 0
    res_zero_paths = WinRateEngine.monte_carlo_winrate(pd.Series(range(10, 30)), 20, 0.08, n_paths=0)
    assert res_zero_paths["cvar_95"] == 0.0

    # 4. 全平盘净值 (sigma = 0): 测试 sigma < 1e-8 截断保护
    flat_nav = pd.Series([100.0] * 50)
    res_flat = WinRateEngine.monte_carlo_winrate(flat_nav, 30, 0.08, n_paths=1000)
    assert not np.isnan(res_flat["cvar_95"])
    assert not np.isnan(res_flat["mean_return"])
    assert not np.isnan(res_flat["median_return"])

    # 5. block_size = 1 (退化为完全独立同分布抽样)
    norm_nav = pd.Series(100.0 * np.cumprod(1.0 + np.random.randn(60) * 0.01))
    res_b1 = WinRateEngine.monte_carlo_winrate(norm_nav, 20, 0.08, n_paths=500, block_size=1)
    assert np.isfinite(res_b1["cvar_95"])

    # 6. block_size > len(daily_returns) (应被安全 clamp)
    res_b_huge = WinRateEngine.monte_carlo_winrate(norm_nav, 20, 0.08, n_paths=500, block_size=9999)
    assert np.isfinite(res_b_huge["cvar_95"])


# =====================================================================
# 8. 组合级综合胜率与 CVaR 联动测试 (Portfolio Composite WinRate)
# =====================================================================

def test_portfolio_composite_winrate_integrates_r4_cvar():
    """
    [实证对抗检验 8] 组合级综合胜率联动测试
    验证 portfolio_composite_winrate 正确接入 upgrade 后的 monte_carlo_winrate，
    且其返回的 monte_carlo 字典中包含合规的 cvar_95 指标。
    """
    rng = np.random.default_rng(42)
    dates = pd.date_range("2026-01-01", periods=100, freq="B")
    nav1 = pd.Series((1.0 + rng.normal(0.0005, 0.01, 100)).cumprod(), index=dates)
    nav2 = pd.Series((1.0 + rng.normal(0.0002, 0.003, 100)).cumprod(), index=dates)

    nav_matrix = pd.DataFrame({"005561": nav1, "002351": nav2})
    weights = {"005561": 0.60, "002351": 0.40}

    res = WinRateEngine.portfolio_composite_winrate(
        nav_matrix=nav_matrix,
        weights=weights,
        holding_days=30,
        target_annual_return=0.08,
        include_friction=True,
    )

    assert "monte_carlo" in res
    mc = res["monte_carlo"]
    assert "cvar_95" in mc
    assert "cvar_95_annualized" in mc
    assert mc["cvar_95"] <= mc["ci_95"][0] <= mc["ci_90"][0] <= mc["median_return"] <= mc["mean_return"]
