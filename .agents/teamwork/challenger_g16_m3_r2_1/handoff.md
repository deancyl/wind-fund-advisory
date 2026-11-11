# Handoff Report — challenger_g16_m3_r2_1

**Target Under Test**: `MultiLedgerManager` Isolation & `combat_29_funds` Combat Ledger (Milestone 3 Round 2)  
**Role**: Empirical Challenger (`teamwork_challenger`)  
**Verdict**: **`APPROVE`**

---

## 1. Observation

### 1.1 MultiLedgerManager Isolation & Idempotency Implementation
- **Source Inspection**: `AGY2_FundAdvisory/multi_ledger_manager.py` (lines 170–190)
  ```python
  # 确保预置实战存量组合（29只·¥2.66万）存在
  # 严格隔离测试环境：仅在生产/主工作区 (self.root == WORKSPACE_ROOT) 自动幂等挂载
  # 严禁向单测隔离临时目录 (temp_workspace) 自动注入 combat_29_funds，彻底杜绝账本计数/总金额单测断言失败
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
- **Temporary Workspace Isolation**: When `workspace_root` points to a temporary directory (`temp_workspace`, `tmp_path`), `self.root != WORKSPACE_ROOT`, so `combat_29_funds` is NEVER auto-injected. The initial ledger count remains strictly 1 (`main_live`), preserving isolation for external test suites.
- **Production Mount Idempotency & User Preservation**: When `combat_item` exists in `ledgers_index.json` and `combat_29_funds.json` exists on disk, `_init_preset_combat_29_ledger()` is bypassed, preventing user mutations (e.g. customized available cash or notes) from being clobbered.
- **Self-Healing**: If `combat_29_funds.json` is missing or `combat_item` is deleted from index, re-initialization restores it automatically.

### 1.2 29-Fund Combat Ledger Data Integrity
- **Physical Ledger File**: `data/ledgers/combat_29_funds.json`
- **Total Market Value**: Exactly `¥26,615.10` (discrepancy = `0.00`):
  - 7 Core Holdings: `¥25,128.29` (`005561` 5681.55, `110020` 5279.05, `017436` 4536.85, `002351` 4101.71, `100032` 2432.90, `011613` 2072.52, `000216` 1023.71)
  - 3 Waist Holdings: `¥1,044.11` (`161725` 524.24, `000217` 395.73, `005827` 124.14)
  - 19 Tail Fragments: `¥442.70` (all < ¥200, ranging from ¥89.60 down to ¥0.59)
  - Total: `25128.29 + 1044.11 + 442.70 = 26615.10`
- **Holding Days & Redemption Fee Zero-Friction**:
  - All 29 holdings in `combat_29_funds.json` have batch `holding_days = 400` (> 365 days threshold) and `safety_lock = false`.
  - In PortfolioManager runtime, calculated holding days from `first_buy_date` (2024-01-05) exceed 1000 days.
  - `pm.get_penalty_free_redeemable_shares(code) == h.shares` for all 29 funds (100% unlocked).
  - All redemption fees under rebalance/sweep scenarios equal `0.00`.
- **Three Deep Loss Bleeding Points**:
  - `#5 100032`: cost 2765.44, mv 2432.90, floating pnl `-332.54` (-12.02%)
  - `#6 011613`: cost 2501.00, mv 2072.52, floating pnl `-428.48` (-17.13%)
  - `#8 161725`: cost 700.00, mv 524.24, floating pnl `-175.76` (-25.11%)
  - Sum of deep losses: `-332.54 + -428.48 + -175.76 = -936.78` (verbatim match).
- **ActiveRiskSentry Dimension 13 & Chief Advisor Memo**:
  - `inspect_portfolio` detects exactly 19 tail funds with `recoverable_cash = 442.70`.
  - Waist funds (`161725`, `000217`, `005827`) and Core funds are 100% protected.
  - `generate_chief_advisor_memo` identifies bleeding points and 19 tail funds with ¥442.70 clean sweep advice.

### 1.3 Test Suite Execution Results
Direct execution of target test suites:
```powershell
py -3 -m pytest tests/test_multi_ledger_manager.py tests/test_multi_ledger_manager_stress.py tests/test_adversarial_m3_combat29_challenger.py tests/test_challenger_deep_stress_m3.py -v
```
Output:
```
tests/test_multi_ledger_manager.py (8 passed)
tests/test_multi_ledger_manager_stress.py (8 passed)
tests/test_adversarial_m3_combat29_challenger.py (9 passed)
tests/test_challenger_deep_stress_m3.py (8 passed)
====================== 33 passed, 31 warnings in 53.24s =======================
```

