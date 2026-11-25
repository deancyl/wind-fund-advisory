# -*- coding: utf-8 -*-
"""
scripts/stress_test_r8_m2_sentry.py
Milestone 2 Adversarial Stress Test Script for 6D Risk Sentry Target Integrity & Action Buttons
"""

import sys
import os
import json
from pathlib import Path

# Ensure workspace root and AGY2_FundAdvisory are in sys.path
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))
sys.path.insert(0, str(WORKSPACE_ROOT / "AGY2_FundAdvisory"))

from AGY2_FundAdvisory.advisory_engine import ActiveRiskSentry, RADAR_SECTOR_CATALOG, OpportunityRadarEngine
from AGY2_FundAdvisory.portfolio_manager import PortfolioManager
from AGY2_FundAdvisory.data_loader import fetch_or_calc_index_valuations


def stress_test_part1_demo_portfolio():
    print("=" * 60)
    print("STRESS TEST PART 1: 6D Risk Sentry on Demo Portfolio")
    print("=" * 60)

    pm = PortfolioManager()
    pm.load_demo_portfolio()

    sentry = ActiveRiskSentry(watchdog_path="data/cache/test_watchdog.json")
    snapshot = {
        "c300_point": 4101.34,
        "trigger_lines": {"surge_line": 4192.0, "breakdown_line": 4034.0},
    }
    fund_metadata = {
        "005561": {"aum_billion": 15.6},
        "100032": {"aum_billion": 35.2},
        "011612": {"aum_billion": 12.0},
        "011613": {"aum_billion": 22.0},
        "013841": {"aum_billion": 8.5},
        "001071": {"aum_billion": 18.0},
    }

    report = sentry.inspect_portfolio(pm.holdings, snapshot, fund_metadata)
    alerts = report["alerts"]

    print(f"Total alerts generated: {len(alerts)}")
    for i, a in enumerate(alerts, 1):
        print(f"  [{i}] level={a.get('level')} dim={a.get('dimension')} code={a.get('fund_code')} act={a.get('action_type')} title={a.get('title')}")

    # 1. Assert 011612 (holding 3 days) triggers Dimension 1 red lock (<7 days)
    red_locks = [a for a in alerts if a.get("fund_code") == "011612" and a.get("dimension") == "未满7天锁仓"]
    assert len(red_locks) >= 1, "011612 must trigger Dimension 1 未满7天锁仓"
    assert red_locks[0]["level"] == "red", f"011612 level must be red, got {red_locks[0]['level']}"
    assert red_locks[0]["action_type"] == "lock_shares", f"011612 action_type must be lock_shares, got {red_locks[0]['action_type']}"
    assert "≤3天" in red_locks[0]["title"], f"011612 title must contain '≤3天', got {red_locks[0]['title']}"
    print("  [PASS] 011612 Dimension 1 red lock verified.")

    # 2. Assert 011613 (holding 28 days) triggers Dimension 2 yellow countdown hold (diff of 2 days to 30d zero fee)
    countdown_holds = [a for a in alerts if a.get("fund_code") == "011613" and a.get("dimension") == "临免赎期倒计时"]
    assert len(countdown_holds) >= 1, "011613 must trigger Dimension 2 临免赎期倒计时"
    assert countdown_holds[0]["level"] == "yellow", f"011613 level must be yellow, got {countdown_holds[0]['level']}"
    assert countdown_holds[0]["action_type"] == "countdown_hold", f"011613 action_type must be countdown_hold, got {countdown_holds[0]['action_type']}"
    assert "差 2 天" in countdown_holds[0]["title"], f"011613 title must contain '差 2 天', got {countdown_holds[0]['title']}"
    print("  [PASS] 011613 Dimension 2 yellow countdown hold verified.")

    # 3. Assert 013841 (floating loss -16.19%) triggers Dimension 4 deep loss rebalance & Dimension 3 (C class >=30d)
    deep_loss = [a for a in alerts if a.get("fund_code") == "013841" and a.get("dimension") == "深套诊断"]
    assert len(deep_loss) >= 1, "013841 must trigger Dimension 4 深套诊断"
    assert deep_loss[0]["level"] == "yellow"
    assert deep_loss[0]["action_type"] == "deep_loss_rebalance"
    assert "-16.2%" in deep_loss[0]["title"] or "-16.1%" in deep_loss[0]["title"] or "16" in deep_loss[0]["title"]

    c_class_switch = [a for a in alerts if a.get("fund_code") == "013841" and a.get("dimension") == "C类零费率置换"]
    assert len(c_class_switch) >= 1, "013841 (40 days C class) must trigger Dimension 3 C类零费率置换"
    assert c_class_switch[0]["level"] == "yellow"
    assert c_class_switch[0]["action_type"] == "switch_a_class"
    print("  [PASS] 013841 Dimension 4 deep loss rebalance & Dimension 3 C class switch verified.")

    # 4. Assert sector concentration alert fires when a sector exceeds 35%
    sec_con = [a for a in alerts if a.get("dimension") == "赛道集中度"]
    assert len(sec_con) >= 1, "Sector concentration alert must fire for demo portfolio (>35%)"
    assert sec_con[0]["level"] == "yellow"
    assert sec_con[0]["action_type"] == "rebalance_sector"
    assert "红利高股息" in sec_con[0]["title"]
    print(f"  [PASS] Sector concentration alert verified: {sec_con[0]['title']}")

    # 5. Assert component stock overlap alert fires when multiple holdings share heavy weights in same underlying stocks (e.g. 011612 + 011613 in STAR 50)
    overlap = [a for a in alerts if a.get("dimension") == "重仓股重叠"]
    assert len(overlap) >= 1, "Component stock overlap alert must fire for 011612 and 011613 (STAR 50)"
    assert overlap[0]["level"] == "yellow"
    assert overlap[0]["action_type"] == "switch_a_class"
    assert "011612" in overlap[0]["title"] and "011613" in overlap[0]["title"]
    print(f"  [PASS] Component stock overlap alert verified: {overlap[0]['title']}")


