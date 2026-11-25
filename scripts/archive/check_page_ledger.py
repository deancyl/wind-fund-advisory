import time
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 960})
    page.goto("http://localhost:8501")
    
    page.locator('div:has-text("🌱 新资建仓")').last.wait_for(timeout=30000)
    
    # Check what ledger is shown on the topbar
    # Topbar has: col_top_ledger
    # Let's find text containing 实盘
    body = page.inner_text("body")
    print("Does page have '主实盘账本'?", "主实盘账本" in body)
    print("Does page have '实战存量组合'?", "实战存量组合" in body)
    print("Does page have '29只'?", "29只" in body)

    browser.close()
