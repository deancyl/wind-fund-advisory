## 2026-11-08T15:52:40Z
[Message] timestamp=2026-11-08T15:52:40Z sender=e873dbb9-9906-41d0-83a7-8e9eb7aaf59a priority=MESSAGE_PRIORITY_HIGH content=You are teamwork_worker for Milestone 2 of G12 Generation.
Your Identity: teamwork_worker
Your Working Directory: d:\Google\Workspace\Wind\.agents\teamwork\worker_g12_m2\
Authoritative Request: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
Scope Document: d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_16\PROJECT.md
Survey & Architecture Report: d:\Google\Workspace\Wind\.agents\teamwork\explorer_g12_survey_2\handoff.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your exclusive write ownership:
- AGY2_FundAdvisory/advisory_engine.py (ActiveRiskSentry Dimension 4)
- AGY2_FundAdvisory/data_loader.py (auto_heal_sector_parquets, fetch_sector_core_etf_metrics, fetch_macro_cross_market_indicators, calc_financial_news_sentiment)
- AGY2_FundAdvisory/app_gui.py (morning brief card leading indicators & sentiment display, tab2 take profit ratio linkage)
- tests/test_g12_stop_profit_and_sensors.py (new test file)

Tasks:
1. In `AGY2_FundAdvisory/advisory_engine.py` ActiveRiskSentry Dimension 4 (lines ~1706-1776):
   - Add right-side breakdown exit: when pnl_pct >= 10.0% and bias_20 < 0.0 and (slope_20 < 0.0 or single_day_drop > 1.5 * daily_vol), trigger RED alert "移动止盈" with action_type: "take_profit", take_profit_ratio: 0.50.
   - Add high-water mark drawdown protection: when pnl_pct >= 10.0% and 60-day HWM drawdown >= 8.0%, trigger YELLOW alert "移动止盈" with take_profit_ratio: 0.40.
   - Retain existing overbought (>6%) and laddered profit (>15% and bias >5%) branches.
2. In `AGY2_FundAdvisory/app_gui.py`:
   - Line ~3098: read dynamic take_profit_ratio from alert (st.session_state.tab2_pending_take_profit = {"fund_code": fcode, "ratio": alert.get("take_profit_ratio", 0.40)}).
   - In double-wing morning brief card (lines ~2869): compact render of sentiment score (0-100) and macro cross-market indicators (10Y bond, gold, Nasdaq).
3. In `AGY2_FundAdvisory/data_loader.py`:
   - Implement `auto_heal_sector_parquets()`: detect when fallback sector parquets lag behind latest closed trading day, fetch missing daily candles atomically.
   - Implement `fetch_sector_core_etf_metrics()`: 14 core ETF realtime metrics (Volume Surge Ratio f10, discount/premium).
   - Implement `fetch_macro_cross_market_indicators()`: 10Y China bond yield, gold ETF, overnight Nasdaq.
   - Implement `calc_financial_news_sentiment(news_items)`: output 0-100 sentiment score and label using financial polarity lexicon.
4. Create `tests/test_g12_stop_profit_and_sensors.py` covering all new functionality and edge cases.
5. Run tests:
   - py -3 -m pytest tests/test_infra.py (verify 0 changes to referee files)
   - py -3 -m pytest tests/test_g12_stop_profit_and_sensors.py
   - py -3 -m pytest tests/test_g12_circuit_breakers_and_sentry.py
   - py -3 -m pytest tests/test_adv_final_closure.py
6. Deliver handoff report to `d:\Google\Workspace\Wind\.agents\teamwork\worker_g12_m2\handoff.md` and message orchestrator.
Do NOT modify global GEMINI.md. Do NOT touch the 4 read-only referee files.


## 2026-11-08T16:03:01Z
[Message] timestamp=2026-11-08T16:03:01Z sender=e873dbb9-9906-41d0-83a7-8e9eb7aaf59a priority=MESSAGE_PRIORITY_HIGH content=**Context**: Milestone 2 Implementation (Trailing Stop-Profit & Sensors)
**Content**: 10 minutes have elapsed since dispatch. Checking in on your implementation progress across Tasks 1-4.
**Action**: Please report your current status, update progress.md, and let us know if you need any guidance or have any blockers.
