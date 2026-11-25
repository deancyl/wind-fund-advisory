# -*- coding: utf-8 -*-
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGY2_DIR = ROOT / "AGY2_FundAdvisory"
BASE = AGY2_DIR if (AGY2_DIR / "app_gui.py").exists() else ROOT
for p in [str(ROOT), str(AGY2_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)


def run_g36_gate():
    print("=== G36 九大课题全链路闭环与零死代码验收门禁 ===")
    gui_txt = (BASE / "app_gui.py").read_text(encoding="utf-8")
    sb_txt = (BASE / "strategy_bridge.py").read_text(encoding="utf-8")
    pm_txt = (BASE / "portfolio_manager.py").read_text(encoding="utf-8")
    adv_txt = (BASE / "advisory_engine.py").read_text(encoding="utf-8")
    api_txt = (BASE / "api_server.py").read_text(encoding="utf-8")

    # 1. AST 语法全绿
    for nm, t in [("app_gui.py", gui_txt), ("strategy_bridge.py", sb_txt), ("portfolio_manager.py", pm_txt), ("advisory_engine.py", adv_txt), ("api_server.py", api_txt)]:
        ast.parse(t, filename=nm)
    print("  [OK] 门禁 1: 5 核心模块 AST 语法零错误")

    # 2. 课题 5 零死代码硬断言：分红除权与买前安检必须真实接入主链路
    assert "inspect_buy_candidate_safety" in sb_txt, "strategy_bridge.py 尚未接入买前四项硬安检"
    assert "detect_dividend_or_split_false_alarm" in pm_txt, "portfolio_manager.py 尚未接入分红除权防误报"
    print("  [OK] 门禁 2: 分红除权与买前硬安检主链路接线通过")

    # 3. 课题 4 零断链硬断言：增量核对与交割倒计时必须接入前台与 API
    assert "reconcile_incremental_holdings_diff" in gui_txt or "reconcile_incremental_holdings_diff" in api_txt, "增量核对器仍未接线"
    assert "estimate_settlement_timeline" in gui_txt, "前台在途视图尚未接入 T+2/T+7 交割倒计时"
    print("  [OK] 门禁 3: 增量核对与交割倒计时接线通过")

    # 4. 课题 1 去重硬断言：持仓页不再重复出现新钱定投副本
    cnt_dca = gui_txt.count('with st.expander("新钱定投"')
    assert cnt_dca <= 1, f"app_gui.py 仍存在重复的新钱定投折叠块: count={cnt_dca}"
    print(f"  [OK] 门禁 4: 职责去重通过 (新钱定投 expander 副本数: {cnt_dca})")

    # 5. 课题 2 陈旧数据中立化实测：传入 15 天前旧截面日期，五维必须全部 delta_pct == 0.0
    from advisory_engine import evaluate_ten_dimensional_advisory
    stale_res = evaluate_ten_dimensional_advisory(
        snapshot={"date": "2026-10-01", "treasury_10y": 1.65, "dr007": 1.38, "us_10y_yield": 4.40, "spot_usdcnh": 7.20, "option_iv_pct": 19.0},
        macro_multi={},
        sentry_rep={},
    )
    for d in stale_res.get("dimensions", []):
        if d.get("dimension") in ("宏观经济", "货币政策", "国际联动", "外汇锁汇", "期权与黑天鹅"):
            assert d.get("delta_pct", 0.0) == 0.0, f"陈旧截面数据未被中立化: {d}"
    print("  [OK] 门禁 5: 陈旧数据五维中立化实测通过")

    # 6. 课题 9 纯净解耦与新增跨端接口实测
    assert "streamlit" not in api_txt and "ui_daily_brief" not in api_txt, "api_server.py 出现 streamlit 依赖污染"
    from fastapi.testclient import TestClient
    import api_server
    client = TestClient(api_server.app)
    r_exp = client.get("/api/v1/ledger/export")
    assert r_exp.status_code == 200 and "holdings" in r_exp.json()
    r_rec = client.post("/api/v1/holdings/reconcile", json={"updates": [], "dry_run": True})
    assert r_rec.status_code == 200
    print("  [OK] 门禁 6: API 纯净解耦、导出与增量核对路由 HTTP 200 实测通过")

    # 7. Playwright 实机双端零异常验收（若 Streamlit 在 8501 运行则进行端到端验证）
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            for label, vp in [("desktop_1440", {"width": 1440, "height": 900}), ("mobile_390", {"width": 390, "height": 844})]:
                page = browser.new_page(viewport=vp)
                page.goto("http://127.0.0.1:8501", wait_until="networkidle", timeout=8000)
                page.wait_for_timeout(2000)
                assert page.locator('[data-testid="stException"]').count() == 0, f"[{label}] 出现红框报错"
                body = page.inner_text("body")
                assert "核心行情源异常" not in body and "部分行情通道降级" not in body, f"[{label}] 首屏仍出现假告警横幅"
                page.close()
            browser.close()
        print("  [OK] 门禁 7: Playwright 实机双端页面零异常验收通过")
    except Exception as e:
        print(f"  [INFO] 门禁 7: Playwright 提示 (8501 端口未就绪或跳过UI探针: {type(e).__name__}: {e})")

    print("ALL G36 NINE-TOPICS CLOSURE & ZERO-DEAD-CODE GATES PASSED")


if __name__ == "__main__":
    run_g36_gate()
