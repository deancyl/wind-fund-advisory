# Dispatch for Explorer Survey 2 (AGY2_FundAdvisory Codebase & Invariants)
Assigned by Project Orchestrator
## 2026-10-29T09:04:08Z
[Message] sender=5fd996d1-bc98-447a-9f35-c5aef5be2e1c priority=MESSAGE_PRIORITY_HIGH
Content:
You are Explorer 2 (AGY2 Architecture Explorer).
Your working directory is: d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_2
Your original parent conversation ID is: 5fd996d1-bc98-447a-9f35-c5aef5be2e1c (Project Orchestrator).

MANDATORY FIRST STEP:
Read the user request at: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md

OBJECTIVE:
Investigate the existing architecture, code structure, test runner, and read-only invariants of `AGY2_FundAdvisory`:
1. Inspect the codebase in `d:\Google\Workspace\Wind\AGY2_FundAdvisory`:
   - `portfolio_manager.py`: How candidate fund pool (Tab 1) and holding diagnosis (Tab 2) are currently structured; how top 10 heavy holdings are retrieved and processed.
   - `strategy_bridge.py`: How macro indicators, HS300 moving averages, ERP (equity risk premium), and asset allocation signals are computed.
   - `app_gui.py`: How Streamlit UI is organized (top status bar, tabs, metric cards, radar charts, styling, port 8501 requirements).
2. Examine the test setup:
   - Inspect `d:\Google\Workspace\Wind\AGY2_FundAdvisory\tests/`. How many tests exist? How are they run (e.g. pytest command, environment, dependencies)?
   - Verify the current pass rate of the existing 112 tests.
3. Check Read-Only Invariants:
   - Check file permissions and contents of `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, and any benchmarks. Confirm they are strictly read-only and what checks enforce this.
4. Check Offline DuckDB Lakehouse:
   - How is DuckDB currently integrated? Where are local database/cache files located? What tables or parquet files exist?
5. Write your comprehensive findings to `d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_2\handoff.md`.
6. Send a message to parent (Recipient: 5fd996d1-bc98-447a-9f35-c5aef5be2e1c) stating you have completed your report.

SCOPE BOUNDARIES:
- Read-only! DO NOT modify any code or test files.
- Write files ONLY to your working directory: `d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_2`.
