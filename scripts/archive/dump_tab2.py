import time
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 960})
    page.goto("http://localhost:8501")
    
    page.locator('div:has-text("🌱 新资建仓")').last.wait_for(timeout=30000)
    tabs = page.locator('div[data-testid="stTab"]')
    tabs.nth(1).click()
    time.sleep(3)
    
    diag_btn = page.locator('button:has-text("诊断持仓")').first
    diag_btn.wait_for(timeout=25000)
    diag_btn.click()
    time.sleep(8)
    
    # Save HTML
    with open("scripts/dump_tab2.html", "w", encoding="utf-8") as f:
        f.write(page.content())
    print("Saved dump_tab2.html, size:", len(page.content()))

    browser.close()
