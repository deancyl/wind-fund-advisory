import time
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 960})
    page.goto("http://localhost:8501")
    
    page.locator('div:has-text("🌱 新资建仓")').last.wait_for(timeout=30000)
    tabs = page.locator('div[data-testid="stTab"]')
    tabs.nth(1).click()
    
    diag_btn = page.locator('button:has-text("诊断持仓")').first
    diag_btn.wait_for(timeout=25000)
    print("Clicking diag_btn at t=0...")
    diag_btn.click()
    
    start_t = time.time()
    for i in range(30):
        time.sleep(2)
        elapsed = time.time() - start_t
        txt = page.inner_text("body")
        has_rx = "三阶专项重塑与减亏手术方案" in txt
        has_stale = page.locator('[data-stale="true"]').count() > 0
        print(f"t={elapsed:.1f}s: has_stale={has_stale}, has_rx={has_rx}")
        if has_rx:
            print("Found rx at t=", elapsed)
            break

    browser.close()
