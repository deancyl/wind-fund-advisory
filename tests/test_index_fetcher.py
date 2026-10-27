"""
指数时序拉取与 Wind Speed 实时行情流解析器单元测试
"""

from pathlib import Path
import pytest
import pandas as pd

from src.parsers.speed_log_parser import WindSpeedLogParser, SpeedQuoteSnapshot
from src.parsers.index_fetcher import IndexDataFetcher, IndexPullSummary
from src.storage.lakehouse import LakehouseManager


def test_speed_log_parser():
    parser = WindSpeedLogParser()
    latest_log = parser.find_latest_speed_log()
    if not latest_log or not latest_log.exists():
        pytest.skip("未在环境中检测到 Wind SpeedData 日志")

    snapshot = parser.get_latest_snapshot("000001.SH")
    assert snapshot is not None
    assert snapshot.symbol == "000001.SH"
    assert snapshot.latest > 0
    assert snapshot.pre_close > 0
    assert isinstance(snapshot.amount, float)
    assert snapshot.date.startswith("202")


def test_index_fetcher_symbol_normalization():
    assert IndexDataFetcher.normalize_symbol("000001") == "000001.SH"
    assert IndexDataFetcher.normalize_symbol("000001.sh") == "000001.SH"
    assert IndexDataFetcher.normalize_symbol("sh000001") == "000001.SH"
    assert IndexDataFetcher.normalize_symbol("399001") == "399001.SZ"
    assert IndexDataFetcher.normalize_symbol("000300.SH") == "000300.SH"
    assert IndexDataFetcher.normalize_symbol("899050.bj") == "899050.BJ"

    assert IndexDataFetcher.to_akshare_symbol("000001.SH") == "sh000001"
    assert IndexDataFetcher.to_akshare_symbol("399001.SZ") == "sz399001"


def test_index_data_fetcher_sync():
    lakehouse = LakehouseManager()
    fetcher = IndexDataFetcher(lakehouse)

    summary = fetcher.pull_and_sync_index("000001.SH")
    assert isinstance(summary, IndexPullSummary)
    assert summary.symbol == "000001.SH"
    assert summary.total_bars >= 8000
    assert summary.all_time_high > 6000.0  # 历史高点 6124
    assert summary.latest_close > 2000.0

    # 验证本地 Parquet 文件存在且有效
    p_path = Path(summary.parquet_path)
    assert p_path.exists()
    df = pd.read_parquet(p_path)
    assert "date" in df.columns
    assert "close" in df.columns
    assert "daily_return" in df.columns
    assert "yield_pct" in df.columns

    # 验证 DuckDB 视图可查
    query_df = lakehouse.query_sql("SELECT count(*) as cnt FROM v_indices WHERE index_code='000001.SH'")
    assert int(query_df["cnt"].iloc[0]) >= 8000
