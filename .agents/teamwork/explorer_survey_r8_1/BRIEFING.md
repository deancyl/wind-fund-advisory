# BRIEFING — 2026-11-05T01:50:00Z

## Mission
Investigate Requirement R1: 升级侧边栏核心指数行情走廊与全市场自由定制 (styles, realtime quotes, 3-layer card rendering, 30+ indices, watchlist dialog, persistence)

## 🔒 My Identity
- Archetype: explorer
- Roles: investigation, survey, synthesis
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r8_1\
- Original parent: 3ef18151-e1aa-4330-83a1-353aa7bcc35e
- Milestone: Survey & Investigation (R1) Complete

## 🔒 Key Constraints
- Read-only investigation — do NOT implement
- 严禁修改裁判文件（judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py）
- 遵循 GEMINI.md 铁律（基准代码真实性、Flexbox物理防压扁、Tab错误隔离等）

## Current Parent
- Conversation ID: 3ef18151-e1aa-4330-83a1-353aa7bcc35e
- Updated: 2026-11-05T01:50:00Z

## Investigation State
- **Explored paths**:
  - `AGY2_FundAdvisory/app_gui.py`: lines 850-985 (CSS style rules), lines 1308-1400 (corridor and dialog), lines 1835-1855 (Tab 1 step 1 text).
  - `AGY2_FundAdvisory/data_loader.py`: lines 40-57 (paths & cache files), lines 215-350 (IndexValuationEngine, valuation label & status generation).
  - `AGY2_FundAdvisory/portfolio_manager.py`: lines 1700-1915 (single index fetch, batch realtime fetch, fallback config).
  - `AGY2_FundAdvisory/advisory_engine.py`: lines 20-176 (RADAR_SECTOR_CATALOG), lines 210-248 (ER, MA20, Bias20 dynamic calculations).
  - `data/processed/aligned_matrix_total_return.parquet`: verified columns and last 2 rows calculation.
  - `data/processed/indices/`: verified presence of 754 local index parquet files.
  - `tests/test_adversarial_m1_2_prod_screener_liquidation_gui.py`: lines 375-415 (CSS class and Rule 14 invariants tests).
  - `tests/test_ui_instant_load.py`: lines 53-70 (`test_fetch_batch_realtime_indices`).
  - `scripts/verify_referee_hashes.py`: 100% PASS.
- **Key findings**:
  1. Root cause of badge style failure: Python generates `.val-very_low` / `.val-very_high`, while CSS only defines `.val-very-low` / `.val-very-high`. Fixing with a union selector `.val-very-low, .val-very_low` and `.val-very-high, .val-very_high` perfectly solves the issue.
  2. Fake 0.00% flat panel root cause: Non-trading hours or offline fallback uses static 0.0. Fixed by dynamically reading the last 2 trading day rows from `data/processed/aligned_matrix_total_return.parquet` or local parquet files to calculate exact historical returns.
  3. 3-layer card structure defined: Row 1 (name/code/point/change capsule with anti-squash flex lock), Row 2 (PE/PB valuation badge + 20-day return), Row 3 (MA20 trend status + ma point).
  4. 38 standardized indices/ETFs catalog mapped with secid, symbol, and pinyin acronyms, strictly mapping CSIndex Dividend to `000922`.
  5. Popover dialog designed with 3~15 slider, 3-mode multiselect, 6-digit real-time validator, and JSON persistence to `data/cache/custom_watchlist.json`.
  6. UI detail fixes identified: `button[kind="primary"]` white text rule and Tab 1 Step 1 duplicate text removal.
- **Unexplored areas**: None for R1 scope.

## Key Decisions Made
- Completed full survey of R1 requirements and verified technical solutions via live python probe and scratch testing.
- Preserved backward compatibility for `fetch_batch_realtime_indices()` while introducing `fetch_custom_realtime_indices()` for custom watchlists.
- Maintained 100% integrity of referee files.

## Artifact Index
- DISPATCH.md — incoming dispatch instructions and timestamps
- BRIEFING.md — persistent working memory
- progress.md — liveness heartbeat
- analysis.md — detailed findings and architectural analysis
- handoff.md — 5-component handoff report for Worker agents
