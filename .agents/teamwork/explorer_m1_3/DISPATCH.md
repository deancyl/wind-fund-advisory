# Task Assignment: Explorer M1-3 (Market Screener Bug Fix & M1 Integration)

## Authoritative Request File
`d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md` (MUST read completely before proceeding)
`d:\Google\Workspace\Wind\.agents\teamwork\orchestrator\PROJECT.md` (Master Architecture & Milestone Contracts)
`d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r7_2\report.md` (Survey findings for R2)

## Scope & Objective
You are Explorer M1-3 for Milestone 1 (Feature 5 & M1 Integration):
1. **修复 `market_screener.py` 成立日期 Bug**:
   - `ak.fund_name_em()` only returns `['基金代码', '拼音缩写', '基金简称', '基金类型', '拼音全称']` without `成立日期`.
   - Lines 258-261 fail or assign NaT, causing `cutoff_date` filtering on line 166 to drop all funds to 0.
   - Investigate best fix: e.g. merge with `ak.fund_scale_open_sina()` or read from `data/master/` or graceful fallback if `inception_date` is missing so that valid candidates are never dropped to 0.
2. **M1 Integration & Verification Pipeline**:
   - Verify how M1 components (`data_loader.py`, `market_screener.py`, `cache_manager.py`) interact.
   - Ensure cold start < 0.5s requirement is 100% satisfied.
   - Check existing tests in `AGY2_FundAdvisory/tests/` (e.g., `test_deep_remodel_final.py`, `test_design_system_v19.py`, `test_infra.py`) to make sure M1 changes do not break any existing test assertions.
   - Verify read-only referee files (`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`) are strictly preserved.

## Working Directory
`d:\Google\Workspace\Wind\.agents\teamwork\explorer_m1_3/`

## Output Requirements
Produce a concrete, line-by-line implementation strategy and precise code diffs in:
`d:\Google\Workspace\Wind\.agents\teamwork\explorer_m1_3\report.md`
And a 5-component handoff report in:
`d:\Google\Workspace\Wind\.agents\teamwork\explorer_m1_3\handoff.md`
When done, notify parent via `send_message`. You are read-only; DO NOT modify any source code files.

## 2026-11-04T09:44:44Z
[Message] timestamp=2026-11-04T09:44:44Z sender=c98181d5-8d61-4839-8d62-5dbcef7c85af priority=MESSAGE_PRIORITY_HIGH content=You are Explorer M1-3 for Milestone 1 (Feature 5 & M1 Integration: Screener Inception Bug & Test Verification).
Working directory: d:\Google\Workspace\Wind\.agents\teamwork\explorer_m1_3/
Read your task dispatch file: d:\Google\Workspace\Wind\.agents\teamwork\explorer_m1_3\DISPATCH.md
Read the authoritative request file: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
Read master architecture: d:\Google\Workspace\Wind\.agents\teamwork\orchestrator\PROJECT.md
Read survey report: d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r7_2\report.md
Read d:\Google\Workspace\Wind\GEMINI.md for workspace rules.
