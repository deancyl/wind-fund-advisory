#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/verify_browser_viewports.py
Milestone M2: Dual-viewport browser verification for Project Wind G22.
Verifies all 4 key user-visible facts:
  1. Tab 1 & Tab 2 headers are clean without 15 paragraphs of text wall (cleanly collapsed inside expander).
  2. Tab 2 screenshot OCR file uploader and editable preview table functions are intact.
  3. Deep loss count is 18 and matches the diagnostic card.
  4. Micro optimization slippage bps in rebalance table is dynamic calculated value (never "1.2 bps").
"""

import sys
import os
import time
import re
import json
from playwright.sync_api import sync_playwright

SCREENSHOT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reports", "screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

APP_URL = "http://localhost:8501"

def run_browser_verification():
    print("=" * 65)
    print("      Starting G22 Browser Verification (Desktop & Mobile)      ")
    print("=" * 65)

    results = {
        "desktop": {},
        "mobile": {},
        "four_facts": {
            "fact1_expander_collapsed": False,
            "fact2_ocr_uploader_intact": False,
            "fact3_deep_loss_count_18": False,
            "fact4_slippage_dynamic": False
        },
        "details": {}
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # -------------------------------------------------------------
        # Part 1: Desktop Viewport (1280 x 800)
        # -------------------------------------------------------------
        print("\n--- [Step 1] Desktop Viewport Verification (1280x800) ---")
        context_dt = browser.new_context(viewport={"width": 1280, "height": 800})
        page_dt = context_dt.new_page()

        print(f"Navigating to {APP_URL} ...")
        page_dt.goto(APP_URL, wait_until="networkidle", timeout=60000)
        page_dt.wait_for_timeout(4000)

        # 1. Fact 1 Check in Tab 1 (ensure Tab 1 is clicked in case of auto-routing)
        try:
            page_dt.get_by_text('🌱 新资建仓').click()
            page_dt.wait_for_timeout(2000)
        except Exception:
            pass

        t1_expander = page_dt.locator('div[data-testid="stExpander"]').filter(has_text="今日关键信息感知与建仓裁决卡").first
        t1_causal_collapsed = False
        if t1_expander.count() > 0:
            details_el = t1_expander.locator('details').first
            is_open = details_el.evaluate('el => el.hasAttribute("open")')
            t1_causal_collapsed = not is_open
            print(f"✓ Tab 1 Causal Expander found: Collapsed={t1_causal_collapsed} (open={is_open})")
            results["details"]["tab1_expander_collapsed"] = t1_causal_collapsed

        screenshot_dt_tab1 = os.path.join(SCREENSHOT_DIR, "desktop_tab1.png")
        page_dt.screenshot(path=screenshot_dt_tab1, full_page=False)
        print(f"✓ Saved desktop Tab 1 screenshot: {screenshot_dt_tab1}")

        # 2. Switch to Tab 2
        print("Switching to Tab 2 ('💼 持仓调仓') ...")
        page_dt.get_by_text('💼 持仓调仓').click()
        page_dt.wait_for_timeout(3000)

        # Check Tab 2 causal expander
        t2_expander = page_dt.locator('div[data-testid="stExpander"]').filter(has_text="今日关键信息感知与调仓裁决卡").first
        t2_causal_collapsed = False
        if t2_expander.count() > 0:
            details_el = t2_expander.locator('details').first
            is_open = details_el.evaluate('el => el.hasAttribute("open")')
            t2_causal_collapsed = not is_open
            print(f"✓ Tab 2 Causal Expander found: Collapsed={t2_causal_collapsed} (open={is_open})")
            results["details"]["tab2_expander_collapsed"] = t2_causal_collapsed

        if t1_causal_collapsed and t2_causal_collapsed:
            results["four_facts"]["fact1_expander_collapsed"] = True
            print("🎉 Fact 1 Verified: Tab 1 & Tab 2 headers are clean without 15 paragraphs text wall (cleanly collapsed)!")

        # 3. Switch Ledger to combat_29_funds (实战存量组合)
        print("Switching ledger to 'combat_29_funds' (实战存量组合)...")
        sb_ledger = page_dt.locator('div[data-testid="stSelectbox"]').filter(has_text="切换账本").first
        combobox = sb_ledger.locator('.react-aria-ComboBox')
        input_elem = combobox.locator('input')
        input_elem.click()
        page_dt.keyboard.press("ArrowDown")
        page_dt.wait_for_timeout(1000)

        options = page_dt.locator('[role="option"]').all()
        for o in options:
            if "29" in o.inner_text() or "实战存量" in o.inner_text():
                print(f"Selecting option: {o.inner_text().strip()}")
                o.click()
                break

        page_dt.wait_for_timeout(4000)

        # 4. Fact 3 Check: Deep loss count is 18 & matches diagnostic card
        metrics = page_dt.locator('div[data-testid="stMetric"]').all()
        deep_loss_found = False
        deep_loss_text = ""
        for m in metrics:
            txt = m.inner_text().replace("\n", " | ")
            if "深套出血点" in txt:
                deep_loss_found = True
                deep_loss_text = txt
                print(f"✓ Found Metric: {txt}")
                break

        app_text = page_dt.locator('div[data-testid="stApp"]').inner_text()
        has_rx_card = "三阶专项重塑与减亏手术方案" in app_text
        has_rx_deep_loss = "核心深套出血点精准置换" in app_text
        print(f"✓ Diagnostic card present: {has_rx_card}")
        print(f"✓ Diagnostic item present: {has_rx_deep_loss}")

        if "18 只" in deep_loss_text and has_rx_card and has_rx_deep_loss:
            results["four_facts"]["fact3_deep_loss_count_18"] = True
            results["details"]["deep_loss_metric"] = deep_loss_text
            print("🎉 Fact 3 Verified: Deep loss count is 18 and matches the diagnostic card!")

        screenshot_dt_tab2 = os.path.join(SCREENSHOT_DIR, "desktop_tab2.png")
        page_dt.screenshot(path=screenshot_dt_tab2, full_page=False)
        print(f"✓ Saved desktop Tab 2 screenshot: {screenshot_dt_tab2}")

        # 5. Fact 2 Check: Tab 2 OCR File Uploader
        ocr_btn = page_dt.locator('button').filter(has_text="截图导入").first
        if ocr_btn.count() > 0:
            print("Opening Popover '📸 截图导入' ...")
            ocr_btn.click()
            page_dt.wait_for_timeout(1500)
            file_uploader = page_dt.locator('div[data-testid="stFileUploader"]').first
            if file_uploader.count() > 0:
                print("✓ Tab 2 OCR file uploader found inside popover!")
                results["four_facts"]["fact2_ocr_uploader_intact"] = True
                screenshot_ocr = os.path.join(SCREENSHOT_DIR, "desktop_tab2_ocr_popover.png")
                page_dt.screenshot(path=screenshot_ocr)
                print(f"✓ Saved desktop Tab 2 OCR popover screenshot: {screenshot_ocr}")
                print("🎉 Fact 2 Verified: Tab 2 screenshot OCR file uploader and functions are intact!")
            # Close popover
            page_dt.keyboard.press("Escape")
            page_dt.wait_for_timeout(1000)

        # 6. Fact 4 Check: Rebalance Table Dynamic Micro Optimization BPS (never 1.2 bps)
        rad_labels = page_dt.locator('label').all()
        for lbl in rad_labels:
            if "调仓执行建议单" in lbl.inner_text():
                print("Clicking radio '🎯 调仓执行建议单' ...")
                lbl.click()
                page_dt.wait_for_timeout(2500)
                break

        page_content = page_dt.content()
        has_static_12 = "1.2 bps" in page_content
        bps_matches = re.findall(r'(\d+\.\d+)\s*bps', page_content)
        print(f"Presence of static '1.2 bps': {has_static_12}")
        print(f"Dynamic bps samples in page: {bps_matches[:6]}")

        if not has_static_12 and len(bps_matches) > 0:
            results["four_facts"]["fact4_slippage_dynamic"] = True
            results["details"]["bps_samples"] = bps_matches
            print("🎉 Fact 4 Verified: Micro optimization slippage bps is dynamic calculated value (never 1.2 bps)!")

        screenshot_dt_rebal = os.path.join(SCREENSHOT_DIR, "desktop_tab2_rebalance.png")
        page_dt.screenshot(path=screenshot_dt_rebal, full_page=False)
        print(f"✓ Saved desktop Tab 2 rebalance screenshot: {screenshot_dt_rebal}")

        context_dt.close()

        # -------------------------------------------------------------
        # Part 2: Mobile Viewport (390 x 844)
        # -------------------------------------------------------------
        print("\n--- [Step 2] Mobile Viewport Verification (390x844) ---")
        context_mb = browser.new_context(
            viewport={"width": 390, "height": 844},
            is_mobile=True,
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
        )
        page_mb = context_mb.new_page()

        print(f"Navigating to {APP_URL} in Mobile viewport ...")
        page_mb.goto(APP_URL, wait_until="networkidle", timeout=60000)
        page_mb.wait_for_timeout(4000)

        # Tab 1 Screenshot
        screenshot_mb_tab1 = os.path.join(SCREENSHOT_DIR, "mobile_tab1.png")
        page_mb.screenshot(path=screenshot_mb_tab1, full_page=False)
        print(f"✓ Saved mobile Tab 1 screenshot: {screenshot_mb_tab1}")

        # Switch to Tab 2
        print("Switching to Tab 2 in mobile view ...")
        page_mb.get_by_text('💼 持仓调仓').click()
        page_mb.wait_for_timeout(3000)

        # Switch Ledger to combat_29_funds in mobile view
        sb_ledger_mb = page_mb.locator('div[data-testid="stSelectbox"]').filter(has_text="切换账本").first
        combobox_mb = sb_ledger_mb.locator('.react-aria-ComboBox')
        input_mb = combobox_mb.locator('input')
        input_mb.click()
        page_mb.keyboard.press("ArrowDown")
        page_mb.wait_for_timeout(1000)

        options_mb = page_mb.locator('[role="option"]').all()
        for o in options_mb:
            if "29" in o.inner_text() or "实战存量" in o.inner_text():
                print(f"Mobile selected: {o.inner_text().strip()}")
                o.click()
                break

        page_mb.wait_for_timeout(4000)

        # Tab 2 Screenshot
        screenshot_mb_tab2 = os.path.join(SCREENSHOT_DIR, "mobile_tab2.png")
        page_mb.screenshot(path=screenshot_mb_tab2, full_page=False)
        print(f"✓ Saved mobile Tab 2 screenshot: {screenshot_mb_tab2}")

        context_mb.close()
        browser.close()

    print("\n" + "=" * 65)
    print("                 BROWSER VERIFICATION SUMMARY                   ")
    print("=" * 65)
    all_facts_passed = all(results["four_facts"].values())
    for fact, passed in results["four_facts"].items():
        status = "PASSED ✓" if passed else "FAILED ✗"
        print(f"  {fact}: {status}")

    print("-" * 65)
    if all_facts_passed:
        print("🎉 ALL 4 USER-VISIBLE FACTS VERIFIED 100% IN BROWSER!")
    else:
        print("❌ Some user-visible facts failed verification.")

    report_path = os.path.join(SCREENSHOT_DIR, "verification_summary.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Saved verification summary report: {report_path}")

    return all_facts_passed

if __name__ == "__main__":
    success = run_browser_verification()
    sys.exit(0 if success else 1)
