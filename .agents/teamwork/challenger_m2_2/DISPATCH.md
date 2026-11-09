# Milestone 2 Challenger 2 Dispatch

## Mission
Perform adversarial stress testing on Milestone 2 UI components and friction logic:
1. `render_chief_advisor_memo_card`: Test with malformed dictionary, HTML injection, missing badges or contents, verify no raw HTML code block leaks (CommonMark 4-space indent defense).
2. `StrategyBridge.run_historical_time_machine_backtest`:
   - Verify minimum sample limit (<60 days raises ValueError).
   - Verify future slice limit (<2 days raises ValueError).
   - Verify alpha vs H00300 and benchmark_nav calculations.
3. Verify referee files are untouched: `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`.
4. Run automated tests and write `handoff.md` with verdict.

## 2026-11-09T18:08:39Z
You are `challenger_m2_2` for G15 Generation Milestone 2 (Phase 2): "破除唯算法论：实装五维投顾首席备忘录与历史任意时点盲测时光机".

Your working directory is:
`d:\Google\Workspace\Wind\.agents\teamwork\challenger_m2_2\`
Write your progress.md and handoff.md inside this directory.

Review the authoritative project files before starting:
- `d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md` (lines 169-204)
- `d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_18\PROJECT.md`
- `d:\Google\Workspace\Wind\.agents\teamwork\challenger_m2_2\DISPATCH.md`
- Worker Handoff: `d:\Google\Workspace\Wind\.agents\teamwork\worker_m2\handoff.md`

PHYSICAL SAFETY REDLINES (ZERO TOLERANCE):
- Verify the 4 read-only referee files are 100% untouched: `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`.
- Verify `DataLoader.simulate_execution` default signature and default fee logic are untouched.

CHALLENGE TASKS:
1. Adversarial verification of UI components:
   - Check `render_chief_advisor_memo_card`: verify that it sanitizes HTML and does not trigger CommonMark 4-space code block syntax leakage.
   - Test `render_chief_advisor_memo_card` when called with empty, partial, or malformed data.
   - Check Tab 3 Time-Machine UI rendering: verify that preset dates work, custom date picker works, and Plotly curve generates cleanly without NaN / inf values.
2. Adversarial verification of historical inflection points:
   - Run `run_historical_time_machine_backtest` at key historical inflection points:
     - 2021-02-18 (core assets peak)
     - 2022-04-26 (market crash bottom)
     - 2024-09-18 (pre-policy reversal bottom)
     - Verify outputs match financial reality and historical market movements.
3. Run automated tests and write a comprehensive handoff.md with a definitive qualitative verdict (APPROVE or REQUEST_CHANGES). Send a message to parent when done.
