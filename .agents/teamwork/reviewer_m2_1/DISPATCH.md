# Dispatch for Reviewer 1 (M2)

Scope: Review Milestone 2 (R4 EWMA inverse-volatility dynamic risk budgeting & R5 rebalance net utility interceptor Delta U & T+2 in-transit discount).
Target files: data_loader.py, strategy_bridge.py, portfolio_manager.py
See orchestrator prompt for details.
## 2026-10-30T02:25:50Z
Sender: 7eb668ae-6843-4834-9b3d-3455ac86af88
Priority: MESSAGE_PRIORITY_HIGH

You are Reviewer 1 for Milestone 2 of the AGY2_FundAdvisory project.
Your working directory is d:\Google\Workspace\Wind\.agents\teamwork\reviewer_m2_1\
You MUST read d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md first before starting work.
Also read d:\Google\Workspace\Wind\.agents\teamwork\orchestrator\PROJECT.md and d:\Google\Workspace\Wind\.agents\teamwork\worker_agent2_m2\handoff.md.
Working directory for code is d:\Google\Workspace\Wind\AGY2_FundAdvisory.

Mission:
Examine data_loader.py, strategy_bridge.py, and portfolio_manager.py for correctness, completeness, robustness, and interface conformance for M2:
1. R4: `DataLoader.compute_ewma_volatility_and_correlation` and `compute_dynamic_tier_weights` inverse-volatility risk budgeting. Verify risk budget transfer to bond ballast, C1-C5 strict monotonicity, and bear stop-loss limits.
2. R5: `calculate_rebalance_net_utility`, same-company SWITCH (Delta t=0, cost=0), cross-company in-transit discount, Delta U <= 0 interception badge "🛡️ 摩擦/在途损耗大于预期收益，建议原地持仓不动", and same-company switching convenience bonus (+5.0 pts).
3. Run tests to independently verify:
   $env:PYTHONPATH="d:\Google\Workspace\Wind\AGY2_FundAdvisory;d:\Google\Workspace\Wind"; python -m pytest tests/test_m2_r4_r5_optimization.py tests/test_trading_clock_fee.py tests/test_portfolio_manager.py tests/test_infra.py -v
4. Write your review verdict (APPROVE or REQUEST_CHANGES) with clear evidence in d:\Google\Workspace\Wind\.agents\teamwork\reviewer_m2_1\handoff.md.
5. Send message to orchestrator with your verdict.