def stress_test_part2_boundary_values():
    print("\n" + "=" * 60)
    print("STRESS TEST PART 2: Boundary Value Stress Testing")
    print("=" * 60)

    sentry = ActiveRiskSentry(watchdog_path="data/cache/test_watchdog.json")

    # Boundary 1: Synthetic holding with exactly 7 days: confirm NO red lock fires
    holding_7d = [{
        "code": "009999",
        "name": "测试红利A",
        "holding_days": 7,
        "share_class": "A",
        "batches": [{"holding_days": 7, "shares": 1000}],
        "market_value": 10000.0,
        "floating_pnl_pct": 2.0,
        "bias_20": 1.0,
    }]
    rep_7d = sentry.inspect_portfolio(holding_7d)
    alerts_7d = rep_7d["alerts"]
    red_lock_7d = [a for a in alerts_7d if a.get("level") == "red" and a.get("dimension") == "未满7天锁仓"]
    assert len(red_lock_7d) == 0, f"Holding exactly 7 days must NOT trigger red lock, found: {red_lock_7d}"
    
    # Check green notice for exactly 7 days
    green_7d = [a for a in alerts_7d if a.get("level") == "green_notice" and a.get("dimension") == "未满7天锁仓"]
    assert len(green_7d) == 1, "Holding exactly 7 days should trigger green notice that 7-day penalty lock is lifted"
    assert green_7d[0]["action_type"] == "rebalance_normal"
    print("  [PASS] Boundary 1 (exact 7 days): NO red lock fires, green unlock notice fires.")

    # Also test boundary 6 days: confirm red lock DOES fire
    holding_6d = [{
        "code": "009998",
        "name": "测试红利A6天",
        "holding_days": 6,
        "share_class": "A",
        "batches": [{"holding_days": 6, "shares": 1000}],
        "market_value": 10000.0,
        "floating_pnl_pct": 0.0,
        "bias_20": 0.0,
    }]
    rep_6d = sentry.inspect_portfolio(holding_6d)
    red_lock_6d = [a for a in rep_6d["alerts"] if a.get("level") == "red" and a.get("dimension") == "未满7天锁仓"]
    assert len(red_lock_6d) == 1, "Holding 6 days MUST trigger red lock"
    assert red_lock_6d[0]["action_type"] == "lock_shares"
    print("  [PASS] Boundary 1b (6 days vs 7 days boundary): 6 days triggers red lock, 7 days does not.")

    # Boundary 2: Synthetic holding with exactly 30 days C class: confirm NO yellow countdown fires, but Dimension 3 zero fee switch fires
    holding_30d_c = [{
        "code": "009997",
        "name": "测试成长C",
        "holding_days": 30,
        "share_class": "C",
        "batches": [{"holding_days": 30, "shares": 1000}],
        "market_value": 10000.0,
        "floating_pnl_pct": 1.0,
        "bias_20": 0.5,
    }]
    rep_30d = sentry.inspect_portfolio(holding_30d_c)
    alerts_30d = rep_30d["alerts"]
    countdown_30d = [a for a in alerts_30d if a.get("dimension") == "临免赎期倒计时"]
    assert len(countdown_30d) == 0, f"Holding exactly 30 days C class must NOT trigger countdown, got: {countdown_30d}"
    
    switch_30d = [a for a in alerts_30d if a.get("dimension") == "C类零费率置换"]
    assert len(switch_30d) == 1, "Holding exactly 30 days C class MUST trigger Dimension 3 zero fee switch"
    assert switch_30d[0]["level"] == "yellow"
    assert switch_30d[0]["action_type"] == "switch_a_class"
    print("  [PASS] Boundary 2 (exact 30 days C class): NO countdown fires, Dimension 3 zero fee switch fires.")

    # Boundary 2b: 29 days C class vs 30 days
    holding_29d_c = [{
        "code": "009996",
        "name": "测试成长C29天",
        "holding_days": 29,
        "share_class": "C",
        "batches": [{"holding_days": 29, "shares": 1000}],
        "market_value": 10000.0,
        "floating_pnl_pct": 1.0,
        "bias_20": 0.5,
    }]
    rep_29d = sentry.inspect_portfolio(holding_29d_c)
    countdown_29d = [a for a in rep_29d["alerts"] if a.get("dimension") == "临免赎期倒计时"]
    switch_29d = [a for a in rep_29d["alerts"] if a.get("dimension") == "C类零费率置换"]
    assert len(countdown_29d) == 1, "29 days C class MUST trigger countdown"
    assert "差 1 天" in countdown_29d[0]["title"]
    assert len(switch_29d) == 0, "29 days C class must NOT trigger zero fee switch yet"
    print("  [PASS] Boundary 2b (29 days vs 30 days C class): 29d triggers countdown (差1天), 30d triggers zero fee switch.")

    # Boundary 3: Synthetic offensive fund with profit +16% and Bias20 +7%: confirm laddered profit taking fires
    holding_profit = [{
        "code": "009995",
        "name": "高弹性成长A",
        "holding_days": 50,
        "share_class": "A",
        "batches": [{"holding_days": 50, "shares": 1000}],
        "market_value": 15000.0,
        "floating_pnl_pct": 16.0,
        "bias_20": 7.0,
    }]
    rep_profit = sentry.inspect_portfolio(holding_profit)
    alerts_profit = rep_profit["alerts"]
    take_profit_alerts = [a for a in alerts_profit if a.get("action_type") == "take_profit"]
    assert len(take_profit_alerts) >= 1, "Profit +16% and Bias20 +7% MUST trigger take profit action"
    print(f"  [PASS] Boundary 3 (profit +16% & bias +7%): take_profit fired ({take_profit_alerts[0]['dimension']}: {take_profit_alerts[0]['title']})")

    # Also test profit +16% with bias 5.5% (triggers explicit '阶梯止盈' dimension)
    holding_profit_ladder = [{
        "code": "009994",
        "name": "高弹性成长A阶梯",
        "holding_days": 50,
        "share_class": "A",
        "batches": [{"holding_days": 50, "shares": 1000}],
        "market_value": 15000.0,
        "floating_pnl_pct": 16.0,
        "bias_20": 5.5,
    }]
    rep_ladder = sentry.inspect_portfolio(holding_profit_ladder)
    ladder_alerts = [a for a in rep_ladder["alerts"] if a.get("dimension") == "阶梯止盈"]
    assert len(ladder_alerts) == 1, "Profit +16% and Bias20 5.5% MUST trigger 阶梯止盈 dimension"
    assert ladder_alerts[0]["action_type"] == "take_profit"
    assert "触发阶梯止盈" in ladder_alerts[0]["title"]
    print("  [PASS] Boundary 3b (profit +16% & bias 5.5%): explicit 阶梯止盈 dimension verified.")

    # Boundary 4: Synthetic fund with AUM 0.3亿 (<0.5亿): confirm mini fund liquidation alert fires
    holding_mini = [{
        "code": "009993",
        "name": "迷你微盘混合A",
        "holding_days": 45,
        "share_class": "A",
        "batches": [{"holding_days": 45, "shares": 1000}],
        "market_value": 10000.0,
        "floating_pnl_pct": 0.0,
        "bias_20": 0.0,
    }]
    fund_meta_mini = {"009993": {"aum_billion": 0.30}}
    rep_mini = sentry.inspect_portfolio(holding_mini, fund_metadata=fund_meta_mini)
    mini_alerts = [a for a in rep_mini["alerts"] if a.get("dimension") == "本体排雷"]
    assert len(mini_alerts) == 1, "Fund with AUM 0.3亿 (<0.5亿) MUST trigger mini fund liquidation alert"
    assert mini_alerts[0]["level"] == "red"
    assert mini_alerts[0]["action_type"] == "replace_fund"
    assert "<0.5亿清盘警戒线" in mini_alerts[0]["title"]
    assert "0.30" in mini_alerts[0]["title"]
    print("  [PASS] Boundary 4 (AUM 0.3亿 < 0.5亿): mini fund liquidation alert verified.")

    # Boundary 4b: Fund with AUM 0.50亿 and 0.60亿 (boundary threshold check)
    fund_meta_safe = {"009993": {"aum_billion": 0.50}}
    rep_safe = sentry.inspect_portfolio(holding_mini, fund_metadata=fund_meta_safe)
    mini_safe_alerts = [a for a in rep_safe["alerts"] if a.get("dimension") == "本体排雷"]
    assert len(mini_safe_alerts) == 0, "Fund with AUM exactly 0.50亿 must NOT trigger mini fund alert"
    print("  [PASS] Boundary 4b (AUM exactly 0.50亿): mini fund alert does NOT fire.")


