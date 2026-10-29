## 2026-10-29T09:16:40Z
You are E2E Test Writer (test_writer_e2e).
Your working directory is: d:\Google\Workspace\Wind\.agents\teamwork\test_writer_e2e
Your parent conversation ID is: 5fd996d1-bc98-447a-9f35-c5aef5be2e1c (Project Orchestrator).

MANDATORY FIRST STEP:
Read the following authoritative documents before starting work:
1. d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
2. d:\Google\Workspace\Wind\PROJECT.md
3. d:\Google\Workspace\Wind\TEST_INFRA.md
4. d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_1\handoff.md
5. d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_2\handoff.md
6. d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_3\handoff.md

OBJECTIVE:
Author comprehensive opaque-box E2E and integration tests for requirements R1, R2, R3, R4 in `d:\Google\Workspace\Wind\AGY2_FundAdvisory\tests\test_toolkit_integration.py`.
Design tests across 4 tiers per TEST_INFRA.md:
1. Tier 1 - Feature Coverage:
   - R1: Look-Through Risk Screen (`screen_fund_look_through_risk`, `calculate_portfolio_penetration_risk`) for goodwill >30%, double-high fraud, pledge ratio/liquidation warning, 30-90D lockup expiration, 3-color tags (🟢/🟡/🔴).
   - R2: Macro Liquidity Thermometer (`get_liquidity_thermometer`, DR007 vs 7D OMO spread bp, loose/neutral/tight state, 7D net injection, dual-track macro radar, defense trigger).
   - R3: Smart Money & Crowding (`get_fund_smart_money_crowding`, Northbound 1D/5D net flow, shareholder concentration trend, dragon/tiger institutional seats, fund crowding degree).
   - R4: WindToolkit initialization, DuckDB lakehouse integration, queries on views (`v_financial_risk_screen`, `v_open_market_operations`, etc.).
2. Tier 2 - Boundary & Corner Cases:
   - Zero goodwill, negative FCF, zero debt, extreme positive/negative DR007 spread, non-A-share asset immunity (pure bonds like 002351, gold 000216, QDII 050025 must have 0 fraud penalty), unknown fund code fallback.
3. Tier 3 - Cross-Feature Combinations:
   - Macro liquidity + ERP dual-track radar logic matrix.
   - Portfolio penetration risk index aggregation across multiple equity and non-equity assets.
   - Smart money crowding alert integrated into fund recommendation / rebalance flow.
4. Tier 4 - Real-World Application Scenarios:
   - Full portfolio look-through risk scan end-to-end.
   - Offline lakehouse disconnect fallback (mock network error, verify 100% graceful degradation to DuckDB/parquet/fallback generators with zero unhandled exceptions).
   - End-to-end simulation of market snapshot + liquidity thermometer + portfolio risk report.

READ-ONLY DEFENSE:
- Verify that read-only files (`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`) have `IsReadOnly: True` in a test case!
- DO NOT touch or modify any existing tests or read-only files.

PUBLISH TEST_READY.md:
When `test_toolkit_integration.py` is authored and validated, write `d:\Google\Workspace\Wind\TEST_READY.md` containing the test command, test counts per tier, and feature checklist.

Write your handoff report to `d:\Google\Workspace\Wind\.agents\teamwork\test_writer_e2e\handoff.md` and send a message to parent.
