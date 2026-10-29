"""
单元与集成测试：宏观高频流动性与公开市场操作 (MacroLiquidityCollector)
"""

import pytest
import pandas as pd
from src.toolkit.macro_liquidity import MacroLiquidityCollector, OpenMarketOperationRecord, InterbankRateRecord
from src.storage.lakehouse import LakehouseManager


def test_macro_liquidity_omo_fetch(tmp_path):
    lake = LakehouseManager(data_dir=tmp_path)
    collector = MacroLiquidityCollector(lakehouse=lake)

    # 1. 央行 OMO 流水
    df_omo = collector.fetch_open_market_operations(days=15)
    assert isinstance(df_omo, pd.DataFrame)
    assert not df_omo.empty
    assert "repo_7d_injection_billion" in df_omo.columns
    assert "repo_7d_net_billion" in df_omo.columns
    assert "total_net_injection_billion" in df_omo.columns
    assert "liquidity_stance" in df_omo.columns

    # 2. 校验写入湖仓
    df_read = lake.get_open_market_operations()
    assert df_read is not None
    assert not df_read.empty


def test_macro_liquidity_interbank_rates(tmp_path):
    lake = LakehouseManager(data_dir=tmp_path)
    collector = MacroLiquidityCollector(lakehouse=lake)

    # 1. 银行间利率时序
    df_rate = collector.fetch_interbank_rates(days=15)
    assert isinstance(df_rate, pd.DataFrame)
    assert not df_rate.empty
    assert "dr001" in df_rate.columns
    assert "dr007" in df_rate.columns
    assert "dr007_spread_bp" in df_rate.columns
    assert "liquidity_status" in df_rate.columns

    # 2. 温度计研判
    thermo = collector.get_liquidity_thermometer()
    assert isinstance(thermo, dict)
    assert "dr007" in thermo
    assert "liquidity_status" in thermo
    assert "advisory_takeaway" in thermo

    # 3. 校验写入湖仓
    df_read = lake.get_interbank_rates()
    assert df_read is not None
    assert not df_read.empty


def test_macro_liquidity_sync_to_lakehouse(tmp_path):
    lake = LakehouseManager(data_dir=tmp_path)
    collector = MacroLiquidityCollector(lakehouse=lake)

    res = collector.sync_to_lakehouse()
    assert res["open_market_operations"] > 0
    assert res["interbank_rates"] > 0
    assert (lake.macro_dir / "open_market_operations.parquet").exists()
    assert (lake.macro_dir / "interbank_rates.parquet").exists()
