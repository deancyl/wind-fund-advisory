# BRIEFING — 2026-11-08T15:05:00Z

## Mission
Investigate OnlineHeuristicFactorEvolver 7D GP upgrade, real-time cross-section injection, popover visualization in app_gui.py, and deep code diagnosis based on audit documents.

## 🔒 My Identity
- Archetype: teamwork_explorer
- Roles: explorer, analyst, investigator
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\explorer_g12_survey_3\
- Original parent: e873dbb9-9906-41d0-83a7-8e9eb7aaf59a
- Milestone: G12 Survey & Deep Diagnosis

## 🔒 Key Constraints
- Read-only investigation — do NOT implement production code
- Write all findings to handoff.md in working directory
- Communicate via send_message to orchestrator upon completion
- Adhere to GEMINI.md workspace rules (no pseudo-constants, safe execution, look-through, etc.)

## Current Parent
- Conversation ID: e873dbb9-9906-41d0-83a7-8e9eb7aaf59a
- Updated: not yet

## Investigation State
- **Explored paths**:
  - `AGY2_FundAdvisory/advisory_engine.py` (OnlineHeuristicFactorEvolver lines 247-765, OpportunityRadarEngine lines 768-1320, ActiveRiskSentry lines 1460-2070)
  - `AGY2_FundAdvisory/app_gui.py` (Popover factor evolution display line 2800, circuit bugs lines 2725 and 2987)
  - `AGY2_FundAdvisory/portfolio_manager.py` (evaluate_dynamic_correlation_mutation lines 8420-8645)
  - Audit documents: `c:\Users\deanc\Downloads\agy2 (1).md` and `c:\Users\deanc\Downloads\agy2_fundadvisory_deep_code_diagnosis.md`
  - Automated tests: `tests/test_infra.py`, `tests/test_adv_final_closure.py`, `tests/test_g3_evolution_loop.py`, `tests/test_gui_multi_ledger_stress.py`, `tests/test_causality_adversarial_m1.py`, `tests/test_g9_causal_brinson_and_suitability.py`, `tests/test_g7_architecture_and_decoupling.py`, `tests/test_g10_correlation_liquidity_and_stress.py`
- **Key findings**:
  - 7D GP upgrade: 4 base weights + 3 event operator genes (Adaptive momentum, Volatility pulse penalty, Sudden drop flight-to-safety).
  - Real-time cross-section injection: Appending today's realtime quotes at sequence tail in `_extract_sector_price_matrix` & `_build_factor_tensor_and_returns` allows GP evolver to immediately sense intraday shocks while strictly maintaining lag-1 causal invariant.
  - Backward compatibility: `_evaluate_population` must support both 4D (for existing tests like `test_causality_adversarial_m1.py`) and 7D populations. Return dictionary must maintain 4D `weights` and add 7D metadata (`chromosome_7d`, `operator_genes`, `market_emergency_mode`, `evolved_rule_expression`) to preserve `test_g7_architecture_and_decoupling.py` assertions.
  - Circuit bugs located: Line 2987 in `app_gui.py` checks non-existent keys `is_mutation_alarm` / `is_regime_shift_risk` instead of `is_triggered` / `is_liquidity_shift_triggered`. Line 2725 omits `investor_risk_tier` and `fund_quotes`, causing Dimensions 8 & 9 to be completely skipped.
  - All existing test suites pass 100% green.
- **Unexplored areas**: None for survey phase.

## Key Decisions Made
- Keep `res["weights"]` as 4D to satisfy `assert len(weights) == 4` in `test_g7_architecture_and_decoupling.py`, while exposing full 7D chromosome via `res["chromosome_7d"]` and `res["operator_genes"]`.
- Ensure `_evaluate_population` dynamically detects `pop.shape[1] == 4` vs `7` so existing adversarial tests continue passing seamlessly.
- Implement pure NumPy vectorization for all 3 heuristic event operators to guarantee execution latency well under 250ms.

## Artifact Index
- handoff.md — Comprehensive findings, logic chain, and implementation proposals
- progress.md — Liveness heartbeat and investigation progress
- DISPATCH.md — Incoming task dispatch records
