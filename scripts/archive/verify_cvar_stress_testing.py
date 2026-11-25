"""
Empirical Adversarial Verification Harness: Multi-Period Monte Carlo Stress Testing
(scripts/verify_cvar_stress_testing.py)

Mission:
Adversarially verify the mathematical and financial correctness of:
1. Multi-period Monte Carlo stress testing in PortfolioManager.simulate_portfolio_cvar_bootstrap across C1-C5.
2. Fundamental risk axioms: CVaR_99 >= VaR_99 >= VaR_95 across all scenarios.
3. Realistic and differentiated drawdown levels (2008 deepest MDD, 2015 highest LiqDays, 2024 structural divergence).
4. Determinism, FIFO locks (holding_days < 7), and Top 5 ADV scaling.
5. Risk tolerance gating (C1 triggers breach, C5 within limits for moderate equity).
"""

import sys
from pathlib import Path
import numpy as np

# Ensure workspace and AGY2 are in sys.path
_WORKSPACE = Path(__file__).resolve().parent.parent
_AGY2_DIR = _WORKSPACE / "AGY2_FundAdvisory"
if str(_AGY2_DIR) not in sys.path:
    sys.path.insert(0, str(_AGY2_DIR))
if str(_WORKSPACE) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE))

from AGY2_FundAdvisory.portfolio_manager import PortfolioManager, simulate_portfolio_cvar_bootstrap


