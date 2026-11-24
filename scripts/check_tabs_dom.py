# -*- coding: utf-8 -*-
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.goto("http://127.0.0.1:8585", wait_until="networkidle")

    body_html = page.evaluate("() => document.body.innerHTML")
    print(f"Body HTML length: {len(body_html)}")
    print("Body HTML snippet:")
    print(body_html[:1000])

    browser.close()
