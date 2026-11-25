# -*- coding: utf-8 -*-
import ast
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
AGY2_DIR = ROOT / "AGY2_FundAdvisory" if (ROOT / "AGY2_FundAdvisory").exists() else ROOT
for p in [str(ROOT), str(AGY2_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)


def detect_active_port():
    for p in [8501, 8585]:
        try:
            resp = urllib.request.urlopen(f"http://127.0.0.1:{p}/_stcore/health", timeout=1.5)
            if resp.status == 200:
                return p
        except Exception:
            pass
    return 8585


def main():
    print("=== G41 九大课题全量封口与双端就绪零 Mock 门禁 ===")

    # 1. 全库 AST 语法全绿 + 废弃文件彻底清除
    for pyf in ROOT.glob("*.py"):
        ast.parse(pyf.read_text(encoding="utf-8"), filename=pyf.name)
    assert not (ROOT / "ui_daily_brief.py").exists(), "废弃文件 ui_daily_brief.py 尚未删除"
    assert (ROOT / "docs" / "openapi_v1.json").exists(), "缺少仓库内 docs/openapi_v1.json"

    # 2. 课题 5 真逻辑实测：分红除权检测（未复权跌 -8%，复权涨 +0.2%）必须精准识别
    from data_resilience_guard import detect_dividend_or_split_false_alarm, inspect_buy_candidate_safety
    div_r = detect_dividend_or_split_false_alarm(prev_unit_nav=2.0000, curr_unit_nav=1.8400, prev_accum_nav=2.5000, curr_accum_nav=2.5050)
    assert div_r.get("is_dividend_ex") is True, f"分红除权识别失败: {div_r}"
    blk_r = inspect_buy_candidate_safety("999999", "迷你暂停基", is_suspended=True, aum_million=30.0)
    assert blk_r.get("is_cleared") is False and len(blk_r.get("blocking_reasons", [])) >= 2
    assert "FundMetadataManager" in (ROOT / "strategy_bridge.py").read_text(encoding="utf-8")
    print("  [OK] 门禁 1: 课题 5 除权拦截与真实元数据买前安检通过")

    # 3. 课题 9 真实子进程全量 v1 路由 200（含新增 4 组双端同步接口，零 HTML，零 streamlit）
    api_txt = (ROOT / "api_server.py").read_text(encoding="utf-8")
    assert "streamlit" not in api_txt
    proc = subprocess.Popen(
        [sys.executable, str(ROOT / "api_server.py"), "--host", "127.0.0.1", "--port", "18101"],
        cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    try:
        ready = False
        for _ in range(30):
            try:
                with urllib.request.urlopen("http://127.0.0.1:18101/api/health", timeout=1.0) as r:
                    if r.status == 200:
                        ready = True
                        break
            except Exception:
                time.sleep(0.3)
        assert ready, "api_server.py 子进程启动超时"

        for ep in [
            "/api/v1/overview", "/api/v1/holdings", "/api/v1/holdings/movers",
            "/api/v1/rebalance", "/api/v1/alerts/push", "/api/v1/ledger/export",
            "/api/v1/watchlist", "/api/v1/funds/search?q=hldb",
        ]:
            with urllib.request.urlopen(f"http://127.0.0.1:18101{ep}", timeout=5.0) as r:
                assert r.status == 200, f"{ep} HTTP {r.status}"
                txt = r.read().decode("utf-8")
                assert "<div" not in txt and "<span" not in txt
                json.loads(txt)
        print("  [OK] 门禁 2: api_server.py 真实子进程 8 组跨端核心 v1 路由全绿")
    finally:
        proc.terminate()
        proc.wait(timeout=5)

    # 4. Playwright 实机双端对比度 + 零滚动 + 零遮挡验收
    target_port = detect_active_port()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"http://127.0.0.1:{target_port}", timeout=30000)
        for _ in range(30):
            try:
                state = page.locator("[data-testid='stApp']").get_attribute("data-test-script-state")
                if state == "notRunning":
                    break
            except Exception:
                pass
            page.wait_for_timeout(1000)
        page.wait_for_timeout(2500)
        assert page.locator('[data-testid="stException"]').count() == 0, "桌面端存在报错"
        metrics = page.evaluate("""() => {
            const sb = document.querySelector('[data-testid="stSidebar"] > div:first-child');
            const navs = Array.from(document.querySelectorAll('[data-testid="stSidebar"] div[role="radiogroup"] label p'));
            const lums = navs.map(el => {
                const m = getComputedStyle(el).color.match(/\\d+/g).map(Number);
                return 0.299*m[0] + 0.587*m[1] + 0.114*m[2];
            });
            return {
                sb_no_scroll: sb ? (sb.scrollHeight <= sb.clientHeight + 2) : false,
                nav_count: navs.length,
                min_nav_lum: lums.length ? Math.min(...lums) : 0,
                no_x_scroll: document.documentElement.scrollWidth <= window.innerWidth + 2
            };
        }""")
        assert metrics["sb_no_scroll"], f"侧边栏出现纵向滚动条: {metrics}"
        assert metrics["nav_count"] == 4 and metrics["min_nav_lum"] >= 180, f"侧边栏导航存在暗字隐身: {metrics}"
        assert metrics["no_x_scroll"], f"桌面端出现横向滚动条: {metrics}"
        page.close()

        m_page = browser.new_page(viewport={"width": 390, "height": 844})
        m_page.goto(f"http://127.0.0.1:{target_port}", timeout=30000)
        for _ in range(30):
            try:
                state = m_page.locator("[data-testid='stApp']").get_attribute("data-test-script-state")
                if state == "notRunning":
                    break
            except Exception:
                pass
            m_page.wait_for_timeout(1000)
        m_page.wait_for_timeout(2500)
        assert m_page.locator('[data-testid="stException"]').count() == 0, "手机端存在报错"
        assert m_page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 2"), "手机端出现横向溢出"
        m_page.close()
        browser.close()
    print("  [OK] 门禁 3: Playwright 1440px 对比度/零滚动 + 390px 移动端零溢出全绿")
    print("ALL G41 PRODUCTION CLOSURE GATES PASSED")


if __name__ == "__main__":
    main()
