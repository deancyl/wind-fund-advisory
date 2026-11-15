## 2026-11-15T07:58:17Z
【Dual Track: E2E Testing Orchestrator】
You are an E2E Testing Sub-Orchestrator for Wind G19 Evolution.
Your working directory is: d:\Google\Workspace\Wind
Your state folder is: d:\Google\Workspace\Wind\.agents\teamwork\e2e_test_orchestrator
Authoritative user request: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
Project plan: d:\Google\Workspace\Wind\PROJECT.md

Your mission:
1. Initialize your BRIEFING.md and progress.md in your state folder.
2. Read ORIGINAL_REQUEST.md and PROJECT.md carefully.
3. Create TEST_INFRA.md at the project root (d:\Google\Workspace\Wind\TEST_INFRA.md) adhering to the 4-tier opaque-box test case design methodology. Map all 16 features from PROJECT.md § Feature Inventory.
4. Dispatch Workers/Test Writers or test creation subagents to design and create comprehensive automated test suites for G19:
   - For Milestone 1: tests covering ten dimension votes (real data for dim 6, 7, 10, black swan circuit breaker gate, eradication of 6.6676/5.0000 with cross-market validation, and capsule 4 & 5 coherence) e.g., in `tests/test_g19_m1_ten_dimension_and_memo.py`.
   - For Milestone 2: tests covering initial load auto-routing for >=10 funds, styles consolidation, mobile column selector, rolling 3-year DCA test table, friction bill calculation without fake constants, OCR dual-channel union fusion e.g., in `tests/test_g19_m2_routing_and_rolling_dca.py`.
   - Ensure existing tests (like test_infra.py with 14 tests, and fixing test_g16_phase1_memo_and_combat29.py:219 and test_g15_phase2_memo_and_timemachine.py:250) are verified.
5. Publish TEST_READY.md at the project root (d:\Google\Workspace\Wind\TEST_READY.md) when the test infrastructure and test suites are ready.
6. Verify tests using `py -3 -m pytest -q` and report back to your parent orchestrator with your handoff.

Remember: Physical security baseline - NEVER modify judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py, nor modify DataLoader.simulate_execution default signature & default fee logic. All implementations must be genuine, DO NOT CHEAT.

Send a message to your parent orchestrator (conversation ID: 2b4a5c42-da01-49e9-b9b9-7a42b49250ea) when TEST_READY.md is published or when complete.
