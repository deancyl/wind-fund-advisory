"""
单元测试：WindToolkit 中债收益率曲线与固定收益分析器 (ChinaBondYieldCollector)
"""

import pytest
import pandas as pd

from src.toolkit.bonds import ChinaBondYieldCollector, YieldCurveSnapshot
from src.storage.lakehouse import LakehouseManager


def test_bonds_fetch_chinabond_yield_curve(tmp_path):
    lake = LakehouseManager(data_dir=tmp_path)
    collector = ChinaBondYieldCollector(lakehouse=lake)
    df = collector.fetch_chinabond_yield_curve(force=True)
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert "date" in df.columns
    assert "y_1y" in df.columns
    assert "y_6m" in df.columns
    assert "y_10y" in df.columns
    assert "y_30y" in df.columns
    assert "term_spread_10y_1y_bp" in df.columns
    assert "term_spread_10y_3y_bp" in df.columns
    assert "curve_regime" in df.columns

    # 验证湖仓文件
    df_read = lake.get_chinabond_yield_curve()
    assert df_read is not None
    assert not df_read.empty


def test_bonds_get_latest_yield_curve(tmp_path):
    lake = LakehouseManager(data_dir=tmp_path)
    collector = ChinaBondYieldCollector(lakehouse=lake)
    curve = collector.get_latest_yield_curve()
    assert isinstance(curve, dict)
    assert "date" in curve
    assert "y_10y" in curve
    assert curve["y_10y"] > 0


def test_bonds_get_term_spreads_analysis(tmp_path):
    lake = LakehouseManager(data_dir=tmp_path)
    collector = ChinaBondYieldCollector(lakehouse=lake)
    analysis = collector.get_term_spreads_analysis()
    assert isinstance(analysis, dict)
    assert "term_spread_10y_1y_bp" in analysis
    assert "curve_regime" in analysis
    assert "advisory_recommendation" in analysis
    assert len(analysis["advisory_recommendation"]) > 10


def test_bonds_sync_to_lakehouse(tmp_path):
    lake = LakehouseManager(data_dir=tmp_path)
    collector = ChinaBondYieldCollector(lakehouse=lake)
    n = collector.sync_to_lakehouse()
    assert n > 0
    assert (lake.macro_dir / "chinabond_yield_curve.parquet").exists()
