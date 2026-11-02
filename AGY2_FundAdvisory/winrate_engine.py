"""
多维度胜率计算引擎 (winrate_engine.py)
阶段三核心模块：提供三种胜率计算方法——
  ① 滚动持有达标胜率（含真实摩擦成本）
  ② 不亏损胜率 + 年化达标率双指标
  ③ Block Bootstrap Monte Carlo 模拟置信区间

所有滚动窗口计算使用 NumPy 向量化，禁止 Python for 循环遍历数据点。
"""

import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


# ══════════════════════════════════════════════════════════════════
#  交易摩擦成本模型
# ══════════════════════════════════════════════════════════════════

# A 类申购费率（一折后典型值）
A_PURCHASE_FEE = 0.0015

# C 类申购费率
C_PURCHASE_FEE = 0.0

# C 类年化销售服务费（取行业中值偏高）
C_ANNUAL_SERVICE_FEE = 0.004

# 阶梯赎回费率 [(最大持有天数, 费率), ...]
REDEMPTION_FEE_TIERS_A = [
    (7, 0.015),          # < 7 天：1.5% 惩罚性
    (30, 0.005),         # 7~30 天：0.5%
    (180, 0.0025),       # 30~180 天：0.25%
    (365, 0.001),        # 180~365 天：0.1%
    (730, 0.0005),       # 1~2 年：0.05%
    (float("inf"), 0.0), # 2 年+：免费
]

# C 类赎回费率（30 天后通常免费）
REDEMPTION_FEE_TIERS_C = [
    (7, 0.015),          # < 7 天：1.5% 惩罚性
    (30, 0.005),         # 7~30 天：0.5%
    (float("inf"), 0.0), # 30 天+：免费
]


def _get_redemption_fee(holding_days: int, fund_type: str = "A") -> float:
    """查阶梯赎回费率"""
    tiers = REDEMPTION_FEE_TIERS_A if fund_type == "A" else REDEMPTION_FEE_TIERS_C
    for max_days, rate in tiers:
        if holding_days < max_days:
            return rate
    return 0.0


# ══════════════════════════════════════════════════════════════════
#  持有期定义
# ══════════════════════════════════════════════════════════════════

HOLDING_PERIODS = {
    "short":  {"label": "短期3~6月",  "months_range": (3, 6),  "trading_days": 125},
    "medium": {"label": "中期1~2年",  "months_range": (12, 24), "trading_days": 500},
    "long":   {"label": "长期3~5年",  "months_range": (36, 60), "trading_days": 1000},
}


def extract_state_vector(snapshot: Optional[Dict[str, Any]]) -> Optional[np.ndarray]:
    """
    从市场快照中提取 5 维当下状态向量:
    x_T_now = [ERP分位, Bias20均线乖离, Mom60动量, EWMA波动率, DR007利差]
    """
    if not snapshot:
        return None
    erp = float(snapshot.get("erp_percentile", snapshot.get("erp_pct", 50.0)))
    bias20 = float(snapshot.get("bias_20", snapshot.get("bias20", 0.0)))
    mom60 = float(snapshot.get("mom60_300", snapshot.get("mom_60", snapshot.get("mom60", 0.0))))
    vol = float(snapshot.get("ewma_vol", snapshot.get("volatility", snapshot.get("ann_vol", 0.15))))
    dr007 = float(snapshot.get("dr007_spread_bp", snapshot.get("dr007_spread", snapshot.get("dr007", 0.0))))
    return np.array([erp, bias20, mom60, vol, dr007], dtype=np.float64)


