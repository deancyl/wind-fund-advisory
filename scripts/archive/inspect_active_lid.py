import time
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 960})
    page.goto("http://localhost:8501")
    
    page.locator('div:has-text("🌱 新资建仓")').last.wait_for(timeout=30000)
    tabs = page.locator('div[data-testid="stTab"]')
    tabs.nth(1).click()
    
    time.sleep(3)
    # Check selectbox for 切换账本 in Tab 2
    tb_led = page.locator('div[data-testid="stSelectbox"]').filter(has_text="切换账本")
    if tb_led.count() == 0:
        tb_led = page.get_by_label("切换账本")
    print(f"Tab 2 ledger selectbox text: {repr(tb_led.first.inner_text() if tb_led.count() > 0 else 'NOT FOUND')}")

    # Also topbar ledger selectbox
    top_led = page.get_by_label("当前激活账本")
    print(f"Topbar ledger selectbox text: {repr(top_led.first.inner_text() if top_led.count() > 0 else 'NOT FOUND')}")

    browser.close()
