"""
Empirical Challenger Stress Harness for G16 M3:
MultiLedgerManager Isolation & 29-Fund Combat Ledger Deep Verification
"""

import sys
import os
import json
import tempfile
import threading
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from AGY2_FundAdvisory.multi_ledger_manager import MultiLedgerManager, WORKSPACE_ROOT
from AGY2_FundAdvisory.advisory_engine import ActiveRiskSentry
from AGY2_FundAdvisory.strategy_bridge import StrategyBridge


def log_test(name, passed, details=""):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"[{status}] {name} {details}")
    if not passed:
        raise AssertionError(f"Test failed: {name} - {details}")


def run_isolation_stress():
    print("\n--- Running Isolation Stress Tests ---")
    
    # 1. Empty temporary directory test
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        mlm_temp = MultiLedgerManager(workspace_root=tmp_path)
        ledgers = mlm_temp.list_ledgers()
        
        # Verify only main_live exists
        log_test(
            "Temp workspace isolation: count is 1",
            len(ledgers) == 1,
            f"Ledgers count = {len(ledgers)}"
        )
        log_test(
            "Temp workspace isolation: ledger is main_live",
            ledgers[0]["id"] == "main_live",
            f"Ledger ID = {ledgers[0]['id']}"
        )
        
        # Verify combat_29_funds is NOT present
        combat_meta = mlm_temp.get_ledger_meta("combat_29_funds")
        log_test(
            "Temp workspace isolation: combat_29_funds meta is None",
            combat_meta is None,
            f"combat_meta = {combat_meta}"
        )
        
        # Verify combat_29_funds.json does NOT exist on disk in temp dir
        combat_file = tmp_path / "data" / "ledgers" / "combat_29_funds.json"
        log_test(
            "Temp workspace isolation: combat_29_funds.json file does not exist",
            not combat_file.exists(),
            f"File exists: {combat_file.exists()}"
        )
        
        # Multiple re-initializations on temp dir
        for i in range(5):
            mlm_re = MultiLedgerManager(workspace_root=tmp_path)
            assert len(mlm_re.list_ledgers()) == 1
            assert not (tmp_path / "data" / "ledgers" / "combat_29_funds.json").exists()
        log_test("Temp workspace isolation: 5x re-init stays isolated", True)

    # 2. Case variations and relative paths for temp workspace (on same drive D:)
    same_drive_temp = WORKSPACE_ROOT / ".tmp_test_isolation"
    same_drive_temp.mkdir(parents=True, exist_ok=True)
    try:
        rel_path = os.path.relpath(same_drive_temp, WORKSPACE_ROOT)
        mlm_rel = MultiLedgerManager(workspace_root=rel_path)
        log_test(
            "Temp workspace with relative path: stays isolated",
            len(mlm_rel.list_ledgers()) == 1 and mlm_rel.get_ledger_meta("combat_29_funds") is None,
            f"Ledgers = {[l['id'] for l in mlm_rel.list_ledgers()]}"
        )
    finally:
        import shutil
        if same_drive_temp.exists():
            shutil.rmtree(same_drive_temp, ignore_errors=True)


def run_production_mount_stress():
    print("\n--- Running Production Mount Stress Tests ---")
    
    # 1. Reset singleton and get instance with WORKSPACE_ROOT
    MultiLedgerManager.reset_instance()
    mlm = MultiLedgerManager.get_instance(workspace_root=WORKSPACE_ROOT)
    
    combat_meta = mlm.get_ledger_meta("combat_29_funds")
    log_test(
        "Production mount: combat_29_funds meta exists",
        combat_meta is not None,
        f"Meta = {combat_meta}"
    )
    
    log_test(
        "Production mount: combat_29_funds file exists",
        (WORKSPACE_ROOT / "data" / "ledgers" / "combat_29_funds.json").exists(),
        "combat_29_funds.json exists"
    )
    
    # 2. Idempotency stress: call _ensure_index_initialized 20 times
    for _ in range(20):
        mlm._ensure_index_initialized()
    
    all_combat = [l for l in mlm.list_ledgers() if l.get("id") == "combat_29_funds"]
    log_test(
        "Production mount: exactly 1 combat_29_funds entry after 20x _ensure_index_initialized",
        len(all_combat) == 1,
        f"Count = {len(all_combat)}"
    )
    
    # 3. PM retrieval
    pm = mlm.get_pm("combat_29_funds")
    log_test(
        "Production mount: PM retrieved with 29 holdings",
        pm is not None and len(pm.holdings) == 29,
        f"Holdings count = {len(pm.holdings) if pm else None}"
    )


