import ast
import urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
AGY2_DIR = ROOT / "AGY2_FundAdvisory"
BASE = AGY2_DIR if (AGY2_DIR / "app_gui.py").exists() else ROOT


def detect_active_port():
    for p in [8501, 8585]:
        try:
            resp = urllib.request.urlopen(f"http://127.0.0.1:{p}/_stcore/health", timeout=1.5)
            if resp.status == 200:
                return p
        except Exception:
            pass
    return 8585


def run_g40_visual_gate():
    gui_txt = (BASE / "app_gui.py").read_text(encoding="utf-8")
    brief_txt = (BASE / "ui_daily_brief.py").read_text(encoding="utf-8")
    ast.parse(gui_txt, filename="app_gui.py")
    ast.parse(brief_txt, filename="ui_daily_brief.py")

    # 1. 代码静态校验：私人银行曜石蓝侧边栏主题、无圆点导航、复选框打卡
    assert "#0F1C2E" in gui_txt, "未注入私人银行深海曜石蓝侧边栏主题令牌"
    assert "tabular-nums" in gui_txt, "未全局启用 tabular-nums 等宽金融数字"
    assert "CheckboxColumn" in brief_txt, "调仓页打卡列尚未升级为真实可勾选 CheckboxColumn"

    active_port = detect_active_port()
    print(f"Connecting to Streamlit on port {active_port}...")

    # 2. Playwright 实机像素级验收 (1440x900 桌面端 + 390x844 手机端)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # 桌面端验收
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        try:
            page.goto(f"http://127.0.0.1:{active_port}", wait_until="networkidle", timeout=30000)
        except Exception:
            page.goto(f"http://127.0.0.1:{active_port}", timeout=30000)
            
        # 等待脚本执行完毕
        for _ in range(25):
            state = page.locator("[data-testid='stApp']").get_attribute("data-test-script-state")
            if state == "notRunning":
                break
            page.wait_for_timeout(1000)
            
        page.wait_for_timeout(2000)
        assert page.locator('[data-testid="stException"]').count() == 0, "桌面端出现红框报错"

        # 核心硬断言 1：侧边栏严禁出现垂直滚动条 (scrollHeight <= clientHeight + 2)
        sb_scroll = page.evaluate("""() => {
            const el = document.querySelector('[data-testid="stSidebar"] > div:first-child');
            if (!el) return {ok: false, reason: 'no sidebar'};
            return {ok: el.scrollHeight <= el.clientHeight + 2, sh: el.scrollHeight, ch: el.clientHeight};
        }""")
        assert sb_scroll["ok"], f"侧边栏仍然可以滚动！scrollHeight={sb_scroll.get('sh')}, clientHeight={sb_scroll.get('ch')}"
        print(f"  [OK] 侧边栏绝对零滚动断言通过: scrollHeight={sb_scroll.get('sh')} <= clientHeight={sb_scroll.get('ch')}")

        # 核心硬断言 2：持仓主视图一屏内可见主蓝色按钮不超过 1 个，避免双主按钮打架
        primary_btns = page.locator('button[kind="primary"]:visible').count()
        assert primary_btns <= 1, f"首屏出现 {primary_btns} 个可见蓝色主按钮争夺焦点，必须仅保留 1 个"
        print(f"  [OK] 单聚焦主按钮断言通过: visible primary_btns count={primary_btns} <= 1")

        # 核心硬断言 3：页面存在清晰的「今日操作路线」引导，让用户一眼知道能干什么
        body = page.inner_text("body")
        assert "今日操作路线" in body, "右栏缺少「今日操作路线」三步行动引导卡"
        print("  [OK] 今日操作路线卡片断言通过")

        page.screenshot(path="g40_desktop_verified.png", full_page=False)
        page.close()

        # 手机端验收
        m_page = browser.new_page(viewport={"width": 390, "height": 844})
        try:
            m_page.goto(f"http://127.0.0.1:{active_port}", wait_until="networkidle", timeout=30000)
        except Exception:
            m_page.goto(f"http://127.0.0.1:{active_port}", timeout=30000)
            
        for _ in range(25):
            state = m_page.locator("[data-testid='stApp']").get_attribute("data-test-script-state")
            if state == "notRunning":
                break
            m_page.wait_for_timeout(1000)
            
        m_page.wait_for_timeout(2000)
        assert m_page.locator('[data-testid="stException"]').count() == 0, "手机端出现红框报错"
        m_page.screenshot(path="g40_mobile_verified.png", full_page=False)
        print("  [OK] 手机端 390x844 视口验收通过: 0 红框报错")
        m_page.close()

        browser.close()

    print("ALL G40 PRIVATE-BANKING AESTHETICS, ZERO-SCROLL SIDEBAR & ACTION-GUIDANCE GATES PASSED")


if __name__ == "__main__":
    run_g40_visual_gate()
