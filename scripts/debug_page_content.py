# -*- coding: utf-8 -*-
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    page = b.new_page()
    page.goto('http://127.0.0.1:8501', wait_until='networkidle')
    page.wait_for_timeout(4000)
    c = page.content()
    with open('data/debug_page.html', 'w', encoding='utf-8') as f:
        f.write(c)
    print("Page length:", len(c))
    print("数据感知时间 in html:", "数据感知时间" in c)
    print("今日市场脉搏晨报 in html:", "今日市场脉搏晨报" in c)
    print("入选依据 in html:", "入选依据" in c)
    print("主动风险预警哨 in html:", "主动风险预警哨" in c)
    print("新资建仓 in html:", "新资建仓" in c)
    print("持仓调仓 in html:", "持仓调仓" in c)
    b.close()
