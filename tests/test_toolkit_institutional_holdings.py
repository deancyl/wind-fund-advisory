"""
单元与集成测试：机构持仓穿透与聪明钱流动 (InstitutionalHoldingsCollector)
"""

import pytest
import pandas as pd
from src.toolkit.institutional_holdings import InstitutionalHoldingsCollector, NorthboundHoldingRecord, FundHeavyweightRecord
from src.storage.lakehouse import LakehouseManager


def test_inst_northbound_holdings_fetch(tmp_path):
    lake = LakehouseManager(data_dir=tmp_path)
    collector = InstitutionalHoldingsCollector(lakehouse=lake)

    # 1. 北向全景
    df_nb = collector.fetch_northbound_holdings(limit=10)
    assert isinstance(df_nb, pd.DataFrame)
    assert not df_nb.empty
    assert "holding_market_value_billion" in df_nb.columns
    assert "float_ratio_pct" in df_nb.columns
    assert "change_1d_value_million" in df_nb.columns
    assert "change_5d_value_million" in df_nb.columns

    # 2. 单只标的
    df_single = collector.fetch_northbound_holdings(symbol="600519")
    assert not df_single.empty
    assert df_single.iloc[0]["symbol"] == "600519.SH"

    # 3. TOP 资金流入
    df_top = collector.get_smart_money_inflow_top(top_n=5)
    assert len(df_top) <= 5

    # 4. 校验写入湖仓
    df_read = lake.get_northbound_holdings("600519")
    assert df_read is not None
    assert not df_read.empty


def test_inst_fund_heavyweight_stocks_fetch(tmp_path):
    lake = LakehouseManager(data_dir=tmp_path)
    collector = InstitutionalHoldingsCollector(lakehouse=lake)

    # 1. 公募重仓拉取
    df_fh = collector.fetch_fund_heavyweight_stocks(report_period="2024Q4", limit=10)
    assert isinstance(df_fh, pd.DataFrame)
    assert not df_fh.empty
    assert "fund_count" in df_fh.columns
    assert "holding_value_billion" in df_fh.columns
    assert "float_shares_ratio_pct" in df_fh.columns
    assert "crowding_degree" in df_fh.columns

    # 2. 抱团拥挤度预警
    df_warn = collector.get_institutional_crowding_warning(top_n=5)
    assert isinstance(df_warn, pd.DataFrame)

    # 3. 校验写入湖仓
    df_read = lake.get_fund_heavyweight_stocks(report_period="2024Q4")
    assert df_read is not None
    assert not df_read.empty


def test_inst_sync_to_lakehouse(tmp_path):
    lake = LakehouseManager(data_dir=tmp_path)
    collector = InstitutionalHoldingsCollector(lakehouse=lake)

    res = collector.sync_to_lakehouse()
    assert res["northbound_holdings"] > 0
    assert res["fund_heavyweight_stocks"] > 0
    assert (lake.mart_dir / "northbound_holdings.parquet").exists()
    assert (lake.mart_dir / "fund_heavyweight_stocks.parquet").exists()
