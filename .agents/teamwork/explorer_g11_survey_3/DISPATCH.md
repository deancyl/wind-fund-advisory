# Task Assignment: Explorer 3 (Survey - Test Suite Alignment & Invariant Checks)

## Objective
Read `d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md`.
Investigate:
1. Four read-only files: `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`. Record their current checksums / status and ensure they are untouched.
2. `DataLoader.simulate_execution`: Check its signature and fee logic to ensure it remains untouched.
3. Check the UI test suites:
   - `tests/test_adv_final_closure.py`
   - `tests/test_g3_evolution_loop.py`
   - `tests/test_gui_multi_ledger_stress.py`
   Identify all assertions checking for old buttons (e.g. `col_s1_all`, `col_s1_step`, duplicate generate buttons, old step indicator, old banner texts, scattered ledger management buttons) that need alignment.
4. Check data files (`data/ledgers_index.json`, ensure clean real ledgers, no temporary test files left).
5. Check current Streamlit service status (port 8501, health probe `http://127.0.0.1:8501/_stcore/health`), how it is launched in Windows, and how it should be restarted.
6. Check G12 requirements: exact command tag format `[slashCommand:/goal] [slashCommand:/boost] [slashCommand:/teamwork]` and `[slashCommand:/browser]`, plain text formatting, git commit/tag conventions (`v4.1-G11`), victory audit criteria.

Document exact findings, test failures anticipated if UI changes, and alignment recommendations in `d:\Google\Workspace\Wind\.agents\teamwork\explorer_g11_survey_3\handoff.md`.

## 2026-11-08T12:01:27Z
[Message] sender=c6b4ebd0-c5f1-4175-8ba5-3bd0979b970d priority=MESSAGE_PRIORITY_HIGH
You are explorer_g11_survey_3.
Your working directory is `d:\Google\Workspace\Wind\.agents\teamwork\explorer_g11_survey_3\`.
Read your task description in `d:\Google\Workspace\Wind\.agents\teamwork\explorer_g11_survey_3\DISPATCH.md`.
Read the authoritative user request in `d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md`.
Investigate the test suite, read-only constraints, ledger index status, service health, and G12 requirements per R1-R4.
Write your complete, structured findings and concrete alignment recommendations to `d:\Google\Workspace\Wind\.agents\teamwork\explorer_g11_survey_3\handoff.md`.
Update `progress.md` in your directory periodically.
When finished, send a message to the orchestrator (conversation ID: c6b4ebd0-c5f1-4175-8ba5-3bd0979b970d) with a summary and path to your handoff.md.
