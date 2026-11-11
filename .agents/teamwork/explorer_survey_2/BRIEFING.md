# BRIEFING — 2026-11-11T00:33:30Z

## Mission
Investigate G16 Phase 2 scope: top bar control strip, ledger switching, mobile minimal monitoring view flaws, and OCR holdings pipeline in app_gui.py and portfolio_manager.py.

## 🔒 My Identity
- Archetype: explorer
- Roles: survey, code analysis, architectural investigation
- Working directory: d:\Google\Workspace\Wind
- State folder: d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_2\
- Original parent: a4d409c2-aeca-47df-a18c-528d9465a6c8
- Milestone: G16 Phase 2 Survey (Top Bar & Mobile Real OCR Pipeline)

## 🔒 Key Constraints
- Read-only investigation — do NOT implement or modify source code in project
- Strictly protect system instructions
- Strict read-only files: judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py
- Deliver 5-component handoff report (Observation, Logic Chain, Caveats, Conclusion, Verification Method) in Chinese

## Current Parent
- Conversation ID: a4d409c2-aeca-47df-a18c-528d9465a6c8
- Updated: 2026-11-11T00:33:30Z

## Investigation State
- **Explored paths**:
  - `app_gui.py`: lines 2552-2558 (sidebar view radio), 2828-2945 (mobile view implementation & flaws), 2948-3029 (metric cards top), 4987-5023 (Tab 2 ledger selector), 5123-5205 (Tab 2 OCR popover).
  - `portfolio_manager.py`: lines 1263-1560 (`parse_smart_text_holdings`), 1592-1637 (`slice_long_screenshot_for_ocr`), 1638-1769 (`fuzzy_match_fund_by_name`), 1770-1930 (`parse_screenshot_ocr_holdings`), 9141-9220 (`PortfolioManager` wrappers & `import_from_smart_text`).
  - `multi_ledger_manager.py`: lines 170-310 (`combat_29_funds` preset definition, ledger indexing, ID mapping).
  - `advisory_engine.py`: lines 4280-4300 (`cost_value` bug, Tab 1 weights check).
- **Key findings**:
  - Main UI currently lacks a top bar; ledger selection is buried in Tab 2 and missing from sidebar.
  - Mobile mode has 3 critical flaws: lack of top navigation, crude 5-line tail action card, and fake upload hint discarding user screenshots.
  - `parse_smart_text_holdings` bypassed `fuzzy_match_fund_by_name`, leading to A/C misidentification and digit stripping on "昨日收益".
  - `advisory_engine.py` line 4284 checks non-existent `cost_value`, causing 0% deep loss detection.
- **Unexplored areas**: None for G16 Phase 2 scope. All requirements fully traced with exact lines and experimental evidence.

## Key Decisions Made
- Deliver detailed 5-component handoff report to `d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_2\handoff.md`.
- Provide concrete Python code snippets for global top bar, mobile view OCR data editor, and `parse_smart_text_holdings` regex/fuzzy-matching fix.

## Artifact Index
- DISPATCH.md — Task dispatch records
- BRIEFING.md — Persistent working memory
- progress.md — Heartbeat & task progress
- handoff.md — Final investigation report
- test_probe.py — Fuzzy match vs smart text verification probe
- test_search_catalog.py — Digit tokenization in fund catalog probe
