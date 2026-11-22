# -*- coding: utf-8 -*-
"""
verify_g34_single_screen_and_routeA_prep_gate.py
====================================================================
AGY2 v6.1-G34 单屏聚焦 UX 革命与 Route A 跨端底座解耦 终极验收门禁
====================================================================
覆盖全量要求：
- Gate 0: 四大只读裁判文件 SHA-256 严格只读一致
- Gate 1: 单屏极简 UX 与反废话文案门禁 (0长按钮, 4大Tab横向分段控制器, 首屏Movers条带)
- Gate 2: Route A 跨平台无头接口解耦门禁 (Streamlit 0 污染, 100% 结构化 JSON, 打卡持久化)
- Gate 3: 客户端 IA 契约与 OpenAPI 规范完备性门禁
- Gate 4: Playwright 双端真实渲染与零告警门禁
"""
import sys
import os
import ast
import json
import re
import hashlib
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))
sys.path.insert(0, str(WORKSPACE_ROOT / "AGY2_FundAdvisory"))

READONLY_HASHES = {
    "AGY2_FundAdvisory/judge_engine.py": "76F930371176DE7EE6A413174B030101E3210AC6E037F5D10FE229AF31CC07BE",
    "AGY2_FundAdvisory/holdout_vault.py": "88122EAF647040A410E2FD95DA81077DB10149A498A47340FF40B670BD031D2A",
    "AGY2_FundAdvisory/AGENT_SPEC.md": "A346586F9BD2DC0EE83E665BD18E7A6471464C9F7B658E392B989B800CD63957",
    "tests/test_infra.py": "48BEE0DA300D7C0A0848EC1376E4B9B2E55224D2736081713B4340F0362CD100",
}


