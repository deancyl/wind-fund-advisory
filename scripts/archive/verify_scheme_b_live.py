# -*- coding: utf-8 -*-
"""
scripts/verify_scheme_b_live.py
方案 B 桌面端侧边栏导航 + 自定义板块行情 + 三刀重构双端实机截屏核验
"""

import sys
import time
import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
BRAIN_ARTIFACTS = Path("C:/Users/deanc/.gemini/antigravity/brain/1395b6f9-733c-4446-9cdb-f33a19e5f711")


def main():
    print("=== 开始方案 B 桌面端侧栏与三刀重构实机核验 ===")

    out_desktop = ROOT / "scheme_b_desktop_verified.png"
    out_mobile = ROOT / "scheme_b_mobile_verified.png"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # -------------------------------------------------------------
        # 1. 桌面端 (1440x900) 核验
        # -------------------------------------------------------------
        print("\n[DESKTOP] 1. 启动桌面端 (1440x900)...")
        ctx_desk = browser.new_context(viewport={"width": 1440, "height": 900})
        page_desk = ctx_desk.new_page()
        page_desk.goto("http://127.0.0.1:8501", wait_until="networkidle", timeout=30000)
        time.sleep(3)  # 等待 Streamlit 内部状态就绪

        # 检查是否包含局部异常报错
        body_desk = page_desk.inner_text("body")
        assert "btn_apply_combat29_rx" not in body_desk, "桌面端依然出现 btn_apply_combat29_rx 错误！"
        assert "There are multiple elements with the same key" not in body_desk, "桌面端出现重复 key 报错！"
        assert "NameError" not in body_desk, "页面出现 NameError！"

        # 检查侧边栏
        sidebar = page_desk.locator('[data-testid="stSidebar"]')
        assert sidebar.count() > 0, "缺少 stSidebar 节点！"
        assert sidebar.is_visible(), "桌面端 stSidebar 应该可见！"
        sidebar_text = sidebar.inner_text()
        print("  -> 侧边栏字样预览:", sidebar_text[:120].replace('\n', ' '))
        assert "核心指数" in sidebar_text, "侧边栏缺少核心指数走廊！"
        assert "自选与行业板块" in sidebar_text, "侧边栏缺少自定义板块行情！"
        assert "中证白酒" in sidebar_text or "半导体" in sidebar_text, "侧边栏自定义板块列表未正确渲染！"
        assert "+ 自选板块" in sidebar_text, "侧边栏缺少 + 自选板块 检索按钮！"

        # 检查主工作区
        assert "智能投顾今日调仓决策" in body_desk, "主工作区缺少统一调仓决策卡！"
        assert "立即执行" in body_desk, "主工作区缺少唯一的 [立即执行] 行动按钮！"

        # 验证表格存在
        df_count = page_desk.locator('[data-testid="stDataFrame"]').count()
        assert df_count > 0, "主工作区缺少持仓数据表格！"
        print(f"  -> 桌面端持仓数据表格已渲染 (count: {df_count})")

        # 截图桌面端
        page_desk.screenshot(path=str(out_desktop), full_page=False)
        print(f"  [OK] 桌面端截图已保存: {out_desktop}")
        if BRAIN_ARTIFACTS.exists():
            shutil.copy2(out_desktop, BRAIN_ARTIFACTS / "scheme_b_desktop_verified.png")
            print(f"  [OK] 已同步至 Brain Artifacts: scheme_b_desktop_verified.png")
        ctx_desk.close()

        # -------------------------------------------------------------
        # 2. 移动端 (390x844) 核验
        # -------------------------------------------------------------
        print("\n[MOBILE] 2. 启动移动端 (390x844)...")
        ctx_mob = browser.new_context(
            viewport={"width": 390, "height": 844},
            is_mobile=True,
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
        )
        page_mob = ctx_mob.new_page()
        page_mob.goto("http://127.0.0.1:8501", wait_until="networkidle", timeout=30000)
        time.sleep(3)

        body_mob = page_mob.inner_text("body")
        assert "btn_apply_combat29_rx" not in body_mob, "移动端依然出现 btn_apply_combat29_rx 错误！"
        assert "There are multiple elements with the same key" not in body_mob, "移动端出现重复 key 报错！"
        assert "NameError" not in body_mob, "移动端出现 NameError！"

        # 检查移动端侧边栏是否隐藏
        sb_mob = page_mob.locator('[data-testid="stSidebar"]')
        if sb_mob.count() > 0:
            assert not sb_mob.is_visible(), "移动端侧边栏应当被 CSS 隐藏！"
        print("  [OK] 移动端侧边栏已成功隐藏，100% 屏宽留给主界面")

        # 截图移动端
        page_mob.screenshot(path=str(out_mobile), full_page=False)
        print(f"  [OK] 移动端截图已保存: {out_mobile}")
        if BRAIN_ARTIFACTS.exists():
            shutil.copy2(out_mobile, BRAIN_ARTIFACTS / "scheme_b_mobile_verified.png")
            print(f"  [OK] 已同步至 Brain Artifacts: scheme_b_mobile_verified.png")
        ctx_mob.close()

        browser.close()

    print("\n🎉 全部实机核验成功，双端表现完美！")


if __name__ == "__main__":
    main()
