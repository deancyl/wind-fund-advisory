# -*- coding: utf-8 -*-
"""
Wind 终端离线导出净值一键合入 AGY2 本地湖仓适配器（零运行时 Wind 账号绑定）
用法：
  py -3 scripts/import_wind_nav_lakehouse.py --input path/to/wind_fund_adj_nav.parquet
支持长表 (date, fund_code, adj_nav) 或宽表 (date + 多列基金代码) 的 CSV / Parquet 文件。
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "AGY2_FundAdvisory"))

from market_lakehouse import import_wind_nav_file


def main():
    parser = argparse.ArgumentParser(description="Import Wind offline exported fund adjusted NAV into AGY2 lakehouse")
    parser.add_argument("--input", required=True, help="CSV or Parquet file exported from Wind")
    args = parser.parse_args()
    res = import_wind_nav_file(Path(args.input))
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
