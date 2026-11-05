# Task Assignment: Reviewer Fix M1 (Milestone 1 Remediation Re-Verification)

## Authoritative Request File
`d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md` (MUST read completely before proceeding)
`d:\Google\Workspace\Wind\.agents\teamwork\orchestrator\PROJECT.md` (Master Architecture & Milestone Contracts)
`d:\Google\Workspace\Wind\GEMINI.md` (Workspace Rules)
`d:\Google\Workspace\Wind\.agents\teamwork\worker_remediation_m1\handoff.md` (Remediation Report)
`d:\Google\Workspace\Wind\.agents\teamwork\challenger_m1_1\handoff.md` (Original Challenger Report)

## Scope & Objective
Perform independent re-verification of Milestone 1 remediation:
1. Verify the cold start latency fix in `AGY2_FundAdvisory/cache_manager.py`:
   - Run `py -3 -m pytest AGY2_FundAdvisory/tests/test_challenger_m1_adversarial.py -v -s` (Confirm `test_fund_purchase_cache_cold_start_under_50ms` passes with < 50ms).
2. Run full M1 regression suite:
   - `py -3 -m pytest AGY2_FundAdvisory/tests/test_m1_open_data_and_cache.py -v`
   - `py -3 -m pytest tests/test_infra.py`
3. Verify that all 5 referee baseline files SHA-256 hashes are 100% untouched.
4. Give a clear verdict: `APPROVE` or `REQUEST_CHANGES`.

## Working Directory
`d:\Google\Workspace\Wind\.agents\teamwork\reviewer_fix_m1/`

## Output Requirements
Write your verification report to:
`d:\Google\Workspace\Wind\.agents\teamwork\reviewer_fix_m1\handoff.md`
Then call `send_message` to parent.

## 2026-11-04T10:51:54Z
You are Reviewer Fix M1.
Working directory: d:\Google\Workspace\Wind\.agents\teamwork\reviewer_fix_m1/
Read your task dispatch file: d:\Google\Workspace\Wind\.agents\teamwork\reviewer_fix_m1\DISPATCH.md
Read the authoritative request file: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
Read master architecture: d:\Google\Workspace\Wind\.agents\teamwork\orchestrator\PROJECT.md
Read Worker Remediation M1 Handoff: d:\Google\Workspace\Wind\.agents\teamwork\worker_remediation_m1\handoff.md
Read Challenger M1-1 Report: d:\Google\Workspace\Wind\.agents\teamwork\challenger_m1_1\handoff.md
Read workspace rules: d:\Google\Workspace\Wind\GEMINI.md

Your task:
Perform independent re-verification of the cold-start latency fix in AGY2_FundAdvisory/cache_manager.py.
Run tests:
- py -3 -m pytest AGY2_FundAdvisory/tests/test_challenger_m1_adversarial.py -v -s (Confirm test_fund_purchase_cache_cold_start_under_50ms passes strictly < 50ms!)
- py -3 -m pytest AGY2_FundAdvisory/tests/test_m1_open_data_and_cache.py -v
- py -3 -m pytest tests/test_infra.py
Verify referee file SHA-256 hashes.
Write your verification report and verdict (APPROVE or REQUEST_CHANGES) to:
d:\Google\Workspace\Wind\.agents\teamwork\reviewer_fix_m1\handoff.md
Notify parent when done via send_message. You are read-only; DO NOT modify any source code files.

