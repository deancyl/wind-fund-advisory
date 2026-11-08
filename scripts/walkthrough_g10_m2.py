# -*- coding: utf-8 -*-
"""
scripts/walkthrough_g10_m2.py
Milestone M2 Service Health & Multimodal Visual/Logic Walkthrough
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
REPORT_FILE = WORKSPACE_ROOT / ".agents" / "teamwork" / "worker_g10_m2" / "walkthrough_results.json"


def check_health_endpoint() -> dict:
    url = "http://127.0.0.1:8501/_stcore/health"
    print(f"=== 1. Probing Health Endpoint: {url} ===")
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            status = resp.status
            body = resp.read().decode("utf-8")
            print(f"Health check status: {status}, body: {body.strip()}")
            return {"status": status, "body": body.strip(), "ok": (status == 200 and body.strip() == "ok")}
    except Exception as e:
        print(f"Health check failed: {e}")
        return {"status": -1, "body": str(e), "ok": False}


def run_apptest_verification() -> dict:
    print("=== 2. Running Streamlit AppTest Runtime Verification ===")
    from streamlit.testing.v1 import AppTest
    gui_file = str(WORKSPACE_ROOT / "AGY2_FundAdvisory" / "app_gui.py")
    
    t0 = time.time()
    at = AppTest.from_file(gui_file, default_timeout=50)
    at.run()
    dur = time.time() - t0
    
    exceptions = [str(exc.value) for exc in at.exception] if at.exception else []
    success = len(exceptions) == 0
    print(f"AppTest run completed in {dur:.2f}s, exceptions: {len(exceptions)}")
    if exceptions:
        for exc in exceptions:
            print(f"  Exception: {exc}")
    else:
        print("  0 exceptions! AppTest mounted cleanly.")
        
    return {
        "duration_sec": round(dur, 2),
        "exception_count": len(exceptions),
        "exceptions": exceptions,
        "success": success
    }


def run_playwright_walkthrough() -> dict:
    print("=== 3. Running Playwright Multimodal Visual & Logic Walkthrough ===")
    results = {
        "desktop_light": {},
        "desktop_dark": {},
        "mobile_640_dark": {},
        "components_detected": {},
        "commonmark_leak_detected": False,
        "overflow_detected": False,
        "screenshots": []
    }
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        # -------------------------------------------------------------
        # A. Desktop Light Mode (1280x900)
        # -------------------------------------------------------------
        print("--- A. Desktop Light Mode (1280x900) ---")
        ctx_light = browser.new_context(
            viewport={"width": 1280, "height": 900},
            color_scheme="light"
        )
        page_light = ctx_light.new_page()
        page_light.goto("http://127.0.0.1:8501", wait_until="networkidle")
        
        # Explicitly wait for Streamlit app to finish rendering tabs
        page_light.wait_for_selector('[data-testid="stTab"]', timeout=35000)
        page_light.wait_for_timeout(2000)
        
        # Verify right wing col_sentry G10 components
        sentry_has_corr = page_light.locator("text=相关性").first.count() > 0
        sentry_has_stress = page_light.locator("text=穿透式蒙特卡洛压力测试").first.count() > 0
        sentry_has_cvar = page_light.locator("text=极限 CVaR 99%").first.count() > 0
        sentry_has_liq_days = page_light.locator("text=变现天数 (加权)").first.count() > 0
        
        print(f"  Right Wing col_sentry: corr_card={sentry_has_corr}, stress_card={sentry_has_stress}, cvar={sentry_has_cvar}, liq_days={sentry_has_liq_days}")
        results["components_detected"]["col_sentry_corr_card"] = sentry_has_corr
        results["components_detected"]["col_sentry_stress_card"] = sentry_has_stress
        results["components_detected"]["col_sentry_cvar_metric"] = sentry_has_cvar
        results["components_detected"]["col_sentry_liq_days_metric"] = sentry_has_liq_days
        
        shot_desk_light_main = str(SCREENSHOT_DIR / "g10_desktop_light_main.png")
        page_light.screenshot(path=shot_desk_light_main, full_page=False)
        results["screenshots"].append(shot_desk_light_main)
        
        # Check Tab 1: 新资建仓
        tab_buttons = page_light.locator('[data-testid="stTab"]')
        tab_count = tab_buttons.count()
        print(f"  Tabs detected: {tab_count}")
        
        if tab_count >= 1:
            tab_buttons.nth(0).click()
            page_light.wait_for_timeout(2500)
            tab1_mc3d_exp = page_light.locator("text=查看蒙特卡洛极端承压 3D 分布曲面图").first
            tab1_has_mc3d = tab1_mc3d_exp.count() > 0
            if tab1_has_mc3d:
                try:
                    tab1_mc3d_exp.scroll_into_view_if_needed()
                    tab1_mc3d_exp.click()
                    page_light.wait_for_timeout(1000)
                except Exception as e:
                    print(f"    Tab 1 mc3d click notice: {e}")
            
            shot_tab1_light = str(SCREENSHOT_DIR / "g10_desktop_light_tab1.png")
            page_light.screenshot(path=shot_tab1_light, full_page=False)
            results["screenshots"].append(shot_tab1_light)
            results["components_detected"]["tab1_mc3d_expander"] = tab1_has_mc3d
            print(f"  Tab 1: mc3d_chart_expander={tab1_has_mc3d}")
            
        # Check Tab 2: 持仓调仓
        if tab_count >= 2:
            tab_buttons.nth(1).click()
            page_light.wait_for_timeout(2500)
            
            tab2_mc3d_exp = page_light.locator("text=查看蒙特卡洛极端承压 3D 分布曲面图").first
            tab2_has_mc3d = tab2_mc3d_exp.count() > 0
            if tab2_has_mc3d:
                try:
                    tab2_mc3d_exp.scroll_into_view_if_needed()
                    tab2_mc3d_exp.click()
                    page_light.wait_for_timeout(1000)
                except Exception as e:
                    print(f"    Tab 2 mc3d click notice: {e}")
                    
            tab2_has_cushion = page_light.locator("text=浮盈安全垫").first.count() > 0 or page_light.locator("text=安全垫").first.count() > 0
            
            shot_tab2_light = str(SCREENSHOT_DIR / "g10_desktop_light_tab2.png")
            page_light.screenshot(path=shot_tab2_light, full_page=False)
            results["screenshots"].append(shot_tab2_light)
            results["components_detected"]["tab2_mc3d_expander"] = tab2_has_mc3d
            results["components_detected"]["tab2_cushion_card"] = tab2_has_cushion
            print(f"  Tab 2: mc3d_chart_expander={tab2_has_mc3d}, cushion_card={tab2_has_cushion}")
            
        ctx_light.close()
        
        # -------------------------------------------------------------
        # B. Desktop Dark Mode (1280x900)
        # -------------------------------------------------------------
        print("--- B. Desktop Dark Mode (1280x900) ---")
        ctx_dark = browser.new_context(
            viewport={"width": 1280, "height": 900},
            color_scheme="dark"
        )
        page_dark = ctx_dark.new_page()
        page_dark.goto("http://127.0.0.1:8501", wait_until="networkidle")
        page_dark.wait_for_selector('[data-testid="stTab"]', timeout=35000)
        page_dark.wait_for_timeout(2000)
        
        shot_desk_dark_main = str(SCREENSHOT_DIR / "g10_desktop_dark_main.png")
        page_dark.screenshot(path=shot_desk_dark_main, full_page=False)
        results["screenshots"].append(shot_desk_dark_main)
        
        # Check Tab 2 in dark mode
        dark_tab_buttons = page_dark.locator('[data-testid="stTab"]')
        if dark_tab_buttons.count() >= 2:
            dark_tab_buttons.nth(1).click()
            page_dark.wait_for_timeout(2000)
            shot_desk_dark_tab2 = str(SCREENSHOT_DIR / "g10_desktop_dark_tab2.png")
            page_dark.screenshot(path=shot_desk_dark_tab2, full_page=False)
            results["screenshots"].append(shot_desk_dark_tab2)
            
        ctx_dark.close()
        
        # -------------------------------------------------------------
        # C. Mobile 640px Responsive Layout (640x960)
        # -------------------------------------------------------------
        print("--- C. Mobile 640px Responsive Layout (640x960) ---")
        ctx_mobile = browser.new_context(
            viewport={"width": 640, "height": 960},
            color_scheme="dark",
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15"
        )
        page_mob = ctx_mobile.new_page()
        page_mob.goto("http://127.0.0.1:8501", wait_until="networkidle")
        page_mob.wait_for_selector('[data-testid="stTab"]', timeout=35000)
        page_mob.wait_for_timeout(2000)
        
        # Measure geometry on main page
        geom_mob_main = page_mob.evaluate("""() => {
            const el = document.documentElement;
            const body = document.body;
            return {
                clientWidth: el.clientWidth,
                scrollWidth: el.scrollWidth,
                bodyClientWidth: body.clientWidth,
                bodyScrollWidth: body.scrollWidth,
                hasOverflow: (el.scrollWidth > el.clientWidth + 1) || (body.scrollWidth > body.clientWidth + 1)
            };
        }""")
        print(f"  Mobile 640px main geometry: {geom_mob_main}")
        results["mobile_640_dark"]["main_geometry"] = geom_mob_main
        if geom_mob_main["hasOverflow"]:
            results["overflow_detected"] = True
            
        shot_mob_main = str(SCREENSHOT_DIR / "g10_mobile_640_main.png")
        page_mob.screenshot(path=shot_mob_main, full_page=False)
        results["screenshots"].append(shot_mob_main)
        
        # Check all tabs in mobile view for overflow and CommonMark leak
        mob_tab_buttons = page_mob.locator('[data-testid="stTab"]')
        tab_names = ["tab1_new", "tab2_rebal", "tab3_backtest", "tab4_tools"]
        for idx in range(min(mob_tab_buttons.count(), 4)):
            mob_tab_buttons.nth(idx).click()
            page_mob.wait_for_timeout(2000)
            
            tab_geom = page_mob.evaluate("""() => {
                const el = document.documentElement;
                return {
                    clientWidth: el.clientWidth,
                    scrollWidth: el.scrollWidth,
                    overflow: el.scrollWidth > el.clientWidth + 1
                };
            }""")
            print(f"  Mobile Tab {idx+1} ({tab_names[idx]}) geometry: {tab_geom}")
            if tab_geom["overflow"]:
                results["overflow_detected"] = True
                
            shot_mob_tab = str(SCREENSHOT_DIR / f"g10_mobile_640_{tab_names[idx]}.png")
            page_mob.screenshot(path=shot_mob_tab, full_page=False)
            results["screenshots"].append(shot_mob_tab)
            
        # CommonMark 4+ space indented code block leak scan
        leak_info = page_mob.evaluate("""() => {
            const codeBlocks = Array.from(document.querySelectorAll('pre code, code'));
            const leaked = [];
            for (const b of codeBlocks) {
                const text = b.innerText || "";
                if (text.includes('<div') || text.includes('class="decision-card"') || text.includes('style="border-left')) {
                    leaked.push(text.substring(0, 100));
                }
            }
            return {
                leakedCount: leaked.length,
                snippets: leaked
            };
        }""")
        print(f"  CommonMark 4+ Space Leak Check: leaked_count={leak_info['leakedCount']}")
        if leak_info["leakedCount"] > 0:
            results["commonmark_leak_detected"] = True
            print(f"  WARNING: Leaked code snippets found: {leak_info['snippets']}")
        else:
            print("  SUCCESS: 0 CommonMark 4+ space code block leaks! HTML pure and clean.")
            
        results["commonmark_check"] = leak_info
        ctx_mobile.close()
        browser.close()
        
    return results


def main():
    t_start = time.time()
    health_res = check_health_endpoint()
    apptest_res = run_apptest_verification()
    walkthrough_res = run_playwright_walkthrough()
    total_time = round(time.time() - t_start, 2)
    
    full_report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_walkthrough_time_sec": total_time,
        "health_endpoint": health_res,
        "apptest_verification": apptest_res,
        "visual_walkthrough": walkthrough_res,
        "milestone_m2_status": "PASSED" if (
            health_res["ok"] and
            apptest_res["success"] and
            not walkthrough_res["overflow_detected"] and
            not walkthrough_res["commonmark_leak_detected"]
        ) else "FAILED"
    }
    
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(full_report, f, ensure_ascii=False, indent=2)
        
    print(f"\n=======================================================")
    print(f"M2 Full Walkthrough Report written to: {REPORT_FILE}")
    print(f"Milestone M2 Status: {full_report['milestone_m2_status']}")
    print(f"=======================================================")


if __name__ == "__main__":
    main()
