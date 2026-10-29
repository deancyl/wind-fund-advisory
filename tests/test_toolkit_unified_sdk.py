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
    assert wk.earnings_forecast is not None
    assert wk.chips_market is not None
    assert wk.holder_risk is not None
    assert wk.institutional_holdings is not None
    assert wk.derivatives is not None
    assert wk.macro_liquidity is not None
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
    assert "earnings_forecast" in res
    assert "financial_risk_screen" in res
    assert "dragon_tiger" in res
    assert "block_trading" in res
    assert "shareholder_count" in res
    assert "lockup_calendar" in res
    assert "pledge_risk" in res
    assert "holder_trading" in res
    assert "northbound_holdings" in res
    assert "fund_heavyweight_stocks" in res
    assert "futures_basis" in res
    assert "option_volatility" in res
    assert "open_market_operations" in res
    assert "interbank_rates" in res


def test_toolkit_sdk_query_duckdb(tmp_path):
    lake = LakehouseManager(data_dir=tmp_path)
    wk = WindToolkit(lakehouse=lake)
    wk.sync_all(force=True)

    # 验证 DuckDB SQL 统一查询全量视图
    views = [
        "v_user_watchlist",
        "v_sector_money_flow",
        "v_chinabond_yield_curve",
        "v_etf_flows",
        "v_earnings_forecast",
        "v_financial_risk_screen",
        "v_dragon_tiger",
        "v_block_trading",
        "v_shareholder_count",
        "v_lockup_calendar",
        "v_pledge_risk",
        "v_holder_trading",
        "v_northbound_holdings",
        "v_fund_heavyweight_stocks",
        "v_futures_basis",
        "v_option_volatility",
        "v_open_market_operations",
        "v_interbank_rates",
    ]
    for v in views:
        df_v = wk.query(f"SELECT * FROM {v} LIMIT 5")
        assert isinstance(df_v, pd.DataFrame)
