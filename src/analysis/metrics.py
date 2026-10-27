"""
金融量化核心指标计算模块：收益率、波动率、最大回撤、夏普比率、索提诺比率、卡玛比率与 Alpha/Beta。
"""

from typing import Tuple, Union
import numpy as np
import pandas as pd


def calculate_cumulative_to_daily_returns(cum_yield_series: pd.Series) -> pd.Series:
    """
    将百分比累计收益率 (如 0%, 5.2%, -1.1%) 转换为逐日简单收益率序列。
    公式: NetValue_t = 1 + y_t / 100
          r_t = (NV_t - NV_{t-1}) / NV_{t-1}
    """
    nv = 1.0 + cum_yield_series / 100.0
    daily_returns = nv.pct_change().dropna()
    return daily_returns


def calculate_annualized_return(
    cum_yield_pct: float,
    total_days: int,
    trading_days_per_year: int = 250
) -> float:
    """
    计算年化复合收益率 (%)
    """
    if total_days <= 0:
        return 0.0
    nv_end = 1.0 + cum_yield_pct / 100.0
    if nv_end <= 0:
        return -100.0
    ann_ret = (nv_end ** (trading_days_per_year / total_days) - 1.0) * 100.0
    return round(float(ann_ret), 2)


def calculate_annualized_volatility(
    daily_returns: pd.Series,
    trading_days_per_year: int = 250
) -> float:
    """
    计算年化收益波动率 (%)
    """
    if len(daily_returns) < 2:
        return 0.0
    daily_vol = float(daily_returns.std())
    ann_vol = daily_vol * np.sqrt(trading_days_per_year) * 100.0
    return round(float(ann_vol), 2)


def calculate_max_drawdown(cum_yield_series: pd.Series) -> Tuple[float, int, int]:
    """
    计算历史最大回撤百分比 (%) 及发生的高点与低点索引位置。
    返回: (max_drawdown_pct, peak_index, trough_index)
    """
    if len(cum_yield_series) < 2:
        return 0.0, 0, 0

    nv = 1.0 + cum_yield_series / 100.0
    cum_max = nv.cummax()
    drawdowns = (nv - cum_max) / cum_max

    max_dd = float(drawdowns.min()) * 100.0  # 负数或 0
    trough_idx = int(drawdowns.argmin())
    peak_idx = int(nv.iloc[:trough_idx + 1].argmax())

    return round(abs(max_dd), 2), peak_idx, trough_idx


def calculate_sharpe_ratio(
    daily_returns: pd.Series,
    risk_free_rate_annual: float = 0.02,
    trading_days_per_year: int = 250
) -> float:
    """
    计算夏普比率 (Sharpe Ratio)
    """
    if len(daily_returns) < 2:
        return 0.0
    rf_daily = risk_free_rate_annual / trading_days_per_year
    excess_returns = daily_returns - rf_daily
    mean_excess = float(excess_returns.mean())
    std_excess = float(daily_returns.std())

    if std_excess <= 1e-8:
        return 0.0

    sharpe = (mean_excess / std_excess) * np.sqrt(trading_days_per_year)
    return round(float(sharpe), 2)


def calculate_sortino_ratio(
    daily_returns: pd.Series,
    risk_free_rate_annual: float = 0.02,
    trading_days_per_year: int = 250
) -> float:
    """
    计算索提诺比率 (Sortino Ratio，仅惩罚下行波动)
    """
    if len(daily_returns) < 2:
        return 0.0
    rf_daily = risk_free_rate_annual / trading_days_per_year
    excess_returns = daily_returns - rf_daily
    downside_returns = excess_returns[excess_returns < 0]

    if len(downside_returns) < 1:
        return 10.0  # 无下行风险

    downside_std = float(np.sqrt(np.mean(downside_returns ** 2)))
    if downside_std <= 1e-8:
        return 0.0

    sortino = (float(excess_returns.mean()) / downside_std) * np.sqrt(trading_days_per_year)
    return round(float(sortino), 2)


def calculate_calmar_ratio(
    annualized_return_pct: float,
    max_drawdown_pct: float
) -> float:
    """
    计算卡玛比率 (Calmar Ratio = 年化收益率 / 最大回撤)
    """
    if max_drawdown_pct <= 0.01:
        return 10.0
    return round(annualized_return_pct / max_drawdown_pct, 2)


def calculate_alpha_beta(
    fund_daily_returns: pd.Series,
    bench_daily_returns: pd.Series,
    risk_free_rate_annual: float = 0.02,
    trading_days_per_year: int = 250
) -> Tuple[float, float]:
    """
    通过 CAPM 模型计算基金的系统性贝塔 (Beta) 与年化阿尔法 (Alpha %)。
    """
    aligned = pd.concat([fund_daily_returns, bench_daily_returns], axis=1, join="inner").dropna()
    if len(aligned) < 20:
        return 0.0, 1.0

    f_ret = aligned.iloc[:, 0]
    b_ret = aligned.iloc[:, 1]

    cov = np.cov(f_ret, b_ret)[0][1]
    var_b = np.var(b_ret)

    beta = cov / var_b if var_b > 1e-8 else 1.0

    rf_daily = risk_free_rate_annual / trading_days_per_year
    alpha_daily = (f_ret.mean() - rf_daily) - beta * (b_ret.mean() - rf_daily)
    alpha_ann = alpha_daily * trading_days_per_year * 100.0

    return round(float(alpha_ann), 2), round(float(beta), 2)
