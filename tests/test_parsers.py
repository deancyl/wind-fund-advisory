"""
本地解析器回归测试
"""

import pytest
from src.parsers.calendar_parser import CalendarParser
from src.parsers.master_dict_parser import MasterDictParser
from src.parsers.cef_cache_parser import CEFCacheParser


def test_calendar_parser():
    cal = CalendarParser()
    assert cal.total_count >= 8000
    assert cal.is_trade_day("20261027")  # 今天是交易日
    assert not cal.is_trade_day("20261025")  # 周日非交易日

    trade_days = cal.get_trade_days("20261001", "20261027")
    assert len(trade_days) > 10


def test_master_dict_parser():
    parser = MasterDictParser()
    total = parser.load()
    assert total > 1000

    record = parser.get("000001.SZ")
    assert record is not None
    assert record.name == "平安银行"
    assert record.market == "SZ"

    search_res = parser.search("茅台", limit=5)
    assert len(search_res) > 0


def test_cef_cache_parser():
    parser = CEFCacheParser()
    charts = parser.extract_fund_yield_charts()
    assert isinstance(charts, dict)
    assert len(charts) > 0
    # 任意验证一个基金 DataFrame
    first_code = list(charts.keys())[0]
    df = charts[first_code]
    assert "yield_pct" in df.columns
    assert "date" in df.columns
    assert len(df) > 5
