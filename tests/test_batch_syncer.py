"""
批量指数同步引擎与指数字典单元测试
"""

from pathlib import Path
import pytest
import pandas as pd

from src.parsers.index_catalog import IndexCatalog
from src.core.batch_index_syncer import BatchIndexSyncer, BatchSyncSummary
from src.storage.lakehouse import LakehouseManager


def test_index_catalog_build():
    catalog = IndexCatalog()
    df = catalog.build_catalog()
    assert not df.empty
    assert len(df) >= 500
    assert "symbol" in df.columns
    assert "tier" in df.columns
    assert "priority" in df.columns

    tier1_indices = catalog.get_indices(tier="1")
    assert len(tier1_indices) >= 20
    tier1_syms = [x["symbol"] for x in tier1_indices]
    assert "000001.SH" in tier1_syms
    assert "000300.SH" in tier1_syms


def test_batch_syncer_checkpoint(tmp_path):
    lakehouse = LakehouseManager()
    cp_path = tmp_path / "test_cp.json"
    syncer = BatchIndexSyncer(lakehouse, checkpoint_path=cp_path)

    # 1. 验证空断点初始化
    cp = syncer.load_checkpoint()
    assert cp["completed_count"] == 0
    assert "results" in cp

    # 2. 模拟写入并读取
    cp["results"]["000001.SH"] = {"status": "success", "bars": 8750}
    cp["completed_count"] = 1
    syncer.save_checkpoint(cp)

    reloaded = syncer.load_checkpoint()
    assert reloaded["completed_count"] == 1
    assert "000001.SH" in reloaded["results"]


def test_batch_syncer_sync_flow(tmp_path):
    lakehouse = LakehouseManager()
    cp_path = tmp_path / "sync_flow_cp.json"
    syncer = BatchIndexSyncer(lakehouse, min_delay=0.1, max_delay=0.2, checkpoint_path=cp_path)

    # 同步 2 个标的
    summary = syncer.sync_all(tier="1", limit=2, force=False)
    assert isinstance(summary, BatchSyncSummary)
    assert summary.target_count == 2
    assert summary.success_count + summary.skipped_count == 2
    assert summary.failed_count == 0
