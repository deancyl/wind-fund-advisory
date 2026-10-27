"""
全市场公募基金同步与净值时序单元测试
"""

from pathlib import Path
import pytest
import pandas as pd

from src.parsers.fund_catalog import FundCatalogManager
from src.parsers.fund_nav_fetcher import FundNAVFetcher
from src.core.batch_fund_syncer import BatchFundSyncer, BatchFundSyncSummary
from src.storage.lakehouse import LakehouseManager


def test_fund_catalog_paths():
    lakehouse = LakehouseManager()
    mgr = FundCatalogManager(lakehouse)
    assert mgr.catalog_path.name == "fund_catalog.parquet"
    assert mgr.rank_path.name == "fund_performance_snapshot.parquet"
    assert mgr.ratings_path.name == "fund_ratings.parquet"
    assert mgr.managers_path.name == "fund_managers.parquet"
    assert mgr.etf_path.name == "etf_catalog.parquet"


def test_fund_nav_fetcher_normalize():
    assert FundNAVFetcher.normalize_code("000001") == "000001"
    assert FundNAVFetcher.normalize_code("000001.OF") == "000001"
    assert FundNAVFetcher.normalize_code("2910") == "002910"
    assert FundNAVFetcher.normalize_code("002910.of") == "002910"


def test_batch_fund_syncer_checkpoint(tmp_path):
    lakehouse = LakehouseManager()
    cp_path = tmp_path / "fund_nav_cp.json"
    syncer = BatchFundSyncer(lakehouse, checkpoint_path=cp_path)

    cp = syncer.load_checkpoint()
    assert cp["completed_count"] == 0
    assert "results" in cp

    cp["results"]["000001.OF"] = {"status": "success", "bars": 6030}
    cp["completed_count"] = 1
    syncer.save_checkpoint(cp)

    reloaded = syncer.load_checkpoint()
    assert reloaded["completed_count"] == 1
    assert "000001.OF" in reloaded["results"]
