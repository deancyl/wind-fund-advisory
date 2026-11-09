# BRIEFING — 2026-11-10T03:17:00Z

## Mission
实装手机长截图高清切片识别导入、碎片尾仓免赎清理器与 29 基真实存量账本 (G15 Milestone 3 / Phase 3)

## 🔒 My Identity
- Archetype: worker
- Roles: [implementer, qa, specialist]
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\worker_m3
- Original parent: 9a123e21-7525-4c57-9715-710c2a94c199
- Milestone: G15 Milestone 3

## 🔒 Key Constraints
- Physical safety redline: NEVER touch judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py
- NEVER modify DataLoader.simulate_execution default signature and default fee logic
- Genuine implementation: NO hardcoded test results, real state and math, exact penny-level accounting for 29 combat funds
- Tab 2 error boundaries and clean HTML rendering invariants must be upheld

## Current Parent
- Conversation ID: 9a123e21-7525-4c57-9715-710c2a94c199
- Updated: 2026-11-10T03:17:00Z

## Task Summary
- **What to build**:
  1. `slice_long_screenshot_for_ocr`, `fuzzy_match_fund_by_name`, `parse_screenshot_ocr_holdings` in `portfolio_manager.py`
  2. ActiveRiskSentry Dimension 13 "碎片尾仓清理" in `advisory_engine.py`
  3. Tab 2 popover "📸 截图导入" with st.data_editor and 1-click write to ledger in `app_gui.py`
  4. "🧹 碎片尾仓一键瘦身建议卡" in Tab 2 with 1-click sweep simulation
  5. `combat_29_funds` preset ledger in `multi_ledger_manager.py` (exact 29 funds, market value 26,615.10, holding days >=365d, deep loss surgery & pre/post rebalance)
  6. Comprehensive test suite `tests/test_g15_phase3_ocr_and_combat29.py` and pass all regressions
- **Success criteria**:
  - All slice ocr, fuzzy match, tail cleaner, and 29-fund ledger functionality complete and verified
  - All tests passing: test_infra.py, test_adv_final_closure.py, test_delta_m1_guardrails.py, test_g15_phase2_memo_and_timemachine.py, test_g15_phase3_ocr_and_combat29.py
- **Interface contracts**: `d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_18\PROJECT.md`
- **Survey Blueprint**: `d:\Google\Workspace\Wind\.agents\teamwork\explorer_g15_survey_3\handoff.md`

## Key Decisions Made
- [Initial plan formulated based on explorer_g15_survey_3 survey findings]
- Preserved negative float sign in `parse_smart_text_holdings` and removed `<100` drop constraint
- Preloaded `data/master/fund_catalog.parquet` (28,177 funds) into `_GLOBAL_CATALOG_DATA` for fast fuzzy matching
- Tail fragment criterion refined in `ActiveRiskSentry` (Dimension 13) and `PortfolioManager.sweep_tail_and_c_class` to protect waist active fund `005827` (124.14元) while sweeping all 19 tail funds (¥442.70)
- Initialized `combat_29_funds` ledger in `_ensure_index_initialized` with exact penny-level market value = ¥26,615.10 and all batches holding_days >= 365d
- Tab 2 toolbar integrated with `📸 截图导入` popover, interactive editable `st.data_editor`, overwrite/append buttons, `🧹 碎片尾仓一键瘦身建议卡`, and 3-stage surgery card for `combat_29_funds`

## Artifact Index
- `BRIEFING.md` — persistent memory index
- `DISPATCH.md` — dispatch log
- `progress.md` — liveness heartbeat and subtask tracking
- `handoff.md` — 5-component handoff report
- `tests/test_g15_phase3_ocr_and_combat29.py` — unit and integration test suite

## Change Tracker
- **Files modified**:
  - `AGY2_FundAdvisory/portfolio_manager.py`: Long screenshot slicing, fuzzy matching, OCR holdings parsing, accounting identity bugfixes, `sweep_tail_and_c_class` waist asset protection.
  - `AGY2_FundAdvisory/advisory_engine.py`: Dimension 13 碎片尾仓清理 in `ActiveRiskSentry`.
  - `AGY2_FundAdvisory/multi_ledger_manager.py`: Preset `combat_29_funds` ledger registration and initialization.
  - `AGY2_FundAdvisory/app_gui.py`: Tab 2 toolbar `📸 截图导入` popover, `🧹 碎片尾仓一键瘦身建议卡`, and `combat_29_funds` 3-stage surgery card.
  - `tests/test_g15_phase3_ocr_and_combat29.py`: New comprehensive test suite (5/5 PASSED).
- **Build status**: PASS (all 5 test suites 100% green).
- **Pending issues**: none.

## Quality Status
- **Build/test result**: PASS
  - `tests/test_infra.py`: 14/14 PASSED
  - `tests/test_adv_final_closure.py`: 14/14 PASSED
  - `tests/test_delta_m1_guardrails.py`: 5/5 PASSED
  - `tests/test_g15_phase2_memo_and_timemachine.py`: 8/8 PASSED
  - `tests/test_g15_phase3_ocr_and_combat29.py`: 5/5 PASSED
- **Lint status**: clean, all syntax compiles without errors.
- **Tests added/modified**: `tests/test_g15_phase3_ocr_and_combat29.py` added covering slicing, fuzzy matching, sentry dimension 13, exact 29-fund ledger accounting, and accounting identities.

## Loaded Skills
- None required directly.
