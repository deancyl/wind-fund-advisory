# Task Assignment: Worker Prod M1 (Features 1-5: Real Open Data Foundation & Persistent Cache)

## Authoritative Request File
`d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md` (MUST read completely before proceeding)
`d:\Google\Workspace\Wind\.agents\teamwork\orchestrator\PROJECT.md` (Master Architecture & Milestone Contracts)
`d:\Google\Workspace\Wind\GEMINI.md` (Workspace Rules & Invariants)

## Explorer Input Reports
1. Explorer M1-1 Report: `d:\Google\Workspace\Wind\.agents\teamwork\explorer_m1_1\report.md` (Market Breadth & Index Valuation)
2. Explorer M1-2 Report: `d:\Google\Workspace\Wind\.agents\teamwork\explorer_m1_2\report.md` (Fund Purchase Quota Parquet & Metadata)
3. Explorer M1-3 Report: `d:\Google\Workspace\Wind\.agents\teamwork\explorer_m1_3\report.md` (Screener Bug Fix & Integration Verification)

## Exclusive Write Ownership
You exclusively own and may modify:
- `AGY2_FundAdvisory/data_loader.py`
- `AGY2_FundAdvisory/cache_manager.py`
- `AGY2_FundAdvisory/market_screener.py`
- `AGY2_FundAdvisory/portfolio_manager.py`
- `AGY2_FundAdvisory/portfolio_optimizer.py`
- `AGY2_FundAdvisory/app_gui.py`
- `data/cache/` (creation of cache files)

## Physical Safety Redline (STRICTLY FORBIDDEN TO TOUCH)
- `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py` (ZERO MODIFICATIONS, SHA-256 LOCKED).

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Detailed Requirements for Implementation
1. **东财真实市场宽度与两市量能 (Feature 1)**:
   - Call `https://push2.eastmoney.com/api/qt/ulist.np/get?secids=1.000001,0.399001&fields=f12,f14,f2,f3,f4,f6,f104,f105,f106`.
   - Calculate total turnover (sum of f6), up_count (f104), down_count (f105), flat_count (f106), up_pct.
   - Completely delete any remaining `3210 / 1780` constants in code.
   - Cache to `data/cache/market_breadth.json` with fallback protection.
2. **真实指数与行业估值分位数引擎 (Feature 2)**:
   - Fetch real PE-TTM and CSI valuation data using akshare/CSI interfaces combined with local history.
   - Calculate latest PE-TTM, PB, dividend yield, and 10-year percentiles for core broad-base and key sector indices.
   - Persist to `data/cache/index_valuation.json`.
   - Completely eliminate and purge `INDEX_PE_METAS` static dictionary across the codebase.
3. **全市场基金真实限购金额与 Parquet 缓存 (Feature 3)**:
   - Persist `ak.fund_purchase_em()` to `data/cache/fund_purchase.parquet` (columns: `['基金代码', '申购状态', '赎回状态', '日累计限定金额']`).
   - Ensure local disk read < 50ms (<0.5s cold start requirement).
   - Wire into `portfolio_manager.py` and `portfolio_optimizer.py` to ensure daily limit filtering logic operates on real data.
   - Offline fallback: smooth degradation to `data/master/fund_trading_rules.parquet`.
4. **基金本体排雷与季报重仓元数据 (Feature 4)**:
   - Extract metadata via Tiantian Fund API (`http://fund.eastmoney.com/pingzhongdata/{code}.js`):
     * AUM scale (<0.5亿 liquidation risk warning)
     * Manager tenure and return
     * Quarterly asset allocation (stock/bond/cash)
     * Top 10 heavy stock holdings
   - 24h TTL cache in `data/cache/funds/{code}_meta.json`, with offline fallback.
5. **修复 `market_screener.py` 成立日期 Bug (Feature 5)**:
   - Fix missing `inception_date` in `ak.fund_name_em()`.
   - Prevent empty candidate pool; restore 7,000+ candidates.
   - Prevent 0-row cache pollution in `cache_manager.py`.

## Verification Commands
After implementing, you MUST run tests:
- `py -3 -m pytest tests/test_infra.py` (Must pass 14/14)
- `cmd /c "set PYTHONPATH=AGY2_FundAdvisory;. && py -3 -m pytest AGY2_FundAdvisory/tests/test_deep_remodel_final.py -v"`
- `cmd /c "set PYTHONPATH=AGY2_FundAdvisory;. && py -3 -m pytest AGY2_FundAdvisory/tests/test_infra.py -v"`
- Confirm `INDEX_PE_METAS` and `3210 / 1780` are nowhere in codebase.
- Confirm `git status --porcelain judge_engine.py holdout_vault.py AGENT_SPEC.md tests/test_infra.py` is clean.

## Output Requirements
Write your detailed implementation report to:
`d:\Google\Workspace\Wind\.agents\teamwork\worker_prod_m1\handoff.md`
Then call `send_message` to parent.


## 2026-11-04T10:00:25Z
You are Worker Prod M1 for Milestone 1 (Features 1-5: Real Open Data Foundation & Persistent Cache).
Working directory: d:\Google\Workspace\Wind\.agents\teamwork\worker_prod_m1/
Read your task dispatch file: d:\Google\Workspace\Wind\.agents\teamwork\worker_prod_m1\DISPATCH.md
Read the authoritative request file: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
Read master architecture: d:\Google\Workspace\Wind\.agents\teamwork\orchestrator\PROJECT.md
Read workspace rules: d:\Google\Workspace\Wind\GEMINI.md
Read Explorer M1-1 Report: d:\Google\Workspace\Wind\.agents\teamwork\explorer_m1_1\report.md
Read Explorer M1-2 Report: d:\Google\Workspace\Wind\.agents\teamwork\explorer_m1_2\report.md
Read Explorer M1-3 Report: d:\Google\Workspace\Wind\.agents\teamwork\explorer_m1_3\report.md
