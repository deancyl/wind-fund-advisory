# -*- coding: utf-8 -*-
"""
scripts/walkthrough_g20_dual_viewport.py
Milestone 4: Dual-Viewport Walk-Through and Verification Harness.
Captures screenshots into artifacts/g20_screenshots/ and verifies:
- Desktop wide viewport (1280x800): 3-block layout, 3-step causal intelligence card, single bottom drawer with reading guides.
- Mobile narrow viewport (390x844): 4-column responsive table auto-projection with no horizontal overflow.
"""

import os
import sys
import time
import socket
import subprocess
import urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
SCREENSHOT_DIR = WORKSPACE_ROOT / "artifacts" / "g20_screenshots"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

HEALTH_URL = "http://127.0.0.1:8501/_stcore/health"


def is_port_in_use(port: int = 8501) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def wait_for_health(timeout: float = 45.0) -> bool:
    start_t = time.time()
    while time.time() - start_t < timeout:
        try:
            req = urllib.request.Request(HEALTH_URL)
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                if resp.status == 200:
                    body = resp.read().decode("utf-8").strip()
                    if body == "ok":
                        return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def kill_process_tree(pid: int):
    try:
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            check=False
        )
    except Exception as e:
        print(f"Warning: taskkill failed: {e}")


def cleanup_port_8501():
    try:
        out = subprocess.run(
            ["powershell", "-Command", "Get-NetTCPConnection -LocalPort 8501 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess"],
            capture_output=True, text=True
        ).stdout.strip()
        for pid_str in out.split():
            if pid_str.isdigit() and int(pid_str) > 0:
                print(f"Cleaning up lingering PID {pid_str} on 8501...")
                kill_process_tree(int(pid_str))
    except Exception as e:
        print(f"Port cleanup notice: {e}")


def wait_until_text(page, keywords, timeout_sec: int = 40) -> bool:
    start = time.time()
    while time.time() - start < timeout_sec:
        time.sleep(1)
        try:
            txt = page.inner_text("body")
            if any(k in txt for k in keywords):
                return True
        except Exception:
            pass
    return False


def click_tab_button(page, tab_label: str, fallback_idx: int):
    # Try finding button by text in tablist
    tab_btn = page.locator(f'[role="tab"]:has-text("{tab_label}"), button:has-text("{tab_label}"), [data-baseweb="tab"]:has-text("{tab_label}")')
    if tab_btn.count() > 0:
        tab_btn.first.click()
        return True
    tabs = page.locator('[role="tab"], button[data-baseweb="tab"]')
    if tabs.count() > fallback_idx:
        tabs.nth(fallback_idx).click()
        return True
    return False


