# DISPATCH — explorer_g14_survey_3

## Objective
Technical survey of Test Suite, Physical Safety Redlines, Browser Verification & Release Procedures:
1. Physical Safety Redlines:
   - Check the 4 read-only judge files: `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`. Note their hashes/contents to ensure ZERO changes.
   - Check `DataLoader.simulate_execution`: verify default signature and fee logic are strictly untouched.
   - Check `data/ledgers_index.json`: verify only clean real portfolios remain, no test ledger garbage.
2. Existing Test Suite Analysis:
   - Inspect existing tests:
     `tests/test_infra.py`
     `tests/test_adv_final_closure.py`
     `tests/test_g3_evolution_loop.py`
     `tests/test_gui_multi_ledger_stress.py`
   - Check if any existing tests fail currently or have outdated assertions.
3. Design New Unit Tests for G14:
   - Verify `radar_sectors_cache.json` actual disk persistence and TTL handling.
   - Verify `get_60d_rolling_nav_and_trajectory` dynamic factor weights Top 3 selection vs static Top 3 selection, and 20 bps turnover cost deduction.
   - Verify 12-dimensional active risk sentry inspection completeness (all 12 dimensions tested, `holdings_hash` caching in `session_state` and `data/portfolio_watchdog.json`).
4. Operational & Delivery Requirements:
   - How to cleanly terminate 8501 port process and launch Streamlit for `/browser` verification.
   - Git operations: `git add -A`, `git commit`, `git tag -a v4.4-G14`, `git push origin HEAD --tags` (strictly NO GitHub release).
   - Strict semicolon-locked slashCommand format for G15 bootstrap prompt:
     `[/goal](slashCommand;goal)`, `[/boost](slashCommand;boost)`, `[/teamwork](slashCommand;teamwork)`, `[/browser](slashCommand;browser)` (zero colons).
   - Rules update: root `GEMINI.md` and `PROGRESS_LOG.md` (never touch global).

Read `ORIGINAL_REQUEST.md` at `d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md`.
Output detailed verification plan and test suite architecture in `handoff.md` in your directory.


## 2026-11-09T11:25:43Z
[Message] sender=675b287a-9df2-4040-9227-01d56b1552b2
You are explorer_g14_survey_3, working in directory: d:\Google\Workspace\Wind\.agents\teamwork\explorer_g14_survey_3\
Read your task assignment in d:\Google\Workspace\Wind\.agents\teamwork\explorer_g14_survey_3\DISPATCH.md and d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md.
Investigate the test suite, physical safety redlines, browser verification, and delivery operations:
1. Physical safety redlines check: 4 read-only judge files (judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py) and DataLoader.simulate_execution.
2. Existing test suites: inspect tests/test_infra.py, test_adv_final_closure.py, test_g3_evolution_loop.py, test_gui_multi_ledger_stress.py. Run them or analyze their assertions.
3. Design new unit tests for G14 (radar cache write/read, get_60d_rolling_nav_and_trajectory dynamic selection/turnover, 12-dim sentry inspection & caching).
4. Outline service restart, browser inspection criteria, Git tag v4.4-G14, and semicolon-locked G15 prompt format.
