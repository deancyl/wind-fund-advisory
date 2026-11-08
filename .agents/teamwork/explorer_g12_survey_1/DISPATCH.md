## 2026-11-08T15:03:59Z

You are teamwork_explorer for Survey Phase of G12 Generation.
Your Identity: teamwork_explorer
Your Working Directory: d:\Google\Workspace\Wind\.agents\teamwork\explorer_g12_survey_1\
Authoritative Request: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md

Please read ORIGINAL_REQUEST.md first (under ## Follow-up — 2026-11-08T14:57:27Z and the latest sections).
Your investigation focuses on: 4 Circuit-Breaker Bugs & Sentry parameter penetration in app_gui.py, advisory_engine.py, portfolio_manager.py:
1. Bug 1: Right-wing correlation mutation card dead bug in app_gui.py around line 1480 (corr_eval_res keys `is_mutation_alarm` / `is_regime_shift_risk` vs actual keys `is_triggered` / `is_liquidity_shift_triggered`). Find exact lines, current code, return keys from advisory_engine.py, and exact fix required.
2. Bug 2: `sentry.inspect_portfolio` missing parameters in app_gui.py around line 1281 (and all other call sites). Needs `investor_risk_tier=st.session_state.get("active_tier_val", "C3")`, and inject `fund_quotes` into `snapshot_dict` so dimension 8 (suitability) and dimension 9 (intraday cushion transmission) activate.
3. Bug 3: Intraday valuation calibration for index funds and ETF feeders in portfolio_manager.py `fetch_realtime_fund_quote` and intraday PnL. Factor 0.95 for feeder funds, benchmark ETF/index realtime change chg_pct to calibrate gszzl, eliminating quarterly report lag.
4. Bug 4: Tab 1 `SmartExecutionDCAEngine.plan_smart_dca` multiplier alignment. In app_gui.py call to plan_smart_dca, compute weighted MA20 bias & ERP from selected portfolio funds rather than just HS300 alone.

Investigate the exact code in the workspace, locate line numbers, analyze dependencies, check any potential test breakages, and design complete, safe implementation steps.
Write your full findings and recommendations to:
`d:\Google\Workspace\Wind\.agents\teamwork\explorer_g12_survey_1\handoff.md`
Remember to update `progress.md` in your working directory.
When finished, send a message to the orchestrator summarizing your report path and key findings.

## 2026-11-08T15:15:52Z

**Context**: G12 Survey Phase Investigation
**Content**: Checking in on your survey status for the 4 Circuit-Breaker Bugs & Sentry Params. Explorer 2 and Explorer 3 have completed their reports.
**Action**: Please report your current progress or any blockers, update progress.md, and deliver handoff.md as soon as possible.
