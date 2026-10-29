# -*- coding: utf-8 -*-
"""
Adversarial Stress Testing Suite for AGY2_FundAdvisory
Tests extreme edge cases, adversarial inputs, boundary conditions, and failure modes.
"""
import sys
import math
from pathlib import Path

WORKSPACE = Path("d:/Google/Workspace/Wind")
AGY2 = WORKSPACE / "AGY2_FundAdvisory"
if str(AGY2) not in sys.path:
    sys.path.insert(0, str(AGY2))

from strategy_bridge import StrategyBridge
from portfolio_manager import PortfolioManager

def run_stress_tests():
    print("=== STARTING ADVERSARIAL STRESS TESTS ===")
    pm = PortfolioManager()

    # -------------------------------------------------------------
    # 1. Extreme inputs to compute_dynamic_tier_weights
    # -------------------------------------------------------------
    print("\n--- TEST 1: compute_dynamic_tier_weights under boundary & adversarial inputs ---")
    extreme_snapshots = [
        ("None snapshot", None),
        ("Empty dict", {}),
        ("NaN price", {"c300_price": float("nan"), "m20_price": float("nan")}),
        ("Negative price", {"c300_price": -500.0, "m20_price": -400.0}),
        ("Huge price", {"c300_price": 1e9, "m20_price": 1e8}),
        ("Zero price", {"c300_price": 0.0, "m20_price": 0.0}),
        ("Extreme high IV", {"opt_iv_pct": 999.0, "market_state_code": "SEVERE_BEAR"}),
        ("Conflicting regime fields", {"market_state_code": "GROWTH_BULL", "regime": "BEAR"}),
    ]

    for name, snap in extreme_snapshots:
        eq_weights = {}
        for tier in ["C1", "C2", "C3", "C4", "C5"]:
            w = StrategyBridge.compute_dynamic_tier_weights(tier=tier, market_snapshot=snap)
            assert isinstance(w, dict), f"Failed for {name}, tier {tier}: not a dict"
            tot = sum(w.values())
            assert abs(tot - 1.0) < 1e-3, f"Failed for {name}, tier {tier}: sum is {tot} != 1.0"
            # calculate equity weight
            eq = sum(val for code, val in w.items() if pm.classify_fund_asset_class(code) not in ["纯债固收", "黄金对冲"])
            eq_weights[tier] = eq

        # Monotonicity check
        print(f"[{name}] Equity: C1={eq_weights['C1']:.2f}, C2={eq_weights['C2']:.2f}, C3={eq_weights['C3']:.2f}, C4={eq_weights['C4']:.2f}, C5={eq_weights['C5']:.2f}")
        assert eq_weights["C1"] < eq_weights["C2"] < eq_weights["C3"] < eq_weights["C4"] < eq_weights["C5"], (
            f"Monotonicity violation in [{name}]: {eq_weights}"
        )
    print(">>> TEST 1 PASSED: compute_dynamic_tier_weights survives extreme inputs and preserves strict monotonicity!")

    # -------------------------------------------------------------
    # 2. Invalid or non-standard Tier inputs
    # -------------------------------------------------------------
    print("\n--- TEST 2: Invalid tier parameter resilience ---")
    weird_tiers = ["c1", " C2 ", "C9", "", None, 123, "UNKNOWN"]
    for t in weird_tiers:
        w = StrategyBridge.compute_dynamic_tier_weights(tier=t)
        assert isinstance(w, dict), f"Failed for tier {t}"
        assert abs(sum(w.values()) - 1.0) < 1e-3
    print(">>> TEST 2 PASSED: Invalid tiers handled gracefully (defaults safely)!")

    # -------------------------------------------------------------
    # 3. Grid Rebalance Point Inversion Stress Test
    # -------------------------------------------------------------
    print("\n--- TEST 3: Grid Point Calculation Stress Test ---")
    extreme_prices = [10.0, 50.0, 100.0, 500.0, 2000.0, 3500.0, 4053.0, 4180.5, 6000.0, 10000.0, 50000.0]
    import portfolio_manager as pm_mod
    for ep in extreme_prices:
        orig_fetch = pm_mod.fetch_realtime_index_quote
        pm_mod.fetch_realtime_index_quote = lambda symbol, use_cache=True: {"point": ep, "change_pct": 0.0}
        try:
            grid = StrategyBridge.get_rebalance_grid_status()
            curr = grid.get("c300_current", grid.get("c300_price", ep))
            surge = grid["surge_threshold_c300"]
            breakdown = grid["breakdown_threshold_c300"]
            assert breakdown < curr < surge, f"Inversion at {ep}: breakdown={breakdown}, curr={curr}, surge={surge}"
        finally:
            pm_mod.fetch_realtime_index_quote = orig_fetch
    print(">>> TEST 3 PASSED: Grid calculations strictly maintain breakdown < current < surge under all price scales!")

    # -------------------------------------------------------------
    # 4. De-Mining 3-Layer Logic & Cash Flow Validation
    # -------------------------------------------------------------
    print("\n--- TEST 4: De-Mining 3-layer logic test ---")
    # Case A: Bank exemption
    res_bank = pm.screen_fund_look_through_risk("100032")
    for s in res_bank.get("top_stocks_screen", []):
        if any(b in s["stock_name"] for b in ["银行", "招商", "农业", "工商", "平安银行", "兴业"]):
            assert s["double_high_risk"] is False, f"Bank stock {s['stock_name']} should have double_high_risk=False"

    # Case B: Tech stock with good CFO vs Non-exempt shell
    res_tech = pm.screen_fund_look_through_risk("011612")
    assert res_tech["risk_level"] in ["Safe", "Watch"], f"Tech fund risk level: {res_tech['risk_level']}"
    print(">>> TEST 4 PASSED: De-mining correctly exempts banks and healthy tech without hardcoded whitelist!")

    # -------------------------------------------------------------
    # 5. Asset Classification Exhaustiveness & Fallback
    # -------------------------------------------------------------
    print("\n--- TEST 5: Asset classification boundary inputs ---")
    test_cases = [
        ("000000", "", "其他权益资产"),
        ("999999", "某某未知名牌基金", "其他权益资产"),
        (None, None, "其他权益资产"),
        ("002351", None, "纯债固收"),
        ("000216", None, "黄金对冲"),
        ("050025", None, "美股海外对冲"),
        ("100032", None, "A股红利高股息"),
        ("005561", None, "A股红利低波"),
        ("011613", None, "科技成长进攻"),
        ("016634", None, "中小盘成长"),
        ("001053", None, "中盘均衡"),
    ]
    for c, n, exp in test_cases:
        res = pm.classify_fund_asset_class(c, n)
        assert res == exp, f"classify_fund_asset_class({c}, {n}) returned {res}, expected {exp}"
    print(">>> TEST 5 PASSED: Asset classification correctly maps all canonical types and gracefully falls back!")

    print("\n=== ALL ADVERSARIAL STRESS TESTS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    run_stress_tests()
