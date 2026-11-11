import time
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 960})
    page.goto("http://localhost:8501")
    time.sleep(15)
    
    # Check tabs container
    tablist = page.locator('[data-testid="stTabs"]')
    print(f"stTabs count: {tablist.count()}")
    
    # In Streamlit, stTabs children with role=tab:
    tab_buttons = page.locator('button[data-baseweb="tab"], [role="tab"]')
    print(f"Role tab count: {tab_buttons.count()}")
    for i in range(tab_buttons.count()):
        print(f"  Tab {i}: {repr(tab_buttons.nth(i).inner_text())}")
        
    print("\n--- Clicking Tab 1 (持仓调仓) ---")
    tab_buttons.nth(1).click()
    time.sleep(3)
    
    # Check for the button: 🔍 诊断持仓并生成今日调仓方案
    diag_btn = page.locator('button:has-text("诊断持仓")')
    print(f"Diag btn count: {diag_btn.count()}")
    if diag_btn.count() > 0:
        print("Clicking '🔍 诊断持仓并生成今日调仓方案'...")
        diag_btn.first.click()
        time.sleep(5)
        
    txt = page.inner_text("body")
    print("Has '三阶专项重塑与减亏手术方案'?", "三阶专项重塑与减亏手术方案" in txt)
    print("Has '19 只免赎碎片尾仓'?", "19 只免赎碎片尾仓" in txt)
    print("Has '442.70'?", "442.70" in txt)

    print("\n--- Clicking Tab 2 (组合回测) ---")
    tab_buttons.nth(2).click()
    time.sleep(3)
    
    # Look for selectbox 🎯 回测模式
    # In Tab 3, the selectbox has label "🎯 回测模式"
    bt_select = page.get_by_label("🎯 回测模式")
    if bt_select.count() == 0:
        bt_select = page.locator('div[data-testid="stSelectbox"]:has-text("回测模式")')
    print(f"bt_select count: {bt_select.count()}")
    if bt_select.count() > 0:
        bt_select.click()
        time.sleep(1)
        opt_29vs6 = page.locator('li[role="option"]:has-text("原始29基 vs 投顾重构6基")')
        print(f"opt_29vs6 count: {opt_29vs6.count()}")
        if opt_29vs6.count() > 0:
            opt_29vs6.first.click()
            time.sleep(5)
            
    txt3 = page.inner_text("body")
    print("Has '投顾重构 6 基核心组合'?", "投顾重构 6 基核心组合" in txt3)
    print("Has '原始 29 基存量组合'?", "原始 29 基存量组合" in txt3)
    print("Has '年化收益率'?", "年化收益率" in txt3)

    browser.close()
