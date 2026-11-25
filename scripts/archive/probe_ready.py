import time
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("http://localhost:8501")
    for attempt in range(20):
        time.sleep(3)
        txt = page.inner_text("body")
        has_agy2 = "AGY2" in txt
        print(f"Attempt {attempt+1}: len={len(txt)}, has_agy2={has_agy2}")
        if has_agy2:
            print("Ready! Snippet:", repr(txt[:300]))
            break
    browser.close()
