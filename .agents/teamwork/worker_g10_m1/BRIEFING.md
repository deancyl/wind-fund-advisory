# BRIEFING — 2026-11-08T04:05:00Z

## Mission
Implement Generation 10: Dynamic Correlation Stress Mutation Defense, OTC Fund Micro-Execution Liquidity Haircut, and See-Through Multi-Period Block Bootstrap Monte Carlo Stress Testing across PortfolioManager, AdvisoryEngine, DataLoader, and GUI.

## 🔒 My Identity
- Archetype: teamwork_worker
- Roles: implementer, qa, specialist
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\worker_g10_m1\
- Original parent: 22f2ddb7-c220-44ca-b889-a5c0901cc3b3
- Milestone: G10 Full Implementation and Test Verification

## 🔒 Key Constraints
- 4 read-only judge files (judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py) MUST NOT be modified under any circumstance.
- DataLoader.simulate_execution default signature and fee logic MUST remain 100% read-only and unchanged.
- Sharpe ratio calculation must deduct 2.0% annual risk-free rate.
- Zero look-ahead bias, no fake constants or pseudo-random series. All implementations genuine.
- Safe HTML / CommonMark 4+ spaces defense, local GEMINI.md compliance, Chinese response requirement.

## Current Parent
- Conversation ID: 22f2ddb7-c220-44ca-b889-a5c0901cc3b3
- Updated: 2026-11-08T04:05:00Z

## Task Summary
- **What to build**: G10 R1-R6:
  - R1: Four read-only judge files strictly untouched; DataLoader.simulate_execution immutable; Sharpe ratio deducts 2.0% Rf.
  - R2: Correlation Stress Mutation & Cross-Asset Liquidity Shift (0.80 jump threshold, selective tech growth cut, 60% bond + 40% gold shift, weight sum = 1.000000).
  - R3: OTC Mutual Fund Micro-Execution & Liquidity Haircut model (Almgren-Chriss/Kyle non-linear, monotonically increasing, ETF isolation, top 5 ADV penetration).
  - R4: Multi-Period Block Bootstrap Monte Carlo Stress Testing (10k resamples, block size 10, 2008/2015/2024 scenarios, CVaR 99% >= VaR 99% >= VaR 95%, liquidation days, C1-C5 tolerance).
  - R5: UI Wireup in app_gui.py (col_sentry correlation card & stress card, Tab 1 & Tab 2 liquidity haircut table & 3D Monte Carlo chart).
  - R6: Comprehensive unit test suite tests/test_g10_correlation_liquidity_and_stress.py and full verification.
- **Success criteria**: All 6 unit tests pass, and full test suite (65 tests) passes 100%. (ACHIEVED: 65 passed in 78.03s).
- **Interface contracts**: SCOPE.md, GEMINI.md, AGENT_SPEC.md.
- **Code layout**: AGY2_FundAdvisory/ and tests/.

## Change Tracker
- **Files modified**:
  - AGY2_FundAdvisory/portfolio_manager.py: EWMA downside correlation, evaluate_dynamic_correlation_mutation with 0.80 stress threshold and selective tech growth cut + liquidity shift, simulate_portfolio_cvar_bootstrap with 10k block bootstrap.
  - AGY2_FundAdvisory/advisory_engine.py: ActiveRiskSentry dimension 7 stress threshold integration, SmartExecutionDCAEngine OTC liquidity haircut integration.
  - AGY2_FundAdvisory/data_loader.py: get_fund_top5_holdings_adv with 24h TTL cache, calculate_otc_fund_liquidity_haircut non-linear model.
  - AGY2_FundAdvisory/app_gui.py: mounted correlation mutation card, stress liquidity card, liquidity haircut table, and 3D Monte Carlo surface chart.
  - tests/test_g10_correlation_liquidity_and_stress.py: 6 comprehensive unit tests.
- **Build status**: 65 passed, 0 failed in 78.03s (100% PASS).
- **Pending issues**: None.

## Quality Status
- **Build/test result**: 65 passed, 121 warnings in 78.03s (100% pass rate).
- **Lint status**: Clean (py_compile passed with 0 errors).
- **Tests added/modified**: tests/test_g10_correlation_liquidity_and_stress.py (6 new tests).

## Loaded Skills
- lidaxiao-advisory referenced.

## Key Decisions Made
- Backward compatibility preserved: all existing keys (status='MUTATION_ALERT', action_type='correlation_mutation_defense', '集中度降级') preserved, with extension keys (is_liquidity_shift_triggered, '流动性平移预案') smoothly added.
- Monotonicity enforced: non-linear model combines square root term and 1.25 power term with continuous scaling to eliminate any artificial constant clamping platforms.

## Artifact Index
- DISPATCH.md — Task assignment
- BRIEFING.md — Persistent context
- progress.md — Liveness & step tracking
- handoff.md — Final completion report
