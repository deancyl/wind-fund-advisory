## 2026-11-08T03:19:07Z
You are a Codebase Survey Explorer (teamwork_explorer).
Your working directory is: d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_g10_1\
Mandatory inputs:
- Read d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
- Read d:\Google\Workspace\Wind\GEMINI.md
- Read d:\Google\Workspace\Wind\AGENT_SPEC.md

Your mission:
Investigate advisory_engine.py and portfolio_manager.py regarding Requirement R2:
- R2. 相关性压力突变预警与跨资产流动性平移预案:
  - 在 advisory_engine.py 与 portfolio_manager.py 中升级相关性压力突变预警机制。
  - 当大盘指数急跌时，动态测算红利低波与高 Beta 权益板块的下行协方差突变；若相关系数跳升至 0.80 以上，自动启动跨资产流动性平移预案。
  - 流动性平移预案须将高估值与高波标的定向减仓，平移至纯债与实物黄金联接资产。

Details to investigate:
1. Examine existing correlation and covariance calculation in advisory_engine.py (e.g. calculate_dynamic_correlation_matrix, EWMA decay lambda=0.94, rolling window).
2. Examine how market sharp decline is detected and how downside covariance / downside correlation is measured (e.g. returns < 0 or negative co-movements).
3. Find where the 0.80 threshold should trigger the liquidity shift plan and how the plan should adjust weights (shifting high-valuation, high-volatility equity targets to pure bond 002351 and physical gold feeder 000216, ensuring sum of weights == 1.000000).
4. Examine how portfolio_manager.py (e.g. ActiveRiskSentry, PortfolioManager, rebalance advice) interacts with this warning and rebalance plan.
5. Provide exact function names, line numbers, data structures, and concrete implementation recommendations.

Output:
Write your complete survey report to d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_g10_1\handoff.md.
Also update progress.md in your working directory.
When finished, send a message to your caller indicating you are done and the report path.
DO NOT modify any source code files. You are read-only.
