# Task Assignment: Challenger M1-2 (Screener Boundary, Liquidation & GUI Invariants Challenger)

## Authoritative Request File
`d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md` (MUST read completely before proceeding)
`d:\Google\Workspace\Wind\.agents\teamwork\orchestrator\PROJECT.md` (Master Architecture & Milestone Contracts)
`d:\Google\Workspace\Wind\GEMINI.md` (Workspace Rules)
`d:\Google\Workspace\Wind\.agents\teamwork\worker_prod_m1\handoff.md` (Worker M1 Handoff Report)

## Scope & Adversarial Challenge Objective
You are Challenger M1-2 for Milestone 1. Adversarially verify screener boundary conditions and GUI invariants:
1. **Screener Candidate Pool Quality & Boundary**:
   - Verify `SmartCacheManager.get_candidate_pool()`: does it return >= 7,000 valid candidates?
   - Try passing an empty DataFrame to `save_candidate_pool`: does it block saving and prevent 0-row cache pollution?
2. **Fund Liquidation Risk Boundary**:
   - Test `portfolio_optimizer.py` with a fund whose AUM is < 0.5 亿元: does it flag `🚨【清盘预警】` in the execution sheet?
   - Test with a fund whose AUM >= 0.5 亿元: does it avoid false-positive warnings?
3. **GUI Geometry & CSS Invariants**:
   - Check `AGY2_FundAdvisory/app_gui.py`:
     * Verify `.index-pill-val-badge` and `.val-*` are correctly scoped and bound to theme CSS variables.
     * Confirm GEMINI.md Rules 14 & 15: `flex: 0 0 auto !important; white-space: nowrap !important; overflow-x: auto !important;`.
4. Give a clear verdict: `APPROVE` or `REQUEST_CHANGES`.

## Working Directory
`d:\Google\Workspace\Wind\.agents\teamwork\challenger_m1_2/`

## Output Requirements
Write your full challenge report to:
`d:\Google\Workspace\Wind\.agents\teamwork\challenger_m1_2\handoff.md`
Then call `send_message` to parent.


## 2026-11-04T10:24:23Z
You are Challenger M1-2 for Milestone 1.
Working directory: d:\Google\Workspace\Wind\.agents\teamwork\challenger_m1_2/
Read your task dispatch file: d:\Google\Workspace\Wind\.agents\teamwork\challenger_m1_2\DISPATCH.md
Read the authoritative request file: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
Read master architecture: d:\Google\Workspace\Wind\.agents\teamwork\orchestrator\PROJECT.md
Read Worker Prod M1 Handoff: d:\Google\Workspace\Wind\.agents\teamwork\worker_prod_m1\handoff.md
Read workspace rules: d:\Google\Workspace\Wind\GEMINI.md

Adversarially challenge Milestone 1:
1. Screener pool boundary: verify candidate pool returns >= 7,000 valid funds; test save_candidate_pool with empty DataFrame to ensure 0-row cache pollution is blocked.
2. Fund liquidation boundary: test liquidation risk alert on funds with AUM < 0.5亿 vs funds >= 0.5亿 in portfolio_optimizer.py.
3. GUI geometry & CSS: verify .index-pill-val-badge and .val-* bindings, and check GEMINI.md Rules 14 & 15.
Write your challenge report and clear verdict (APPROVE or REQUEST_CHANGES) to:
d:\Google\Workspace\Wind\.agents\teamwork\challenger_m1_2\handoff.md
Notify parent when done via send_message. You are read-only; DO NOT modify any source code files.
