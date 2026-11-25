import time
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 960})
    page.goto("http://localhost:8501")
    time.sleep(20)
    
    print("[1] Clicking '💼 持仓调仓'...")
    page.locator('text="💼 持仓调仓"').first.click()
    time.sleep(5)
    
    txt = page.inner_text("body")
    print("Has '三阶专项重塑与减亏手术方案'?", "三阶专项重塑与减亏手术方案" in txt)
    print("Has '19 只免赎碎片尾仓'?", "19 只免赎碎片尾仓" in txt)
    print("Has '易方达裕祥回报债券A'?", "易方达裕祥回报债券A" in txt)
    print("Has '442.70'?", "442.70" in txt)
    print("Has '26,615.10'?", "26,615.10" in txt)

    print("\n[2] Clicking '📈 组合回测'...")
    page.locator('text="📈 组合回测"').first.click()
    time.sleep(5)
    
    txt3 = page.inner_text("body")
    print("Has '回测模式'?", "回测模式" in txt3)
    print("Has '原始29基'?", "原始29基" in txt3)
    print("Has '投顾重构 6 基核心组合'?", "投顾重构 6 基核心组合" in txt3)

    browser.close()
