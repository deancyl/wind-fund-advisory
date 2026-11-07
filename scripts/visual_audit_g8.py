# -*- coding: utf-8 -*-
"""
scripts/visual_audit_g8.py
G8 世代买方量化多模态视觉与 UX 金融防错全项实证走查脚本
"""

import sys
import os
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

SCREENSHOT_DIR = Path("data/screenshots/g8_audit")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

def run_g8_audit():
    audit_report = {
        "dual_wing_dashboard": {},
        "html_leak_check": {},
        "tab1_features": {},
        "tab2_isolation": {},
        "mobile_640_geom": {},
        "screenshots": [],
        "passed": False
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            color_scheme="dark"
        )
        page = context.new_page()
        
        print("1. 访问 http://127.0.0.1:8501 ...")
        page.goto("http://127.0.0.1:8501", wait_until="networkidle")
        page.wait_for_timeout(3500)

        # 1. 审核首屏双翼看板
        print("2. 审核首屏双翼看板...")
        c = page.content()
        has_perceive_time = "数据感知时间" in c or "⏱️ 数据感知时间" in c
        has_realtime_news = "实时快讯" in c or "⚡ 实时快讯" in c
        has_selection_reason = "入选依据" in c or "💡 入选依据" in c
        has_sentry = "主动风险预警哨" in c
        has_clean_sentry = "六维主动巡检" in c

        # 检查是否泄漏源码 <div class="inflection-ruler-card" 到 <pre><code> 中
        code_blocks = page.locator("pre code").all_text_contents()
        html_leaked_in_code = any("<div" in cb for cb in code_blocks)
        
        audit_report["dual_wing_dashboard"] = {
            "has_perceive_time": has_perceive_time,
            "has_realtime_news": has_realtime_news,
            "has_selection_reason": has_selection_reason,
            "has_sentry": has_sentry,
            "has_clean_sentry": has_clean_sentry,
        }
        audit_report["html_leak_check"] = {
            "html_leaked_in_code": html_leaked_in_code,
            "code_block_count": len(code_blocks)
        }
        
        shot1 = str(SCREENSHOT_DIR / "g8_screen_header.png")
        page.screenshot(path=shot1, full_page=False)
        audit_report["screenshots"].append(shot1)
        print(f"首屏双翼看板截图保存至: {shot1}")

        # 2. 审核 Tab 1 新资建仓
        print("3. 审核 Tab 1 新资建仓...")
        tab1_locator = page.locator('div[role="tab"]:has-text("新资建仓")')
        if tab1_locator.count() > 0:
            tab1_locator.first.click()
            page.wait_for_timeout(2000)
            tab1_text = page.content()
            has_amount_check = "金额核对" in tab1_text
            audit_report["tab1_features"]["has_amount_check"] = has_amount_check
            shot2 = str(SCREENSHOT_DIR / "g8_tab1_overview.png")
            page.screenshot(path=shot2, full_page=False)
            audit_report["screenshots"].append(shot2)
            print(f"Tab 1 截图保存至: {shot2}")

        # 3. 审核 Tab 2 持仓调仓视图物理隔离
        print("4. 审核 Tab 2 持仓调仓视图真隔离...")
        tab2_locator = page.locator('div[role="tab"]:has-text("持仓调仓")')
        if tab2_locator.count() > 0:
            tab2_locator.first.click()
            page.wait_for_timeout(3000)
            
            # 主流程模式检查
            tab2_main_text = page.content()
            has_cushion = "浮盈安全垫" in tab2_main_text or "安全垫" in tab2_main_text
            has_holdings_table = "持仓总市值" in tab2_main_text or "基金代码" in tab2_main_text or "赎回费状态" in tab2_main_text
            # 确认主流程下不存在底部的工具坞 Expander
            has_dock_expander = "账本运维与实盘复盘工具坞" in tab2_main_text
            
            audit_report["tab2_isolation"]["main_mode"] = {
                "has_cushion": has_cushion,
                "has_holdings_table": has_holdings_table,
                "has_dock_expander_in_main": has_dock_expander
            }
            shot3 = str(SCREENSHOT_DIR / "g8_tab2_main_mode.png")
            page.screenshot(path=shot3, full_page=False)
            audit_report["screenshots"].append(shot3)
            print(f"Tab 2 主流程截图保存至: {shot3}")

            # 切换至宽屏工具坞模式
            radios = page.locator('[data-testid="stRadio"] label')
            dock_radio = None
            for i in range(radios.count()):
                txt = radios.nth(i).text_content()
                if "工具坞" in txt or "复盘档案" in txt:
                    dock_radio = radios.nth(i)
                    break
            
            if dock_radio:
                print("点击切换至【账本运维与实盘复盘档案 (宽屏工具坞)】...")
                dock_radio.click()
                page.wait_for_timeout(3500)
                tab2_dock_text = page.content()
                
                # 宽屏工具坞下，主流程步骤一应被隐藏
                has_step1_hidden = "步骤二：核心标的五维时机裁决" not in tab2_dock_text
                has_dock_subtabs = "FIFO批次解锁透视" in tab2_dock_text or "快速录入/导入持仓" in tab2_dock_text
                
                audit_report["tab2_isolation"]["dock_mode"] = {
                    "has_step1_hidden": has_step1_hidden,
                    "has_dock_subtabs": has_dock_subtabs
                }
                shot4 = str(SCREENSHOT_DIR / "g8_tab2_dock_mode.png")
                page.screenshot(path=shot4, full_page=False)
                audit_report["screenshots"].append(shot4)
                print(f"Tab 2 宽屏工具坞截图保存至: {shot4}")

        # 4. 极端移动端 640px 视口核验
        print("5. 审核 640px 移动端视口几何...")
        context_mobile = browser.new_context(
            viewport={"width": 640, "height": 960},
            color_scheme="dark"
        )
        page_m = context_mobile.new_page()
        page_m.goto("http://127.0.0.1:8501", wait_until="networkidle")
        page_m.wait_for_timeout(3000)
        
        geom = page_m.evaluate("""() => {
            const el = document.documentElement;
            const body = document.body;
            return {
                clientWidth: el.clientWidth,
                scrollWidth: el.scrollWidth,
                bodyClientWidth: body.clientWidth,
                bodyScrollWidth: body.scrollWidth,
                hasOverflow: el.scrollWidth > el.clientWidth + 2
            };
        }""")
        audit_report["mobile_640_geom"] = geom
        shot5 = str(SCREENSHOT_DIR / "g8_mobile_640.png")
        page_m.screenshot(path=shot5, full_page=False)
        audit_report["screenshots"].append(shot5)
        print(f"640px 移动端截图保存至: {shot5}")

        browser.close()

    # 综合判定
    all_ok = (
        not audit_report["html_leak_check"]["html_leaked_in_code"] and
        audit_report["dual_wing_dashboard"]["has_perceive_time"] and
        audit_report["dual_wing_dashboard"]["has_realtime_news"] and
        audit_report["dual_wing_dashboard"]["has_selection_reason"] and
        audit_report["tab1_features"].get("has_amount_check", False) and
        audit_report["tab2_isolation"].get("main_mode", {}).get("has_cushion", False) and
        audit_report["tab2_isolation"].get("main_mode", {}).get("has_holdings_table", False) and
        not audit_report["tab2_isolation"].get("main_mode", {}).get("has_dock_expander_in_main", True) and
        audit_report["tab2_isolation"].get("dock_mode", {}).get("has_step1_hidden", False) and
        audit_report["tab2_isolation"].get("dock_mode", {}).get("has_dock_subtabs", False) and
        not audit_report["mobile_640_geom"].get("hasOverflow", False)
    )
    audit_report["passed"] = all_ok
    print(f"\n==========================================")
    print(f"=== G8 视觉与 UX 审核判定: {'PASSED 100%' if all_ok else 'FAILED'} ===")
    print(f"==========================================\n")
    print(json.dumps(audit_report, ensure_ascii=False, indent=2))
    return audit_report

if __name__ == "__main__":
    report = run_g8_audit()
    if not report["passed"]:
        sys.exit(1)
    print("\nVisual audit completed successfully with zero defects!")