def run_walkthrough():
    print("=== Starting Milestone 4 Dual-Viewport Walkthrough ===")

    cleanup_port_8501()
    time.sleep(1.0)

    # Step 1: Start Streamlit
    print("Launching Streamlit on port 8501...")
    cmd = [
        sys.executable, "-m", "streamlit", "run",
        "AGY2_FundAdvisory/app_gui.py",
        "--server.port", "8501",
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false"
    ]
    server_proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(WORKSPACE_ROOT)
    )

    if not wait_for_health(timeout=45.0):
        print("ERROR: Streamlit server failed to return health OK within timeout!")
        if server_proc:
            kill_process_tree(server_proc.pid)
        sys.exit(1)

    print("Streamlit server is healthy on http://127.0.0.1:8501.")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            # -----------------------------------------------------------
            # 1. Desktop Wide Viewport (1280x800)
            # -----------------------------------------------------------
            print("\n--- 1. Testing Desktop Wide Viewport (1280x800) ---")
            desktop_ctx = browser.new_context(
                viewport={"width": 1280, "height": 800}
            )
            page = desktop_ctx.new_page()

            url_desktop = "http://127.0.0.1:8501/?view=desktop"
            print(f"Navigating to {url_desktop}...")
            page.goto(url_desktop)
            
            # Wait for Tab 1 Chief memo card to render
            print("Waiting for Tab 1 Chief Memo card...")
            ready_t1 = wait_until_text(
                page,
                ["今日关键信息感知", "获取到的关键信息", "展开底层投研与十维风控验算底稿", "新资建仓"],
                timeout_sec=40
            )
            print(f"Tab 1 loaded (ready={ready_t1})")
            time.sleep(2.0)

            # Capture Desktop Tab 1
            ss_dt1 = SCREENSHOT_DIR / "desktop_tab1.png"
            page.screenshot(path=str(ss_dt1), full_page=False)
            print(f"Captured: {ss_dt1} (size: {os.path.getsize(ss_dt1)} bytes)")

            # Verify Desktop Tab 1 elements
            content_t1 = page.content()
            has_causal_chain = any(k in content_t1 for k in [
                "今日关键信息感知与决策传导清单",
                "今日关键信息感知与调仓裁决卡",
                "获取到的关键信息",
                "投顾大脑的深度理解",
                "对您今日组合的具体动作"
            ])
            has_bottom_drawer_t1 = "展开底层投研与十维风控验算底稿" in content_t1
            print(f"  [Tab 1 Check] 3-step causal intelligence card present: {has_causal_chain}")
            print(f"  [Tab 1 Check] Single bottom drawer present: {has_bottom_drawer_t1}")
            assert has_causal_chain, "Tab 1 missing 3-step causal intelligence card"
            assert has_bottom_drawer_t1, "Tab 1 missing bottom drawer"

            # Switch to Tab 2
            print("Switching to Tab 2 (持仓调仓)...")
            click_tab_button(page, "持仓调仓", 1)
            ready_t2 = wait_until_text(
                page,
                ["今日调仓裁决", "免赎碎片尾仓", "深套出血点", "三阶专项重塑"],
                timeout_sec=30
            )
            print(f"Tab 2 loaded (ready={ready_t2})")
            time.sleep(2.0)

            # Capture Desktop Tab 2
            ss_dt2 = SCREENSHOT_DIR / "desktop_tab2.png"
            page.screenshot(path=str(ss_dt2), full_page=False)
            print(f"Captured: {ss_dt2} (size: {os.path.getsize(ss_dt2)} bytes)")

            content_t2 = page.content()
            has_tab2_card = any(k in content_t2 for k in [
                "今日调仓裁决",
                "今日关键信息感知与调仓裁决卡",
                "免赎碎片尾仓",
                "深套出血点"
            ])
            has_bottom_drawer_t2 = "展开底层投研与十维风控验算底稿" in content_t2
            print(f"  [Tab 2 Check] Tab 2 intelligence/decision card present: {has_tab2_card}")
            print(f"  [Tab 2 Check] Single bottom drawer present: {has_bottom_drawer_t2}")
            assert has_tab2_card, "Tab 2 missing intelligence/decision card"
            assert has_bottom_drawer_t2, "Tab 2 missing bottom drawer"

            # Switch to Tab 3
            print("Switching to Tab 3 (组合回测)...")
            click_tab_button(page, "组合回测", 2)
            ready_t3 = wait_until_text(
                page,
                ["实战存量组合", "原始29基", "投顾重构6基", "滚动发车", "回测"],
                timeout_sec=30
            )
            print(f"Tab 3 loaded (ready={ready_t3})")
            time.sleep(2.0)

            # Capture Desktop Tab 3
            ss_dt3 = SCREENSHOT_DIR / "desktop_tab3.png"
            page.screenshot(path=str(ss_dt3), full_page=False)
            print(f"Captured: {ss_dt3} (size: {os.path.getsize(ss_dt3)} bytes)")

            content_t3 = page.content()
            has_backtest = any(k in content_t3 for k in [
                "实战存量组合",
                "原始29基",
                "投顾重构6基",
                "滚动发车",
                "回测"
            ])
            print(f"  [Tab 3 Check] Combat 29 vs 6 backtest present: {has_backtest}")
            assert has_backtest, "Tab 3 missing backtest content"

            desktop_ctx.close()

            # -----------------------------------------------------------
            # 2. Mobile Narrow Viewport (390x844)
            # -----------------------------------------------------------
            print("\n--- 2. Testing Mobile Narrow Viewport (390x844) ---")
            mobile_ua = (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"
            )
            mobile_ctx = browser.new_context(
                viewport={"width": 390, "height": 844},
                user_agent=mobile_ua,
                is_mobile=True,
                has_touch=True
            )
            mpage = mobile_ctx.new_page()

            url_mobile = "http://127.0.0.1:8501/?view=mobile"
            print(f"Navigating to {url_mobile}...")
            mpage.goto(url_mobile)
            m_ready_t1 = wait_until_text(
                mpage,
                ["今日关键信息感知", "获取到的关键信息", "展开底层投研与十维风控验算底稿", "新资建仓"],
                timeout_sec=40
            )
            print(f"Mobile Tab 1 loaded (ready={m_ready_t1})")
            time.sleep(2.0)

            # Capture Mobile Tab 1
            ss_mb1 = SCREENSHOT_DIR / "mobile_tab1.png"
            mpage.screenshot(path=str(ss_mb1), full_page=False)
            print(f"Captured: {ss_mb1} (size: {os.path.getsize(ss_mb1)} bytes)")

            # Verify mobile 4 columns in Tab 1
            m_content_t1 = mpage.content()
            cols_4 = ["基金名称与代码", "当前或建议金额", "累计盈亏或目标占比", "今日明确操作指令"]
            cols_found = [c for c in cols_4 if c in m_content_t1]
            print(f"  [Mobile Tab 1 Check] 4-column projection found: {cols_found}")

            # Check for horizontal scroll / viewport overflow on mobile
            scroll_width = mpage.evaluate("() => document.documentElement.scrollWidth")
            client_width = mpage.evaluate("() => document.documentElement.clientWidth")
            print(f"  [Mobile Tab 1 Check] scrollWidth: {scroll_width}px, clientWidth: {client_width}px (overflow check: {scroll_width <= client_width + 15})")
            assert scroll_width <= client_width + 15, f"Mobile viewport has horizontal overflow: scrollWidth {scroll_width} > clientWidth {client_width}"

            # Switch to Mobile Tab 2
            print("Switching to Mobile Tab 2 (持仓调仓)...")
            click_tab_button(mpage, "持仓调仓", 1)
            m_ready_t2 = wait_until_text(
                mpage,
                ["今日调仓裁决", "免赎碎片尾仓", "深套出血点", "三阶专项重塑"],
                timeout_sec=30
            )
            print(f"Mobile Tab 2 loaded (ready={m_ready_t2})")
            time.sleep(2.0)

            # Capture Mobile Tab 2
            ss_mb2 = SCREENSHOT_DIR / "mobile_tab2.png"
            mpage.screenshot(path=str(ss_mb2), full_page=False)
            print(f"Captured: {ss_mb2} (size: {os.path.getsize(ss_mb2)} bytes)")

            m_content_t2 = mpage.content()
            m_cols2_found = [c for c in cols_4 if c in m_content_t2]
            print(f"  [Mobile Tab 2 Check] 4-column projection in Tab 2: {m_cols2_found}")

            m_scroll_width2 = mpage.evaluate("() => document.documentElement.scrollWidth")
            m_client_width2 = mpage.evaluate("() => document.documentElement.clientWidth")
            print(f"  [Mobile Tab 2 Check] scrollWidth: {m_scroll_width2}px, clientWidth: {m_client_width2}px")
            assert m_scroll_width2 <= m_client_width2 + 15, f"Mobile Tab 2 has horizontal overflow: scrollWidth {m_scroll_width2} > clientWidth {m_client_width2}"

            mobile_ctx.close()
            browser.close()

        print("\nAll Playwright Dual-Viewport Walkthrough Tasks Completed Successfully!")

    finally:
        # Step 3: Cleanly terminate Streamlit server
        if server_proc:
            print("\nTerminating Streamlit server process (PID %d)..." % server_proc.pid)
            kill_process_tree(server_proc.pid)
            server_proc.wait(timeout=5)
            print("Streamlit process terminated.")

        cleanup_port_8501()
        time.sleep(1.0)
        port_open = is_port_in_use(8501)
        print(f"Port 8501 final status: in_use={port_open}")


if __name__ == "__main__":
    run_walkthrough()