def run_adversarial_suite():
    print("=" * 80)
    print("EMPIRICAL ADVERSARIAL VERIFICATION HARNESS: CVAR MONTE CARLO STRESS TESTING")
    print("=" * 80)

    findings = []

    # ---------------------------------------------------------
    # 1. Representative Portfolios Setup
    # ---------------------------------------------------------
    representative_portfolios = {
        "HighEquity_Growth": {
            "011613": {"market_value": 60000.0, "fund_name": "华夏科创50联接A", "holding_days": 30},
            "161725": {"market_value": 40000.0, "fund_name": "招商中证白酒指数A", "holding_days": 30},
        },
        "Balanced_Core": {
            "005561": {"market_value": 35000.0, "fund_name": "创金合信红利低波A", "holding_days": 30},
            "100032": {"market_value": 20000.0, "fund_name": "富国中证红利增强A", "holding_days": 30},
            "161725": {"market_value": 15000.0, "fund_name": "招商中证白酒指数A", "holding_days": 30},
            "002351": {"market_value": 15000.0, "fund_name": "易方达裕祥回报债券A", "holding_days": 30},
            "000216": {"market_value": 15000.0, "fund_name": "华安易富黄金ETF联接A", "holding_days": 30},
        },
        "Moderate_Equity": {
            "005561": {"market_value": 50000.0, "fund_name": "创金合信红利低波A", "holding_days": 30},
            "002351": {"market_value": 30000.0, "fund_name": "易方达裕祥回报债券A", "holding_days": 30},
            "000216": {"market_value": 20000.0, "fund_name": "华安易富黄金ETF联接A", "holding_days": 30},
        },
        "Pure_Star50_Tech": {
            "011613": {"market_value": 100000.0, "fund_name": "华夏科创50联接A", "holding_days": 30},
        },
        "Pure_Bond": {
            "002351": {"market_value": 100000.0, "fund_name": "易方达裕祥回报债券A", "holding_days": 30},
        },
        "Pure_Gold": {
            "000216": {"market_value": 100000.0, "fund_name": "华安易富黄金ETF联接A", "holding_days": 30},
        },
    }

    tiers = ["C1", "C2", "C3", "C4", "C5"]

    # ---------------------------------------------------------
    # CHECK 1: Mathematical Risk Axioms across portfolios and risk tiers
    # Axiom: CVaR_99 >= VaR_99 >= VaR_95 across all scenarios
    # ---------------------------------------------------------
    print("\n[CHECK 1] Testing Mathematical Risk Axioms across portfolios and risk tiers...")
    total_axiom_checks = 0
    axiom_failures = 0
    for p_name, p_holdings in representative_portfolios.items():
        for tier in tiers:
            res = simulate_portfolio_cvar_bootstrap(
                holdings=p_holdings,
                total_capital=100000.0,
                investor_risk_tier=tier,
                n_simulations=3000,
                random_seed=123
            )
            for sc in res["scenarios"]:
                sc_id = sc["id"]
                v95 = sc["var_95_pct"]
                v99 = sc["var_99_pct"]
                cvar99 = sc["cvar_99_pct"]
                tot_cvar = sc["total_cvar_99_pct"]
                pred_mdd = sc["predicted_mdd_pct"]

                if not (cvar99 >= v99 >= v95):
                    axiom_failures += 1
                    print(f"  FAILED Axiom: {cvar99} >= {v99} >= {v95} broken in {p_name} / {tier} / {sc_id}")
                if pred_mdd < v95:
                    axiom_failures += 1
                    print(f"  FAILED Pred MDD: {pred_mdd} < VaR95 {v95} in {p_name} / {tier} / {sc_id}")
                if tot_cvar < cvar99:
                    axiom_failures += 1
                    print(f"  FAILED Total CVaR: {tot_cvar} < CVaR99 {cvar99} in {p_name} / {tier} / {sc_id}")
                total_axiom_checks += 1

    if axiom_failures == 0:
        print(f"  -> PASS: All {total_axiom_checks} scenario risk axiom checks verified (CVaR_99 >= VaR_99 >= VaR_95).")
    else:
        findings.append(f"Mathematical risk axiom failure in {axiom_failures} instances.")

    # ---------------------------------------------------------
    # CHECK 2: Scenario Realism and Differentiation
    # ---------------------------------------------------------
    print("\n[CHECK 2] Testing Scenario Realism and Differentiation...")
    for p_name in ["HighEquity_Growth", "Balanced_Core", "Pure_Star50_Tech"]:
        p_holdings = representative_portfolios[p_name]
        res = simulate_portfolio_cvar_bootstrap(
            holdings=p_holdings,
            total_capital=100000.0,
            investor_risk_tier="C3",
            n_simulations=3000,
            random_seed=42
        )
        sc_map = {s["id"]: s for s in res["scenarios"]}
        sc_2008 = sc_map["2008_financial_crisis"]
        sc_2015 = sc_map["2015_liquidity_stampede"]
        sc_2024 = sc_map["2024_smallcap_liquidity"]

        assert sc_2008["predicted_mdd_pct"] > sc_2015["predicted_mdd_pct"]
        assert sc_2008["predicted_mdd_pct"] > sc_2024["predicted_mdd_pct"]
        liq_2015 = sc_2015["liquidation_days"]["avg_days"]
        liq_2008 = sc_2008["liquidation_days"]["avg_days"]
        liq_2024 = sc_2024["liquidation_days"]["avg_days"]
        assert liq_2015 > liq_2008
        assert liq_2015 > liq_2024
        print(f"  {p_name}: 2008 MDD={sc_2008['predicted_mdd_pct']}% (deepest), "
              f"2015 LiqDays={liq_2015} (highest), 2024 MDD={sc_2024['predicted_mdd_pct']}%")

    print("  -> PASS: Scenario differentiation verified: 2008 has deepest equity drawdown, 2015 has highest liquidation days.")

    # ---------------------------------------------------------
    # CHECK 3: Determinism & Top 5 ADV scaling
    # ---------------------------------------------------------
    print("\n[CHECK 3] Testing Determinism and Top 5 ADV Capacity Scaling...")
    res1 = simulate_portfolio_cvar_bootstrap(holdings=representative_portfolios["Balanced_Core"], random_seed=777)
    res2 = simulate_portfolio_cvar_bootstrap(holdings=representative_portfolios["Balanced_Core"], random_seed=777)
    for s1, s2 in zip(res1["scenarios"], res2["scenarios"]):
        assert s1["predicted_mdd_pct"] == s2["predicted_mdd_pct"]
        assert s1["liquidation_days"]["avg_days"] == s2["liquidation_days"]["avg_days"]
    print("  -> PASS: Deterministic repeatability verified.")

    res_small_cap = simulate_portfolio_cvar_bootstrap(
        holdings={"011613": {"market_value": 10000.0, "holding_days": 30}},
        total_capital=10000.0
    )
    res_huge_cap = simulate_portfolio_cvar_bootstrap(
        holdings={"011613": {"market_value": 50000000000.0, "holding_days": 30}},
        total_capital=50000000000.0
    )
    d_small = res_small_cap["scenarios"][0]["liquidation_days"]["avg_days"]
    d_huge = res_huge_cap["scenarios"][0]["liquidation_days"]["avg_days"]
    assert d_huge > d_small, f"Expected 50B liq days ({d_huge}) > 10k liq days ({d_small})"
    print(f"  -> PASS: Top 5 ADV capacity scaling verified: 10k capital={d_small}d, 50B capital={d_huge}d.")

    # ---------------------------------------------------------
    # CHECK 4: Risk Tolerance Tiers (C1 vs C5)
    # ---------------------------------------------------------
    print("\n[CHECK 4] Testing Investor Risk Tolerance Gating (C1 vs C5)...")
    res_c1 = simulate_portfolio_cvar_bootstrap(
        holdings=representative_portfolios["Moderate_Equity"],
        total_capital=100000.0,
        investor_risk_tier="C1",
        random_seed=42
    )
    res_c5 = simulate_portfolio_cvar_bootstrap(
        holdings=representative_portfolios["Moderate_Equity"],
        total_capital=100000.0,
        investor_risk_tier="C5",
        random_seed=42
    )
    worst_mdd = res_c1["scenarios"][0]["predicted_mdd_pct"]
    print(f"  Moderate Equity MDD: {worst_mdd}%, C1 limit: {res_c1['risk_tolerance_mdd']}%, C5 limit: {res_c5['risk_tolerance_mdd']}%")
    assert res_c1["exceeds_risk_tolerance"] is True, "C1 conservative must trigger breach on equity portfolio"
    assert res_c5["exceeds_risk_tolerance"] is False, "C5 aggressive must be within limits for moderate equity portfolio"
    print("  -> PASS: C1 conservative triggers exceeds_risk_tolerance=True, while C5 aggressive remains within limits.")

    # ---------------------------------------------------------
    # CHECK 5: FIFO Lock Accountability (ADVERSARIAL STRESS TEST)
    # ---------------------------------------------------------
    print("\n[CHECK 5] ADVERSARIAL TEST: FIFO 7-Day Lock Penalty Defense...")
    # Case A: Dictionary input with holding_days=2
    p_locked_dict = {
        "005561": {"market_value": 100000.0, "fund_name": "创金合信红利低波A", "holding_days": 2}
    }
    p_unlocked_dict = {
        "005561": {"market_value": 100000.0, "fund_name": "创金合信红利低波A", "holding_days": 30}
    }
    res_dict_l = simulate_portfolio_cvar_bootstrap(holdings=p_locked_dict, total_capital=100000.0)
    res_dict_u = simulate_portfolio_cvar_bootstrap(holdings=p_unlocked_dict, total_capital=100000.0)
    days_dict_l = res_dict_l["scenarios"][0]["liquidation_days"]["avg_days"]
    days_dict_u = res_dict_u["scenarios"][0]["liquidation_days"]["avg_days"]
    diff_dict = round(days_dict_l - days_dict_u, 1)

    print(f"  Dict input (holding_days=2): liquidation_days={days_dict_l}")
    print(f"  Dict input (holding_days=30): liquidation_days={days_dict_u}")
    print(f"  Dict difference: {diff_dict} days (expected 5.0 days penalty)")

    if diff_dict != 5.0:
        msg = (
            f"CRITICAL BUG: simulate_portfolio_cvar_bootstrap fails to account for FIFO locks when holdings are passed as dicts! "
            f"Got diff={diff_dict} days instead of 5.0 days. "
            f"Root cause in portfolio_manager.py:8677: 'getattr(v, \"holding_days\", 30)' returns default 30 on dict objects, "
            f"and '30 or ...' short-circuits, completely ignoring v['holding_days']."
        )
        print(f"  -> FAIL: {msg}")
        findings.append(msg)
    else:
        print("  -> PASS: Dict FIFO lock verified.")

    # Case B: PortfolioManager real FundHolding instance
    pm_locked = PortfolioManager(db_path=":memory:")
    pm_locked.add_or_update_holding("005561", shares=10000.0, nav=1.5, holding_days=2)
    pm_unlocked = PortfolioManager(db_path=":memory:")
    pm_unlocked.add_or_update_holding("005561", shares=10000.0, nav=1.5, holding_days=30)

    res_pm_l = pm_locked.simulate_portfolio_cvar_bootstrap_instance()
    res_pm_u = pm_unlocked.simulate_portfolio_cvar_bootstrap_instance()
    days_pm_l = res_pm_l["scenarios"][0]["liquidation_days"]["avg_days"]
    days_pm_u = res_pm_u["scenarios"][0]["liquidation_days"]["avg_days"]
    diff_pm = round(days_pm_l - days_pm_u, 1)

    print(f"  PM instance (holding_days=2 in batch): liquidation_days={days_pm_l}")
    print(f"  PM instance (holding_days=30 in batch): liquidation_days={days_pm_u}")
    print(f"  PM instance difference: {diff_pm} days (expected 5.0 days penalty)")

    if diff_pm != 5.0:
        msg = (
            f"CRITICAL BUG: simulate_portfolio_cvar_bootstrap_instance fails to account for FIFO locks in real FundHolding batches! "
            f"Got diff={diff_pm} days instead of 5.0 days. "
            f"Root cause: FundHolding instances store holding days in h.batches, but portfolio_manager.py:8677 only checks "
            f"getattr(v, 'holding_days', 30), returning 30 and ignoring batches."
        )
        print(f"  -> FAIL: {msg}")
        findings.append(msg)
    else:
        print("  -> PASS: PM FundHolding FIFO lock verified.")

    # Case C: Calling simulate_portfolio_cvar_bootstrap with holdings=None, pm_instance=pm
    print("\n[CHECK 6] ADVERSARIAL TEST: simulate_portfolio_cvar_bootstrap(holdings=None, pm_instance=pm)...")
    try:
        PortfolioManager.simulate_portfolio_cvar_bootstrap(holdings=None, pm_instance=pm_locked)
        print("  -> PASS: pm_instance call succeeded.")
    except Exception as e:
        msg = (
            f"CRITICAL BUG: simulate_portfolio_cvar_bootstrap(holdings=None, pm_instance=pm) crashes with: "
            f"{type(e).__name__}: {e}. "
            f"Root cause in portfolio_manager.py:8697: 'holding_days': h.holding_days accesses non-existent attribute on FundHolding."
        )
        print(f"  -> FAIL: {msg}")
        findings.append(msg)

    # ---------------------------------------------------------
    # FINAL VERDICT
    # ---------------------------------------------------------
    print("\n" + "=" * 80)
    print("VERIFICATION SUMMARY & VERDICT")
    print("=" * 80)
    if findings:
        print(f"VERDICT: REJECT ({len(findings)} critical defect(s) discovered empirically)")
        for idx, f in enumerate(findings, 1):
            print(f"[{idx}] {f}")
        return False
    else:
        print("VERDICT: APPROVE (All empirical adversarial checks passed)")
        return True


if __name__ == "__main__":
    passed = run_adversarial_suite()
    sys.exit(0 if passed else 1)
