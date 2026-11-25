import time
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 960})
    page.goto("http://localhost:8501")
    time.sleep(15)
    
    # Check topbar text
    print("Topbar area text:")
    # Find all divs with text containing 实盘
    for el in page.locator('div:has-text("实盘")').all()[:10]:
        t = el.inner_text().strip()
        if len(t) < 100:
            print("  -", repr(t))

    browser.close()
