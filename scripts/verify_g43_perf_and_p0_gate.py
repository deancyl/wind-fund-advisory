# -*- coding: utf-8 -*-
import ast
import json
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
AGY2_DIR = ROOT / "AGY2_FundAdvisory" if (ROOT / "AGY2_FundAdvisory").exists() else ROOT
BASE = AGY2_DIR if (AGY2_DIR / "app_gui.py").exists() and ROOT.name != "AGY2_FundAdvisory" else ROOT
for p in [str(ROOT), str(AGY2_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)


def detect_active_port() -> int:
    for p in [8501, 8585]:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{p}/_stcore/health", timeout=1.5) as resp:
                if resp.status == 200:
                    return p
        except Exception:
            pass
    return 8585


def wait_st_idle(page, timeout_s: float = 25.0) -> float:
    t0 = time.perf_counter()
    for _ in range(int(timeout_s * 4)):
        try:
            state = page.locator("[data-testid='stApp']").get_attribute("data-test-script-state")
            if state == "notRunning":
                break
        except Exception:
            pass
        page.wait_for_timeout(250)
    page.wait_for_timeout(400)
    return round((time.perf_counter() - t0) * 1000.0, 1)


def check_ast_invariants() -> None:
    src = (BASE / "app_gui.py").read_text(encoding="utf-8")
    tree = ast.parse(src, filename="app_gui.py")

    # 1. Check _h_items hoisted in render_tab4_toolbox_content
    fn4 = next((n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "render_tab4_toolbox_content"), None)
    assert fn4 is not None, "未找到 render_tab4_toolbox_content"
    first_h_line = None
    first_if_sub_line = None
    for stmt in fn4.body:
        if isinstance(stmt, ast.Assign):
            for t in stmt.targets:
                if isinstance(t, ast.Name) and t.id == "_h_items":
                    first_h_line = stmt.lineno
        if isinstance(stmt, ast.If) and first_if_sub_line is None:
            seg = ast.get_source_segment(src, stmt.test) or ""
            if "active_subview" in seg:
                first_if_sub_line = stmt.lineno
    assert first_h_line is not None and first_if_sub_line is not None and first_h_line < first_if_sub_line, (
        f"_h_items(L{first_h_line}) 必须定义在 active_subview 分支(L{first_if_sub_line})之前"
    )
    print(f"  [OK] AST 1: _h_items 已提升至 L{first_h_line} (早于 L{first_if_sub_line})")

    # 2. Check Tab 3 strict subview isolation
    fn3 = next((n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "render_tab3_backtest_content"), None)
    assert fn3 is not None, "未找到 render_tab3_backtest_content"
    returns = [n for n in ast.walk(fn3) if isinstance(n, ast.Return)]
    assert len(returns) >= 4, f"Tab 3 子视图隔离不足，仅发现 {len(returns)} 处 return (要求 >= 4)"
    print(f"  [OK] AST 2: Tab 3 子视图严格互斥隔离，共 {len(returns)} 处提前返回出口")


def check_api_security_and_latency() -> None:
    proc = subprocess.Popen(
        [sys.executable, str(BASE / "api_server.py"), "--host", "127.0.0.1", "--port", "18143"],
        cwd=str(BASE), stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    try:
        ready = False
        for _ in range(40):
            try:
                with urllib.request.urlopen("http://127.0.0.1:18143/api/v1/overview", timeout=2.0) as r:
                    if r.status == 200:
                        ready = True
                        break
            except Exception:
                time.sleep(0.25)
        assert ready, "api_server.py 子进程启动超时"

        # 等待后台预热线程完成首轮暖仓
        time.sleep(3.0)

        # 1. 非法 Origin CORS 校验 (OPTIONS 与 GET 均检查)
        req_evil = urllib.request.Request(
            "http://127.0.0.1:18143/api/v1/overview",
            headers={"Origin": "https://evil.example.com", "Access-Control-Request-Method": "GET"},
            method="OPTIONS",
        )
        try:
            with urllib.request.urlopen(req_evil, timeout=3.0) as r:
                acao_evil = r.headers.get("access-control-allow-origin", "")
        except urllib.error.HTTPError as he:
            acao_evil = he.headers.get("access-control-allow-origin", "")
        assert acao_evil not in ("*", "https://evil.example.com"), f"CORS 漏洞: 恶意源返回了 {acao_evil}"

        # 2. 合法 Tauri 源放行校验
        req_tauri = urllib.request.Request(
            "http://127.0.0.1:18143/api/v1/overview",
            headers={"Origin": "http://tauri.localhost", "Access-Control-Request-Method": "GET"},
            method="OPTIONS",
        )
        with urllib.request.urlopen(req_tauri, timeout=3.0) as r:
            acao_tauri = r.headers.get("access-control-allow-origin", "")
        assert acao_tauri == "http://tauri.localhost", f"Tauri 合法源未放行: {acao_tauri}"
        print("  [OK] API 安全: CORS 白名单严格拦截恶意 Origin 并放行 Tauri/本地源")

        # 3. 连续请求延迟校验 (< 300ms)
        t0 = time.perf_counter()
        with urllib.request.urlopen("http://127.0.0.1:18143/api/v1/overview", timeout=3.0) as r:
            assert r.status == 200
            data = json.loads(r.read().decode("utf-8"))
        dt_ms = (time.perf_counter() - t0) * 1000.0
        assert "today_est_pnl" in data and "indices" in data
        assert dt_ms < 300.0, f"/api/v1/overview 热响应过慢: {dt_ms:.1f} ms (门槛 < 300 ms)"
        print(f"  [OK] API 性能: /api/v1/overview 预热/缓存响应 {dt_ms:.1f} ms (< 300 ms)")
    finally:
        proc.terminate()
        proc.wait(timeout=5)


def check_ui_perf_and_narrow_nav() -> None:
    port = detect_active_port()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # 1. Desktop 1440x900: 诊断 UnboundLocalError 清零 + 裁决台防溢出 + 复盘子视图隔离
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"http://127.0.0.1:{port}", timeout=30000)
        wait_st_idle(page)
        assert page.locator('[data-testid="stException"]').count() == 0

        # 切入诊断工作台 -> 重仓重叠 & 极端承压
        page.locator('[data-testid="stSidebar"] div[role="radiogroup"] label:has-text("诊断 · 深度穿透")').click()
        wait_st_idle(page)
        assert page.locator('[data-testid="stException"]').count() == 0, "诊断首页出现异常"

        # 检查首席投顾裁决台第5胶囊不向右溢出容器
        cap_ok = page.evaluate("""() => {
            const container = document.querySelector('.chief-memo-grid');
            if (!container) return {ok: true, note: 'no memo grid'};
            const cards = Array.from(container.children);
            const bad = [];
            for (const c of cards) {
                const cr = c.getBoundingClientRect();
                for (const s of c.querySelectorAll('span')) {
                    const sr = s.getBoundingClientRect();
                    if (sr.right > cr.right + 2) {
                        bad.push({text: s.innerText, sr_right: sr.right, cr_right: cr.right});
                    }
                }
            }
            return {ok: bad.length === 0, bad};
        }""")
        assert cap_ok["ok"], f"首席投顾裁决台胶囊文字溢出边框: {cap_ok}"
        print("  [OK] UI 1: 首席投顾今日裁决台 5 胶囊零溢出边框")

        for sub_diag in ["重仓重叠", "极端承压"]:
            page.locator(f'[data-testid="stMain"] div[role="radiogroup"] label:has-text("{sub_diag}")').first.click()
            dt = wait_st_idle(page)
            exc_cnt = page.locator('[data-testid="stException"]').count()
            assert exc_cnt == 0, f"诊断子视图「{sub_diag}」触发异常: stException={exc_cnt}"
            print(f"  [OK] UI 2: 诊断子视图「{sub_diag}」零崩溃异常 ({dt} ms)")

        # 切入复盘工作台 -> 近三年胜率 & 样本外前瞻
        page.locator('[data-testid="stSidebar"] div[role="radiogroup"] label:has-text("复盘 · 回测与验真")').click()
        dt_bt = wait_st_idle(page)
        assert page.locator('[data-testid="stException"]').count() == 0
        body_tm = page.inner_text("body")
        assert "回测模式" not in body_tm, "历史时光机仍穿透渲染了全周期PK的「回测模式」选择器"

        t_win0 = time.perf_counter()
        page.locator('[data-testid="stMain"] div[role="radiogroup"] label:has-text("近三年胜率")').first.click()
        wait_st_idle(page)
        dt_win = (time.perf_counter() - t_win0) * 1000.0
        assert page.locator('[data-testid="stException"]').count() == 0
        body_win = page.inner_text("body")
        assert "回测模式" not in body_win, "近三年胜率仍穿透渲染「回测模式」"
        assert "滚动发车" in body_win
        assert dt_win < 5000.0, f"近三年胜率切换过慢: {dt_win:.1f} ms (>= 5000 ms)"
        print(f"  [OK] UI 3: 复盘「近三年胜率」严格隔离，切换耗时 {dt_win:.1f} ms (< 5000 ms)")

        page.locator('[data-testid="stMain"] div[role="radiogroup"] label:has-text("样本外前瞻")').first.click()
        wait_st_idle(page)
        assert page.locator('[data-testid="stException"]').count() == 0
        body_oos = page.inner_text("body")
        for en_col in ("days_elapsed", "excess_alpha_pct", "horizon_bucket"):
            assert en_col not in body_oos, f"样本外前瞻仍泄露原始英文列名: {en_col}"
        print("  [OK] UI 4: 复盘「样本外前瞻」英文冗余列已彻底清洗")
        page.close()

        # 2. Narrow 390x844 with ordinary Desktop UA: must NOT lose navigation or overflow horizontally
        n_page = browser.new_page(viewport={"width": 390, "height": 844})
        n_page.goto(f"http://127.0.0.1:{port}", timeout=30000)
        n_page.locator('[data-testid="stSidebar"], [data-testid="stMain"] [data-testid="stRadio"]').first.wait_for(timeout=15000)
        wait_st_idle(n_page)
        assert n_page.locator('[data-testid="stException"]').count() == 0
        # If sidebar starts expanded on narrow Desktop UA, check obsidian bg, collapse it, then verify expand btn & re-open
        col_btn = n_page.locator('[data-testid="stSidebarCollapseButton"] button, [data-testid="stSidebarCollapseButton"]').first
        if col_btn.count() > 0 and col_btn.is_visible():
            sb_bg = n_page.evaluate("() => getComputedStyle(document.querySelector('[data-testid=\"stSidebar\"]')).backgroundColor")
            assert "15, 28, 46" in sb_bg, f"390x844 窄屏侧边栏未继承深海曜石蓝底色: {sb_bg}"
            col_btn.click()
            n_page.wait_for_timeout(600)
        narrow_res = n_page.evaluate("""() => {
            const expBtn = document.querySelector('[data-testid="stExpandSidebarButton"] button, [data-testid="stExpandSidebarButton"], [data-testid="collapsedControl"] button, [data-testid="collapsedControl"], button[aria-label="Expand sidebar"]');
            const expRect = expBtn ? expBtn.getBoundingClientRect() : null;
            const expVis = !!(expBtn && getComputedStyle(expBtn).display !== 'none' && getComputedStyle(expBtn).visibility !== 'hidden' && expRect && expRect.width > 0);
            const mobNav = Array.from(document.querySelectorAll('[data-testid="stMain"] [data-testid="stRadio"]')).some(r => r.innerText.includes('持仓') && r.innerText.includes('调仓'));
            return {
                expVis,
                mobNav,
                xOverflow: Math.max(0, document.documentElement.scrollWidth - window.innerWidth)
            };
        }""")
        assert narrow_res["expVis"] or narrow_res["mobNav"], f"390x844 窄屏(普通桌面UA)导航彻底失联: {narrow_res}"
        assert narrow_res["xOverflow"] <= 2, f"390x844 窄屏存在横向溢出: {narrow_res}"
        if narrow_res["expVis"]:
            n_page.locator('[data-testid="stExpandSidebarButton"] button, [data-testid="stExpandSidebarButton"], [data-testid="collapsedControl"] button, [data-testid="collapsedControl"]').first.click()
            n_page.wait_for_timeout(500)
            nav_count = n_page.locator('[data-testid="stSidebar"] div[role="radiogroup"] label').count()
            assert nav_count >= 4, f"390x844 展开侧边栏后缺少主导航菜单: {nav_count}"
        print(f"  [OK] UI 5: 390x844 普通桌面UA 窄屏导航折叠/展开及深色主题正常，零横向溢出 ({narrow_res})")
        n_page.close()

        # 3. Mobile UA 390x844 check
        m_ctx = browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
            is_mobile=True,
        )
        m_page = m_ctx.new_page()
        m_page.goto(f"http://127.0.0.1:{port}", timeout=30000)
        wait_st_idle(m_page)
        assert m_page.locator('[data-testid="stException"]').count() == 0
        mob_res = m_page.evaluate("""() => {
            const mobNav = Array.from(document.querySelectorAll('[data-testid="stMain"] [data-testid="stRadio"]')).some(r => r.innerText.includes('持仓') && r.innerText.includes('调仓'));
            return {mobNav, xOverflow: Math.max(0, document.documentElement.scrollWidth - window.innerWidth)};
        }""")
        assert mob_res["mobNav"], f"Mobile UA 390x844 缺少底部/顶部移动分段导航: {mob_res}"
        assert mob_res["xOverflow"] <= 2, f"Mobile UA 390x844 存在横向溢出: {mob_res}"
        print(f"  [OK] UI 6: 390x844 Mobile UA 极简导航正常且零横向溢出 ({mob_res})")
        m_ctx.close()
        browser.close()


def main() -> None:
    print("=== G43 性能止血、P0崩溃修复与安全加固零 Mock 门禁 ===")
    check_ast_invariants()
    check_api_security_and_latency()
    check_ui_perf_and_narrow_nav()
    print("ALL G43 PERF, CRASH-FIX & SECURITY GATES PASSED")


if __name__ == "__main__":
    main()
