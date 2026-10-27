"""
全球宏观资产采集、跨市场联动分析与温度计外生因子单元测试
"""

from pathlib import Path
import pytest
import pandas as pd
import numpy as np

from src.storage.lakehouse import LakehouseManager
from src.parsers.global_market_collector import GlobalMarketCollector
from src.analysis.global_linkage_analyzer import GlobalLinkageAnalyzer, GlobalLinkageMetrics
from src.analysis.market_temperature import MarketTemperatureAnalyzer, MarketTemperatureReport


def test_global_collector_paths():
    lakehouse = LakehouseManager()
    collector = GlobalMarketCollector(lakehouse)
    assert collector.indices_path.name == "global_indices.parquet"
    assert collector.fx_path.name == "fx_rates.parquet"
    assert collector.commodities_path.name == "commodities.parquet"


def test_global_linkage_analyzer_mock(tmp_path):
    lakehouse = LakehouseManager(data_dir=tmp_path)
    lakehouse.global_dir.mkdir(parents=True, exist_ok=True)
    lakehouse.macro_dir.mkdir(parents=True, exist_ok=True)
    lakehouse.mart_dir.mkdir(parents=True, exist_ok=True)
    lakehouse.indices_dir.mkdir(parents=True, exist_ok=True)

    dates = pd.date_range("2024-01-01", "2026-10-26", freq="B").strftime("%Y-%m-%d").tolist()
    n = len(dates)

    # 1. 模拟汇率数据
    fx_df = pd.DataFrame({
        "date": dates,
        "usd_cny": [6.80 + i * 0.001 for i in range(n)],
        "usd_cnh": [6.81 + i * 0.001 for i in range(n)],
        "cnh_cny_spread": [0.010] * n,
        "dxy_close": [102.5] * n
    })
    fx_df.to_parquet(lakehouse.global_dir / "fx_rates.parquet", index=False)

    # 2. 模拟中美利差数据
    rate_df = pd.DataFrame({
        "date": dates,
        "cn_yield_10y": [2.15] * n,
        "us_yield_10y": [4.05] * n,
        "cn_us_spread_10y": [-1.90] * n
    })
    rate_df.to_parquet(lakehouse.macro_dir / "bond_zh_us_rate.parquet", index=False)

    # 3. 模拟大宗商品数据
    comm_df = pd.DataFrame({
        "date": dates,
        "commodity_code": ["GC"] * n,
        "commodity_name": ["COMEX黄金"] * n,
        "open": [2500.0] * n,
        "high": [2550.0] * n,
        "low": [2490.0] * n,
        "close": [2500.0 + i * 0.2 for i in range(n)],
        "volume": [10000.0] * n,
        "daily_return": [0.05] * n
    })
    comm_df.to_parquet(lakehouse.global_dir / "commodities.parquet", index=False)

    # 4. 模拟本土基准指数 (沪深300)
    hs300_df = pd.DataFrame({
        "date": dates,
        "index_code": ["000300.SH"] * n,
        "open": [3800.0] * n,
        "high": [3850.0] * n,
        "low": [3790.0] * n,
        "close": [3800.0 + i * 0.3 for i in range(n)],
        "volume": [5000000.0] * n,
        "daily_return": [0.08] * n
    })
    lakehouse.upsert_index_series("000300.SH", hs300_df)

    analyzer = GlobalLinkageAnalyzer(lakehouse)
    metrics = analyzer.analyze()

    assert metrics is not None
    assert isinstance(metrics, GlobalLinkageMetrics)
    assert metrics.usd_cny_latest > 0
    assert metrics.usd_cnh_latest > 0
    assert -10.0 <= metrics.fx_pressure_factor <= 10.0
    assert -10.0 <= metrics.us_yield_spread_factor <= 10.0
    assert -10.0 <= metrics.risk_sentiment_factor <= 10.0
    assert -15.0 <= metrics.total_external_adjustment <= 15.0
    assert len(metrics.macro_regime_desc) > 0


