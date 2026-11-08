## 2026-11-08T07:27:02Z
You are worker_g9_m2_fix, a versatile implementation and QA worker.
Your working directory is: d:\Google\Workspace\Wind\.agents\teamwork\worker_g9_m2_fix\

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

MANDATORY INSTRUCTION:
Read the authoritative user request at:
d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
and the scope document at:
d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_13\SCOPE.md
and the technical investigation and diff plan from explorer_g9_m2_fix at:
d:\Google\Workspace\Wind\.agents\teamwork\explorer_g9_m2_fix\handoff.md

### Exclusive Write Ownership:
You own `d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py` exclusively.
STRICT PROHIBITION:
- NEVER modify the four read-only referee files: `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`.
- NEVER modify `DataLoader.simulate_execution` signature or default fee logic.
- NEVER modify global `c:\Users\deanc\.gemini\GEMINI.md`.

### Your Task: Milestone 2 Remediation
1. In `AGY2_FundAdvisory/app_gui.py` around line 5100:
   Fix the Popover quick fund entry import:
   Change:
   `from data_loader import search_funds_in_catalog`
   To:
   `from portfolio_manager import search_funds_in_catalog`
   (Or safely call `search_funds_in_catalog` which is already imported from `portfolio_manager` at line 69 / line 162).
2. In `AGY2_FundAdvisory/app_gui.py` around line 2766:
   Fix `data_loader.get_fund_metadata(_c)` to `DataLoader.get_fund_metadata(_c)`.
3. Verify that Rule 27 HTML purification is 100% maintained and no regressions were introduced.
4. Run tests:
   `pytest tests/test_challenger_g9_m2_adversarial.py`
   (Confirm that all 30 tests pass, including `test_app_gui_popover_fund_name_search_no_broken_import`).
   `pytest tests/test_infra.py tests/test_sidebar_remodel_and_bugfixes.py tests/test_g8_ux_and_realtime_fusion.py tests/test_gui_multi_ledger_stress.py tests/test_challenger_g9_m2_stress.py tests/test_g9_causal_brinson_and_suitability.py`
   (Confirm 100% pass across all test suites).
5. Document your edits and test execution results in `d:\Google\Workspace\Wind\.agents\teamwork\worker_g9_m2_fix\handoff.md`.
6. Send a message to orchestrator with your results.
