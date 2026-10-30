## 2026-10-30T01:56:26Z
[Message] timestamp=2026-10-30T01:56:26Z sender=7eb668ae-6843-4834-9b3d-3455ac86af88 priority=MESSAGE_PRIORITY_HIGH content=You are Agent-2 (动态风险平价与摩擦效用优化专家) for Milestone 2 of the AGY2_FundAdvisory project.
Your working directory is d:\Google\Workspace\Wind\.agents\teamwork\worker_agent2_m2\
You MUST read d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md first before starting work.
Also read the detailed blueprint in d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_2\handoff.md and d:\Google\Workspace\Wind\.agents\teamwork\orchestrator\PROJECT.md.
Working directory for code is d:\Google\Workspace\Wind\AGY2_FundAdvisory.

Your write ownership covers:
- data_loader.py
- strategy_bridge.py
- portfolio_manager.py
STRICT READ-ONLY SAFETY REDLINE: NEVER touch, modify, or unlock judge_engine.py, holdout_vault.py, AGENT_SPEC.md, or tests/test_infra.py!

Tasks:
1. Implement R4 (滚动 EWMA 波动率倒数与动态风险预算配权):
   - In data_loader.py: implement `DataLoader.compute_ewma_volatility_and_correlation(df, window=60, span=60, asset_cols=None) -> Tuple[pd.Series, pd.DataFrame]`.
   - In strategy_bridge.py: in `compute_dynamic_tier_weights`, calculate 60-day EWMA annualized volatility sigma_{k,t} and correlation matrix; perform inverse volatility weighting (scaling proportional to base_vol / max(vol, 0.08)); transfer trimmed excess risk budget 100% to low-vol pure bond ballast (002351 / 000086); preserve C1-C5 risk monotonicity theorem: Equity(C1) < Equity(C2) < Equity(C3) < Equity(C4) < Equity(C5) across bull, bear, and oscillating states, and ensure deep bear stop-loss limits (Equity(C4) <= 55%, Equity(C5) <= 70%).
2. Implement R5 (调仓净效用拦截器与真实 A/C 阶梯费率及 T+2 在途踏空折价):
   - In portfolio_manager.py: implement `calculate_rebalance_net_utility(from_fund_code, to_fund_code, amount, expected_alpha_20d=None, market_snapshot=None) -> Dict[str, Any]` calculating Delta U = ExpectedAlphaGain_20d - ExactRedemptionFee(FIFO) - SubscriptionFee - InTransitOpportunityCost(Delta t, sigma_index).
   - Same-company T+1 SWITCH: Delta t_arrive = 0 => InTransitOpportunityCost = 0.
   - Cross-company redemption + subscription: Delta t_arrive = 2~4 days with index volatility discount.
   - When Delta U <= 0, intercept and badge with "🛡️ 摩擦/在途损耗大于预期收益，建议原地持仓不动", and do not generate executable orders.
   - In fund scoring / selection: add same-company switching convenience bonus (+5.0 points) if candidate fund belongs to a fund company already held in user's portfolio.
3. Test Verification:
   - Run tests: $env:PYTHONPATH="d:\Google\Workspace\Wind\AGY2_FundAdvisory;d:\Google\Workspace\Wind"; python -m pytest tests/test_trading_clock_fee.py tests/test_portfolio_manager.py tests/test_infra.py tests/test_strategy_bridge.py -v
   - Ensure all pass 100%. (Do not run tests that hang on unmocked external network calls).
4. Reporting:
   - Write your handoff report to d:\Google\Workspace\Wind\.agents\teamwork\worker_agent2_m2\handoff.md following standard format.
   - Send completion message to orchestrator.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.


## 2026-10-30T02:06:40Z
[Message] timestamp=2026-10-30T02:06:40Z sender=7eb668ae-6843-4834-9b3d-3455ac86af88 priority=MESSAGE_PRIORITY_HIGH content=**Context**: Milestone 2 Implementation (R4 EWMA risk budgeting & R5 friction utility interceptor)
**Content**: Heartbeat status check: How is your progress on Milestone 2? Have you completed inspecting data_loader.py, strategy_bridge.py, and portfolio_manager.py, and started implementation of R4/R5?
**Action**: Please provide a brief update on your current step.
