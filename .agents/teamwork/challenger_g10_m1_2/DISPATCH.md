## 2026-11-08T04:06:17Z
You are an adversarial verifier (teamwork_challenger).
Your working directory is: d:\Google\Workspace\Wind\.agents\teamwork\challenger_g10_m1_2\

Mandatory read inputs:
- Read d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
- Read d:\Google\Workspace\Wind\GEMINI.md
- Read d:\Google\Workspace\Wind\AGENT_SPEC.md
- Read d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_11\SCOPE.md
- Read d:\Google\Workspace\Wind\.agents\teamwork\worker_g10_m1\handoff.md

Your adversarial mission:
Empirically verify the mathematical and financial correctness of:
1. Multi-period Monte Carlo stress testing in PortfolioManager.simulate_portfolio_cvar_bootstrap:
   - Run simulation on representative portfolios across C1, C2, C3, C4, C5.
   - Mathematically verify the fundamental risk axioms:
     CVaR_99 >= VaR_99 >= VaR_95 across all scenarios!
   - Verify that 2008 Financial Crisis, 2015 Liquidity Stampede, and 2024 Small-cap Crisis scenarios produce realistic and differentiated drawdown levels (e.g. 2008 has deepest equity drawdown, 2015 has highest liquidity liquidation days).
   - Verify liquidity liquidation days calculation is deterministic and accounts for FIFO locks and top 5 ADV.
   - Check that for C1 conservative investors, high-equity portfolios trigger `exceeds_risk_tolerance = True`, whereas for C5 aggressive investors they are within limits.

Execute your stress testing script with `py -3 <script>` and verify all assertions pass.
Write your report to d:\Google\Workspace\Wind\.agents\teamwork\challenger_g10_m1_2\handoff.md with a clear verdict: APPROVE or REJECT.
When done, send a message to your caller with your verdict and report path.
