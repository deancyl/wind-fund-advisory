# -*- coding: utf-8 -*-
"""
scripts/walkthrough_g11.py
G11 Generation Playwright Visual & Three-Block Minimalist Architecture Verification Script
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
    print("=== G11 Three-Block Architecture Visual Walkthrough Starting ===")
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

        # Check Page Content
        page_text = page.inner_text("body")

        # Check 1: 独立行动总开关横幅是否已删除（不应再作为独立横幅）
        has_drone = "无人机" in page_text or "沙特" in page_text or "导弹" in page_text
        print(f"  [Check 1] Irrelevant military news (drone/Saudi): {has_drone} (Must be False)")

        # Check 2: Tabs Y 坐标
        tab_box = page.locator('[data-testid="stTabs"]').first.bounding_box()
        if tab_box:
            tabs_y = tab_box['y']
            print(f"  [Check 2] Main Tabs Y coordinate: {tabs_y:.1f}px (Target < 300px in 1080p for instant visibility)")

        # Screenshot 1920x1080 full & viewport
        ss_1080p = SCREENSHOT_DIR / "g11_desktop_1080p_main.png"
        page.screenshot(path=str(ss_1080p), full_page=False)
        print(f"  Saved screenshot: {ss_1080p}")

        # Check Tabs
        tabs = page.locator('[data-testid="stTabs"]').first.locator('[data-testid="stTab"]')
        tab_count = tabs.count()
        print(f"  Total tabs: {tab_count}")

        # Click Tab 1 (新资建仓)
        if tab_count >= 1:
            tabs.nth(0).click()
            page.wait_for_timeout(2000)

            tab1_text = page.inner_text("body")
            has_step_capsule = "Step 1" in tab1_text or "第一步" in tab1_text
            print(f"  [Tab 1 Check] Step capsule present: {has_step_capsule} (Must be False in Three-Block)")

            ss_tab1 = SCREENSHOT_DIR / "g11_desktop_tab1.png"
            page.screenshot(path=str(ss_tab1), full_page=False)
            print(f"  Saved Tab 1 screenshot: {ss_tab1}")

        # Click Tab 2 (持仓调仓)
        if tab_count >= 2:
            tabs.nth(1).click()
            page.wait_for_timeout(2000)

            tab2_text = page.inner_text("body")
            has_popover_record = "极速录基" in tab2_text or "录基" in tab2_text or "录入" in tab2_text
            print(f"  [Tab 2 Check] Quick fund recording present: {has_popover_record} (Must be True)")

            ss_tab2 = SCREENSHOT_DIR / "g11_desktop_tab2.png"
            page.screenshot(path=str(ss_tab2), full_page=False)
            print(f"  Saved Tab 2 screenshot: {ss_tab2}")

        # 2. 640px Mobile Viewport
        print("--- 2. Testing 640px Mobile Viewport ---")
        ctx_mobile = browser.new_context(viewport={"width": 640, "height": 1136}, color_scheme="light")
        page_m = ctx_mobile.new_page()
        page_m.goto("http://127.0.0.1:8501", wait_until="networkidle")
        page_m.wait_for_selector('[data-testid="stTab"]', timeout=30000)
        page_m.wait_for_timeout(3000)

        ss_mobile = SCREENSHOT_DIR / "g11_mobile_640.png"
        page_m.screenshot(path=str(ss_mobile), full_page=False)
        print(f"  Saved Mobile screenshot: {ss_mobile}")

        browser.close()
    print("=== G11 Visual Walkthrough Complete ===")


if __name__ == "__main__":
    main()
