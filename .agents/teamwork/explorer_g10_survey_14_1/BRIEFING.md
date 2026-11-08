# BRIEFING — 2026-11-08T09:20:00Z

## Mission
Survey `AGY2_FundAdvisory/app_gui.py` and analyze the required UI surgeries for G10: Top 3 sector cards, right-wing sentry container, sidebar vs top 4 metric cards, top 4 metric cards compression, Tab hoisting & dual-wing compact folding, and Tab 1/2 card styling.

## 🔒 My Identity
- Archetype: teamwork_explorer
- Roles: explorer, UI survey, architectural analysis
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\explorer_g10_survey_14_1
- Original parent: 496bfcfb-72ea-446e-b3dc-c85871c12398
- Milestone: G10 Survey & UI Surgery Analysis

## 🔒 Key Constraints
- Read-only investigation — do NOT implement or modify source code / tests.
- Only write to `d:\Google\Workspace\Wind\.agents\teamwork\explorer_g10_survey_14_1\`.
- Rule 1 & 2 system prompt protection.
- Adhere to GEMINI.md invariants (e.g. Rule 14, 15, 27, 28, etc.).

## Current Parent
- Conversation ID: 496bfcfb-72ea-446e-b3dc-c85871c12398
- Updated: not yet

## Investigation State
- **Explored paths**:
  - `AGY2_FundAdvisory/app_gui.py`: Top 3 cards (lines 2941-2984), right sentry (lines 3035-3206), sidebar (lines 2289-2403), top 4 cards (lines 640-670, 2592-2686), layout & tabs (lines 2750-3300).
  - `AGY2_FundAdvisory/advisory_engine.py`: evidence chain synthesis & contradiction (lines 1160-1175).
  - `AGY2_FundAdvisory/data_loader.py`: news filtering whitelist/blacklist (lines 338-360).
  - `AGY2_FundAdvisory/portfolio_manager.py`: CVaR bootstrap instance & volatility scaling (line 1403).
  - Test suites: `test_infra.py`, `test_adv_final_closure.py`, `test_g8_ux_and_realtime_fusion.py`, `test_g3_evolution_loop.py`, `test_g10_correlation_liquidity_and_stress.py`, `test_ui_instant_load.py`.
- **Key findings**:
  1. Top 3 cards wrap because title lacks `white-space: nowrap !important; flex-shrink: 0;` and right cluster has realtime quote + points + tag in a ~240px card column. Solution: 3-row layout, moving realtime quotes to Row 2, concise rationale (<=18 chars) to Row 3.
  2. Right-wing sentry calls `render_stress_liquidity_card_html` (-36.1% CVaR), which should be removed (and invoked in Tab 3). Green correlation card should be suppressed when <= 0.75. Action switch streamlined to compact <= 44px bar.
  3. Sidebar "市场状态与底座" is 100% duplicate of Top 4 cards, wasting 220px. Compress to 1-line status bar (retaining `"行情源状态"` for tests), freeing sidebar space for index corridor. Fix popover column ratio to `[6.0, 4.0]`.
  4. Top 4 cards compressed to 88px (padding 6px 10px, 3 clean rows). Update `test_ui_instant_load.py` line 97.
  5. Dual-wing dashboard default collapsed (`expanded=False`), hoisting `st.tabs` to y ≈ 180px, making tabs and primary controls 100% visible on 1080p without scrolling.
- **Unexplored areas**: None. All 6 surgery areas and test impacts thoroughly investigated and planned.

## Key Decisions Made
- Formulate complete before/after DOM and CSS designs in `analysis.md` and `handoff.md`.
- Explicitly trace test assertions to prevent any regressions in existing test suites.

## Artifact Index
- `d:\Google\Workspace\Wind\.agents\teamwork\explorer_g10_survey_14_1\DISPATCH.md` — Incoming dispatch log
- `d:\Google\Workspace\Wind\.agents\teamwork\explorer_g10_survey_14_1\progress.md` — Liveness heartbeat
- `d:\Google\Workspace\Wind\.agents\teamwork\explorer_g10_survey_14_1\analysis.md` — In-depth architectural analysis
- `d:\Google\Workspace\Wind\.agents\teamwork\explorer_g10_survey_14_1\handoff.md` — Structured 5-component handoff report
