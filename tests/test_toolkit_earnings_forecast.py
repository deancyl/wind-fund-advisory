"""
单元与集成测试：业绩预告、FCF 自由现金流与财务高危排雷 (EarningsForecastCollector)
"""

import pytest
import pandas as pd
from src.toolkit.earnings_forecast import EarningsForecastCollector, EarningsForecastRecord, FinancialRiskScreenRecord
from src.storage.lakehouse import LakehouseManager


def test_earnings_forecast_fetch(tmp_path):
    lake = LakehouseManager(data_dir=tmp_path)
    collector = EarningsForecastCollector(lakehouse=lake)
    
    # 1. 全市场拉取
    df = collector.fetch_earnings_forecast(limit=10)
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert "symbol" in df.columns
    assert "forecast_type" in df.columns
    assert "profit_min_million" in df.columns
    assert "profit_max_million" in df.columns
    assert "profit_change_min_pct" in df.columns
    assert "profit_change_max_pct" in df.columns

    # 2. 单只股票精准拉取
    df_single = collector.fetch_earnings_forecast(symbol="600519", limit=5)
    assert not df_single.empty
    assert any("600519" in s for s in df_single["symbol"])

    # 3. 校验写入湖仓
    df_read = lake.get_earnings_forecast()
    assert df_read is not None
    assert not df_read.empty


def test_earnings_forecast_risk_screening(tmp_path):
    lake = LakehouseManager(data_dir=tmp_path)
    collector = EarningsForecastCollector(lakehouse=lake)

    # 1. 扫描蓝筹标的 (茅台: 安全)
    res_safe = collector.screen_financial_risks("600519")
    assert isinstance(res_safe, dict)
    assert res_safe["symbol"] == "600519.SH"
    assert res_safe["fcf_billion"] > 0
    assert res_safe["goodwill_ratio_pct"] == 0.0
    assert res_safe["risk_level"] == "Safe"

    # 2. 扫描承压标的 (万科A: 存在造血与负债预警)
    res_watch = collector.screen_financial_risks("000002")
    assert res_watch["symbol"] == "000002.SZ"
    assert res_watch["risk_level"] in ["Watch", "Danger"]

    # 3. 批量扫描
    df_batch = collector.batch_screen_risks(["600519", "300750", "000002"])
    assert len(df_batch) == 3
    assert "risk_level" in df_batch.columns

    # 4. 校验写入湖仓
    df_lake = lake.get_financial_risk_screen("600519")
    assert df_lake is not None
    assert not df_lake.empty


def test_earnings_forecast_fcf_analysis(tmp_path):
    lake = LakehouseManager(data_dir=tmp_path)
    collector = EarningsForecastCollector(lakehouse=lake)

    fcf_res = collector.get_fcf_analysis("600519", periods=4)
    assert isinstance(fcf_res, dict)
    assert "average_fcf_billion" in fcf_res
    assert "fcf_quality" in fcf_res
    assert len(fcf_res["history"]) == 4

    # 2. 验证非预设档案股票（在线提取或湖仓计算）
    res_non_profile = collector.screen_financial_risks("002594")
    assert isinstance(res_non_profile, dict)
    assert res_non_profile["symbol"] == "002594.SZ"
    assert "risk_level" in res_non_profile

    # 3. 验证亏损企业（净利润为负）时 FCF/净利润乘数不发生倒挂除以 0.01 爆炸
    df_loss = pd.DataFrame([{
        "symbol": "600000.SH",
        "stock_name": "亏损标的",
        "report_date": "2026-12-31",
        "period_type": "年报",
        "total_revenue_billion": 50.0,
        "revenue_yoy_pct": -20.0,
        "net_profit_billion": -15.0,  # 亏损 15 亿
        "net_profit_yoy_pct": -150.0,
        "roe_pct": -8.5,
        "gross_margin_pct": 5.0,
        "eps": -0.5,
        "bps": 4.2,
        "ocf_per_share": -0.3,
        "updated_at": "2026-10-29 12:00:00"
    }])
    lake.upsert_stock_financials("600000", df_loss)
    fcf_loss = collector.get_fcf_analysis("600000", periods=1)
    assert fcf_loss["history"][0]["fcf_to_profit_ratio"] == 0.0
    assert "脆弱" in fcf_loss["fcf_quality"]


def test_earnings_forecast_sync_and_fallback(tmp_path):
    lake = LakehouseManager(data_dir=tmp_path)
    collector = EarningsForecastCollector(lakehouse=lake)

    # 验证未匹配代码的保底生成
    df_fb = collector._generate_fallback_forecast(symbol="999999", limit=2)
    assert len(df_fb) == 1
    assert "999999" in df_fb.iloc[0]["symbol"]

    # 验证增量入湖同步
    res_sync = collector.sync_to_lakehouse(["600519", "300750"])
    assert res_sync["earnings_forecast"] > 0
    assert res_sync["financial_risk_screen"] == 2
    assert (lake.mart_dir / "earnings_forecast.parquet").exists()
    assert (lake.mart_dir / "financial_risk_screen.parquet").exists()
