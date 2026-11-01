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


# ══════════════════════════════════════════════════════════════════
#  核心引擎
# ══════════════════════════════════════════════════════════════════

class WinRateEngine:
    """多维度胜率计算引擎"""

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

    # ─── ① 滚动持有达标胜率（向量化）──────────────────────────

    @staticmethod
    def rolling_target_winrate(
        nav_series: pd.Series,
        holding_days: int,
        target_annual_return: float,
        include_friction: bool = True,
        fund_type: str = "A",
    ) -> Dict[str, Any]:
        """
        滚动持有达标胜率（NumPy 向量化计算）。

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

        Returns
        -------
        Dict with win_rate, no_loss_rate, stats, etc.
        """
        nav = np.asarray(nav_series, dtype=np.float64)
        n = len(nav)

        if n <= holding_days or holding_days <= 0:
            return {
                "win_rate": 0.0,
                "no_loss_rate": 0.0,
                "avg_return_annualized": 0.0,
                "median_return_annualized": 0.0,
                "worst_return_annualized": 0.0,
                "best_return_annualized": 0.0,
                "p10_return": 0.0,
                "p90_return": 0.0,
                "total_windows": 0,
                "winning_windows": 0,
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
        # 避免负数底数的幂运算问题
        ann_returns = np.sign(total_returns + 1.0) * (
            np.abs(total_returns + 1.0) ** (1.0 / years)
        ) - 1.0

        total_windows = len(ann_returns)
        winning = int(np.sum(ann_returns >= target_annual_return))
        no_loss = int(np.sum(total_returns >= 0))

        return {
            "win_rate": winning / total_windows if total_windows > 0 else 0.0,
            "no_loss_rate": no_loss / total_windows if total_windows > 0 else 0.0,
            "avg_return_annualized": float(np.mean(ann_returns)),
            "median_return_annualized": float(np.median(ann_returns)),
            "worst_return_annualized": float(np.min(ann_returns)),
            "best_return_annualized": float(np.max(ann_returns)),
            "p10_return": float(np.percentile(ann_returns, 10)),
            "p90_return": float(np.percentile(ann_returns, 90)),
            "total_windows": total_windows,
            "winning_windows": winning,
        }

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

    @staticmethod
    def multi_horizon_winrate_table(
        nav_series: pd.Series,
        target_annual_return: float,
        include_friction: bool = True,
        fund_type: str = "A",
    ) -> Dict[str, Dict[str, Any]]:
        """
        一次性计算三个持有期（短期/中期/长期）的胜率。
        用于用户拉滑块时实时显示"该目标在三个持有期下的历史胜率参考值"。
        """
        result = {}
        for period_key, period_cfg in HOLDING_PERIODS.items():
            days = period_cfg["trading_days"]
            rolling = WinRateEngine.rolling_target_winrate(
                nav_series, days, target_annual_return,
                include_friction=include_friction, fund_type=fund_type,
            )
            result[period_key] = {
                "label": period_cfg["label"],
                "holding_days": days,
                "win_rate": rolling["win_rate"],
                "no_loss_rate": rolling["no_loss_rate"],
                "avg_return": rolling["avg_return_annualized"],
                "median_return": rolling["median_return_annualized"],
                "p10_return": rolling["p10_return"],
                "p90_return": rolling["p90_return"],
            }
        return result
