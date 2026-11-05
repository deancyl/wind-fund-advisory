# BRIEFING — 2026-11-05T16:28:00Z

## Mission
Investigate Section 1 of ORIGINAL_REQUEST.md: 4 financial facts & regulatory compliance issues (dividend low-vol index error, QDII clearing rules & valuation confidence labels, eliminate non-compliant "保本" wording, harmonize 14 sector momentum/bias price index basis).

## 🔒 My Identity
- Archetype: explorer
- Roles: Financial & Regulatory Facts Explorer
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r10_1
- Original parent: f7b8d799-910f-4e70-94f5-3538a52207de
- Milestone: survey_r10

## 🔒 Key Constraints
- Read-only technical investigation — do NOT modify source code files.
- DO NOT run build/test execution yourself.
- Write findings to handoff.md and analysis.md in working directory.
- Report back to caller via send_message with handoff.md path and summary.

## Current Parent
- Conversation ID: f7b8d799-910f-4e70-94f5-3538a52207de
- Updated: 2026-11-05T16:28:00Z

## Investigation State
- **Explored paths**:
  - `AGY2_FundAdvisory/advisory_engine.py` (RADAR_SECTOR_CATALOG, _calc_dynamic_sector_metrics, get_sector_valuation_percentile)
  - `AGY2_FundAdvisory/data_loader.py` (IndexValuationEngine, calc_offline_2day_return, EXPANDED_INDEX_CATALOG)
  - `AGY2_FundAdvisory/trading_clock_fee.py` (TradingClock, FeeMatrixCalculator, calculate_settlement_dates)
  - `AGY2_FundAdvisory/portfolio_manager.py` (calculate_rebalance_routes, calculate_rebalance_net_utility, export_snapshot_df, PendingOrder)
  - `AGY2_FundAdvisory/strategy_bridge.py` (consequences, in_transit_risk, route matching)
  - `AGY2_FundAdvisory/app_gui.py` (Tab 1 blueprint table, Tab 2 data_editor & reconciliation center, winrate cards)
  - Local Parquet databases and DuckDB tables
- **Key findings**:
  1. `000978` is CSI Medicine 100, erroneously used in `advisory_engine.py:29,31` for dividend low-vol. `csindex_H30269.parquet` exists with 2,139 rows up to 2026-10-27. `data_loader.py:225` has alias `000978` which must be purged.
  2. US QDII funds (050025, 001071) lack T+2 confirm / T+6~T+8 arrival tags. Same-company conversion currently erroneously matches QDII if fund company is identical (e.g. Bosera). QDII must be excluded from T+1 conversion and domestic T+2 step-out risk. Valuation confidence labels needed across Tab 1 & Tab 2: 指数高准度 / 债基看久期票息 / 美股休市·看隔夜期指 / 季报重仓估算.
  3. "保本率" appears on UI in `app_gui.py:2728, 2736`. Must be replaced by "正收益概率 (≥0%)" or "本金安全率". `winrate_engine.py:70`, `strategy_bridge.py:4684`, `src/analysis/market_temperature.py:164` also updated. Legal negative disclaimers preserved.
  4. Total return indices (H00922, H30269) produce fake positive Bias20 pulses during May-July dividend season. `RADAR_SECTOR_CATALOG["dividend_low_vol"]` needs `fallback_parquet` pointed to `csindex_H30269.parquet`. Dynamic dividend smoothing needed in `_calc_dynamic_sector_metrics`.
- **Unexplored areas**: None for Section 1. All objectives fully investigated.

## Key Decisions Made
- All findings and step-by-step proposals documented in `analysis.md` and `handoff.md`. Ready to dispatch to caller.

## Artifact Index
- d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r10_1\DISPATCH.md — Incoming task dispatch record
- d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r10_1\BRIEFING.md — Persistent working memory
- d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r10_1\progress.md — Liveness heartbeat
- d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r10_1\analysis.md — Detailed technical analysis
- d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r10_1\handoff.md — 5-component handoff report