Additional regression suites executed:
- `tests/test_infra.py`: 14 passed in 8.10s (all 4 referee files untouched)
- `tests/test_gui_multi_ledger_stress.py`: 10 passed in 66.47s
- `tests/test_m3_adversarial_challenger2_stress.py` & `test_m3_item2_rebalance_impact.py`: 20 passed in 8.17s
- `tests/test_m3_item3_tab3_backtest.py`: 3 passed in 4.22s

---

## 2. Logic Chain

1. **Isolation Invariant**: By anchoring auto-injection to `str(self.root.resolve()).lower() == str(WORKSPACE_ROOT.resolve()).lower()`, any temporary test workspace running with `MultiLedgerManager(workspace_root=tmp_path)` sees only `main_live`. This strictly prevents pollution of isolated unit tests expecting single-ledger setups.
2. **Idempotency & Non-Destructive Invariant**: The condition `if not combat_item or not combat_json_path.exists():` guarantees that on repeated production startups or GUI reloads, existing combat ledger modifications are preserved. This was empirically validated by test `test_production_workspace_mount_idempotency_and_preservation`.
3. **Holding Days & Penalty Immunity Invariant**: Because each batch is explicitly timestamped `2024-01-05` and pre-populated with `holding_days = 400`, pessimistic evaluation `min(b.holding_days for b in batches)` always exceeds the regulatory 365-day barrier for Class A and 30-day barrier for Class C. Consequently, redemption fees are strictly ¥0.00, satisfying Rule 2 and Rule 7.
4. **Market Value Arithmetic Invariant**: Re-summing market values in both raw JSON and PortfolioManager memory yields `25,128.29 + 1,044.11 + 442.70 = 26,615.10` with exactly 0.00 discrepancy. Accounting identity `cost_basis + floating_pnl == market_value` holds across all 29 holdings.
5. **Bleed Resistance & File Immutability**: Under extreme stress (40 funds, 120 batches, 15 pending orders, 25 state saves into sandbox), SHA256 of `portfolio_ledger.json` and `portfolio_state.db` remained identical to pre-test hashes. Direct deletion attacks using case variants (`MAIN_LIVE`, `MaIn_LiVe`), whitespace padding, and path traversal (`data/../portfolio_ledger.json`) were all intercepted with `PermissionError`.

---

## 3. Caveats

- **Network Warnings**: Eastmoney endpoint TLS warnings (`InsecureRequestWarning`) are expected during live market data probes in development environments; they do not impact test assertions or offline fallbacks.
- **Ghost Ledger Reaper Window**: `_ensure_index_initialized` cleans up test/apptest ledgers older than 45 seconds that are not in `_recently_created_lids`. Real user ledgers (like `combat_29_funds` or custom names not matching test keywords) are never treated as ghost ledgers.

---

## 4. Conclusion

**Verdict: `APPROVE`**

The implementation of `MultiLedgerManager` workspace isolation and the 29-fund combat ledger (`combat_29_funds`) fully satisfies all functional, architectural, and adversarial requirements:
1. Workspace isolation is robust against directory variants and prevents test contamination.
2. Mount idempotency preserves user modifications while offering self-healing resilience.
3. Holding days (>= 365), zero redemption fee, and market value (¥26,615.10) are mathematically verified.
4. All 33 multi-ledger and combat test cases passed 100% green.

---

## 5. Verification Method

To independently verify these findings, execute the following commands in the workspace root:

1. **Run the 3 Dispatch Test Suites + Challenger Deep Stress Suite**:
   ```powershell
   py -3 -m pytest tests/test_multi_ledger_manager.py tests/test_multi_ledger_manager_stress.py tests/test_adversarial_m3_combat29_challenger.py tests/test_challenger_deep_stress_m3.py -v
   ```
   *Expected outcome*: 33 passed, 0 failed.

2. **Verify Referee Files Immutability & Infra Integrity**:
   ```powershell
   py -3 -m pytest tests/test_infra.py -v
   ```
   *Expected outcome*: 14 passed in < 10s.

3. **Verify Combat Ledger Exact Sum**:
   ```powershell
   py -3 -c "import json; d = json.load(open('data/ledgers/combat_29_funds.json', encoding='utf-8')); mv = sum(h['market_value'] for h in d['holdings']); print(f'Total MV: {mv:.2f}'); assert round(mv, 2) == 26615.10; print('PASS')"
   ```
