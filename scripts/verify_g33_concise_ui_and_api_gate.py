# -*- coding: utf-8 -*-
"""
AGY2 v5.13-G33 去废话统一主视图与跨端 REST API v1 自动化零作弊门禁
"""

import ast
import hashlib
import io
import json
import re
import sys
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
AGY2_DIR = ROOT / "AGY2_FundAdvisory"
BASE = AGY2_DIR if (AGY2_DIR / "app_gui.py").exists() else ROOT
for p in [str(ROOT), str(AGY2_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

REFEREE_HASHES = {
    "AGY2_FundAdvisory/judge_engine.py": "76F930371176DE7EE6A413174B030101E3210AC6E037F5D10FE229AF31CC07BE",
    "AGY2_FundAdvisory/holdout_vault.py": "88122EAF647040A410E2FD95DA81077DB10149A498A47340FF40B670BD031D2A",
    "AGY2_FundAdvisory/AGENT_SPEC.md": "A346586F9BD2DC0EE83E665BD18E7A6471464C9F7B658E392B989B800CD63957",
    "tests/test_infra.py": "48BEE0DA300D7C0A0848EC1376E4B9B2E55224D2736081713B4340F0362CD100",
}

_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
_HTML_RE = re.compile(r"<(?:div|span|br|table|script|p|b|h[1-6]|tr|td|th)\b", re.I)
_EMOJI_RE = re.compile(r"[\U0001F300-\U0001FAFF\u2600-\u27BF\uFE0F\u200D]")


def _check_pure_json(name: str, payload: dict) -> None:
    raw = json.dumps(payload, ensure_ascii=False)
    html_hit = _HTML_RE.search(raw)
    assert not html_hit, f"{name} 响应包含 HTML 标签污染: {html_hit.group(0)}"
    emoji_hit = _EMOJI_RE.search(raw)
    assert not emoji_hit, f"{name} 响应包含 Emoji 污染: {repr(emoji_hit.group(0))}"


def run_g33_gate():
    print("=" * 64)
    print("AGY2 v5.13-G33 去废话统一主视图与跨端 API v1 强门禁")
    print("=" * 64)

    # 1. 四大裁判文件只读校验
    for rel_path, expected in REFEREE_HASHES.items():
        actual = hashlib.sha256((ROOT / rel_path).read_bytes()).hexdigest().upper()
        assert actual == expected, f"裁判文件 SHA256 被篡改: {rel_path}"
    print("  [PASS] Gate 0: 四大裁判文件 SHA256 绝对只读一致")

    # 2. AST 与反废话文案门禁
    gui_txt = (BASE / "app_gui.py").read_text(encoding="utf-8")
    brief_txt = (BASE / "ui_daily_brief.py").read_text(encoding="utf-8")
    api_txt = (BASE / "api_server.py").read_text(encoding="utf-8")

    for fname, src_txt in [("app_gui.py", gui_txt), ("ui_daily_brief.py", brief_txt), ("api_server.py", api_txt)]:
        ast.parse(src_txt, filename=fname)

    for fname, src_txt in [("app_gui.py", gui_txt), ("ui_daily_brief.py", brief_txt)]:
        tree = ast.parse(src_txt, filename=fname)
        long_btns = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in ("button", "form_submit_button"):
                arg = node.args[0] if node.args else None
                if arg is None:
                    for kw in node.keywords:
                        if kw.arg == "label":
                            arg = kw.value
                lbl = ast.unparse(arg) if arg else ""
                cjk_cnt = len(_CJK_RE.findall(lbl))
                if cjk_cnt > 8 or "(" in lbl or "（" in lbl:
                    long_btns.append((node.lineno, lbl, cjk_cnt))
        assert not long_btns, f"{fname} 存在超过8字或含括号的废话长按钮: {long_btns}"

    assert "每日极简投顾" not in gui_txt, "app_gui.py 仍残留割裂的「每日极简投顾」模式开关"
    for tab_lbl in ['"持仓"', '"调仓"', '"复盘"', '"工具"']:
        assert tab_lbl in gui_txt, f"app_gui.py 缺少统一主标签: {tab_lbl}"
    print("  [PASS] Gate 1: 反废话文案门禁 (app_gui & ui_daily_brief 0 个长按钮, 统一 4 大主标签)")

    # 3. API v1 全链路 7 组契约与零污染门禁
    from fastapi.testclient import TestClient
    import api_server
    client = TestClient(api_server.app)

    r_ov = client.get("/api/v1/overview")
    assert r_ov.status_code == 200, f"/api/v1/overview 失败: {r_ov.text}"
    d_ov = r_ov.json()
    for k in ("total_equity", "today_est_pnl", "market_verdict", "indices", "data_health", "valuation_mae"):
        assert k in d_ov, f"/api/v1/overview 缺少字段: {k}"
    _check_pure_json("/api/v1/overview", d_ov)
    assert client.get("/api/v1/overview?ledger_id=nonexistent_999").status_code == 404

    r_h = client.get("/api/v1/holdings")
    assert r_h.status_code == 200
    d_h = r_h.json()
    assert d_h.get("count", 0) > 0 and "redemption_fee_status" in d_h["items"][0] and "risk_tags" in d_h["items"][0]
    _check_pure_json("/api/v1/holdings", d_h)

    r_reb = client.get("/api/v1/rebalance")
    assert r_reb.status_code == 200
    d_reb = r_reb.json()
    assert "groups" in d_reb and "quota_split_plans" in d_reb and "cheat_sheet_text" in d_reb
    _check_pure_json("/api/v1/rebalance", d_reb)

    r_cf = client.post("/api/v1/cashflow/plan", json={"monthly_new_cash": 3000.0, "plan_months": 3, "rigid_reserve": 500.0})
    assert r_cf.status_code == 200
    d_cf = r_cf.json()
    assert "liquidity_guard" in d_cf and "dca_plan" in d_cf and "left_side_bullets" in d_cf
    _check_pure_json("/api/v1/cashflow/plan", d_cf)

    r_aud = client.get("/api/v1/audit/trackers")
    assert r_aud.status_code == 200
    d_aud = r_aud.json()
    assert "shadow_tracker" in d_aud and "forward_audit" in d_aud
    _check_pure_json("/api/v1/audit/trackers", d_aud)

    r_bk = client.get("/api/v1/backups")
    assert r_bk.status_code == 200 and isinstance(r_bk.json().get("snapshots"), list)
    _check_pure_json("/api/v1/backups", r_bk.json())
    assert client.post("/api/v1/backups/restore", json={"snapshot_id": "invalid_snap_id_xxx"}).status_code == 400

    r_txt = client.post("/api/v1/import/text", json={"text": "005561 创金合信红利低波A 10000元", "mode": "preview"})
    assert r_txt.status_code == 200 and r_txt.json().get("applied") is False
    _check_pure_json("/api/v1/import/text", r_txt.json())

    buf = io.BytesIO()
    Image.new("RGB", (100, 100), color="white").save(buf, format="PNG")
    buf.seek(0)
    r_ocr = client.post(
        "/api/v1/import/ocr",
        files={"file": ("test.png", buf, "image/png")},
        data={"mode": "preview"},
    )
    assert r_ocr.status_code == 200 and r_ocr.json().get("applied") is False and "items" in r_ocr.json()
    _check_pure_json("/api/v1/import/ocr", r_ocr.json())
    print("  [PASS] Gate 2: API v1 全部 7 组接口 HTTP 200、404/400 容错、0 HTML 与 0 Emoji 污染")

    # 4. Playwright 双端真机无异常渲染门禁
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for label, vp in [("desktop_1440", {"width": 1440, "height": 900}), ("mobile_390", {"width": 390, "height": 844})]:
            page = browser.new_page(viewport=vp)
            page.goto("http://127.0.0.1:8501", timeout=30000)
            try:
                page.wait_for_selector("text=免赎碎片尾仓", timeout=35000)
            except Exception:
                page.wait_for_timeout(5000)
            page.wait_for_timeout(1500)
            exc_cnt = page.locator('[data-testid="stException"]').count()
            assert exc_cnt == 0, f"[{label}] 出现 {exc_cnt} 个 Streamlit 异常红框"
            body = page.inner_text("body")
            full_dom_text = page.locator("body").text_content() or ""
            for must_kw in ["总资产", "持仓", "调仓", "复盘", "工具", "¥562.89"]:
                assert must_kw in body, f"[{label}] 页面缺少核心元素: {must_kw}"
            for bad_kw in ["每日极简投顾", "🧹 🧹", "TypeError", "Traceback", "¥442.70", "💼 持仓总资产"]:
                assert bad_kw not in body, f"[{label}] 页面出现非法残留文本: {bad_kw}"
            assert "¥442.70" not in full_dom_text, f"[{label}] 折叠抽屉内部仍残留旧尾仓金额 ¥442.70"

            # (A) Material Symbols 图标字体不被 .stApp span 覆盖
            icon_fonts = page.evaluate("""() => {
                const icons = Array.from(document.querySelectorAll('[data-testid="stIconMaterial"], .material-symbols-rounded'));
                return icons.map(el => ({
                    text: el.textContent,
                    fontFamily: window.getComputedStyle(el).fontFamily
                }));
            }""")
            assert len(icon_fonts) > 0, f"[{label}] 未检测到 Material Symbols 图标元素"
            for ic in icon_fonts:
                assert "Material Symbols Rounded" in ic["fontFamily"], f"[{label}] Material 图标字体被覆盖: {ic}"

            # (B) 切换至「实时持仓明细」时隐藏底部 4 个调仓执行按钮
            page.locator("label:has-text('📋 实时持仓明细')").first.click()
            try:
                page.wait_for_selector("text=实时持仓资产明细", timeout=15000)
            except Exception:
                page.wait_for_selector("text=移动端 4 列极简持仓表", timeout=15000)
            page.wait_for_timeout(1500)
            for btn_lbl in ["确认执行", "清扫尾仓", "等待尾盘", "提前执行", "保存预案"]:
                assert page.locator(f"button:has-text('{btn_lbl}'):visible").count() == 0, f"[{label}] 实时持仓明细视图下仍残留调仓执行按钮: {btn_lbl}"

            # (C) 复盘 Tab 校验：历史时光机默认折叠、无裸 **历史环境类比**、无自相矛盾超额文案
            page.get_by_role("tab", name="复盘").first.click()
            page.wait_for_timeout(2500)
            body_t3 = page.inner_text("body")
            assert "**历史环境类比**" not in body_t3, f"[{label}] 复盘 Tab 仍残留未解析 Markdown 星号 **历史环境类比**"
            assert "历史环境类比" in body_t3, f"[{label}] 复盘 Tab 缺少历史环境类比文案"
            assert not ("平均相对超额 -" in body_t3 and "明显战胜纯宽基基准" in body_t3), f"[{label}] 复盘 Tab 存在负超额却宣称明显战胜基准的自相矛盾文案"
            tm_open = page.evaluate("""() => {
                const details = Array.from(document.querySelectorAll('details'));
                const tm = details.find(d => d.textContent.includes('历史时光机'));
                return tm ? tm.hasAttribute('open') : null;
            }""")
            assert tm_open is False, f"[{label}] 复盘 Tab 历史时光机未默认收起 (open={tm_open})"

            # (D) 工具 Tab 校验：四象限散点图静态标签 <= 6 个，热力图轴标签 <= 6 字
            page.get_by_role("tab", name="工具").first.click()
            page.wait_for_timeout(2500)
            quad_check = page.evaluate("""() => {
                const plots = Array.from(document.querySelectorAll('.js-plotly-plot'));
                let nonEmptyLabels = 0;
                let heatTicks = [];
                for (const p of plots) {
                    if (p.data) {
                        for (const tr of p.data) {
                            if (tr.mode && tr.mode.includes('text') && Array.isArray(tr.text)) {
                                nonEmptyLabels += tr.text.filter(t => t && String(t).trim().length > 0).length;
                            }
                            if (tr.type === 'heatmap' && p.layout && p.layout.yaxis && p.layout.yaxis.ticktext) {
                                heatTicks = p.layout.yaxis.ticktext;
                            }
                        }
                    }
                }
                return { nonEmptyLabels, heatTicks };
            }""")
            assert 0 < quad_check["nonEmptyLabels"] <= 6, f"[{label}] 四象限散点静态标签数量超出 6 个: {quad_check}"
            for ht in quad_check["heatTicks"]:
                assert len(str(ht)) <= 6, f"[{label}] 热力图轴标签超过 6 字: {ht}"
            page.close()
        browser.close()
    print("  [PASS] Gate 3: Playwright 双端浏览器渲染零异常、统一 4 主标签就绪")
    print("ALL G33 CONCISE-UI & API v1 GATES PASSED")


if __name__ == "__main__":
    run_g33_gate()
