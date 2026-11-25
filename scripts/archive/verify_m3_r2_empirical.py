# -*- coding: utf-8 -*-
"""
Empirical verification script for Milestone 3 Round 2.
Evaluates Tab 2 Rebalance Impact Arithmetic and Tab 3 Dynamic Rebalance.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "AGY2_FundAdvisory") not in sys.path:
    sys.path.insert(0, str(ROOT / "AGY2_FundAdvisory"))

from AGY2_FundAdvisory.strategy_bridge import StrategyBridge
from AGY2_FundAdvisory.multi_ledger_manager import MultiLedgerManager


def verify_m3_r2():
    print("=" * 60)
    print("RUNNING EMPIRICAL VERIFICATION FOR M3 R2")
    print("=" * 60)

    # 1. Verify get_combat_29_rebalance_prescription schema
    print("\n[CHECK 1] StrategyBridge.get_combat_29_rebalance_prescription schema...")
    rx = StrategyBridge.get_combat_29_rebalance_prescription()
    step3 = rx["step3_core_reconstruction"]
    funds = step3["funds"]
    assert len(funds) == 6, f"Expected 6 funds, got {len(funds)}"
    for idx, f in enumerate(funds):
        assert "code" in f, f"Fund at index {idx} missing 'code': {f}"
        assert "name" in f, f"Fund at index {idx} missing 'name': {f}"
        assert "weight_pct" in f, f"Fund at index {idx} missing 'weight_pct': {f}"
        assert isinstance(f["code"], str) and len(f["code"]) == 6, f"Invalid code: {f['code']}"
        assert isinstance(f["name"], str) and len(f["name"]) > 0, f"Invalid name: {f['name']}"
        assert isinstance(f["weight_pct"], (int, float)) and f["weight_pct"] > 0, f"Invalid weight: {f['weight_pct']}"
        print(f"  Fund {idx+1}: code={f['code']}, name={f['name']}, weight={f['weight_pct']}%")

    tot_weight = sum(f["weight_pct"] for f in funds)
    print(f"  Total weight sum = {tot_weight:.2f}%")
    assert abs(tot_weight - 100.0) < 0.1, f"Weights should sum to 100%, got {tot_weight}"

    step1 = rx["step1_tail_cleanup"]
    assert step1["count"] == 19
    assert step1["amount"] == 442.70
    assert step1["fee"] == 0.00
    print(f"  Step 1 cleanup: {step1['count']} funds, ¥{step1['amount']:.2f}, fee=¥{step1['fee']:.2f} PASS")

    step2 = rx["step2_deep_loss_surgery"]
    assert len(step2["items"]) == 3
    assert step2["total_loss"] == -936.78
    print(f"  Step 2 surgery: {len(step2['items'])} items, total loss=¥{step2['total_loss']:.2f} PASS")
    print("[CHECK 1] SUCCESS!")

    # 2. Verify estimate_rebalance_impact outputs
    print("\n[CHECK 2] StrategyBridge.estimate_rebalance_impact outputs...")
    mlm = MultiLedgerManager.get_instance()
    pm = mlm.get_pm("combat_29_funds")
    preset = StrategyBridge.get_combat_29_vs_reconstructed_6_preset()
    target_weights = preset["reconstructed_6_weights"]

    impact = StrategyBridge.estimate_rebalance_impact(
        current_holdings=pm.holdings,
        target_weights_funds=target_weights,
        total_equity=pm.total_equity,
        rebalance_items=[]
    )

    print(f"  fund_count_before = {impact['fund_count_before']} (expected 29)")
    print(f"  fund_count_after = {impact['fund_count_after']} (expected 6)")
    print(f"  revitalized_cash_min = {impact['revitalized_cash_min']:.2f} (expected 442.70)")
    print(f"  revitalized_cash_max = {impact['revitalized_cash_max']:.2f} (expected 962.57)")
    print(f"  total_fee = {impact['total_fee']:.2f} (expected 0.00)")
    print(f"  payback_days = {impact['payback_days']} (expected 0)")
    print(f"  payback_desc = {impact['payback_desc']} (expected 即时零损耗)")
    print(f"  vol_before = {impact['vol_before']}%, vol_after = {impact['vol_after']}%, vol_diff = {impact['vol_diff']}%")
    print(f"  div_before = {impact['div_before']}%, div_after = {impact['div_after']}%, div_diff = {impact['div_diff']}%")

    assert impact["fund_count_before"] == 29
    assert impact["fund_count_after"] == 6
    assert abs(impact["revitalized_cash_min"] - 442.70) < 1e-4
    assert abs(impact["revitalized_cash_max"] - 962.57) < 1e-4
    assert impact["total_fee"] == 0.00
    assert impact["payback_days"] == 0
    assert impact["payback_desc"] == "即时零损耗"
    print("[CHECK 2] SUCCESS!")

    # 3. Verify Tab 3 dynamic rebalance at 2024-09-18
    print("\n[CHECK 3] Tab 3 Dynamic Rebalance at 2024-09-18...")
    res_dyn = StrategyBridge.run_historical_time_machine_backtest(
        target_date="2024-09-18",
        tier="C3",
        capital=100000.0,
        dynamic_rebalance=True
    )
    res_static = StrategyBridge.run_historical_time_machine_backtest(
        target_date="2024-09-18",
        tier="C3",
        capital=100000.0,
        dynamic_rebalance=False
    )

    kpi_dyn_3m = res_dyn["kpi_3m"]
    kpi_static_3m = res_static["kpi_3m"]

    print(f"  Dynamic 3M Net Return: {kpi_dyn_3m['net_return_pct']:.2f}% (dispatch requirement > 25.0%)")
    print(f"  Dynamic 3M Alpha vs H300: {kpi_dyn_3m['alpha_vs_h300']:.2f}% (dispatch requirement > 5.0%)")
    print(f"  Static 3M Net Return: {kpi_static_3m['net_return_pct']:.2f}%")
    print(f"  Dynamic outperformance: +{kpi_dyn_3m['net_return_pct'] - kpi_static_3m['net_return_pct']:.2f}%")

    assert kpi_dyn_3m["net_return_pct"] > 25.0, f"Expected >25.0%, got {kpi_dyn_3m['net_return_pct']}%"
    assert kpi_dyn_3m["alpha_vs_h300"] > 5.0, f"Expected >5.0%, got {kpi_dyn_3m['alpha_vs_h300']}%"
    assert kpi_dyn_3m["net_return_pct"] > kpi_static_3m["net_return_pct"]
    print("[CHECK 3] SUCCESS!")

    # 4. Verify GUI file integrity
    print("\n[CHECK 4] GUI File Integrity in AGY2_FundAdvisory/app_gui.py...")
    gui_src = open(ROOT / "AGY2_FundAdvisory" / "app_gui.py", encoding="utf-8").read()
    assert "estimate_rebalance_impact" in gui_src, "Missing estimate_rebalance_impact call"
    assert "get_combat_29_rebalance_prescription" in gui_src, "Missing get_combat_29_rebalance_prescription call"
    assert "7 只全天候" not in gui_src, "Typo '7 只全天候' still exists in app_gui.py"
    assert "6 只全天候核心压舱石" in gui_src, "Missing corrected '6 只全天候核心压舱石'"
    assert "tab2_sweep_tail" not in gui_src, "Dead state tab2_sweep_tail still present"
    assert 'rad_tab2_scenario_mode = "🧹 尾部碎片与C类一键归拢' in gui_src, "Button does not wire scenario mode"
    assert "tgl_dynamic" in gui_src, "Missing tgl_dynamic toggle in Time Machine"
    assert "投顾重构 6 基核心组合" in gui_src, "Missing corrected primary curve label"
    assert "原始 29 基存量组合" in gui_src, "Missing corrected secondary curve label"
    print("  All GUI assertions passed!")
    print("[CHECK 4] SUCCESS!")

    print("\n" + "=" * 60)
    print("ALL EMPIRICAL CHECKS PASSED (100% GREEN)")
    print("=" * 60)


if __name__ == "__main__":
    verify_m3_r2()
