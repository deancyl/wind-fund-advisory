# -*- coding: utf-8 -*-
"""
scripts/walkthrough_g12.py
G12 Generation Playwright Visual Walkthrough:
1. Three-block minimalist layout & instant first-screen tabs
2. Trailing stop-profit & right-side breakdown alarm
3. 7-dimensional GP rule tree in factor evolution popover
4. Market sentiment temperature & multi-source macro indicators
5. Light / Bloomberg Dark theme & 640px mobile responsiveness
"""

import sys
import os
import json
import time
import urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
SCREENSHOT_DIR = WORKSPACE_ROOT / "data" / "screenshots"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


def check_health():
    url = "http://127.0.0.1:8501/_stcore/health"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            return resp.status == 200 and resp.read().decode("utf-8").strip() == "ok"
    except Exception:
        return False


def main():
    print("=== G12 Visual Walkthrough Starting ===")
    if not check_health():
        print("ERROR: Streamlit service not healthy on port 8501!")
        sys.exit(1)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # 1. 1920x1080 Desktop Viewport (Default Theme)
        print("--- 1. Testing 1920x1080 Desktop Viewport ---")
        ctx = browser.new_context(viewport={"width": 1920, "height": 1080}, color_scheme="light")
        page = ctx.new_page()
        page.goto("http://127.0.0.1:8501", wait_until="networkidle")
        page.wait_for_selector('[data-testid="stTab"]', timeout=30000)
        page.wait_for_timeout(3000)

        # 检查首屏 Tab Y 坐标
        tab_box = page.locator('[data-testid="stTabs"]').first.bounding_box()
        if tab_box:
            tabs_y = tab_box['y']
            print(f"  [G12 Check 1] Main Tabs Y coordinate: {tabs_y:.1f}px (Target < 250px for instant visibility)")

        # 截图首屏
        ss_main = SCREENSHOT_DIR / "g12_desktop_1080p_main.png"
        page.screenshot(path=str(ss_main), full_page=False)
        print(f"  Saved main screen: {ss_main}")

        # 展开双翼智能投顾看板
        page_text = page.inner_text("body")
        print(f"  [G12 Check 2] Page contains action switch/sentry text: {'今日投顾结论' in page_text or '行动总开关' in page_text or '全市场机会雷达' in page_text}")

        # 展开折叠框查看双翼看板
        expander = page.locator('details').first
        if expander.count() > 0:
            expander.click()
            page.wait_for_timeout(2000)

            # 点击 🧬 因子进化 Popover
            popover_btn = page.locator('button:has-text("因子进化")').first
            if popover_btn.count() > 0:
                popover_btn.click()
                page.wait_for_timeout(1500)
                ss_popover = SCREENSHOT_DIR / "g12_desktop_factor_evolution_popover.png"
                page.screenshot(path=str(ss_popover), full_page=False)
                print(f"  Saved factor evolution popover screenshot: {ss_popover}")

        # 切换到 Tab 2 持仓调仓
        tabs = page.locator('[data-testid="stTabs"]').first.locator('[data-testid="stTab"]')
        if tabs.count() >= 2:
            tabs.nth(1).click()
            page.wait_for_timeout(2000)
            ss_tab2 = SCREENSHOT_DIR / "g12_desktop_tab2_holdings.png"
            page.screenshot(path=str(ss_tab2), full_page=False)
            print(f"  Saved Tab 2 screenshot: {ss_tab2}")

        # 2. 640px Mobile Viewport
        print("--- 2. Testing 640px Mobile Viewport ---")
        ctx_mobile = browser.new_context(viewport={"width": 640, "height": 1136}, color_scheme="light")
        page_m = ctx_mobile.new_page()
        page_m.goto("http://127.0.0.1:8501", wait_until="networkidle")
        page_m.wait_for_selector('[data-testid="stTab"]', timeout=30000)
        page_m.wait_for_timeout(3000)

        ss_mobile = SCREENSHOT_DIR / "g12_mobile_640.png"
        page_m.screenshot(path=str(ss_mobile), full_page=False)
        print(f"  Saved mobile screenshot: {ss_mobile}")

        browser.close()

    print("=== G12 Visual Walkthrough Successfully Completed ===")


if __name__ == "__main__":
    main()
