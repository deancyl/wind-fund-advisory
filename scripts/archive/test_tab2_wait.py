import time
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 960})
    page.goto("http://localhost:8501")
    
    tab_elem = page.locator('div:has-text("🌱 新资建仓")').last
    tab_elem.wait_for(timeout=30000)
    
    tabs = page.locator('div[data-testid="stTab"]')
    print("[1] Clicking Tab 1: 💼 持仓调仓...")
    tabs.nth(1).click()
    
    # Wait for the button
    diag_btn = page.locator('button:has-text("诊断持仓")').first
    diag_btn.wait_for(timeout=25000)
    print("Found diag_btn! Clicking...")
    diag_btn.click()
    
    print("Waiting 10s for diagnosis result...")
    time.sleep(10)
    
    txt2 = page.inner_text("body")
    print("Has '三阶专项重塑与减亏手术方案'?", "三阶专项重塑与减亏手术方案" in txt2)
    print("Has '19 只免赎碎片尾仓'?", "19 只免赎碎片尾仓" in txt2)
    print("Has '442.70'?", "442.70" in txt2)
    print("Has '易方达裕祥回报债券A'?", "易方达裕祥回报债券A" in txt2)

    browser.close()
