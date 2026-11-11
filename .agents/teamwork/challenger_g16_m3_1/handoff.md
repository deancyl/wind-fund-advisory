# Handoff Report — challenger_g16_m3_1

## 1. Observation

### 1.1 Direct Automated Test Suite Results
Executed the requested pytest command:
```powershell
py -3 -m pytest tests/test_multi_ledger_manager.py tests/test_multi_ledger_manager_stress.py tests/test_adversarial_m3_combat29_challenger.py -v
```
Output:
```
====================== 25 passed, 31 warnings in 44.03s =======================
tests/test_multi_ledger_manager.py: 8 passed (100%)
tests/test_multi_ledger_manager_stress.py: 8 passed (100%)
tests/test_adversarial_m3_combat29_challenger.py: 9 passed (100%)
```

Additionally ran the GUI multi-ledger stress test suite:
```powershell
py -3 -m pytest tests/test_gui_multi_ledger_stress.py -v
```
Output:
```
================= 10 passed, 103 warnings in 78.76s (0:01:18) =================
```

### 1.2 MultiLedgerManager Isolation Mechanism Observation
In `AGY2_FundAdvisory/multi_ledger_manager.py` lines 173–185:
```python
if str(self.root.resolve()).lower() == str(WORKSPACE_ROOT.resolve()).lower():
    combat_item = next((l for l in final_ledgers if l.get("id") == "combat_29_funds"), None)
    combat_json_path = self.ledgers_dir / "combat_29_funds.json"
    if not combat_item or not combat_json_path.exists():
        combat_meta = self._init_preset_combat_29_ledger()
        if not combat_item:
            final_ledgers.append(combat_meta)
        else:
            for idx, l in enumerate(final_ledgers):
                if l.get("id") == "combat_29_funds":
                    final_ledgers[idx] = combat_meta
                    break
```
- When `workspace_root` points to a temporary workspace (e.g. `tmp_path`), `str(self.root.resolve()).lower() != str(WORKSPACE_ROOT.resolve()).lower()`. Consequently, `combat_29_funds` is **never** injected into the index nor initialized on disk.
- When `workspace_root` points to `WORKSPACE_ROOT`, `combat_29_funds` is idempotently mounted.

### 1.3 Combat 29 Accounting and Precision Empirical Measurements
From execution of `scripts/inspect_combat_ledger_accounting.py` and `scripts/challenger_m3_stress_harness.py`:
- **Holdings Count**: Exactly 29 holdings in both `data/ledgers/combat_29_funds.json` and `PortfolioManager.holdings`.
- **Total Market Value**: Exactly `¥26,615.10` (error `0.00`).
  - 7 Core Strategy funds (`005561`, `110020`, `017436`, `002351`, `100032`, `011613`, `000216`): sum = `¥25,128.29`.
  - 3 Waist funds (`161725`, `000217`, `005827`): sum = `¥1,044.11`.
  - 19 Fragment Tail funds (`016634`, `001053`, `050025`, `002352`, `016441`, `013841`, `012832`, `012769`, `008682`, `011612`, `002611`, `019260`, `000086`, `018757`, `001071`, `006113`, `004854`, `001595`, `001551`): sum = `¥442.70`.
  - Invariance: `25128.29 + 1044.11 + 442.70 == 26615.10`.
- **Cost Basis & Floating PnL**:
  - Cost basis sum: `¥27,372.20`.
  - Net floating PnL: `-¥757.10`.
  - Identity check: `27372.20 + (-757.10) == 26615.10`.
  - Negative PnL signs are 100% preserved in JSON and PM.
  - Three major bleeding sources:
    - `#5 100032`: MV `2432.90`, Cost `2765.44`, PnL `-332.54` (`-12.02%`)
    - `#6 011613`: MV `2072.52`, Cost `2501.00`, PnL `-428.48` (`-17.13%`)
    - `#8 161725`: MV `524.24`, Cost `700.00`, PnL `-175.76` (`-25.11%`)
    - Sum of 3 deep losses: `-332.54 + (-428.48) + (-175.76) == -936.78`.
- **Holding Days & Redemption Fee**:
  - In static JSON: Every holding batch explicitly has `holding_days == 400` and `safety_lock == False`.
  - In PM dynamic calculation: `first_buy_date == '2024-01-05'`, dynamic holding days exceed 1,000 days (`>= 365` days).
  - When running `generate_scenario_rebalance_plan({}, scenario_mode="sweep_tail_and_c_class", core_anchor_code="002351")`:
    - Total sell actions: 19
    - Total sell amount: `¥442.70`
    - Total redemption fee: `¥0.00` (0.00%)
    - Total buy amount: `¥442.70` (100% capital conservation, targeting `002351`)

