# -*- coding: utf-8 -*-
import sys
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
AGY2_DIR = WORKSPACE_ROOT / "AGY2_FundAdvisory"

if str(AGY2_DIR) not in sys.path:
    sys.path.insert(0, str(AGY2_DIR))
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from portfolio_manager import PortfolioManager, FundHolding, HoldingItem
from strategy_bridge import StrategyBridge

def run_special_test_1():
    print("=" * 60)
    print("SPECIAL TEST 1: Asset Classification for 9 Key Test Funds")
    print("=" * 60)

    pm = PortfolioManager(db_path=":memory:")

    funds = [
        ("161726", "中盘均衡", "医药/招商国证生物医药指数"),
        ("161725", "核心蓝筹", "白酒/招商中证白酒指数"),
        ("160418", "A股红利高股息", "银行/华安中证银行指数"),
        ("013402", "科技成长进攻", "恒科/华夏恒生科技ETF联接A"),
        ("008888", "科技成长进攻", "半导体/华夏国证半导体芯片ETF联接A"),
        ("050025", "美股海外对冲", "标普QDII/博时标普500ETF联接A"),
        ("005561", "A股红利低波", "红利低波/创金合信红利低波A"),
        ("002351", "纯债固收", "纯债固收/易方达裕祥回报债券A"),
        ("000216", "黄金对冲", "黄金对冲/华安黄金ETF联接A")
    ]

    STANDARD_NINE = {
        "纯债固收", "黄金对冲", "美股海外对冲", "A股红利低波",
        "A股红利高股息", "科技成长进攻", "中小盘成长", "中盘均衡", "核心蓝筹"
    }

    all_nine_ok = True
    zero_other_equity = True

    for code, exp_cat, desc in funds:
        actual_cat_inst = pm.classify_fund_asset_class(code)
        actual_cat_cls = PortfolioManager.classify_fund_asset_class(code)

        print(f"Fund {code} ({desc}):")
        print(f"  Expected Category : {exp_cat}")
        print(f"  Instance Result   : {actual_cat_inst}")
        print(f"  Class Result      : {actual_cat_cls}")

        if actual_cat_inst == "其他权益资产" or actual_cat_cls == "其他权益资产":
            zero_other_equity = False
            print(f"  [FAIL] Returned '其他权益资产'!")

        if actual_cat_inst not in STANDARD_NINE or actual_cat_cls not in STANDARD_NINE:
            all_nine_ok = False
            print(f"  [FAIL] Not in standard 9 classes!")

        if actual_cat_inst != exp_cat or actual_cat_cls != exp_cat:
            all_nine_ok = False
            print(f"  [FAIL] Did not match expected category {exp_cat}!")
        else:
            print(f"  [PASS] Matches standard 9 categories perfectly.")

    assert zero_other_equity, "Special Test 1 Failed: Some funds classified as '其他权益资产'"
    assert all_nine_ok, "Special Test 1 Failed: Asset classification mismatch"
    print("\nSpecial Test 1 PASSED: All 9 funds return standard categories, 0 return '其他权益资产'!\n")


