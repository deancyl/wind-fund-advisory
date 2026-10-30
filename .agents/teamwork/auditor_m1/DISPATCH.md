# Dispatch for Auditor (M1)

Scope: Forensic integrity audit of M1 implementation in strategy_bridge.py against R1-R3. Check for hardcoding, facades, dummy returns, look-ahead bias, and verify 4 referee files remain untouched.
See orchestrator prompt for details.

## 2026-10-30T01:46:22Z
You are the Forensic Integrity Auditor for Milestone 1 of the AGY2_FundAdvisory project.
Your working directory is d:\Google\Workspace\Wind\.agents\teamwork\auditor_m1\
You MUST read d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md first before starting work.
Also read d:\Google\Workspace\Wind\.agents\teamwork\orchestrator\PROJECT.md and d:\Google\Workspace\Wind\.agents\teamwork\worker_agent1_m1_gen2\handoff.md.
Working directory for code is d:\Google\Workspace\Wind\AGY2_FundAdvisory.

Mission:
Perform strict forensic integrity auditing of Milestone 1 changes in strategy_bridge.py:
1. Physical safety invariants: Verify that judge_engine.py, holdout_vault.py, AGENT_SPEC.md, and tests/test_infra.py have NOT been modified (compare hashes/timestamps).
2. Anti-cheating & No Look-Ahead Bias:
   - Check strategy_bridge.py for any hardcoded test results, calendar dates ('2018', '2019', etc. used as hardcoded regime switches), mock returns, or dummy facades.
   - Verify that OnlineExpertWeightUpdater uses genuine rolling mathematical formulas with t <= T cutoff (no future lookahead).
   - Verify that SchmidtHysteresisBuffer implements genuine stateful hysteresis logic, not hardcoded mock flags.
3. Verification checks:
   - Run python -m py_compile strategy_bridge.py
   - Run python -m pytest tests/test_infra.py (which runs AST anti-cheating scan and causal probe)
4. Audit Verdict:
   - If ANY integrity violation, dummy facade, hardcoding, or tampering with referee files is detected -> report INTEGRITY VIOLATION with full evidence.
   - If completely clean and authentic -> report CLEAN.
5. Write full audit report in d:\Google\Workspace\Wind\.agents\teamwork\auditor_m1\handoff.md.
6. Send message to orchestrator with your verdict (CLEAN or INTEGRITY VIOLATION).
