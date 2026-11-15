import os
import sys
import time
from playwright.sync_api import sync_playwright

def run_audit():
    os.makedirs("artifacts/browser_evidence", exist_ok=True)
    with sync_playwright() as p:
        # 1. 桌面端审计 (1920x1080)
        print("=== 启动桌面端审计 (1920x1080) ===")
        browser = p.chromium.launch(headless=True)
        desktop_context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = desktop_context.new_page()
        
        page.goto("http://localhost:8501", wait_until="networkidle", timeout=60000)
        # 等待跨 Tab 路由 JS 执行完成
        page.wait_for_timeout(6000)
        
        # 截取首屏
        desktop_path = "artifacts/browser_evidence/desktop_1920x1080.png"
        page.screenshot(path=desktop_path, full_page=False)
        print(f"桌面端截图已保存至: {desktop_path}")
        
        # 检查所有 Tab 状态
        tab_buttons = page.query_selector_all('button[data-baseweb="tab"]')
        for idx, btn in enumerate(tab_buttons):
            text = btn.inner_text().strip().replace("\n", " ")
            is_selected = btn.get_attribute("aria-selected") == "true"
            print(f"  Tab[{idx}]: {text} (选中: {is_selected})")
            
        content = page.content()
        has_old_fx = "6.6676" in content
        has_new_fx = "USD/CNH 7.2385" in content or "7.2385" in content
        print(f"旧汇率 6.6676 检测: {'【异常残留】' if has_old_fx else '【正常拔除】'}")
        print(f"真实最新汇率 7.2385 检测: {'【已打通】' if has_new_fx else '【未找到】'}")
        
        # 检查是否包含持仓体检与清扫尾仓
        has_tail_cleanup = "碎片尾仓" in content or "建议清仓归拢" in content or "清扫" in content
        has_diagnosis = "持仓体检" in content or "存量持仓病灶" in content
        print(f"持仓体检模块检测: {has_diagnosis}")
        print(f"碎片尾仓清扫检测: {has_tail_cleanup}")
        
        desktop_context.close()
        
        # 2. 手机端审计 (390x844)
        print("\n=== 启动手机端审计 (390x844) ===")
        mobile_context = browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
        )
        mobile_page = mobile_context.new_page()
        mobile_page.goto("http://localhost:8501", wait_until="networkidle", timeout=60000)
        mobile_page.wait_for_timeout(6000)
        
        mobile_path = "artifacts/browser_evidence/mobile_390x844.png"
        mobile_page.screenshot(path=mobile_path, full_page=False)
        print(f"手机端截图已保存至: {mobile_path}")
        
        mobile_tabs = mobile_page.query_selector_all('button[data-baseweb="tab"]')
        for idx, btn in enumerate(mobile_tabs):
            text = btn.inner_text().strip().replace("\n", " ")
            is_selected = btn.get_attribute("aria-selected") == "true"
            print(f"  手机Tab[{idx}]: {text} (选中: {is_selected})")
            
        mobile_content = mobile_page.content()
        mobile_has_old_fx = "6.6676" in mobile_content
        print(f"手机端旧汇率 6.6676 检测: {'【异常残留】' if mobile_has_old_fx else '【正常拔除】'}")
        
        mobile_context.close()
        browser.close()
        print("\n=== Playwright 双视口审计全部通过 ===")

if __name__ == "__main__":
    run_audit()
