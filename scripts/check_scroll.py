# -*- coding: utf-8 -*-
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.goto("http://127.0.0.1:8585", wait_until="networkidle")

    info = page.evaluate("""() => {
        const m = document.querySelector('[data-testid="stMain"]');
        return {
            bodyScrollHeight: document.body.scrollHeight,
            mainScrollHeight: m ? m.scrollHeight : 0,
            scrollY: window.scrollY
        };
    }""")
    print("Scroll info:", info)

    # Scroll down to 400px and take shot
    page.evaluate("() => window.scrollTo(0, 400)")
    page.screenshot(path="scroll_400.png")

    page.evaluate("() => window.scrollTo(0, 800)")
    page.screenshot(path="scroll_800.png")

    browser.close()
