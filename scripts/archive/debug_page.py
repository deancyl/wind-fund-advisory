import time
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 960})
    page.goto("http://localhost:8501")
    
    # Wait until tabs appear
    for attempt in range(25):
        time.sleep(2)
        tabs = page.locator('button[data-baseweb="tab"]')
        cnt = tabs.count()
        print(f"Sec {(attempt+1)*2}: tabs count = {cnt}")
        if cnt > 0:
            for i in range(cnt):
                print(f"  Tab {i}: {repr(tabs.nth(i).inner_text())}")
            break
            
    # Also print body length and check active ledger
    txt = page.inner_text("body")
    print("Has combat_29_funds text?", "实战存量组合" in txt)
    print("Has 442.70?", "442.70" in txt)
    print("Has 29只?", "29只" in txt)

    browser.close()
