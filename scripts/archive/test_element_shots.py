# -*- coding: utf-8 -*-
import time
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.goto("http://127.0.0.1:8585", wait_until="networkidle")
    time.sleep(3)

    sb = page.locator('[data-testid="stSidebar"]')
    main = page.locator('[data-testid="stMain"]')

    print("Sidebar inner text snippet:")
    print(repr(sb.inner_text()[:300]))

    print("Main inner text snippet:")
    print(repr(main.inner_text()[:300]))

    page.screenshot(path="page_full.png")
    sb.screenshot(path="sb_shot.png")
    main.screenshot(path="main_shot.png")

    print("Screenshots saved!")
    browser.close()
