# BRIEFING — 2026-11-08T15:18:00Z

## Mission
Survey and produce precise investigation report for the 4 Circuit-Breaker Bugs & Sentry parameter penetration in G12 generation.

## 🔒 My Identity
- Archetype: teamwork_explorer
- Roles: explorer, survey
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\explorer_g12_survey_1\
- Original parent: e873dbb9-9906-41d0-83a7-8e9eb7aaf59a
- Milestone: G12 Survey Phase

## 🔒 Key Constraints
- Read-only investigation — do NOT implement code in source files directly
- Propose precise before/after code snippets, line numbers, and impact analysis in handoff.md
- Strict adherence to four read-only referee files: judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py
- Protect c:\Users\deanc\.gemini\GEMINI.md from modification

## Current Parent
- Conversation ID: e873dbb9-9906-41d0-83a7-8e9eb7aaf59a
- Updated: 2026-11-08T15:15:52Z

## Investigation State
- **Explored paths**:
  - `AGY2_FundAdvisory/app_gui.py`: lines 1849-1900, 2715-2760, 2980-3020, 3142, 3886-3901, 6980-7010
  - `AGY2_FundAdvisory/portfolio_manager.py`: lines 1760-1800, 1920-2005, 2132-2380, 7643-7690, 8420-8660
  - `AGY2_FundAdvisory/advisory_engine.py`: lines 1038-1090, 1460-1510, 1940-2095, 2283-2350, 2663-2750
  - `tests/test_infra.py`, `tests/test_adv_final_closure.py`, `tests/test_g3_evolution_loop.py`, `tests/test_g10_correlation_liquidity_and_stress.py`, `AGY2_FundAdvisory/tests/test_live_rebalance_upgrades.py`, `AGY2_FundAdvisory/tests/test_realtime_and_upgrades.py`
  - Peer reports: `explorer_g12_survey_2/handoff.md`, `explorer_g12_survey_3/handoff.md`
- **Key findings**:
  - Bug 1: Dead key lookup in `app_gui.py` line 2987 (`is_mutation_alarm` / `is_regime_shift_risk`) vs actual return keys `is_triggered` / `is_liquidity_shift_triggered` from `portfolio_manager.py:8628`.
  - Bug 2: Missing `investor_risk_tier` and `fund_quotes` in `sentry.inspect_portfolio` at `app_gui.py` line 2725 causes Dimension 8 (suitability) and Dimension 9 (intraday cushion transmission) to be completely disabled.
  - Bug 3: `_apply_qdii_valuation_correction` only covers QDII and gold, leaving all domestic index and ETF feeder funds uncalibrated from live ETF/benchmark quotes. Feeder funds need `* 0.95` factor to eliminate quarterly lag.
  - Bug 4: Tab 1 `SmartExecutionDCAEngine.plan_smart_dca` at `app_gui.py` line 3889 uses only HS300 bias & macro ERP instead of portfolio-weighted MA20 bias & sector ERP.
- **Unexplored areas**: None. Investigation complete and cross-verified with tests and codebase.

## Key Decisions Made
- Confirmed exact lines and proposed backward-compatible implementations for all 4 bugs.
- Verified test suite baselines (core 40 tests passed, test_infra 14 tests passed).

## Artifact Index
- handoff.md — Complete 5-component survey report
- progress.md — Liveness heartbeat
- DISPATCH.md — Incoming task log
