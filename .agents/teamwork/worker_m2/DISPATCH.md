# Milestone 2 Dispatch: Five-Dimensional Chief Advisor Memo & Historical Time-Machine Blind Backtesting

## Mission
Implement G15 Milestone 2 (Phase 2):
1. `generate_chief_advisor_memo(snapshot, holdings, radar_top3, sentry_rep, **kwargs)` in `AGY2_FundAdvisory/advisory_engine.py`
2. `render_chief_advisor_memo_card(memo_data, title=...)` in `AGY2_FundAdvisory/app_gui.py` and mount in initial screen advisor dashboard and Tab 1 top
3. `run_historical_time_machine_backtest(target_date, tier, capital, df)` in `AGY2_FundAdvisory/strategy_bridge.py`
4. Tab 3 top Historical Time-Machine blind backtesting UI in `AGY2_FundAdvisory/app_gui.py`
5. Create targeted test suite `tests/test_g15_phase2_memo_and_timemachine.py` and run full regression tests.

## Reference Blueprint
- Survey Report: `d:\Google\Workspace\Wind\.agents\teamwork\explorer_g15_survey_2_rep\handoff.md`
- Project Document: `d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_18\PROJECT.md`
- Original Request: `d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md`

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Safety Redlines
- NEVER touch the 4 read-only referee files: `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`.
- NEVER modify `DataLoader.simulate_execution` default signature and fee logic.

## 2026-11-09T17:37:08Z
[Message received from orchestrator 9a123e21-7525-4c57-9715-710c2a94c199]
Mission: G15 Generation Milestone 2 (Phase 2): "破除唯算法论：实装五维投顾首席备忘录与历史任意时点盲测时光机".
Tasks:
1. `AGY2_FundAdvisory/advisory_engine.py`:
   - Implement `generate_chief_advisor_memo(snapshot, holdings, radar_top3, sentry_rep, **kwargs)` producing the 5 dimensions.
2. `AGY2_FundAdvisory/app_gui.py`:
   - Implement `render_chief_advisor_memo_card(memo_data, title=...)` with responsive cards and clean HTML formatting. Dual mounting (wing_expander & Tab 1).
3. `AGY2_FundAdvisory/strategy_bridge.py`:
   - Implement `StrategyBridge.run_historical_time_machine_backtest(target_date, tier="C3", capital=100000.0, df=None)`:
     Point-in-Time, deduct full public fund transaction frictions, calculate 3M, 6M, 1Y, and all-period metrics.
4. `AGY2_FundAdvisory/app_gui.py`:
   - In Tab 3 `render_tab3_backtest_content`: Mount Time-Machine blind backtest UI with 4 preset buttons, custom date, 4-horizon KPI metric cards, interactive comparison curve.
5. Test Suite & Verification:
   - Create `tests/test_g15_phase2_memo_and_timemachine.py`.
   - Run tests.
