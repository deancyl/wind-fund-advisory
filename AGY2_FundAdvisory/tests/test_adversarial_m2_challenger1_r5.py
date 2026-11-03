"""
Adversarial Stress Test Suite for Milestone 2 (R3: RMT Marchenko-Pastur Denoising & Ledoit-Wolf Shrinkage)
Author: Empirical Challenger (Challenger 1 for Milestone 2)
Focus:
1. High collinearity / Near-singular matrix condition number drop (>10^6 -> <5.0)
2. Strict positive definiteness (lambda_min >= 0.1499) across stress regimes
3. Exact trace preservation (trace == N)
4. Exact symmetry preservation
5. Identity matrix invariant
6. Covariance scale preservation (diag == original variances)
7. Full DataFrame index/column metadata preservation
8. Extreme boundaries (N=1, fat N>T, rank-1, zero variance, alpha bounds)
9. Integration with DataLoader EWMA volatility & correlation
10. Integration with PortfolioOptimizer HRP under extreme collinearity
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

# Ensure AGY2_FundAdvisory is on path
PROJECT_DIR = Path(__file__).resolve().parent.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from data_loader import denoise_covariance_matrix, DataLoader
from portfolio_optimizer import WinRateOptimizer, DEFAULT_CONSTRAINTS


class TestAdversarialRMTDenoising:
    """Empirical adversarial tests for R3 RMT Marchenko-Pastur denoising & Ledoit-Wolf shrinkage."""

    def test_adv_rmt_high_collinearity_condition_number_drop(self):
        """
        [Adversarial Challenge 1] 高共线性/近奇异矩阵测试：
        构造 10 维资产，其中资产 1 与资产 2 的相关系数高达 0.999999。
        断言原始样本相关矩阵条件数极大 (> 10^6)，经 RMT 去噪后条件数暴跌至极小区间 (如 < 5.0)。
        """
        rng = np.random.default_rng(20261103)
        n_assets = 10
        n_obs = 60

        # 生成 10 个资产的收益率序列，资产 0 与 1 极度共线性
        x = rng.standard_normal((n_obs, n_assets))
        x[:, 1] = x[:, 0] + rng.standard_normal(n_obs) * 1e-6
        raw_corr = np.corrcoef(x, rowvar=False)

        # 验证资产 0 与 1 相关性 >= 0.99999
        assert raw_corr[0, 1] >= 0.99999, f"Collinearity expected >= 0.99999, got {raw_corr[0, 1]}"

        # 原始条件数应极大 (> 10^6)
        raw_cond = np.linalg.cond(raw_corr)
        assert raw_cond > 1e6, f"Raw condition number expected > 10^6, got {raw_cond}"

        # 运行 RMT + Ledoit-Wolf 去噪
        denoised = denoise_covariance_matrix(raw_corr, n_obs=n_obs, shrink_alpha=0.15)
        denoised_cond = np.linalg.cond(denoised)

        # 断言去噪后条件数剧烈下降 (< 5.0)
        assert denoised_cond < 5.0, f"Denoised condition number expected < 5.0, got {denoised_cond}"
        # 降幅应 > 99.999%
        drop_pct = (1.0 - denoised_cond / raw_cond) * 100.0
        assert drop_pct > 99.999, f"Condition number drop percent {drop_pct}% is below 99.999%"

    def test_adv_rmt_positive_definiteness_lower_bound(self):
        """
        [Adversarial Challenge 2] 严格正定性底线测试：
        验证去噪后矩阵所有特征值均为严格正数，最小特征值 lambda_min >= 0.1499。
        对多种病态与脏数据矩阵进行遍历压测。
        """
        rng = np.random.default_rng(42)

        test_cases = []
        # Case A: 极度共线性矩阵
        n = 10
        raw_corr_a = np.eye(n)
        raw_corr_a[0, 1] = raw_corr_a[1, 0] = 0.99999
        test_cases.append(("Near-singular 10x10", raw_corr_a, 60, 0.15))

        # Case B: 全 1 秩 1 极端退化矩阵
        raw_corr_b = np.ones((10, 10))
        test_cases.append(("Rank-1 All-Ones 10x10", raw_corr_b, 60, 0.15))

        # Case C: 胖矩阵 N > T (50 资产，20 观测)，经验协方差有 30 个零特征值
        x_fat = rng.standard_normal((20, 50))
        raw_corr_c = np.corrcoef(x_fat, rowvar=False)
        test_cases.append(("Fat Matrix N=50, T=20", raw_corr_c, 20, 0.15))

        # Case D: 存在轻微负特征值的非正定扰动相关矩阵 (模拟数值截断误差)
        raw_corr_d = np.eye(8)
        raw_corr_d[0, 1] = raw_corr_d[1, 0] = 0.95
        raw_corr_d[1, 2] = raw_corr_d[2, 1] = 0.95
        raw_corr_d[0, 2] = raw_corr_d[2, 0] = -0.90  # 破坏正定性
        eigs_d = np.linalg.eigvalsh(raw_corr_d)
        assert eigs_d.min() < 0, f"Expected non-PSD matrix, got min eig {eigs_d.min()}"
        test_cases.append(("Non-PSD Corrupted 8x8", raw_corr_d, 60, 0.15))

        for name, mat, n_obs, alpha in test_cases:
            denoised = denoise_covariance_matrix(mat, n_obs=n_obs, shrink_alpha=alpha)
            eigs = np.linalg.eigvalsh(denoised)
            min_eig = eigs.min()
            assert min_eig >= 0.1499, (
                f"[{name}] Positive definiteness violation! lambda_min={min_eig:.6f} < 0.1499"
            )

    def test_adv_rmt_trace_preservation(self):
        """
        [Adversarial Challenge 3] 迹守恒物理不变量测试：
        验证去噪后的相关性矩阵对角元素恒为 1.0，矩阵迹恒等于维度 N。
        测试维度 N = 2, 5, 10, 30。
        """
        rng = np.random.default_rng(777)
        for n in [2, 5, 10, 30]:
            x = rng.standard_normal((60, n))
            corr = np.corrcoef(x, rowvar=False)
            denoised = denoise_covariance_matrix(corr, n_obs=60, shrink_alpha=0.15)

            # 对角元严格为 1.0
            assert np.allclose(np.diag(denoised), 1.0, atol=1e-8), (
                f"Diagonal is not 1.0 for N={n}: {np.diag(denoised)}"
            )
            # 迹严格等于 N
            trace_val = np.trace(denoised)
            assert np.isclose(trace_val, float(n), atol=1e-8), (
                f"Trace preservation failed for N={n}: trace={trace_val}, expected={n}"
            )

    def test_adv_rmt_symmetry(self):
        """
        [Adversarial Challenge 4] 对称性测试：
        验证去噪后矩阵满足 np.allclose(denoised, denoised.T)。
        即使输入矩阵存在非对称噪声（由于浮点抖动），去噪算子亦能输出完美对称矩阵。
        """
        rng = np.random.default_rng(888)
        n = 10
        raw = rng.standard_normal((n, n))
        # 制造轻度非对称
        asym = 0.5 * (raw + raw.T)
        asym[0, 1] += 1e-4
        np.fill_diagonal(asym, 1.0)
        asym = np.clip(asym, -1.0, 1.0)

        denoised = denoise_covariance_matrix(asym, n_obs=60, shrink_alpha=0.15)
        assert np.allclose(denoised, denoised.T, atol=1e-12), "Denoised matrix is not symmetric!"

    def test_adv_rmt_identity_matrix_invariant(self):
        """
        [Adversarial Challenge 5] 单位矩阵恒等不变量测试：
        验证 denoise_covariance_matrix(np.eye(10)) 恒等返回单位矩阵。
        同时测试 N=1, N=5, N=20 单位矩阵。
        """
        for n in [1, 5, 10, 20]:
            eye_mat = np.eye(n)
            res = denoise_covariance_matrix(eye_mat, n_obs=60, shrink_alpha=0.15)
            assert isinstance(res, np.ndarray)
            assert np.allclose(res, eye_mat, atol=1e-12), f"Identity invariant failed for N={n}"

    def test_adv_rmt_covariance_scale_preservation(self):
        """
        [Adversarial Challenge 6] 协方差输入尺度完整保留测试：
        传入对角元 != 1.0 的协方差矩阵（各资产方差跨越多个数量级，从 0.0001 到 0.25），
        验证去噪后的协方差矩阵对角线元素严格匹配原始方差，且协方差矩阵严格正定。
        """
        rng = np.random.default_rng(999)
        n = 8
        orig_vars = np.array([0.0001, 0.0025, 0.01, 0.04, 0.09, 0.16, 0.25, 0.02])
        orig_std = np.sqrt(orig_vars)

        # 构造基底相关矩阵
        corr = np.eye(n)
        corr[0, 1] = corr[1, 0] = 0.85
        corr[2, 3] = corr[3, 2] = -0.70

        # 合成协方差矩阵
        cov = corr * np.outer(orig_std, orig_std)

        denoised_cov = denoise_covariance_matrix(cov, n_obs=60, shrink_alpha=0.15)

        # 1. 对角方差尺度精确守恒
        assert np.allclose(np.diag(denoised_cov), orig_vars, atol=1e-8), (
            f"Covariance diagonal variances changed: {np.diag(denoised_cov)} vs {orig_vars}"
        )

        # 2. 对称性与正定性
        assert np.allclose(denoised_cov, denoised_cov.T, atol=1e-12), "Denoised cov is not symmetric"
        cov_eigs = np.linalg.eigvalsh(denoised_cov)
        assert cov_eigs.min() > 0, f"Denoised cov is not positive definite: min eig {cov_eigs.min()}"

    def test_adv_rmt_dataframe_metadata_preservation(self):
        """
        [Adversarial Challenge 7] DataFrame 类型与元数据保真测试：
        传入 pd.DataFrame，验证返回对象依然为 pd.DataFrame，且 index 与 columns 严格保持一致。
        分别测试相关性矩阵 DataFrame 与协方差矩阵 DataFrame。
        """
        tickers = ["510300.SH", "510500.SH", "159915.SZ", "588000.SH", "511010.SH"]
        corr_data = np.eye(5)
        corr_data[0, 1] = corr_data[1, 0] = 0.75
        df_corr = pd.DataFrame(corr_data, index=tickers, columns=tickers)

        # 1. 相关矩阵 DataFrame
        res_corr_df = denoise_covariance_matrix(df_corr, n_obs=60, shrink_alpha=0.15)
        assert isinstance(res_corr_df, pd.DataFrame), "Output must be pd.DataFrame"
        assert list(res_corr_df.index) == tickers, "DataFrame index was corrupted"
        assert list(res_corr_df.columns) == tickers, "DataFrame columns were corrupted"
        assert np.allclose(np.diag(res_corr_df.values), 1.0)

        # 2. 协方差矩阵 DataFrame
        var_vec = np.array([0.04, 0.05, 0.08, 0.12, 0.005])
        cov_data = corr_data * np.outer(np.sqrt(var_vec), np.sqrt(var_vec))
        df_cov = pd.DataFrame(cov_data, index=tickers, columns=tickers)

        res_cov_df = denoise_covariance_matrix(df_cov, n_obs=60, shrink_alpha=0.15)
        assert isinstance(res_cov_df, pd.DataFrame), "Output must be pd.DataFrame"
        assert list(res_cov_df.index) == tickers
        assert list(res_cov_df.columns) == tickers
        assert np.allclose(np.diag(res_cov_df.values), var_vec, atol=1e-8)

    def test_adv_rmt_extreme_boundaries(self):
        """
        [Adversarial Challenge 8] 极端边界测试：
        1. N=1 标量矩阵与 1x1 DataFrame
        2. shrink_alpha 边界 (alpha=0.0, alpha=1.0)
        3. 零方差资产（现金类无风险标的）
        4. 非方阵或非 2D 异常输入
        """
        # 1. N=1
        m1 = np.array([[0.04]])
        r1 = denoise_covariance_matrix(m1)
        assert np.allclose(r1, m1)

        df1 = pd.DataFrame([[1.0]], index=["CASH"], columns=["CASH"])
        r_df1 = denoise_covariance_matrix(df1)
        assert isinstance(r_df1, pd.DataFrame)
        assert np.allclose(r_df1.values, [[1.0]])

        # 2. shrink_alpha 边界
        c = np.array([[1.0, 0.9], [0.9, 1.0]])
        # alpha = 1.0 -> 必须直接变成单位阵
        r_alpha1 = denoise_covariance_matrix(c, shrink_alpha=1.0)
        assert np.allclose(r_alpha1, np.eye(2))

        # alpha = 0.0 -> 仅谱去噪，无对角收缩
        r_alpha0 = denoise_covariance_matrix(c, shrink_alpha=0.0)
        assert np.allclose(r_alpha0, r_alpha0.T)
        assert np.isclose(np.trace(r_alpha0), 2.0)

        # 3. 零方差资产边界 (极微小方差 0.0)
        c_zero = np.zeros((3, 3))
        np.fill_diagonal(c_zero, [0.0, 0.04, 0.09])
        r_zero = denoise_covariance_matrix(c_zero, shrink_alpha=0.15)
        assert np.allclose(r_zero, r_zero.T)
        assert np.all(np.isfinite(r_zero))

        # 4. 非方阵异常输入
        rect = np.zeros((3, 4))
        r_rect = denoise_covariance_matrix(rect)
        assert np.array_equal(r_rect, rect)

    def test_adv_rmt_dataloader_integration(self):
        """
        [Adversarial Challenge 9] DataLoader.compute_ewma_volatility_and_correlation 真实集成测试：
        使用高共线性资产净值数据调用 DataLoader 算子，断言输出的 corr_matrix 为去噪后的正定矩阵。
        """
        rng = np.random.default_rng(12345)
        n_days = 80
        dates = pd.date_range("2026-01-01", periods=n_days, freq="B")
        cols = ['H00300', 'H00905', 'H00852', 'H00922', 'H30269', 'STAR50_STITCH', 'AU9999', 'SPX_CNY', '930609', 'H11009']

        # 构造资产价格序列，使 H00300 与 H00905 高度共线
        p_base = (1.0 + rng.standard_normal(n_days) * 0.01).cumprod() * 100.0
        data = {}
        for c in cols:
            if c == 'H00905':
                data[c] = p_base * (1.0 + rng.standard_normal(n_days) * 1e-5)
            elif c == 'H00300':
                data[c] = p_base
            else:
                data[c] = (1.0 + rng.standard_normal(n_days) * 0.01).cumprod() * 100.0

        df_prices = pd.DataFrame(data, index=dates)

        vols, corr = DataLoader.compute_ewma_volatility_and_correlation(df_prices, window=60, span=60)

        # 断言输出类型与维度
        assert isinstance(vols, pd.Series)
        assert isinstance(corr, pd.DataFrame)
        assert corr.shape == (10, 10)

        # 断言去噪后矩阵性质
        corr_vals = corr.values
        assert np.allclose(np.diag(corr_vals), 1.0)
        assert np.isclose(np.trace(corr_vals), 10.0)
        assert np.allclose(corr_vals, corr_vals.T)

        eigs = np.linalg.eigvalsh(corr_vals)
        assert eigs.min() >= 0.1499, f"DataLoader corr matrix min eigenvalue {eigs.min()} < 0.1499"
        assert np.linalg.cond(corr_vals) < 15.0, f"DataLoader corr matrix condition number {np.linalg.cond(corr_vals)} too high"

    def test_adv_rmt_portfolio_optimizer_hrp_stress(self):
        """
        [Adversarial Challenge 10] WinRateOptimizer 层次风险平价 (HRP) 极端共线性压力测试：
        当备选基金池中存在两只净值 99.999% 复制的基金时，
        验证 HRP 在 RMT 去噪协方差/相关性矩阵支持下，平稳完成聚类与权重分配，
        不出现奇异矩阵除零异常、权重为 NaN 或权重偏激击穿约束。
        """
        rng = np.random.default_rng(54321)
        n_days = 250
        dates = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=n_days)

        nav_f1 = pd.Series(np.cumprod(1.0 + rng.normal(0.0004, 0.01, n_days)), index=dates)
        # F2 极度拟合 F1 (相关性 > 0.99999)
        nav_f2 = nav_f1 * (1.0 + rng.normal(0.0, 1e-5, n_days))
        nav_f3 = pd.Series(np.cumprod(1.0 + rng.normal(0.0002, 0.003, n_days)), index=dates)
        nav_f4 = pd.Series(np.cumprod(1.0 + rng.normal(0.0003, 0.012, n_days)), index=dates)
        nav_f5 = pd.Series(np.cumprod(1.0 + rng.normal(0.0002, 0.005, n_days)), index=dates)
        nav_f6 = pd.Series(np.cumprod(1.0 + rng.normal(0.0004, 0.015, n_days)), index=dates)

        nav_df = pd.DataFrame({
            "F1": nav_f1,
            "F2": nav_f2,
            "F3": nav_f3,
            "F4": nav_f4,
            "F5": nav_f5,
            "F6": nav_f6,
        })

        candidate_info = pd.DataFrame([
            {"fund_code": "F1", "fund_name": "共线大盘A", "bucket": "equity", "ac_pair_code": ""},
            {"fund_code": "F2", "fund_name": "共线大盘B", "bucket": "equity", "ac_pair_code": ""},
            {"fund_code": "F3", "fund_name": "稳健纯债C", "bucket": "bond", "ac_pair_code": ""},
            {"fund_code": "F4", "fund_name": "成长科技D", "bucket": "equity", "ac_pair_code": ""},
            {"fund_code": "F5", "fund_name": "海外精选E", "bucket": "overseas", "ac_pair_code": ""},
            {"fund_code": "F6", "fund_name": "黄金商品F", "bucket": "commodity", "ac_pair_code": ""},
        ])

        opt = WinRateOptimizer(
            nav_matrix=nav_df,
            candidate_info=candidate_info,
            holding_days=125,
            target_annual_return=0.06,
            tier="C4",
            model_type="hrp_cvar",
            constraints={"n_funds_range": (3, 5)},
        )

        # 1. 验证直接调用 _compute_hrp_weights
        opt._individual_metrics = opt._precompute_individual_metrics()
        hrp_weights = opt._compute_hrp_weights(["F1", "F2", "F3", "F4", "F5"], nav_df)
        assert len(hrp_weights) == 5, f"Expected 5 weights from HRP, got {hrp_weights}"
        for c, w in hrp_weights.items():
            assert np.isfinite(w), f"HRP weight for {c} is non-finite: {w}"
            assert w >= 0.0, f"HRP weight for {c} is negative: {w}"
        assert np.isclose(sum(hrp_weights.values()), 1.0, atol=1e-3)

        # 2. 验证端到端 optimize
        res = opt.optimize()
        assert res is not None, "Optimizer failed to return result"
        weights = res.get("optimal_weights", {})
        assert len(weights) >= 3, f"Expected at least 3 funds selected, got {weights}"

        # 检查权重有效性
        total_w = sum(weights.values())
        assert np.isclose(total_w, 1.0, atol=1e-3), f"Total weight {total_w} != 1.0"
        for code, w in weights.items():
            assert np.isfinite(w), f"Weight for {code} is not finite: {w}"
            assert w >= 0.0, f"Weight for {code} is negative: {w}"
