"""
check_live_valuation_reconciliation.py
一键巡检 29 只基金持仓的「当日估算 vs 官方涨跌」双轨对账单
"""

import sys
import time
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = CURRENT_DIR.parent if CURRENT_DIR.name == "scripts" else CURRENT_DIR
AGY2_DIR = WORKSPACE_ROOT / "AGY2_FundAdvisory" if (WORKSPACE_ROOT / "AGY2_FundAdvisory").exists() else WORKSPACE_ROOT
if str(AGY2_DIR) not in sys.path:
    sys.path.insert(0, str(AGY2_DIR))
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from portfolio_manager import prefetch_batch_fund_quotes


def print_live_reconciliation():
    combat_29 = [
        "005561", "100032", "011612", "011613", "002351", "110020", "161725",
        "000216", "000217", "017436", "005827", "016634", "001053", "050025",
        "002352", "016441", "013841", "012832", "012769", "008682", "002611",
        "019260", "000058", "001071", "000086", "018757", "001595", "007339", "160418"
    ]
    t0 = time.perf_counter()
    quotes = prefetch_batch_fund_quotes(combat_29, force_refresh=True)
    elapsed = time.perf_counter() - t0

    print("=" * 115)
    print(f"AGY2 实盘组合实时估值 vs 官方涨跌 双轨对账单 (总耗时: {elapsed:.2f}s)")
    print("=" * 115)
    print(f"{'代码':<8} {'基金简称':<16} {'官方净值':<10} {'官方涨跌':<10} {'当日综合估算':<12} {'偏差(bp)':<10} {'估算来源':<20} {'状态'}")
    print("-" * 115)

    off_diffs = []
    for c in combat_29:
        q = quotes[c]
        off_chg_str = f"{q.official_chg_pct:+.2f}%" if (q.is_official_nav and q.official_chg_pct is not None) else (
            f"待出({q.prev_official_chg_pct:+.2f}%)" if q.prev_official_chg_pct is not None else "--"
        )
        est_chg_str = f"{q.est_gszzl:+.2f}%" if q.est_gszzl is not None else "--"
        if q.is_official_nav and q.est_diff is not None:
            bp_val = round(q.est_diff * 100.0, 1)
            diff_str = f"{bp_val:+.1f}bp"
            off_diffs.append(abs(q.est_diff))
            badge = "🟢" if abs(q.est_diff) <= 0.15 else ("🟡" if abs(q.est_diff) <= 0.40 else "🔴")
        else:
            diff_str = "--"
            badge = "⏳"

        src_str = q.est_source or "四级穿透"
        status_tag = f"{badge} {q.official_pdate[-5:] if q.official_pdate else ''}"
        print(f"{c:<8} {q.name[:14]:<16} {q.dwjz:<10.4f} {off_chg_str:<10} {est_chg_str:<12} {diff_str:<10} {src_str:<20} {status_tag}")

    print("-" * 115)
    if off_diffs:
        mae = sum(off_diffs) / len(off_diffs)
        green = sum(1 for d in off_diffs if d <= 0.15)
        yellow = sum(1 for d in off_diffs if 0.15 < d <= 0.40)
        red = sum(1 for d in off_diffs if d > 0.40)
        print(f"统计指标: 已出官方 {len(off_diffs)}/29 只 | MAE = {mae:.3f}% ({mae*100.0:.1f} bps) | 🟢 <=15bp: {green}只 | 🟡 15~40bp: {yellow}只 | 🔴 >40bp: {red}只")
    print("=" * 115)


if __name__ == "__main__":
    print_live_reconciliation()
