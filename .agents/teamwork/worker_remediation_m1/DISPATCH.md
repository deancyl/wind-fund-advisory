# Task Assignment: Worker Remediation M1 (Fund Purchase Cache Cold Start Latency Optimization)

## Authoritative Request File
`d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md` (MUST read completely before proceeding)
`d:\Google\Workspace\Wind\.agents\teamwork\orchestrator\PROJECT.md` (Master Architecture & Milestone Contracts)
`d:\Google\Workspace\Wind\GEMINI.md` (Workspace Rules)
`d:\Google\Workspace\Wind\.agents\teamwork\challenger_m1_1\handoff.md` (Challenger M1-1 Defect Report)

## Scope & Objective
Challenger M1-1 found that `FundPurchaseCacheManager.get_fund_quota` cold start time averages 113ms, exceeding the strict `< 50ms` requirement in `PROJECT.md` & `ORIGINAL_REQUEST.md`.
Test failure: `AGY2_FundAdvisory/tests/test_challenger_m1_adversarial.py::test_fund_purchase_cache_cold_start_under_50ms`.

### Root Cause
In `AGY2_FundAdvisory/cache_manager.py:476-491`, `_update_memory_cache` iterates 27,964 rows via pure Python `itertuples(index=False)`:
```python
records = {}
for row in df.itertuples(index=False):
    code = getattr(row, "基金代码", "")
    ...
```
This takes ~110ms.

### Remediation Plan
Optimize `_update_memory_cache` using vectorized operations or indexing:
For example:
```python
# Convert directly or use fast column-oriented extraction:
codes = df["基金代码"].astype(str).str.zfill(6).values
buy_status = df["申购状态"].astype(str).values
redeem_status = df["赎回状态"].astype(str).values
daily_limits = df["日累计限定金额"].values

records = {
    c: {
        "buy_status": b,
        "redeem_status": r,
        "daily_limit": None if (pd.isna(d) or d is None or str(d).strip() in ("", "nan", "None", "--")) else float(d)
    }
    for c, b, r, d in zip(codes, buy_status, redeem_status, daily_limits)
}
```
Or use `df.set_index("基金代码")` with fast `.loc` lookup or vectorized dictionary comprehension.
Verify that:
1. `FundPurchaseCacheManager.get_fund_quota(code)` executes cold start in < 30ms (strictly < 50ms).
2. `py -3 -m pytest AGY2_FundAdvisory/tests/test_challenger_m1_adversarial.py -v` passes 100%.
3. `py -3 -m pytest AGY2_FundAdvisory/tests/test_m1_open_data_and_cache.py -v` passes 100%.
4. `py -3 -m pytest tests/test_infra.py` passes 14/14.
5. All 5 referee files remain 100% untouched.

## Exclusive Write Ownership
`AGY2_FundAdvisory/cache_manager.py`

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. Integrity violations WILL be detected and your work WILL be rejected.

## Output Requirements
Write your remediation report with before/after benchmark results to:
`d:\Google\Workspace\Wind\.agents\teamwork\worker_remediation_m1\handoff.md`
Then call `send_message` to parent.


## 2026-11-04T10:37:48Z
You are Worker Remediation M1.
Working directory: d:\Google\Workspace\Wind\.agents\teamwork\worker_remediation_m1/
Read your task dispatch file: d:\Google\Workspace\Wind\.agents\teamwork\worker_remediation_m1\DISPATCH.md
Read the authoritative request file: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
Read master architecture: d:\Google\Workspace\Wind\.agents\teamwork\orchestrator\PROJECT.md
Read Challenger M1-1 Report: d:\Google\Workspace\Wind\.agents\teamwork\challenger_m1_1\handoff.md
Read workspace rules: d:\Google\Workspace\Wind\GEMINI.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

PHYSICAL SAFETY REDLINE:
judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py are STRICTLY READ-ONLY. Do NOT modify them under any circumstances.

Your Task:
Optimize FundPurchaseCacheManager._update_memory_cache in AGY2_FundAdvisory/cache_manager.py:476-491.
Eliminate itertuples row-by-row iteration overhead. Use vectorized column zip or indexing so that FundPurchaseCacheManager.get_fund_quota cold start latency drops from 113ms to < 25ms (strictly < 50ms).
Run verification:
- py -3 -m pytest AGY2_FundAdvisory/tests/test_challenger_m1_adversarial.py -v (All tests including test_fund_purchase_cache_cold_start_under_50ms MUST pass!)
- py -3 -m pytest AGY2_FundAdvisory/tests/test_m1_open_data_and_cache.py -v
- py -3 -m pytest tests/test_infra.py
- Verify referee file SHA-256 hashes are untouched.

Write handoff report with exact timing benchmarks to:
d:\Google\Workspace\Wind\.agents\teamwork\worker_remediation_m1\handoff.md
Notify parent when done via send_message.
