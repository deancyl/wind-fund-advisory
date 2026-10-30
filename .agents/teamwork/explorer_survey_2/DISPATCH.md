## 2026-10-30T00:58:57Z
You are Explorer 2 for the AGY2_FundAdvisory self-evolving quant engine project.
Your working directory is d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_2\
You MUST read d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md first before starting work.
Working directory for code is d:\Google\Workspace\Wind\AGY2_FundAdvisory.

Mission:
Investigate data_loader.py, portfolio_manager.py, and strategy_bridge.py in d:\Google\Workspace\Wind\AGY2_FundAdvisory.
Focus on:
1. compute_dynamic_tier_weights, asset return/volatility calculations, C1~C5 tier risk budgets and drawdowns.
2. Existing fee structures (A/C shares, FIFO holding period redemption fees, subscription fees), rebalancing orders generation, and in-transit friction handling.
3. Requirements and exact code insertion points for:
   - R4: Rolling 60-day EWMA annualized volatility sigma_{k,t} and correlation matrix in compute_dynamic_tier_weights (in data_loader.py / strategy_bridge.py); inverse volatility risk budgeting w_{k,t} proportional to SignalScore_{k,t} / sigma_{k,t}; transferring excess risk budget to low-volatility pure bond ballast.
   - R5: Rebalancing net utility interceptor Delta U = ExpectedAlphaGain_20d - ExactRedemptionFee(FIFO) - SubscriptionFee - InTransitOpportunityCost(Delta t_arrive, sigma_index).
     - Same-company T+1 SWITCH -> Delta t_arrive = 0.
     - Cross-company redemption + subscription -> Delta t_arrive = 2~4 days with index volatility discount.
     - MinNetBenefitThreshold interception: mark as "🛡️ 摩擦/在途损耗大于预期收益，建议原地持仓不动".
     - Candidate selection convenience bonus for same-company switching.
4. Record all relevant classes, functions, variable names, interfaces, and dependencies.
5. Check which files are read-only and must NOT be touched (judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py).

Deliverables:
- Keep updating d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_2\progress.md with timestamps.
- Write your detailed investigation report to d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_2\handoff.md following standard handoff structure (Observation, Logic Chain, Caveats, Conclusion, Verification Method).
- Send a message to orchestrator when completed.


## 2026-10-30T01:08:37Z
**Context**: Survey Phase
**Content**: Explorer 1 and Explorer 3 have completed their survey handoff reports. How is your survey progressing on R4 (EWMA volatility reciprocal risk budgeting in data_loader.py / strategy_bridge.py) and R5 (friction & in-transit utility interceptor in portfolio_manager.py)?
**Action**: Please let me know your status or finalize your handoff.md report.
