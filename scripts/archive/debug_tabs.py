import time
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 960})
    page.goto("http://localhost:8501")
    time.sleep(20)
    
    # Find all elements with role tab or containing Tab or tab-like text
    tab_candidates = page.locator('[role="tab"], [data-testid="stTab"], [data-baseweb="tab"], button:has-text("新资建仓"), button:has-text("持仓诊断"), button:has-text("回测")')
    print(f"Candidates count: {tab_candidates.count()}")
    for i in range(tab_candidates.count()):
        el = tab_candidates.nth(i)
        tag = el.evaluate("e => e.tagName")
        cls = el.evaluate("e => e.className")
        txt = el.inner_text()
        print(f"Candidate {i}: tag={tag}, class={cls}, text={repr(txt)}")

    browser.close()
