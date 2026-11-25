# -*- coding: utf-8 -*-
"""
verify_tiantian_fundgz_live_gate.py
====================================================================
AGY2 G36 根治“核心行情源异常：天天基金盘中实时估值(tiantian_fundgz)”实机验收门禁
====================================================================
验证点：
1. 连续 2 次全量拉取 29 只实战持仓（包含 002352 等无天天估值文件的债基），tiantian_fundgz 严禁因单基 404 误入 RED
2. 主力源健康在线时，pause_aggressive_rebalance 严格为 False
3. Playwright 真机打开 8501 确认首屏 0 红框报错、0「核心行情源异常」、0「部分行情通道降级」
"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
AGY2_DIR = ROOT / "AGY2_FundAdvisory"
for p in [str(ROOT), str(AGY2_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from data_resilience_guard import DataSourceHealthRegistry
from portfolio_manager import prefetch_batch_fund_quotes, clear_realtime_cache
from strategy_bridge import StrategyBridge


def run_live_gate():
    print("[G36] 1. 开始重置并执行 29 只实战组合双轮真实拉取...")
    DataSourceHealthRegistry.reset()
    clear_realtime_cache()

    combat_29 = [
        "005561", "100032", "011612", "011613", "002351", "110020", "161725",
        "000216", "000217", "017436", "005827", "016634", "001053", "050025",
        "002352", "016441", "013841", "012832", "012769", "008682", "002611",
        "019260", "000058", "001071", "000086", "018757", "001595", "007339", "160418"
    ]
    # 连续拉取 2 次真实 29 只组合（复现原 2 次失败即触发 RED 熔断的场景）
    StrategyBridge.get_latest_market_snapshot(force_reload=True)
    for i in range(2):
        clear_realtime_cache()
        quotes = prefetch_batch_fund_quotes(combat_29, force_refresh=True)
        print(f"  -> 第 {i+1} 轮拉取完成，获取 {len(quotes)} 只基金行情。")

    summary = DataSourceHealthRegistry.get_health_summary()
    tt_status = summary["channels"]["tiantian_fundgz"]["status"]
    print("\n[LIVE HEALTH]", {k: v["status"] for k, v in summary["channels"].items()})

    # 硬断言 1：连续 2 次拉取含 002352 的 29 只实盘组合后，tiantian_fundgz 严禁因单基 404 误入 RED
    assert tt_status in ("GREEN", "STANDBY"), f"tiantian_fundgz 仍异常: {summary['channels']['tiantian_fundgz']}"
    assert summary["pause_aggressive_rebalance"] is False, f"主源健康时误触发了激进调仓熔断: {summary['pause_reason']}"
    print("  -> 硬断言 1 通过：tiantian_fundgz 保持健康待命态，未误触发激进调仓熔断！")

    # 硬断言 2：Playwright 真实打开 8501 确认首屏零红框报错、零「核心行情源异常」、零「部分行情通道降级」
    print("[G36] 2. Playwright 真机打开 8501 校验首屏渲染...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto("http://127.0.0.1:8501", wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(3500)
        assert page.locator('[data-testid="stException"]').count() == 0, "页面出现 Streamlit 异常框"
        body = page.inner_text("body")
        assert "核心行情源异常" not in body, "首屏仍残留「核心行情源异常」红条"
        assert "部分行情通道降级" not in body, "首屏仍残留「部分行情通道降级」黄条"
        page.close()
        browser.close()
    print("  -> 硬断言 2 通过：首屏完全纯净，零红条零黄条！")

    print("\n✅ ALL TIANTIAN_FUNDGZ LIVE PROBE & ZERO-FALSE-RED-BANNER GATES PASSED")


if __name__ == "__main__":
    run_live_gate()
