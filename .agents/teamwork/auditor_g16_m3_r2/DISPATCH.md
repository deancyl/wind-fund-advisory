# DISPATCH — auditor_g16_m3_r2

## Role
teamwork_auditor

## Working Directory
d:\Google\Workspace\Wind

## State Folder
d:\Google\Workspace\Wind\.agents\teamwork\auditor_g16_m3_r2\

## Original Request & Scope Documents
- ORIGINAL_REQUEST.md: `d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md`
- SCOPE.md: `d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_g16_gen4\SCOPE.md`

## Mission & Forensic Integrity Verification
Perform forensic integrity verification:
1. Verify 4 read-only referee files have 0 modifications:
   - `AGY2_FundAdvisory/judge_engine.py` (or root `judge_engine.py`)
   - `AGY2_FundAdvisory/holdout_vault.py` (or root `holdout_vault.py`)
   - `AGY2_FundAdvisory/AGENT_SPEC.md` (or root `AGENT_SPEC.md`)
   - `tests/test_infra.py` (or `AGY2_FundAdvisory/tests/test_infra.py`)
2. Verify `DataLoader.simulate_execution` signature and default fee logic have 0 modifications.
3. Check for any hardcoding, cheating, or facade bypass.
4. Run tests: `py -3 -m pytest tests/test_infra.py -v`
5. Write your verdict (`CLEAN` or `INTEGRITY VIOLATION`) to `handoff.md` in your state folder. Send message to orchestrator upon completion.


## 2026-11-11T04:33:12Z
You are auditor_g16_m3_r2. Your state folder is d:\Google\Workspace\Wind\.agents\teamwork\auditor_g16_m3_r2\.
Read your assignment in d:\Google\Workspace\Wind\.agents\teamwork\auditor_g16_m3_r2\DISPATCH.md.
Perform forensic integrity verification:
1. Verify 4 read-only referee files have 0 modifications: judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py.
2. Verify DataLoader.simulate_execution signature and default fees have 0 modifications.
3. Check for any hardcoding, cheating, or facade bypass in recent commits and current working tree.
4. Run tests: py -3 -m pytest tests/test_infra.py -v
Write your report and verdict (CLEAN or INTEGRITY VIOLATION) to handoff.md in your state folder.
Send a message to your caller (orchestrator) with your verdict upon completion.
