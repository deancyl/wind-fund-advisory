# Dispatch for Auditor (M2)

Scope: Forensic integrity audit of M2 (data_loader.py, strategy_bridge.py, portfolio_manager.py).
Check for hardcoded test results, facade shortcuts, future look-ahead bias, and verify 4 referee files remain untouched.
See orchestrator prompt for details.

## 2026-10-30T02:26:20Z
[Message] timestamp=2026-10-30T02:26:20Z sender=7eb668ae-6843-4834-9b3d-3455ac86af88 priority=MESSAGE_PRIORITY_HIGH content=You are the Forensic Integrity Auditor for Milestone 2 of the AGY2_FundAdvisory project.
Your working directory is d:\Google\Workspace\Wind\.agents\teamwork\auditor_m2\
You MUST read d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md first before starting work.
Also read d:\Google\Workspace\Wind\.agents\teamwork\orchestrator\PROJECT.md and d:\Google\Workspace\Wind\.agents\teamwork\worker_agent2_m2\handoff.md.
Working directory for code is d:\Google\Workspace\Wind\AGY2_FundAdvisory.

Mission:
Perform strict forensic integrity auditing of Milestone 2 changes in data_loader.py, strategy_bridge.py, and portfolio_manager.py:
1. Physical safety invariants: Verify that judge_engine.py, holdout_vault.py, AGENT_SPEC.md, and tests/test_infra.py have NOT been modified (compare hashes and git diff).
2. Anti-cheating & No Look-Ahead Bias:
   - Check data_loader.py, strategy_bridge.py, and portfolio_manager.py for hardcoded test fixtures, calendar dates ('2018'-'2025' used as shortcuts), or dummy facades.
   - Verify that EWMA volatility and correlation calculations use genuine rolling mathematical formulas on t <= T data (no future information).
   - Verify that calculate_rebalance_net_utility uses genuine formula calculation and FIFO batch queries, not mock/fake return values.
3. Verification:
   - Run python -m py_compile data_loader.py strategy_bridge.py portfolio_manager.py
   - Run python -m pytest tests/test_infra.py (which runs AST anti-cheating scan and causal probe)
4. Audit Verdict:
   - If ANY integrity violation, dummy facade, hardcoding, or tampering with referee files is detected -> report INTEGRITY VIOLATION with full evidence.
   - If completely clean and authentic -> report CLEAN.
5. Write full audit report in d:\Google\Workspace\Wind\.agents\teamwork\auditor_m2\handoff.md.
6. Send message to orchestrator with your verdict (CLEAN or INTEGRITY VIOLATION).
