"""
单元测试：WindToolkit 股票与基金 F10 财务指标、杜邦分析与分红送配 (FinancialsCollector)
"""

import pytest
import pandas as pd

from src.toolkit.financials import FinancialsCollector, FinancialMetricRecord, DividendRecord
from src.storage.lakehouse import LakehouseManager


def test_financials_fetch_stock_financials(tmp_path):
    lake = LakehouseManager(data_dir=tmp_path)
    collector = FinancialsCollector(lakehouse=lake)
    df = collector.fetch_stock_financials("600519", limit=4)
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert "total_revenue_billion" in df.columns
    assert "net_profit_billion" in df.columns
    assert "roe_pct" in df.columns
    assert "gross_margin_pct" in df.columns
    assert "eps" in df.columns
    assert len(df) <= 4

    # 验证是否写入湖仓
    df_read = lake.get_stock_financials("600519")
    assert df_read is not None
    assert not df_read.empty


def test_financials_fetch_dividends(tmp_path):
    lake = LakehouseManager(data_dir=tmp_path)
    collector = FinancialsCollector(lakehouse=lake)
    df = collector.fetch_dividends("600519", limit=5)
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert "cash_dividend_10" in df.columns
    assert "dividend_yield_pct" in df.columns
    assert "report_date" in df.columns
    assert "plan_desc" in df.columns

    # 验证是否写入湖仓
    df_read = lake.get_stock_dividends("600519")
    assert df_read is not None
    assert not df_read.empty


def test_financials_get_dupont_analysis(tmp_path):
    lake = LakehouseManager(data_dir=tmp_path)
    collector = FinancialsCollector(lakehouse=lake)
    dupont = collector.get_dupont_analysis("600519")
    assert isinstance(dupont, dict)
    assert "roe_pct" in dupont
    assert "net_margin_pct" in dupont
    assert "asset_turnover" in dupont
    assert "equity_multiplier" in dupont
    assert "dupont_formula" in dupont
    assert dupont["roe_pct"] > 0
    assert dupont["net_margin_pct"] > 0


def test_financials_sync_financials_to_lakehouse(tmp_path):
    lake = LakehouseManager(data_dir=tmp_path)
    collector = FinancialsCollector(lakehouse=lake)
    total = collector.sync_financials_to_lakehouse(["600519", "601318"])
    assert total >= 2
    assert (lake.mart_dir / "stock_financials.parquet").exists()
    assert (lake.mart_dir / "stock_dividends.parquet").exists()


def test_financials_fallback(tmp_path):
    lake = LakehouseManager(data_dir=tmp_path)
    collector = FinancialsCollector(lakehouse=lake)
    # 测试未知代码保底生成
    df_fb = collector._generate_fallback_financials("999999", limit=3)
    assert isinstance(df_fb, pd.DataFrame)
    assert len(df_fb) == 3
    assert "roe_pct" in df_fb.columns
    assert "symbol" in df_fb.columns


def test_financials_symbol_resolution():
    collector = FinancialsCollector()
    # 1. 北交所代码
    assert collector._resolve_symbol("832000.BJ") == "832000.BJ"
    assert collector._resolve_symbol("920002") == "920002.BJ"
    assert collector._resolve_symbol("430047") == "430047.BJ"
    # 2. 上交所代码
    assert collector._resolve_symbol("600519") == "600519.SH"
    assert collector._resolve_symbol("688981") == "688981.SH"
    # 3. 深交所代码
    assert collector._resolve_symbol("000858") == "000858.SZ"
    assert collector._resolve_symbol("300750") == "300750.SZ"
    # 4. API 权威 SECUCODE 优先
    assert collector._resolve_symbol("600519", "600519.SH") == "600519.SH"
    assert collector._resolve_symbol("832000", "832000.BJ") == "832000.BJ"
