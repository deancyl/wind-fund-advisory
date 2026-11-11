## 2026-11-11T02:40:35Z
You are worker_m3 (Milestone 3 Implementer Worker).

【Mandatory Integrity Warning】
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

【Identity & Constraints】
- Working directory: d:\Google\Workspace\Wind
- State folder: d:\Google\Workspace\Wind\.agents\teamwork\worker_m3
- MANDATORY: Read d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md before starting work.
- Also read:
  - d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_g16_gen3\SCOPE.md
  - d:\Google\Workspace\Wind\.agents\teamwork\explorer_m3_1\analysis.md and handoff.md
  - d:\Google\Workspace\Wind\.agents\teamwork\explorer_m3_2\analysis.md and handoff.md
  - d:\Google\Workspace\Wind\.agents\teamwork\explorer_m3_3\analysis.md and handoff.md
- File Ownership: You exclusively own:
  1. `AGY2_FundAdvisory/multi_ledger_manager.py`
  2. `AGY2_FundAdvisory/strategy_bridge.py`
  3. `AGY2_FundAdvisory/app_gui.py`
  4. Unit test additions in `tests/`
- PHYSICAL REDLINE INVARIANTS:
  - NEVER modify the 4 read-only referee files: `AGY2_FundAdvisory/judge_engine.py`, `AGY2_FundAdvisory/holdout_vault.py`, `AGY2_FundAdvisory/AGENT_SPEC.md`, `tests/test_infra.py`.
  - NEVER modify `DataLoader.simulate_execution` signature or default fee/delay parameters!
  - NEVER modify `data/ledgers/combat_29_funds.json` static holding_days (keep 400).

【Implementation Plan】
Task 1: `multi_ledger_manager.py` Idempotent Mount & Test Isolation
- In `_ensure_index_initialized`: add root directory check `if str(self.root.resolve()).lower() == str(WORKSPACE_ROOT.resolve()).lower():` around the automatic mounting of `combat_29_funds`.
- This ensures `combat_29_funds` is mounted in production/UI while protecting pytest `temp_workspace` isolation in `tests/test_multi_ledger_manager.py` (fixing `test_get_all_ledgers_summary`) and `tests/test_multi_ledger_manager_stress.py`.

Task 2: `app_gui.py` Holding Days Copy & Tab 2 3-Step Refactor Prescription
- Holding days copy: In lines ~6134 and ~6145, reconcile copy to "400~1,040+ 天（基准 400 天 / 现已超 1,040 天，均成立满1年以上）".
- Tab 2 Rebalance Prescription Panel (`if active_lid == "combat_29_funds":`):
  - Replace static text with a 4-dimensional comparative metric grid (29->6 core funds, ¥442.70~¥962.57 revitalized cash, dividend cushion boost & zero C-class sales fee, 0 days fee payback).
  - Add action button `[🧹 一键模拟三步瘦身重构（清扫19只免赎尾仓 + 置换深套出血点）]` with `st.session_state` state-machine binding that activates sweep tail cleaner & C-class replacement for `011613`.
  - Ensure all HTML passes through `_clean_html` and `safe_markdown_html` (Rules 27, 28).

Task 3: `strategy_bridge.py` Impact Estimation & Backtest Enhancements
- `estimate_rebalance_impact`:
  - Keep full backward compatibility.
  - Return additional keys: `fund_count_before`, `fund_count_after`, `revitalized_cash_min` (442.70), `revitalized_cash_max` (962.57), `c_class_fee_saved_annual`, `payback_days_shortened`.
  - Add convenience method `get_combat_29_rebalance_prescription()`.
- Tab 3 Backtest Preset & `code_to_col_alpha`:
  - Expand `code_to_col_alpha` mapping for all 29 funds in `combat_29_funds.json`.
  - Add `get_combat_29_vs_reconstructed_6_preset()` returning exact weights: `005561`: 30.49%, `110020`: 21.80%, `017436`: 17.05%, `002351`: 17.54%, `011612`: 7.79%, `000216`: 5.33% (sum = 1.0000).
- `run_historical_time_machine_backtest`:
  - Add optional parameter `dynamic_rebalance: bool = False` (MUST default to False for backward compatibility with existing tests).
  - When `dynamic_rebalance=True`, perform Point-in-Time weight updates with T+1 execution delay and 10 bps friction, eliminating the static freeze during the September 2024 policy reversal (+32.29% return vs CSI 300's +24.53%).

Task 4: `app_gui.py` Tab 3 Backtest UI
- In Tab 3 `bt_mode` options, add `"🎯 实战存量组合：原始29基 vs 投顾重构6基（近1年真规则回测对比）"`.
- When selected, load dual curves for 29 funds vs reconstructed 6 funds over the past 250 trading days.
- Add dynamic rebalance toggle `tgl_dynamic = st.toggle("启用时光机动态再平衡（按日/周信号敏捷调仓）", value=True)` passed into `run_historical_time_machine_backtest`.

【Verification Requirements】
Run all of the following commands and include full output in your report:
1. `py -3 -m pytest tests/test_multi_ledger_manager.py` (Must PASS 8/8)
2. `py -3 -m pytest tests/test_multi_ledger_manager_stress.py` (Must PASS 8/8)
3. `py -3 -m pytest tests/test_adversarial_m3_combat29_challenger.py` (Must PASS 9/9)
4. `py -3 -m pytest AGY2_FundAdvisory/tests/test_realtime_and_upgrades.py -k test_estimate_rebalance_impact` (Must PASS)
5. `py -3 -m pytest tests/test_adversarial_m2_challenger2_timemachine_and_memo.py` (Must PASS)
6. `py -3 -m pytest tests/test_infra.py` (Must PASS 14/14, 0 referee modifications)
7. Write and run `tests/test_m3_item2_rebalance_impact.py` and `tests/test_m3_item3_tab3_backtest.py` to confirm 100% coverage.

【Deliverables】
1. Complete code implementations in the 3 owned files.
2. Write `changes.md` and `handoff.md` in `d:\Google\Workspace\Wind\.agents\teamwork\worker_m3\`.
3. Send a brief message back to orchestrator when completed.
