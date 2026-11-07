# BRIEFING — 2026-11-07T14:42:00Z

## Mission
Implement G7 generation tasks: OnlineHeuristicFactorEvolver fitness enhancement, Opportunity Radar whitebox badge & micro-charts, Three-Way Risk Linkage (Watchdog -> Tab 2 -> Tab 4), Tab 2 dual-view decoupling, code architecture purification, and verify with tests.

## 🔒 My Identity
- Archetype: implementer
- Roles: implementer, qa, specialist
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\worker_g7_1
- Original parent: edefabf5-5abf-4405-bb80-202032d71b10
- Milestone: G7 Generation Lead Implementation

## 🔒 Key Constraints
- Absolutely DO NOT modify: judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py
- Absolutely DO NOT modify: DataLoader.simulate_execution default signature or fee logic in data_loader.py
- Exclusively owned files: AGY2_FundAdvisory/advisory_engine.py, AGY2_FundAdvisory/app_gui.py, AGY2_FundAdvisory/strategy_bridge.py, AGY2_FundAdvisory/portfolio_optimizer.py, tests/test_g3_evolution_loop.py (or dedicated tests/test_g7_interactions.py)
- CRITICAL TEST INVARIANTS: Keep `'<b>{len(pm.holdings)} 只</b>'` in dock_tab3, and `'if "edited_table" in locals() and edited_table is not None:'` in timing/rebalance buttons.
- Integrity: no hardcoded test results or facade implementations. Genuine NumPy vectorized calculations.

## Current Parent
- Conversation ID: edefabf5-5abf-4405-bb80-202032d71b10
- Updated: 2026-11-07T14:42:00Z

## Task Summary
- **What to build**:
  1. OnlineHeuristicFactorEvolver: Population N=32, 4D weights (valuation, momentum, SNR, anti-crowding), 60 trading days sector returns, turnover penalty (-0.8*turnover) and tail MDD (-1.5*tail_mdd), vectorized < 50ms, rolling 60-day comparison & trajectory data.
  2. Opportunity Radar Whitebox Badge & Comparison Micro-Charts in app_gui.py: dynamic vs static weights badge, expander with 60-day rolling cumulative NAV comparison curve & 4D weight evolution trajectory Plotly charts.
  3. Three-Way Risk Linkage (Watchdog -> Tab 2 -> Tab 4): clean title, 380px container height, Button A (btn_sentry_act_*) to Tab 2, Button B (btn_sentry_tab4_*) to Tab 4, Tab 4 highlight banner with reverse link to Tab 2.
  4. Tab 2 Dual-View Decoupling: Mode 1 (持仓诊断与智能调仓) and Mode 2 (账本运维与实盘复盘档案) switcher, jump buttons, preserving exact string test invariants.
  5. Code Architecture Purification: Extract helper functions to strategy_bridge.py, explicit imports.
  6. Verification: New tests covering G7 features, pass full test suite.
- **Success criteria**: All tests pass, 0 regressions, clean architecture, responsive UI, zero read-only violations.
- **Interface contracts**: PROJECT.md, GEMINI.md, explorer handoffs.

## Change Tracker
- **Files modified**: None yet
- **Build status**: TBD
- **Pending issues**: None

## Quality Status
- **Build/test result**: Not yet run
- **Lint status**: Clean
- **Tests added/modified**: TBD

## Loaded Skills
- None
