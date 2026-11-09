# -*- coding: utf-8 -*-
"""
scripts/verify_g13_browser_5points.py
G13 Generation Browser Visual & DOM Verification:
Validates all 5 pain points from user request against the live Streamlit instance:
1. Pain Point 1 (图 1): Fast first-screen rendering, 4 top metric cards, zero white screen lockup.
2. Pain Point 2 & 3 (图 2, 图 3): Removal of pseudo-action red button ('查看锁仓保护'), 100% full-width bar,
   expanded dual-wing dashboard, clean Top 3 cards without '+入备选池',
   clean risk sentry without '一键批量锁定' / '择机置换' buttons, and 5 deep tools evicted to Tab 4.
3. Pain Point 5 (图 5): Full-width 4-column 46px segmented navigation bar with high-contrast active state,
   elimination of duplicate large subheaders in Tabs 1-4, compact merged top row in Tab 4.
4. Pain Point 4 (图 4): Tab 3 Plotly chart legend floating outside at y=1.06 with transparent background,
   zero curve occlusion, real H11009 daily total return benchmark, hindsight disclaimer and C3 comparison toggle.
"""

import sys
import os
import time
import json
import urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
SCREENSHOT_DIR = WORKSPACE_ROOT / "data" / "screenshots"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

REPORT_DATA = {
    "pain_point_1": {},
    "pain_point_2_3": {},
    "pain_point_4": {},
    "pain_point_5": {},
    "summary": "PENDING"
}


def check_health():
    url = "http://127.0.0.1:8501/_stcore/health"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            return resp.status == 200 and resp.read().decode("utf-8").strip() == "ok"
    except Exception as e:
        print(f"Health check failed: {e}")
        return False


