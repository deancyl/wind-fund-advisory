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
BASE = AGY2_DIR if (AGY2_DIR / "app_gui.py").exists() and ROOT.name != "AGY2_FundAdvisory" else ROOT
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


def run_g42_gate():
    gui_txt = (BASE / "app_gui.py").read_text(encoding="utf-8")
    sb_txt = (BASE / "strategy_bridge.py").read_text(encoding="utf-8")
    pm_txt = (AGY2_DIR / "portfolio_manager.py").read_text(encoding="utf-8") if (AGY2_DIR / "portfolio_manager.py").exists() else (ROOT / "portfolio_manager.py").read_text(encoding="utf-8")
    ve_path = AGY2_DIR / "valuation_engine.py"
    ve_txt = ve_path.read_text(encoding="utf-8") if ve_path.exists() else ""
    api_txt = (BASE / "api_server.py").read_text(encoding="utf-8")

    # 1. AST 语法全绿
    for nm, t in [("app_gui.py", gui_txt), ("strategy_bridge.py", sb_txt), ("portfolio_manager.py", pm_txt), ("api_server.py", api_txt)]:
        ast.parse(t, filename=nm)

    # 2. 验证 3 处隐蔽 Bug 已真实修复
    assert "_pending_desktop_nav_redirect" in gui_txt, "app_gui.py 尚未修复立即执行跳转 widget key 锁死 Bug"
    assert "fetch_realtime_fund_quota" in sb_txt and "FundMetadataManager" in sb_txt, "strategy_bridge.py 买前安检尚未接入真实限额与元数据"
    assert "persisted_prev_nav" in (pm_txt + ve_txt), "valuation_engine/portfolio_manager 分红除权检测尚未改用持久化昨日净值基准"

    # 3. 验证 docs/openapi_v1.json 已落盘且包含全部跨端必备路由
    oa_path = (BASE / "docs" / "openapi_v1.json") if (BASE / "docs" / "openapi_v1.json").exists() else (ROOT / "docs" / "openapi_v1.json")
    assert oa_path.exists(), "缺少 docs/openapi_v1.json，请先运行 py -3 api_server.py --export-openapi"
    oa = json.loads(oa_path.read_text(encoding="utf-8"))
    for ep in ["/api/v1/overview", "/api/v1/holdings", "/api/v1/sectors", "/api/v1/ledger/export", "/api/v1/ledger/import", "/api/v1/holdings/reconcile"]:
        assert ep in oa.get("paths", {}), f"OpenAPI 契约缺少跨端核心路径: {ep}"

    # 4. 真实子进程启动 api_server.py 校验 /api/v1/sectors 与 /api/v1/ledger/export 返回 HTTP 200
    proc = subprocess.Popen(
        [sys.executable, str(BASE / "api_server.py"), "--host", "127.0.0.1", "--port", "18142"],
        cwd=str(BASE), stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    try:
        for _ in range(30):
            try:
                with urllib.request.urlopen("http://127.0.0.1:18142/api/health", timeout=1.0) as r:
                    if r.status == 200:
                        break
            except Exception:
                time.sleep(0.3)
        for ep in ["/api/v1/sectors", "/api/v1/ledger/export", "/api/v1/overview"]:
            with urllib.request.urlopen(f"http://127.0.0.1:18142{ep}", timeout=5.0) as r:
                assert r.status == 200
                json.loads(r.read().decode("utf-8"))
    finally:
        proc.terminate()
        proc.wait(timeout=5)

    # 5. Playwright 实机点击「立即执行」，验证页面真正跳转至「调仓工作台」且零红框异常
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
        assert page.locator('[data-testid="stException"]').count() == 0
        page.locator('button:has-text("立即执行")').first.click()
        page.wait_for_timeout(2500)
        assert page.locator('[data-testid="stException"]').count() == 0, "点击立即执行后出现异常"
        assert "调仓工作台" in page.inner_text("body"), "点击立即执行后未真正跳转至调仓工作台"
        browser.close()

    print("ALL G42 FINAL CLOSURE & CROSS-PLATFORM CLIENT-READY GATES PASSED")


if __name__ == "__main__":
    run_g42_gate()
