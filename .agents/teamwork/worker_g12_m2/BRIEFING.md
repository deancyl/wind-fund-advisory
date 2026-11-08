# BRIEFING — 2026-11-08T16:11:45Z

## Mission
Implement Milestone 2 of G12 Generation: ActiveRiskSentry Dim 4 dynamic stop-profit rules, sector parquet auto-healing, core ETF metrics, cross-market indicators, financial news sentiment, and morning brief card display.

## 🔒 My Identity
- Archetype: teamwork_worker
- Roles: implementer, qa, specialist
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\worker_g12_m2\
- Original parent: e873dbb9-9906-41d0-83a7-8e9eb7aaf59a
- Milestone: Milestone 2 (G12 Generation)

## 🔒 Key Constraints
- Do NOT cheat, fabricate, hardcode test outputs or mock shortcuts.
- Exclusive write ownership:
  - AGY2_FundAdvisory/advisory_engine.py (ActiveRiskSentry Dimension 4)
  - AGY2_FundAdvisory/data_loader.py (auto_heal_sector_parquets, fetch_sector_core_etf_metrics, fetch_macro_cross_market_indicators, calc_financial_news_sentiment)
  - AGY2_FundAdvisory/app_gui.py (morning brief card leading indicators & sentiment display, tab2 take profit ratio linkage)
  - tests/test_g12_stop_profit_and_sensors.py (new test file)
- Do NOT modify global GEMINI.md.
- Do NOT touch the 4 referee files (test_infra.py etc.).
- Follow rules in workspace GEMINI.md.

## Current Parent
- Conversation ID: e873dbb9-9906-41d0-83a7-8e9eb7aaf59a
- Updated: 2026-11-08T16:03:43Z

## Task Summary
- **What to build**: Dynamic stop-profit rules (right-side breakdown 50%, 60-day HWM drawdown 40%), data loader auto healing & market sensors (core ETF metrics, cross-market indicators, news sentiment), app GUI morning brief compact card & tab2 dynamic ratio linkage, comprehensive test suite.
- **Success criteria**: All tests pass including test_infra, test_g12_stop_profit_and_sensors, test_g12_circuit_breakers_and_sentry, test_adv_final_closure.
- **Interface contracts**: PROJECT.md, survey handoff.md, ORIGINAL_REQUEST.md.
- **Code layout**: AGY2_FundAdvisory/

## Key Decisions Made
- Sentry Dim 4: right-side breakdown triggered when pnl >= 10.0%, bias_20 < 0, and (slope_20 < 0 or single_day_drop > 1.5 * daily_vol), emitting red alert with take_profit_ratio 0.50.
- Sentry Dim 4: 60-day HWM drawdown protection triggered when pnl >= 10.0% and hwm_dd >= 8.0%, emitting yellow alert with take_profit_ratio 0.40.
- data_loader auto_heal_sector_parquets: detects lag between fallback parquets and latest matrix close date, pulls daily candles from Eastmoney/matrix and writes atomically (.tmp + replace).
- data_loader sensors: 14 ETF metrics (f10 volume surge ratio), macro cross-market indicators (10Y bond, gold, Nasdaq), 0-100 financial news sentiment score & label.
- app_gui: dynamic take_profit_ratio linkage in tab2 jump; morning brief card renders sentiment score and macro indicators.

## Artifact Index
- `d:\Google\Workspace\Wind\AGY2_FundAdvisory\advisory_engine.py`
- `d:\Google\Workspace\Wind\AGY2_FundAdvisory\data_loader.py`
- `d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py`
- `d:\Google\Workspace\Wind\tests\test_g12_stop_profit_and_sensors.py`
- `d:\Google\Workspace\Wind\.agents\teamwork\worker_g12_m2\handoff.md`

## Change Tracker
- **Files modified**:
  - `AGY2_FundAdvisory/advisory_engine.py`: ActiveRiskSentry Dimension 4 trailing stop-profit & right-side breakdown exit
  - `AGY2_FundAdvisory/data_loader.py`: auto_heal_sector_parquets, fetch_sector_core_etf_metrics, fetch_macro_cross_market_indicators, calc_financial_news_sentiment
  - `AGY2_FundAdvisory/app_gui.py`: dynamic take_profit_ratio from alert, morning brief compact card sentiment & macro indicators
  - `tests/test_g12_stop_profit_and_sensors.py`: 13 comprehensive unit tests covering all tasks and edge cases
- **Build status**: All tests pass (14/14 test_infra, 13/13 test_g12_stop_profit_and_sensors, 11/11 test_g12_circuit_breakers_and_sentry, 14/14 test_adv_final_closure)
- **Pending issues**: None

## Quality Status
- **Build/test result**: PASS (52/52 tests total)
- **Lint status**: clean
- **Tests added/modified**: tests/test_g12_stop_profit_and_sensors.py (13 tests)

## Loaded Skills
- None
