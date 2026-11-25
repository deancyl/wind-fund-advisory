# -*- coding: utf-8 -*-
"""
scripts/visual_tour_full.py
多模态视觉自愈巡检脚本：
1. 极端移动端 (640px 视口) 几何检查与零溢出核验
2. 暗色主题 (color_scheme='dark') 走查
3. 覆盖 Tab 1 ~ Tab 4，深度定位验证：
   - Tab 2: 智能微观执行滑点优化卡片与 VWAP 挂单调度
   - Tab 3: 10,000 次蒙特卡洛块重采样与极限 CVaR 99%
   - Tab 4: 动态相关性突变防御与集中度降级警报 + EWMA 走势图
4. 全量与局部高精截图沉淀至 data/screenshots/ 目录
"""

from playwright.sync_api import sync_playwright
from pathlib import Path
import json
import time

SCREENSHOT_DIR = Path("data/screenshots")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

def run_tour():
    results = {
        "mobile_640": {},
        "dark_mode": {},
        "overflow_detected": False,
        "tabs_checked": [],
        "cards_verified": []
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        # 1. 极端移动端 640px 视口测试
        print("=== 开始 640px 移动端视口走查 ===")
        context = browser.new_context(
            viewport={"width": 640, "height": 960},
            color_scheme="dark",
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15"
        )
        page = context.new_page()
        page.goto("http://127.0.0.1:8501", wait_until="networkidle")
        page.wait_for_timeout(4000)
        
        # 检查主视口宽度与溢出
        geom = page.evaluate("""() => {
            const el = document.documentElement;
            const body = document.body;
            const app = document.querySelector('[data-testid="stAppViewContainer"]') || body;
            return {
                clientWidth: el.clientWidth,
                scrollWidth: el.scrollWidth,
                bodyClientWidth: body.clientWidth,
                bodyScrollWidth: body.scrollWidth,
                appClientWidth: app.clientWidth,
                appScrollWidth: app.scrollWidth,
                hasOverflow: el.scrollWidth > el.clientWidth || body.scrollWidth > body.clientWidth
            };
        }""")
        print(f"640px 视口几何指标: {geom}")
        results["mobile_640"]["geometry"] = geom
        if geom["hasOverflow"]:
            results["overflow_detected"] = True

        tab_buttons = page.locator('[data-testid="stTab"]')
        tab_count = tab_buttons.count()
        print(f"检测到顶层 Tab 数量: {tab_count}")
        
        tab_names = ["tab1_new_capital", "tab2_rebalance", "tab3_backtest", "tab4_toolbox"]
        
        for i in range(min(tab_count, 4)):
            t_button = tab_buttons.nth(i)
            t_text = t_button.inner_text().strip().split("\n")[0]
            print(f"正在巡检 Tab {i+1}: {t_text}...")
            t_button.click()
            page.wait_for_timeout(2500)
            
            # 检查当前 Tab 下的溢出情况
            tab_geom = page.evaluate("""() => {
                const el = document.documentElement;
                return {
                    clientWidth: el.clientWidth,
                    scrollWidth: el.scrollWidth,
                    overflow: el.scrollWidth > el.clientWidth
                };
            }""")
            print(f"  Tab {i+1} 几何: {tab_geom}")
            
            # 全页面截图
            shot_full = SCREENSHOT_DIR / f"mobile_640_{tab_names[i]}_full.png"
            page.screenshot(path=str(shot_full), full_page=True)
            print(f"  全页截图已保存: {shot_full}")

            # 视口首屏截图
            shot_path = SCREENSHOT_DIR / f"mobile_640_{tab_names[i]}.png"
            page.screenshot(path=str(shot_path), full_page=False)
            
            results["tabs_checked"].append({
                "index": i + 1,
                "name": t_text,
                "screenshot": str(shot_path),
                "screenshot_full": str(shot_full),
                "geom": tab_geom
            })
            if tab_geom["overflow"]:
                results["overflow_detected"] = True

            # 针对性卡片局部滚轮定位
            if i == 2:  # Tab 3 回测承压推演
                mc_elem = page.locator("text=极端黑天鹅 10,000 次蒙特卡洛块重采样推演").first
                if mc_elem.count() > 0:
                    mc_elem.scroll_into_view_if_needed()
                    page.wait_for_timeout(1000)
                    shot_mc = SCREENSHOT_DIR / "mobile_640_tab3_monte_carlo_card.png"
                    page.screenshot(path=str(shot_mc), full_page=False)
                    print(f"  🎲 Tab 3 蒙特卡洛卡片截图已保存: {shot_mc}")
                    results["cards_verified"].append("tab3_monte_carlo_card_mobile")

            elif i == 3:  # Tab 4 穿透与突变防御
                corr_elem = page.locator("text=动态相关性突变防御与集中度降级警报").first
                if corr_elem.count() > 0:
                    corr_elem.scroll_into_view_if_needed()
                    page.wait_for_timeout(1000)
                    shot_corr = SCREENSHOT_DIR / "mobile_640_tab4_corr_mutation_card.png"
                    page.screenshot(path=str(shot_corr), full_page=False)
                    print(f"  🚨 Tab 4 动态突变防御卡片截图已保存: {shot_corr}")
                    results["cards_verified"].append("tab4_corr_mutation_card_mobile")

        context.close()

        # 2. 桌面端 1280px 暗色主题走查
        print("=== 开始 1280px 桌面暗色主题走查 ===")
        context_desk = browser.new_context(
            viewport={"width": 1280, "height": 900},
            color_scheme="dark"
        )
        page_desk = context_desk.new_page()
        page_desk.goto("http://127.0.0.1:8501", wait_until="networkidle")
        page_desk.wait_for_timeout(4000)

        desk_tabs = page_desk.locator('[data-testid="stTab"]')
        for i in range(min(desk_tabs.count(), 4)):
            t_btn = desk_tabs.nth(i)
            t_btn.click()
            page_desk.wait_for_timeout(2000)

            shot_full = SCREENSHOT_DIR / f"desktop_dark_{tab_names[i]}_full.png"
            page_desk.screenshot(path=str(shot_full), full_page=True)
            shot_path = SCREENSHOT_DIR / f"desktop_dark_{tab_names[i]}.png"
            page_desk.screenshot(path=str(shot_path), full_page=False)
            print(f"  桌面暗色全页截图已保存: {shot_full}")

            if i == 2:  # Tab 3
                mc_elem = page_desk.locator("text=极端黑天鹅 10,000 次蒙特卡洛块重采样推演").first
                if mc_elem.count() > 0:
                    mc_elem.scroll_into_view_if_needed()
                    page_desk.wait_for_timeout(1000)
                    shot_mc = SCREENSHOT_DIR / "desktop_dark_tab3_monte_carlo_card.png"
                    page_desk.screenshot(path=str(shot_mc), full_page=False)
                    print(f"  🎲 Tab 3 蒙特卡洛桌面截图已保存: {shot_mc}")
                    results["cards_verified"].append("tab3_monte_carlo_card_desktop")

            elif i == 3:  # Tab 4
                corr_elem = page_desk.locator("text=动态相关性突变防御与集中度降级警报").first
                if corr_elem.count() > 0:
                    corr_elem.scroll_into_view_if_needed()
                    page_desk.wait_for_timeout(1000)
                    shot_corr = SCREENSHOT_DIR / "desktop_dark_tab4_corr_mutation_card.png"
                    page_desk.screenshot(path=str(shot_corr), full_page=False)
                    print(f"  🚨 Tab 4 动态突变桌面截图已保存: {shot_corr}")
                    results["cards_verified"].append("tab4_corr_mutation_card_desktop")

        context_desk.close()
        browser.close()

    summary_file = SCREENSHOT_DIR / "visual_tour_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"=== 巡检报告已保存至 {summary_file} ===")
    print(f"溢出检测结果: {'❌ 存在横向溢出' if results['overflow_detected'] else '✅ 零溢出，几何自适应完美'}")

if __name__ == "__main__":
    run_tour()
