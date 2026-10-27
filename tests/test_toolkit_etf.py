"""
单元测试：WindToolkit ETF 份额与资金流动追踪器 (ETFFlowCollector)
"""

import pytest
import pandas as pd

from src.toolkit.etf import ETFFlowCollector, ETFFlowRecord
from src.storage.lakehouse import LakehouseManager


def test_etf_fetch_flows(tmp_path):
    lake = LakehouseManager(data_dir=tmp_path)
    collector = ETFFlowCollector(lakehouse=lake)
    df = collector.fetch_etf_flows(force=True)
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert "etf_code" in df.columns
    assert "etf_name" in df.columns
    assert "shares_billion" in df.columns
    assert "nav" in df.columns
    assert "est_net_inflow_billion" in df.columns
    assert "category" in df.columns

    # 验证湖仓保存
    df_read = lake.get_etf_flows()
    assert df_read is not None
    assert not df_read.empty


def test_etf_get_top_inflow(tmp_path):
    lake = LakehouseManager(data_dir=tmp_path)
    collector = ETFFlowCollector(lakehouse=lake)
    df_top = collector.get_top_inflow_etfs(top_n=5)
    assert isinstance(df_top, pd.DataFrame)
    assert len(df_top) <= 5
    if len(df_top) >= 2:
        assert df_top.iloc[0]["est_net_inflow_billion"] >= df_top.iloc[1]["est_net_inflow_billion"]


def test_etf_get_top_outflow(tmp_path):
    lake = LakehouseManager(data_dir=tmp_path)
    collector = ETFFlowCollector(lakehouse=lake)
    df_out = collector.get_top_outflow_etfs(top_n=5)
    assert isinstance(df_top := df_out, pd.DataFrame)
    assert len(df_top) <= 5
    if len(df_top) >= 2:
        assert df_top.iloc[0]["est_net_inflow_billion"] <= df_top.iloc[1]["est_net_inflow_billion"]


def test_etf_category_summary(tmp_path):
    lake = LakehouseManager(data_dir=tmp_path)
    collector = ETFFlowCollector(lakehouse=lake)
    df_cat = collector.get_category_flow_summary()
    assert isinstance(df_cat, pd.DataFrame)
    assert not df_cat.empty
    assert "category" in df_cat.columns
    assert "etf_count" in df_cat.columns
    assert "total_aum_billion" in df_cat.columns


def test_etf_sync_to_lakehouse(tmp_path):
    lake = LakehouseManager(data_dir=tmp_path)
    collector = ETFFlowCollector(lakehouse=lake)
    n = collector.sync_to_lakehouse()
    assert n > 0
    assert (lake.mart_dir / "etf_flows.parquet").exists()


def test_etf_classification_edge_cases():
    collector = ETFFlowCollector()
    # 1. 固收与货币 ETF
    assert collector._classify_etf("科创债ETF南方", "511010") == "固收商品"
    assert collector._classify_etf("华宝添益", "511880") == "固收商品"
    assert collector._classify_etf("银华日利", "511990") == "固收商品"
    assert collector._classify_etf("30年国债ETF", "511090") == "固收商品"
    # 2. 宽基与大盘指数 ETF
    assert collector._classify_etf("中证100ETF", "159903") == "宽基ETF"
    assert collector._classify_etf("上证180ETF", "510180") == "宽基ETF"
    assert collector._classify_etf("华泰柏瑞沪深300ETF", "510300") == "宽基ETF"
    assert collector._classify_etf("科创50ETF", "588000") == "宽基ETF"
    assert collector._classify_etf("创业板ETF", "159915") == "宽基ETF"
    # 3. 策略与红利
    assert collector._classify_etf("红利低波ETF", "512890") == "策略红利"
    assert collector._classify_etf("央企股东回报ETF", "560070") == "策略红利"
    # 4. 跨境 QDII
    assert collector._classify_etf("纳斯达克100ETF", "513100") == "跨境QDII"
    assert collector._classify_etf("恒生科技ETF", "513130") == "跨境QDII"
    # 5. 行业主题
    assert collector._classify_etf("半导体ETF", "512480") == "行业主题"
    assert collector._classify_etf("光伏ETF", "515790") == "行业主题"
