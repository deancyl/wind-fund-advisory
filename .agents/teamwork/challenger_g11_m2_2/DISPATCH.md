# Task Assignment: Challenger 2 (Milestone 2 Tab 2 Rebalance Engine Adversarial Verification)

## Target
`AGY2_FundAdvisory/app_gui.py` (Tab 2 Rebalancing & Orders)

## Inputs
- Authoritative Request: `d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md`
- Project Plan: `d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_15\PROJECT.md`
- Worker 2 Handoff: `d:\Google\Workspace\Wind\.agents\teamwork\worker_g11_m2\handoff.md`

## Objectives
Adversarially challenge Tab 2 Rebalancing & Execution Orders:
1. Test buffer slider boundaries (`tab2_rebal_buf_slider` from 0.0% to 10.0%).
2. Test rebalance diagnosis trigger (`btn_tab2_diagnose`) under:
   - Empty portfolio / cash-only portfolio.
   - All locked funds (<7 days).
   - High correlation portfolios.
3. Verify that rebalance orders dataframe (`df_orders_tbl`), VWAP schedule, and one-click follow button (`btn_confirm_follow_rebalance_tab2`) operate without exception.
4. Verify that the 4-cell summary bar and merged asset top bar reflect true values with 0 math anomalies.

Deliver verdict in `d:\Google\Workspace\Wind\.agents\teamwork\challenger_g11_m2_2\handoff.md`.


## 2026-11-08T13:58:37Z
You are challenger_g11_m2_2.
Your working directory is `d:\Google\Workspace\Wind\.agents\teamwork\challenger_g11_m2_2\`.
Read your task in `d:\Google\Workspace\Wind\.agents\teamwork\challenger_g11_m2_2\DISPATCH.md`.
Read `d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md`.
Read `d:\Google\Workspace\Wind\.agents\teamwork\worker_g11_m2\handoff.md`.
Adversarially challenge Tab 2 rebalance buffer slider, diagnosis trigger, orders table, and execution follow button in `AGY2_FundAdvisory/app_gui.py`.
Deliver your report and empirical correctness verdict in `d:\Google\Workspace\Wind\.agents\teamwork\challenger_g11_m2_2\handoff.md`.
Notify the orchestrator (conversation ID: c6b4ebd0-c5f1-4175-8ba5-3bd0979b970d) when done.
