import time
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 960})
    page.goto("http://localhost:8501")
    time.sleep(15)
    
    cand = page.locator('div:has-text("🌱 新资建仓")').last
    html = cand.evaluate("e => e.outerHTML")
    parent_html = cand.evaluate("e => e.parentElement.outerHTML")
    print("Candidate HTML:", html[:300])
    print("Parent HTML:", parent_html[:400])

    browser.close()
