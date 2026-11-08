## 2026-11-08T04:05:49Z
You are an objective code reviewer (teamwork_reviewer).
Your working directory is: d:\Google\Workspace\Wind\.agents\teamwork\reviewer_g10_m1_1\

Mandatory read inputs:
- Read d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
- Read d:\Google\Workspace\Wind\GEMINI.md
- Read d:\Google\Workspace\Wind\AGENT_SPEC.md
- Read d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_11\SCOPE.md
- Read d:\Google\Workspace\Wind\.agents\teamwork\worker_g10_m1\handoff.md

Review Scope:
Review the code changes made by worker_g10_m1 in:
- AGY2_FundAdvisory/portfolio_manager.py (downside_only correlation, 0.80 stress jump threshold, liquidity shift plan, simulate_portfolio_cvar_bootstrap)
- AGY2_FundAdvisory/advisory_engine.py (downside correlation integration, ActiveRiskSentry, OTC fund non-linear liquidity haircut)
- AGY2_FundAdvisory/data_loader.py (Top 5 holdings ADV and AUM extraction, verify DataLoader.simulate_execution is 100% unchanged)
- AGY2_FundAdvisory/app_gui.py (col_sentry correlation card & liquidity metrics, Tab 1 & Tab 2 haircut table & Plotly 3D Monte Carlo chart, safe_markdown_html)
- tests/test_g10_correlation_liquidity_and_stress.py

Verification Tasks:
1. Run the test command:
   py -3 -m pytest tests/test_g10_correlation_liquidity_and_stress.py tests/test_infra.py tests/test_g3_evolution_loop.py
2. Verify that all requirements R1, R2, R3, R4, R5, R6 are correctly and completely satisfied.
3. Check code style, documentation, and interface conformance against SCOPE.md.

Output:
Write your review report to d:\Google\Workspace\Wind\.agents\teamwork\reviewer_g10_m1_1\handoff.md with a clear verdict: APPROVE or REQUEST_CHANGES.
When done, send a message to your caller with your verdict and report path.
