## 2026-11-09T08:43:49Z
You are worker_g13_m3, a teamwork_worker.
Your working directory is: d:\Google\Workspace\Wind\.agents\teamwork\worker_g13_m3\
You MUST read the user's original request file before starting:
d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
Also read the detailed Explorer 3 handoff report:
d:\Google\Workspace\Wind\.agents\teamwork\explorer_g13_survey_3\handoff.md
And reference:
d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_1\PROJECT.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

PHYSICAL SAFETY RED LINES:
- NEVER touch or modify the 4 strictly read-only files:
  `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py` (and `AGY2_FundAdvisory/tests/test_infra.py`).
- `DataLoader.simulate_execution` default signature and default fee deduction logic MUST remain 100% intact.

YOUR SCOPE & WRITE OWNERSHIP (Milestone 3: 非只读测试适配更新、孤儿账本清理与全量回归 100% 绿灯):
Files you own:
- Non-read-only test files in `tests/` (e.g. `tests/test_challenger_g11_m1_actions.py`, `tests/test_g7_architecture_and_decoupling.py`, `tests/test_final_acceptance_all_features.py`)
- `data/ledgers/` orphan sandbox files

DETAILED TASKS:
1. Clean up orphaned sandbox files in `data/ledgers/`:
   - Delete `data/ledgers/sandbox_20261108_000418_344a.db` and `data/ledgers/sandbox_20261108_000418_344a.json`.
   - Verify that `data/ledgers_index.json` only contains the clean, protected `main_live` ledger.
2. Adapt non-read-only test assertions to G13 reality:
   - In `tests/test_challenger_g11_m1_actions.py` (around L550, L610):
     Update the test assertion that previously expected `btn_master_action_switch`.
     Assert that `at.button(key="btn_master_action_switch") is None`, confirming the fake red button has been completely eliminated! And verify that the top advisory expander displays clear human-readable advice without errors.
   - In `tests/test_g7_architecture_and_decoupling.py`:
     Check L53 (`len(traj.get("dates", []))`), adapt to `>= 45` or valid slice count.
     Check L111-112 (old button string checks), adapt assertion to reflect buttonless clean risk list.
   - In `tests/test_final_acceptance_all_features.py`:
     Check L132 (banking_dividend radar=45.7 vs corridor=92.1) valuation percentile assertion conflict, fix assertion to align with anti-whipsaw valuation percentile.
3. Run the FULL test suite:
   Run:
   `py -3 -m pytest tests/test_infra.py tests/test_adv_final_closure.py tests/test_g3_evolution_loop.py tests/test_gui_multi_ledger_stress.py tests/test_challenger_g11_m1_actions.py tests/test_g7_architecture_and_decoupling.py tests/test_final_acceptance_all_features.py`
   Ensure 100% pass (0 failures).
4. Verify SHA256 of 4 strictly read-only files:
   - `judge_engine.py`: `76F930371176DE7EE6A413174B030101E3210AC6E037F5D10FE229AF31CC07BE`
   - `holdout_vault.py`: `88122EAF647040A410E2FD95DA81077DB10149A498A47340FF40B670BD031D2A`
   - `AGENT_SPEC.md`: `A346586F9BD2DC0EE83E665BD18E7A6471464C9F7B658E392B989B800CD63957`
   - `tests/test_infra.py`: `48BEE0DA300D7C0A0848EC1376E4B9B2E55224D2736081713B4340F0362CD100`

Deliver your complete report to:
`d:\Google\Workspace\Wind\.agents\teamwork\worker_g13_m3\handoff.md`
And notify parent via send_message.
