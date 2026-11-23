# -*- coding: utf-8 -*-
"""
scripts/verify_scheme_a_sidebarless_live.py
Playwright 实机验证：方案 A 彻底去侧边栏 + 顶栏 🎨 外观 + 顶部单行指数走廊横条
"""

import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

WORKSPACE_DIR = Path(__file__).resolve().parent.parent
DESKTOP_IMG = WORKSPACE_DIR / "scheme_a_desktop_verified.png"
MOBILE_IMG = WORKSPACE_DIR / "scheme_a_mobile_verified.png"


def run_live_verification():
    print("=== 开始方案 A 实机双端与去侧边栏验证 ===")
    with sync_playwright() as p:
        # 1. 桌面端验证 (1440 x 900)
        print("\n--- [1/2] 桌面端 (1440x900) 验证 ---")
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        page.goto("http://127.0.0.1:8501", timeout=60000)
        page.wait_for_load_state("networkidle")
        page.wait_for_selector('text=AGY2 智投', timeout=20000)
        time.sleep(2)

        # 检查无全屏崩溃
        err_box = page.locator('.stAlert[data-baseweb="notification"]')
        if err_box.count() > 0:
            for i in range(err_box.count()):
                txt = err_box.nth(i).text_content() or ""
                print(f"  [Notice] Page Alert #{i}: {txt[:120]}")
                assert "There are multiple elements with the same key" not in txt, f"Duplicate key detected: {txt}"

        # 验证侧边栏彻底隐藏
        sidebar = page.locator('[data-testid="stSidebar"]')
        if sidebar.count() > 0:
            assert not sidebar.is_visible(), "stSidebar 应该在 CSS 中隐藏不可见！"
            print("  [OK] stSidebar 在 CSS 中处于隐藏状态 (display: none / hidden)")
        else:
            print("  [OK] stSidebar 未在 DOM 中渲染")

        # 验证展开箭头也不可见
        expand_btn = page.locator('[data-testid="stExpandSidebarButton"], [data-testid="collapsedControl"]')
        if expand_btn.count() > 0:
            assert not expand_btn.is_visible(), "展开箭头应该隐藏！"
            print("  [OK] 展开侧边栏触点已彻底隐藏")

        # 验证顶栏包含品牌、状态与外观 🎨
        topbar_title = page.locator('text=AGY2 智投')
        assert topbar_title.count() > 0 and topbar_title.first.is_visible(), "顶栏未找到 'AGY2 智投' 品牌标识"
        print("  [OK] 顶栏品牌标识 'AGY2 智投' 正常展示")

        # 验证 🎨 Popover 按钮存在
        theme_pop = page.locator('button[data-testid="stPopoverButton"]:has-text("🎨")')
        assert theme_pop.count() > 0 and theme_pop.first.is_visible(), "顶栏必须包含 '🎨' 外观设置 Popover 按钮"
        print("  [OK] 顶栏 '🎨' 外观定制入口正常展示")

        # 验证单行指数走廊横条存在
        ticker_strip = page.locator('.top-index-strip')
        assert ticker_strip.count() > 0 and ticker_strip.first.is_visible(), "必须存在顶部单行指数走廊横条 (.top-index-strip)"
        pills = page.locator('.top-index-pill')
        pill_cnt = pills.count()
        assert pill_cnt >= 3, f"顶部指数胶囊数量不足: {pill_cnt}"
        print(f"  [OK] 顶部单行指数走廊横条正常展示，包含 {pill_cnt} 只核心指数胶囊")

        # 验证走廊配置 ⚙️ 与 刷新 按钮存在
        corridor_cfg = page.locator('button[data-testid="stPopoverButton"]:has-text("⚙️")')
        assert corridor_cfg.count() > 0 and corridor_cfg.first.is_visible(), "走廊必须包含 '⚙️' 配置 Popover"
        print("  [OK] 指数走廊 '⚙️' 定制入口正常展示")

        rf_btn = page.locator('button[data-testid="stBaseButton-secondary"]:has-text("🔄"), button[data-testid="stBaseButton-secondary"]:has-text("刷新")')
        assert rf_btn.count() > 0 and rf_btn.first.is_visible(), "行情带必须包含 '🔄' 或 '刷新' 按钮"
        print("  [OK] 核心行情带 '🔄' 刷新按钮正常展示")

        # 验证 3 张 Hero 卡存在
        hero_cards = page.locator('.main-metric-card')
        assert hero_cards.count() >= 3, f"首屏 Hero 卡片数量不足 3 张: {hero_cards.count()}"
        print(f"  [OK] 首屏等宽 Hero 核心看板卡片正常展示 ({hero_cards.count()} 张)")

        page.screenshot(path=str(DESKTOP_IMG), full_page=False)
        print(f"  [OK] 桌面端实机截图已保存至: {DESKTOP_IMG}")
        context.close()

        # 2. 移动端验证 (390 x 844 iPhone 14)
        print("\n--- [2/2] 移动端 (390x844) 验证 ---")
        context_m = browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1"
        )
        page_m = context_m.new_page()
        page_m.goto("http://127.0.0.1:8501", timeout=60000)
        page_m.wait_for_load_state("networkidle")
        page_m.wait_for_selector('text=AGY2 智投', timeout=20000)
        time.sleep(2)

        # 验证移动端同样无侧边栏遮挡
        sidebar_m = page_m.locator('[data-testid="stSidebar"]')
        if sidebar_m.count() > 0:
            assert not sidebar_m.is_visible(), "移动端 stSidebar 应该隐藏！"
        print("  [OK] 移动端侧边栏零遮挡")

        # 验证移动端指数走廊横条横向平滑可滚动
        strip_m = page_m.locator('.top-index-strip')
        assert strip_m.count() > 0 and strip_m.first.is_visible(), "移动端必须可见顶部单行指数走廊横条"
        print("  [OK] 移动端单行指数走廊横条正常展示")

        page_m.screenshot(path=str(MOBILE_IMG), full_page=False)
        print(f"  [OK] 移动端实机截图已保存至: {MOBILE_IMG}")
        context_m.close()

        browser.close()

    print("\n✅ 方案 A 实机双端 Playwright 验证全部通过！")


if __name__ == "__main__":
    run_live_verification()
