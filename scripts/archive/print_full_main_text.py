# -*- coding: utf-8 -*-
import time
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.goto("http://127.0.0.1:8585", wait_until="networkidle")
    time.sleep(4)

    main = page.locator('[data-testid="stMain"]')
    txt = main.inner_text()
    print("Full main text length:", len(txt))
    print("=== Full Main Text Lines ===")
    for i, l in enumerate(txt.splitlines()):
        print(f"{i+1}: {l}")

    browser.close()
