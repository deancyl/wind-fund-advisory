"""
单元与集成测试：股东信用、解禁日历与高管增减持 (HolderRiskCollector)
"""

import pytest
import pandas as pd
from src.toolkit.holder_risk import HolderRiskCollector, LockupCalendarRecord, PledgeRiskRecord, HolderTradingRecord
from src.storage.lakehouse import LakehouseManager


def test_holder_risk_lockup_calendar(tmp_path):
    lake = LakehouseManager(data_dir=tmp_path)
    collector = HolderRiskCollector(lakehouse=lake)

    # 1. 解禁日历拉取
    df_lock = collector.fetch_lockup_calendar(days_ahead=45, limit=10)
    assert isinstance(df_lock, pd.DataFrame)
    assert not df_lock.empty
    assert "unlock_date" in df_lock.columns
    assert "days_to_unlock" in df_lock.columns
    assert "unlock_shares_million" in df_lock.columns
    assert "unlock_market_value_billion" in df_lock.columns
    assert "risk_level" in df_lock.columns

    # 2. 筛选高风险解禁
    df_high = collector.get_high_risk_calendar(days_ahead=45)
    assert isinstance(df_high, pd.DataFrame)

    # 3. 校验写入湖仓
    df_read = lake.get_lockup_calendar()
    assert df_read is not None
    assert not df_read.empty


def test_holder_risk_pledge_risk(tmp_path):
    lake = LakehouseManager(data_dir=tmp_path)
    collector = HolderRiskCollector(lakehouse=lake)

    # 1. 全市场质押拉取
    df_pledge = collector.fetch_pledge_risk(limit=10)
    assert isinstance(df_pledge, pd.DataFrame)
    assert not df_pledge.empty
    assert "pledge_ratio_total_pct" in df_pledge.columns
    assert "pledge_ratio_controlling_pct" in df_pledge.columns
    assert "warning_close_line_status" in df_pledge.columns

    # 2. 单只标的质押拉取
    df_single = collector.fetch_pledge_risk(symbol="600519")
    assert not df_single.empty
    assert 0.0 <= df_single.iloc[0]["pledge_ratio_total_pct"] <= 5.0
    assert df_single.iloc[0]["warning_close_line_status"] == "远离平仓线"

    # 3. 校验写入湖仓
    df_read = lake.get_pledge_risk("600519")
    assert df_read is not None
    assert not df_read.empty


def test_holder_risk_holder_trading(tmp_path):
    lake = LakehouseManager(data_dir=tmp_path)
    collector = HolderRiskCollector(lakehouse=lake)

    df_trade = collector.fetch_holder_trading(limit=10)
    assert isinstance(df_trade, pd.DataFrame)
    assert not df_trade.empty
    assert "holder_name" in df_trade.columns
    assert "trade_type" in df_trade.columns
    assert "change_shares_ten_thousand" in df_trade.columns
    assert "avg_price" in df_trade.columns

    # 校验写入湖仓
    df_read = lake.get_holder_trading()
    assert df_read is not None
    assert not df_read.empty


def test_holder_risk_sync_to_lakehouse(tmp_path):
    lake = LakehouseManager(data_dir=tmp_path)
    collector = HolderRiskCollector(lakehouse=lake)

    res = collector.sync_to_lakehouse()
    assert res["lockup_calendar"] > 0
    assert res["pledge_risk"] > 0
    assert res["holder_trading"] > 0
    assert (lake.mart_dir / "lockup_calendar.parquet").exists()
    assert (lake.mart_dir / "pledge_risk.parquet").exists()
    assert (lake.mart_dir / "holder_trading.parquet").exists()
