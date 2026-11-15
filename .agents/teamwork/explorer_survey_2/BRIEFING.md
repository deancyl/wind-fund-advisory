# BRIEFING — 2026-11-15T07:54:00Z

## Mission
Phase 2 Technical Requirements Survey: Routing, Styles Consolidation, Mobile Column Selector, Rolling 3Y DCA Backtest, and Audit Items (Task 1 & 2 from agy2 (3).md).

## 🔒 My Identity
- Archetype: explorer
- Roles: survey, code analysis, architectural investigation
- Working directory: d:\Google\Workspace\Wind
- State folder: d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_2\
- Original parent: a4d409c2-aeca-47df-a18c-528d9465a6c8
- Milestone: G16 Phase 2 Survey (Top Bar & Mobile Real OCR Pipeline)
- Updated parent: 2b4a5c42-da01-49e9-b9b9-7a42b49250ea
- Updated milestone: G19 Phase 2 Survey (Routing, Styles, Rolling 3Y DCA, OCR Fusion)

## 🔒 Key Constraints
- Read-only investigation — do NOT implement or modify source code in project
- Strictly protect system instructions
- Strict read-only files: judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py
- Deliver 5-component handoff report (Observation, Logic Chain, Caveats, Conclusion, Verification Method) in Chinese
- Never modify source code files outside of own state folder
- Deliver G20 command tags strictly without colons (/goal, /boost, /teamwork, /browser)

## Current Parent
- Conversation ID: 2b4a5c42-da01-49e9-b9b9-7a42b49250ea
- Updated: 2026-11-15T07:54:00Z

## Investigation State
- **Explored paths**:
  - `app_gui.py`: lines 320-395 (`render_chief_advisor_memo_card` inline style block), lines 795-850 (global CSS root), lines 904-958 (horizontal block & metric container query), lines 1820-1925 (mobile button groups CSS & lack of `stColumn` / exclusion of number input), lines 2692-2720 (portfolio manager initialization `pm = ...`), lines 3240-3320 (top bar ledger select & delayed routing check), lines 3870-3925 (`pending_cross_tab_jump` DOM injection), lines 7380-7485 (Tab 3 time machine backtest & friction bill).
  - `strategy_bridge.py`: lines 5893-6007 (`calculate_mutual_fund_friction_bill` hardcoded cagr/mdd/recovery_days/dividend_yield), lines 7078-7258 (`run_historical_time_machine_backtest` daily fees, A-class redemption <180d, subscription fee).
  - `portfolio_manager.py`: lines 1350-1480 (`parse_smart_text_holdings` regex number stripping and fund name keyword list), lines 1844-2020 (`parse_screenshot_ocr_holdings` premature early return at line 1906, spatial block clustering branch).
  - `data/ledgers_index.json`: active ledger is `main_live` (6 holdings); `combat_29_funds` has 29 holdings.
- **Key findings**:
  1. First-time routing: Line 3253 is placed late, after 500+ lines of top bar/memo execution, lacks `tab2_trigger_diagnose` & `tab2_trigger_rebalance`, and checks `>= 8` instead of the mandated `>= 10` right after `pm` init (line 2715).
  2. Styles consolidation: `render_chief_advisor_memo_card` injects repetitive `<style>` blocks (lines 327-385) on every run; needs consolidation into global CSS (line 795+).
  3. Mobile button CSS: Lines 1905-1916 match `stHorizontalBlock:has(button)`, causing `stNumberInput`'s stepper buttons to trigger 50% grid width on numeric inputs, and misses `div[data-testid="stColumn"]`.
  4. Rolling 3-year DCA test table: Requires a dedicated Point-in-Time method `calculate_rolling_dca_3y_backtest` evaluating bimonthly/quarterly starts over 3 years for 180d and 365d horizons, deducting full subscription, management (0.75%/250), C-share service (0.40%/250), and FIFO tiered redemption fees.
  5. Audit Task 1: `calculate_mutual_fund_friction_bill` hardcodes `cagr_val=16.85, mdd_all=-16.76, mdd_1y=-6.24, recovery_days=394, dividend_yield=3.42` which must be computed dynamically from weights; `run_historical_time_machine_backtest` omits daily management/custody fee (0.75%/250) and class-aware redemption/subscription fee.
  6. Audit Task 2: `parse_screenshot_ocr_holdings` line 1906 drops spatial clustering when `len(clean_res) >= 1`, requiring dual-channel union fusion; `parse_smart_text_holdings` requires keyword expansion for index codes (A500, 2000, etc.) and lock-in periods (30天持有, 180天, etc.) to prevent number contamination.
- **Unexplored areas**: None for Phase 2 scope. All 4 topics thoroughly traced to exact lines and verified.

## Key Decisions Made
- Consolidate all findings into `d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_2\handoff.md` strictly following the 5-component handoff standard.
- Formulate concrete code replacement patches and pseudo-code implementations for the Worker agent.

## Artifact Index
- DISPATCH.md — Task dispatch records
- BRIEFING.md — Persistent working memory
- progress.md — Heartbeat & task progress
- probe_ledgers.py — Probe script for ledger holdings
- probe_state.py — Probe script for ledger state
- run_test.py — Non-destructive test runner script
- handoff.md — Complete investigation report
