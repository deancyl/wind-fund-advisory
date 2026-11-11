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
    time.sleep(3)
    
    # Print all buttons
    btns = page.locator('button')
    print(f"Total buttons: {btns.count()}")
    for i in range(btns.count()):
        txt = btns.nth(i).inner_text().strip()
        if txt:
            print(f"  Btn {i}: {repr(txt)}")

    browser.close()
