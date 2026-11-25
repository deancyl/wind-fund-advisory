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
    
    # Let's print inner_text of body right before click
    print("Before click body length:", len(page.inner_text("body")))
    
    diag_btn.click()
    print("Clicked diag_btn, waiting for networkidle...")
    page.wait_for_load_state("networkidle")
    time.sleep(5)
    
    # Check all headings or decision-card elements
    cards = page.locator('div.decision-card')
    print(f"Decision cards count: {cards.count()}")
    for i in range(cards.count()):
        print(f"Card {i}: {repr(cards.nth(i).inner_text()[:120])}")
        
    txt = page.inner_text("body")
    print("\nContains '三阶'?", "三阶" in txt)
    print("Contains '处方'?", "处方" in txt)
    print("Contains '重塑'?", "重塑" in txt)
    print("Contains '减亏'?", "减亏" in txt)

    browser.close()
