# Task Assignment: Reviewer 2 (Milestone 1 Gate Review)

## Target File
`AGY2_FundAdvisory/app_gui.py`

## Inputs
- Authoritative Request: `d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md`
- Project Plan: `d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_15\PROJECT.md`
- Worker Handoff: `d:\Google\Workspace\Wind\.agents\teamwork\worker_g11_m1\handoff.md`

## Review Scope
Review Worker 1's implementation of Milestone 1 independently:
1. CSS & Layout: Check CSS `.main-metric-card` 82px height lock, emoji reduction >70%, `block-container` `padding-top: 1.2rem`, card `margin-bottom: 6px`.
2. Top Area & Banners: Check removal of duplicate banners, integration into wing expander dynamic title, jump button placement, and retention of test hooks.
3. Tab 1 Architecture: Check complete removal of step indicator, caption, AI box, duplicate button; verify Module 1 single-line control bar, Module 2 dataframe & 3-metric bar placement, Module 3 single-line action popovers & bottom drawer.
4. Interface & Contracts: Verify widget keys (`btn_run_simulation_now`, `tab1_sel_model_type`, `plan_capital_input`, `tab1_tier_selector`, `radio_capital_deployment_mode`).
5. Run tests: `pytest tests/test_infra.py tests/test_adv_final_closure.py tests/test_g8_ux_and_realtime_fusion.py tests/test_g10_correlation_liquidity_and_stress.py`.

Deliver clear verdict: **APPROVE** or **REQUEST_CHANGES** in `d:\Google\Workspace\Wind\.agents\teamwork\reviewer_g11_m1_2\handoff.md`.

## 2026-11-08T12:59:36Z
You are reviewer_g11_m1_2.
Your working directory is `d:\Google\Workspace\Wind\.agents\teamwork\reviewer_g11_m1_2\`.
Read your task in `d:\Google\Workspace\Wind\.agents\teamwork\reviewer_g11_m1_2\DISPATCH.md`.
Read `d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md`.
Read `d:\Google\Workspace\Wind\.agents\teamwork\worker_g11_m1\handoff.md`.
Review Worker 1's changes in `AGY2_FundAdvisory/app_gui.py` and run tests.
Deliver your review report with a clear verdict (APPROVE or REQUEST_CHANGES) in `d:\Google\Workspace\Wind\.agents\teamwork\reviewer_g11_m1_2\handoff.md`.
Notify the orchestrator (conversation ID: c6b4ebd0-c5f1-4175-8ba5-3bd0979b970d) when done.
