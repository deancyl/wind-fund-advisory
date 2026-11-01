# -*- coding: utf-8 -*-
"""
Tests for UI and logic refinements:
1. Visual contrast & card styles (clean white cards, dark titles, dark high-contrast body text).
2. State logic fix (severe bear only triggered when c300 breaks MA60 & MA120 with MA diverging downward).
3. Fund selection funnel stats (28,177 -> 6,850 -> 20 -> 5) & elimination of 005561 collision in alternatives.
4. Smart split-order cheat sheet for quota-limited funds (050025 -> 500 + 5500 into 001071).
5. Step 1 first-screen compaction inside border container.
"""

import pytest
import math
import re
from pathlib import Path

from portfolio_manager import (
    SECTOR_FUND_SELECTION,
    CORE_STRATEGY_POOL,
    FUND_LOOK_THROUGH_DATA,
    get_fund_selection_funnel_stats,
    PortfolioManager,
)
from strategy_bridge import StrategyBridge


class TestUIAndLogicRefinements:
    """Test suite for the 5 targeted UI and logic refinements."""

    def test_visual_contrast_and_card_colors_in_app_gui(self):
        """Item 1: Ensure high-contrast dark text and bold titles in app_gui.py."""
        gui_path = Path(__file__).resolve().parent.parent / "app_gui.py"
        content = gui_path.read_text(encoding="utf-8")

        # 1. Check attribution card titles have high-contrast dark colors
        assert "#b91c1c" in content, "Attribution card ① title should be dark red #b91c1c"
        assert "#15803d" in content, "Attribution card ② title should be dark green #15803d"
        assert "#b45309" in content, "Attribution card ③ title should be dark amber #b45309"
        assert "#0369a1" in content, "Attribution card ④ title should be dark blue #0369a1"

        # 2. Check no light grey #cbd5e1 is used as text color in attribution cards
        # (It should only appear as card borders: border: 1px solid #cbd5e1)
        matches_cbd_color = re.findall(r"color:\s*#cbd5e1", content, re.IGNORECASE)
        assert len(matches_cbd_color) == 0, f"Found unexpected text color #cbd5e1: {matches_cbd_color}"

        # 3. Check Tab 2 main metric cards sublabels use dark grey #64748b instead of #94a3b8
        assert 'style="font-size:11px; color:#64748b;"' in content

        # 4. Check dual-track box has dark text and dark red title
        assert 'color: #b91c1c; font-size: 14px; margin-bottom: 4px;' in content
        assert 'color: #1e293b; line-height: 1.6;' in content

        # 5. Check late-market notice card uses #a16207 title and #1e293b text
        assert "color: #a16207;" in content
        assert "color: #fef08a;" not in content

        # 6. Check .decision-card has clean white background
        assert ".decision-card {" in content
        assert "background: #ffffff;" in content

        # 7. Check top countdown banner is clean white card (no dark gradient)
        assert "linear-gradient(135deg, #1e293b 0%, #0f172a 100%)" not in content
        assert "🕒 交易时钟与窗口" in content or "📅 <b>调仓网格倒计时</b>" in content

        # 8. Check funnel step 3 displays candidate_funds (20 只)
        assert 'st.metric("3. 5大赛道入围池", f"{funnel_stats[\'candidate_funds\']} 只"' in content

    def test_market_state_severe_bear_strict_condition(self):
        """Item 2: Severe bear should ONLY trigger when c300 simultaneously breaks MA60 and MA120 with MA diverging."""
        snapshot = StrategyBridge.get_latest_market_snapshot(force_reload=True)
        state_code = snapshot.get("market_state_code")
        state_name = snapshot.get("market_state_name", snapshot.get("market_state"))
        c300_close = snapshot.get("c300_price", 0.0)
        m60 = snapshot.get("m60_price", 0.0)

        # When c300 is above MA60, it MUST NOT be evaluated as SEVERE_BEAR
        assert c300_close >= m60, f"c300 ({c300_close}) should be >= m60 ({m60})"
        assert state_code != "SEVERE_BEAR", f"c300 ({c300_close}) >= m60 ({m60}) but got {state_code}"
        assert state_code == "STABLE_DIVIDEND"
        assert "深度大熊市防御" not in state_name

        # Weights consistency: top card weights match snapshot
        w_funds = snapshot.get("target_weights_funds", {})
        assert w_funds.get("100032", 0.0) == 0.38
        assert w_funds.get("005561", 0.0) == 0.30
        assert w_funds.get("002351", 0.0) == 0.12

        # Intraday signal evaluation strictness
        # Case A: Above MA60 (e.g. 4050.0) -> Never severe bear
        sig_above = StrategyBridge.evaluate_intraday_signal(
            realtime_c300=4050.0,
            current_time_str="14:45"
        )
        assert sig_above.get("simulated_state_code") != "SEVERE_BEAR"
        assert sig_above.get("simulated_state_code") == "STABLE_DIVIDEND"
        assert "深度大熊市防御" not in sig_above.get("simulated_state", "")

        # Case B: Below MA60 & MA120 (e.g. 3600.0) -> MUST trigger severe bear
        sig_below = StrategyBridge.evaluate_intraday_signal(
            realtime_c300=3600.0,
            current_time_str="14:55"
        )
        assert sig_below.get("simulated_state_code") == "SEVERE_BEAR"
        assert "深度大熊市防御" in sig_below.get("simulated_state", "")
        assert sig_below.get("is_state_changed") is True
        assert sig_below.get("action_urgency") == "URGENT_CHANGE"

    def test_fund_selection_funnel_and_alternatives_collision(self):
        """Item 3: Funnel stats 28,177 -> 6,850 -> 20 -> 5 and 005561 replaced in alternatives."""
        stats = get_fund_selection_funnel_stats()
        assert stats["total_market_funds"] == 28177
        assert stats["hard_filtered_funds"] == 6850
        assert stats["candidate_funds"] == 20
        assert stats["final_champion_funds"] == 5

        # 005561 must NOT be in CORE_DIVIDEND alternatives to prevent collision
        core_div = SECTOR_FUND_SELECTION["CORE_DIVIDEND"]
        alt_codes = [a["code"] if isinstance(a, dict) else a for a in core_div["alternatives"]]
        top_alt_codes = [a["code"] if isinstance(a, dict) else a for a in core_div["top_alternatives"]]
        assert "005561" not in alt_codes, "005561 must not collide in alternatives"
        assert "005561" not in top_alt_codes, "005561 must not collide in top_alternatives"

        # 090010 and 012643 must be present
        assert "090010" in alt_codes
        assert "012643" in alt_codes
        assert "090010" in top_alt_codes
        assert "012643" in top_alt_codes
        assert "090010" in CORE_STRATEGY_POOL
        assert "012643" in CORE_STRATEGY_POOL
        assert "090010" in FUND_LOOK_THROUGH_DATA
        assert "012643" in FUND_LOOK_THROUGH_DATA

    def test_smart_split_order_blueprint(self):
        """Item 4: Smart split-order when allocation exceeds daily_limit (050025 > 500)."""
        bp = StrategyBridge.generate_zero_start_blueprint(total_capital=100000.0, tier="C3")
        items = bp["items"]

        # Find 050025 item
        spx_item = next((it for it in items if it["fund_code"] == "050025"), None)
        assert spx_item is not None, "050025 should be in C3 blueprint"
        assert spx_item["has_split"] is True, "050025 should trigger has_split when > 500"

        s_info = spx_item["split_info"]
        assert s_info["daily_limit"] == 500.0
        assert s_info["today_amount"] == 500.0
        assert s_info["excess_amount"] == 5500.0
        assert s_info["fallback_code"] == "001071"
        assert "今日先买 ¥500.00" in s_info["instruction"]
        assert "剩余 ¥5,500.00 直接买入不限购备选【001071 摩根标普500A】" in s_info["instruction"]
        assert "分12天定投" in s_info["instruction"]

        # Verify portfolio manager application splits holdings correctly
        pm = PortfolioManager()
        res = pm.apply_zero_start_blueprint(bp)
        assert res["status"] == "SUCCESS"
        assert "050025" in pm.holdings
        assert "001071" in pm.holdings
        assert 490.0 <= pm.holdings["050025"].market_value <= 510.0
        assert 5400.0 <= pm.holdings["001071"].market_value <= 5600.0

    def test_first_screen_step1_compaction(self):
        """Item 5: Step 1 enclosed in container(border=True) with scenario, capital, and button."""
        gui_path = Path(__file__).resolve().parent.parent / "app_gui.py"
        content = gui_path.read_text(encoding="utf-8")

        # Check st.container(border=True) is used for Step 1
        assert "with st.container(border=True):" in content
        assert "tier_determination_mode" in content or "gui_scenario_mode_v2" in content
        assert "plan_capital_input" in content
        assert "btn_run_simulation_now" in content
