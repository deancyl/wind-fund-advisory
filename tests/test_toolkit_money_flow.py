"""
单元测试：WindToolkit 行业板块主力资金流向分析器 (MoneyFlowCollector)
"""

import pytest
import pandas as pd

from src.toolkit.money_flow import MoneyFlowCollector, SectorMoneyFlowRecord
from src.storage.lakehouse import LakehouseManager


def test_money_flow_fetch_sector_flow(tmp_path):
    lake = LakehouseManager(data_dir=tmp_path)
    collector = MoneyFlowCollector(lakehouse=lake)
    df = collector.fetch_sector_money_flow(limit=10, force=True)
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert "sector_code" in df.columns
    assert "sector_name" in df.columns
    assert "main_net_inflow_billion" in df.columns
    assert "super_large_inflow_billion" in df.columns
    assert "change_pct" in df.columns

    # 验证湖仓文件
    df_read = lake.get_sector_money_flow()
    assert df_read is not None
    assert not df_read.empty


def test_money_flow_get_top_inflow(tmp_path):
    lake = LakehouseManager(data_dir=tmp_path)
    collector = MoneyFlowCollector(lakehouse=lake)
    df_top = collector.get_top_inflow_sectors(top_n=3)
    assert isinstance(df_top, pd.DataFrame)
    assert len(df_top) <= 3
    if len(df_top) >= 2:
        assert df_top.iloc[0]["main_net_inflow_billion"] >= df_top.iloc[1]["main_net_inflow_billion"]


def test_money_flow_get_top_outflow(tmp_path):
    lake = LakehouseManager(data_dir=tmp_path)
    collector = MoneyFlowCollector(lakehouse=lake)
    df_out = collector.get_top_outflow_sectors(top_n=3)
    assert isinstance(df_out, pd.DataFrame)
    assert len(df_out) <= 3
    if len(df_out) >= 2:
        assert df_out.iloc[0]["main_net_inflow_billion"] <= df_out.iloc[1]["main_net_inflow_billion"]


def test_money_flow_get_single_sector(tmp_path):
    lake = LakehouseManager(data_dir=tmp_path)
    collector = MoneyFlowCollector(lakehouse=lake)
    collector.fetch_sector_money_flow(limit=25, force=True)
    info_bank = collector.get_sector_flow("银行")
    assert info_bank is not None
    assert "银行" in info_bank["sector_name"]
    assert "main_net_inflow_billion" in info_bank

    # 验证非默认前7行业（如煤炭、汽车）亦可精准命中
    info_coal = collector.get_sector_flow("煤炭")
    assert info_coal is not None
    assert "煤炭" in info_coal["sector_name"]


def test_money_flow_sync_to_lakehouse(tmp_path):
    lake = LakehouseManager(data_dir=tmp_path)
    collector = MoneyFlowCollector(lakehouse=lake)
    n = collector.sync_to_lakehouse()
    assert n > 0
    assert (lake.mart_dir / "sector_money_flow.parquet").exists()
