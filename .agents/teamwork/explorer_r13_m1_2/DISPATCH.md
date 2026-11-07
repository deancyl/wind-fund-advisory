## 2026-11-07T14:06:54Z
You are Explorer M1-2 for Milestone 1 (Risk Control & Dividend Rebalancing).
Working directory: d:\Google\Workspace\Wind\.agents\teamwork\explorer_r13_m1_2\

MANDATORY FIRST STEP:
Read the authoritative user request at:
d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md

Also read the Scope specification at:
d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_8\SCOPE.md
And reference survey report at:
d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r13_2\report.md

Your mission:
Formulate the exact implementation plan and production-ready code design for Target Volatility Risk Control and Dividend Cash Rebalancing.
Specifically detail:
1. portfolio_optimizer.py:
   - TARGET_VOLATILITY_BY_TIER definition (C1: 0.05, C2: 0.08, C3: 0.12, C4: 0.16, C5: 0.22).
   - Implementation of apply_target_volatility_risk_control(current_holdings, user_risk_tier):
     * Calculate 20-day weighted rolling annualized volatility using SmartExecutionDCAEngine.get_fund_real_volatility_and_bias.
     * Check if current_vol > target_vol.
     * Calculate reduction ratio = (current_vol - target_vol) / current_vol.
     * Reduce high-volatility holdings (vol > 0.08) by this ratio, transfer released funds to pure bond 002351 or cash buffer.
     * Ensure weights strictly normalize to 1.000000.
2. portfolio_manager.py:
   - Implementation of evaluate_dividend_cash_rebalancing(holdings_or_ledger):
     * Identify dividend/core funds with holding_days >= 365.
     * Calculate dividend yield from dividend_yield_map.
     * Quantify saved 0.50% redemption fee + in-transit loss (0.16%~0.30%) compared to manual redemption and repurchase.
     * Return structured output for Tab 2 rebalancing recommendation.
3. Transaction rules & safety:
   - Zero violation of <7 days 1.50% penalty fee.
   - FIFO batch integrity.
   - DataLoader.simulate_execution signature and fee rules MUST NOT be modified.
   - Four referee files (judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py) MUST NOT be modified.

Outputs:
Write your full technical strategy to d:\Google\Workspace\Wind\.agents\teamwork\explorer_r13_m1_2\report.md and a self-contained handoff to d:\Google\Workspace\Wind\.agents\teamwork\explorer_r13_m1_2\handoff.md.
Then send a completion message with summary to your caller.
