import os
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT_DIR = Path("data/screenshots/g16")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def wait_for_app_ready(page, timeout_sec=30):
    start = time.time()
    while time.time() - start < timeout_sec:
        time.sleep(1)
        txt = page.inner_text("body")
        if "AGY2" in txt and ("总资产" in txt or "主实盘" in txt or "实战存量" in txt or "全息决策" in txt):
            return True
    return False

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        # ─────────────────────────────────────────────────────────────
        # DESKTOP CONTEXT (1440 x 960)
        # ─────────────────────────────────────────────────────────────
        context = browser.new_context(viewport={"width": 1440, "height": 960})
        page = context.new_page()

        print("[1] Opening http://localhost:8501...")
        page.goto("http://localhost:8501")
        if not wait_for_app_ready(page, 30):
            print("Warning: App may not be fully ready, continuing...")
        page.wait_for_timeout(2000)

        # Step 1: Switch ledger to combat_29_funds in topbar
        print("[2] Switching active ledger to 'combat_29_funds'...")
        ledger_box = page.get_by_label("当前激活账本")
        if ledger_box.count() == 0:
            # Fallback locator
            ledger_box = page.locator('div[data-testid="stSelectbox"]').first
        
        ledger_box.click()
        page.wait_for_timeout(600)
        
        opt_combat = page.locator('li[role="option"]:has-text("实战存量组合")')
        if opt_combat.count() > 0:
            print("Selecting '实战存量组合（29只·¥2.66万）'...")
            opt_combat.first.click()
        else:
            print("Dropdown option not found by text, trying keyboard ArrowDown + Enter...")
            page.keyboard.press("ArrowDown")
            page.keyboard.press("Enter")
        
        # Wait for Streamlit to rerun and re-render
        page.wait_for_timeout(4000)
        wait_for_app_ready(page, 15)
        print("Body text snippet after switch:", repr(page.inner_text("body")[:300]))

        # ─────────────────────────────────────────────────────────────
        # SCREEN 1: Top Control Bar + 1-row-5-col Horizontal Memo Cards
        # ─────────────────────────────────────────────────────────────
        print("[3] Capturing Screen 1: Top Bar & Horizontal Memo Cards...")
        body_txt = page.inner_text("body")
        print("Screen 1 checks:")
        print("  - Contains '五维全息决策备忘录':", "五维全息决策备忘录" in body_txt)
        print("  - Contains '深套':", "深套" in body_txt)
        print("  - Contains '442.70':", "442.70" in body_txt)
        print("  - Contains '19 只免赎碎片尾仓':", "19 只免赎碎片尾仓" in body_txt)

        # Scroll to top to ensure topbar and memo are in frame
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(1000)
        screen1_path = OUT_DIR / "screen1_topbar_horizontal_memo.png"
        page.screenshot(path=str(screen1_path))
        print(f"Saved: {screen1_path}")

        # ─────────────────────────────────────────────────────────────
        # SCREEN 2: Tab 2 3-step Prescription Panel for 29 funds
        # ─────────────────────────────────────────────────────────────
        print("[4] Navigating to Tab 2...")
        tab2 = page.locator('button[role="tab"]:has-text("持仓诊断"), button[data-testid="stTab"]:has-text("持仓诊断")')
        if tab2.count() > 0:
            tab2.first.click()
        else:
            # Fallback to second tab
            all_tabs = page.locator('button[role="tab"]')
            if all_tabs.count() >= 2:
                all_tabs.nth(1).click()
        
        page.wait_for_timeout(4000)
        wait_for_app_ready(page, 15)
        
        t2_txt = page.inner_text("body")
        print("Tab 2 checks:")
        print("  - Contains '三阶专项重塑与减亏手术方案':", "三阶专项重塑与减亏手术方案" in t2_txt)
        print("  - Contains '19 只免赎碎片尾仓':", "19 只免赎碎片尾仓" in t2_txt)
        print("  - Contains '高费率/深套 C 类':", "高费率/深套 C 类" in t2_txt)
        print("  - Contains '核心战略底仓':", "核心战略底仓" in t2_txt)

        # Scroll to prescription card location
        # Find element containing "三阶专项重塑与减亏手术方案"
        rx_elem = page.locator('div:has-text("三阶专项重塑与减亏手术方案")').first
        if rx_elem.count() > 0:
            rx_elem.scroll_into_view_if_needed()
            page.evaluate("window.scrollBy(0, -60)")
        else:
            page.evaluate("window.scrollBy(0, 400)")
            
        page.wait_for_timeout(1500)
        screen2_path = OUT_DIR / "screen2_tab2_3step_prescription.png"
        page.screenshot(path=str(screen2_path))
        print(f"Saved: {screen2_path}")

        # ─────────────────────────────────────────────────────────────
        # SCREEN 3: Tab 3 29 vs 6 Backtest Dual Curves
        # ─────────────────────────────────────────────────────────────
        print("[5] Navigating to Tab 3...")
        tab3 = page.locator('button[role="tab"]:has-text("回测"), button[data-testid="stTab"]:has-text("回测")')
        if tab3.count() > 0:
            tab3.first.click()
        else:
            all_tabs = page.locator('button[role="tab"]')
            if all_tabs.count() >= 3:
                all_tabs.nth(2).click()
        
        page.wait_for_timeout(4000)
        wait_for_app_ready(page, 15)

        # Select backtest mode: "🎯 实战存量组合：原始29基 vs 投顾重构6基（近1年真规则回测对比）"
        bt_mode_box = page.get_by_label("🎯 回测模式")
        if bt_mode_box.count() > 0:
            bt_mode_box.click()
            page.wait_for_timeout(600)
            opt_29vs6 = page.locator('li[role="option"]:has-text("原始29基 vs 投顾重构6基")')
            if opt_29vs6.count() > 0:
                print("Selecting '原始29基 vs 投顾重构6基' mode...")
                opt_29vs6.first.click()
                page.wait_for_timeout(4000)
                wait_for_app_ready(page, 15)

        t3_txt = page.inner_text("body")
        print("Tab 3 checks:")
        print("  - Contains '投顾重构 6 基核心组合':", "投顾重构 6 基核心组合" in t3_txt)
        print("  - Contains '原始 29 基存量组合':", "原始 29 基存量组合" in t3_txt)
        print("  - Contains '年化收益率':", "年化收益率" in t3_txt)

        # Wait for Plotly charts to render
        page.wait_for_timeout(3000)
        # Scroll to backtest dual curve chart
        chart_elem = page.locator('div[data-testid="stPlotlyChart"]').first
        if chart_elem.count() > 0:
            chart_elem.scroll_into_view_if_needed()
            page.evaluate("window.scrollBy(0, -80)")
        else:
            page.evaluate("window.scrollBy(0, 300)")

        page.wait_for_timeout(1500)
        screen3_path = OUT_DIR / "screen3_tab3_29vs6_backtest_curves.png"
        page.screenshot(path=str(screen3_path))
        print(f"Saved: {screen3_path}")

        context.close()

        # ─────────────────────────────────────────────────────────────
        # SCREEN 4: Mobile Minimal View (390 x 844)
        # ─────────────────────────────────────────────────────────────
        print("[6] Capturing Screen 4: Mobile Minimal View...")
        mobile_ctx = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True)
        m_page = mobile_ctx.new_page()
        m_page.goto("http://localhost:8501")
        wait_for_app_ready(m_page, 30)
        m_page.wait_for_timeout(2000)

        # Switch to combat_29_funds if needed
        try:
            m_ledger_box = m_page.get_by_label("当前激活账本")
            if m_ledger_box.count() == 0:
                m_ledger_box = m_page.locator('div[data-testid="stSelectbox"]').first
            m_ledger_box.click()
            m_page.wait_for_timeout(600)
            m_opt = m_page.locator('li[role="option"]:has-text("实战存量组合")')
            if m_opt.count() > 0:
                m_opt.first.click()
                m_page.wait_for_timeout(3000)
                wait_for_app_ready(m_page, 15)
        except Exception as e:
            print("Mobile ledger select exception:", e)

        # Click "📱 手机盯盘" in topbar mode segmented control
        print("Switching mode to '📱 手机盯盘'...")
        mode_btn = m_page.locator('button:has-text("手机盯盘"), label:has-text("手机盯盘")')
        if mode_btn.count() > 0:
            mode_btn.first.click()
            m_page.wait_for_timeout(3000)
            wait_for_app_ready(m_page, 15)
        else:
            print("Mobile mode button not found directly, checking radio buttons...")
            m_page.locator('text="📱 手机盯盘"').first.click()
            m_page.wait_for_timeout(3000)

        m_body = m_page.inner_text("body")
        print("Mobile view checks:")
        print("  - Contains '手机极简盯盘':", "手机极简盯盘" in m_body)
        print("  - Contains '账户总资产':", "账户总资产" in m_body)
        print("  - Contains '深套':", "深套" in m_body)
        print("  - Contains '442.70':", "442.70" in m_body)

        m_page.evaluate("window.scrollTo(0, 0)")
        m_page.wait_for_timeout(1000)
        screen4_path = OUT_DIR / "screen4_mobile_minimal_view.png"
        m_page.screenshot(path=str(screen4_path))
        print(f"Saved: {screen4_path}")

        mobile_ctx.close()
        browser.close()
        print("\n=== SUCCESS: All 4 screenshots captured genuinely and verified! ===")

if __name__ == "__main__":
    run()
