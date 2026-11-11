# DISPATCH — worker_g16_m3_fix

## Role
teamwork_worker

## Working Directory
d:\Google\Workspace\Wind

## State Folder
d:\Google\Workspace\Wind\.agents\teamwork\worker_g16_m3_fix\

## Input Documents
- ORIGINAL_REQUEST.md: `d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md`
- SCOPE.md: `d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_g16_gen4\SCOPE.md`
- Reviewer 1 Report: `d:\Google\Workspace\Wind\.agents\teamwork\reviewer_g16_m3_1\handoff.md`
- Reviewer 2 Report: `d:\Google\Workspace\Wind\.agents\teamwork\reviewer_g16_m3_2\handoff.md`

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## PHYSICAL REDLINE INVARIANTS
1. NEVER modify the 4 read-only referee files:
   - `AGY2_FundAdvisory/judge_engine.py` (or root `judge_engine.py`)
   - `AGY2_FundAdvisory/holdout_vault.py` (or root `holdout_vault.py`)
   - `AGY2_FundAdvisory/AGENT_SPEC.md` (or root `AGENT_SPEC.md`)
   - `tests/test_infra.py` (or `AGY2_FundAdvisory/tests/test_infra.py`)
2. NEVER modify `DataLoader.simulate_execution` signature or default parameters or fee logic.

## Exclusively Owned Files
- `AGY2_FundAdvisory/strategy_bridge.py`
- `AGY2_FundAdvisory/app_gui.py`
- `tests/test_m3_item2_rebalance_impact.py`

## Specific Remediation Tasks
### Task 1: Fix `StrategyBridge.get_combat_29_rebalance_prescription` schema
In `AGY2_FundAdvisory/strategy_bridge.py` around line 6355-6365:
The dictionary `step3_core_reconstruction["funds"]` has keys as fund codes for items 1-5 (e.g. `{"110020": "易方达沪深300ETF联接A", "weight_pct": 21.80}`).
Fix all 6 items to have standard schema:
`{"code": "005561", "name": "创金合信中证红利低波动指数A", "weight_pct": 30.49}`
`{"code": "110020", "name": "易方达沪深300ETF联接A", "weight_pct": 21.80}`
`{"code": "017436", "name": "华安纳斯达克100ETF联接A", "weight_pct": 17.05}`
`{"code": "002351", "name": "易方达裕祥回报债券A", "weight_pct": 17.54}`
`{"code": "011612", "name": "华夏上证科创板50成份ETF联接A", "weight_pct": 7.79}`
`{"code": "000216", "name": "华安黄金ETF联接A", "weight_pct": 5.33}`
In `tests/test_m3_item2_rebalance_impact.py`, add strong assertion:
`assert all("code" in f and "name" in f and "weight_pct" in f for f in step3["funds"])`

### Task 2: Real Tab 2 Rebalance Impact Wiring & Button State Machine
In `AGY2_FundAdvisory/app_gui.py` around lines 6116-6200:
1. Dynamically call `rx_data = StrategyBridge.get_combat_29_rebalance_prescription()` and `impact = StrategyBridge.estimate_rebalance_impact(...)`.
2. Replace hardcoded "7 只全天候压舱石" with "6 只全天候核心压舱石".
3. Display the 4-dimension quantitative metrics in the comparison panel:
   - 持仓只数: 29 只 ➔ 6 只
   - 盘活零费率碎片资金: ¥442.70 ~ ¥962.57
   - 票息垫厚度提升: +1.32% (或由 impact 动态计算)
   - 预计回本天数: 0 天 (即时零损耗)
4. Fix the button `btn_apply_combat29_rx` click handler:
   ```python
   st.session_state.rad_tab2_scenario_mode = "🧹 尾部碎片与C类一键归拢 (清理<3%碎片与满期高费率C类至底仓)"
   st.session_state.sel_sc_anchor = "002351 - 易方达裕祥回报债券A"
   st.session_state.tab2_c_replace = "011613"
   st.session_state.tab2_diagnosed = True
   st.session_state.tab2_rebalanced = True
   st.session_state.tab2_trigger_rebalance = True
   st.session_state.tab2_rebal_cache = None
   st.rerun()
   ```

### Task 3: Tab 3 Backtest Curve Legend & Time Machine Dynamic Toggle
In `AGY2_FundAdvisory/app_gui.py`:
1. In `preset_combat_29_vs_6` backtest plotting (around line 7406-7411, 7610-7619, 7715-7722):
   Ensure the plot legends clearly distinguish:
   - Primary curve: "投顾重构 6 基核心组合" (reconstructed 6 funds)
   - Secondary curve: "原始 29 基存量组合" (raw 29 funds)
   NEVER label the raw 29 funds as "调仓后组合"!
2. In Tab 3 Time Machine (around line 7240):
   Add a toggle:
   `tgl_dynamic = st.toggle("⚡ 启用时光机动态再平衡（按信号敏捷轮动）", value=True, key="tm_dynamic_rebalance_toggle")`
   And pass `dynamic_rebalance=tgl_dynamic` into `StrategyBridge.run_historical_time_machine_backtest(...)`.

### Task 4: Verification
Run tests:
`py -3 -m pytest tests/test_multi_ledger_manager.py tests/test_m3_item2_rebalance_impact.py tests/test_m3_item3_tab3_backtest.py tests/test_adversarial_m3_combat29_challenger.py tests/test_e2e_gui_render.py tests/test_g16_phase1_memo_and_combat29.py -v`
Write `changes.md` and `handoff.md` in your state folder.
Notify orchestrator when done.
