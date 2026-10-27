"""
量化指标单元测试
"""

import pytest
import pandas as pd
import numpy as np

from src.analysis.metrics import (
    calculate_cumulative_to_daily_returns,
    calculate_annualized_return,
    calculate_annualized_volatility,
    calculate_max_drawdown,
    calculate_sharpe_ratio,
    calculate_calmar_ratio,
    calculate_alpha_beta
)


def test_cumulative_to_daily_returns():
    cum_yield = pd.Series([0.0, 10.0, 21.0])
    daily = calculate_cumulative_to_daily_returns(cum_yield)
    assert len(daily) == 2
    assert pytest.approx(daily.iloc[0], 0.001) == 0.10
    assert pytest.approx(daily.iloc[1], 0.001) == 0.10


def test_annualized_return():
    # 250 天翻倍 (100% 收益) -> 年化收益应约为 100%
    ann_ret = calculate_annualized_return(100.0, 250, 250)
    assert pytest.approx(ann_ret, 0.1) == 100.0


def test_max_drawdown():
    # 净值走势: 100 -> 120 -> 90 -> 110 (高点 120, 最低 90, 回撤 = (90-120)/120 = -25%)
    cum_yield = pd.Series([0.0, 20.0, -10.0, 10.0])
    max_dd, peak, trough = calculate_max_drawdown(cum_yield)
    assert pytest.approx(max_dd, 0.1) == 25.0
    assert peak == 1
    assert trough == 2


def test_sharpe_and_calmar():
    daily_returns = pd.Series([0.01, 0.02, -0.005, 0.015, 0.008] * 10)
    sharpe = calculate_sharpe_ratio(daily_returns)
    assert sharpe > 0.0

    calmar = calculate_calmar_ratio(15.0, 10.0)
    assert pytest.approx(calmar, 0.01) == 1.5
