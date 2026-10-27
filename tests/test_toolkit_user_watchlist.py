"""
单元测试：WindToolkit 投顾自选标的与工作台配置探索器 (UserWatchlistParser)
"""

import pytest
import pandas as pd
from pathlib import Path

from src.toolkit.user_watchlist import UserWatchlistParser, WatchlistItem
from src.storage.lakehouse import LakehouseManager


def test_watchlist_parser_init():
    parser = UserWatchlistParser()
    assert parser.users_dir.exists()


def test_watchlist_parser_read_terminal_user():
    parser = UserWatchlistParser()
    active_dir = parser._get_active_user_dir()
    assert active_dir is not None
    assert active_dir.name.startswith("W")


def test_watchlist_get_latest_visited_symbols():
    parser = UserWatchlistParser()
    symbols = parser.get_latest_visited_symbols()
    assert isinstance(symbols, list)
    assert len(symbols) > 0
    assert any("000001" in s or "SPX" in s or "512890" in s for s in symbols)


def test_watchlist_get_smart_search_history():
    parser = UserWatchlistParser()
    history = parser.get_smart_search_history()
    assert isinstance(history, list)
    assert len(history) > 0
    assert any("symbol" in h and "name" in h for h in history)


def test_watchlist_get_hotwords():
    parser = UserWatchlistParser()
    hotwords = parser.get_hotwords()
    assert isinstance(hotwords, list)


def test_watchlist_get_workbench_tabs():
    parser = UserWatchlistParser()
    tabs = parser.get_workbench_tabs()
    assert isinstance(tabs, list)
    if tabs:
        assert "caption" in tabs[0]
        assert "command_code" in tabs[0]


def test_watchlist_get_bbq_schemes():
    parser = UserWatchlistParser()
    schemes = parser.get_bbq_schemes()
    assert isinstance(schemes, dict)
    if schemes:
        assert "DEB" in schemes or "NCD" in schemes or "Tab" in schemes


def test_watchlist_get_user_preferences():
    parser = UserWatchlistParser()
    prefs = parser.get_user_preferences()
    assert isinstance(prefs, dict)


def test_watchlist_get_marked_userlines():
    parser = UserWatchlistParser()
    marks = parser.get_marked_userlines()
    assert isinstance(marks, list)
    if marks:
        assert "symbol" in marks[0]


def test_watchlist_build_consolidated_watchlist():
    parser = UserWatchlistParser()
    df = parser.build_consolidated_watchlist()
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert "symbol" in df.columns
    assert "name" in df.columns
    assert "asset_class" in df.columns
    assert "source" in df.columns
    assert len(df) >= 5


def test_watchlist_sync_to_lakehouse(tmp_path):
    lake = LakehouseManager(data_dir=tmp_path)
    parser = UserWatchlistParser(lakehouse=lake)
    n = parser.sync_to_lakehouse()
    assert n > 0
    df_read = lake.get_user_watchlist()
    assert df_read is not None
    assert len(df_read) == n


def test_watchlist_advisor_profile():
    parser = UserWatchlistParser()
    prof = parser.get_advisor_profile()
    assert isinstance(prof, dict)
    assert "user_id" in prof
    assert "name" in prof
    assert "phone" in prof
    assert "wdid" in prof
    # 实际 Wind 终端环境存在时应解析出真实投顾姓名与 WDID
    if prof.get("name") != "本地投顾":
        assert prof["name"] == "梁可"
        assert "Coco" in prof.get("en_name", "")


def test_watchlist_investassist_and_wdd():
    parser = UserWatchlistParser()
    ia = parser.get_investassist_config()
    assert isinstance(ia, dict)
    assert "status" in ia
    wdd = parser.get_wdd_config()
    assert isinstance(wdd, dict)
    assert "status" in wdd


def test_watchlist_infer_asset_class_edge_cases():
    parser = UserWatchlistParser()
    # 1. 核心大盘指数
    assert parser._infer_asset_class("000016.SH") == "index"   # 上证50
    assert parser._infer_asset_class("000852.SH") == "index"   # 中证1000
    assert parser._infer_asset_class("000015.SH") == "index"   # 红利指数
    assert parser._infer_asset_class("399300.SZ") == "index"   # 沪深300 (深市)
    assert parser._infer_asset_class("399006.SZ") == "index"   # 创业板指
    # 2. 场内 ETF
    assert parser._infer_asset_class("510300.SH") == "etf"
    assert parser._infer_asset_class("560050.SH") == "etf"     # 56 开头 ETF
    assert parser._infer_asset_class("588000.SH") == "etf"     # 科创50 ETF
    assert parser._infer_asset_class("159915.SZ") == "etf"     # 创业板 ETF
    # 3. 债券与转债
    assert parser._infer_asset_class("010107.SH") == "bond"    # 国债
    assert parser._infer_asset_class("113050.SH") == "bond"    # 上交所转债
    assert parser._infer_asset_class("128036.SZ") == "bond"    # 深交所转债
    # 4. 北交所标的
    assert parser._infer_asset_class("832000.BJ") == "stock"
    assert parser._infer_asset_class("920002.BJ") == "stock"
    assert parser._infer_asset_class("899050.BJ") == "index"   # 北证50
    # 5. 期货与全球代码
    assert parser._infer_asset_class("IF2412.CFE") == "futures"
    assert parser._infer_asset_class("SPX.GI") == "index"
