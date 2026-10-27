"""
A 股全市场指数批量防风控同步引擎 (BatchIndexSyncer)：
负责按梯级 (Tier 1 核心宽基 -> Tier 2 主流行业 -> Tier 3 细分全量) 顺序、
单线程节流防风控 (Anti-Throttling)、指数级退避重试 (Exponential Backoff)、
断点记忆恢复 (Checkpoint Resumption) 批量拉取全市场指数日 K 线入湖。
"""

from dataclasses import dataclass, asdict
from datetime import datetime
import json
from pathlib import Path
import random
import time
from typing import Callable, Dict, List, Optional, Any, Union
import pandas as pd
from rich.console import Console

from ..storage.lakehouse import LakehouseManager
from ..parsers.index_catalog import IndexCatalog
from ..parsers.index_fetcher import IndexDataFetcher, IndexPullSummary


@dataclass
class BatchSyncSummary:
    """批量同步任务执行摘要报告"""
    target_count: int
    success_count: int
    skipped_count: int
    failed_count: int
    total_bars: int
    start_time: str
    end_time: str
    elapsed_seconds: float
    checkpoint_file: str


class BatchIndexSyncer:
    """全市场指数批量同步控制器"""

    def __init__(
        self,
        lakehouse: Optional[LakehouseManager] = None,
        catalog: Optional[IndexCatalog] = None,
        min_delay: float = 1.2,
        max_delay: float = 2.2,
        max_retries: int = 3,
        checkpoint_path: Optional[Union[str, Path]] = None
    ):
        self.lakehouse = lakehouse or LakehouseManager()
        self.catalog = catalog or IndexCatalog(self.lakehouse)
        self.fetcher = IndexDataFetcher(self.lakehouse, catalog=self.catalog)
        self.min_delay = max(0.5, float(min_delay))
        self.max_delay = max(self.min_delay, float(max_delay))
        self.max_retries = max(1, int(max_retries))
        
        if checkpoint_path:
            self.checkpoint_path = Path(checkpoint_path)
        else:
            self.checkpoint_path = self.lakehouse.master_dir / "index_sync_checkpoint.json"

    def load_checkpoint(self) -> Dict[str, Any]:
        """读取断点记录文件"""
        if self.checkpoint_path.exists():
            try:
                with open(self.checkpoint_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "completed_count": 0,
            "failed_count": 0,
            "results": {}
        }

    def save_checkpoint(self, data: Dict[str, Any]) -> None:
        """保存断点记录"""
        data["updated_at"] = datetime.now().isoformat()
        self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.checkpoint_path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        temp_path.replace(self.checkpoint_path)

    def is_already_synced(self, symbol: str, checkpoint: Dict[str, Any]) -> bool:
        """研判该标的是否已在湖仓中且状态正常"""
        parquet_file = self.lakehouse.get_index_file_path(symbol)
        if not parquet_file.exists():
            return False
        
        res = checkpoint.get("results", {}).get(symbol)
        if res and res.get("status") == "success":
            return True
        return False

    def sync_all(
        self,
        tier: Optional[str] = None,
        limit: Optional[int] = None,
        force: bool = False,
        on_progress: Optional[Callable[[int, int, str, str, str, float], None]] = None
    ) -> BatchSyncSummary:
        """
        执行批量指数同步任务
        """
        start_ts = time.time()
        start_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        checkpoint = self.load_checkpoint()
        targets = self.catalog.get_indices(tier=tier)
        if limit and limit > 0:
            targets = targets[:limit]

        total_target = len(targets)
        success_count = 0
        skipped_count = 0
        failed_count = 0
        total_bars_accumulated = 0

        for idx, item in enumerate(targets, start=1):
            sym = item["symbol"]
            name = item["name"]
            ak_sym = item["ak_symbol"]

            # 1. 检查断点记忆 (防重复请求，秒级跳过)
            if not force and self.is_already_synced(sym, checkpoint):
                skipped_count += 1
                rec = checkpoint["results"][sym]
                total_bars_accumulated += rec.get("bars", 0)
                if on_progress:
                    on_progress(idx, total_target, sym, name, "SKIPPED", 0.0)
                continue

            # 2. 带有指数退避重试的防风控安全拉取
            success = False
            last_err = ""
            summary: Optional[IndexPullSummary] = None

            for attempt in range(1, self.max_retries + 1):
                try:
                    summary = self.fetcher.pull_and_sync_index(sym)
                    success = True
                    break
                except Exception as e:
                    last_err = str(e)
                    if attempt < self.max_retries:
                        backoff = 3.0 * (2 ** (attempt - 1))  # 3s, 6s, 12s
                        time.sleep(backoff)

            # 3. 记录结果与落盘断点
            if success and summary:
                success_count += 1
                total_bars_accumulated += summary.total_bars
                checkpoint["results"][sym] = {
                    "status": "success",
                    "name": name,
                    "bars": summary.total_bars,
                    "latest_date": summary.end_date,
                    "latest_close": summary.latest_close,
                    "wind_synced": summary.wind_live_synced,
                    "synced_at": datetime.now().isoformat()
                }
                checkpoint["completed_count"] = len([r for r in checkpoint["results"].values() if r.get("status") == "success"])
                self.save_checkpoint(checkpoint)

                if on_progress:
                    on_progress(idx, total_target, sym, name, "SUCCESS", summary.latest_close)
            else:
                failed_count += 1
                checkpoint["results"][sym] = {
                    "status": "failed",
                    "name": name,
                    "error": last_err,
                    "failed_at": datetime.now().isoformat()
                }
                checkpoint["failed_count"] = len([r for r in checkpoint["results"].values() if r.get("status") == "failed"])
                self.save_checkpoint(checkpoint)

                if on_progress:
                    on_progress(idx, total_target, sym, name, "FAILED", 0.0)

            # 4. 周期性刷新 DuckDB 视图 (每 10 只标的)
            if (idx % 10 == 0) or (idx == total_target):
                self.lakehouse.init_duckdb_views()

            # 5. 防风控节流冷却 (动态抖动休眠)
            if idx < total_target:
                jitter = random.uniform(self.min_delay, self.max_delay)
                time.sleep(jitter)

        # 最终刷新视图
        self.lakehouse.init_duckdb_views()

        end_ts = time.time()
        end_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return BatchSyncSummary(
            target_count=total_target,
            success_count=success_count,
            skipped_count=skipped_count,
            failed_count=failed_count,
            total_bars=total_bars_accumulated,
            start_time=start_time_str,
            end_time=end_time_str,
            elapsed_seconds=round(end_ts - start_ts, 2),
            checkpoint_file=str(self.checkpoint_path)
        )
