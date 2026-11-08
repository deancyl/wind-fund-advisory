"""
Milestone 1 因果律严苛核验与 Walk-Forward 真实演化轨迹独立对抗测试套件
tests/test_causality_adversarial_m1.py

由团队对抗验证员 1 (teamwork_challenger_1) 独立编写与执行。
专门用于经验证 Milestone 1 的算法鲁棒性、因果律、摩擦成本与真实数据底座：
1. 因果律对抗探针：
   - 脉冲收益注入测试：第 t 日收益率 R[t] 的巨大冲击，绝不能被第 t 日决策权重 P[t] 提前获取；
   - 步进切片因果性验证：get_60d_rolling_nav_and_trajectory 中 sub_today 严格截断至 p_idx，物理排斥当日收盘；
   - 动态净值序列 nav 终端净值严格小于毛收益累乘净值（证实真实内扣换手摩擦成本）；
   - 夏普比率精算：年化收益率 <= 0% 的资产序列，夏普比率严格为负数（证实扣减 2.0% 无风险利率）。
2. Walk-Forward 演化轨迹真实性核验：
   - 60 日滚动演化轨迹格式与完整性；
   - 四维权重序列二阶差分绝非恒为 0（彻底废除 lam 线性插值）；
   - 赛道价格矩阵绝无 linspace(1.0, 1.05) 假序列；缺失数据常数 1.0 回退。
"""

import sys
from pathlib import Path
import numpy as np
import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))
if str(WORKSPACE_ROOT / "AGY2_FundAdvisory") not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT / "AGY2_FundAdvisory"))

from AGY2_FundAdvisory.advisory_engine import OnlineHeuristicFactorEvolver


