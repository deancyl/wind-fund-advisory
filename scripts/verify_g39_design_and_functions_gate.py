# -*- coding: utf-8 -*-
"""
AGY2 (v5.18-G39) UI/UX Modernization & Defect Remediation Acceptance Gate.
Validates:
Stage 1: File presence, 100% byte mirror sync, and AST parse.
Stage 2: Crash remediation assertions (no cat_res unpack, no res_ocr list.get, cost_basis = m_val - pnl_val).
Stage 3: Desktop 70:30 dual-column and sidebar primary navigation assertions.
Stage 4: Real sector_watchlist CRUD and multi-market quote routing.
Stage 5: UI de-duplication guard and button label length <= 6 guard.
Stage 6: Headless Playwright dual-viewport (1440x900 desktop & 390x844 mobile) live validation.
"""
import ast
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGY2_DIR = ROOT / "AGY2_FundAdvisory"
for p in [str(ROOT), str(AGY2_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)


def main():
    print("=== G39 审美重塑、功能修复与架构门禁验收 ===")

    # -------------------------------------------------------------
    # Stage 1: 文件存在、100% 字节镜像一致性与 AST 编译
    # -------------------------------------------------------------
    print("--- [Stage 1] 文件存在、100% 字节镜像一致性与 AST 编译 ---")
    gui_root = ROOT / "app_gui.py"
    gui_agy2 = AGY2_DIR / "app_gui.py"
    sec_root = ROOT / "sector_watchlist.py"
    sec_agy2 = AGY2_DIR / "sector_watchlist.py"

    assert gui_root.exists(), "根目录缺少 app_gui.py"
    assert gui_agy2.exists(), "AGY2_FundAdvisory 缺少 app_gui.py"
    assert sec_root.exists(), "根目录缺少 sector_watchlist.py"
    assert sec_agy2.exists(), "AGY2_FundAdvisory 缺少 sector_watchlist.py"

    gui_root_bytes = gui_root.read_bytes()
    gui_agy2_bytes = gui_agy2.read_bytes()
    assert gui_root_bytes == gui_agy2_bytes, f"app_gui.py 镜像不一致: root={len(gui_root_bytes)} vs agy2={len(gui_agy2_bytes)}"
    print(f"  [OK] app_gui.py 双端镜像 100% 字节一致 ({len(gui_root_bytes)} 字节)")

    sec_root_bytes = sec_root.read_bytes()
    sec_agy2_bytes = sec_agy2.read_bytes()
    assert sec_root_bytes == sec_agy2_bytes, f"sector_watchlist.py 镜像不一致: root={len(sec_root_bytes)} vs agy2={len(sec_agy2_bytes)}"
    print(f"  [OK] sector_watchlist.py 双端镜像 100% 字节一致 ({len(sec_root_bytes)} 字节)")

    gui_txt = gui_root.read_text(encoding="utf-8")
    sec_txt = sec_root.read_text(encoding="utf-8")
    ast.parse(gui_txt, filename="app_gui.py")
    ast.parse(sec_txt, filename="sector_watchlist.py")
    print("  [OK] app_gui.py 与 sector_watchlist.py AST 编译通过，零语法错误")

    # -------------------------------------------------------------
    # Stage 2: 三处功能性崩溃硬消除断言
    # -------------------------------------------------------------
    print("--- [Stage 2] 三大崩溃与会计缺陷消除断言 ---")
    assert "n_code, n_name = cat_res[0]" not in gui_txt, "自选板块仍存在解包字典必崩缺陷"
    print("  [OK] 自选板块字典解包崩溃缺陷彻底清除 (n_code, n_name = cat_res[0] 已不存在)")

    assert 'res_ocr.get("holdings")' not in gui_txt, "顶栏截图导入仍存在 list.get 必崩缺陷"
    print("  [OK] 顶栏截图 OCR list.get 崩溃缺陷彻底清除 (res_ocr.get('holdings') 已不存在)")

    assert "cost_basis = m_val - pnl_val" in gui_txt, "单基录入未接入真实成本会计公式 cost_basis = m_val - pnl_val"
    print("  [OK] 单基录入会计成本公式已接入 (cost_basis = m_val - pnl_val 存在)")

    # -------------------------------------------------------------
    # Stage 3: 桌面真双栏与侧边栏主导航硬断言
    # -------------------------------------------------------------
    print("--- [Stage 3] 桌面端 70/30 真双栏与侧边栏主导航断言 ---")
    assert "col_main, col_rail = st.columns([7.0, 3.0]" in gui_txt, "未检测到桌面端 70/30 双栏布局 (col_main, col_rail = st.columns([7.0, 3.0])"
    print("  [OK] 桌面端 70/30 真双栏布局已准确落地")

    assert "desktop_nav_tab" in gui_txt, "侧边栏未接入桌面端单一主导航 (desktop_nav_tab)"
    print("  [OK] 侧边栏桌面端单一主导航已准确接入 (desktop_nav_tab)")

    # -------------------------------------------------------------
    # Stage 4: 自选板块持久化 CRUD 与多市场行情统一路由真实功能
    # -------------------------------------------------------------
    print("--- [Stage 4] 自选板块真实增删持久化与多市场行情路由测试 ---")
    import sector_watchlist as sw
    initial_items = sw.load_sector_watchlist()
    assert isinstance(initial_items, list) and len(initial_items) >= 5, f"默认自选列表异常: {initial_items}"

    # 增
    sw.add_sector_item("512880", "证券ETF")
    after_add = sw.load_sector_watchlist()
    target = next((x for x in after_add if x["code"] == "512880"), None)
    assert target is not None, "add_sector_item 未成功添加标的"
    assert target.get("asset_type") == "etf", f"资产类型推断错误: {target}"
    print("  [OK] add_sector_item 添加标的与资产类型推断 ('etf') 测试通过")

    # 删
    sw.remove_sector_item("512880")
    after_remove = sw.load_sector_watchlist()
    assert not any(x["code"] == "512880" for x in after_remove), "remove_sector_item 未能成功删除标的"
    print("  [OK] remove_sector_item 删除标的测试通过")

    # 磁盘文件持久化有效性检查
    wl_json = ROOT / "data" / "custom_sector_watchlist.json"
    assert wl_json.exists(), f"磁盘持久化文件不存在: {wl_json}"
    disk_data = json.loads(wl_json.read_text(encoding="utf-8"))
    assert isinstance(disk_data, list) and len(disk_data) >= 5, "磁盘持久化数据内容非合法列表"
    print(f"  [OK] 自选列表已持久化至 {wl_json} (合法 JSON，条目数: {len(disk_data)})")

    # 多市场行情路由实测
    etf_chg = sw.fetch_sector_change_pct({"code": "512480", "name": "半导体ETF", "asset_type": "etf"})
    fund_chg = sw.fetch_sector_change_pct({"code": "161725", "name": "中证白酒", "asset_type": "fund"})
    assert isinstance(etf_chg, float), f"ETF 行情返回值类型错误: {type(etf_chg)}"
    assert isinstance(fund_chg, float), f"基金行情返回值类型错误: {type(fund_chg)}"
    print(f"  [OK] 行情路由实测通过: 半导体ETF={etf_chg:+.2f}%, 中证白酒={fund_chg:+.2f}%")

    # -------------------------------------------------------------
    # Stage 5: UI 去重与按钮字数守卫
    # -------------------------------------------------------------
    print("--- [Stage 5] UI 控件去重与全站按钮字数守卫 ---")
    assert "topbar_ledger_select" not in gui_txt, "顶栏仍残留重复的账本下拉选择器 topbar_ledger_select"
    print("  [OK] 顶栏重复账本选择器已彻底清除 (topbar_ledger_select 0 命中)")

    btns = re.findall(r'st\.button\(\s*["\']([^"\']+)["\']', gui_txt)
    long_btns = [b for b in btns if len(re.sub(r'[^\u4e00-\u9fffA-Za-z0-9]', '', b)) > 6]
    assert not long_btns, f"存在超 6 字符长按钮破坏 G37 门禁: {long_btns}"
    print(f"  [OK] 全站 {len(btns)} 个 st.button 标签文字长度全量符合 <= 6 规范 (超长 0 命中)")

    # -------------------------------------------------------------
    # Stage 6: Playwright 实机双端页面零异常验收
    # -------------------------------------------------------------
    print("--- [Stage 6] Playwright 实机双端无头浏览器零异常验收 ---")
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            for label, vp in [("desktop_1440", {"width": 1440, "height": 900}), ("mobile_390", {"width": 390, "height": 844})]:
                page = browser.new_page(viewport=vp)
                try:
                    page.goto("http://127.0.0.1:8501", wait_until="networkidle", timeout=12000)
                except Exception:
                    page.goto("http://127.0.0.1:8501", timeout=12000)
                page.wait_for_timeout(3000)
                err_cnt = page.locator('[data-testid="stException"]').count()
                assert err_cnt == 0, f"[{label}] 页面出现红框异常 (count={err_cnt})"
                screenshot_path = ROOT / f"g39_{label}_verified.png"
                page.screenshot(path=str(screenshot_path), full_page=False)
                print(f"  [OK] [{label}] 视口实测通过: 0 红框报错，截图已保存至 {screenshot_path.name}")
                page.close()
            browser.close()
    except Exception as e:
        print(f"  [WARN/ERROR] Playwright 实测异常: {e}")
        raise e

    print("ALL G39 DESIGN-SYSTEM, DUAL-COLUMN & FUNCTION-REPAIR GATES PASSED")


if __name__ == "__main__":
    main()
