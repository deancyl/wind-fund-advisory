## 2026-11-05T15:46:22Z
You are a teamwork_challenger agent.
Your working directory: d:\Google\Workspace\Wind\.agents\teamwork\challenger_r9_m2_1
User request specification: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
Master Project document: d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_1\PROJECT.md
Worker M2 Handoff: d:\Google\Workspace\Wind\.agents\teamwork\worker_prod_r9_m2\handoff.md

Your mission is Adversarial Stress Testing of Rebalancing Scenarios (M2):
1. Write and execute stress tests for the 4 rebalancing scenarios:
   - `new_cash_only`: test boundary amounts (0.01, 1e7), verify buy amounts sum exactly to new cash, sell amounts strictly 0, redemption fees strictly 0.
   - `withdraw_cash_only`: test withdrawal with multiple holdings under 7 days lock (verify 0 shares redeemed), test withdrawal exceeding total equity, verify buy amounts strictly 0.
   - `freeze_reserved_cash`: verify reservation deduction when reserved cash > available cash (bounds at 0).
   - Test cache key mutation when changing scenarios or amounts.
2. Deliver handoff report with explicit verdict: `APPROVE` or `REQUEST_CHANGES`.
3. Notify orchestrator via `send_message` when done.
