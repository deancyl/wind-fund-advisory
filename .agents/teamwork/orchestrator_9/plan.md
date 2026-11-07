# G7 Generation Execution Plan: Tab 2 Decoupling & Risk Control Linkage

## Architecture & Code Layout
- Target Core Modules:
  - `AGY2_FundAdvisory/app_gui.py`: Tab 2 dual-view decoupling, risk watchdog card buttons, Tab 4 highlight linkage, HTML card deduplication
  - `AGY2_FundAdvisory/advisory_engine.py`: OnlineHeuristicFactorEvolver fitness function (turnover penalty, tail MDD constraint, 60-day historical comparison data), risk warning dispatch metadata
  - `AGY2_FundAdvisory/portfolio_optimizer.py`: genetic evolution population simulation & fitness penalties
  - `AGY2_FundAdvisory/strategy_bridge.py` & `portfolio_manager.py`: sunken logic and helper functions
- Read-Only Invariants:
  - `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py` (STRICTLY READ-ONLY)
  - `DataLoader.simulate_execution` default signature and fee logic (STRICTLY READ-ONLY)

## Milestones
| # | Milestone | Scope | Dependencies | Status |
|---|-----------|-------|-------------|--------|
| M1 | Survey & Technical Architecture Audit | Explore import paths, app_gui structure, OnlineHeuristicFactorEvolver, risk watchdog | none | IN_PROGRESS |
| M2 | Code Implementation & Refactoring | Tab 2 dual view, 3-way risk linkage, genetic evolver enhancements, app_gui purification | M1 | PENDING |
| M3 | Comprehensive Verification | Reviewers, Challengers, Forensic Integrity Auditor | M2 | PENDING |
| M4 | Browser Walkthrough & UI Inspection | Service restart, http://localhost:8501 inspection, mobile 640px check | M3 | PENDING |
| M5 | Test Suite Regression & Git Archive | Full pytest 50+ passing, GEMINI.md/PROGRESS_LOG.md update, Git tag v3.7-G7, G8 generation prompt | M4 | PENDING |
