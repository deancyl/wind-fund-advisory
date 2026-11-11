# Task Assignment for Explorer G17-1

## Role
Data & Quant Engine Explorer

## Objectives
1. Inspect lines 1549-1593 in `advisory_engine.py` (and `generate_chief_advisor_memo`) to identify all static fake constants and broken dictionary keys:
   - `snap.get("treasury_10y", 1.6258)`
   - `macro_multi.get("usdcnh_rate", 7.2450)`
   - `macro_multi.get("gold_price", 628.5)`
   - `macro_multi.get("nasdaq_change_pct", -0.25)`
   - Any other missing keys or fallback constants.
2. Investigate real data sources in the project:
   - `data/macro/bond_zh_us_rate.parquet`: check schema, available columns (`cn_yield_10y`, `us_yield_10y`), date range, 20-day bp calculation.
   - Gold and global equities: `data/processed/aligned_matrix_total_return.parquet`, `data/processed/indices/AU9999.SGE.parquet`, `data/global/global_indices.parquet` or real-time APIs (`fetch_realtime_gold_price` / `fetch_global_indices` / etc.).
   - USD/CNH: `DataLoader.fetch_realtime_usdcnh_fx(use_cache=True)` or related methods.
3. Design the implementation for:
   - Connecting `generate_chief_advisor_memo` to these real data sources with real date stamps and source attribution.
   - Adding `ten_dimension_votes` (covering ①宏观经济, ②货币政策, ③股债ERP, ④国际联动, ⑤外汇锁汇, ⑥产业估值, ⑦资金情绪, ⑧技术信噪比, ⑨历史同温层, ⑩期权IV与相关性黑天鹅) with scores and bull/bear vote totals.
   - Generating a transparent "position causal derivation formula" string (e.g. `基准权益中枢 60% + ERP极低估溢价(+10%) + 货币宽松(+5%) - 局部赛道超买约束(-5%) = 当前建议权益仓位 70%`).
4. Design unit test assertions:
   - Strictly forbid magic numbers `628.5` and `-0.25%`.
   - Ensure every indicator has real date and data source tags.
5. Write your comprehensive analysis report to `.agents/teamwork/explorer_g17_1/analysis.md`.


## 2026-11-11T14:21:20Z
You are an Explorer for the G17 generation.
Read your task description in: d:\Google\Workspace\Wind\.agents\teamwork\explorer_g17_1\DISPATCH.md
Also read ORIGINAL_REQUEST.md: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
Your state folder: d:\Google\Workspace\Wind\.agents\teamwork\explorer_g17_1\
Write your analysis to: d:\Google\Workspace\Wind\.agents\teamwork\explorer_g17_1\analysis.md
When finished, send a brief message to parent with your summary and handoff report path.
DO NOT write or modify implementation code. You are an Explorer (read-only investigation).
Follow all workspace rules in GEMINI.md.
