"""
公募基金批量防风控净值同步引擎 (BatchFundSyncer)：
负责按梯度（晨星高星级、头部旗舰、热门 ETF 等）顺序、
单线程节流防风控 (Anti-Throttling)、指数级退避重试与断点续传，
批量同步公募基金全历史日净值时序入湖。
"""

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import random
import time
from typing import Callable, Dict, List, Optional, Any, Union
import pandas as pd

from ..storage.lakehouse import LakehouseManager
from ..parsers.fund_nav_fetcher import FundNAVFetcher, FundNAVSummary


@dataclass
class BatchFundSyncSummary:
    """批量基金净值同步摘要报告"""
    target_count: int
    success_count: int
    skipped_count: int
    failed_count: int
    total_nav_days: int
    start_time: str
    end_time: str
    elapsed_seconds: float
    checkpoint_file: str


class BatchFundSyncer:
    """全市场基金批量时序同步控制器"""

    def __init__(
        self,
        lakehouse: Optional[LakehouseManager] = None,
        min_delay: float = 1.2,
        max_delay: float = 2.2,
        max_retries: int = 3,
        checkpoint_path: Optional[Union[str, Path]] = None
    ):
        self.lakehouse = lakehouse or LakehouseManager()
        self.fetcher = FundNAVFetcher(self.lakehouse)
        self.min_delay = max(0.5, float(min_delay))
        self.max_delay = max(self.min_delay, float(max_delay))
        self.max_retries = max(1, int(max_retries))

        if checkpoint_path:
            self.checkpoint_path = Path(checkpoint_path)
        else:
            self.checkpoint_path = self.lakehouse.master_dir / "fund_nav_checkpoint.json"

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
        """检查标的是否在本地湖仓中且状态正常"""
        code = self.fetcher.normalize_code(symbol)
        std_sym = f"{code}.OF"
        parquet_file = self.lakehouse.get_fund_file_path(std_sym)
        if not parquet_file.exists():
            return False

        res = checkpoint.get("results", {}).get(std_sym)
        if res and res.get("status") == "success":
            return True
        return False

    def sync_funds(
        self,
        fund_list: List[Dict[str, str]],
        limit: Optional[int] = None,
        force: bool = False,
        on_progress: Optional[Callable[[int, int, str, str, str, float], None]] = None
    ) -> BatchFundSyncSummary:
        """
        批量拉取指定基金列表的完整历史日净值时序
        fund_list: [{"symbol": "000001", "name": "华夏成长混合"}, ...]
        """
        start_ts = time.time()
        start_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        checkpoint = self.load_checkpoint()
        targets = fund_list[:limit] if limit and limit > 0 else fund_list

        total_target = len(targets)
        success_count = 0
        skipped_count = 0
        failed_count = 0
        total_nav_days_accumulated = 0

        for idx, item in enumerate(targets, start=1):
            raw_sym = item.get("symbol", "")
            code = self.fetcher.normalize_code(raw_sym)
            std_sym = f"{code}.OF"
            name = item.get("name") or item.get("fund_name") or f"公募基金_{code}"

            # 1. 检查断点防重跑
            if not force and self.is_already_synced(std_sym, checkpoint):
                skipped_count += 1
                rec = checkpoint["results"][std_sym]
                total_nav_days_accumulated += rec.get("bars", 0)
                if on_progress:
                    on_progress(idx, total_target, std_sym, name, "SKIPPED", 0.0)
                continue

            # 2. 带有退避重试的安全防风控拉取
            success = False
            last_err = ""
            summary: Optional[FundNAVSummary] = None

            for attempt in range(1, self.max_retries + 1):
                try:
                    summary = self.fetcher.fetch_fund_nav(code, fund_name=name)
                    success = True
                    break
                except Exception as e:
                    last_err = str(e)
                    if attempt < self.max_retries:
                        backoff = 3.0 * (2 ** (attempt - 1))
                        time.sleep(backoff)

            # 3. 记录结果与落盘断点
            if success and summary:
                success_count += 1
                total_nav_days_accumulated += summary.total_nav_days
                checkpoint["results"][std_sym] = {
                    "status": "success",
                    "name": name,
                    "bars": summary.total_nav_days,
                    "latest_date": summary.end_date,
                    "latest_nav": summary.latest_unit_nav,
                    "synced_at": datetime.now().isoformat()
                }
                checkpoint["completed_count"] = len([r for r in checkpoint["results"].values() if r.get("status") == "success"])
                self.save_checkpoint(checkpoint)

                if on_progress:
                    on_progress(idx, total_target, std_sym, name, "SUCCESS", summary.latest_unit_nav)
            else:
                failed_count += 1
                checkpoint["results"][std_sym] = {
                    "status": "failed",
                    "name": name,
                    "error": last_err,
                    "failed_at": datetime.now().isoformat()
                }
                checkpoint["failed_count"] = len([r for r in checkpoint["results"].values() if r.get("status") == "failed"])
                self.save_checkpoint(checkpoint)

                if on_progress:
                    on_progress(idx, total_target, std_sym, name, "FAILED", 0.0)

            # 4. 周期性刷新 DuckDB 视图
            if (idx % 10 == 0) or (idx == total_target):
                self.lakehouse.init_duckdb_views()

            # 5. 动态冷却休眠
            if idx < total_target:
                jitter = random.uniform(self.min_delay, self.max_delay)
                time.sleep(jitter)

        self.lakehouse.init_duckdb_views()

        end_ts = time.time()
        end_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return BatchFundSyncSummary(
            target_count=total_target,
            success_count=success_count,
            skipped_count=skipped_count,
            failed_count=failed_count,
            total_nav_days=total_nav_days_accumulated,
            start_time=start_time_str,
            end_time=end_time_str,
            elapsed_seconds=round(end_ts - start_ts, 2),
            checkpoint_file=str(self.checkpoint_path)
        )