def run_special_test_2():
    print("=" * 60)
    print("SPECIAL TEST 2: Dynamic Yield Cushion & Shadow Rebalance Audit")
    print("=" * 60)

    pm = PortfolioManager(db_path=":memory:")
    pm.available_cash = 20000.0
    pm.baseline_equity = 100000.0

    # Add 3 holdings:
    # 005561 (A股红利低波, 5.2% yield): 20,000 shares @ NAV 1.5 = 30,000
    # 002351 (纯债固收, 2.75% yield): 20,000 shares @ NAV 1.0 = 20,000
    # 050025 (美股海外对冲, 1.3% yield): 20,000 shares @ NAV 1.5 = 30,000
    # Available cash: 20,000
    # Total capital: 100,000
    pm.add_or_update_holding("005561", shares=20000, nav=1.5, cost_price=1.4, holding_days=45, fund_name="创金合信红利低波A", dividend_method="cash")
    pm.add_or_update_holding("002351", shares=20000, nav=1.0, cost_price=1.0, holding_days=90, fund_name="易方达裕祥回报债券A", dividend_method="reinvest")
    pm.add_or_update_holding("050025", shares=20000, nav=1.5, cost_price=1.2, holding_days=60, fund_name="博时标普500ETF联接A", dividend_method="reinvest")

    print("[Step 1] Testing StrategyBridge.calculate_portfolio_yield_cushion")
    cushion = StrategyBridge.calculate_portfolio_yield_cushion(pm.holdings, total_capital=100000.0, pm=pm)
    print(f"  weighted_yield_pct        : {cushion.get('weighted_yield_pct')}%")
    print(f"  annual_cushion_amount     : ¥{cushion.get('annual_cushion_amount')}")
    print(f"  monthly_equivalent_amount : ¥{cushion.get('monthly_equivalent_amount')}")
    print(f"  cash_dividend_payout_est  : ¥{cushion.get('cash_dividend_payout_est')}")

    assert "weighted_yield_pct" in cushion
    assert "annual_cushion_amount" in cushion
    assert "monthly_equivalent_amount" in cushion
    assert "cash_dividend_payout_est" in cushion
    assert cushion["weighted_yield_pct"] == 2.50
    assert cushion["annual_cushion_amount"] == 2500.0
    assert cushion["monthly_equivalent_amount"] == 208.33
    # 005561 is 30,000 * 5.2% = 1,560
    assert cushion["cash_dividend_payout_est"] == 1560.0
    print("  [PASS] Yield cushion returns real dynamic calculated values!")

    print("\n[Step 2] Testing pm.evaluate_rebalance_audit Initial Baseline")
    audit_init = pm.evaluate_rebalance_audit()
    print(f"  current_actual_equity       : ¥{audit_init['current_actual_equity']}")
    print(f"  shadow_hold_equity          : ¥{audit_init['shadow_hold_equity']}")
    print(f"  rebalance_value_add         : ¥{audit_init['rebalance_value_add']}")
    print(f"  saved_penalty_and_buffer_fees: ¥{audit_init['saved_penalty_and_buffer_fees']}")

    assert audit_init["current_actual_equity"] == 100000.0
    assert audit_init["shadow_hold_equity"] == 100000.0
    assert audit_init["rebalance_value_add"] == 0.0

    print("\n[Step 3] Modifying NAVs (005561: 1.50 -> 1.80, 050025: 1.50 -> 1.60)")
    # When modifying holding NAVs dynamically
    pm.holdings["005561"].current_nav = 1.80
    pm.holdings["005561"].market_value = 20000 * 1.80 # 36000
    pm.holdings["050025"].current_nav = 1.60
    pm.holdings["050025"].market_value = 20000 * 1.60 # 32000

    audit_nav_change = pm.evaluate_rebalance_audit()
    print(f"  After NAV increase:")
    print(f"  current_actual_equity : ¥{audit_nav_change['current_actual_equity']}")
    print(f"  shadow_hold_equity    : ¥{audit_nav_change['shadow_hold_equity']}")
    print(f"  rebalance_value_add   : ¥{audit_nav_change['rebalance_value_add']}")

    assert audit_nav_change["current_actual_equity"] == 108000.0
    assert audit_nav_change["shadow_hold_equity"] == 108000.0
    assert audit_nav_change["rebalance_value_add"] == 0.0
    print("  [PASS] Both current_actual_equity and shadow_hold_equity genuinely and dynamically reflect NAV changes!")

    print("\n[Step 4] Executing Rebalance and further NAV change to test divergence")
    # Rebalance: Sell 10,000 shares of 050025 (worth 16,000) and buy 16,000 shares of 002351
    pm.holdings["050025"].shares = 10000.0
    pm.holdings["050025"].market_value = 16000.0
    pm.holdings["002351"].shares += 16000.0
    pm.holdings["002351"].market_value = pm.holdings["002351"].shares * 1.0

    # Further NAV change: 050025 rises to 2.00
    pm.holdings["050025"].current_nav = 2.00
    pm.holdings["050025"].market_value = 10000.0 * 2.00 # 20000

    audit_diverged = pm.evaluate_rebalance_audit()
    print(f"  After Rebalance & NAV movement:")
    print(f"  current_actual_equity : ¥{audit_diverged['current_actual_equity']}")
    print(f"  shadow_hold_equity    : ¥{audit_diverged['shadow_hold_equity']}")
    print(f"  rebalance_value_add   : ¥{audit_diverged['rebalance_value_add']}")
    print(f"  rebalance_value_add_pct: {audit_diverged['rebalance_value_add_pct']}%")

    # Actual equity: 36,000 (005561) + 36,000 (002351) + 20,000 (050025) + 20,000 cash = 112,000
    # Shadow equity: 20000*1.8 (36000) + 20000*1.0 (20000) + 20000*2.0 (40000) + 20000 cash = 116,000
    # Rebalance value add: 112,000 - 116,000 = -4,000
    assert audit_diverged["current_actual_equity"] == 112000.0
    assert audit_diverged["shadow_hold_equity"] == 116000.0
    assert audit_diverged["rebalance_value_add"] == -4000.0
    print("  [PASS] Shadow portfolio genuinely accounts for initial baseline holding vs actual trades!")

    print("\nSpecial Test 2 PASSED completely!\n")

if __name__ == "__main__":
    run_special_test_1()
    run_special_test_2()
