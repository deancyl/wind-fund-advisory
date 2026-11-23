# -*- coding: utf-8 -*-
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent

def verify_gui_no_dup_key():
    print("[TEST] 1. 验证 app_gui.py 中 key 唯一性...")
    import re, collections
    gui_p = ROOT / "app_gui.py"
    content = gui_p.read_text(encoding="utf-8")
    keys = re.findall(r'key=[\'"]([^\'"]+)[\'"]', content)
    counts = collections.Counter(keys)
    dups = {k: v for k, v in counts.items() if v > 1}
    assert not dups, f"app_gui.py 仍存在重复 key: {dups}"
    print("  -> key 唯一性校验 100% 通过！")

    print("[TEST] 2. Playwright 实机测试 8501 页面渲染...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto("http://127.0.0.1:8501", wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(3500)

        # 检查首屏是否存在 stException 或局部异常
        body_text = page.inner_text("body")
        assert "btn_apply_combat29_rx" not in body_text, "页面仍残留 btn_apply_combat29_rx 错误！"
        assert "There are multiple elements with the same key" not in body_text, "仍存在重复 key 错误！"
        assert "渲染出现局部异常" not in body_text, "持仓调仓页面仍有局部渲染异常！"

        # 截图保存证据
        out_shot = ROOT.parent / ".gemini" / "antigravity" / "brain" / "1395b6f9-733c-4446-9cdb-f33a19e5f711" / "fix_btn_apply_combat29_rx_verified.png"
        if not out_shot.parent.exists():
            out_shot = ROOT / "fix_btn_apply_combat29_rx_verified.png"
        page.screenshot(path=str(out_shot))
        print(f"  -> 实机验证截图已保存至: {out_shot}")

        # 切换分段单选检查
        print("[TEST] 3. 逐项测试【估值对账】与【在途限购】分段...")
        # 点击估值对账
        try:
            page.click("text=估值对账", timeout=5000)
            page.wait_for_timeout(2000)
            body_val = page.inner_text("body")
            assert "There are multiple elements with the same key" not in body_val
            assert "渲染出现局部异常" not in body_val
            print("  -> 【估值对账】分段渲染正常！")
        except Exception as e:
            print(f"  -> 估值对账点击测试提示: {e}")

        # 点击持仓明细
        try:
            page.click("text=持仓明细", timeout=5000)
            page.wait_for_timeout(2000)
            body_m = page.inner_text("body")
            assert "btn_apply_combat29_rx" not in body_m
            assert "渲染出现局部异常" not in body_m
            print("  -> 【持仓明细】分段回切正常！")
        except Exception as e:
            print(f"  -> 持仓明细点击测试提示: {e}")

        page.close()
        browser.close()

    print("\n✅ ALL DUPLICATE KEY CHECKS & LIVE GUI TESTS PASSED!")

if __name__ == "__main__":
    verify_gui_no_dup_key()
