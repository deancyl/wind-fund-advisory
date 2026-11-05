# Task Assignment: Challenger M1-1 (Data Freshness, Latency & Fallback Stress Challenger)

## Authoritative Request File
`d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md` (MUST read completely before proceeding)
`d:\Google\Workspace\Wind\.agents\teamwork\orchestrator\PROJECT.md` (Master Architecture & Milestone Contracts)
`d:\Google\Workspace\Wind\GEMINI.md` (Workspace Rules)
`d:\Google\Workspace\Wind\.agents\teamwork\worker_prod_m1\handoff.md` (Worker M1 Handoff Report)

## Scope & Adversarial Challenge Objective
You are Challenger M1-1 for Milestone 1. Adversarially stress-test the data engine and caching layer:
1. **Cold Start & Latency Stress**:
   - Write a stress script or test to measure `FundPurchaseCacheManager.get_fund_quota` cold start time. Is it strictly < 50ms?
   - Measure `FundMetadataManager.get_fund_metadata` cached retrieval. Is it strictly < 5ms?
2. **Network Offline / Disconnection Simulation**:
   - Disconnect or mock failure of EastMoney push2 endpoint: does `fetch_market_turnover_and_sentiment` gracefully fallback to `data/cache/market_breadth.json` without throwing unhandled exceptions?
   - Disconnect or mock failure of `akshare`: does `fetch_or_calc_index_valuations` gracefully fallback without crashing?
3. **Absence of Fake Constants**:
   - Execute regex or AST scan across the entire repo (`AGY2_FundAdvisory/` and root):
     * Check if `3210` or `1780` exist in any market breadth logic.
     * Check if `INDEX_PE_METAS` exists anywhere in Python files.
4. Give a clear verdict: `APPROVE` or `REQUEST_CHANGES`.

## Working Directory
`d:\Google\Workspace\Wind\.agents\teamwork\challenger_m1_1/`

## Output Requirements
Write your full challenge report to:
`d:\Google\Workspace\Wind\.agents\teamwork\challenger_m1_1\handoff.md`
Then call `send_message` to parent.


## 2026-11-04T10:24:16Z
[Message] timestamp=2026-11-04T10:24:16Z sender=c98181d5-8d61-4839-8d62-5dbcef7c85af priority=MESSAGE_PRIORITY_HIGH content=You are Challenger M1-1 for Milestone 1.
Working directory: d:\Google\Workspace\Wind\.agents\teamwork\challenger_m1_1/
Read your task dispatch file: d:\Google\Workspace\Wind\.agents\teamwork\challenger_m1_1\DISPATCH.md
Read the authoritative request file: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
Read master architecture: d:\Google\Workspace\Wind\.agents\teamwork\orchestrator\PROJECT.md
Read Worker Prod M1 Handoff: d:\Google\Workspace\Wind\.agents\teamwork\worker_prod_m1\handoff.md
Read workspace rules: d:\Google\Workspace\Wind\GEMINI.md

Adversarially challenge Milestone 1:
1. Benchmark cold start and latency: verify FundPurchaseCacheManager read < 50ms, FundMetadataManager read < 5ms.
2. Test network offline / disconnection simulation: simulate failure of push2 EastMoney and akshare, verify graceful fallback without crashes.
3. Code scan: verify 3210/1780 and INDEX_PE_METAS are completely absent from codebase.
Write your challenge report and clear verdict (APPROVE or REQUEST_CHANGES) to:
d:\Google\Workspace\Wind\.agents\teamwork\challenger_m1_1\handoff.md
Notify parent when done via send_message. You are read-only; DO NOT modify any source code files.
