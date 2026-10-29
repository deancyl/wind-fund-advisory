"""
单元与集成测试：微观筹码面与市场资金分布 (ChipsMarketCollector)
"""

import pytest
import pandas as pd
from src.toolkit.chips_market import ChipsMarketCollector, DragonTigerRecord, BlockTradingRecord, ShareholderCountRecord
from src.storage.lakehouse import LakehouseManager


def test_chips_dragon_tiger_fetch(tmp_path):
    lake = LakehouseManager(data_dir=tmp_path)
    collector = ChipsMarketCollector(lakehouse=lake)

    # 1. 龙虎榜拉取
    df_dt = collector.fetch_dragon_tiger_daily(limit=10)
    assert isinstance(df_dt, pd.DataFrame)
    assert not df_dt.empty
    assert "symbol" in df_dt.columns
    assert "net_buy_million" in df_dt.columns
    assert "institution_net_million" in df_dt.columns
    assert "top_buy_seats" in df_dt.columns

    # 2. 机构博弈汇总统计
    summary = collector.get_institutional_dragon_tiger_summary()
    assert isinstance(summary, dict)
    assert "institution_total_buy_million" in summary
    assert "institution_sentiment" in summary
    assert "top_institutional_inflows" in summary

    # 3. 校验写入湖仓
    df_read = lake.get_dragon_tiger()
    assert df_read is not None
    assert not df_read.empty


def test_chips_block_trading_fetch(tmp_path):
    lake = LakehouseManager(data_dir=tmp_path)
    collector = ChipsMarketCollector(lakehouse=lake)

    df_bt = collector.fetch_block_trading(limit=10)
    assert isinstance(df_bt, pd.DataFrame)
    assert not df_bt.empty
    assert "deal_price" in df_bt.columns
    assert "discount_rate_pct" in df_bt.columns
    assert "buyer_branch" in df_bt.columns
    assert "deal_amount_ten_thousand" in df_bt.columns

    # 校验写入湖仓
    df_read = lake.get_block_trading()
    assert df_read is not None
    assert not df_read.empty


def test_chips_shareholder_concentration(tmp_path):
    lake = LakehouseManager(data_dir=tmp_path)
    collector = ChipsMarketCollector(lakehouse=lake)

    df_sh = collector.fetch_shareholder_concentration("600519", limit=6)
    assert isinstance(df_sh, pd.DataFrame)
    assert not df_sh.empty
    assert "holder_count" in df_sh.columns
    assert "holder_change_pct" in df_sh.columns
    assert "avg_market_value_ten_thousand" in df_sh.columns
    assert "concentration_trend" in df_sh.columns
    assert df_sh.iloc[0]["holder_count"] > 0
    assert df_sh.iloc[0]["avg_market_value_ten_thousand"] > 0

    # 校验写入湖仓
    df_read = lake.get_shareholder_count("600519")
    assert df_read is not None
    assert not df_read.empty


def test_chips_sync_to_lakehouse(tmp_path):
    lake = LakehouseManager(data_dir=tmp_path)
    collector = ChipsMarketCollector(lakehouse=lake)

    res = collector.sync_to_lakehouse()
    assert res["dragon_tiger"] > 0
    assert res["block_trading"] > 0
    assert res["shareholder_count"] > 0
    assert (lake.mart_dir / "dragon_tiger.parquet").exists()
    assert (lake.mart_dir / "block_trading.parquet").exists()
    assert (lake.mart_dir / "shareholder_count.parquet").exists()
