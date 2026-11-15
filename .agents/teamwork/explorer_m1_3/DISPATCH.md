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


## 2026-11-15T08:00:43Z
[Message] timestamp=2026-11-15T08:00:43Z sender=a29ecba0-a4ab-4a58-a8c7-4276082800c0 priority=MESSAGE_PRIORITY_HIGH content=You are Explorer 3 for Milestone 1 (M1: 十维真实投票与汇率校验及胶囊联动).
Working directory: d:\Google\Workspace\Wind
Your state folder: d:\Google\Workspace\Wind\.agents\teamwork\explorer_m1_3
Authoritative user request: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
Project plan: d:\Google\Workspace\Wind\PROJECT.md
Scope definition: d:\Google\Workspace\Wind\.agents\teamwork\sub_orch_m1\SCOPE.md

You are READ-ONLY. Do not modify source code or tests.
Read ORIGINAL_REQUEST.md and PROJECT.md and SCOPE.md first.

Your specific exploration focus is Feature 6 and Test Coverage / Compatibility:
6. 胶囊4（持仓病灶）与胶囊5（今日行动准则）知行合一联动：在 `generate_chief_advisor_memo` 与 `render_chief_advisor_memo_card` 中，当检测到当前账本存在免赎碎片尾仓或深套出血点或红牌止盈预警时，第五颗胶囊今日行动准则的主结论与副标题优先输出账户级实战指令（如清扫尾仓并置换深套出血点），消除割裂。

Please investigate:
- In `advisory_engine.py`, examine `generate_chief_advisor_memo` and `render_chief_advisor_memo_card`. How are the 5 capsules currently constructed and rendered?
- How does `generate_chief_advisor_memo` receive portfolio pathology? Does it currently take `portfolio_pathology` dict, or `pm` (PortfolioManager), or `alerts`?
- How are `frag_count`, `deep_loss_count`, and `red_alert` defined and passed in `app_gui.py` and `advisory_engine.py`?
- How should Capsule 5's main conclusion, subtitle, and badge/color adapt when pathologies are present vs when the portfolio is clean?
- Investigate all existing tests in `tests/` that test advisory engine, ten dimension votes, memo capsules, and data loader.
- Design a comprehensive test suite for Milestone 1 to be placed in `tests/test_g19_m1_ten_dimension_and_memo.py` that covers Features 1-6 thoroughly.
- Physical security baseline: DO NOT modify judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py. DO NOT modify DataLoader.simulate_execution default signature & default fee logic.
- Propose the exact, concrete implementation design and code modifications for the Worker.
Write your complete report to `d:\Google\Workspace\Wind\.agents\teamwork\explorer_m1_3\handoff.md`.
Send a message when finished.
