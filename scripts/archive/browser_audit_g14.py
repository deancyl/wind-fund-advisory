# -*- coding: utf-8 -*-
import os
import sys
import time
from playwright.sync_api import sync_playwright

output_dir = "data/audit_screenshots_g14"
os.makedirs(output_dir, exist_ok=True)

def run_audit():
    print("=== STARTING PLAYWRIGHT G14 MULTIMODAL AUDIT ===")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()

        start_t = time.time()
        print("Navigating to http://localhost:8501 ...")
        page.goto("http://localhost:8501", wait_until="networkidle", timeout=30000)
        load_duration = time.time() - start_t
        print(f"Page loaded in {load_duration:.2f}s")

        # 等待主要容器就绪
        page.wait_for_selector(".main-metric-card", timeout=15000)
        time.sleep(2.0)

        # 1. 验证首屏 4 张卡片
        cards = page.query_selector_all(".main-metric-card")
        print(f"Found {len(cards)} KPI cards on page")
        assert len(cards) >= 4, f"Expected at least 4 metric cards, found {len(cards)}"

        # 2. 验证主按钮样式 (确认机构蓝而非番茄红)
        primary_btn = page.query_selector('button[kind="primary"], [data-testid="stBaseButton-primary"]')
        btn_style_info = {}
        if primary_btn:
            btn_style_info = page.evaluate("""btn => {
                const s = window.getComputedStyle(btn);
                return {
                    backgroundColor: s.backgroundColor,
                    color: s.color,
                    height: s.height,
                    borderRadius: s.borderRadius
                };
            }""", primary_btn)
            print(f"Primary button style: {btn_style_info}")
            bg = btn_style_info.get("backgroundColor", "")
            print("Button background check:", bg)
            assert "255, 75, 75" not in bg, f"Primary button still has tomato red background: {bg}"

        # 截图 1: 首屏开箱即用 (全屏 1080p，包含大表)
        shot1 = os.path.join(output_dir, "01_first_screen_tab1_instant.png")
        page.screenshot(path=shot1, full_page=False)
        print(f"Saved Screenshot 1: {shot1}")

        # 3. 展开双翼看板验证十二维风控 (使用 JS 直接调度 click，避免元素遮挡)
        print("Expanding dual-wing advisory dashboard via JS ...")
        page.evaluate("""() => {
            const exp = document.querySelector('details summary');
            if (exp) exp.click();
        }""")
        time.sleep(1.5)
        shot2 = os.path.join(output_dir, "02_dual_wing_expanded_12d_sentry.png")
        page.screenshot(path=shot2, full_page=False)
        print(f"Saved Screenshot 2: {shot2}")

        # 4. 切换至 Tab 2: 持仓调仓
        tabs = page.query_selector_all('div[role="tab"], [data-testid="stTab"]')
        print(f"Found {len(tabs)} tabs")
        if len(tabs) >= 2:
            print("Clicking Tab 2 (持仓调仓)...")
            tabs[1].click()
            time.sleep(2.0)
            shot3 = os.path.join(output_dir, "03_tab2_portfolio_rebalance.png")
            page.screenshot(path=shot3, full_page=False)
            print(f"Saved Screenshot 3: {shot3}")

        # 5. 切换至 Tab 3: 组合回测
        if len(tabs) >= 3:
            print("Clicking Tab 3 (组合回测)...")
            tabs[2].click()
            time.sleep(2.0)
            shot4 = os.path.join(output_dir, "04_tab3_backtest_curve.png")
            page.screenshot(path=shot4, full_page=False)
            print(f"Saved Screenshot 4: {shot4}")

        # 6. 切换至 Tab 4: 穿透工具
        if len(tabs) >= 4:
            print("Clicking Tab 4 (穿透工具)...")
            tabs[3].click()
            time.sleep(1.5)
            shot5 = os.path.join(output_dir, "05_tab4_penetration_tools.png")
            page.screenshot(path=shot5, full_page=False)
            print(f"Saved Screenshot 5: {shot5}")

        # 7. 移动端 640px 视口走查
        print("Switching to mobile viewport 640x960 ...")
        page.set_viewport_size({"width": 640, "height": 960})
        time.sleep(1.5)
        shot6 = os.path.join(output_dir, "06_mobile_640px_responsive.png")
        page.screenshot(path=shot6, full_page=False)
        print(f"Saved Screenshot 6: {shot6}")

        browser.close()
        print("=== AUDIT WALKTHROUGH COMPLETED SUCCESSFULLY ===")

if __name__ == "__main__":
    run_audit()
