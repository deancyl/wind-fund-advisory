# Task Assignment: Auditor (Milestone 2 Forensic Integrity Verification)

## Target
Codebase integrity and anti-cheating audit for Milestone 2.

## Inputs
- Authoritative Request: `d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md`
- Project Plan: `d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_15\PROJECT.md`
- Worker 2 Handoff: `d:\Google\Workspace\Wind\.agents\teamwork\worker_g11_m2\handoff.md`

## Audit Objectives
Execute forensic integrity checks:
1. Verify SHA256 hashes of the 4 read-only referee files:
   - `AGY2_FundAdvisory/judge_engine.py`
   - `holdout_vault.py`
   - `AGENT_SPEC.md`
   - `tests/test_infra.py`
   Must have 0 modification, 0 git diff.
2. Verify `DataLoader.simulate_execution`:
   - Function signature unchanged.
   - Fee deduction logic unchanged.
3. Verify global configuration:
   - `c:\Users\deanc\.gemini\GEMINI.md` must have zero changes.
4. Verify `AGY2_FundAdvisory/app_gui.py` Tab 2:
   - Authentic implementation of Three-Block structure and real connection to portfolio manager, risk engines, and rebalance solvers.
   - No hardcoded strings, dummy facades, or test-bypassing tricks.

Deliver binary verdict: **CLEAN** or **INTEGRITY VIOLATION** with full evidence in `d:\Google\Workspace\Wind\.agents\teamwork\auditor_g11_m2\handoff.md`.


## 2026-11-08T13:58:51Z
You are auditor_g11_m2.
Your working directory is `d:\Google\Workspace\Wind\.agents\teamwork\auditor_g11_m2\`.
Read your task in `d:\Google\Workspace\Wind\.agents\teamwork\auditor_g11_m2\DISPATCH.md`.
Read `d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md`.
Read `d:\Google\Workspace\Wind\.agents\teamwork\worker_g11_m2\handoff.md`.
Execute forensic integrity checks on the codebase:
1. Four read-only referee files SHA256 hashes and git diff (0 modification).
2. DataLoader.simulate_execution signature and fee logic (0 modification).
3. Global configuration c:\Users\deanc\.gemini\GEMINI.md zero changes.
4. AGY2_FundAdvisory/app_gui.py Tab 2 authenticity and anti-cheating check.
Deliver your report with a clear binary verdict (CLEAN or INTEGRITY VIOLATION) in `d:\Google\Workspace\Wind\.agents\teamwork\auditor_g11_m2\handoff.md`.
Notify the orchestrator (conversation ID: c6b4ebd0-c5f1-4175-8ba5-3bd0979b970d) when done.
