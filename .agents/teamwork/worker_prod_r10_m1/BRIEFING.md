# BRIEFING — 2026-11-05T16:31:00Z

## Mission
Execute Milestone 1 (M1): Fix dividend low vol benchmark code to H30269, differentiate QDII settlement/credibility, replace non-compliant "capital preservation" wording, and unify sector price caliber for momentum/bias.

## 🔒 My Identity
- Archetype: teamwork_worker
- Roles: implementer, qa, specialist
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\worker_prod_r10_m1
- Original parent: f7b8d799-910f-4e70-94f5-3538a52207de
- Milestone: M1 (Core Engine & Regulatory Compliance)

## 🔒 Key Constraints
- Physical Safety Redline: 严禁修改只读裁判文件（judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py），保持哈希完好无损。
- Physical Safety Redline: 严禁修改 DataLoader.simulate_execution 的默认函数签名与默认扣费逻辑。
- Exclusive write ownership:
  - AGY2_FundAdvisory/advisory_engine.py
  - AGY2_FundAdvisory/data_loader.py
  - AGY2_FundAdvisory/trading_clock_fee.py
  - AGY2_FundAdvisory/portfolio_manager.py
  - AGY2_FundAdvisory/strategy_bridge.py
  - AGY2_FundAdvisory/winrate_engine.py
  - src/analysis/market_temperature.py (if needed for compliance text)
- DO NOT edit app_gui.py in this milestone (owned by M2/M3).
- DO NOT edit tests/test_infra.py.
- Follow Integrity Mandate: No hardcoded test results, genuine implementations only.

## Current Parent
- Conversation ID: f7b8d799-910f-4e70-94f5-3538a52207de
- Updated: 2026-11-05T16:31:00Z

## Task Summary
- **What to build**:
  1. Fix dividend_low_vol benchmark index and index_code to H30269 (remove 000978 which is Pharma 100), update aliases and fallback parquet.
  2. Add QDII identification, settlement rules (T+2 confirmation, T+6~T+8 redemption, skip T+1 switch, exclude QDII from Tab 2 T+2 in-flight risk), and fund valuation credibility tagging.
  3. Replace non-compliant "保本率" with "正收益概率 (≥0%)" or "本金安全率" in winrate_engine, strategy_bridge, market_temperature.
  4. Unify 14 sector momentum/bias price calibers (prioritize price index or dividend-adjusted series for dividend sectors).
- **Success criteria**:
  - All targeted unit tests pass.
  - Zero integrity violations.
  - Handoff report completed.
- **Interface contracts**: PROJECT.md, GEMINI.md
- **Code layout**: AGY2_FundAdvisory/

## Key Decisions Made
- [Initial turn: Initialized BRIEFING and DISPATCH]

## Artifact Index
- DISPATCH.md — assignment dispatch
- BRIEFING.md — persistent working memory
- progress.md — liveness heartbeat
- handoff.md — final handoff report

## Change Tracker
- **Files modified**: None yet
- **Build status**: Pending
- **Pending issues**: None

## Quality Status
- **Build/test result**: Pending
- **Lint status**: Pending
- **Tests added/modified**: Pending

## Loaded Skills
- None explicitly dumped.
