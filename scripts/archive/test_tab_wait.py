import time
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 960})
    page.goto("http://localhost:8501")
    
    print("Waiting for tabs to appear...")
    tab_elem = page.locator('div:has-text("🌱 新资建仓")').last
    tab_elem.wait_for(timeout=30000)
    print("Tabs appeared!")
    
    tabs = page.locator('div[data-testid="stTab"]')
    print(f"Tabs count: {tabs.count()}")
    for i in range(tabs.count()):
        print(f"  Tab {i}: {repr(tabs.nth(i).inner_text())}")

    print("\n[1] Clicking Tab 1: 💼 持仓调仓...")
    tabs.nth(1).click()
    page.wait_for_timeout(3000)
    
    # Wait for Diag btn
    diag_btn = page.locator('button:has-text("诊断持仓")').first
    diag_btn.wait_for(timeout=10000)
    print("Found diag button, clicking it...")
    diag_btn.click()
    print("Waiting for diagnosis...")
    page.wait_for_timeout(6000)
    
    txt2 = page.inner_text("body")
    print("Has '三阶专项重塑与减亏手术方案'?", "三阶专项重塑与减亏手术方案" in txt2)
    print("Has '19 只免赎碎片尾仓'?", "19 只免赎碎片尾仓" in txt2)
    print("Has '442.70'?", "442.70" in txt2)
    print("Has '易方达裕祥回报债券A'?", "易方达裕祥回报债券A" in txt2)

    print("\n[2] Clicking Tab 2: 📈 组合回测...")
    tabs.nth(2).click()
    page.wait_for_timeout(3000)

    # Locate selectbox for 回测模式
    sb_elem = page.locator('div:has-text("🎯 回测模式")').last
    sb_elem.wait_for(timeout=10000)
    
    # In Tab 3, the selectbox can be clicked
    sb_box = page.locator('div[data-testid="stSelectbox"]').filter(has=page.locator('text="🎯 回测模式"'))
    if sb_box.count() == 0:
        sb_box = page.locator('div[data-testid="stSelectbox"]').filter(has_text="回测模式")
    print(f"sb_box count: {sb_box.count()}")
    if sb_box.count() > 0:
        sb_box.first.click()
        page.wait_for_timeout(1000)
        opt = page.locator('li[role="option"]:has-text("原始29基 vs 投顾重构6基")')
        print(f"Option count: {opt.count()}")
        if opt.count() > 0:
            opt.first.click()
            print("Selected 29 vs 6, waiting for charts...")
            page.wait_for_timeout(8000)
            
    txt3 = page.inner_text("body")
    print("Has '投顾重构 6 基核心组合'?", "投顾重构 6 基核心组合" in txt3)
    print("Has '原始 29 基存量组合'?", "原始 29 基存量组合" in txt3)
    print("Has '年化收益率'?", "年化收益率" in txt3)
    
    charts = page.locator('div[data-testid="stPlotlyChart"]')
    print(f"Plotly charts count: {charts.count()}")

    browser.close()
