# Milestone 3 Handoff Report: Test Suite Alignment & Invariant Verification

**Worker ID**: `worker_g11_m3`  
**Milestone**: Milestone 3 (Test Suite Alignment & Invariant Verification)  
**Date**: 2026-11-08  

---

## 1. Observation

### 1.1 Read-Only Referee Integrity & Checksums
We directly executed `Get-FileHash` and `git diff HEAD` to verify the four read-only referee files:
- `AGY2_FundAdvisory/judge_engine.py`: `76F930371176DE7EE6A413174B030101E3210AC6E037F5D10FE229AF31CC07BE`
- `AGY2_FundAdvisory/holdout_vault.py`: `88122EAF647040A410E2FD95DA81077DB10149A498A47340FF40B670BD031D2A`
- `AGY2_FundAdvisory/AGENT_SPEC.md`: `A346586F9BD2DC0EE83E665BD18E7A6471464C9F7B658E392B989B800CD63957`
- `tests/test_infra.py`: `48BEE0DA300D7C0A0848EC1376E4B9B2E55224D2736081713B4340F0362CD100`

`git diff HEAD -- AGY2_FundAdvisory/judge_engine.py AGY2_FundAdvisory/holdout_vault.py AGY2_FundAdvisory/AGENT_SPEC.md tests/test_infra.py AGY2_FundAdvisory/data_loader.py` returned exit code 0 and empty output. Checksums match canonical baseline records exactly.

### 1.2 `DataLoader.simulate_execution` Signature & Fee Logic
In `AGY2_FundAdvisory/data_loader.py:1437-1444`:
- Function signature: `simulate_execution(weights_df, prices_df, is_otc=True, penalty_days=7, penalty_rate=0.015, etf_impact=0.001) -> pd.DataFrame`
- T+1 execution shift and ladder fee deductions in lines 1511-1536 are 100% intact. Zero modifications.

### 1.3 Order String Matching in `PortfolioManager.apply_rebalance_orders_to_holdings`
- In `AGY2_FundAdvisory/portfolio_manager.py:6965-6990`, previous code only matched `"减持"` for sell and `"增持"`, `"建仓"`, `"买入"` for buy:
  ```python
  if "清仓" in action_desc:
      ...
  elif "减持" in action_desc and cur_h:
      ...
  elif "增持" in action_desc or "建仓" in action_desc or "买入" in action_desc:
      ...
  ```
- In `AGY2_FundAdvisory/app_gui.py:5567-5573`, the UI produces:
  - `"➕ 建议加仓"`
  - `"➖ 建议减仓"`
- Because `"减持"` is not a substring of `"➖ 建议减仓"` and `"增持"` is not a substring of `"➕ 建议加仓"`, standard buy/sell rebalance orders were not applied when clicking `btn_confirm_follow_rebalance_tab2`.
- We updated lines 6969 and 6989 in `AGY2_FundAdvisory/portfolio_manager.py`:
  ```python
  elif any(k in action_desc for k in ["减持", "减仓", "建议减仓", "卖出"]) and cur_h:
      ...
  elif any(k in action_desc for k in ["增持", "加仓", "建议加仓", "建仓", "买入"]):
      ...
  ```
- In `tests/test_challenger_tab2_rebalance_adversarial.py:444-450`, the test was updated to verify that `apply_rebalance_orders_to_holdings` successfully matches both `app_gui_rows` and `compatible_rows`, returning `fixed_count_app == 2`.

### 1.4 Test Suite Inspections for Obsolete Assertions
We systematically scanned `tests/test_adv_final_closure.py`, `tests/test_g3_evolution_loop.py`, `tests/test_gui_multi_ledger_stress.py`, and the entire `tests/` directory for:
- `btn_t1_run_all`
- `col_s1_step` / `col_s1_all`
- `render_workflow_step_indicator`
- Old divisive step indicator headers
Result: 0 occurrences in test assertions. All 50 tests in the 4 target suites already execute without being blocked by old GUI widgets.

### 1.5 Baseline Ledger Cleanliness
- Executed `git checkout -- portfolio_ledger.json data/portfolio_watchdog.json`.
- `data/ledgers_index.json` contains only `main_live`.
- `git status --short` confirms zero uncommitted changes to `portfolio_ledger.json` or `data/portfolio_watchdog.json`.

### 1.6 Pytest Verification Outputs
1. Target suites:
   `py -3 -m pytest tests/test_infra.py tests/test_adv_final_closure.py tests/test_g3_evolution_loop.py tests/test_gui_multi_ledger_stress.py`
   - Output: `50 passed, 121 warnings in 86.15s (100% green)`
