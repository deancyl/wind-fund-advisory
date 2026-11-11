# DISPATCH — auditor_g16_m3

## Role
teamwork_auditor

## Working Directory
d:\Google\Workspace\Wind

## State Folder
d:\Google\Workspace\Wind\.agents\teamwork\auditor_g16_m3\

## Original Request & Scope Documents
- ORIGINAL_REQUEST.md: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
- SCOPE.md: d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_g16_gen4\SCOPE.md

## Mission & Forensic Integrity Verification
Perform forensic integrity verification on the codebase (including commit ee1795a and current state):
1. Mandatory Read-Only Referee Files Check:
   - `AGY2_FundAdvisory/judge_engine.py` (or root `judge_engine.py`)
   - `AGY2_FundAdvisory/holdout_vault.py` (or root `holdout_vault.py`)
   - `AGY2_FundAdvisory/AGENT_SPEC.md` (or root `AGENT_SPEC.md`)
   - `tests/test_infra.py` (or `AGY2_FundAdvisory/tests/test_infra.py`)
   Check git status / git diff against initial or master to verify ZERO modifications to these 4 referee files!
2. `DataLoader.simulate_execution` Redline Check:
   - Check `AGY2_FundAdvisory/data_loader.py`
   - Verify `inspect.signature(DataLoader.simulate_execution)` has exactly default arguments: `is_otc=True, penalty_days=7, penalty_rate=0.015, etf_impact=0.001`.
   - Verify zero modification to fee calculation logic.
3. Anti-Cheating & Integrity Analysis:
   - No hardcoded test responses or facade bypasses.
   - Run tests: `py -3 -m pytest tests/test_infra.py -v`
4. Write your verdict (`CLEAN` or `INTEGRITY VIOLATION`) to `handoff.md` in your state folder. Send message to orchestrator upon completion.


## 2026-11-11T04:05:38Z
You are auditor_g16_m3. Your state folder is d:\Google\Workspace\Wind\.agents\teamwork\auditor_g16_m3\.
Read your assignment in d:\Google\Workspace\Wind\.agents\teamwork\auditor_g16_m3\DISPATCH.md, as well as d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md and d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_g16_gen4\SCOPE.md.
Perform forensic integrity verification:
1. Verify 4 read-only referee files have 0 modifications: judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py.
2. Verify DataLoader.simulate_execution has 0 modifications to signature and default fees.
3. Check for any hardcoding, cheating, or facade bypass.
4. Run tests: py -3 -m pytest tests/test_infra.py -v
Write your report and verdict (CLEAN or INTEGRITY VIOLATION) to handoff.md in your state folder.
Send a message to your caller (orchestrator) with your verdict and findings upon completion.
