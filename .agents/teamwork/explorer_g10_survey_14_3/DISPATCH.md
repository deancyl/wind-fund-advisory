## 2026-11-08T09:10:02Z

You are Explorer 3 (explorer_g10_survey_14_3) in the G10 visual subtraction and UI elevation mission.

## Identity & Workspace
- Type: teamwork_explorer
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\explorer_g10_survey_14_3\
- Authoritative user request file: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
- You are read-only: do NOT edit source code or test files. Only write to your working directory.

## Objective
Survey the test suite in `tests/` and assess assertions against the planned G10 UI subtractions:
1. Four strictly read-only referee files:
   - Check `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`.
   - Confirm SHA-256 hash checking logic in `tests/test_infra.py`.
   - Verify that `tests/test_infra.py` and the other three files must NEVER be touched under any circumstances.
2. Search and list all test assertions in non-read-only test files (such as `tests/test_adv_final_closure.py`, `tests/test_g3_evolution_loop.py`, `tests/test_gui_multi_ledger_stress.py`, etc.) that inspect UI text or DOM elements that will be modified by the G10 surgeries:
   - Sector card text (e.g. `【量化因果链】`, `入选依据`, `20日波动`, etc.).
   - Right-wing sentry assertions (e.g. checking for `render_stress_liquidity_card_html` or CVaR -36.1% text, green correlation card text, or duplicate action button strings).
   - Sidebar assertions (e.g. checking for market status in sidebar).
   - Top 4 metrics / dual wing expander state assertions (e.g. `expanded=True` or `expanded=False`).
   - News feed assertions (e.g. news text keywords).
3. Outline the precise modifications required in those non-read-only test files to ensure 100% test pass rate while keeping test integrity intact.

## Outputs
Write your detailed analysis to `d:\Google\Workspace\Wind\.agents\teamwork\explorer_g10_survey_14_3\analysis.md` and a structured `handoff.md`.
Then send a completion message back with your findings summary.

## 2026-11-08T09:20:53Z

**Context**: Survey status check
**Content**: Checking in on your test suite survey progress. Please report current status and write your analysis to analysis.md / handoff.md as soon as ready.
**Action**: Update progress.md and report status.
