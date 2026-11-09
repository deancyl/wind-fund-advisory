# Milestone 2 Challenger 1 Dispatch

## Mission
Perform adversarial challenge & empirical verification on Milestone 2:
1. `generate_chief_advisor_memo`: Test edge cases (None inputs, zero holdings, missing keys, extreme macro indicators like inverted yield curve, DR007 spikes, ERP extremes).
2. `run_historical_time_machine_backtest`:
   - Empirically verify Point-in-Time integrity: ensure changing future data does NOT change historical weights at T.
   - Verify transaction frictions: subscription fee, C-share daily sales fee, step-down redemption fees FIFO (<7d 1.50%).
   - Verify boundary dates (e.g., historical extreme days: 2021-02-18, 2022-04-26, 2024-09-18, 2025-11-09).
3. Verify referee files are untouched: `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`.
4. Run automated tests and write `handoff.md` with verdict.

## 2026-11-09T18:07:57Z
You are `challenger_m2_1` for G15 Generation Milestone 2 (Phase 2): "破除唯算法论：实装五维投顾首席备忘录与历史任意时点盲测时光机".

Your working directory is:
`d:\Google\Workspace\Wind\.agents\teamwork\challenger_m2_1\`
Write your progress.md and handoff.md inside this directory.

Review the authoritative project files before starting:
- `d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md` (lines 169-204)
- `d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_18\PROJECT.md`
- `d:\Google\Workspace\Wind\.agents\teamwork\challenger_m2_1\DISPATCH.md`
- Worker Handoff: `d:\Google\Workspace\Wind\.agents\teamwork\worker_m2\handoff.md`

PHYSICAL SAFETY REDLINES (ZERO TOLERANCE):
- Verify the 4 read-only referee files are 100% untouched: `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`.
- Verify `DataLoader.simulate_execution` default signature and default fee logic are untouched.

CHALLENGE TASKS:
1. Adversarial verification of `generate_chief_advisor_memo`:
   - Empty/None inputs handling.
   - Extreme inputs: negative DR007 spread, inverted yield curves, ERP percentiles (0% and 100%), deep loss holdings (>-50%), large tail fragments.
   - Verify all 5 dimensions return structured text without crashing or raising exceptions.
2. Adversarial verification of `StrategyBridge.run_historical_time_machine_backtest`:
   - Verify Point-in-Time integrity: does running backtest at target_date strictly ignore all data after target_date?
   - Verify fee deductions:
     - 0.12% front-end subscription fee applied on day 0
     - Daily 0.40% / 250 sales service fee deducted
     - FIFO step-down redemption fee: <7 days 1.50%, <30 days 0.50%, <180 days 0.35%, <365 days 0.15%, >=365 days 0.00%
   - Verify benchmark calculations (H00300 and BENCHMARK_50_50).
   - Verify boundary conditions (<60 days raises ValueError; <2 days forward raises ValueError).
3. Run automated tests and write a comprehensive handoff.md with a definitive qualitative verdict (APPROVE or REQUEST_CHANGES). Send a message to parent when done.
