# -*- coding: utf-8 -*-
"""
scripts/walkthrough_g10.py
G10 Generation Playwright Visual & Layout Verification Script
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
    print("=== G10 Visual Walkthrough Starting ===")
    if not check_health():
        print("ERROR: Service not healthy on 8501")
        sys.exit(1)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # 1. 1920x1080 Desktop Viewport
        print("--- 1. Testing 1920x1080 Desktop Viewport ---")
        ctx = browser.new_context(viewport={"width": 1920, "height": 1080}, color_scheme="light")
        page = ctx.new_page()
        page.goto("http://127.0.0.1:8501", wait_until="networkidle")
        page.wait_for_selector('[data-testid="stTab"]', timeout=30000)
        page.wait_for_timeout(3000)

        # Check Top 3 cards text for wrapping
        page_text = page.inner_text("body")
        has_drone = "无人机" in page_text or "沙特" in page_text or "导弹" in page_text
        print(f"  [Check 1] Irrelevant military news (drone/Saudi): {has_drone} (Must be False)")

        has_36_cvar = "-36.1%" in page_text
        print(f"  [Check 2] Right wing contains -36.1% CVaR: {has_36_cvar} (Must be False)")

        # Check Tab position
        tab_box = page.locator('[data-testid="stTabs"]').first.bounding_box()
        if tab_box:
            print(f"  [Check 3] Tabs Y coordinate: {tab_box['y']:.1f}px (Must be < 500px in 1080p)")

        # Screenshot 1920x1080 full & viewport
        ss_1080p = SCREENSHOT_DIR / "g10_desktop_1080p_main.png"
        page.screenshot(path=str(ss_1080p), full_page=False)
        print(f"  Saved screenshot: {ss_1080p}")

        # Check Tabs
        tabs = page.locator('[data-testid="stTabs"]').first.locator('[data-testid="stTab"]')
        tab_count = tabs.count()
        print(f"  Total tabs: {tab_count}")

        # Click Tab 1
        if tab_count >= 1:
            tabs.nth(0).click()
            page.wait_for_timeout(1500)
            ss_tab1 = SCREENSHOT_DIR / "g10_desktop_tab1.png"
            page.screenshot(path=str(ss_tab1), full_page=False)
            print(f"  Saved Tab 1 screenshot: {ss_tab1}")

        # Click Tab 2
        if tab_count >= 2:
            tabs.nth(1).click()
            page.wait_for_timeout(1500)
            ss_tab2 = SCREENSHOT_DIR / "g10_desktop_tab2.png"
            page.screenshot(path=str(ss_tab2), full_page=False)
            print(f"  Saved Tab 2 screenshot: {ss_tab2}")

        # Click Tab 3
        if tab_count >= 3:
            tabs.nth(2).click()
            page.wait_for_timeout(1500)
            ss_tab3 = SCREENSHOT_DIR / "g10_desktop_tab3.png"
            page.screenshot(path=str(ss_tab3), full_page=False)
            print(f"  Saved Tab 3 screenshot: {ss_tab3}")

        # Click Tab 4
        if tab_count >= 4:
            tabs.nth(3).click()
            page.wait_for_timeout(1500)
            ss_tab4 = SCREENSHOT_DIR / "g10_desktop_tab4.png"
            page.screenshot(path=str(ss_tab4), full_page=False)
            print(f"  Saved Tab 4 screenshot: {ss_tab4}")

        # 2. 640px Mobile Viewport
        print("--- 2. Testing 640px Mobile Viewport ---")
        ctx_mobile = browser.new_context(viewport={"width": 640, "height": 1136}, color_scheme="light")
        page_m = ctx_mobile.new_page()
        page_m.goto("http://127.0.0.1:8501", wait_until="networkidle")
        page_m.wait_for_selector('[data-testid="stTab"]', timeout=30000)
        page_m.wait_for_timeout(2500)

        overflow = page_m.evaluate("document.documentElement.scrollWidth > window.innerWidth")
        print(f"  [Mobile Check] Has horizontal overflow: {overflow} (Must be False)")

        ss_m = SCREENSHOT_DIR / "g10_mobile_640.png"
        page_m.screenshot(path=str(ss_m), full_page=False)
        print(f"  Saved mobile screenshot: {ss_m}")

        browser.close()
        print("=== G10 Walkthrough Successfully Completed ===")


if __name__ == "__main__":
    main()
