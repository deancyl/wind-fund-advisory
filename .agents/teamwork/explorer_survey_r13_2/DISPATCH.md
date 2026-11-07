## 2026-11-07T13:52:31Z

You are Explorer 2 for the G6 codebase survey.
Working directory: d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r13_2\

MANDATORY FIRST STEP:
Read the authoritative user request at:
d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md

Your mission:
Deep technical investigation into Portfolio Target Volatility Risk Control and Dividend Tax-Free Rebalancing in portfolio_optimizer.py, portfolio_manager.py, and strategy_bridge.py.

Specifically investigate:
1. Target Volatility Risk Control:
   - User risk levels C1 to C5 definitions in the codebase and their target volatility ceilings (e.g. C1 Conservative <= 5%, C2 Cautious <= 8%, C3 Balanced <= 12%, C4 Growth <= 16%, C5 Aggressive <= 22%).
   - How past 20-day weighted rolling annualized volatility is currently computed or should be computed across user holdings.
   - Exact mathematical formula for the reduction ratio when current volatility exceeds target ceiling: how much to scale down high-volatility assets and transfer to pure bond (e.g. 002351) or cash buffer pool.
   - Integration points in portfolio_optimizer.py and how it affects Tab 1 and Tab 2 advice.
2. Dividend Reinvestment vs. Cash Dividend Dynamic Switching Rebalancing:
   - How portfolio_manager.py and ledger track fund holding days, dividend history, and dividend methods (reinvestment vs cash).
   - How to identify funds held >= 1 year (no dividend tax/redemption fee advantages).
   - Cost-benefit calculation: quantify the saved 0.50% redemption fee and trading friction/transit time when using cash dividends to fund new DCA/rebalancing targets vs directly redeeming and buying.
   - Output format in Tab 2 rebalancing recommendations.
3. Check interactions with existing transaction rules:
   - 7-day 1.50% penalty fee invariant.
   - FIFO batch tracking.
   - DataLoader.simulate_execution signature and fee rules (strictly read-only!).
4. Verify that four read-only files (judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py) are completely untouched.

Outputs:
Write your full findings to d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r13_2\report.md and a self-contained handoff to d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r13_2\handoff.md.
Then send a completion message with summary to your caller.
