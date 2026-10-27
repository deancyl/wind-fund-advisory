"""
宏观经济、利率、两融资金与大盘温度计单元测试
"""

from pathlib import Path
import pytest
import pandas as pd

from src.parsers.market_data_collector import MarketDataCollector
from src.analysis.market_temperature import MarketTemperatureAnalyzer, MarketTemperatureReport
from src.storage.lakehouse import LakehouseManager


def test_market_collector_paths():
    lakehouse = LakehouseManager()
    collector = MarketDataCollector(lakehouse)
    assert collector.rates_path.name == "bond_zh_us_rate.parquet"
    assert collector.margin_path.name == "margin_trading.parquet"
    assert collector.m2_path.name == "money_supply.parquet"
    assert collector.pmi_path.name == "pmi.parquet"
    assert collector.valuation_path.name == "index_valuations.parquet"


def test_market_temperature_evaluate_mock(tmp_path):
    lakehouse = LakehouseManager(data_dir=tmp_path)
    lakehouse.mart_dir.mkdir(parents=True, exist_ok=True)
    lakehouse.macro_dir.mkdir(parents=True, exist_ok=True)

    # 构造模拟沪深300估值数据
    val_dates = pd.date_range("2024-01-01", "2026-10-26", freq="B").strftime("%Y-%m-%d").tolist()
    val_df = pd.DataFrame({
        "date": val_dates,
        "close": [3800.0 + i * 0.5 for i in range(len(val_dates))],
        "pe_ttm": [11.5 + (i % 20) * 0.1 for i in range(len(val_dates))],
        "pe_median": [18.0] * len(val_dates),
        "pb": [1.3 + (i % 10) * 0.02 for i in range(len(val_dates))],
        "pb_median": [2.1] * len(val_dates),
        "index_code": ["000300.SH"] * len(val_dates),
        "index_name": ["沪深300"] * len(val_dates)
    })
    val_df.to_parquet(lakehouse.mart_dir / "index_valuations.parquet", index=False)

    # 构造模拟国债数据
    rate_df = pd.DataFrame({
        "date": val_dates,
        "cn_yield_10y": [2.20] * len(val_dates),
        "us_yield_10y": [4.10] * len(val_dates),
        "cn_us_spread_10y": [-1.90] * len(val_dates)
    })
    rate_df.to_parquet(lakehouse.macro_dir / "bond_zh_us_rate.parquet", index=False)

    analyzer = MarketTemperatureAnalyzer(lakehouse)
    report = analyzer.evaluate()

    assert report is not None
    assert isinstance(report, MarketTemperatureReport)
    assert report.hs300_close > 0
    assert report.hs300_pe > 0
    assert report.cn_10y_treasury_yield == 2.20
    assert report.erp_value > 0
    assert 0 <= report.market_temperature_score <= 100
    assert report.suggested_equity_ratio + report.suggested_bond_ratio + report.suggested_gold_ratio == 100