def stress_test_part3_all_action_buttons_coverage():
    print("\n" + "=" * 60)
    print("STRESS TEST PART 3: Action Buttons Exhaustive Coverage")
    print("=" * 60)

    # We want to test that all 6 dimensional warning card types can generate their respective action types
    # and that app_gui.py has handlers for every single action type:
    expected_actions = [
        "lock_shares",           # Dim 1
        "countdown_hold",        # Dim 2
        "switch_a_class",         # Dim 3 / Dim 5 overlap
        "take_profit",           # Dim 4
        "deep_loss_rebalance",   # Dim 4
        "rebalance_sector",      # Dim 5
        "replace_fund",          # Dim 6 (mini fund)
        "defense_mode",          # Dim 6 (c300 breakdown)
        "offense_mode",          # Dim 6 (c300 surge)
    ]

    with open("AGY2_FundAdvisory/app_gui.py", "r", encoding="utf-8") as f:
        gui_code = f.read()

    for act in expected_actions:
        assert f'act_type == "{act}"' in gui_code, f"app_gui.py must handle action_type: {act}"
        print(f"  [PASS] Verified app_gui.py handles action_type: {act}")


if __name__ == "__main__":
    stress_test_part1_demo_portfolio()
    stress_test_part2_boundary_values()
    stress_test_part3_all_action_buttons_coverage()
    print("\n" + "=" * 60)
    print("ALL EMPIRICAL STRESS TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)
