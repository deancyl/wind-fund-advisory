# Task Assignment: Challenger 1 (Milestone 2 Tab 2 Adversarial Stress)

## Target
`AGY2_FundAdvisory/app_gui.py` (Tab 2)

## Inputs
- Authoritative Request: `d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md`
- Project Plan: `d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_15\PROJECT.md`
- Worker 2 Handoff: `d:\Google\Workspace\Wind\.agents\teamwork\worker_g11_m2\handoff.md`

## Objectives
Adversarially challenge Tab 2 Toolbar & Popovers:
1. Test ledger switching across multiple ledgers, creating new ledgers, deleting ledgers, renaming ledgers via the Popover.
2. Test fast fund recording inside Popover (`btn_bar_add_holding`):
   - Boundary fund codes, share counts (0, negative, fractional, huge numbers).
   - Verify that adding a fund updates the holdings table cleanly without crashing.
3. Test dual-view switching (`rad_tab2_view_mode`):
   - Verify that when in Main Mode (`is_t2_main_mode == True`), `dock_tab1..6` are never rendered.
   - Verify that when in Ops Archive Mode (`is_t2_main_mode == False`), `dock_tab1..6` render properly.
4. Run empirical test harness and report results.

Deliver verdict in `d:\Google\Workspace\Wind\.agents\teamwork\challenger_g11_m2_1\handoff.md`.


## 2026-11-08T13:57:56Z
You are challenger_g11_m2_1.
Your working directory is `d:\Google\Workspace\Wind\.agents\teamwork\challenger_g11_m2_1\`.
Read your task in `d:\Google\Workspace\Wind\.agents\teamwork\challenger_g11_m2_1\DISPATCH.md`.
Read `d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md`.
Read `d:\Google\Workspace\Wind\.agents\teamwork\worker_g11_m2\handoff.md`.
Adversarially challenge Tab 2 toolbar, ledger switching, fast fund recording Popover, and dual-view mode in `AGY2_FundAdvisory/app_gui.py`.
Deliver your report and empirical correctness verdict in `d:\Google\Workspace\Wind\.agents\teamwork\challenger_g11_m2_1\handoff.md`.
Notify the orchestrator (conversation ID: c6b4ebd0-c5f1-4175-8ba5-3bd0979b970d) when done.
