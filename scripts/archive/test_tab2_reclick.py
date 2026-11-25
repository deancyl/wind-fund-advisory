import time
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 960})
    page.goto("http://localhost:8501")
    
    page.locator('div:has-text("🌱 新资建仓")').last.wait_for(timeout=30000)
    tabs = page.locator('div[data-testid="stTab"]')
    
    print("[1] Clicking Tab 1: 💼 持仓调仓...")
    tabs.nth(1).click()
    time.sleep(3)
    
    diag_btn = page.locator('button:has-text("诊断持仓")').first
    diag_btn.wait_for(timeout=25000)
    print("[2] Clicking diag_btn...")
    diag_btn.click()
    
    print("Waiting 10s for rerun to complete...")
    time.sleep(10)
    
    print("[3] Clicking Tab 1: 💼 持仓调仓 again to view diagnosed results...")
    tabs = page.locator('div[data-testid="stTab"]')
    tabs.nth(1).click()
    time.sleep(4)
    
    txt = page.inner_text("body")
    print("\nResults after re-clicking Tab 1:")
    print("Contains '三阶专项重塑与减亏手术方案'?", "三阶专项重塑与减亏手术方案" in txt)
    print("Contains '19 只免赎碎片尾仓'?", "19 只免赎碎片尾仓" in txt)
    print("Contains '442.70'?", "442.70" in txt)
    print("Contains '易方达裕祥回报债券A'?", "易方达裕祥回报债券A" in txt)

    browser.close()
