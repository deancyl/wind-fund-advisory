import time
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 960})
    page.goto("http://localhost:8501")
    
    print("Waiting for tabs to appear...")
    page.locator('div:has-text("🌱 新资建仓")').last.wait_for(timeout=30000)
    
    tabs = page.locator('div[data-testid="stTab"]')
    print("[1] Clicking Tab 1: 💼 持仓调仓...")
    tabs.nth(1).click()
    
    # Wait for the button
    diag_btn = page.locator('button:has-text("诊断持仓")').first
    diag_btn.wait_for(timeout=25000)
    print("Found diag_btn! Clicking...")
    diag_btn.click()
    
    print("Waiting for '三阶专项重塑与减亏手术方案' to appear (timeout=45s)...")
    rx_elem = page.locator('text="三阶专项重塑与减亏手术方案"').first
    rx_elem.wait_for(timeout=45000)
    print("SUCCESS! Found '三阶专项重塑与减亏手术方案'!")

    # Check text around it
    card_txt = rx_elem.locator("..").inner_text()
    print("Card text preview:", repr(card_txt[:200]))

    browser.close()
