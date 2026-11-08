# BRIEFING — 2026-11-08T03:32:00Z

## Mission
Investigate portfolio_manager.py, AGY2_FundAdvisory/app_gui.py, and tests/ for R4 (Monte Carlo Stress Test with Block Bootstrap), R5 (UI/visual audit for double-wing dashboard, Tab 1 & Tab 2 liquidity/stress test components), and R6 (test baseline & new test plan).

## 🔒 My Identity
- Archetype: teamwork_explorer
- Roles: Codebase Survey Explorer
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_g10_3\
- Original parent: 22f2ddb7-c220-44ca-b889-a5c0901cc3b3
- Milestone: G10 Milestone 3 Survey (R4, R5, R6)

## 🔒 Key Constraints
- Read-only investigation — do NOT implement or modify source code
- Chinese response in communications
- Strictly adhere to GEMINI.md invariants (Rules 18, 27, 28, etc.)

## Current Parent
- Conversation ID: 22f2ddb7-c220-44ca-b889-a5c0901cc3b3
- Updated: 2026-11-08T03:32:00Z

## Investigation State
- **Explored paths**:
  - `AGY2_FundAdvisory/portfolio_manager.py` (lines 8369-8566: correlation mutation, class structure)
  - `AGY2_FundAdvisory/winrate_engine.py` (lines 776-1081: `simulate_black_swan_stress`, `simulate_monte_carlo_block_bootstrap_stress`)
  - `AGY2_FundAdvisory/strategy_bridge.py` (lines 191-275: `RISK_TIERS_CONFIG`, lines 4881-4945: `build_custom_portfolio_backtest`)
  - `AGY2_FundAdvisory/advisory_engine.py` (lines 1395-1930: `ActiveRiskSentry`, lines 2349-2480: `calculate_vwap_execution_slippage`)
  - `AGY2_FundAdvisory/app_gui.py` (lines 183-200: safe HTML, lines 1298-1376: 640px CSS, lines 1476-1586: stress cards, lines 1791-1823: Plotly theme, lines 2538-2906: double-wing dashboard, lines 2975-2980: tabs, lines 3530-3600 & 4015-4115: Tab 1, lines 5500-5645: Tab 2)
  - `tests/` (verified 59 baseline tests across 5 modules)
  - `data/processed/indices/` (verified availability of 2008 and 2015 historical index data)
- **Key findings**:
  - `simulate_portfolio_cvar_bootstrap` is not yet defined in `portfolio_manager.py` and should be added at lines 8547+ with both classmethod and instance method wrappers.
  - Historical scenarios: 2008 Financial Crisis (-72.3% CSI300), 2015 Stampede (-43.3% to -46.5%), 2024 Small-Cap (-26.7% CSI1000) can be modeled using asset-class returns and 10-day block bootstrap (10,000 resamples).
  - C1-C5 integration: contract limits (-5%, -10%, -15%, -25%, -40%), breach calculation, and liquidity liquidation days ($T_{liq} = T_{base} \times \lambda_{scenario} + T_{lock} + T_{adv}$).
  - UI injection points in `app_gui.py`: double-wing dashboard right wing, Tab 1 Step 3/4, Tab 2 execution section. Plotly 3D charts supported via `apply_theme_to_plotly_figure`.
  - Test baseline: 59 tests exact. Planned 6 new tests in `tests/test_g10_correlation_liquidity_and_stress.py`.
- **Unexplored areas**: none within R4, R5, R6 scope.

## Key Decisions Made
- Fully documented architecture, mathematical formulas, data structures, UI injection points, and test specifications in handoff.md.

## Artifact Index
- DISPATCH.md — incoming instructions
- BRIEFING.md — working memory and identity
- progress.md — task progress and heartbeat
- handoff.md — final comprehensive survey report
