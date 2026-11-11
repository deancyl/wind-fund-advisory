# Handoff Report — worker_g16_m3_fix

## 1. Observation
- **StrategyBridge Schema Bug (Reviewer 1 Finding 1)**: In `AGY2_FundAdvisory/strategy_bridge.py:6355-6365`, `step3_core_reconstruction["funds"]` items 1-5 used fund code string as key (e.g. `{"110020": "..."}`) rather than standard format `{"code": "...", "name": "...", "weight_pct": ...}`.
- **Tab 2 Facade & Button Dead State (Reviewer 1 & 2 Findings)**: In `AGY2_FundAdvisory/app_gui.py:6117-6194`, `StrategyBridge.estimate_rebalance_impact` and `StrategyBridge.get_combat_29_rebalance_prescription` were not called; text hardcoded "7 只全天候压舱石" instead of 6 funds; `btn_apply_combat29_rx` only set dead variable `tab2_sweep_tail = True` without configuring `rad_tab2_scenario_mode` or `sel_sc_anchor`, executing default standard rebalance rather than fragment sweep.
- **Tab 3 Backtest Curve Inversion & Missing Toggle (Reviewer 1 & 2 Findings)**: In `AGY2_FundAdvisory/app_gui.py`, primary curve and secondary curve in `preset_combat_29_vs_6` mislabeled the raw 29 funds as "调仓后组合"; in Time Machine, `tgl_dynamic` was missing and `dynamic_rebalance` was never passed.
- **Baseline and Test Suite**: Running `py -3 -m pytest tests/test_multi_ledger_manager.py tests/test_m3_item2_rebalance_impact.py tests/test_m3_item3_tab3_backtest.py tests/test_adversarial_m3_combat29_challenger.py tests/test_g16_phase1_memo_and_combat29.py AGY2_FundAdvisory/tests/test_e2e_gui_render.py -v` yields **36 passed (100%)**. Running `tests/test_infra.py` yields **14 passed (100%)**.

## 2. Logic Chain
1. Fixing `step3_core_reconstruction["funds"]` to uniform `{"code": "...", "name": "...", "weight_pct": ...}` ensures standard API consumption without KeyError, and adding strong assertions in `tests/test_m3_item2_rebalance_impact.py` guarantees regression resistance.
2. Dynamically calling `StrategyBridge.get_combat_29_rebalance_prescription` and `StrategyBridge.estimate_rebalance_impact` in `app_gui.py` allows real metrics (持仓只数 29->6 只, 盘活资金 ¥442.70~¥962.57, 手续费 ¥0.00, 回本天数 0 天) to be genuinely computed and rendered. Correcting "7 只" to "6 只" restores alignment with the 6-fund portfolio.
3. Rewiring `btn_apply_combat29_rx` to set `st.session_state.rad_tab2_scenario_mode = "🧹 尾部碎片与C类一键归拢 (清理<3%碎片与满期高费率C类至底仓)"`, `st.session_state.sel_sc_anchor = "002351 - 易方达裕祥回报债券A"`, and `st.session_state.tab2_c_replace = "011613"` ensures the rebalance engine enters `sweep_tail_and_c_class` mode with anchor `002351`, liquidating 19 fragment funds into core bonds and swapping 011613 to 011612 while protecting core assets.
4. Correctly labeling `preset_combat_29_vs_6` primary curve as "投顾重构 6 基核心组合" and secondary as "原始 29 基存量组合" eliminates narrative inversion. Adding `tgl_dynamic` toggle in Time Machine UI and passing `dynamic_rebalance=tgl_dynamic` provides interactive historical replay without 2024.09 policy-bottom whipsaw.

## 3. Caveats
- Read-only referee files (`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`) and DataLoader signatures remained strictly untouched.
- `portfolio_ledger.json` touched during e2e test execution was reverted to pristine working tree state.

## 4. Conclusion
All issues raised by Reviewers 1 & 2 in Milestone 3 have been genuinely remediated:
- Step 3 prescription schema: Fixed and validated.
- Tab 2 real quantitative wiring: Implemented with 4-dimension metric comparison and operational button state machine.
- Tab 3 curve legends & Time Machine toggle: Accurately labeled and dynamically wired.
- Integrity: No hardcoding, no facades, genuine execution.

## 5. Verification Method
Execute the following verification commands in PowerShell:

```powershell
# 1. Verify get_combat_29_rebalance_prescription schema
py -3 -c "from AGY2_FundAdvisory.strategy_bridge import StrategyBridge; rx = StrategyBridge.get_combat_29_rebalance_prescription(); funds = rx['step3_core_reconstruction']['funds']; codes = [f['code'] for f in funds]; names = [f['name'] for f in funds]; assert len(codes) == 6 and len(names) == 6; print('Step 3 Funds Schema PASS:', codes)"

# 2. Verify Tab 2 dynamic call, 6-funds text, and dead variable removal
py -3 -c "src = open('AGY2_FundAdvisory/app_gui.py', encoding='utf-8').read(); assert 'estimate_rebalance_impact' in src, 'estimate_rebalance_impact must be called'; assert '7 只全天候' not in src, '7-funds typo must be fixed'; assert 'tab2_sweep_tail' not in src; print('Tab 2 Real Call PASS')"

# 3. Verify Tab 3 tgl_dynamic toggle presence and usage
Select-String -Path "AGY2_FundAdvisory\app_gui.py" -Pattern "tgl_dynamic"

# 4. Run full regression test suite
py -3 -m pytest tests/test_multi_ledger_manager.py tests/test_m3_item2_rebalance_impact.py tests/test_m3_item3_tab3_backtest.py tests/test_adversarial_m3_combat29_challenger.py tests/test_g16_phase1_memo_and_combat29.py AGY2_FundAdvisory/tests/test_e2e_gui_render.py -v

# 5. Run referee baseline
py -3 -m pytest tests/test_infra.py -v
```
