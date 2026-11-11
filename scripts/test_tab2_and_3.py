import time
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 960})
    page.goto("http://localhost:8501")
    time.sleep(15)
    
    tabs = page.locator('div[data-testid="stTab"]')
    print(f"Tabs count: {tabs.count()}")
    for i in range(tabs.count()):
        print(f"  Tab {i}: {repr(tabs.nth(i).inner_text())}")
        
    print("\n[1] Clicking Tab 1: 持仓调仓...")
    tabs.nth(1).click()
    time.sleep(3)
    
    diag_btn = page.locator('button:has-text("诊断持仓")')
    print(f"Diag btn count: {diag_btn.count()}")
    if diag_btn.count() > 0:
        diag_btn.first.click()
        print("Clicked diagnose button, waiting 6s...")
        time.sleep(6)
        
    txt2 = page.inner_text("body")
    print("Has '三阶专项重塑与减亏手术方案'?", "三阶专项重塑与减亏手术方案" in txt2)
    print("Has '19 只免赎碎片尾仓'?", "19 只免赎碎片尾仓" in txt2)
    print("Has '442.70'?", "442.70" in txt2)
    print("Has '易方达裕祥回报债券A'?", "易方达裕祥回报债券A" in txt2)

    print("\n[2] Clicking Tab 2: 组合回测...")
    tabs.nth(2).click()
    time.sleep(3)
    
    # Locate selectbox for 回测模式
    # Find selectbox inside Tab 3
    all_sb = page.locator('div[data-testid="stSelectbox"]')
    print(f"All selectboxes: {all_sb.count()}")
    target_sb = None
    for i in range(all_sb.count()):
        t = all_sb.nth(i).inner_text()
        if "回测模式" in t or "单账本" in t or "29基" in t:
            print(f"Found backtest mode selectbox at {i}: {repr(t)}")
            target_sb = all_sb.nth(i)
            break
            
    if target_sb:
        target_sb.click()
        time.sleep(1)
        opt = page.locator('li[role="option"]:has-text("原始29基 vs 投顾重构6基")')
        print(f"Option count: {opt.count()}")
        if opt.count() > 0:
            opt.first.click()
            print("Selected 29 vs 6 mode, waiting 6s for calculation...")
            time.sleep(6)
            
    txt3 = page.inner_text("body")
    print("Has '投顾重构 6 基核心组合'?", "投顾重构 6 基核心组合" in txt3)
    print("Has '原始 29 基存量组合'?", "原始 29 基存量组合" in txt3)
    print("Has '年化收益率'?", "年化收益率" in txt3)
    
    # Check plotly chart
    charts = page.locator('div[data-testid="stPlotlyChart"]')
    print(f"Plotly charts count: {charts.count()}")

    browser.close()