2. Target suites + Challenger adversarial suite:
   `py -3 -m pytest tests/test_infra.py tests/test_adv_final_closure.py tests/test_g3_evolution_loop.py tests/test_gui_multi_ledger_stress.py tests/test_challenger_tab2_rebalance_adversarial.py`
   - Output: `80 passed, 121 warnings in 98.84s (100% green)`

---

## 2. Logic Chain

1. *Read-Only Constraints*:
   - Observation 1.1 confirms that SHA256 hashes of all four referee files (`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`) match the canonical values with 0 git diff.
   - Observation 1.2 confirms `DataLoader.simulate_execution` signature and fee logic are unchanged.
   - Therefore, the core safety baseline is completely preserved.

2. *Rebalance String Matching Alignment*:
   - Observation 1.3 showed that `app_gui.py` sends `建议加仓` and `建议减仓`, whereas `portfolio_manager.py` previously expected `增持` and `减持`.
   - Modifying line 6969 to `any(k in action_desc for k in ["减持", "减仓", "建议减仓", "卖出"])` and line 6989 to `any(k in action_desc for k in ["增持", "加仓", "建议加仓", "建仓", "买入"])` allows both UI-generated strings and canonical engine strings to trigger order application.
   - Updating `test_challenger_tab2_rebalance_adversarial.py` confirmed empirical fix with 2 orders applied.

3. *Test Suite Compatibility & Cleanliness*:
   - Observation 1.4 confirmed that no tests were asserting the deleted duplicate buttons or step indicator capsules.
   - Observation 1.5 confirmed ledger baselines were restored.
   - Observation 1.6 confirmed that all 50 target tests pass 100% green without regressions.

---

## 3. Caveats

- **Network-dependent tests in `test_adv_final_closure.py`**: Queries to Eastmoney endpoints emit `InsecureRequestWarning` (121 warnings captured), but pass reliably with network access.
- **`data/portfolio_watchdog.json` during test execution**: Some tests in `test_gui_multi_ledger_stress.py` write runtime states to `data/portfolio_watchdog.json`. Running `git checkout -- portfolio_ledger.json data/portfolio_watchdog.json` after running tests cleanses the working tree.
- No caveats regarding code modifications.

---

## 4. Conclusion

Milestone 3 is complete and verified:
1. Rebalance string matching in `AGY2_FundAdvisory/portfolio_manager.py` is fixed, correctly handling `"加仓"`, `"建议加仓"`, `"减仓"`, `"建议减仓"` alongside `"增持"`, `"减持"`, `"买入"`.
2. UI tests in `tests/test_adv_final_closure.py`, `tests/test_g3_evolution_loop.py`, `tests/test_gui_multi_ledger_stress.py` are confirmed compatible with the G11 Three-Block streamlined UI.
3. Baseline ledgers are restored and clean.
4. All 50 tests in `test_infra.py`, `test_adv_final_closure.py`, `test_g3_evolution_loop.py`, `test_gui_multi_ledger_stress.py` pass 100% green.
5. All 30 tests in `test_challenger_tab2_rebalance_adversarial.py` pass 100% green.
6. All read-only referee files and `DataLoader.simulate_execution` remain strictly untouched.

---

## 5. Verification Method

To independently verify the results, execute the following commands in PowerShell from `d:\Google\Workspace\Wind`:

1. **Verify Referee Integrity**:
   ```powershell
   powershell -NoProfile -Command "Get-FileHash AGY2_FundAdvisory/judge_engine.py, AGY2_FundAdvisory/holdout_vault.py, AGY2_FundAdvisory/AGENT_SPEC.md, tests/test_infra.py -Algorithm SHA256"
   git diff HEAD -- AGY2_FundAdvisory/judge_engine.py AGY2_FundAdvisory/holdout_vault.py AGY2_FundAdvisory/AGENT_SPEC.md tests/test_infra.py AGY2_FundAdvisory/data_loader.py
   ```
   *Expected result*: Checksums match Section 1.1; git diff is completely empty.

2. **Verify Target Pytest Suites**:
   ```powershell
   py -3 -m pytest tests/test_infra.py tests/test_adv_final_closure.py tests/test_g3_evolution_loop.py tests/test_gui_multi_ledger_stress.py
   ```
   *Expected result*: 50 passed in ~85s.

3. **Verify Challenger Adversarial Suite**:
   ```powershell
   py -3 -m pytest tests/test_challenger_tab2_rebalance_adversarial.py
   ```
   *Expected result*: 30 passed in ~35s.

4. **Verify Ledger Cleanliness**:
   ```powershell
   git status --short portfolio_ledger.json data/portfolio_watchdog.json data/ledgers_index.json
   ```
   *Expected result*: Zero modifications reported.
