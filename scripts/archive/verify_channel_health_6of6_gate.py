import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
AGY2_DIR = ROOT / "AGY2_FundAdvisory"
BASE = AGY2_DIR if (AGY2_DIR / "app_gui.py").exists() else ROOT
for p in [str(ROOT), str(AGY2_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from data_resilience_guard import DataSourceHealthRegistry
from portfolio_manager import prefetch_batch_fund_quotes, clear_realtime_cache
from strategy_bridge import StrategyBridge

def run_channel_health_gate():
    DataSourceHealthRegistry.reset()
    clear_realtime_cache()

    # 触发真实行情与宏观快照拉取
    StrategyBridge.get_latest_market_snapshot(force_reload=True)
    prefetch_batch_fund_quotes(["005561", "100032", "017436", "000216", "002351"], force_refresh=True)

    summary = DataSourceHealthRegistry.get_health_summary()
    print("Channel summary:", {k: v["status"] for k, v in summary["channels"].items()})

    # 硬断言 1：6 路通道严禁再出现无埋点的 UNKNOWN
    assert summary["unknown_count"] == 0, f"仍有通道未埋点处于 UNKNOWN: {summary['channels']}"
    # 硬断言 2：健康通道数 (GREEN + STANDBY) 必须达到 6/6（在网络正常时）
    assert summary["healthy_count"] == summary["total_count"], f"存在异常通道: {summary['degraded_channels']}"
    assert summary["is_degraded"] is False, f"网络正常时不应误报降级: {summary}"

    # 硬断言 3：app_gui.py 中已彻底删除 green_count < total_count 误报黄条
    gui_txt = (BASE / "app_gui.py").read_text(encoding="utf-8")
    assert 'st.warning(f"部分行情通道降级' not in gui_txt, "app_gui.py 第 4342 行误报黄条尚未删除"

    # 硬断言 4：Playwright 真机打开 8501 确认首屏零黄色降级横幅、零红框报错
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto("http://127.0.0.1:8501", wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(3500)
        assert page.locator('[data-testid="stException"]').count() == 0, "页面出现红框报错"
        body = page.inner_text("body")
        assert "部分行情通道降级" not in body, "首屏依然残留「部分行情通道降级」黄色横幅"
        page.close()
        browser.close()

    print("ALL 6/6 CHANNEL HEALTH & ZERO-FALSE-DEGRADATION GATES PASSED")

if __name__ == "__main__":
    run_channel_health_gate()
