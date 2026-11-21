# -*- coding: utf-8 -*-
import sys
from playwright.sync_api import sync_playwright

def run_browser_e2e():
    url = "http://127.0.0.1:8501"
    viewports = [
        ("desktop_1440", {"width": 1440, "height": 900}),
        ("mobile_390", {"width": 390, "height": 844}),
    ]
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for label, vp in viewports:
            page = browser.new_page(viewport=vp)
            print(f"[{label}] 正在导航至 {url} ...")
            page.goto(url, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(4000)

            # 硬断言 1：页面严禁出现任何 Streamlit 红色异常框
            exc_count = page.locator('[data-testid="stException"]').count()
            if exc_count > 0:
                exc_texts = page.locator('[data-testid="stException"]').all_inner_texts()
                print(f"[{label}] EXCEPTION DETECTED: {exc_texts}")
            assert exc_count == 0, f"[{label}] 页面出现 {exc_count} 个 Streamlit 异常崩溃框"

            body_text = page.inner_text("body")
            # 硬断言 2：极简首页核心区块已真实渲染
            assert "今日市场定调" in body_text, f"[{label}] 未渲染卡片 1 今日市场定调"
            assert "当前总资产" in body_text, f"[{label}] 未渲染卡片 2 当前总资产"
            assert "今日预估盈亏" in body_text, f"[{label}] 未渲染卡片 2 今日预估盈亏"

            # 硬断言 3：页面文本中严禁出现 G30 写死假常数或重复拼接截断
            for bad in ["3950.0", "1025.0", "4120.0", "+0.38%", "TypeError", "Traceback"]:
                assert bad not in body_text, f"[{label}] 页面出现非法假数据或报错文本: {bad}"

            page.screenshot(path=f"g31_e2e_{label}.png", full_page=True)
            print(f"[PASS] {label} 真机浏览器渲染零异常，截图已保存至 g31_e2e_{label}.png")
            page.close()
        browser.close()
    print("ALL G31 BROWSER E2E GATES PASSED")

if __name__ == "__main__":
    run_browser_e2e()
