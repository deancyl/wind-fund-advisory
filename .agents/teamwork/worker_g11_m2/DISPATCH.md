# Task Assignment: Worker 2 (Milestone 2 - Tab 2 Three-Block Refactoring)

## Target File Ownership
- Exclusively owns: `AGY2_FundAdvisory/app_gui.py` (Tab 2 section)

## Inputs
- Authoritative User Request: `d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md`
- Project Milestone Plan: `d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_15\PROJECT.md`
- Detailed Technical Blueprint: `d:\Google\Workspace\Wind\.agents\teamwork\explorer_g11_survey_2\handoff.md`

## Objectives
Implement Milestone 2 per R1 & R2:
1. Tab 2 Noise Elimination:
   - Completely delete `render_workflow_step_indicator` call and caption in Tab 2.
   - Delete `### 步骤一：持仓账本` (L4723), `### 步骤二：时机裁决` (L5327), `### 步骤三：方案执行` (L5449) headers.
2. Tab 2 Module 1 (Single-Line Full Toolbar):
   - Single row of 5 columns:
     1) Ledger selectbox (`sel_tab2_active_ledger` / `sel_tab2_ledger_picker_{active_lid}`).
     2) View mode switcher (`rad_tab2_view_mode`, options: "💼 持仓诊断与智能调仓 (主流程)" vs "🛠️ 账本运维与实盘复盘档案 (宽屏工具坞)").
     3) Fast fund recording Popover: place the entire 5-column fund add bar (`btn_bar_add_holding`) inside this popover.
     4) Global sync valuation button (`btn_tab2_sync` / `btn_sync_holdings_tab2`).
     5) Ledger & Environment management Popover: integrate New Ledger, Clone, Rename, Delete, Load Demo Portfolio, and Undo Last Edit inside this popover. Remove scattered buttons from the main screen.
3. Tab 2 Module 2 (Merged 4-Cell Top Bar + Real-time Holdings Table):
   - Eliminate the two duplicated 4-card sets (floating pnl cushion 4 cards vs holdings overview 4 cards).
   - Merge into a single row of 4 compact cards:
     ① 持仓总市值与仓位占比
     ② 可用现金池与在途资金
     ③ 累计浮盈与今日预估涨跌
     ④ 综合安全垫厚度与沪深300破净临界点（点击可展开查看 -3%/-5%/-10% 三级压力推演，保留 `render_portfolio_cushion_and_stress_card_html` 兼容性或紧凑渲染）。
   - Place the Monte Carlo 3D surface chart into a collapsible expander (not directly exposed above holdings).
   - Right below the top bar with zero gap, render the editable real-time holdings dataframe table (`st.data_editor` / `main_holdings_editor_tab2`) and quick actions (cash edit popover `btn_confirm_cash_pop_tb`, delete fund popover `btn_pop_del_confirm_tab2`).
4. Tab 2 Module 3 (Compact Rebalance Verdict & Execution Order):
   - Under holdings table, keep ONLY "诊断并生成调仓方案" button (`btn_tab2_diagnose`) and rebalance buffer slider (`tab2_rebal_buf_slider`, ensure comment hook `# tab2_rebal_buf_slider_bot` is present).
   - Clicking triggers diagnosis: condense timing verdict & consequences into a single row of 4 summary cells (时机裁决结论, 手续费损耗, T+2在途风险, 攻防与回撤变化).
   - Directly underneath, show the rebalance recommendation table (`df_orders_tbl`) and one-click follow button (`btn_confirm_follow_rebalance_tab2`).
   - Completely remove the 3 repetitive Net Utility Gate blue lecture boxes.
5. Invariant & Test Guard:
   - Ensure all widget keys and test hooks are preserved: `rad_tab2_view_mode`, `is_t2_main_mode`, `dock_tab1` through `dock_tab6`, `btn_bar_add_holding`, `tab2_rebal_buf_slider`, `# tab2_rebal_buf_slider_bot`, `btn_tab2_diagnose`, `btn_confirm_follow_rebalance_tab2`.
   - Restore baseline `portfolio_ledger.json` and `data/portfolio_watchdog.json` if modified by demo tests: run `git checkout -- portfolio_ledger.json data/portfolio_watchdog.json`.

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Verification
Run tests: `pytest tests/test_infra.py tests/test_g8_ux_and_realtime_fusion.py tests/test_gui_multi_ledger_stress.py tests/test_g3_evolution_loop.py tests/test_challenger_g9_m2_adversarial.py` to confirm syntax and regression safety.
Report all changes, diffs, and verification commands in `d:\Google\Workspace\Wind\.agents\teamwork\worker_g11_m2\handoff.md`.

## 2026-11-08T13:22:17Z
You are worker_g11_m2.
Your working directory is `d:\Google\Workspace\Wind\.agents\teamwork\worker_g11_m2\`.
Read your task in `d:\Google\Workspace\Wind\.agents\teamwork\worker_g11_m2\DISPATCH.md`.
Read `d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md`.
Read `d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_15\PROJECT.md`.
Read the technical blueprint in `d:\Google\Workspace\Wind\.agents\teamwork\explorer_g11_survey_2\handoff.md`.

You exclusively own: `AGY2_FundAdvisory/app_gui.py` (Tab 2 section).
Implement all requirements of Milestone 2:
- Remove Tab 2 workflow step indicators, caption, and step 1/2/3 headers.
- Build Module 1 (Single-Line Full Toolbar: Ledger selectbox, view mode switcher, fast fund recording Popover with all 5 columns, sync valuation button, ledger & environment management Popover).
- Build Module 2 (Merged 4-Cell Top Bar + Real-time Holdings Table: eliminate double 4-card duplication, merge into single row of 4 compact cards, fold 3D chart into expander, display holdings table and quick actions directly underneath).
- Build Module 3 (Compact Rebalance Verdict & Execution Order: single diagnose button + buffer slider + single 4-cell summary bar + rebalance order table & follow button directly below; eliminate the 3 repetitive Net Utility Gate blue boxes).
- Ensure all test keys and hooks are preserved (`rad_tab2_view_mode`, `is_t2_main_mode`, `dock_tab1~6`, `btn_bar_add_holding`, `tab2_rebal_buf_slider`, `# tab2_rebal_buf_slider_bot`, `btn_tab2_diagnose`, `btn_confirm_follow_rebalance_tab2`).
- Restore baseline ledger if modified: `git checkout -- portfolio_ledger.json data/portfolio_watchdog.json`.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Run affected verification tests and verify code syntax. Document your changes and verification results in `d:\Google\Workspace\Wind\.agents\teamwork\worker_g11_m2\handoff.md`.
Update `progress.md` periodically.
When finished, send a message to the orchestrator (conversation ID: c6b4ebd0-c5f1-4175-8ba5-3bd0979b970d).
