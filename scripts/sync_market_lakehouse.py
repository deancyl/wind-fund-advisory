# -*- coding: utf-8 -*-
"""
AGY2 全市场 360 只精英复权净值湖仓防封禁建库与增量日更 CLI 工具
用法：
  - 首次全市场安全建库（2 并发 + 随机抖动 + 断点续传）: py -3 scripts/sync_market_lakehouse.py --mode build --target 360
  - 盘后极轻增量日更（仅 7~8 次批量请求，< 2 秒）:      py -3 scripts/sync_market_lakehouse.py --mode daily
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "AGY2_FundAdvisory"))

from market_lakehouse import incremental_daily_sync, sync_elite_nav_lakehouse


def main():
    parser = argparse.ArgumentParser(description="AGY2 Full-Market Elite Real-NAV Lakehouse Syncer")
    parser.add_argument("--mode", choices=["build", "daily"], default="build")
    parser.add_argument("--target", type=int, default=360)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if args.mode == "daily":
        res = incremental_daily_sync(cooldown_minutes=0 if args.force else 30)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return

    def _cb(cur: int, tot: int, msg: str):
        print(f"[{cur}/{tot}] {msg}", flush=True)

    status = sync_elite_nav_lakehouse(
        target_total=args.target,
        workers=args.workers,
        resume=True,
        force_refetch=args.force,
        progress_cb=_cb,
    )
    print("\n=== LAKEHOUSE BUILD COMPLETE ===")
    print(json.dumps(status, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
