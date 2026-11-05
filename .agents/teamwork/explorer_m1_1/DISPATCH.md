# Task Assignment: Explorer M1-1 (Market Breadth & Index Valuation)

## Authoritative Request File
`d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md` (MUST read completely before proceeding)
`d:\Google\Workspace\Wind\.agents\teamwork\orchestrator\PROJECT.md` (Master Architecture & Milestone Contracts)
`d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r7_2\report.md` (Survey findings for R2)

## Scope & Objective
You are Explorer M1-1 for Milestone 1 (Features 1 & 2):
1. **东财两市真实成交额与涨跌家数**:
   - In `AGY2_FundAdvisory/data_loader.py` and `app_gui.py`:
   - Replace any remaining hardcoded `3210 / 1780` constants.
   - Implement `fetch_market_turnover_and_sentiment()` to call `https://push2.eastmoney.com/api/qt/ulist.np/get?secids=1.000001,0.399001&fields=f12,f14,f2,f3,f4,f6,f104,f105,f106`.
   - Calculate total turnover (sum of f6 in 亿元), up_count (sum of f104), down_count (sum of f105), flat_count (sum of f106), up_pct = up / (up+down+flat)*100.
   - Implement persistent caching to `data/cache/market_breadth.json` with 60s TTL and offline fallback.
2. **真实指数与行业估值分位数引擎**:
   - Implement `fetch_or_calc_index_valuations()` in `data_loader.py` / `cache_manager.py`.
   - Use `ak.stock_index_pe_lg()` / `ak.stock_zh_index_value_csindex()` combined with local series.
   - For core indices (000300, 000905, 000852, 000922, H30269, 000688, etc.), compute latest PE-TTM, 10-year percentile (%), label (e.g. "PE 12.7 (33%低估)"), status ("low"|"mid"|"high").
   - Persist to `data/cache/index_valuation.json`.
   - Completely purge and replace `INDEX_PE_METAS` static dictionary across the codebase.
   - Provide fallback to local historical series or `data/storage.duckdb:v_index_valuations` when offline.

## Working Directory
`d:\Google\Workspace\Wind\.agents\teamwork\explorer_m1_1/`

## Output Requirements
Produce a concrete, line-by-line implementation strategy and precise code diffs in:
`d:\Google\Workspace\Wind\.agents\teamwork\explorer_m1_1\report.md`
And a 5-component handoff report in:
`d:\Google\Workspace\Wind\.agents\teamwork\explorer_m1_1\handoff.md`
When done, notify parent via `send_message`. You are read-only; DO NOT modify any source code files.

## 2026-11-04T09:44:26Z
[Message] timestamp=2026-11-04T09:44:26Z sender=c98181d5-8d61-4839-8d62-5dbcef7c85af priority=MESSAGE_PRIORITY_HIGH content=You are Explorer M1-1 for Milestone 1 (Features 1 & 2: Real Market Breadth & Index Valuation Engine).
Working directory: d:\Google\Workspace\Wind\.agents\teamwork\explorer_m1_1/
Read your task dispatch file: d:\Google\Workspace\Wind\.agents\teamwork\explorer_m1_1\DISPATCH.md
Read the authoritative request file: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
Read master architecture: d:\Google\Workspace\Wind\.agents\teamwork\orchestrator\PROJECT.md
Read survey report: d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r7_2\report.md
Read d:\Google\Workspace\Wind\GEMINI.md for workspace rules.

Your task:
1. Formulate exact code modifications in AGY2_FundAdvisory/data_loader.py and app_gui.py to fetch real market turnover and up/down/flat counts from EastMoney push2 API (f6, f104, f105, f106), eliminating hardcoded 3210/1780, with data/cache/market_breadth.json persistent cache and fallback.
2. Formulate exact code modifications to compute real PE-TTM and 10-year percentiles using akshare/CSI interfaces for core indices (000300, 000905, 000852, 000922, H30269, 000688, etc.), caching to data/cache/index_valuation.json, and replacing INDEX_PE_METAS.
3. Write your report with concrete line numbers and code diffs to:
d:\Google\Workspace\Wind\.agents\teamwork\explorer_m1_1\report.md
and handoff to:
d:\Google\Workspace\Wind\.agents\teamwork\explorer_m1_1\handoff.md
Notify parent when done via send_message. You are read-only; DO NOT modify any source code files.