def run_accounting_precision_stress():
    print("\n--- Running Accounting Precision Stress Tests ---")
    
    mlm = MultiLedgerManager.get_instance()
    pm = mlm.get_pm("combat_29_funds")
    
    json_path = WORKSPACE_ROOT / "data" / "ledgers" / "combat_29_funds.json"
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    holdings_json = data["holdings"]
    log_test(
        "Accounting: exactly 29 holdings in JSON",
        len(holdings_json) == 29,
        f"Holdings count = {len(holdings_json)}"
    )
    
    # Market value breakdown
    total_mv_json = round(sum(h["market_value"] for h in holdings_json), 2)
    log_test(
        "Accounting: total market value in JSON is exactly 26615.10",
        total_mv_json == 26615.10,
        f"Actual = {total_mv_json}"
    )
    
    total_mv_pm = round(sum(h.market_value for h in pm.holdings.values()), 2)
    log_test(
        "Accounting: total market value in PM is exactly 26615.10",
        total_mv_pm == 26615.10,
        f"Actual = {total_mv_pm}"
    )
    
    # Cost basis and floating PnL preservation
    cost_basis_sum = round(sum(h["cost_basis"] for h in holdings_json), 2)
    floating_pnl_sum = round(sum(h["floating_pnl"] for h in holdings_json), 2)
    log_test(
        "Accounting: cost basis sum in JSON is 27372.20",
        cost_basis_sum == 27372.20,
        f"Actual cost basis = {cost_basis_sum}"
    )
    log_test(
        "Accounting: floating PnL sum in JSON preserves negative sign (-757.10 net, -1116.57 gross losses)",
        floating_pnl_sum < 0 and floating_pnl_sum == -757.10,
        f"Actual floating PnL = {floating_pnl_sum}"
    )
    
    identity_check = round(cost_basis_sum + floating_pnl_sum, 2)
    log_test(
        "Accounting: cost basis + floating PnL == total market value",
        identity_check == 26615.10,
        f"{cost_basis_sum} + {floating_pnl_sum} = {identity_check}"
    )
    
    # Check 19 tail funds sum == 442.70
    tail_codes = [
        "016634", "001053", "050025", "002352", "016441", "013841", "012832", "012769",
        "008682", "011612", "002611", "019260", "000086", "018757", "001071", "006113",
        "004854", "001595", "001551"
    ]
    log_test(
        "Accounting: exactly 19 tail codes defined",
        len(tail_codes) == 19
    )
    tail_sum_json = round(sum(h["market_value"] for h in holdings_json if h["fund_code"] in tail_codes), 2)
    log_test(
        "Accounting: 19 tail funds sum in JSON is exactly 442.70",
        tail_sum_json == 442.70,
        f"Actual = {tail_sum_json}"
    )
    
    tail_sum_pm = round(sum(pm.holdings[c].market_value for c in tail_codes), 2)
    log_test(
        "Accounting: 19 tail funds sum in PM is exactly 442.70",
        tail_sum_pm == 442.70,
        f"Actual = {tail_sum_pm}"
    )
    
    # 7 core funds == 25128.29
    core_codes = ["005561", "110020", "017436", "002351", "100032", "011613", "000216"]
    core_sum_json = round(sum(h["market_value"] for h in holdings_json if h["fund_code"] in core_codes), 2)
    log_test(
        "Accounting: 7 core funds sum in JSON is exactly 25128.29",
        core_sum_json == 25128.29,
        f"Actual = {core_sum_json}"
    )
    
    # 3 waist funds == 1044.11
    waist_codes = ["161725", "000217", "005827"]
    waist_sum_json = round(sum(h["market_value"] for h in holdings_json if h["fund_code"] in waist_codes), 2)
    log_test(
        "Accounting: 3 waist funds sum in JSON is exactly 1044.11",
        waist_sum_json == 1044.11,
        f"Actual = {waist_sum_json}"
    )
    
    log_test(
        "Accounting: Core (25128.29) + Waist (1044.11) + Tail (442.70) == 26615.10",
        round(core_sum_json + waist_sum_json + tail_sum_json, 2) == 26615.10
    )
    
    # Deep loss items:
    # #5 100032 (-332.54), #6 011613 (-428.48), #8 161725 (-175.76)
    json_targets = {h["fund_code"]: h for h in holdings_json if h["fund_code"] in ["100032", "011613", "161725"]}
    log_test(
        "Accounting: #5 100032 loss is -332.54",
        json_targets["100032"]["floating_pnl"] == -332.54
    )
    log_test(
        "Accounting: #6 011613 loss is -428.48",
        json_targets["011613"]["floating_pnl"] == -428.48
    )
    log_test(
        "Accounting: #8 161725 loss is -175.76",
        json_targets["161725"]["floating_pnl"] == -175.76
    )
    total_deep_loss = round(
        json_targets["100032"]["floating_pnl"] +
        json_targets["011613"]["floating_pnl"] +
        json_targets["161725"]["floating_pnl"],
        2
    )
    log_test(
        "Accounting: total 3 deep losses == -936.78",
        total_deep_loss == -936.78,
        f"Actual = {total_deep_loss}"
    )


