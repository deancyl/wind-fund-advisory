# DISPATCH — explorer_g14_survey_2

## Objective
Technical survey of Institutional Bespoke Royal Blue Aesthetic & UX Upgrades in `app_gui.py`:
1. Eliminate Tomato Red Primary Buttons:
   - Inspect global CSS in `app_gui.py`. Find all styles affecting `button[kind="primary"]`, `[data-testid="stBaseButton-primary"]`.
   - Design explicit CSS binding:
     `background: var(--accent-primary) !important; border: 1px solid var(--accent-primary) !important; color: #ffffff !important; border-radius: 8px !important; height: 40px !important; font-weight: 600 !important; box-shadow: 0 2px 6px rgba(29, 78, 216, 0.2) !important; transition: all 0.2s ease !important;`
     and hover state with slight lift/brightness transition. Completely eliminate Streamlit default `#ff4b4b`.
2. Fix Tab 1 top 5-col control bar vertical alignment:
   - Inspect Tab 1 control columns: `col_l1_cap`, `col_l1_tier`, `col_l1_rhythm`, `col_l1_adv`, `col_l1_btn`.
   - Identify why cols 4 & 5 are misaligned with cols 1-3.
   - Replace `st.caption("微调参数")` and `st.caption("开始执行")` with exact widget-matching HTML label:
     `<div style="font-size: 14px; font-weight: 500; color: var(--text-primary); margin-bottom: 4px; height: 21px; line-height: 21px;">高级参数</div>` and `<div style="font-size: 14px; font-weight: 500; color: var(--text-primary); margin-bottom: 4px; height: 21px; line-height: 21px;">生成方案</div>`.
   - Ensure horizontal baseline alignment across all 5 inputs/buttons.
3. Tab 1 Out-of-the-box instant rendering (no bottom half blank screen on first load):
   - Inspect Tab 1 rendering logic when `st.session_state` has no plan or on fresh startup.
   - Design silent, instant generation of default plan (100k capital, C3 balanced tier, mode 1) and 3-metric summary strip (<100ms, using cache, no blocking spinners).
   - Only trigger full re-computation when user modifies parameters and clicks "生成实盘建仓方案".
4. Top 4 Global Cards visual consistency:
   - Inspect `render_top_market_corridor` / top 4 cards in `app_gui.py`.
   - Remove emoji in front of card 2 title (e.g. `🟢 震荡收息期` -> `震荡收息期`), conveying state via text color and capsule dot.
   - Verify font size (18px bold), line-height, padding match across all 4 cards.
5. Review external audit notes:
   - `c:\Users\deanc\Downloads\agy2_v8_code_audit_and_aesthetic_review.md`
   - `c:\Users\deanc\Downloads\agy2_ui_ux_audit_and_fix_plan (2).md`
   Extract any relevant UI/UX findings that affect these 4 areas.

Read `ORIGINAL_REQUEST.md` at `d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md`.
Output detailed analysis and concrete CSS/UI modification plans in `handoff.md` in your directory.


## 2026-11-09T11:25:38Z
You are explorer_g14_survey_2, working in directory: d:\Google\Workspace\Wind\.agents\teamwork\explorer_g14_survey_2\
Read your task assignment in d:\Google\Workspace\Wind\.agents\teamwork\explorer_g14_survey_2\DISPATCH.md and d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md.

Investigate the institutional bespoke royal blue aesthetic & UX upgrades in app_gui.py:
1. Eliminate tomato red primary buttons: locate primary button styles, bind to var(--accent-primary) with hover states.
2. Fix Tab 1 top 5-col control bar vertical alignment: replace captions with exact 21px line-height HTML labels to align with inputs.
3. Tab 1 Out-of-the-box instant rendering: silent default 100k C3 plan generation without blocking spinners (<100ms).
4. Top 4 Global Cards visual consistency: remove emoji before card 2 title, unify font sizes and margins.
5. Review external audit notes: c:\Users\deanc\Downloads\agy2_v8_code_audit_and_aesthetic_review.md and c:\Users\deanc\Downloads\agy2_ui_ux_audit_and_fix_plan (2).md.

Document exact line numbers, CSS selectors, HTML snippets, and logic changes.
Write your complete report to handoff.md in your working directory and notify the orchestrator with send_message.
