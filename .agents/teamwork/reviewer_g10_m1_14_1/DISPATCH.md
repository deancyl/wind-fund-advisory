## 2026-11-08T09:46:44Z

[Message] timestamp=2026-11-08T09:46:44Z sender=496bfcfb-72ea-446e-b3dc-c85871c12398 priority=MESSAGE_PRIORITY_HIGH content=You are Reviewer 1 (`reviewer_g10_m1_14_1`) in the G10 visual subtraction, filter & UI elevation mission.

## Identity & Workspace
- Type: teamwork_reviewer
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\reviewer_g10_m1_14_1\
- Authoritative user request file: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
- Worker handoff report: d:\Google\Workspace\Wind\.agents\teamwork\worker_g10_m1_14\handoff.md

## Objective
Independently review the UI layout, styling, and visual subtraction changes implemented in `AGY2_FundAdvisory/app_gui.py`:
1. Top 3 Sector cards:
   - Verify 3-row architecture.
   - Verify `white-space: nowrap !important; flex-shrink: 0 !important;` on sector name and status tag.
   - Verify no realtime change or points in Row 1.
   - Verify Row 2 is single-line core metrics (`得分 ... ｜ 今日 ... ｜ 估值分位 ...%`).
   - Verify Row 3 has selected fund + concise rationale (<= 18 Chinese characters).
   - Verify hover `title` contains four-factor subscores and 20d risk metrics.
   - Verify bulky gray box and redundant gray text lines are completely removed.
2. Right-wing sentry container:
   - Verify `-36.1%` CVaR card is removed from right wing and relocated to Tab 3.
   - Verify bulky green card is suppressed when correlation <= 0.75, showing a clean single-line status bar.
   - Verify pending risk alerts are capped at max 2.
   - Verify action bar is <=44px with inline button, and button key prefixes `btn_sentry_act_` and `btn_sentry_evid_` are preserved.
3. Sidebar vs Top 4 metric cards:
   - Verify 220px duplicate market status block is replaced by a single status line (`行情源状态: {data_src_badge} ｜ 底座: {latest_date}`).
   - Verify core index corridor is elevated ~190px.
   - Verify appearance popover column ratio `[6.0, 4.0]` eliminates ellipsis truncation.
   - Verify `.main-metric-card` min-height is 88px, padding 6px 10px, 3 clean rows per card.
4. Tab hoisting:
   - Verify dual-wing expander is default collapsed (`expanded=False`, ~36px height).
   - Verify Tab headers sit at y ≈ 180px, visible on 1080p without scrolling.
5. Standardize Tab 1 & Tab 2 cards: border-radius 8px, border 1px solid var(--border-subtle).
6. Run tests:
   `py -3 -m pytest tests/test_ui_pro_redesign_verification.py AGY2_FundAdvisory/tests/test_ui_instant_load.py tests/test_adv_final_closure.py`
7. Write your 5-component report to `d:\Google\Workspace\Wind\.agents\teamwork\reviewer_g10_m1_14_1\handoff.md` and conclude with a clear verdict: **APPROVE** or **REQUEST_CHANGES**. Send a completion message.
