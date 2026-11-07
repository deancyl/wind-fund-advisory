## 2026-11-07T14:26:52Z

[Message] timestamp=2026-11-07T14:26:52Z sender=edefabf5-5abf-4405-bb80-202032d71b10 priority=MESSAGE_PRIORITY_HIGH content=You are Explorer 3 for the G7 Generation Survey.
Your working directory is: d:\Google\Workspace\Wind\.agents\teamwork\explorer_g7_3
MANDATORY: Read d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md and d:\Google\Workspace\Wind\GEMINI.md before starting work.
Do NOT write or modify application code. You are an investigation agent.

Task:
1. Thoroughly investigate OnlineHeuristicFactorEvolver in AGY2_FundAdvisory/advisory_engine.py and portfolio_optimizer.py:
   - Where is OnlineHeuristicFactorEvolver defined, initialized, and invoked?
   - What is its current fitness evaluation logic?
   - How to add turnover penalty (换手率惩罚) and tail maximum drawdown (尾部最大回撤) constraints to the fitness function?
   - How is the genetic evolution whitebox badge rendered at the top of Opportunity Radar in app_gui.py?
   - How to implement the expandable comparison view:
     * 60-day rolling net value comparison between static fixed weights (0.30, 0.30, 0.25, 0.15) vs online genetic dynamic weights.
     * 4-dimensional weight evolution trajectory (valuation, momentum, SNR, anti-crowding).
     * Vectorized computation in pure NumPy under 50ms.
2. Investigate codebase import paths and legacy root src disambiguation:
   - Check all business modules in AGY2_FundAdvisory/ and test scripts in tests/ to verify if any imports reference legacy `src/` or ambiguous package names.
   - Confirm how sys.path is initialized in app_gui.py and test fixtures to ensure 100% explicit reference to AGY2_FundAdvisory.
3. Investigate the 4 strictly read-only judge files:
   - judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py: verify their exact roles and confirm that our G7 changes touch ZERO lines in these 4 files.
   - Verify DataLoader.simulate_execution default signature and fee logic remains untouched.
4. Test Suite Strategy:
   - Review pytest test suite (tests/test_infra.py, tests/test_adv_final_closure.py, tests/test_g3_evolution_loop.py, tests/test_gui_multi_ledger_stress.py).
   - Design test specifications for G7 additions: Tab 2 dual-view switching, 3-way risk linkage, genetic evolver turnover penalty and 60-day comparison.

Deliver your detailed findings, code locations, mathematical fitness formulas, and test plans in:
d:\Google\Workspace\Wind\.agents\teamwork\explorer_g7_3\handoff.md
Send a completion message back when done.
