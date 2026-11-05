# BRIEFING — 2026-11-03T14:54:00Z

## Mission
Implement Milestone 1 (Sidebar & Guardrails Architect): R1 Redline data source unification, core index ticker styling enhancement, R2 sidebar risk/return sync, execution guardrails (purchase limit filter & rebalance buffer), and ledger/snapshot environment migration.

## 🔒 My Identity
- Archetype: worker_m1
- Roles: implementer, qa, specialist
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\worker_m1
- Original parent: 4b9235fc-5501-4c70-bc98-8ac4f7ce5f18
- Milestone: Milestone 1 (Sidebar & Guardrails Architect)

## 🔒 Key Constraints
- Genuine implementations only, no hardcoded results or dummy facades.
- Strictly read-only files: judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py
- Primary owned files: AGY2_FundAdvisory/app_gui.py, portfolio_manager.py, strategy_bridge.py
- Comply with GEMINI.md rules: Rule 14 (Geometry Invariants), Rule 15 (Flexbox anti-squash & scroll container), Rule 16 (Index integrity), Rule 10 (string-based dynamic mocking), Rule 9 (Tab error isolation), Rule 7 (FIFO penalty defense), Rule 8 (Anti-overbought), etc.
- Maintain compatibility with existing tests (e.g. at.sidebar.button[0] is '🚀 加载演示组合').

## Current Parent
- Conversation ID: 4b9235fc-5501-4c70-bc98-8ac4f7ce5f18
- Updated: 2026-11-03T14:53:19Z

## Task Summary
- **What to build**: Sidebar & Guardrails Architect for Milestone 1:
  1. R1 攻防红线数据源对齐: trigger_lines unified from snapshot before sidebar rendering.
  2. R1 核心指数实时行情条视觉提权: CSS upgrade, tabular font, gap, padding, scroll container preserved.
  3. R2 侧边栏全局目标与档位联动器: C1~C5 risk tier & annual return slider sync.
  4. R2 实盘交易风控护栏: purchase limit filter & replace_restricted_funds_with_alternatives; rebalance buffer slider 1~5%.
  5. R2 账本环境与快照管理迁移: Demo combo button at at.sidebar.button[0], undo snapshot, sync market, display lakehouse date 2026-11-03.
- **Success criteria**: All tests pass including `test_deep_remodel_final.py`, clean handoff report.
- **Interface contracts**: PROJECT.md & Explorer reports.
- **Code layout**: AGY2_FundAdvisory/

## Key Decisions Made
- Initializing work directory and briefing.

## Artifact Index
- `DISPATCH.md` — assignment details
- `BRIEFING.md` — situational awareness and context tracker
- `progress.md` — liveness heartbeat and execution log

## Change Tracker
- **Files modified**: None yet
- **Build status**: Untested
- **Pending issues**: None

## Quality Status
- **Build/test result**: Pending baseline run
- **Lint status**: Clean
- **Tests added/modified**: Pending

## Loaded Skills
- None
