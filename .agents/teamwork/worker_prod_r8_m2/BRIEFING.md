# BRIEFING — 2026-11-05T03:00:00Z

## Mission
Complete Milestone 2 - 估值动量单源同真与双翼看板升级 (Features 7-10). Ensure single source of truth for valuations and momentums, implement 14-sector thermometer & pulse brief, 6-dimensional risk sentry with full test compatibility, and interactive alert buttons.

## 🔒 My Identity
- Archetype: implementer
- Roles: implementer, qa, specialist
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\worker_prod_r8_m2\
- Original parent: 3ef18151-e1aa-4330-83a1-353aa7bcc35e
- Milestone: Milestone 2

## 🔒 Key Constraints
- Exclusive write ownership:
  - `AGY2_FundAdvisory/advisory_engine.py`
  - `AGY2_FundAdvisory/app_gui.py`
  - `d:\Google\Workspace\Wind\.agents\teamwork\worker_prod_r8_m2\*`
- NEVER touch or modify the 4 readonly referee files:
  `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`.
- No cheating, no fake mocks, maintain real logic.
- Follow GEMINI.md rules: CSI Dividend is 000922, FIFO holding penalty defense, Tab error boundary, transient port defense.

## Current Parent
- Conversation ID: 3ef18151-e1aa-4330-83a1-353aa7bcc35e
- Updated: 2026-11-05T03:00:00Z

## Task Summary
- **What to build**:
  - Feature 7: Single source of truth for valuation & momentum. Eliminate static fake fields in `RADAR_SECTOR_CATALOG`. Fix parquet matrix discovery (`data/processed/aligned_matrix_total_return.parquet` + index parquets). Calculate Kaufman ER, MA20 Bias, momentum slope, crowding score dynamically.
  - Feature 8: Left wing opportunity radar upgrade. Add morning pulse brief (<=80 words) and expandable 14-sector thermometer table.
  - Feature 9: Right wing 6-dimensional active risk sentry. Fully implement 6 alert dimensions (011612, 011613, 013841, overlap, concentration, mini funds, market defense/offense) with backward compatibility for all existing tests.
  - Feature 10: Interactive action buttons under risk alerts linking to Tab 2 actions with session state and toasts.
- **Success criteria**:
  - All 20 tests pass: `test_m3_advisory_modules.py`, `test_m3_full_integration_apptest.py`, `test_sidebar_remodel_and_bugfixes.py`.
  - `verify_referee_hashes.py` passes with 0 changes.
- **Interface contracts**: PROJECT.md § Interface Contracts
- **Code layout**: PROJECT.md § Code Layout

## Change Tracker
- **Files modified**:
  - `AGY2_FundAdvisory/advisory_engine.py`: Eliminated static constants in RADAR_SECTOR_CATALOG; added dynamic parquet matrix metrics calculation with fallback; unified valuation lookup via IndexValuationEngine; implemented 6-dimensional ActiveRiskSentry with action types.
  - `AGY2_FundAdvisory/app_gui.py`: Added morning market pulse brief (<=80 words); added expandable 14-sector thermometer table; upgraded risk sentry header; added interactive action buttons under risk alerts.
- **Build status**: PASS (20/20 pytest tests passed, referee hashes intact).
- **Pending issues**: None.

## Quality Status
- **Build/test result**: 20 passed, 0 failed in 18.18s.
- **Lint status**: Clean.
- **Tests added/modified**: Covered by existing and empirical test suite.

## Loaded Skills
- None specified for dump.

## Key Decisions Made
- `RADAR_SECTOR_CATALOG` retained only sector metadata (sector_id, name, benchmark_index, symbol, top_fund_code, top_fund_name, core_logic, category, default_fund, matrix_col, fallback_parquet).
- Dynamic metrics calculation automatically falls back to index parquet files (`000685`, `000933`, `000932`, `399986`) and global index parquet (`HSTECH`).
- CSI Dividend valuation percentile strictly equals 91.3% across both sidebar corridor and opportunity radar (diff < 1e-4).
- 6D ActiveRiskSentry strictly targets demo funds `011612` (Dim 1 <7d penalty lock), `011613` (Dim 2 countdown hold), `013841` (Dim 4 deep loss rebalance & Dim 3 switch A class).

## Artifact Index
- `.agents/teamwork/worker_prod_r8_m2/DISPATCH.md` — Dispatch requirements
- `.agents/teamwork/worker_prod_r8_m2/BRIEFING.md` — Situational awareness
- `.agents/teamwork/worker_prod_r8_m2/progress.md` — Progress tracker
- `.agents/teamwork/worker_prod_r8_m2/handoff.md` — Final handoff report
