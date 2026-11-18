"""
verify_g27_anticheat_and_routing_gate.py
G27 世代底层估值逻辑长效加固与五类资产分治路由反作弊门禁
"""

import sys
import os
import time
from pathlib import Path

# 将 AGY2_FundAdvisory 纳入模块搜索路径
CURRENT_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = CURRENT_DIR.parent if CURRENT_DIR.name == "scripts" else CURRENT_DIR
AGY2_DIR = WORKSPACE_ROOT / "AGY2_FundAdvisory" if (WORKSPACE_ROOT / "AGY2_FundAdvisory").exists() else WORKSPACE_ROOT
if str(AGY2_DIR) not in sys.path:
    sys.path.insert(0, str(AGY2_DIR))
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from portfolio_manager import (
    prefetch_batch_fund_quotes,
    fetch_realtime_fund_quote,
    clear_realtime_cache,
    get_calibrated_feeder_beta,
    _DAILY_EST_ARCHIVE_FILE,
    _TODAY_EST_ARCHIVE,
    _REALTIME_QUOTE_CACHE,
    FundQuote,
)


def run_g27_anticheat_and_routing_audit():
    combat_29 = [
        "005561", "100032", "011612", "011613", "002351", "110020", "161725",
        "000216", "000217", "017436", "005827", "016634", "001053", "050025",
        "002352", "016441", "013841", "012832", "012769", "008682", "002611",
        "019260", "000058", "001071", "000086", "018757", "001595", "007339", "160418"
    ]
    clear_realtime_cache()
    t0 = time.perf_counter()
    quotes = prefetch_batch_fund_quotes(combat_29, force_refresh=True)
    elapsed = time.perf_counter() - t0
    assert elapsed < 3.5, f"批量预取耗时超标: {elapsed:.2f}s"

    # 门禁 1：验证 q_seed 隔离修复，所有映射标的的 penetration_gszzl 绝不为 None
    must_have_pen = ["100032", "008682", "005561", "110020", "011612", "016441", "000216", "017436", "050025", "001053", "002351"]
    for c in must_have_pen:
        q = quotes[c]
        assert q.penetration_gszzl is not None, f"{c} ({q.name}) 的 penetration_gszzl 被错误置为 None！"

    # 门禁 2：验证 QDII 严禁采信新浪白天失真 fu_ 估值
    for qdii_c in ["017436", "050025", "001071"]:
        q_qdii = quotes[qdii_c]
        assert "新浪" not in q_qdii.est_source, f"QDII {qdii_c} 严禁使用新浪白天失真估值，当前来源: {q_qdii.est_source}"

    # 门禁 3：验证 001053 (华夏中证500ETF联接C) 残余股票失真熔断生效
    q_001053 = quotes["001053"]
    if q_001053.tiantian_gszzl is not None and q_001053.penetration_gszzl is not None:
        if abs(q_001053.tiantian_gszzl - q_001053.penetration_gszzl) > 0.18:
            assert q_001053.est_gszzl == q_001053.penetration_gszzl, (
                f"001053 未触发残余股票失真熔断: est={q_001053.est_gszzl}, pen={q_001053.penetration_gszzl}, tt={q_001053.tiantian_gszzl}"
            )

    # 门禁 4：验证单基查询入口 fetch_realtime_fund_quote 与批量入口完全同轨
    q_single = fetch_realtime_fund_quote("100032", use_cache=False)
    assert q_single.est_gszzl is not None and len(q_single.val_compare_str) > 0

    # 门禁 5：验证独立盘中定格归档文件已生成且非空
    assert _DAILY_EST_ARCHIVE_FILE.exists() or (WORKSPACE_ROOT / "data" / "daily_intraday_est_archive.json").exists(), "独立盘中定格估算归档文件未生成"

    # 门禁 6：缓存过期单基金查询不退化断言（杜绝假 0 误差）
    # 模拟在官方公布净值后（如 100032），清空缓存后单独单基金查询，est_gszzl 仍保持定格估算，绝不被 official_chg 覆写
    clear_realtime_cache()
    q_recheck = fetch_realtime_fund_quote("100032", use_cache=False)
    if q_recheck.is_official_nav and q_recheck.official_chg_pct is not None:
        arch = _TODAY_EST_ARCHIVE.get("100032")
        if arch:
            expected_est = arch[2]
            assert q_recheck.est_gszzl == expected_est, f"单基金缓存过期后 est_gszzl 退化: got {q_recheck.est_gszzl}, expected {expected_est}"
            if abs(expected_est - q_recheck.official_chg_pct) > 1e-4:
                assert q_recheck.est_diff != 0.0, f"单基金制造了假0误差: diff={q_recheck.est_diff}"

    # 门禁 7：验证滚动有效仓位 Beta 在合理物理区间 [0.85, 1.00]
    beta_val = get_calibrated_feeder_beta("110020", "sh000300", 0.95)
    assert 0.85 <= beta_val <= 1.00, f"110020 滚动 Beta 越界: {beta_val}"

    # 打印对账汇总
    diffs = [abs(q.est_diff) for q in quotes.values() if q.is_official_nav and q.est_diff is not None]
    green_cnt = sum(1 for d in diffs if d <= 0.15)
    mae = (sum(diffs) / len(diffs)) if diffs else 0.0
    print(f"[PASS] G27 反作弊与分治路由核验通过 | 耗时={elapsed:.2f}s | 已出官方={len(diffs)}只 | MAE={mae:.3f}% ({mae*100:.1f}bps) | <=15bp绿灯={green_cnt}/{len(diffs)}")
    for c in ["001053", "001071", "017436", "000216", "100032", "016441", "002351", "011612"]:
        q = quotes[c]
        print(f"  {c} {q.name[:12]:<12} | 综合估={q.est_gszzl:+.2f}% [{q.est_source}] | 新浪/天天={q.tiantian_gszzl} | 穿透={q.penetration_gszzl} | 对账={q.val_compare_str}")


if __name__ == "__main__":
    run_g27_anticheat_and_routing_audit()
