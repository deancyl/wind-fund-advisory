# Project: G7 Generation Architecture & Interaction Evolution

## Architecture
- Presentation Layer:
  - `AGY2_FundAdvisory/app_gui.py`: Tab 2 dual-view decoupling, right-wing risk watchdog dual action buttons, Tab 4 diagnostic promotion and highlight banner, Opportunity Radar genetic whitebox badge & 60-day expandable comparison view, tab switching dual-track navigator.
- Brain / Advisory Layer:
  - `AGY2_FundAdvisory/advisory_engine.py`: Implement `OnlineHeuristicFactorEvolver` with turnover penalty & tail MDD constraints, replace static weights in `OpportunityRadarEngine.evaluate_sector`, provide 60-day backtest data generator for comparison charts.
  - `AGY2_FundAdvisory/portfolio_optimizer.py`: Genetic algorithm vectorization support if needed.
  - `AGY2_FundAdvisory/strategy_bridge.py`: Sunken helpers for same-company conversion and macro adaptive dividend evaluation.
- Read-Only Hard Invariants (SHA256 locked):
  - `judge_engine.py`: `76f930371176de7ee6a413174b030101e3210ac6e037f5d10fe229af31cc07be`
  - `holdout_vault.py`: `88122eaf647040a410e2fd95da81077db10149a498a47340ff40b670bd031d2a`
  - `AGENT_SPEC.md`: `a346586f9bd2dc0ee83e665bd18e7a6471464c9f7b658e392b989b800cd63957`
  - `tests/test_infra.py`: `48bee0da300d7c0a0848ec1376e4b9b2e55224d2736081713b4340f0362cd100`
  - `DataLoader.simulate_execution` default signature and fee logic untouched.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Tab 2 Dual-View Decoupling | Segmented switcher for Mode 1 (Diagnosis & Rebalancing) vs Mode 2 (Ledger Ops & Review Archive), reducing Mode 1 vertical scroll by >30% | M2 | Survey 1 |
| 2 | Right-Wing Watchdog Dual Buttons | Each alert card gets Button A (Go to Tab 2 to rebalance) and Button B (Go to Tab 4 for evidence) | M2 | Survey 2 |
| 3 | Tab 4 Diagnostic Promotion & Linkage | Promote dynamic correlation and heavyweight overlap to top core zone, render evidence banner with back-to-Tab 2 button | M2 | Survey 2 |
| 4 | OnlineHeuristicFactorEvolver & Fitness | Dynamic factor weights with turnover penalty and tail MDD constraints in pure NumPy (<50ms) | M2 | Survey 3 |
| 5 | Genetic Whitebox Badge & Micro-Charts | Opportunity Radar whitebox badge with expandable 60-day NAV comparison and 4D trajectory charts | M2 | Survey 3 |
| 6 | Codebase Import & Dedup Purification | Ensure 100% explicit imports to AGY2_FundAdvisory, sink HTML/calculation helpers to strategy_bridge | M2 | Survey 1,3 |
| 7 | Dedicated G7 Automated Tests | Unit and AppTest tests for Tab 2 views, 3-way risk linkage, and evolver fitness | M2/M3 | Survey 3 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Survey & Technical Architecture Audit | Map out exact lines, test assertions, SHA256 invariants, and math formulas | none | DONE |
| M2 | Implementation & Refactoring | Worker implements all 6 features + dedicated tests | M1 | IN_PROGRESS |
| M3 | Comprehensive Multi-Agent Verification | Reviewers, Challengers, and Forensic Auditor verify correctness and integrity | M2 | PENDING |
| M4 | Browser Walkthrough & Visual Validation | Terminate 8501, restart clean service, verify UI via /browser on desktop & 640px mobile | M3 | PENDING |
| M5 | Test Regression, Git Archive & G8 Generation | 100% pass on 50+ pytest tests, update GEMINI.md/PROGRESS_LOG.md, Git tag v3.7-G7, output G8 prompt | M4 | PENDING |

## Interface Contracts & Test Invariants
- `tab2_view_mode`: "持仓诊断与智能调仓" (default) / "账本运维与实盘复盘档案"
- `active_main_tab_idx`: 0 (Tab 1), 1 (Tab 2), 2 (Tab 3), 3 (Tab 4)
- `tab4_highlight_module`: "correlation_mutation", "stock_overlap", "industry_sector_gap", "holding_days_fifo", "ac_fee_calc", "fund_deep_penetration"
- Static AST / String checks to preserve:
  - `<b>{len(pm.holdings)} 只</b>` in app_gui.py
  - `if "edited_table" in locals() and edited_table is not None:` in app_gui.py
  - `btn_sentry_act_` prefix on Button A
  - `FundHolding, HoldingItem`, `calculate_portfolio_yield_cushion`, `evaluate_rebalance_audit`, `resolve_fund_display_name`, `strategy_fn_for_tier`, `sel_tab2_vwap_schedule_item`, `render_historical_inflection_ruler_html`, `render_portfolio_cushion_and_stress_card_html`
