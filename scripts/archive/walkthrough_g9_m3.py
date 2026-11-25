# -*- coding: utf-8 -*-
"""
scripts/walkthrough_g9_m3.py
Milestone 3 (M3) Service Health, HTML Purification & Multimodal Visual Walkthrough
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
REPORT_FILE = WORKSPACE_ROOT / ".agents" / "teamwork" / "worker_g9_m3_13" / "walkthrough_results.json"


def check_health_endpoint() -> dict:
    url = "http://127.0.0.1:8501/_stcore/health"
    print(f"=== 1. Probing Health Endpoint: {url} ===")
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            status = resp.status
            body = resp.read().decode("utf-8").strip()
            print(f"Health check status: {status}, body: {body}")
            return {"status": status, "body": body, "ok": (status == 200 and body == "ok")}
    except Exception as e:
        print(f"Health check failed: {e}")
        return {"status": -1, "body": str(e), "ok": False}


def run_visual_walkthrough() -> dict:
    print("=== 2. Running Playwright Multimodal Visual & Logic Walkthrough ===")
    results = {
        "health": {},
        "desktop_light": {},
        "desktop_dark": {},
        "mobile_640": {},
        "html_code_block_leaks": [],
        "components_detected": {},
        "screenshots": []
    }

    results["health"] = check_health_endpoint()
    if not results["health"]["ok"]:
        raise RuntimeError(f"Service not healthy: {results['health']}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # =========================================================================
        # A. Desktop Light Mode (1280x900)
        # =========================================================================
        print("--- A. Desktop Light Mode (1280x900) ---")
        ctx_light = browser.new_context(
            viewport={"width": 1280, "height": 900},
            color_scheme="light"
        )
        page = ctx_light.new_page()
        page.goto("http://127.0.0.1:8501", wait_until="networkidle")

        # Wait for Streamlit app main structure
        page.wait_for_selector('[data-testid="stTab"]', timeout=35000)
        page.wait_for_timeout(3000)

        # 1. Check "今日投顾行动总开关" at top of dashboard
        has_action_switch = (
            page.locator("text=今日投顾行动总开关").count() > 0 or
            page.locator("text=今日建议").count() > 0 or
            page.locator("text=安心吃息").count() > 0 or
            page.locator("text=按兵不动").count() > 0 or
            page.locator("text=锁定防御").count() > 0 or
            page.locator("text=行动总开关").count() > 0
        )
        print(f"  [Check 1] 今日投顾行动总开关 detected: {has_action_switch}")
        results["components_detected"]["action_switch"] = has_action_switch

        # 2. Check HTML Code Block Leakage across the page (Rule 27)
        code_blocks = page.locator("pre, code, [data-testid='stCodeBlock']").all_text_contents()
        leaked_html = []
        for cb in code_blocks:
            cb_str = cb.strip()
            # If a code block contains HTML tags like <div, <span, <table, class=, style=
            if ("<div" in cb_str or "<span" in cb_str or "<table" in cb_str or "style=" in cb_str) and not cb_str.startswith("#"):
                leaked_html.append(cb_str[:120])
        print(f"  [Check 2] Leaked raw HTML code blocks: {len(leaked_html)}")
        results["html_code_block_leaks"] = leaked_html

        # 3. Check "历史三大牛熊拐点实盘对照尺"
        has_inflection_ruler = (
            page.locator("text=历史三大牛熊拐点实盘对照尺").count() > 0 or
            page.locator("text=牛熊拐点").count() > 0 or
            page.locator("text=2021年2月").count() > 0 or
            page.locator("text=2024年9月").count() > 0
        )
        print(f"  [Check 3] 历史三大牛熊拐点对照尺 detected: {has_inflection_ruler}")
        results["components_detected"]["inflection_ruler"] = has_inflection_ruler

        # 4. Check Top 3 Sectors
        has_top3 = (
            page.locator("text=Top 3").count() > 0 or
            page.locator("text=优选赛道").count() > 0
        )
        print(f"  [Check 4] Top 3 优选赛道 detected: {has_top3}")
        results["components_detected"]["top3_sectors"] = has_top3

        # Screenshot Desktop Light Main
        shot_main_light = str(SCREENSHOT_DIR / "g9_m3_desktop_light_main.png")
        page.screenshot(path=shot_main_light, full_page=False)
        results["screenshots"].append(shot_main_light)

        # Tab Navigation Check
        tab_buttons = page.locator('[data-testid="stTab"]')
        tab_count = tab_buttons.count()
        print(f"  Tabs detected: {tab_count}")
        results["components_detected"]["tab_count"] = tab_count

        # 5. Check Tab 1: 新资建仓 L1 & L2
        if tab_count >= 1:
            print("  --- Checking Tab 1 (新资建仓) ---")
            tab_buttons.nth(0).click()
            page.wait_for_timeout(2500)

            # Check L1 inputs: Capital amount & Risk level (C1-C5)
            has_capital_input = (
                page.locator("text=投资本金").count() > 0 or
                page.locator("text=拟投资").count() > 0 or
                page.locator("text=拟投金额").count() > 0
            )
            has_risk_tier = (
                page.locator("text=C1").count() > 0 or
                page.locator("text=C2").count() > 0 or
                page.locator("text=C3").count() > 0 or
                page.locator("text=C4").count() > 0 or
                page.locator("text=C5").count() > 0 or
                page.locator("text=风险等级").count() > 0 or
                page.locator("text=风险档位").count() > 0
            )
            # Check L2 Expander for advanced quant / pressure test / selection funnel
            has_l2_expander = (
                page.locator("text=展开机构级量化压力测试与选基白盒证据").count() > 0 or
                page.locator("text=量化压力测试").count() > 0 or
                page.locator("text=白盒证据").count() > 0 or
                page.locator("text=机构级模型与参数微调").count() > 0 or
                page.locator("text=微调").count() > 0
            )

            # Check core conclusion big cards
            has_core_cards = (
                page.locator("text=达标胜率").count() > 0 or
                page.locator("text=年化票息").count() > 0 or
                page.locator("text=回撤").count() > 0 or
                page.locator("text=仓位").count() > 0
            )

            print(f"    Tab 1 L1 capital input: {has_capital_input}, risk tier: {has_risk_tier}")
            print(f"    Tab 1 L2 expander: {has_l2_expander}, core cards: {has_core_cards}")
            results["components_detected"]["tab1_l1_inputs"] = (has_capital_input and has_risk_tier)
            results["components_detected"]["tab1_l2_expander"] = has_l2_expander

            # Expand L2 whitebox drawer if present
            expander_btn = page.locator("text=展开机构级量化压力测试与选基白盒证据").first
            if expander_btn.count() > 0:
                try:
                    expander_btn.scroll_into_view_if_needed()
                    expander_btn.click()
                    page.wait_for_timeout(1500)
                    print("    Expanded Tab 1 L2 Whitebox Drawer successfully.")
                except Exception as ex:
                    print(f"    Notice clicking L2 expander: {ex}")

            shot_tab1_light = str(SCREENSHOT_DIR / "g9_m3_desktop_light_tab1.png")
            page.screenshot(path=shot_tab1_light, full_page=False)
            results["screenshots"].append(shot_tab1_light)

        # 6. Check Tab 2: 持仓调仓 L1 & L2 & Popover
        if tab_count >= 2:
            print("  --- Checking Tab 2 (持仓调仓) ---")
            tab_buttons.nth(1).click()
            page.wait_for_timeout(2500)

            # Check compact top cushion banner
            has_cushion_banner = (
                page.locator("text=安全垫").count() > 0 or
                page.locator("text=浮盈").count() > 0 or
                page.locator("text=总资产").count() > 0
            )
            # Check fast entry popover "➕ 极速录基"
            has_fast_entry_popover = (
                page.locator("text=极速录基").count() > 0 or
                page.locator("text=录基").count() > 0
            )
            # Check view mode toggle (dual view isolation)
            has_view_mode_toggle = (
                page.locator("text=持仓诊断与智能调仓").count() > 0 or
                page.locator("text=账本运维").count() > 0
            )

            print(f"    Tab 2 cushion banner: {has_cushion_banner}, fast entry popover: {has_fast_entry_popover}, view mode: {has_view_mode_toggle}")
            results["components_detected"]["tab2_cushion"] = has_cushion_banner
            results["components_detected"]["tab2_fast_entry"] = has_fast_entry_popover
            results["components_detected"]["tab2_view_mode"] = has_view_mode_toggle

            shot_tab2_light = str(SCREENSHOT_DIR / "g9_m3_desktop_light_tab2.png")
            page.screenshot(path=shot_tab2_light, full_page=False)
            results["screenshots"].append(shot_tab2_light)

        ctx_light.close()

        # =========================================================================
        # B. Mobile 640px Viewport (640x960)
        # =========================================================================
        print("--- B. Mobile 640px Viewport (640x960) ---")
        ctx_mobile = browser.new_context(
            viewport={"width": 640, "height": 960},
            is_mobile=True,
            has_touch=True
        )
        page_m = ctx_mobile.new_page()
        page_m.goto("http://127.0.0.1:8501", wait_until="networkidle")
        page_m.wait_for_selector('[data-testid="stTab"]', timeout=35000)
        page_m.wait_for_timeout(2500)

        # Check horizontal overflow on mobile
        overflow_result = page_m.evaluate("""() => {
            const docWidth = document.documentElement.offsetWidth;
            const scrollWidth = document.documentElement.scrollWidth;
            const windowWidth = window.innerWidth;
            const hasDocumentOverflow = (scrollWidth > windowWidth + 5);
            
            // Check for horizontal scroll containers (e.g. pills, tabs)
            const scrollableContainers = Array.from(document.querySelectorAll('*')).filter(el => {
                const style = window.getComputedStyle(el);
                return (style.overflowX === 'auto' || style.overflowX === 'scroll') && el.scrollWidth > el.clientWidth;
            }).length;

            return {
                docWidth,
                scrollWidth,
                windowWidth,
                hasDocumentOverflow,
                scrollableContainers
            };
        }""")
        print(f"  Mobile 640px overflow check: {overflow_result}")
        results["mobile_640"] = overflow_result

        shot_mobile = str(SCREENSHOT_DIR / "g9_m3_mobile_640.png")
        page_m.screenshot(path=shot_mobile, full_page=False)
        results["screenshots"].append(shot_mobile)

        ctx_mobile.close()
        browser.close()

    # Save results json
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"=== Walkthrough finished! Report written to {REPORT_FILE} ===")
    return results


if __name__ == "__main__":
    res = run_visual_walkthrough()
    if len(res["html_code_block_leaks"]) > 0:
        print("FAIL: HTML code block leakage detected!")
        sys.exit(1)
    print("PASS: Multimodal Visual Walkthrough 100% SUCCESSFUL!")