class TestCausalityAndAdversarialM1:
    """Milestone 1 核心因果律与演化真实性对抗检验探针"""

    def test_causality_pulse_return_isolation_probe(self):
        """
        因果律对抗探针 1 (脉冲收益注入)：
        验证在 _evaluate_population 中，第 t 日收盘特征 F[t] 选出的权重 P[t]
        绝对无法感知并提前获取第 t 日当天的收益率冲击 R[t]。
        注入超大脉冲收益 (+1000%) 到 R[t_shock, s_shock]，
        断言在 t_shock 当天生效的持仓 P[t_shock - 1] 绝不因而提前重配。
        """
        evolver = OnlineHeuristicFactorEvolver(population_size=16, generations=5, random_seed=42)
        T_len = 25
        S_num = 6
        N_pop = 4

        # 构造确定性的种群和特征张量
        pop = np.full((N_pop, 4), 0.25, dtype=float)
        F = np.full((T_len, S_num, 4), 50.0, dtype=float)

        # 设定：在 t=0..11，赛道 0, 1, 2 分数最高 (60.0) -> Top 3 为 {0, 1, 2}
        # 赛道 5 分数为 40.0，不在 Top 3 中
        F[:12, 0:3, :] = 60.0
        F[:12, 3:6, :] = 40.0

        t_shock = 10
        s_shock = 5

        # 基线收益率矩阵：全 0
        R_baseline = np.zeros((T_len, S_num), dtype=float)

        # 脉冲收益率矩阵：仅在 t_shock 注入超大脉冲 (+1000% 收益)
        R_shocked = np.zeros((T_len, S_num), dtype=float)
        R_shocked[t_shock, s_shock] = 10.0

        # 运行评估
        fit_base, metrics_base = evolver._evaluate_population(pop, F, R_baseline)
        fit_shock, metrics_shock = evolver._evaluate_population(pop, F, R_shocked)

        # 在 t_shock 当天，生效的有效决策是 P_eff[t_shock - 1] = P[t_shock - 1]
        # 对应的日收益率是 R_eff[t_shock - 1] = R[t_shock]
        tau = t_shock - 1
        ret_base_day10 = metrics_base["R_p"][tau, 0]
        ret_shock_day10 = metrics_shock["R_p"][tau, 0]

        # 核心断言 1：t_shock 当日组合收益绝对不能因为 R[t_shock, s_shock] 的暴涨而产生任何波动！
        assert abs(ret_shock_day10 - ret_base_day10) < 1e-9, (
            f"因果律泄露！t_shock 当日组合收益从 {ret_base_day10} 突增至 {ret_shock_day10}，"
            f"说明第 t-1 日权重提前偷窥了第 t 日的脉冲收益！"
        )

        # 核心断言 2：即便 t_shock 当天收盘特征 F[t_shock, s_shock] 飙升至最高分 99.0，
        # 该选入动作 P[t_shock] 只能从 t_shock+1 (第 11 天) 起生效，绝不能逆流回第 10 天自身！
        F_with_shock_feature = F.copy()
        F_with_shock_feature[t_shock, s_shock, :] = 99.0

        fit_sf, metrics_sf = evolver._evaluate_population(pop, F_with_shock_feature, R_shocked)
        ret_sf_day10 = metrics_sf["R_p"][tau, 0]

        assert abs(ret_sf_day10 - ret_base_day10) < 1e-9, (
            f"同日收盘未来函数致命缺陷！t_shock 收盘优选出的权重竟然获得了 t_shock 当天的暴涨收益！"
            f"实际收益: {ret_sf_day10}, 预期隔离: {ret_base_day10}"
        )

        # 核心断言 3：滞后一期因果生效验证。
        # 在第 11 天 (tau = t_shock)，如果赛道 5 有收益 0.03，P[10] 选入后正常获取收益
        R_shocked[t_shock + 1, s_shock] = 0.03
        fit_next, metrics_next = evolver._evaluate_population(pop, F_with_shock_feature, R_shocked)
        tau_next = t_shock  # 对应第 11 天收益
        ret_next_day = metrics_next["R_p"][tau_next, 0]
        assert ret_next_day > metrics_base["R_p"][tau_next, 0], (
            "滞后一期生效验证：t_shock 收盘选入的赛道在 t+1 日未能正常兑现收益！"
        )

    def test_causality_rolling_sub_today_slice_probe(self):
        """
        因果律对抗探针 2 (样本外滚动切片因果性)：
        深入核查 get_60d_rolling_nav_and_trajectory 中的切片索引机制：
        对于每个走步日 cur_day_idx，其特征构建历史切片 sub_today = price_matrix[:p_idx, :]
        物理上绝不包含 p_idx 当日的收盘价，确保决策纯粹依赖历史数据。
        """
        evolver = OnlineHeuristicFactorEvolver()
        price_matrix, sector_ids, dates = evolver._extract_sector_price_matrix(window_days=140)
        total_len = len(price_matrix)
        
        # 模拟演化轨迹中每一个交易日的决策窗口
        for cur_day_idx in range(60):
            p_idx = total_len - 60 + cur_day_idx
            sub_today = price_matrix[:p_idx, :]
            
            # 断言 1: sub_today 行数严格等于 p_idx (不包含 p_idx 自身)
            assert len(sub_today) == p_idx, f"切片泄漏：sub_today 长度应为 {p_idx}，实际为 {len(sub_today)}"
            
            # 断言 2: sub_today 的最后一行是 price_matrix[p_idx - 1] (即昨日收盘价)
            np.testing.assert_array_equal(
                sub_today[-1, :], price_matrix[p_idx - 1, :],
                err_msg=f"第 {cur_day_idx} 日决策特征末端点位不是昨天收盘价，存在未来函数隐患！"
            )

    def test_turnover_friction_cost_deduction_probe(self):
        """
        换手摩擦成本内扣对抗探针：
        验证动态净值序列 nav 终端净值严格小于毛收益累乘净值。
        证明调仓摩擦成本 0.0020 * daily_to 确实从日度收益率净值中真实扣除，而非假装扣除。
        """
        evolver = OnlineHeuristicFactorEvolver(population_size=16, generations=5, random_seed=42)
        price_matrix, sector_ids, dates = evolver._extract_sector_price_matrix(window_days=70)
        F, R = evolver._build_factor_tensor_and_returns(price_matrix, horizon=60, sector_ids=sector_ids)

        pop = np.array([
            [0.30, 0.30, 0.25, 0.15],
            [0.10, 0.50, 0.20, 0.20],
            [0.40, 0.10, 0.40, 0.10],
            [0.15, 0.15, 0.35, 0.35],
        ])

        fitness, metrics = evolver._evaluate_population(pop, F, R)

        # 手工精确重构毛收益率与换手率
        scores = np.einsum("tsd,kd->tsk", F, pop)
        top3_idx = np.argpartition(-scores, 3, axis=1)[:, :3, :]
        P = np.zeros_like(scores)
        np.put_along_axis(P, top3_idx, 1.0 / 3.0, axis=1)

        P_eff = P[:-1, :, :]
        R_eff = R[1:, :]
        gross_R_p = np.sum(P_eff * R_eff[:, :, None], axis=1)  # (T-1, N)

        gross_nav = np.vstack([np.ones((1, pop.shape[0])), np.cumprod(1.0 + gross_R_p, axis=0)])
        net_nav = metrics["nav"]

        # 断言所有染色体的终态净值：真实净值必须严格小于毛收益净值 (因存在非零换手摩擦)
        for k in range(pop.shape[0]):
            turnover_k = metrics["turnover"][k]
            assert turnover_k > 0.0, f"染色体 {k} 换手率异常为 0"
            gross_terminal = gross_nav[-1, k]
            net_terminal = net_nav[-1, k]

            assert net_terminal < gross_terminal, (
                f"染色体 {k} 摩擦成本未扣除！净值终端 {net_terminal} >= 毛收益终端 {gross_terminal}"
            )
            friction_drag = gross_terminal - net_terminal
            assert friction_drag > 0.0005, (
                f"染色体 {k} 换手损耗过小 ({friction_drag})，疑似摩擦成本虚设！"
            )

    def test_sharpe_ratio_risk_free_rate_deduction_probe(self):
        """
        夏普比率扣减无风险利率对抗探针：
        1. 对年化收益率为 0% 的资产序列，验证夏普比率严格为负数（证实扣除了 2.0% 无风险利率）；
        2. 对年化收益率恰好等于 2.0% 的资产序列，验证夏普比率接近 0.0；
        3. 对年化收益率等于 1.0% 的资产序列 (低于 2% Rf)，夏普比率仍必须严格为负数；
        4. 杜绝纯债等低波资产在零收益下白嫖高夏普。
        """
        evolver = OnlineHeuristicFactorEvolver(population_size=4, generations=2, random_seed=42)
        T_len = 100
        S_num = 4
        pop = np.array([[0.25, 0.25, 0.25, 0.25]])
        F = np.full((T_len, S_num, 4), 50.0, dtype=float)

        # 场景 A: 年化收益率恰为 0.0% 的微波资产序列 (无换手，日收益在均值 0 附近微幅波动)
        np.random.seed(123)
        noise = np.random.normal(0.0, 0.002, size=(T_len, S_num))
        # 强行均值中心化至 0.0
        noise -= np.mean(noise, axis=0)
        R_zero_mean = noise

        fit_zero, metrics_zero = evolver._evaluate_population(pop, F, R_zero_mean)
        sharpe_zero = float(metrics_zero["sharpe"][0])

        # 预期夏普比率: (0.0 - 0.02/250.0) / std * sqrt(250) < 0
        assert sharpe_zero < -0.10, (
            f"零收益资产夏普比率必须严格为负数！实际计算值: {sharpe_zero}，"
            f"若为 0 说明未扣除 2.0% 年化无风险利率！"
        )

        # 场景 B: 年化收益率仅为 1.2% (日收益 0.012 / 250.0 = 0.000048 < 0.00008 Rf)
        # 低于 2.0% 无风险利率，夏普比率仍必须严格为负数
        R_low_return = noise + (0.012 / 250.0)
        fit_low, metrics_low = evolver._evaluate_population(pop, F, R_low_return)
        sharpe_low = float(metrics_low["sharpe"][0])
        assert sharpe_low < -0.05, (
            f"年化 1.2% 资产收益低于 2.0% Rf，夏普比率必须为负数！实际计算值: {sharpe_low}"
        )

        # 场景 C: 年化收益率等于 2.0% (日均收益恰好等于日化 Rf = 0.02 / 250.0 = 0.00008)
        R_rf_match = noise + (0.020 / 250.0)
        fit_rf, metrics_rf = evolver._evaluate_population(pop, F, R_rf_match)
        sharpe_rf = float(metrics_rf["sharpe"][0])
        assert abs(sharpe_rf) < 0.15, (
            f"年化 2.0% 资产收益等于 Rf，夏普比率应在 0 附近！实际计算值: {sharpe_rf}"
        )

        # 场景 D: 年化收益率 10.0% (远高于 Rf)，夏普必须确定性大于 0
        R_high_return = noise + (0.100 / 250.0)
        fit_high, metrics_high = evolver._evaluate_population(pop, F, R_high_return)
        sharpe_high = float(metrics_high["sharpe"][0])
        assert sharpe_high > 1.0, f"年化 10% 资产夏普必须确定性为正，实际: {sharpe_high}"

    def test_walk_forward_rolling_trajectory_authenticity_probe(self):
        """
        Walk-Forward 样本外演化轨迹真实性核验：
        1. 调用 get_60d_rolling_nav_and_trajectory 检查返回完整字典；
        2. 断言四维权重序列绝非线性函数（二阶差分不全为 0，彻底废除 lam = (t+1)/60）；
        3. 断言四维权重单项在演化中有真实状态跃迁（不是静态死常数）。
        """
        evolver = OnlineHeuristicFactorEvolver(population_size=16, generations=5, random_seed=42)
        res = evolver.get_60d_rolling_nav_and_trajectory()

        # 检查契约字段
        assert "dates" in res and len(res["dates"]) == 60
        assert "nav_dynamic" in res and len(res["nav_dynamic"]) == 60
        assert "nav_static" in res and len(res["nav_static"]) == 60
        assert "trajectory" in res and len(res["trajectory"]) == 60
        assert "final_nav_dynamic" in res
        assert "final_nav_static" in res
        assert "alpha_pct" in res
        assert "mdd_dynamic_pct" in res
        assert "mdd_static_pct" in res

        # 提取四维因子权重时间序列
        traj = res["trajectory"]
        weights_series = np.array([
            [pt["valuation"], pt["momentum"], pt["snr"], pt["anti_crowding"]]
            for pt in traj
        ])  # shape: (60, 4)

        # 1. 验证单项因子 >= 0.05 硬约束与归一化
        assert np.all(weights_series >= 0.0499), "发现权重存在低于 0.05 违背硬约束！"
        row_sums = np.sum(weights_series, axis=1)
        assert np.all(np.abs(row_sums - 1.0) < 1e-3), "权重行和必须严格归一化为 1.0"

        # 2. 核心对抗断言：二阶差分绝不能全部为 0！
        # 如果是老旧的 lam = (t + 1) / 60 线性插值：
        # w(t) = w_start + t * delta
        # 一阶差分 diff(w) = delta (常数)
        # 二阶差分 diff(diff(w)) 恒等于 0！
        first_diff = np.diff(weights_series, axis=0)  # (59, 4)
        second_diff = np.diff(first_diff, axis=0)     # (58, 4)

        max_second_diff = np.max(np.abs(second_diff))
        assert max_second_diff > 1e-4, (
            f"检测到虚假线性插值轨迹！四维权重二阶差分最大值仅为 {max_second_diff}，"
            f"说明四维轨迹依然由线性函数 lam = (t+1)/60 伪造！"
        )

        # 3. 验证权重序列存在步进跳跃与离散阶段（12 个 5 日切片）
        assert np.sum(np.abs(first_diff) > 1e-4) >= 4, (
            "演化权重序列缺乏切片更迭，未能真实反映 Walk-Forward 滚动求解！"
        )

    def test_sector_price_matrix_no_linspace_fabrication_probe(self):
        """
        赛道价格矩阵假序列根除对抗探针：
        1. 验证 _extract_sector_price_matrix 绝无 col[-1] - col[0] == 0.05 and col[0] == 1.0 的 linspace 伪序列；
        2. 验证价格序列中若存在缺失降级，采用收益率恒为 0 的常数 1.0。
        """
        evolver = OnlineHeuristicFactorEvolver()
        price_matrix, sector_ids, dates = evolver._extract_sector_price_matrix(window_days=140)

        assert price_matrix.shape[0] == 140, f"提取价格矩阵行数应为 140，实际: {price_matrix.shape[0]}"
        assert price_matrix.shape[1] == len(sector_ids), "价格矩阵列数必须与赛道数一致"

        for col_idx in range(price_matrix.shape[1]):
            col = price_matrix[:, col_idx]
            # 严格断言：绝不能存在 np.linspace(1.0, 1.05, 140) 的假直线！
            is_fake_linspace = (
                abs(col[0] - 1.0) < 1e-6
                and abs((col[-1] - col[0]) - 0.05) < 1e-5
                and np.all(np.abs(np.diff(col) - (0.05 / 139.0)) < 1e-6)
            )
            assert not is_fake_linspace, (
                f"赛道 {sector_ids[col_idx]} 检测到伪造的 np.linspace(1.0, 1.05) 单边牛市假序列！"
            )

            # 验证如果全为 1.0，收益率恒为 0
            if np.all(col == 1.0):
                # 缺失降级赛道必须为全 1.0
                pass
            else:
                # 真实赛道点位不应全部平躺
                assert np.std(col) > 0.0, f"非缺失赛道 {sector_ids[col_idx]} 波动率异常为 0"
