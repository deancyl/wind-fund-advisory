# Task Assignment: Explorer M1-2 (Fund Purchase Quota & Screening Metadata)

## Authoritative Request File
`d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md` (MUST read completely before proceeding)
`d:\Google\Workspace\Wind\.agents\teamwork\orchestrator\PROJECT.md` (Master Architecture & Milestone Contracts)
`d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r7_2\report.md` (Survey findings for R2)

## Scope & Objective
You are Explorer M1-2 for Milestone 1 (Features 3 & 4):
1. **全市场基金真实限购金额与 Parquet 缓存**:
   - In `AGY2_FundAdvisory/cache_manager.py` / `data_loader.py`:
   - Fetch fund purchase status and daily quota via `ak.fund_purchase_em()`.
   - Persist to `data/cache/fund_purchase.parquet` (columns: `基金代码`, `申购状态`, `赎回状态`, `日累计限定金额`).
   - Benchmark and ensure local read time < 50ms (<0.5s cold start requirement).
   - Wire with `portfolio_manager.py` and `portfolio_optimizer.py` to ensure daily limit filtering logic operates on real data.
   - Offline fallback: fallback to `data/master/fund_trading_rules.parquet`.
2. **基金本体排雷与季报重仓元数据**:
   - For candidate pool and held funds:
   - Extract metadata via Tiantian Fund API (`http://fund.eastmoney.com/pingzhongdata/{code}.js`) or akshare:
     * Latest fund AUM (`Data_fluctuationScale`): flag liquidation risk if < 0.5 亿元.
     * Current manager (`Data_currentFundManager`): name, tenure, term return.
     * Quarterly asset allocation (`Data_assetAllocation`): stock %, bond %, cash %.
     * Top 10 heavy holdings (`stockCodesNew`).
   - Implement local 24h TTL cache in `data/cache/funds/{code}_meta.json`.
   - Provide offline fallback to local DuckDB / historical parquet.

## Working Directory
`d:\Google\Workspace\Wind\.agents\teamwork\explorer_m1_2/`

## Output Requirements
Produce a concrete, line-by-line implementation strategy and precise code diffs in:
`d:\Google\Workspace\Wind\.agents\teamwork\explorer_m1_2\report.md`
And a 5-component handoff report in:
`d:\Google\Workspace\Wind\.agents\teamwork\explorer_m1_2\handoff.md`
When done, notify parent via `send_message`. You are read-only; DO NOT modify any source code files.


## 2026-11-04T09:44:34Z
You are Explorer M1-2 for Milestone 1 (Features 3 & 4: Fund Purchase Limit Parquet & Screening Metadata).
Working directory: d:\Google\Workspace\Wind\.agents\teamwork\explorer_m1_2/
Read your task dispatch file: d:\Google\Workspace\Wind\.agents\teamwork\explorer_m1_2\DISPATCH.md
Read the authoritative request file: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
Read master architecture: d:\Google\Workspace\Wind\.agents\teamwork\orchestrator\PROJECT.md
Read survey report: d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r7_2\report.md
Read d:\Google\Workspace\Wind\GEMINI.md for workspace rules.

Your task:
1. Formulate exact code modifications in AGY2_FundAdvisory/cache_manager.py and data_loader.py to persist ak.fund_purchase_em() to data/cache/fund_purchase.parquet (read time < 50ms) and connect to daily limit filtering in portfolio_manager.py and portfolio_optimizer.py, with offline fallback to data/master/fund_trading_rules.parquet.
2. Formulate exact code modifications to extract fund AUM (<0.5亿 liquidation risk), manager tenure & return, quarterly asset allocation (stock/bond/cash) and top 10 holdings via Tiantian Fund API with 24h TTL cache in data/cache/funds/{code}_meta.json and offline fallback.
3. Write your report with concrete line numbers and code diffs to:
d:\Google\Workspace\Wind\.agents\teamwork\explorer_m1_2\report.md
and handoff to:
d:\Google\Workspace\Wind\.agents\teamwork\explorer_m1_2\handoff.md
Notify parent when done via send_message. You are read-only; DO NOT modify any source code files.
