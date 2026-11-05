# BRIEFING — 2026-11-05T02:12:00Z

## Mission
Complete Milestone 1: Upgrade sidebar index corridor with full market customization (38+ catalog, arbitrary 6-digit code validation, offline double-day return fallback), 3-row professional metric cards, persistent watchlist, and UI details fixes (CSS union classes, primary button white text, Tab 1 Step 1 text deduplication).

## 🔒 My Identity
- Archetype: worker_prod
- Roles: implementer, qa, specialist
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\worker_prod_r8_m1\
- Original parent: 3ef18151-e1aa-4330-83a1-353aa7bcc35e
- Milestone: Milestone 1 (Features 1-6)

## 🔒 Key Constraints
- Exclusive write ownership: `AGY2_FundAdvisory/app_gui.py`, `AGY2_FundAdvisory/data_loader.py`, `data/cache/custom_watchlist.json`, and `.agents/teamwork/worker_prod_r8_m1/*`.
- Physical safety redline: NEVER touch referee files (`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`).
- Rule 16 Invariant: CSI Dividend benchmark strictly mapped to 000922, NEVER 000015.
- Rule 14 & 15: Flexbox anti-squash (`flex: 0 0 auto !important; white-space: nowrap !important;`), no clipping.
- No dummy/facade implementations. Real data, real calculation, real persistence.

## Current Parent
- Conversation ID: 3ef18151-e1aa-4330-83a1-353aa7bcc35e
- Updated: 2026-11-05T02:12:00Z

## Task Summary
- **What to build**:
  - Feature 1: CSS union selectors `.val-very-low, .val-very_low` and `.val-very-high, .val-very_high`.
  - Feature 2: Offline 2-trading-day return calculation fallback when API closed/offline/0.00%.
  - Feature 3: 3-row sidebar card layout (Row 1: name, code, price, return capsule; Row 2: valuation percentile tag & 20d return; Row 3: MA20 trend & bias).
  - Feature 4: 40-item index/ETF catalog across 12 sectors + sidebar setting modal (count slider, multiselect search, 6-digit code real-time validation).
  - Feature 5: Watchlist persistence to `data/cache/custom_watchlist.json`.
  - Feature 6: Primary button white text & Tab 1 Step 1 text deduplication.
- **Success criteria**: All features genuinely implemented; `verify_referee_hashes.py` passes; `test_sidebar_remodel_and_bugfixes.py` passes.
- **Interface contracts**: `d:\Google\Workspace\Wind\.agents\teamwork\orchestrator\PROJECT.md`, `d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r8_1\analysis.md`.
- **Code layout**: `AGY2_FundAdvisory/app_gui.py`, `AGY2_FundAdvisory/data_loader.py`, `data/cache/custom_watchlist.json`.

## Key Decisions Made
- In `data_loader.py`, catalog `EXPANDED_INDEX_CATALOG` defines 40 targets covering 12 sectors, with CSI Dividend strictly locked to `000922`.
- When calculating MA20 on spot prices (like Gold ETF 8.44 vs AU9999 index 1440), proportionally scale the historical moving average to avoid cross-scale bias distortion.
- Handled cold-start for `custom_watchlist.json` by auto-generating default configuration with 6 core benchmark indices if missing.
- Tab 1 Step 1 deduplication retains the comprehensive strategy card (core assets, equity range, and max drawdown limit) while refining caption to clean target return & tier confirmation.

## Artifact Index
- `.agents/teamwork/worker_prod_r8_m1/DISPATCH.md` — Orchestrator assignment
- `.agents/teamwork/worker_prod_r8_m1/BRIEFING.md` — Persistent working memory
- `.agents/teamwork/worker_prod_r8_m1/progress.md` — Liveness heartbeat
- `.agents/teamwork/worker_prod_r8_m1/handoff.md` — Complete handoff report

## Change Tracker
- **Files modified**:
  - `AGY2_FundAdvisory/data_loader.py`: Added 40-item catalog across 12 sectors, `load_custom_watchlist`, `save_custom_watchlist`, `validate_and_fetch_code`, `calc_offline_2day_return`, `get_index_corridor_metrics`, `fetch_custom_realtime_indices`, and `fetch_batch_realtime_indices`.
  - `AGY2_FundAdvisory/app_gui.py`: Added union CSS classes, primary button white text, 3-row sidebar card layout with anti-squash, settings popover dialog, and Tab 1 Step 1 text deduplication.
  - `data/cache/custom_watchlist.json`: Auto-generated persistent watchlist cache.
- **Build status**: All tests pass. Referee hashes verified intact.
- **Pending issues**: None.

## Quality Status
- **Build/test result**: 6 passed in `test_sidebar_remodel_and_bugfixes.py`, 38 passed in regression suite.
- **Lint status**: Clean, no forbidden constants (`INDEX_PE_METAS`, `3210`, `1780`).
- **Tests added/modified**: Verified against `test_sidebar_remodel_and_bugfixes.py`, `test_m1_open_data_and_cache.py`, `test_challenger_m1_adversarial.py`, and `test_infra.py`.

## Loaded Skills
- None
