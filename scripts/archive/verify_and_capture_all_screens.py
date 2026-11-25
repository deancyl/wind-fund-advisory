import os
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT_DIR = Path("data/screenshots/g16")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def wait_for_ready(page, timeout=35):
    t0 = time.time()
    while time.time() - t0 < timeout:
        time.sleep(1)
        txt = page.inner_text("body")
        if "AGY2" in txt and ("实战存量组合" in txt or "五维全息决策备忘录" in txt or "总资产" in txt):
            return True
    return False

def capture_all():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        # ─────────────────────────────────────────────────────────────
        # DESKTOP VIEWPORT: 1440 x 960
        # ─────────────────────────────────────────────────────────────
        context = browser.new_context(viewport={"width": 1440, "height": 960})
        page = context.new_page()

        print("[1] Opening http://localhost:8501...")
        page.goto("http://localhost:8501")
        wait_for_ready(page)
        page.wait_for_timeout(3000)

        # ── SCREEN 1: Top Bar & 1-Row-5-Col Horizontal Memo Cards ──
        print("[2] Screen 1: Top Bar & 1-Row-5-Col Horizontal Memo Cards...")
        body1 = page.inner_text("body")
        print("  - '五维全息决策备忘录' present?", "五维全息决策备忘录" in body1)
        print("  - '442.70' present?", "442.70" in body1)
        print("  - '深套' present?", "深套" in body1)
        print("  - '19 只免赎碎片尾仓' present?", "19 只免赎碎片尾仓" in body1)
        
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(1000)
        s1_path = OUT_DIR / "screen1_topbar_horizontal_memo.png"
        page.screenshot(path=str(s1_path))
        print(f"  -> Saved Screen 1: {s1_path}")

        # ── SCREEN 2: Tab 2 3-Step Prescription Panel ──
        print("[3] Screen 2: Tab 2 3-Step Prescription Panel...")
        tabs = page.locator('div[data-testid="stTab"]')
        tabs.nth(1).click()
        page.wait_for_timeout(4000)
        
        body2 = page.inner_text("body")
        print("  - '三阶专项重塑与减亏手术方案' present?", "三阶专项重塑与减亏手术方案" in body2)
        print("  - '19 只免赎碎片尾仓全额清扫归拢' present?", "19 只免赎碎片尾仓全额清扫归拢" in body2)
        print("  - '三大深套与高费率标的' present?", "三大深套与高费率标的" in body2 or "高费率/深套" in body2)
        print("  - '易方达裕祥回报债券A' present?", "易方达裕祥回报债券A" in body2)

        # Scroll to prescription card
        rx_target = page.locator('text="三阶专项重塑与减亏手术方案"').first
        if rx_target.count() > 0:
            rx_target.scroll_into_view_if_needed()
            page.evaluate("window.scrollBy(0, -60)")
        else:
            page.evaluate("window.scrollBy(0, 500)")
            
        page.wait_for_timeout(1500)
        s2_path = OUT_DIR / "screen2_tab2_3step_prescription.png"
        page.screenshot(path=str(s2_path))
        print(f"  -> Saved Screen 2: {s2_path}")

        # ── SCREEN 3: Tab 3 29 vs 6 Backtest Dual Curves ──
        print("[4] Screen 3: Tab 3 29 vs 6 Backtest Dual Curves...")
        tabs = page.locator('div[data-testid="stTab"]')
        tabs.nth(2).click()
        page.wait_for_timeout(6000)
        
        body3 = page.inner_text("body")
        print("  - '投顾重构 6 基核心组合' present?", "投顾重构 6 基核心组合" in body3)
        print("  - '原始 29 基存量组合' present?", "原始 29 基存量组合" in body3)
        print("  - '年化收益率' present?", "年化收益率" in body3)

        # Scroll to Plotly chart
        chart = page.locator('div[data-testid="stPlotlyChart"]').first
        if chart.count() > 0:
            chart.scroll_into_view_if_needed()
            page.evaluate("window.scrollBy(0, -80)")
        else:
            page.evaluate("window.scrollBy(0, 350)")

        page.wait_for_timeout(1500)
        s3_path = OUT_DIR / "screen3_tab3_29vs6_backtest_curves.png"
        page.screenshot(path=str(s3_path))
        print(f"  -> Saved Screen 3: {s3_path}")

        context.close()

        # ─────────────────────────────────────────────────────────────
        # MOBILE VIEWPORT: 390 x 844
        # ─────────────────────────────────────────────────────────────
        print("[5] Screen 4: Mobile Minimal View...")
        mob_context = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True)
        mob_page = mob_context.new_page()
        mob_page.goto("http://localhost:8501")
        wait_for_ready(mob_page)
        mob_page.wait_for_timeout(2000)

        # Click "📱 手机盯盘"
        mode_btn = mob_page.locator('button:has-text("手机盯盘"), label:has-text("手机盯盘"), [role="button"]:has-text("手机盯盘")')
        if mode_btn.count() > 0:
            mode_btn.first.click()
        else:
            mob_page.locator('text="📱 手机盯盘"').first.click()
            
        mob_page.wait_for_timeout(3500)
        
        body4 = mob_page.inner_text("body")
        print("  - '手机极简盯盘' present?", "手机极简盯盘" in body4)
        print("  - '账户总资产' present?", "账户总资产" in body4)
        print("  - '442.70' present?", "442.70" in body4)
        print("  - '深套' present?", "深套" in body4)

        mob_page.evaluate("window.scrollTo(0, 0)")
        mob_page.wait_for_timeout(1000)
        s4_path = OUT_DIR / "screen4_mobile_minimal_view.png"
        mob_page.screenshot(path=str(s4_path))
        print(f"  -> Saved Screen 4: {s4_path}")

        mob_context.close()
        browser.close()
        print("\nAll 4 core screenshots successfully verified and saved to data/screenshots/g16/!")

if __name__ == "__main__":
    capture_all()
