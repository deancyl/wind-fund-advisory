# BRIEFING — 2026-11-08T15:13:30Z

## Mission
Survey investigation for G12 Generation: Trailing Stop-Profit, Right-Side Breakdown Exit, Local Parquet Auto-Heal, and Multi-Source Leading Indicators.

## 🔒 My Identity
- Archetype: explorer
- Roles: Teamwork Explorer
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\explorer_g12_survey_2
- Original parent: e873dbb9-9906-41d0-83a7-8e9eb7aaf59a
- Milestone: G12 Survey Phase

## 🔒 Key Constraints
- Read-only investigation — do NOT implement production code
- Adhere to Wind workspace guidelines and rules
- Deliver structured handoff.md with 5-component protocol

## Current Parent
- Conversation ID: e873dbb9-9906-41d0-83a7-8e9eb7aaf59a
- Updated: 2026-11-08T15:05:00Z

## Investigation State
- **Explored paths**:
  - `AGY2_FundAdvisory/advisory_engine.py`: Lines 1454-2115 (`ActiveRiskSentry.inspect_portfolio`, dimension 4 lines 1706-1776, `OpportunityRadarEngine._calc_dynamic_sector_metrics` lines 768-995)
  - `AGY2_FundAdvisory/app_gui.py`: Lines 2710-3120 (Dual-wing advisory dashboard, action switch, sentry alert rendering, Tab 2 `tab2_pending_take_profit` linkage lines 4590-4623, 5390-5420)
  - `AGY2_FundAdvisory/data_loader.py`: Lines 62-200 (`fetch_market_turnover_and_sentiment`), 268-460 (`fetch_realtime_market_news_and_catalysts`), 1031-1260 (`sync_latest_market_data`), 2215-2350 (`fetch_custom_realtime_indices`)
  - `AGY2_FundAdvisory/cache_manager.py`: Lines 120-170 (`SmartCacheManager` nav cache)
  - `data/master/etf_catalog.parquet`, `data/macro/chinabond_yield_curve.parquet`, `data/processed/` parquets
  - Referee files: `AGY2_FundAdvisory/judge_engine.py`, `AGY2_FundAdvisory/holdout_vault.py`, `AGY2_FundAdvisory/AGENT_SPEC.md`, `tests/test_infra.py`
- **Key findings**:
  1. Dimension 4 in `ActiveRiskSentry`: currently only checks `bias_20 > 6.0` (超买) and `pnl_pct >= 15.0 and bias_20 > 5.0` (阶梯止盈). When profitable holdings break below MA20 on a large down candle, all alerts silence! Needs right-side breakdown exit (`pnl_pct >= 10.0`, `bias_20 < 0`, and (`slope < 0` or `single_day_drop > 1.5 * daily_vol`)) triggering red alert (50% profit lock-in), plus HWM drawdown protection (drawdown >= 8% from 60d peak NAV).
  2. Local daily line auto-heal in `data_loader.py`: `sync_latest_market_data` only updates `aligned_matrix_total_return.parquet`, leaving individual sector parquets (e.g. `000685.SH.parquet` max date 2026-10-26) 2 weeks behind. Needs auto-heal checking max date against latest closed trading day and fetching missing candles.
  3. Multi-source leading indicators: 14 core ETFs verified via Eastmoney push2 (`f10` volume ratio, price, IOPV/NAV premium rate); Macro indicators (10Y bond yield 1.62% from chinabond curve, Gold ETF 518880, Nasdaq overnight gb_ixic +1.09%); Financial news sentiment score (0-100) via polarity scoring on filtered news; Morning Brief rendering in double-wing header.
- **Unexplored areas**: None, full survey complete.

## Key Decisions Made
- Confirmed backward compatibility with all existing test suites.
- Formulated exact mathematical definitions and code insertion points.

## Artifact Index
- `d:\Google\Workspace\Wind\.agents\teamwork\explorer_g12_survey_2\DISPATCH.md`
- `d:\Google\Workspace\Wind\.agents\teamwork\explorer_g12_survey_2\BRIEFING.md`
- `d:\Google\Workspace\Wind\.agents\teamwork\explorer_g12_survey_2\progress.md`
- `d:\Google\Workspace\Wind\.agents\teamwork\explorer_g12_survey_2\handoff.md` (writing now)
