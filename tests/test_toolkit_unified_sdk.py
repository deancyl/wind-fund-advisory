"""
单元测试：WindToolkit 统一 Python SDK 入口集成测试
"""

import pytest
import pandas as pd

from src.toolkit import WindToolkit
from src.storage.lakehouse import LakehouseManager


def test_toolkit_sdk_instantiation():
    wk = WindToolkit()
    assert wk.watchlist is not None
    assert wk.financials is not None
    assert wk.money_flow is not None
    assert wk.bonds is not None
    assert wk.etf is not None
    assert wk.lakehouse is not None


def test_toolkit_sdk_get_terminal_status():
    wk = WindToolkit()
    status = wk.get_terminal_status()
    assert isinstance(status, dict)
    assert "wfc_root" in status
    assert "user" in status
    assert "company" in status


def test_toolkit_sdk_sync_all(tmp_path):
    lake = LakehouseManager(data_dir=tmp_path)
    wk = WindToolkit(lakehouse=lake)
    res = wk.sync_all(force=True)
    assert isinstance(res, dict)
    assert "user_watchlist" in res
    assert "sector_money_flow" in res
    assert "chinabond_yield_curve" in res
    assert "etf_flows" in res


def test_toolkit_sdk_query_duckdb(tmp_path):
    lake = LakehouseManager(data_dir=tmp_path)
    wk = WindToolkit(lakehouse=lake)
    wk.sync_all(force=True)

    # 验证 DuckDB SQL 查询各个新视图
    df_wl = wk.query("SELECT * FROM v_user_watchlist")
    assert isinstance(df_wl, pd.DataFrame)

    df_flow = wk.query("SELECT * FROM v_sector_money_flow")
    assert isinstance(df_flow, pd.DataFrame)

    df_curve = wk.query("SELECT * FROM v_chinabond_yield_curve")
    assert isinstance(df_curve, pd.DataFrame)

    df_etf = wk.query("SELECT * FROM v_etf_flows")
    assert isinstance(df_etf, pd.DataFrame)