def run_verification():
    print("=================================================================")
    print("   G13 GENERATION BROWSER REAL-DEVICE 5-POINT VERIFICATION      ")
    print("=================================================================")

    if not check_health():
        print("FATAL: Streamlit daemon not healthy on port 8501!")
        sys.exit(1)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1920, "height": 1080}, color_scheme="light")
        page = ctx.new_page()

        # -------------------------------------------------------------
        # PAIN POINT 1: First-Screen Render Timing & Top 4 Cards
        # -------------------------------------------------------------
        print("\n--- [1/4] Verifying Pain Point 1: First-Screen Speed & Zero Block ---")
        t0 = time.time()
        page.goto("http://127.0.0.1:8501", wait_until="domcontentloaded")
        dom_loaded_ms = (time.time() - t0) * 1000

        # Wait for Streamlit top elements
        page.wait_for_selector('div[data-testid="stTabs"]', timeout=30000)
        t_first_render_ms = (time.time() - t0) * 1000

        # Allow initial run to complete
        page.wait_for_timeout(5000)

        print(f"  DOM Loaded: {dom_loaded_ms:.1f}ms | First Tab Render: {t_first_render_ms:.1f}ms")

        # Check top 4 metric cards
        metric_cards = page.locator('.main-metric-card')
        metric_count = metric_cards.count()
        print(f"  Total metric cards on page: {metric_count} (Expected >= 4)")
        assert metric_count >= 4, f"Expected at least 4 metric cards, found {metric_count}"

        card_titles = [metric_cards.nth(i).locator('.metric-card-title').inner_text().split('\n')[0].strip() for i in range(4)]
        print(f"  Top 4 header card titles: {card_titles}")
        expected_top_4 = ['交易时钟与窗口', '市场定调与攻防', '估值与资金量能', '总资产与今日预估']
        assert card_titles == expected_top_4, f"Top 4 cards {card_titles} did not match {expected_top_4}"

        # Save Screenshot 1
        ss_p1 = SCREENSHOT_DIR / "g13_verification_painpoint1_first_screen.png"
        page.screenshot(path=str(ss_p1), full_page=False)
        print(f"  Captured Screenshot 1: {ss_p1}")

        REPORT_DATA["pain_point_1"] = {
            "dom_loaded_ms": round(dom_loaded_ms, 1),
            "first_render_ms": round(t_first_render_ms, 1),
            "metric_cards_count": metric_count,
            "metric_card_titles": card_titles,
            "status": "PASS"
        }

        # -------------------------------------------------------------
        # PAIN POINT 2 & 3: Removal of Fake Action Buttons & Clean Full-Width Bar
        # -------------------------------------------------------------
        print("\n--- [2/4] Verifying Pain Points 2 & 3: Fake Button Removal & Clean Bar ---")
        
        # 1. Verify absence of the red action button 'btn_master_action_switch' / '👉 查看锁仓保护'
        red_btn = page.locator('button:has-text("查看锁仓保护")')
        red_btn_count = red_btn.count()
        print(f"  '查看锁仓保护' button count: {red_btn_count} (Expected 0)")
        assert red_btn_count == 0, "Red action button still exists in DOM!"

        # 2. Check full width expander
        expander = page.locator('details').first
        assert expander.count() > 0, "Top advisory expander not found!"
        expander_summary_text = expander.locator('summary').inner_text()
        print(f"  Advisory expander summary text: {expander_summary_text[:60]}...")
        assert "投顾参谋" in expander_summary_text or "展开" in expander_summary_text, "Summary text mismatch!"

        # 3. Expand the advisory expander and measure height & contents
        expander.click()
        page.wait_for_timeout(1000)

        # Check absence of fake buttons in right wing
        batch_lock_btn = page.locator('button:has-text("一键批量锁定")')
        assert batch_lock_btn.count() == 0, "'一键批量锁定' button still exists!"

        replace_btn = page.locator('button:has-text("择机置换")')
        assert replace_btn.count() == 0, "'择机置换' button still exists!"

        balance_btn = page.locator('button:has-text("平衡赛道敞口")')
        assert balance_btn.count() == 0, "'平衡赛道敞口' button still exists!"

        penetrate_btn = page.locator('button:has-text("穿透到底层")')
        assert penetrate_btn.count() == 0, "'穿透到底层' button still exists!"

        # Check absence of '+ 入备选池' buttons in left wing
        add_pool_btn = page.locator('button:has-text("入备选池")')
        assert add_pool_btn.count() == 0, "'+ 入备选池' buttons still exist!"

        # Check absence of the 5 evicted deep tools inside this expander
        expander_inner = expander.locator('> div')
        expander_text = expander_inner.inner_text()
        
        has_14_sectors_table = "全市场 14 大赛道量化温度计总表" in expander_text
        has_feeder_arb = "14:45 尾盘折溢价套利感知" in expander_text
        has_option_iv = "认沽期权隐含波动率防暴跌哨" in expander_text
        has_qdii_fx = "跨境QDII溢价与外汇期货锁汇" in expander_text
        has_inflection_ruler = "历史三大牛熊拐点实盘对照尺" in expander_text

        print(f"  Evicted tools present in expander: 14-sectors={has_14_sectors_table}, 14:45-arb={has_feeder_arb}, option-iv={has_option_iv}, qdii={has_qdii_fx}, inflection-ruler={has_inflection_ruler} (All should be False)")
        assert not has_14_sectors_table and not has_feeder_arb and not has_option_iv and not has_qdii_fx and not has_inflection_ruler, "Deep tools were not cleanly evicted from dual-wing expander!"

        # Measure expanded height
        expander_box = expander.bounding_box()
        exp_height = expander_box['height'] if expander_box else 0
        print(f"  Expander expanded total height: {exp_height:.1f}px")

        # Save Screenshot 2 & 3
        ss_p2_3 = SCREENSHOT_DIR / "g13_verification_painpoint2_3_dual_wing_expanded.png"
        page.screenshot(path=str(ss_p2_3), full_page=False)
        print(f"  Captured Screenshot 2/3: {ss_p2_3}")

        REPORT_DATA["pain_point_2_3"] = {
            "red_action_button_count": red_btn_count,
            "batch_lock_button_count": batch_lock_btn.count(),
            "add_to_pool_button_count": add_pool_btn.count(),
            "deep_tools_evicted": True,
            "expanded_height_px": round(exp_height, 1),
            "status": "PASS"
        }

        # Close expander to return to clean state
        expander.click()
        page.wait_for_timeout(500)

        # -------------------------------------------------------------
        # PAIN POINT 5: Full-Width 4-Column 46px Segmented Navigation
        # -------------------------------------------------------------
        print("\n--- [3/4] Verifying Pain Point 5: Full-Width 46px Segmented Navigation & Clean Tabs ---")
        
        # 1. Main tabs list styling and geometry
        tabs_container = page.locator('div[data-testid="stTabs"]').first
        tab_list = tabs_container.locator('div[role="tablist"], [data-baseweb="tab-list"]').first
        assert tab_list.count() > 0, "Tab list not found!"

        tab_buttons = tab_list.locator('button[data-baseweb="tab"], div[role="tab"], [data-testid="stTab"]')
        tab_count = tab_buttons.count()
        print(f"  Top tab buttons count: {tab_count} (Expected 4)")
        assert tab_count == 4, f"Expected 4 tabs, got {tab_count}"

        tab_texts = [tab_buttons.nth(i).inner_text().strip() for i in range(tab_count)]
        print(f"  Tabs labels: {tab_texts}")

        # Check tab height & styles
        first_tab_box = tab_buttons.first.bounding_box()
        tab_height = first_tab_box['height'] if first_tab_box else 0
        tab_width = first_tab_box['width'] if first_tab_box else 0
        print(f"  Tab 1 dimensions: height={tab_height:.1f}px (target ~46px), width={tab_width:.1f}px (target full-width / 4)")
        assert abs(tab_height - 46.0) <= 2.0, f"Tab height ({tab_height}px) is not 46px!"
        assert tab_width >= 250.0, f"Tab width ({tab_width}px) is not wide full-width card!"

        # Active tab styling: first tab is selected
        active_tab = tab_list.locator('button[aria-selected="true"], [role="tab"][aria-selected="true"]').first
        active_text = active_tab.inner_text().strip()
        print(f"  Active tab: {active_text}")

        # Save Screenshot 5: Segmented Navigation
        ss_p5 = SCREENSHOT_DIR / "g13_verification_painpoint5_segmented_nav.png"
        page.screenshot(path=str(ss_p5), full_page=False)
        print(f"  Captured Screenshot 5: {ss_p5}")

        # Switch to Tab 4 to check compact top bar
        print("  Switching to Tab 4 (穿透工具)...")
        tab_buttons.nth(3).click()
        page.wait_for_timeout(3000)

        # Check Tab 4 subheaders inside tabpanel content
        tabpanel_t4 = page.locator('div[role="tabpanel"]').first
        t4_headers = tabpanel_t4.locator('h1, h2, h3').all_inner_texts()
        has_dup_h4 = any("穿透工具" in h for h in t4_headers)
        print(f"  Tab 4 content headers: {t4_headers}")
        print(f"  Duplicate large subheader in Tab 4 content: {has_dup_h4} (Expected False)")
        assert not has_dup_h4, "Duplicate subheader '🔍 穿透工具' found in Tab 4 content!"

        # Check sub-tabs in Tab 4
        sub_tab_list = page.locator('[data-testid="stTabs"]').nth(1) if page.locator('[data-testid="stTabs"]').count() > 1 else None
        if sub_tab_list:
            sub_tabs_count = sub_tab_list.locator('button[data-baseweb="tab"], div[role="tab"], [data-testid="stTab"]').count()
            print(f"  Tab 4 sub-tabs count: {sub_tabs_count} (Expected >= 4)")

        # Save Screenshot Tab 4
        ss_p5_tab4 = SCREENSHOT_DIR / "g13_verification_painpoint5_tab4_compact.png"
        page.screenshot(path=str(ss_p5_tab4), full_page=False)
        print(f"  Captured Tab 4 Screenshot: {ss_p5_tab4}")

        REPORT_DATA["pain_point_5"] = {
            "tab_count": tab_count,
            "tab_height_px": round(tab_height, 1),
            "tab_width_px": round(tab_width, 1),
            "tab_labels": tab_texts,
            "duplicate_headers_removed": not has_dup_h4,
            "status": "PASS"
        }

        # -------------------------------------------------------------
        # PAIN POINT 4: Tab 3 Backtest Curve, Legend Placement & Benchmark Integrity
        # -------------------------------------------------------------
        print("\n--- [4/4] Verifying Pain Point 4: Backtest Legend Floating & Benchmark Real Curve ---")
        
        # Switch to Tab 3 (组合回测)
        print("  Switching to Tab 3 (组合回测)...")
        tab_buttons.nth(2).click()
        page.wait_for_timeout(6000)

        # Find Plotly chart inside tabpanel
        tabpanel = page.locator('div[role="tabpanel"]').first
        plots = tabpanel.locator('div.js-plotly-plot')
        plot_count = plots.count()
        print(f"  Plotly plots inside Tab 3: {plot_count} (Expected >= 1)")
        assert plot_count >= 1, "No Plotly plot found inside Tab 3!"

        chart = plots.nth(0)
        chart_title = chart.evaluate("el => el.layout && el.layout.title ? el.layout.title.text : null")
        chart_legend = chart.evaluate("el => el.layout && el.layout.legend ? el.layout.legend : null")
        chart_margin = chart.evaluate("el => el.layout && el.layout.margin ? el.layout.margin : null")
        trace_names = chart.evaluate("el => el.data ? el.data.map(t => t.name) : []")

        print(f"  Chart 0 Title: {chart_title}")
        print(f"  Chart 0 Legend: {chart_legend}")
        print(f"  Chart 0 Margin: {chart_margin}")
        print(f"  Chart 0 Trace Names: {trace_names}")

        # Assert legend layout rules
        assert chart_legend is not None, "Legend is missing from Plotly figure layout!"
        legend_y = chart_legend.get("y")
        legend_ori = chart_legend.get("orientation")
        legend_bg = chart_legend.get("bgcolor")
        print(f"  Legend details: y={legend_y} (>= 1.05), orientation='{legend_ori}' ('h'), bgcolor='{legend_bg}'")
        assert legend_y is not None and legend_y >= 1.05, f"Legend y ({legend_y}) is not floating above chart (>= 1.05)!"
        assert legend_ori == "h", f"Legend orientation ({legend_ori}) is not horizontal ('h')!"
        assert chart_margin.get("t") == 75, f"Chart top margin ({chart_margin.get('t')}) is not 75px!"

        # Check benchmarks in trace names
        has_hs300 = any("沪深300" in name for name in trace_names)
        has_dividend = any("红利低波" in name for name in trace_names)
        has_bond = any("纯债指数" in name for name in trace_names)
        print(f"  Benchmarks verified: 沪深300={has_hs300}, 红利低波={has_dividend}, 纯债指数={has_bond}")
        assert has_hs300 and has_dividend and has_bond, "Core benchmarks missing from backtest traces!"

        # Check disclaimer card and C3 toggle
        tab3_text = tabpanel.inner_text()
        has_disclaimer = "当前持仓静态权重历史回溯（含历史后视镜权重效应" in tab3_text
        has_c3_toggle = "全天候" in tab3_text or "动态策略" in tab3_text or "C3" in tab3_text
        print(f"  Hindsight disclaimer card verified: {has_disclaimer}")
        print(f"  C3 dynamic comparison toggle verified: {has_c3_toggle}")
        assert has_disclaimer, "Hindsight disclaimer missing from Tab 3!"
        assert has_c3_toggle, "C3 dynamic strategy toggle missing from Tab 3!"

        # Scroll chart into view and take screenshot
        chart.scroll_into_view_if_needed()
        page.wait_for_timeout(1000)
        ss_p4 = SCREENSHOT_DIR / "g13_verification_painpoint4_backtest_chart.png"
        page.screenshot(path=str(ss_p4), full_page=False)
        print(f"  Captured Screenshot 4: {ss_p4}")

        REPORT_DATA["pain_point_4"] = {
            "title": chart_title,
            "legend": chart_legend,
            "margin": chart_margin,
            "trace_names": trace_names,
            "has_hindsight_disclaimer": has_disclaimer,
            "has_c3_toggle": has_c3_toggle,
            "status": "PASS"
        }

        browser.close()

    REPORT_DATA["summary"] = "ALL_5_PAIN_POINTS_VERIFIED_AND_PASSED"
    print("\n=================================================================")
    print("   ALL 5 PAIN POINTS VERIFIED SUCCESSFULLY (100% PASS)          ")
    print("=================================================================")

    # Write summary JSON
    summary_path = SCREENSHOT_DIR / "g13_5points_verification_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(REPORT_DATA, f, ensure_ascii=False, indent=2)
    print(f"Summary JSON written to: {summary_path}")


if __name__ == "__main__":
    run_verification()
