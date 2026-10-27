"""
湖仓存储引擎测试 (LakehouseManager)
"""

import pytest
import pandas as pd
from pathlib import Path

from src.storage.lakehouse import LakehouseManager


def test_lakehouse_upsert_and_read(tmp_path):
    mgr = LakehouseManager(data_dir=tmp_path)

    # 1. 第一批数据
    df1 = pd.DataFrame({
        "date": ["2026-01-05", "2026-01-06", "2026-01-07"],
        "yield_pct": [0.0, 1.2, 2.5],
        "fund_name": ["测试基金A"] * 3
    })
    p = mgr.upsert_fund_series("000001.OF", df1)
    assert p.exists()

    res1 = mgr.get_fund_series("000001.OF")
    assert len(res1) == 3
    assert "daily_return" in res1.columns
    assert "net_value_est" in res1.columns

    # 2. 第二批增量重叠数据 (覆盖 01-07 并新增 01-08)
    df2 = pd.DataFrame({
        "date": ["2026-01-07", "2026-01-08"],
        "yield_pct": [2.6, 3.1],  # 01-07 修正为 2.6
        "fund_name": ["测试基金A"] * 2
    })
    mgr.upsert_fund_series("000001.OF", df2)

    res2 = mgr.get_fund_series("000001.OF")
    assert len(res2) == 4
    # 验证 01-07 被平滑覆盖更新
    row_07 = res2[res2["date"] == "2026-01-07"].iloc[0]
    assert row_07["yield_pct"] == 2.6


def test_duckdb_views_and_query(tmp_path):
    mgr = LakehouseManager(data_dir=tmp_path)
    df = pd.DataFrame({
        "date": ["2026-01-05", "2026-01-06"],
        "yield_pct": [0.0, 1.5],
        "fund_name": ["测试基金B"] * 2
    })
    mgr.upsert_fund_series("000002.OF", df)

    mgr.init_duckdb_views()
    q_df = mgr.query_sql("SELECT symbol, COUNT(*) as cnt FROM v_funds GROUP BY symbol")
    assert len(q_df) == 1
    assert q_df.iloc[0]["symbol"] == "000002.OF"
    assert q_df.iloc[0]["cnt"] == 2


def test_duckdb_lock_concurrency_fallback(tmp_path):
    """测试当底层 DuckDB 文件被另一进程/连接独占锁定时，内存视图平滑降级兜底查询全量 v_funds 数据"""
    import duckdb
    mgr = LakehouseManager(data_dir=tmp_path)
    df = pd.DataFrame({
        "date": ["2026-01-05", "2026-01-06"],
        "yield_pct": [0.0, 1.5],
        "fund_name": ["测试基金C"] * 2
    })
    mgr.upsert_fund_series("000003.OF", df)

    # 模拟外部写连接独占 storage.duckdb
    ext_conn = duckdb.connect(str(mgr.db_path))
    try:
        # 在独占锁状态下发起查询，应自动触发内存视图降级
        df_res = mgr.query_sql("SELECT symbol, COUNT(*) as cnt FROM v_funds GROUP BY symbol")
        assert len(df_res) == 1
        assert df_res.iloc[0]["symbol"] == "000003.OF"
        assert df_res.iloc[0]["cnt"] == 2
    finally:
        ext_conn.close()
