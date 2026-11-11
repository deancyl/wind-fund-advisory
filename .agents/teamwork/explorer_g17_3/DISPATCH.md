# Task Assignment for Explorer G17-3

## Role
Backtest, Friction Bill, Screenshot & Safety Explorer

## Objectives
1. Inspect `portfolio_manager.py` long screenshot matching:
   - In `fuzzy_match_fund_by_name` and `parse_long_screenshot_holdings`:
     - Problem: Mobile screenshots often truncate fund names with ellipsis `...`.
     - Requirement: Add "name keyword + yesterday return (`yesterday_pnl / (market_value - yesterday_pnl)`) dual-factor cross-check" to accurately identify the fund among 28,177 mutual funds.
     - Support searching/editing questionable funds in the import preview table.
2. Inspect Tab 3 in `strategy_bridge.py` and `app_gui.py`:
   - In Tab 3 historical blind test and 29-fund portfolio restructuring backtest:
     - Add "🧾 中国公募交易规则全真摩擦扣减明细栏" (clearly listing cumulative subscription fee, redemption fee, C-class service fee, T+1/T+2 in-transit loss, and quota split counts).
     - Verify restructured portfolio advantages: net profit enhancement, max drawdown reduction, break-even days reduction compared to original 29-fund portfolio.
3. Verify Physical Safety Redlines:
   - Verify SHA-256 hashes and integrity of:
     - `judge_engine.py`
     - `holdout_vault.py`
     - `AGENT_SPEC.md`
     - `tests/test_infra.py`
   - Verify that `DataLoader.simulate_execution` signature and default fee logic are untouched.
4. Plan verification and test architecture:
   - Unit tests to be added (Delta test suite `tests/test_g17_*.py`).
   - AppTest UI regression tests.
   - Dual-viewport browser verification plan (1920x1080 desktop and 390x844 mobile).
   - Git tagging `v4.7-G17` and G18 directive output constraints (strictly no colon `slashCommand:`).
5. Write your comprehensive analysis report to `.agents/teamwork/explorer_g17_3/analysis.md`.


## 2026-11-11T14:21:29Z
You are an Explorer for the G17 generation.
Read your task description in: d:\Google\Workspace\Wind\.agents\teamwork\explorer_g17_3\DISPATCH.md
Also read ORIGINAL_REQUEST.md: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
Your state folder: d:\Google\Workspace\Wind\.agents\teamwork\explorer_g17_3\
Write your analysis to: d:\Google\Workspace\Wind\.agents\teamwork\explorer_g17_3\analysis.md
When finished, send a brief message to parent with your summary and handoff report path.
DO NOT write or modify implementation code. You are an Explorer (read-only investigation).
Follow all workspace rules in GEMINI.md.
