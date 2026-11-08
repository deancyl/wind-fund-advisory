# Task Assignment: Reviewer 1 (Milestone 1 Gate Review)

## Target File
`AGY2_FundAdvisory/app_gui.py`

## Inputs
- Authoritative Request: `d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md`
- Project Plan: `d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_15\PROJECT.md`
- Worker Handoff: `d:\Google\Workspace\Wind\.agents\teamwork\worker_g11_m1\handoff.md`

## Review Scope
Review Worker 1's implementation of Milestone 1:
1. CSS: 82px card height locked in CSS (`.main-metric-card`), emoji reduced >70%, `block-container` `padding-top: 1.2rem`, card `margin-bottom: 6px`.
2. Top Area: No standalone action switch banner, no standalone cross-tab banner; dynamic conclusion title in wing expander with compact jump button; `# 跨区联动指令已生效承接横幅` comment preserved.
3. Tab 1: No step indicator, no caption, no gray AI box, no duplicate `btn_t1_run_all`.
4. Tab 1 Module 1: Single line controls with capital, C1-C5, rhythm, advanced Popover with 7 standard model names, single primary button.
5. Tab 1 Module 2: 3-column metric bar right above dataframe without intervening PCR banner or blue summary advice.
6. Tab 1 Module 3: 4 action Popovers/buttons + single bottom drawer expander.
7. Run tests: `pytest tests/test_infra.py tests/test_adv_final_closure.py tests/test_g8_ux_and_realtime_fusion.py tests/test_g10_correlation_liquidity_and_stress.py`.

Deliver clear verdict: **APPROVE** or **REQUEST_CHANGES** in `d:\Google\Workspace\Wind\.agents\teamwork\reviewer_g11_m1_1\handoff.md`.


## 2026-11-08T12:59:23Z
You are reviewer_g11_m1_1.
Your working directory is `d:\Google\Workspace\Wind\.agents\teamwork\reviewer_g11_m1_1\`.
Read your task in `d:\Google\Workspace\Wind\.agents\teamwork\reviewer_g11_m1_1\DISPATCH.md`.
Read `d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md`.
Read `d:\Google\Workspace\Wind\.agents\teamwork\worker_g11_m1\handoff.md`.
Review Worker 1's changes in `AGY2_FundAdvisory/app_gui.py` and run tests.
Deliver your review report with a clear verdict (APPROVE or REQUEST_CHANGES) in `d:\Google\Workspace\Wind\.agents\teamwork\reviewer_g11_m1_1\handoff.md`.
Notify the orchestrator (conversation ID: c6b4ebd0-c5f1-4175-8ba5-3bd0979b970d) when done.
