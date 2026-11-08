# Task Assignment: Explorer 2 (Survey - Tab 2 Refactoring Scope)

## Objective
Read `d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md`.
Also check reference files:
- `c:\Users\deanc\Downloads\agy2_fundadvisory_ultra_minimalist_spec.md`
- `c:\Users\deanc\Downloads\agy2_app_gui (2).md` (if accessible)
Investigate `AGY2_FundAdvisory/app_gui.py` for Tab 2 (持仓调仓):
1. Removal of `render_workflow_step_indicator` and caption in Tab 2.
2. Tab 2 Module 1 (single-line full toolbar): compact arrangement of ledger selectbox, view mode switcher (main workflow vs ops archive), fast fund recording Popover (moving the entire 5-column bar into this popover, zero height normally), global sync valuation button, ledger & environment management Popover (integrating new ledger, clone, rename, delete, load demo portfolio, undo last edit - removing scattered buttons).
3. Tab 2 Module 2 (unified 4-cell asset & cushion top bar + holdings detail table): removing the two duplicated 4-cell grids (floating pnl cushion 4-cell vs holdings market value/cash/floating pnl/lock overview 4-cell), merging into a single clean 4-cell bar (① total market value & equity ratio, ② available cash & in-transit, ③ cumulative floating PnL & today's est change, ④ comprehensive cushion & HS300 break-even with click-to-expand -3%/-5%/-10% stress test); directly underneath with zero gap, display the editable real-time holdings table.
4. Tab 2 Module 3 (rebalancing verdict & execution order): beneath holdings table, keep only "诊断并生成调仓方案" button and buffer slider; collapse timing verdict & consequences into a compact 4-cell summary bar (timing verdict, fee friction, T+2 in-transit risk, vol & drawdown change), with rebalance execution table and sync button directly below; remove preachy text boxes.

Document exact functions, lines, components, state keys, and recommended implementation plan in `d:\Google\Workspace\Wind\.agents\teamwork\explorer_g11_survey_2\handoff.md`.

## 2026-11-08T12:01:21Z
[Message] sender=c6b4ebd0-c5f1-4175-8ba5-3bd0979b970d priority=MESSAGE_PRIORITY_HIGH
content=You are explorer_g11_survey_2.
Your working directory is `d:\Google\Workspace\Wind\.agents\teamwork\explorer_g11_survey_2\`.
Read your task description in `d:\Google\Workspace\Wind\.agents\teamwork\explorer_g11_survey_2\DISPATCH.md`.
Read the authoritative user request in `d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md`.
Also check reference files:
- `c:\Users\deanc\Downloads\agy2_fundadvisory_ultra_minimalist_spec.md`
- `c:\Users\deanc\Downloads\agy2_app_gui (2).md` (if accessible)
Investigate `AGY2_FundAdvisory/app_gui.py` for Tab 2 refactoring per requirements R1 & R2.
Write your complete, structured findings and concrete implementation plan to `d:\Google\Workspace\Wind\.agents\teamwork\explorer_g11_survey_2\handoff.md`.
Update `progress.md` in your directory periodically.
When finished, send a message to the orchestrator (conversation ID: c6b4ebd0-c5f1-4175-8ba5-3bd0979b970d) with a summary and path to your handoff.md.
