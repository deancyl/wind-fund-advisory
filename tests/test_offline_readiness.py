"""
Wind 客户端完全退出/离线脱机场景单元测试：
验证即使没有 Wind 客户端进程运行 (wmain.exe 退出)，
静态物理文件解析、本地 Parquet 湖仓读取、DuckDB 即席查询、大盘温度计与组合回测
依然 100% 独立稳定可用。
"""

from pathlib import Path
import pytest
import pandas as pd

from src.config import WIND_CONFIG
from src.parsers.calendar_parser import CalendarParser
from src.parsers.master_dict_parser import MasterDictParser
from src.parsers.sector_parser import SectorParser
from src.storage.lakehouse import LakehouseManager
from src.analysis.market_temperature import MarketTemperatureAnalyzer
from src.analysis.portfolio_analyzer import PortfolioAnalyzer


def test_offline_calendar_and_master_dict():
    """验证不依赖 Wind 进程直接读取底层静态物理文件"""
    # 1. 交易日历
    cal = CalendarParser()
    assert cal.total_count > 8000
    assert cal.is_trade_day("2026-10-26") == True

    # 2. 代码主字典 (二进制解析)
    parser = MasterDictParser()
    assert parser.file_path.exists() == True
    results = parser.search("000300", limit=5)
    assert len(results) > 0
    assert any(r.symbol == "000300.SH" for r in results)


def test_offline_lakehouse_and_duckdb():
    """验证本地湖仓与 DuckDB 视图完全独立于 Wind 运行"""
    lakehouse = LakehouseManager()

    # 查询指数湖仓
    hs300 = lakehouse.get_index_series("000300.SH")
    assert hs300 is not None
    assert not hs300.empty
    assert "close" in hs300.columns

    # 查询公募基金交易规则与费率
    rule = lakehouse.get_fund_trading_rule("000001.OF")
    assert rule is not None
    assert rule["purchase_status"] in ["开放申购", "暂停大额申购", "暂停申购"]

    # DuckDB 即席 SQL 查询
    df_sql = lakehouse.query_sql("SELECT count(*) as total_indices FROM v_indices")
    assert df_sql["total_indices"].iloc[0] > 1000000


def test_offline_models_and_portfolio_mpt():
    """验证大盘温度计与 MPT 组合优化模型纯本地离线执行"""
    lakehouse = LakehouseManager()

    # 1. 大盘估值温度计
    mta = MarketTemperatureAnalyzer(lakehouse)
    report = mta.evaluate()
    assert report is not None
    assert 0 <= report.market_temperature_score <= 100
    assert report.suggested_equity_ratio + report.suggested_bond_ratio + report.suggested_gold_ratio == 100

    # 2. 投资组合 MPT 深度回测
    pa = PortfolioAnalyzer(lakehouse)
    res = pa.analyze_portfolio(weights_map={"000300.SH": 0.6, "000905.SH": 0.4})
    assert res is not None
    assert res.metrics.sharpe_ratio is not None
    assert res.diversification.diversification_ratio >= 1.0
