"""
单元与集成测试：衍生品基差与期权波动率 (DerivativesCollector)
"""

import pytest
import pandas as pd
from src.toolkit.derivatives import DerivativesCollector, FuturesBasisRecord, OptionVolatilityRecord
from src.storage.lakehouse import LakehouseManager


def test_derivatives_futures_basis(tmp_path):
    lake = LakehouseManager(data_dir=tmp_path)
    collector = DerivativesCollector(lakehouse=lake)

    # 1. 期货基差拉取
    df_fb = collector.fetch_futures_basis()
    assert isinstance(df_fb, pd.DataFrame)
    assert not df_fb.empty
    assert "contract_code" in df_fb.columns
    assert "spot_price" in df_fb.columns
    assert "futures_price" in df_fb.columns
    assert "basis" in df_fb.columns
    assert "annualized_basis_rate_pct" in df_fb.columns
    assert "days_to_expiry" in df_fb.columns

    # 2. 套利机会计算
    opps = collector.get_arbitrage_opportunities()
    assert isinstance(opps, list)

    # 3. 校验写入湖仓与增量去重防膨胀
    df_read = lake.get_futures_basis()
    assert df_read is not None
    assert not df_read.empty
    cnt_first = len(df_read)

    # 再次触发入湖，校验合约代码级幂等去重
    lake.upsert_futures_basis(df_fb)
    df_read_again = lake.get_futures_basis()
    assert len(df_read_again) == cnt_first
    assert df_read_again["contract_code"].is_unique


def test_derivatives_option_volatility(tmp_path):
    lake = LakehouseManager(data_dir=tmp_path)
    collector = DerivativesCollector(lakehouse=lake)

    # 1. 期权 IV 拉取
    df_ov = collector.fetch_option_volatility()
    assert isinstance(df_ov, pd.DataFrame)
    assert not df_ov.empty
    assert "underlying_symbol" in df_ov.columns
    assert "iv_pct" in df_ov.columns
    assert "hv_20d_pct" in df_ov.columns
    assert "ivix_index" in df_ov.columns
    assert "market_sentiment" in df_ov.columns

    # 2. 校验写入湖仓
    df_read = lake.get_option_volatility("510050")
    assert df_read is not None
    assert not df_read.empty


def test_derivatives_sync_to_lakehouse(tmp_path):
    lake = LakehouseManager(data_dir=tmp_path)
    collector = DerivativesCollector(lakehouse=lake)

    res = collector.sync_to_lakehouse()
    assert res["futures_basis"] > 0
    assert res["option_volatility"] > 0
    assert (lake.derivatives_dir / "futures_basis.parquet").exists()
    assert (lake.derivatives_dir / "option_volatility.parquet").exists()
