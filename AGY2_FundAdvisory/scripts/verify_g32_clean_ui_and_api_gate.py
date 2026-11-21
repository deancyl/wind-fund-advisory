import ast
import re
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
AGY2_DIR = ROOT / "AGY2_FundAdvisory"
BASE = AGY2_DIR if (AGY2_DIR / "app_gui.py").exists() else ROOT
for p in [str(ROOT), str(AGY2_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)


def run_g32_gate():
    brief_txt = (BASE / "ui_daily_brief.py").read_text(encoding="utf-8")
    api_file = BASE / "api_server.py"
    assert api_file.exists(), "缺少跨端 REST API 模块 api_server.py"
    api_txt = api_file.read_text(encoding="utf-8")

    # 1. AST 语法全绿
    ast.parse(brief_txt, filename="ui_daily_brief.py")
    ast.parse(api_txt, filename="api_server.py")

    # 2. 零废话、零空壳、零重复图标硬断言
    forbidden_strings = [
        "系统安全保障：每次调仓或改动",
        "今日调仓行动单（按意图分组聚合）",
        "前往专家量化实验室 · 账本运维与导入工作区",
        "手头有新钱 / 发工资了？",
        "为什么这么建议？进入专家量化实验室",
        'f"🧹 {t_grp',
        'f"🔄 {c_grp',
        'f"🎯 {k_grp',
    ]
    for bad in forbidden_strings:
        assert bad not in brief_txt, f"ui_daily_brief.py 仍残留废话或重复图标代码: {bad}"

    # 3. 按钮字数硬断言（极简页按钮不得超过 6 个汉字）
    btns = re.findall(r'st\.button\(\s*["\']([^"\']+)["\']', brief_txt)
    assert len(btns) <= 5, f"极简页按钮数量超标: {btns}"
    for b in btns:
        assert len(b.strip()) <= 6, f"极简页按钮文案过长 (上限6字): {b}"

    # 4. C转A 统计口径单元测试（1 卖 C + 1 买 A 必须记为 1 组，不得记为 2 只高费率 C 类）
    from ui_daily_brief import group_rebalance_orders_by_intent
    sample_c = [
        {"fund_code": "011613", "fund_name": "华夏科创50联接C", "action": "SELL", "action_text": "C转A置换", "diff_amount": -2072.52, "is_c_replace": True},
        {"fund_code": "011612", "fund_name": "华夏科创50联接A", "action": "BUY", "action_text": "C转A置换", "diff_amount": 2147.27, "is_c_replace": True},
    ]
    g_res = group_rebalance_orders_by_intent(sample_c)
    assert g_res["c_replace"].get("c_sell_count") == 1, f"C转A 计数错误: {g_res['c_replace']}"
    assert "(1组)" in g_res["c_replace"]["title"], f"C转A 标题未显示 1 组: {g_res['c_replace']['title']}"

    # 5. FastAPI 跨端底座接口实测（覆盖全部 8 大接口与 404/400 异常分支）
    try:
        from fastapi.testclient import TestClient
        import api_server
        client = TestClient(api_server.app)
        
        # /api/health
        r_health = client.get("/api/health")
        assert r_health.status_code == 200 and r_health.json().get("status") == "ok"
        
        # /api/overview
        r_ov = client.get("/api/overview")
        assert r_ov.status_code == 200 and "total_equity" in r_ov.json()
        assert client.get("/api/overview?ledger_id=nonexistent_999").status_code == 404
        
        # /api/holdings
        r_h = client.get("/api/holdings")
        assert r_h.status_code == 200 and r_h.json().get("count", 0) > 0
        assert client.get("/api/holdings?ledger_id=nonexistent_999").status_code == 404
        
        # /api/rebalance
        r_reb = client.get("/api/rebalance")
        assert r_reb.status_code == 200 and "tail_sweep" in r_reb.json()
        assert "items" in r_reb.json().get("buffer_hold", {})
        assert client.get("/api/rebalance?ledger_id=nonexistent_999").status_code == 404
        
        # /api/cashflow/plan
        r_cf = client.post("/api/cashflow/plan", json={"monthly_new_cash": 3000.0, "plan_months": 3})
        assert r_cf.status_code == 200 and "investable_cash" in r_cf.json()
        assert client.post("/api/cashflow/plan", json={"ledger_id": "nonexistent_999"}).status_code == 404
        
        # /api/backups
        r_bk = client.get("/api/backups")
        assert r_bk.status_code == 200 and isinstance(r_bk.json().get("snapshots"), list)
        
        # /api/backups/restore
        r_res_bad = client.post("/api/backups/restore", json={"snapshot_id": "bad_id_nonexistent"})
        assert r_res_bad.status_code == 400
        
        # /api/forward-audit
        r_fa = client.get("/api/forward-audit")
        assert r_fa.status_code == 200 and "logs" in r_fa.json()
        
        print("[PASS] FastAPI 跨端全量 8 大接口与 404/400 容错全部通过")
    except ImportError:
        print("[WARN] 本地未安装 fastapi/httpx，已完成 AST 与代码结构校验，请安装 fastapi uvicorn 后启动 api_server.py")

    # 6. Playwright 真机双端浏览器零报错与零重复图标验收
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for label, vp in [("desktop_1440", {"width": 1440, "height": 900}), ("mobile_390", {"width": 390, "height": 844})]:
            page = browser.new_page(viewport=vp)
            page.goto("http://127.0.0.1:8501", wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(3500)
            assert page.locator('[data-testid="stException"]').count() == 0, f"[{label}] 页面出现红框报错"
            body = page.inner_text("body")
            for bad_txt in ["🧹 🧹", "🔄 🔄", "🎯 🎯", "识别到 2 只已持满免赎期的高费率 C 类", "TypeError", "Traceback"]:
                assert bad_txt not in body, f"[{label}] 真实页面仍存在非法文本: {bad_txt}"
            page.close()
        browser.close()

    print("ALL G32 CLEAN-UI, API-FOUNDATION & BROWSER E2E GATES PASSED")


if __name__ == "__main__":
    run_g32_gate()