def test_market_temperature_with_global_factors(tmp_path):
    lakehouse = LakehouseManager(data_dir=tmp_path)
    lakehouse.mart_dir.mkdir(parents=True, exist_ok=True)
    lakehouse.macro_dir.mkdir(parents=True, exist_ok=True)
    lakehouse.global_dir.mkdir(parents=True, exist_ok=True)
    lakehouse.indices_dir.mkdir(parents=True, exist_ok=True)

    dates = pd.date_range("2024-01-01", "2026-10-26", freq="B").strftime("%Y-%m-%d").tolist()
    n = len(dates)

    # 沪深300估值
    val_df = pd.DataFrame({
        "date": dates,
        "close": [3900.0] * n,
        "pe_ttm": [12.0] * n,
        "pe_median": [18.0] * n,
        "pb": [1.3] * n,
        "pb_median": [2.0] * n,
        "index_code": ["000300.SH"] * n,
        "index_name": ["沪深300"] * n
    })
    val_df.to_parquet(lakehouse.mart_dir / "index_valuations.parquet", index=False)

    # 国债利率
    rate_df = pd.DataFrame({
        "date": dates,
        "cn_yield_10y": [2.15] * n,
        "us_yield_10y": [4.15] * n,
        "cn_us_spread_10y": [-2.00] * n
    })
    rate_df.to_parquet(lakehouse.macro_dir / "bond_zh_us_rate.parquet", index=False)

    # 外汇
    fx_df = pd.DataFrame({
        "date": dates,
        "usd_cny": [7.10] * n,
        "usd_cnh": [7.12] * n,
        "cnh_cny_spread": [0.020] * n,
        "dxy_close": [103.5] * n
    })
    fx_df.to_parquet(lakehouse.global_dir / "fx_rates.parquet", index=False)

    # 测算温度计
    analyzer = MarketTemperatureAnalyzer(lakehouse)
    report = analyzer.evaluate()

    assert report is not None
    assert isinstance(report, MarketTemperatureReport)
    assert report.base_valuation_score >= 0
    assert 0 <= report.market_temperature_score <= 100
    # 资产配比总和应为 100%
    assert report.suggested_equity_ratio + report.suggested_bond_ratio + report.suggested_gold_ratio == 100
    assert len(report.global_linkage_summary) > 0


def test_duckdb_views_global(tmp_path):
    lakehouse = LakehouseManager(data_dir=tmp_path)
    lakehouse.global_dir.mkdir(parents=True, exist_ok=True)
    lakehouse.mart_dir.mkdir(parents=True, exist_ok=True)

    # 写入假数据验证视图
    dates = ["2026-10-25", "2026-10-26"]
    df_idx = pd.DataFrame({"date": dates, "index_code": ["SPX", "SPX"], "close": [5800.0, 5820.0]})
    df_idx.to_parquet(lakehouse.global_dir / "global_indices.parquet", index=False)

    df_fx = pd.DataFrame({"date": dates, "usd_cny": [7.10, 7.11], "cnh_cny_spread": [0.01, 0.01]})
    df_fx.to_parquet(lakehouse.global_dir / "fx_rates.parquet", index=False)

    df_comm = pd.DataFrame({"date": dates, "commodity_code": ["GC", "GC"], "close": [2700.0, 2710.0]})
    df_comm.to_parquet(lakehouse.global_dir / "commodities.parquet", index=False)

    lakehouse.init_duckdb_views()

    res_idx = lakehouse.query_sql("SELECT count(*) as cnt FROM v_global_indices")
    assert res_idx["cnt"].iloc[0] == 2

    res_fx = lakehouse.query_sql("SELECT avg(usd_cny) as avg_fx FROM v_global_fx")
    assert abs(res_fx["avg_fx"].iloc[0] - 7.105) < 1e-4

    res_comm = lakehouse.query_sql("SELECT max(close) as max_gold FROM v_global_commodities WHERE commodity_code='GC'")
    assert res_comm["max_gold"].iloc[0] == 2710.0
