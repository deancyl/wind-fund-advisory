## 2026-11-08T15:42:45Z
You are teamwork_reviewer for Milestone 1 of G12 Generation.
Your Identity: teamwork_reviewer
Your Working Directory: d:\Google\Workspace\Wind\.agents\teamwork\reviewer_g12_m1_1\
Authoritative Request: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
Scope Document: d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_16\PROJECT.md
Worker Handoff Report: d:\Google\Workspace\Wind\.agents\teamwork\worker_g12_m1\handoff.md

Review tasks for Milestone 1:
1. Verify Bug 1 (correlation gate check in app_gui.py:2987 and portfolio_manager.py:8628 aliases).
2. Verify Bug 2 (sentry.inspect_portfolio investor_risk_tier & fund_quotes snapshot injection in app_gui.py:2725).
3. Verify Bug 3 (_apply_fund_valuation_calibration in portfolio_manager.py with 0.95 feeder factor).
4. Verify Bug 4 (compute_portfolio_weighted_bias_and_erp in advisory_engine.py and app_gui.py).
5. Run the build/test commands:
   - py -3 -m pytest tests/test_infra.py
   - py -3 -m pytest tests/test_g12_circuit_breakers_and_sentry.py
   - py -3 -m pytest tests/test_adv_final_closure.py
6. Verify 4 referee files (judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py) are untouched (0 git diff).
7. Issue a definitive verdict: APPROVE or REQUEST_CHANGES.
Write your report to `d:\Google\Workspace\Wind\.agents\teamwork\reviewer_g12_m1_1\handoff.md` and send a message back.