### 1.4 Adversarial Stress Harness Results
Executed `py -3 scripts/challenger_m3_stress_harness.py`:
- Temp workspace isolation: PASS (count=1, combat_29_funds meta is None, 0 disk files created).
- Production mount: PASS (combat_29_funds present, exactly 1 entry in `ledgers_index.json` even after 20 consecutive initialization calls).
- Accounting precision: PASS (all 29 holdings satisfy `cost_basis + floating_pnl == market_value`).
- Concurrency: PASS (10 concurrent threads x 10 cycles of PM retrieval and plan generation completed with 0 errors).
- StrategyBridge preset: PASS (`raw_29_weights` sums to 1.0, `reconstructed_6_weights` sums to 1.0, step 1 sweeps 19 tail funds / ¥442.70, step 2 identifies 3 deep losses / -¥936.78).

---

## 2. Logic Chain

1. **Isolation Proof**: In `_ensure_index_initialized`, line 173 explicitly compares `str(self.root.resolve()).lower() == str(WORKSPACE_ROOT.resolve()).lower()`. In any test using a temporary workspace, this evaluates to `False`. Our stress harness demonstrated that `list_ledgers()` returns strictly `[main_live]` and `data/ledgers/combat_29_funds.json` is not created in the temporary folder. This guarantees zero test contamination and ensures that existing single-ledger unit tests pass without assertion conflicts on ledger count.
2. **Mount Idempotency Proof**: In production workspace, `_ensure_index_initialized` checks whether `combat_item` exists or `combat_json_path` exists. If already present, it updates or keeps the existing entry without duplicating it. Tested with 20 consecutive initialization loops, resulting in exactly one `combat_29_funds` entry in `ledgers_index.json`.
3. **Accounting & Fee Defense Proof**: Each of the 29 funds was checked at both the JSON file level and the runtime PM object level. The sum of market values is exactly 26,615.10. Tail funds total 442.70 across 19 funds. The 3 deep loss funds sum to -936.78. Because all batches have holding days of 400 (and dynamic >1000 days), none trigger the <=7 days penalty fee or the <30 days C-class fee, ensuring that the 19-fund tail sweep rebalance plan incurs strictly 0.00 yuan in fees.
4. **Integration Cohesion Proof**: In `app_gui.py` and `strategy_bridge.py`, Tab 2 renders the 29-fund specific prescription card (19 tail funds sweep, 3 deep loss surgery, and rebalance impact) and Tab 3 enables the `preset_combat_29_vs_6` true-rules 1-year backtest comparison between the 29 original funds and the 6 reconstructed funds. All weights normalize cleanly to 1.000000.

---

## 3. Caveats

- **Operating System Drives**: In Windows PowerShell environments, temporary directory paths created via `tempfile.TemporaryDirectory()` may reside on `C:` while the workspace resides on `D:`. Path comparisons must use resolved absolute paths (`.resolve()`) rather than cross-drive relative paths. The codebase handles this correctly via `Path.resolve()`.
- **Live GUI Browser Interaction**: Multimodal UI visual verification (/browser) is deferred to Milestone 4 per the pipeline architecture. All underlying backend and AppTest GUI states have been empirically verified.

---

## 4. Conclusion

**Verdict**: **APPROVE**

The implementation of `MultiLedgerManager` workspace isolation and the `combat_29_funds` 29-fund combat ledger satisfies all functional and non-functional requirements:
1. Complete isolation between production and temporary workspaces (zero contamination in unit tests).
2. Idempotent mounting and registration in production.
3. Cent-accurate market value accounting (¥26,615.10 total, ¥442.70 tail), negative PnL sign preservation, and deep loss identification (-¥936.78 across 3 funds).
4. Strictly 0.00% redemption fee on 19 tail fund liquidation due to holding days > 365 days.
5. High concurrency safety under multi-threaded execution.

---

## 5. Verification Method

To independently verify all claims made in this report, execute the following commands in the workspace root:

```powershell
# 1. Run core multi-ledger and adversarial combat suites:
py -3 -m pytest tests/test_multi_ledger_manager.py tests/test_multi_ledger_manager_stress.py tests/test_adversarial_m3_combat29_challenger.py -v

# 2. Run multi-ledger GUI stress suite:
py -3 -m pytest tests/test_gui_multi_ledger_stress.py -v

# 3. Run empirical stress harness:
py -3 scripts/challenger_m3_stress_harness.py

# 4. Run accounting inspection script:
py -3 scripts/inspect_combat_ledger_accounting.py
```

Invalidation conditions:
- Any test failure or assertion error in the above suites.
- Any creation of `combat_29_funds.json` when `MultiLedgerManager(workspace_root=temp_dir)` is called with an empty temporary directory.
- `ledgers_index.json` containing more than 1 entry for `combat_29_funds` in production.
- Any non-zero redemption fee generated by `sweep_tail_and_c_class`.
