## 2026-11-09T06:56:49Z
You are explorer_g13_survey_3, a teamwork_explorer.
Your working directory is: d:\Google\Workspace\Wind\.agents\teamwork\explorer_g13_survey_3\
You MUST read the user's original request file before starting:
d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
Also refer to external audit files if helpful:
c:\Users\deanc\Downloads\agy2_ui_ux_audit_and_fix_plan (1).md
c:\Users\deanc\Downloads\agy2_fundadvisory_5_screenshots_diagnosis_and_fix.md

Your mission is technical exploration of test suite impact, read-only file integrity baseline, and browser verification plan:
1. Physical read-only files check:
   - Verify SHA256 / content of the 4 strictly read-only files: `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`.
   - Verify `DataLoader.simulate_execution` signature and fee deduction logic.
   - Note down hash verification requirements.
2. Existing test suite analysis:
   - Search across `tests/` for tests that might assert on old UI elements:
     `btn_master_action_switch`, `查看锁仓保护`, `一键批量锁定`, `+ 入备选池`, `col_wing_btn`, `择机置换`, etc.
   - Check `tests/test_adv_final_closure.py`, `tests/test_infra.py`, `tests/test_g3_evolution_loop.py`, `tests/test_gui_multi_ledger_stress.py`, `tests/test_adv_upgrade_suite.py`, etc.
   - List every test that may fail due to the removal of fake buttons or layout changes, and formulate how to update these non-read-only test assertions to ensure 100% green pass.
3. Clean ledger and temp files audit:
   - Check `data/ledgers_index.json` and ensure only clean main real ledger is preserved.
   - Identify any temporary test scripts or artifacts to clean up.
4. Browser verification plan:
   - Check how Streamlit 8501 is currently hosted/managed, how to stop and restart it cleanly without port collision.
   - Define exact browser verification steps and criteria for each of the 5 screenshots/pain points.

Hard constraints:
- You are read-only. Do NOT modify source code files.
- Produce your comprehensive report at:
  d:\Google\Workspace\Wind\.agents\teamwork\explorer_g13_survey_3\handoff.md
- Report your findings back via send_message.
