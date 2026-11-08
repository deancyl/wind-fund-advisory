## 2026-11-08T03:38:18Z

You are a versatile implementation worker (teamwork_worker).
Your working directory is: d:\Google\Workspace\Wind\.agents\teamwork\worker_g10_m1\

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Mandatory read inputs:
- Read d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
- Read d:\Google\Workspace\Wind\GEMINI.md
- Read d:\Google\Workspace\Wind\AGENT_SPEC.md
- Read d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_11\SCOPE.md
- Read d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_g10_1\handoff.md (R2 Survey)
- Read d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_g10_2\handoff.md (R1 & R3 Survey)
- Read d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_g10_3\handoff.md (R4, R5, R6 Survey)

Write Ownership (you own these files exclusively):
- AGY2_FundAdvisory/portfolio_manager.py
- AGY2_FundAdvisory/advisory_engine.py
- AGY2_FundAdvisory/data_loader.py (ONLY for helper extraction; DataLoader.simulate_execution must remain strictly untouched!)
- AGY2_FundAdvisory/app_gui.py
- tests/test_g10_correlation_liquidity_and_stress.py

Mission Tasks:
1. R1 Safety Invariants:
   - Four read-only judge files (judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py) MUST NOT be modified under any circumstance.
   - DataLoader.simulate_execution default signature and fee logic MUST remain 100% read-only and unchanged.
   - Sharpe ratio calculation must deduct 2.0% annual risk-free rate. Zero look-ahead bias, no fake constants or pseudo-random series.

2. R2 Correlation Stress Mutation & Cross-Asset Liquidity Shift:
   - In AGY2_FundAdvisory/portfolio_manager.py and AGY2_FundAdvisory/advisory_engine.py:
     - Update compute_ewma_correlation with downside_only support and bench_series return filtering.
     - Update evaluate_dynamic_correlation_mutation: add 0.80 correlation jump threshold and cross-asset liquidity shift plan.
     - Fix asset selection: ensure high-volatility / high-valuation technology assets (e.g. 科技成长进攻, STAR50/chips, vol >= 0.22, valuation percentile > 70%) are selectively reduced by 15%-35% along with dividend/cyclical assets.
     - Reallocate cut weights: 60% to pure bond 002351 and 40% to physical gold feeder 000216. Ensure sum of adjusted weights == 1.000000.
     - Keep backward-compatible keys: status == "MUTATION_ALERT", action_type == "correlation_mutation_defense", text containing "集中度降级", while adding is_liquidity_shift_triggered and "流动性平移预案".

3. R3 OTC Mutual Fund Micro-Execution & Liquidity Haircut:
   - In AGY2_FundAdvisory/advisory_engine.py and data_loader.py:
     - Implement calculate_otc_fund_execution_slippage (and connect into calculate_vwap_execution_slippage).
     - Use non-linear Almgren-Chriss / Kyle lambda model based on fund AUM, top 5 holdings ADV, equity ratio, and daily volatility:
       Haircut_bps = sigma_day_bps * [kappa_1 * (Q * w_eq / ADV_top5)^0.5 + kappa_2 * (Q / AUM)^1.25 * (1 + ln(1 + AUM / ADV_top5))]
     - Strictly monotonically increasing with order amount Q (from 1,000 to 500,000 RMB), no constant clamp.
     - Physical isolation for ETFs (is_etf = True -> 0 bps).

4. R4 See-Through Multi-Period Monte Carlo Stress Testing:
   - In AGY2_FundAdvisory/portfolio_manager.py:
     - Implement simulate_portfolio_cvar_bootstrap(holdings, total_capital=100000.0, risk_level="C3", n_sims=10000, block_size=10):
       - Circular Block Bootstrap (block size 10 days, 10,000 resamples, vectorized).
       - Three historical scenarios: 2008 Financial Crisis, 2015 Liquidity Stampede, 2024 Small-cap Liquidity Crisis.
       - Output max drawdown prediction, CVaR 99% >= VaR 99% >= VaR 95%, liquidity liquidation days (based on settlement cycle, FIFO lock, and top 5 ADV), and risk tolerance check for C1-C5.
       - Export classmethod, instance method, and module-level alias.

5. R5 UI Wireup:
   - In AGY2_FundAdvisory/app_gui.py:
     - In col_sentry (right wing of double-wing dashboard): mount correlation stress mutation warning card and stress test liquidity metrics.
     - In Tab 1 & Tab 2: mount large order liquidity haircut table and Plotly 3D Monte Carlo distribution chart.
     - Enforce safe_markdown_html / _clean_html, theme adaptability, and 640px mobile responsive layout.

6. R6 Testing & Verification:
   - Create tests/test_g10_correlation_liquidity_and_stress.py with the 6 planned unit tests.
   - Run build and test commands:
     py -3 -m pytest tests/test_g10_correlation_liquidity_and_stress.py tests/test_infra.py tests/test_adv_final_closure.py tests/test_g3_evolution_loop.py tests/test_gui_multi_ledger_stress.py tests/test_g9_causal_brinson_and_suitability.py
   - Ensure all 65 tests pass 100%!

Output:
Write your complete implementation report to d:\Google\Workspace\Wind\.agents\teamwork\worker_g10_m1\handoff.md.
Include all test execution outputs and verification logs.
When finished, send a message to your caller indicating you are done and the report path.