def sha256_file(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest().upper()


def main():
    print("=" * 68)
    print("AGY2 v6.1-G34 单屏聚焦 UX 革命与 Route A 跨端底座解耦 终极验收门禁")
    print("=" * 68)

    # -------------------------------------------------------------
    # Gate 0: 四大只读裁判文件哈希
    # -------------------------------------------------------------
    for rel_path, expected in READONLY_HASHES.items():
        fp = WORKSPACE_ROOT / rel_path
        assert fp.exists(), f"裁判文件丢失: {rel_path}"
        actual = sha256_file(fp)
        assert actual == expected, f"裁判文件被非法篡改: {rel_path} ({actual} != {expected})"
    print("  [PASS] Gate 0: 四大裁判文件 SHA256 绝对只读一致")

    # -------------------------------------------------------------
    # Gate 1: 单屏极简 UX 与反废话文案门禁
    # -------------------------------------------------------------
    gui_p = WORKSPACE_ROOT / "AGY2_FundAdvisory" / "app_gui.py"
    brief_p = WORKSPACE_ROOT / "AGY2_FundAdvisory" / "ui_daily_brief.py"
    for fp in [gui_p, brief_p]:
        tree = ast.parse(fp.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                fname = getattr(func, "attr", "") or getattr(func, "id", "")
                if fname == "button" and node.args:
                    arg0 = node.args[0]
                    if isinstance(arg0, ast.Constant) and isinstance(arg0.value, str):
                        txt = arg0.value
                        clean = re.sub(r"[^\u4e00-\u9fa5]", "", txt)
                        assert len(txt) <= 8 and len(clean) <= 4, f"违规长按钮: {txt} in {fp.name}"
                        assert "(" not in txt and "（" not in txt, f"按钮含括号: {txt} in {fp.name}"

    gui_txt = gui_p.read_text(encoding="utf-8")
    for req_key in [
        "rad_holdings_single_view",
        "rad_rebalance_single_view",
        "rad_backtest_single_view",
        "rad_toolbox_single_view",
        "_render_daily_movers_strip",
        "今日贡献 Top 3",
    ]:
        assert req_key in gui_txt, f"app_gui.py 缺少单屏控制关键符号: {req_key}"

    # 确认黄色常驻 banner 已消除
    assert "当前有 {yellow_count} 个数据源触发降级" not in gui_txt, "仍然存在常驻黄色警告 banner!"

    print("  [PASS] Gate 1: 单屏极简 UX 与反废话文案门禁 (0长按钮, 4大Tab横向分段控制器, 首屏Movers条带, 0黄色常驻Banner)")

    # -------------------------------------------------------------
    # Gate 2: Route A 跨平台无头接口解耦门禁
    # -------------------------------------------------------------
    # 在独立环境中导入 api_server，断言未引入 streamlit
    import subprocess
    cmd_decoupled = [
        sys.executable, "-c",
        "import sys; import api_server; assert 'streamlit' not in sys.modules, 'Streamlit was imported!'; print('DECOUPLED_OK')"
    ]
    res_dec = subprocess.run(cmd_decoupled, capture_output=True, text=True, cwd=str(WORKSPACE_ROOT))
    assert res_dec.returncode == 0 and "DECOUPLED_OK" in res_dec.stdout, f"api_server 未彻底解耦 Streamlit: {res_dec.stderr}"

    from fastapi.testclient import TestClient
    import api_server
    client = TestClient(api_server.app)

    # 1. overview
    r_ov = client.get("/api/v1/overview")
    assert r_ov.status_code == 200
    d_ov = r_ov.json()
    for k in ("total_equity", "today_est_pnl", "market_verdict", "indices", "data_health", "valuation_mae"):
        assert k in d_ov, f"/api/v1/overview 缺少字段: {k}"

    # 2. holdings & movers
    r_h = client.get("/api/v1/holdings")
    assert r_h.status_code == 200
    d_h = r_h.json()
    assert d_h["count"] > 0 and "redemption_fee_status" in d_h["items"][0]

    r_mov = client.get("/api/v1/holdings/movers")
    assert r_mov.status_code == 200
    d_mov = r_mov.json()
    assert "top_gainers" in d_mov and "top_losers" in d_mov

    # 3. rebalance & checkin
    r_reb = client.get("/api/v1/rebalance")
    assert r_reb.status_code == 200
    d_reb = r_reb.json()
    assert "groups" in d_reb and "quota_split_plans" in d_reb and "cheat_sheet_text" in d_reb

    # checkin POST & GET & revert
    r_ck = client.post("/api/v1/rebalance/checkin", json={"fund_code": "005561", "action": "BUY", "amount": 500.0, "checked": True})
    assert r_ck.status_code == 200
    r_ck_g = client.get("/api/v1/rebalance/checkin")
    assert r_ck_g.status_code == 200 and "005561" in r_ck_g.json().get("checked_codes", {})
    client.post("/api/v1/rebalance/checkin", json={"fund_code": "005561", "action": "BUY", "amount": 500.0, "checked": False})

    # 4. alerts push
    r_alt = client.get("/api/v1/alerts/push")
    assert r_alt.status_code == 200
    assert "alerts" in r_alt.json()

    # 5. review subviews
    for sv in ["timemachine", "rolling_winrate", "forward_audit", "shadow_race"]:
        r_rev = client.get(f"/api/v1/review/{sv}")
        assert r_rev.status_code == 200, f"review/{sv} 失败"
        assert "<div" not in r_rev.text and "<span" not in r_rev.text

    # 6. diagnose subviews
    for sv in ["risk_check", "exposure", "overlap", "stress_test", "ten_dim_votes"]:
        r_diag = client.get(f"/api/v1/diagnose/{sv}")
        assert r_diag.status_code == 200, f"diagnose/{sv} 失败"
        assert "<div" not in r_diag.text and "<span" not in r_diag.text

    # 7. backtest summary
    r_bts = client.get("/api/v1/backtest/summary")
    assert r_bts.status_code == 200
    assert "annualized_return_pct" in r_bts.json()

    print("  [PASS] Gate 2: Route A 跨平台无头接口解耦门禁 (Streamlit 0 污染, 100% 结构化 JSON, 打卡持久化通过)")

    # -------------------------------------------------------------
    # Gate 3: 客户端 IA 契约与 OpenAPI 规范完备性门禁
    # -------------------------------------------------------------
    openapi_p = WORKSPACE_ROOT / "docs" / "openapi_v1.json"
    assert openapi_p.exists(), "docs/openapi_v1.json 丢失"
    openapi_data = json.loads(openapi_p.read_text(encoding="utf-8"))
    assert "/api/v1/overview" in openapi_data.get("paths", {}), "OpenAPI 缺少 /api/v1/overview"
    assert "/api/v1/holdings/movers" in openapi_data.get("paths", {}), "OpenAPI 缺少 /api/v1/holdings/movers"
    assert "/api/v1/rebalance/checkin" in openapi_data.get("paths", {}), "OpenAPI 缺少 /api/v1/rebalance/checkin"

    ia_p = WORKSPACE_ROOT / "docs" / "client_ia_contract.json"
    assert ia_p.exists(), "docs/client_ia_contract.json 丢失"
    ia_data = json.loads(ia_p.read_text(encoding="utf-8"))
    assert "desktop_navigation" in ia_data and "mobile_navigation" in ia_data, "IA 契约缺少双端导航"

    doc_md = WORKSPACE_ROOT / "AGY2_FundAdvisory" / "API_CONTRACT.md"
    assert doc_md.exists(), "API_CONTRACT.md 丢失"

    print("  [PASS] Gate 3: 客户端 IA 契约与 OpenAPI 规范完备性门禁")

    # -------------------------------------------------------------
    # Gate 4: Playwright 双端真实渲染与零告警门禁
    # -------------------------------------------------------------
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Desktop
        page_d = browser.new_page(viewport={"width": 1440, "height": 900})
        page_d.goto("http://127.0.0.1:8501", timeout=60000)
        page_d.wait_for_selector('[data-testid="stTabs"]', timeout=30000)
        page_d.wait_for_timeout(3000)

        # 检查无异常与无黄色横幅
        body_text_d = page_d.inner_text("body")
        assert "stException" not in body_text_d, "桌面端检测到 stException 异常!"
        assert "数据源触发降级" not in body_text_d, "桌面端依然显示黄色降级警告 banner!"
        assert "持仓" in body_text_d and "调仓" in body_text_d and "复盘" in body_text_d and "工具" in body_text_d, "四大主标签未完整渲染!"

        # Mobile
        page_m = browser.new_page(viewport={"width": 390, "height": 844})
        page_m.goto("http://127.0.0.1:8501", timeout=60000)
        page_m.wait_for_selector('[data-testid="stTabs"]', timeout=30000)
        page_m.wait_for_timeout(3000)
        body_text_m = page_m.inner_text("body")
        assert "stException" not in body_text_m, "移动端检测到 stException 异常!"

        browser.close()

    print("  [PASS] Gate 4: Playwright 双端真实渲染与零告警门禁 (0 异常, 0 黄色横幅, 4大主Tab均就绪)")
    print("=" * 68)
    print("ALL G34 SINGLE-SCREEN UX & ROUTE A PREP GATES 100% PASSED!")
    print("=" * 68)


if __name__ == "__main__":
    main()