def compute_historical_feature_matrix(
    nav_series: pd.Series,
    holding_days: int,
) -> np.ndarray:
    """
    对日频净值序列计算每个滚动窗口起点 t (0 <= t < n - holding_days) 处的 5 维历史特征向量:
    [ERP分位(或逆价格分位代理), Bias20均线乖离(%), Mom60动量(%), EWMA波动率, DR007利差(或流动性代理)]
    全程 NumPy 向量化，零 Python 显式循环。
    """
    nav = np.asarray(nav_series, dtype=np.float64)
    n = len(nav)
    M = n - holding_days
    if M <= 0:
        return np.empty((0, 5), dtype=np.float64)

    s_nav = pd.Series(nav)

    # 1. Bias20 (%) at each t: (nav[t] / MA20[t] - 1.0) * 100
    ma20 = s_nav.rolling(20, min_periods=1).mean().values[:M]
    nav_head = nav[:M]
    bias20 = np.where(ma20 > 0, (nav_head / ma20 - 1.0) * 100.0, 0.0)

    # 2. Mom60 (%) at each t: (nav[t] / nav[max(0, t-60)] - 1.0) * 100
    base_idx = np.maximum(0, np.arange(M) - 60)
    mom60 = np.where(nav[base_idx] > 0, (nav_head / nav[base_idx] - 1.0) * 100.0, 0.0)

    # 3. EWMA 波动率 (年化)
    ret = np.zeros(n, dtype=np.float64)
    ret[1:] = nav[1:] / np.maximum(nav[:-1], 1e-8) - 1.0
    s_ret = pd.Series(ret)
    ewma_vol = (s_ret.ewm(span=20, min_periods=1).std().bfill().fillna(0.01).values * np.sqrt(250.0))[:M]

    # 4. ERP 分位代理 (0~100)
    # 价格处于 250 天低位 -> ERP 极高 (80~90+); 处于高位 -> ERP 极低 (10~20)
    roll_min = s_nav.rolling(250, min_periods=1).min().values[:M]
    roll_max = s_nav.rolling(250, min_periods=1).max().values[:M]
    spread = np.maximum(roll_max - roll_min, 1e-6)
    norm_p = (nav_head - roll_min) / spread
    erp_proxy = np.clip((1.0 - norm_p) * 80.0 + 10.0, 5.0, 95.0)

    # 5. DR007 利差代理 (bp)
    dr007_proxy = np.clip(bias20 * 2.0, -50.0, 50.0)

    features = np.column_stack([erp_proxy, bias20, mom60, ewma_vol, dr007_proxy])
    return features


def compute_kernel_weights(
    historical_features: np.ndarray,
    target_state: np.ndarray,
    h_bandwidth: float = 1.2,
) -> np.ndarray:
    """
    计算历史状态向量与当下状态 target_state 的标准化马氏/欧氏距离 d_t，
    生成高斯同温层核权重 kappa_t:
        kappa_t = exp(-d_t^2 / (2 * h^2)) / sum(exp(-d_j^2 / (2 * h^2)))
    """
    M = len(historical_features)
    if M == 0:
        return np.array([], dtype=np.float64)

    mean_vec = np.nanmean(historical_features, axis=0)
    std_vec = np.nanstd(historical_features, axis=0)
    std_vec = np.where(std_vec < 1e-6, 1.0, std_vec)

    Z = (historical_features - mean_vec) / std_vec
    z_target = (target_state - mean_vec) / std_vec

    d2 = np.sum((Z - z_target) ** 2, axis=1)
    h = h_bandwidth if h_bandwidth > 0 else 1.2
    d2_shift = d2 - np.min(d2)  # 数值稳定性保护
    exp_args = -d2_shift / (2.0 * (h ** 2))
    raw_weights = np.exp(exp_args)
    weights_sum = np.sum(raw_weights)
    if weights_sum <= 0 or not np.isfinite(weights_sum):
        return np.full(M, 1.0 / M, dtype=np.float64)
    return raw_weights / weights_sum


# ══════════════════════════════════════════════════════════════════
#  核心引擎
# ══════════════════════════════════════════════════════════════════

