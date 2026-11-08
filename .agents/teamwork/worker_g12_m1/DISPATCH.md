## 2026-11-08T15:22:22Z
You are teamwork_worker for Milestone 1 of G12 Generation.
Your Identity: teamwork_worker
Your Working Directory: d:\Google\Workspace\Wind\.agents\teamwork\worker_g12_m1\
Authoritative Request: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
Project Scope Document: d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_16\PROJECT.md
Survey & Architecture Report: d:\Google\Workspace\Wind\.agents\teamwork\explorer_g12_survey_1\handoff.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your exclusive write ownership:
- AGY2_FundAdvisory/app_gui.py
- AGY2_FundAdvisory/portfolio_manager.py
- AGY2_FundAdvisory/advisory_engine.py
- tests/test_g12_circuit_breakers_and_sentry.py (new test file)

Tasks to implement:
1. Bug 1: In `AGY2_FundAdvisory/app_gui.py` line ~2987, fix correlation gate check from `is_mutation_alarm`/`is_regime_shift_risk` to `is_triggered` or `is_liquidity_shift_triggered` (while also allowing the aliases). In `AGY2_FundAdvisory/portfolio_manager.py` line ~8628, ensure return dict includes alias keys `is_mutation_alarm: is_triggered`, `is_regime_shift_risk: is_liquidity_shift_triggered`.
2. Bug 2: In `AGY2_FundAdvisory/app_gui.py` line ~2725, pass `investor_risk_tier=str(st.session_state.get("active_tier_val", "C3")).upper()`, and inject holdings' realtime quotes into `_augmented_snapshot["fund_quotes"] = _f_quotes` so ActiveRiskSentry Dimension 8 (suitability) and Dimension 9 (intraday cushion transmission) are active on the home screen.
3. Bug 3: In `AGY2_FundAdvisory/portfolio_manager.py` lines ~2176-2240, implement `_apply_fund_valuation_calibration` (alias `_apply_qdii_valuation_correction`) supporting all index funds and ETF feeder funds (with 0.95 factor for feeder funds) against real-time benchmark ETF/index quotes, eliminating quarterly report lag. Ensure `calculate_intraday_pnl` and `test_calculate_intraday_pnl` compatibility.
4. Bug 4: In `AGY2_FundAdvisory/advisory_engine.py`, add `SmartExecutionDCAEngine.compute_portfolio_weighted_bias_and_erp(allocations, snapshot)`. In `AGY2_FundAdvisory/app_gui.py` line ~3889, call this method to compute portfolio-weighted MA20 bias & ERP across selected funds for `plan_smart_dca` and `get_historical_inflection_ruler`.
5. Create `tests/test_g12_circuit_breakers_and_sentry.py` with comprehensive unit tests for all 4 bug fixes.
6. Run tests via PowerShell:
   - `py -3 -m pytest tests/test_infra.py` (Must be 100% green, verify 0 modifications to referee files)
   - `py -3 -m pytest tests/test_g12_circuit_breakers_and_sentry.py`
   - `py -3 -m pytest tests/test_adv_final_closure.py`
   - `py -3 -m pytest tests/test_g10_correlation_liquidity_and_stress.py`
   - `py -3 -m pytest AGY2_FundAdvisory/tests/test_live_rebalance_upgrades.py`
7. Write your handoff report to `d:\Google\Workspace\Wind\.agents\teamwork\worker_g12_m1\handoff.md` and send a message back to the orchestrator.
Do NOT modify global GEMINI.md. Do NOT touch the 4 read-only referee files.


## 2026-11-08T15:33:47Z
**Context**: Milestone 1 Implementation (4 Circuit-Breaker Bugs)
**Content**: Checking in on your implementation progress. 10 minutes have elapsed since dispatch.
**Action**: Please provide a brief status update on your current step, and remember to update progress.md. If you need any clarification, let us know.
