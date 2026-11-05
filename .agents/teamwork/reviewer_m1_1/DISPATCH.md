# Task Assignment: Reviewer M1-1 (Data Engine & Cache Integrity Reviewer)

## Authoritative Request File
`d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md` (MUST read completely before proceeding)
`d:\Google\Workspace\Wind\.agents\teamwork\orchestrator\PROJECT.md` (Master Architecture & Milestone Contracts)
`d:\Google\Workspace\Wind\GEMINI.md` (Workspace Rules)
`d:\Google\Workspace\Wind\.agents\teamwork\worker_prod_m1\handoff.md` (Worker M1 Handoff Report)

## Scope & Review Objective
Perform an independent, objective review and verification of Milestone 1 (Features 1-5):
1. Code verification in `AGY2_FundAdvisory/data_loader.py` and `cache_manager.py`:
   - Feature 1: Confirm EastMoney `f6, f104, f105, f106` implementation, complete deletion of `3210/1780` fake constants.
   - Feature 2: Confirm `IndexValuationEngine`, dynamic percentiles, and complete purging of `INDEX_PE_METAS`.
   - Feature 3: Confirm `FundPurchaseCacheManager`, parquet cache in `data/cache/fund_purchase.parquet` with read latency < 50ms, and wiring into `portfolio_manager.py` / `portfolio_optimizer.py`.
   - Feature 4: Confirm `FundMetadataManager`, Tiantian Fund API extraction (AUM liquidation check <0.5亿, manager tenure, quarterly assets, top 10 stocks), 24h TTL cache, and offline fallback.
2. Run automated test commands:
   - `py -3 -m pytest tests/test_infra.py`
   - `cmd /c "set PYTHONPATH=AGY2_FundAdvisory;. && py -3 -m pytest AGY2_FundAdvisory/tests/test_m1_open_data_and_cache.py -v"`
   - `cmd /c "set PYTHONPATH=AGY2_FundAdvisory;. && py -3 -m pytest AGY2_FundAdvisory/tests/test_infra.py -v"`
3. Verify referee files SHA-256 hashes are untouched (`tests/test_infra.py`, `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`).
4. Give a clear verdict: `APPROVE` or `REQUEST_CHANGES`.

## Working Directory
`d:\Google\Workspace\Wind\.agents\teamwork\reviewer_m1_1/`

## Output Requirements
Write your full review report to:
`d:\Google\Workspace\Wind\.agents\teamwork\reviewer_m1_1\handoff.md`
Then call `send_message` to parent.

## 2026-11-04T10:23:55Z
You are Reviewer M1-1 for Milestone 1.
Working directory: d:\Google\Workspace\Wind\.agents\teamwork\reviewer_m1_1/
Read your task dispatch file: d:\Google\Workspace\Wind\.agents\teamwork\reviewer_m1_1\DISPATCH.md
Read the authoritative request file: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
Read master architecture: d:\Google\Workspace\Wind\.agents\teamwork\orchestrator\PROJECT.md
Read Worker Prod M1 Handoff: d:\Google\Workspace\Wind\.agents\teamwork\worker_prod_m1\handoff.md
Read workspace rules: d:\Google\Workspace\Wind\GEMINI.md

Examine correctness, completeness, and robustness of Features 1-4 (data_loader.py, cache_manager.py, portfolio_manager.py).
Run test commands:
- py -3 -m pytest tests/test_infra.py
- cmd /c "set PYTHONPATH=AGY2_FundAdvisory;. && py -3 -m pytest AGY2_FundAdvisory/tests/test_m1_open_data_and_cache.py -v"
- cmd /c "set PYTHONPATH=AGY2_FundAdvisory;. && py -3 -m pytest AGY2_FundAdvisory/tests/test_infra.py -v"
Verify referee file SHA-256 hashes.
Write your review report and clear verdict (APPROVE or REQUEST_CHANGES) to:
d:\Google\Workspace\Wind\.agents\teamwork\reviewer_m1_1\handoff.md
Notify parent when done via send_message. You are read-only; DO NOT modify any source code files.
