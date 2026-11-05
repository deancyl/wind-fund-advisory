# Task Assignment: Explorer Survey r7_2 (Real Data Foundation & Persistent Cache)

## Authoritative Request File
`d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md` (MUST read completely before proceeding)

## Objective
Thoroughly explore the codebase for Requirement R2:
1. Real market breadth & turnover:
   - Investigate EastMoney interface: `push2.eastmoney.com/api/qt/ulist.np/get?secids=1.000001,0.399001`
   - Fields: `f6` (turnover), `f104` (up count), `f105` (down count), `f106` (flat count).
   - Locate where `3210 / 1780` hardcoded constants exist in `data_loader.py`, `app_gui.py`, or elsewhere, and how to completely purge them with fallback to local cache.
2. Real index & sector valuation percentiles:
   - Locate where `INDEX_PE_METAS` static dictionary is defined and used.
   - Investigate how `akshare` index valuation interfaces (`ak.stock_index_pe_lg()`, `ak.stock_zh_index_value_csindex()`) can be integrated with local historical market series.
   - How to dynamically calculate PE-TTM/PB/dividend yield & historical percentiles for core broad-base and key sector indices.
   - Investigate persistence caching mechanism in `data/cache/` (or `cache_manager.py`) to replace `INDEX_PE_METAS`.
3. Fund purchase limits and fund risk/metadata:
   - Check `ak.fund_purchase_em()` integration, caching to local parquet (`data/cache/fund_purchase.parquet` or similar).
   - Ensure daily purchase limit filtering logic operates on real data.
   - For candidate pool and held funds: investigate extracting asset scale (<0.5亿 liquidation risk), manager tenure & return, latest quarterly report real stock/bond allocation and top holdings via Tiantian Fund API or akshare, with local TTL cache in `data/cache/` (guaranteeing first-screen load < 0.5s) and offline fallback.

## Working Directory
`d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r7_2/`

## Output Requirements
Write comprehensive analysis, file locations, exact line numbers, and concrete implementation plan to:
`d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r7_2\report.md`
Then call `send_message` to parent.

## 2026-11-04T09:25:19Z
[Message] timestamp=2026-11-04T09:25:19Z sender=c98181d5-8d61-4839-8d62-5dbcef7c85af priority=MESSAGE_PRIORITY_HIGH content=You are Explorer Survey r7_2.
Working directory: d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r7_2/
Read your task dispatch file: d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r7_2\DISPATCH.md
Read the authoritative request file: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
Read d:\Google\Workspace\Wind\GEMINI.md for workspace rules.

Your focus is Requirement R2 (免费开源真实数据底座升级与持久化缓存):
1. Investigate AGY2_FundAdvisory/data_loader.py, market_screener.py, cache_manager.py, and app_gui.py.
2. Locate hardcoded constants (e.g. 3210 / 1780, INDEX_PE_METAS).
3. Investigate EastMoney interface: push2.eastmoney.com/api/qt/ulist.np/get?secids=1.000001,0.399001 for f6, f104, f105, f106. Design robust request with local cache fallback.
4. Investigate akshare interfaces for real index and sector valuation (ak.stock_index_pe_lg(), ak.stock_zh_index_value_csindex(), etc.) combined with local historical series, caching to data/cache/ to dynamically calculate PE-TTM/PB/dividend yield & historical percentiles.
5. Investigate fund purchase limits via ak.fund_purchase_em(), caching to local parquet in data/cache/, and connecting to daily purchase limit filter.
6. Investigate candidate pool and held fund metadata extraction (scale <0.5亿 check, manager tenure & return, quarterly report stock/bond asset allocation & top holdings) via Tiantian Fund API / akshare with TTL cache in data/cache/ (guaranteeing cold start <0.5s) and offline fallback.

Write your comprehensive findings and concrete implementation plan to:
d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r7_2\report.md
When done, notify parent via send_message. You are read-only; DO NOT modify any source code files.
