"""
投资策略多维胜率分析器测试 (WinRateAnalyzer)
"""

import pytest
import pandas as pd
import numpy as np

from src.analysis.winrate_analyzer import WinRateAnalyzer
from src.storage.lakehouse import LakehouseManager


def test_winrate_analyzer(tmp_path):
    mgr = LakehouseManager(data_dir=tmp_path)

    # 构造 100 个交易日平稳上升净值
    dates = pd.date_range("2026-01-01", periods=100, freq="B").strftime("%Y-%m-%d").tolist()
    np.random.seed(123)
    daily_gains = np.random.normal(0.002, 0.005, 100)
    cum_yield = (np.cumprod(1.0 + daily_gains) - 1.0) * 100.0

    df = pd.DataFrame({
        "date": dates,
        "yield_pct": cum_yield,
        "fund_name": "成长稳赢A"
    })
    mgr.upsert_fund_series("999999.OF", df)

    analyzer = WinRateAnalyzer(lakehouse=mgr)
    res = analyzer.analyze("999999.OF", df)

    assert res is not None
    assert res.symbol == "999999.OF"
    assert res.fund_name == "成长稳赢A"
    assert res.overall_daily_win_rate > 50.0
    assert len(res.holding_win_rates) > 0

    # 验证 mart/strategy_winrate.parquet 成功生成
    mart_file = mgr.mart_dir / "strategy_winrate.parquet"
    assert mart_file.exists()