def run_holding_days_and_redemption_fee_stress():
    print("\n--- Running Holding Days & Fee Stress Tests ---")
    
    json_path = WORKSPACE_ROOT / "data" / "ledgers" / "combat_29_funds.json"
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    for h in data["holdings"]:
        code = h["fund_code"]
        assert len(h["batches"]) >= 1
        for b in h["batches"]:
            assert b["holding_days"] == 400, f"{code} batch holding_days != 400"
            assert not b["safety_lock"], f"{code} safety_lock is True"
    log_test("Holding days: all batches in JSON preset to 400 days and safety_lock=False", True)
    
    mlm = MultiLedgerManager.get_instance()
    pm = mlm.get_pm("combat_29_funds")
    
    for code, h in pm.holdings.items():
        for b in h.batches:
            assert b.holding_days >= 365, f"PM {code} batch holding_days < 365"
            assert not b.safety_lock, f"PM {code} safety_lock is True"
        free_sh = pm.get_penalty_free_redeemable_shares(code)
        assert abs(free_sh - h.shares) < 1e-4, f"PM {code} free_sh != h.shares"
    log_test("Holding days: all PM dynamic batch holding_days >= 365, 100% penalty-free shares", True)
    
    # Rebalance scenario: sweep_tail_and_c_class
    plan = pm.generate_scenario_rebalance_plan({}, scenario_mode="sweep_tail_and_c_class", core_anchor_code="002351")
    log_test(
        "Scenario rebalance: total redemption fee is exactly 0.00",
        plan["total_redemption_fee"] == 0.0,
        f"Actual fee = {plan['total_redemption_fee']}"
    )
    log_test(
        "Scenario rebalance: 19 sell actions",
        len(plan["sell_actions"]) == 19,
        f"Sell actions count = {len(plan['sell_actions'])}"
    )
    log_test(
        "Scenario rebalance: total sell amount is exactly 442.70",
        round(plan["total_sell_amount"], 2) == 442.70,
        f"Actual sell amount = {plan['total_sell_amount']}"
    )
    log_test(
        "Scenario rebalance: total buy amount is exactly 442.70",
        round(plan["total_buy_amount"], 2) == 442.70,
        f"Actual buy amount = {plan['total_buy_amount']}"
    )
    log_test(
        "Scenario rebalance: 1 buy action targeting 002351",
        len(plan["buy_actions"]) == 1 and plan["buy_actions"][0]["fund_code"] == "002351",
        f"Buy action = {plan['buy_actions']}"
    )


