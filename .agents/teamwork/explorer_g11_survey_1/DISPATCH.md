# Task Assignment: Explorer 1 (Survey - Top Area & Tab 1 Refactoring Scope)

## Objective
Read `d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md`.
Also check reference files:
- `c:\Users\deanc\Downloads\agy2_fundadvisory_ultra_minimalist_spec.md`
- `c:\Users\deanc\Downloads\agy2_app_gui (2).md` (if accessible)
Investigate `AGY2_FundAdvisory/app_gui.py` for:
1. Top area: 4 compact global metric cards (height locked at 82px, removing cluttered icons/subtitles), removal of standalone "今日投顾行动总开关" banner and "跨区联动指令已生效承接" banner, merging today's one-line conclusion into the wing dashboard expander dynamic title, and compact jump button.
2. Tab 1 (新资建仓): Removal of `render_workflow_step_indicator`, captions, gray AI box, duplicate "一键生成全案" button.
3. Tab 1 Module 1 (single-line control bar): capital, risk C1-C5, rhythm (一次性/三步分批/智能定投), advanced popover, single primary "生成实盘建仓方案" button.
4. Tab 1 Module 2 (execution table top & 3 core metrics bar): removing step 2/3 headers, re-generate button, standalone PCR banner, `summary_advice` blue box; compact 3-column metric bar right above execution dataframe table.
5. Tab 1 Module 3 (action bar & single white-box drawer): Popovers for write-to-ledger, save-as-new-ledger, order cheat sheet, backtest; single bottom expander for stress testing and fund selection white-box evidence.
6. Global CSS: emoji reduction by >70%, `block-container` `padding-top` 1.2rem, card `margin-bottom` 6px.

Document exact functions, lines, components, and recommended implementation plan in `d:\Google\Workspace\Wind\.agents\teamwork\explorer_g11_survey_1\handoff.md`.

## 2026-11-08T12:01:16Z
You are explorer_g11_survey_1.
Your working directory is `d:\Google\Workspace\Wind\.agents\teamwork\explorer_g11_survey_1\`.
Read your task description in `d:\Google\Workspace\Wind\.agents\teamwork\explorer_g11_survey_1\DISPATCH.md`.
Read the authoritative user request in `d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md`.
Also check reference files:
- `c:\Users\deanc\Downloads\agy2_fundadvisory_ultra_minimalist_spec.md`
- `c:\Users\deanc\Downloads\agy2_app_gui (2).md` (if accessible)
Investigate `AGY2_FundAdvisory/app_gui.py` for Top Area and Tab 1 refactoring per requirements R1 & R2.
Write your complete, structured findings and concrete implementation plan to `d:\Google\Workspace\Wind\.agents\teamwork\explorer_g11_survey_1\handoff.md`.
Update `progress.md` in your directory periodically.
When finished, send a message to the orchestrator (conversation ID: c6b4ebd0-c5f1-4175-8ba5-3bd0979b970d) with a summary and path to your handoff.md.