class WinRateEngine:
    """多维度胜率计算引擎"""

    extract_state_vector = staticmethod(extract_state_vector)
    compute_historical_feature_matrix = staticmethod(compute_historical_feature_matrix)
    compute_kernel_weights = staticmethod(compute_kernel_weights)

    # ─── 辅助：摩擦成本调整后的收益率 ─────────────────────────

    @staticmethod
    def compute_friction_adjusted_return(
        buy_nav: float,
        sell_nav: float,
        holding_days: int,
        fund_type: str = "A",
    ) -> float:
        """
        计算扣除真实摩擦成本后的实际总收益率（非年化）。
        A 类：扣申购费 + 阶梯赎回费
        C 类：扣年化销售服务费 + 阶梯赎回费
        """
        if buy_nav <= 0:
            return 0.0

        # 申购费
        purchase_fee = A_PURCHASE_FEE if fund_type == "A" else C_PURCHASE_FEE
        # 实际买入净值（扣申购费后能买到的份额更少）
        effective_buy_cost = buy_nav * (1.0 + purchase_fee)

        # 赎回费
        redeem_fee_rate = _get_redemption_fee(holding_days, fund_type)
        effective_sell_value = sell_nav * (1.0 - redeem_fee_rate)

        # C 类额外扣年化销售服务费（holding_days 是交易日，需转换为自然日）
        if fund_type == "C":
            calendar_days = holding_days / 250.0 * 365.0
            service_fee = C_ANNUAL_SERVICE_FEE * (calendar_days / 365.0)
            effective_sell_value *= (1.0 - service_fee)

        return (effective_sell_value / effective_buy_cost) - 1.0


    # ─── ① 滚动持有达标胜率（向量化 + 当下时点条件胜率）─────────

    @classmethod
    def rolling_target_winrate(
        cls,
        nav_series: pd.Series,
        holding_days: int,
        target_annual_return: float,
        include_friction: bool = True,
        fund_type: str = "A",
        market_snapshot: Optional[Dict[str, Any]] = None,
        h_bandwidth: float = 1.2,
    ) -> Dict[str, Any]:
        """
        滚动持有达标胜率（NumPy 向量化计算 + 当下时点 T_now 高斯核条件胜率）。

        Parameters
        ----------
        nav_series : pd.Series
            日频净值序列（DatetimeIndex 或 RangeIndex）
        holding_days : int
            持有交易日数
        target_annual_return : float
            目标年化收益率，如 0.08 = 8%
        include_friction : bool
            是否扣除摩擦成本
        fund_type : str
            "A" 或 "C"
        market_snapshot : Optional[Dict[str, Any]]
            当下市场状态快照，用于高斯核同温层条件胜率
        h_bandwidth : float
            高斯核带宽系数

        Returns
        -------
        Dict with conditional_win_rate, unconditional_win_rate, win_rate, stats, etc.
        """
        nav = np.asarray(nav_series, dtype=np.float64)
        n = len(nav)

        if n <= holding_days or holding_days <= 0:
            return {
                "win_rate": 0.0,
                "conditional_win_rate": 0.0,
                "unconditional_win_rate": 0.0,
                "no_loss_rate": 0.0,
                "unconditional_no_loss_rate": 0.0,
                "avg_return_annualized": 0.0,
                "unconditional_avg_return": 0.0,
                "median_return_annualized": 0.0,
                "worst_return_annualized": 0.0,
                "best_return_annualized": 0.0,
                "p10_return": 0.0,
                "p90_return": 0.0,
                "total_windows": 0,
                "winning_windows": 0,
                "kernel_weights": np.array([], dtype=np.float64),
            }

        # 向量化：买入 NAV 和卖出 NAV
        buy_navs = nav[: n - holding_days]
        sell_navs = nav[holding_days:]

        # 总收益率
        if include_friction:
            purchase_fee = A_PURCHASE_FEE if fund_type == "A" else C_PURCHASE_FEE
            redeem_fee = _get_redemption_fee(holding_days, fund_type)
            effective_buy = buy_navs * (1.0 + purchase_fee)
            effective_sell = sell_navs * (1.0 - redeem_fee)
            if fund_type == "C":
                calendar_days = holding_days / 250.0 * 365.0
                service_fee = C_ANNUAL_SERVICE_FEE * (calendar_days / 365.0)
                effective_sell = effective_sell * (1.0 - service_fee)
            total_returns = (effective_sell / effective_buy) - 1.0
        else:
            total_returns = (sell_navs / buy_navs) - 1.0

        # 年化收益率
        years = holding_days / 250.0  # 约 250 个交易日/年
        ann_returns = np.sign(total_returns + 1.0) * (
            np.abs(total_returns + 1.0) ** (1.0 / years)
        ) - 1.0

        total_windows = len(ann_returns)
        winning = int(np.sum(ann_returns >= target_annual_return))
        no_loss = int(np.sum(total_returns >= 0))
        unconditional_wr = winning / total_windows if total_windows > 0 else 0.0
        unconditional_nlr = no_loss / total_windows if total_windows > 0 else 0.0
        unconditional_avg = float(np.mean(ann_returns)) if total_windows > 0 else 0.0

        # 高斯核同温层条件胜率计算 (Conditional Win-Rate at T_now)
        state_vec = extract_state_vector(market_snapshot)
        if state_vec is not None and total_windows > 0:
            hist_feat = compute_historical_feature_matrix(nav_series, holding_days)
            kw = compute_kernel_weights(hist_feat, state_vec, h_bandwidth=h_bandwidth)
            conditional_wr = float(np.sum(kw * (ann_returns >= target_annual_return)))
            conditional_nlr = float(np.sum(kw * (total_returns >= 0.0)))
            conditional_avg = float(np.sum(kw * ann_returns))
            win_rate = conditional_wr
            no_loss_rate = conditional_nlr
            avg_return_annualized = conditional_avg
        else:
            conditional_wr = unconditional_wr
            conditional_nlr = unconditional_nlr
            kw = np.full(total_windows, 1.0 / total_windows, dtype=np.float64) if total_windows > 0 else np.array([])
            win_rate = unconditional_wr
            no_loss_rate = unconditional_nlr
            avg_return_annualized = unconditional_avg

        return {
            "win_rate": win_rate,
            "conditional_win_rate": conditional_wr,
            "unconditional_win_rate": unconditional_wr,
            "no_loss_rate": no_loss_rate,
            "unconditional_no_loss_rate": unconditional_nlr,
            "avg_return_annualized": avg_return_annualized,
            "unconditional_avg_return": unconditional_avg,
            "median_return_annualized": float(np.median(ann_returns)),
            "worst_return_annualized": float(np.min(ann_returns)),
            "best_return_annualized": float(np.max(ann_returns)),
            "p10_return": float(np.percentile(ann_returns, 10)),
            "p90_return": float(np.percentile(ann_returns, 90)),
            "total_windows": total_windows,
            "winning_windows": winning,
            "kernel_weights": kw,
        }

    # ─── ② 当下状态条件胜率快捷接口 ─────────────────────────────

    @classmethod
    def compute_fund_winrate(
        cls,
        nav_series: pd.Series,
        holding_days: int,
        target_annual_return: float,
        market_snapshot: Optional[Dict[str, Any]] = None,
        include_friction: bool = True,
        fund_type: str = "A",
        h_bandwidth: float = 1.2,
    ) -> Dict[str, Any]:
        """
        当下时点 (T_now) 核密度条件胜率核心接口。
        输出 conditional_win_rate 与 unconditional_win_rate。
        """
        return cls.rolling_target_winrate(
            nav_series=nav_series,
            holding_days=holding_days,
            target_annual_return=target_annual_return,
            include_friction=include_friction,
            fund_type=fund_type,
            market_snapshot=market_snapshot,
            h_bandwidth=h_bandwidth,
        )

    # ─── ③ Block Bootstrap Monte Carlo ────────────────────────

    @staticmethod
    def monte_carlo_simulation(
        nav_series: pd.Series,
        holding_days: int,
        target_annual_return: float,
        n_paths: int = 10000,
        block_size: int = 20,
        include_friction: bool = True,
        fund_type: str = "A",
        seed: int = 42,
    ) -> Dict[str, Any]:
        """
        Block Bootstrap Monte Carlo 模拟。

        算法：
        1. 计算日收益率 r = nav[1:] / nav[:-1] - 1
        2. 随机抽取 block_size 长的连续块拼接成 holding_days 长的路径
        3. 重复 n_paths 次
        4. 计算每条路径的年化收益（含摩擦成本）
        5. 统计达标概率和置信区间

        全程 NumPy 矩阵运算。
        """
        nav = np.asarray(nav_series, dtype=np.float64)
        n = len(nav)

        if n < block_size + 2 or holding_days <= 0:
            return {
                "prob_reach_target": 0.0,
                "prob_no_loss": 0.0,
                "ci_90": (0.0, 0.0),
                "ci_95": (0.0, 0.0),
                "mean_return": 0.0,
                "median_return": 0.0,
                "distribution_percentiles": {},
            }

        # 日收益率
        daily_returns = nav[1:] / nav[:-1] - 1.0
        n_returns = len(daily_returns)

        rng = np.random.default_rng(seed)

        # 需要多少个块才能拼满 holding_days
        n_blocks = int(np.ceil(holding_days / block_size))
        actual_path_len = n_blocks * block_size

        # 随机抽取块的起始索引 (n_paths × n_blocks)
        max_start = n_returns - block_size
        if max_start <= 0:
            max_start = 1
        block_starts = rng.integers(0, max_start, size=(n_paths, n_blocks))

        # 构建收益率路径矩阵 (n_paths × actual_path_len)
        path_returns = np.empty((n_paths, actual_path_len), dtype=np.float64)
        for b in range(n_blocks):
            starts = block_starts[:, b]
            for d in range(block_size):
                idx = np.clip(starts + d, 0, n_returns - 1)
                path_returns[:, b * block_size + d] = daily_returns[idx]

        # 截取到 holding_days
        path_returns = path_returns[:, :holding_days]

        # 累积收益 = prod(1 + r) - 1
        cum_returns = np.prod(1.0 + path_returns, axis=1) - 1.0

        # 扣除摩擦成本
        if include_friction:
            purchase_fee = A_PURCHASE_FEE if fund_type == "A" else C_PURCHASE_FEE
            redeem_fee = _get_redemption_fee(holding_days, fund_type)
            # 调整总收益率
            friction_mult = (1.0 - redeem_fee) / (1.0 + purchase_fee)
            if fund_type == "C":
                service_fee = C_ANNUAL_SERVICE_FEE * (holding_days / 365.0)
                friction_mult *= (1.0 - service_fee)
            cum_returns = (1.0 + cum_returns) * friction_mult - 1.0

        # 年化
        years = holding_days / 250.0
        ann_returns = np.sign(cum_returns + 1.0) * (
            np.abs(cum_returns + 1.0) ** (1.0 / years)
        ) - 1.0

        prob_target = float(np.mean(ann_returns >= target_annual_return))
        prob_no_loss = float(np.mean(cum_returns >= 0))

        percentiles_keys = [5, 10, 25, 50, 75, 90, 95]
        percentiles_vals = np.percentile(ann_returns, percentiles_keys)
        distribution_percentiles = {
            f"p{k}": float(v) for k, v in zip(percentiles_keys, percentiles_vals)
        }

        return {
            "prob_reach_target": prob_target,
            "prob_no_loss": prob_no_loss,
            "ci_90": (float(np.percentile(ann_returns, 5)), float(np.percentile(ann_returns, 95))),
            "ci_95": (float(np.percentile(ann_returns, 2.5)), float(np.percentile(ann_returns, 97.5))),
            "mean_return": float(np.mean(ann_returns)),
            "median_return": float(np.median(ann_returns)),
            "distribution_percentiles": distribution_percentiles,
        }

    # ─── 组合级综合胜率 ─────────────────────────────────────────

    @staticmethod
    def portfolio_composite_winrate(
        nav_matrix: pd.DataFrame,
        weights: Dict[str, float],
        holding_days: int,
        target_annual_return: float,
        include_friction: bool = True,
        fund_types: Optional[Dict[str, str]] = None,
        market_snapshot: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        组合级综合胜率。

        将 NAV 矩阵按权重加权合成组合 NAV 序列，
        然后计算三种胜率指标。

        Parameters
        ----------
        nav_matrix : pd.DataFrame
            DatetimeIndex × fund_code 的 NAV 矩阵
        weights : Dict[str, float]
            fund_code → weight（和为 1）
        holding_days : int
            持有交易日数
        target_annual_return : float
            目标年化收益率
        fund_types : Dict[str, str] or None
            fund_code → "A"/"C"，默认全 A
        """
        if fund_types is None:
            fund_types = {}

        # 筛选出权重中有效的列
        valid_codes = [c for c in weights if c in nav_matrix.columns]
        if not valid_codes:
            return {"rolling_winrate": {}, "monte_carlo": {}, "portfolio_nav": pd.Series(dtype=float)}

        # 归一化 NAV 到起点 = 1.0
        sub_matrix = nav_matrix[valid_codes].dropna()
        if sub_matrix.empty:
            return {"rolling_winrate": {}, "monte_carlo": {}, "portfolio_nav": pd.Series(dtype=float)}

        normalized = sub_matrix / sub_matrix.iloc[0]

        # 加权合成组合 NAV
        w_arr = np.array([weights.get(c, 0.0) for c in valid_codes])
        w_arr = w_arr / w_arr.sum()  # 归一化
        portfolio_nav = pd.Series(
            (normalized.values @ w_arr),
            index=sub_matrix.index,
            name="portfolio_nav",
        )

        # 组合级摩擦成本使用加权平均份额类型
        # 简化：按权重最大的份额类型计算
        dominant_type = "A"
        if fund_types:
            c_weight = sum(weights.get(c, 0) for c in valid_codes if fund_types.get(c, "A") == "C")
            if c_weight > 0.5:
                dominant_type = "C"

        rolling = WinRateEngine.rolling_target_winrate(
            portfolio_nav, holding_days, target_annual_return,
            include_friction=include_friction, fund_type=dominant_type,
            market_snapshot=market_snapshot,
        )

        mc = WinRateEngine.monte_carlo_simulation(
            portfolio_nav, holding_days, target_annual_return,
            include_friction=include_friction, fund_type=dominant_type,
        )

        # 各成分基金的单独胜率
        component_winrates = {}
        for code in valid_codes:
            ft = fund_types.get(code, "A")
            component_winrates[code] = WinRateEngine.rolling_target_winrate(
                sub_matrix[code], holding_days, target_annual_return,
                include_friction=include_friction, fund_type=ft,
                market_snapshot=market_snapshot,
            )

        return {
            "rolling_winrate": rolling,
            "monte_carlo": mc,
            "portfolio_nav": portfolio_nav,
            "component_winrates": component_winrates,
        }

    # ─── 快速筛选评分（高性能，不含 MC）─────────────────────────

    @staticmethod
    def quick_screening_score(
        nav_series: pd.Series,
        holding_days: int,
        target_annual_return: float,
    ) -> float:
        """
        快速筛选评分：仅计算简单滚动胜率，不含摩擦成本和 MC。
        用于 3000+ 只基金的初筛排名。
        返回达标胜率 [0, 1]。
        """
        nav = np.asarray(nav_series, dtype=np.float64)
        n = len(nav)
        if n <= holding_days or holding_days <= 0:
            return 0.0

        buy = nav[: n - holding_days]
        sell = nav[holding_days:]
        total_ret = sell / buy - 1.0
        years = holding_days / 250.0
        ann_ret = np.sign(total_ret + 1.0) * (np.abs(total_ret + 1.0) ** (1.0 / years)) - 1.0
        return float(np.mean(ann_ret >= target_annual_return))

    # ─── 批量快速评分 ──────────────────────────────────────────

    @staticmethod
    def batch_quick_scores(
        nav_matrix: pd.DataFrame,
        holding_days: int,
        target_annual_return: float,
        progress_callback: Optional[Callable] = None,
    ) -> Dict[str, float]:
        """
        批量快速筛选评分。

        Parameters
        ----------
        nav_matrix : pd.DataFrame
            DatetimeIndex × fund_code
        """
        scores = {}
        total = len(nav_matrix.columns)
        for i, col in enumerate(nav_matrix.columns):
            series = nav_matrix[col].dropna()
            if len(series) > holding_days:
                scores[col] = WinRateEngine.quick_screening_score(
                    series, holding_days, target_annual_return
                )
            else:
                scores[col] = 0.0
            if progress_callback and (i + 1) % 50 == 0:
                progress_callback(i + 1, total, f"胜率初筛: {i+1}/{total}")
        return scores

    # ─── 多持有期综合胜率表 ────────────────────────────────────

    @classmethod
    def multi_horizon_winrate_table(
        cls,
        nav_series: pd.Series,
        target_annual_return: float,
        include_friction: bool = True,
        fund_type: str = "A",
        market_snapshot: Optional[Dict[str, Any]] = None,
        h_bandwidth: float = 1.2,
    ) -> Dict[str, Dict[str, Any]]:
        """
        一次性计算三个持有期（短期/中期/长期）的胜率。
        支持传入 market_snapshot 计算当下状态条件胜率。
        """
        result = {}
        for period_key, period_cfg in HOLDING_PERIODS.items():
            days = period_cfg["trading_days"]
            rolling = cls.rolling_target_winrate(
                nav_series, days, target_annual_return,
                include_friction=include_friction, fund_type=fund_type,
                market_snapshot=market_snapshot, h_bandwidth=h_bandwidth,
            )
            result[period_key] = {
                "label": period_cfg["label"],
                "holding_days": days,
                "win_rate": rolling["win_rate"],
                "conditional_win_rate": rolling.get("conditional_win_rate", rolling["win_rate"]),
                "unconditional_win_rate": rolling.get("unconditional_win_rate", rolling["win_rate"]),
                "no_loss_rate": rolling["no_loss_rate"],
                "avg_return": rolling["avg_return_annualized"],
                "median_return": rolling["median_return_annualized"],
                "p10_return": rolling["p10_return"],
                "p90_return": rolling["p90_return"],
            }
        return result
