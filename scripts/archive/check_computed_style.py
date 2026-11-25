# -*- coding: utf-8 -*-
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.goto("http://127.0.0.1:8585", wait_until="networkidle")

    sb = page.locator('[data-testid="stSidebar"]')
    main = page.locator('[data-testid="stMain"]')
    app = page.locator('[data-testid="stApp"]')

    print(f"stSidebar count: {sb.count()}")
    if sb.count() > 0:
        res = sb.evaluate("el => ({display: window.getComputedStyle(el).display, visibility: window.getComputedStyle(el).visibility, opacity: window.getComputedStyle(el).opacity, rect: el.getBoundingClientRect()})")
        print("stSidebar style:", res)

    print(f"stMain count: {main.count()}")
    if main.count() > 0:
        res = main.evaluate("el => ({display: window.getComputedStyle(el).display, visibility: window.getComputedStyle(el).visibility, opacity: window.getComputedStyle(el).opacity, rect: el.getBoundingClientRect()})")
        print("stMain style:", res)

    # Check all elements that might be white or covering
    body_info = page.evaluate("""() => {
        const els = Array.from(document.querySelectorAll('*'));
        let covering = [];
        for (const el of els) {
            const style = window.getComputedStyle(el);
            const rect = el.getBoundingClientRect();
            if (rect.width >= window.innerWidth && rect.height >= window.innerHeight && style.position === 'fixed') {
                covering.push({tag: el.tagName, id: el.id, className: el.className, zIndex: style.zIndex, bg: style.backgroundColor});
            }
        }
        return {
            title: document.title,
            bodyBg: window.getComputedStyle(document.body).backgroundColor,
            covering: covering
        };
    }""")
    print("Body info:", body_info)

    browser.close()