def run_concurrency_stress():
    print("\n--- Running Multi-Threaded Concurrency Stress Tests ---")
    
    mlm = MultiLedgerManager.get_instance()
    errors = []
    
    def worker(tid):
        try:
            for _ in range(10):
                pm = mlm.get_pm("combat_29_funds")
                mv = round(sum(h.market_value for h in pm.holdings.values()), 2)
                if mv != 26615.10:
                    errors.append(f"Thread {tid}: MV {mv} != 26615.10")
                plan = pm.generate_scenario_rebalance_plan({}, scenario_mode="sweep_tail_and_c_class", core_anchor_code="002351")
                if len(plan["sell_actions"]) != 19 or round(plan["total_sell_amount"], 2) != 442.70:
                    errors.append(f"Thread {tid}: Plan sell count {len(plan['sell_actions'])} or amt {plan['total_sell_amount']}")
        except Exception as e:
            errors.append(f"Thread {tid} exception: {e}")

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    log_test(
        "Concurrency stress: 10 threads x 10 cycles without race conditions or errors",
        len(errors) == 0,
        f"Errors: {errors[:5]}"
    )


def run_strategy_bridge_presets_stress():
    print("\n--- Running StrategyBridge Presets Stress Tests ---")
    
    preset = StrategyBridge.get_combat_29_vs_reconstructed_6_preset()
    log_test(
        "StrategyBridge preset: fund_count_before == 29",
        preset["fund_count_before"] == 29
    )
    log_test(
        "StrategyBridge preset: fund_count_after == 6",
        preset["fund_count_after"] == 6
    )
    log_test(
        "StrategyBridge preset: total_market_value == 26615.10",
        round(preset["total_market_value"], 2) == 26615.10,
        f"Actual = {preset['total_market_value']}"
    )
    sum_w29 = sum(preset["raw_29_weights"].values())
    log_test(
        "StrategyBridge preset: raw_29_weights sum == 1.0",
        abs(sum_w29 - 1.0) < 1e-4,
        f"Sum = {sum_w29}"
    )
    sum_w6 = sum(preset["reconstructed_6_weights"].values())
    log_test(
        "StrategyBridge preset: reconstructed_6_weights sum == 1.0",
        abs(sum_w6 - 1.0) < 1e-4,
        f"Sum = {sum_w6}"
    )
    
    rx = StrategyBridge.get_combat_29_rebalance_prescription()
    log_test(
        "StrategyBridge prescription: step1 tail cleanup count == 19 and amount == 442.70",
        rx["step1_tail_cleanup"]["count"] == 19 and rx["step1_tail_cleanup"]["amount"] == 442.70
    )
    log_test(
        "StrategyBridge prescription: step2 deep loss surgery total_loss == -936.78",
        rx["step2_deep_loss_surgery"]["total_loss"] == -936.78
    )
    log_test(
        "StrategyBridge prescription: step3 funds count == 6",
        len(rx["step3_core_reconstruction"]["funds"]) == 6
    )


if __name__ == "__main__":
    print("==================================================================")
    print("STARTING EMPIRICAL CHALLENGER STRESS HARNESS FOR G16 M3")
    print("==================================================================")
    
    run_isolation_stress()
    run_production_mount_stress()
    run_accounting_precision_stress()
    run_holding_days_and_redemption_fee_stress()
    run_concurrency_stress()
    run_strategy_bridge_presets_stress()
    
    print("\n==================================================================")
    print("ALL EMPIRICAL CHALLENGE SUITES COMPLETED SUCCESSFULLY!")
    print("==================================================================")
