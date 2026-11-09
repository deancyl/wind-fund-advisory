# BRIEFING — 2026-11-09T15:58:00Z

## Mission
Milestone 1: Fix 5 UI/UX & Code Alignment Bugs + Remove 3D/RuleTree Vanity in AGY2_FundAdvisory

## 🔒 My Identity
- Archetype: worker
- Roles: implementer, qa
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\worker_m1\
- Original parent: 9a123e21-7525-4c57-9715-710c2a94c199
- Milestone: M1

## 🔒 Key Constraints
- Physical Safety Redlines:
  - 严禁修改四个只读裁判文件 judge_engine.py、holdout_vault.py、AGENT_SPEC.md、tests/test_infra.py
  - 严禁修改 DataLoader.simulate_execution 的默认函数签名与默认扣费逻辑
- 允许并要求同步更新非只读测试文件（如 tests/test_adv_final_closure.py 等）中针对旧按钮或旧布局的断言
- Integrity Mandate: No hardcoding test results, no dummy facade implementations, real logic only.
- 5 UI/UX Fixes:
  1. Remove 3D Surface chart -> 2D 3-crisis scenario table; Replace RuleTree code box with 2D parameter mechanism table.
  2. Right-wing sentry alerts: fix red/yellow badge and detail text extraction; sort alerts by severity.
  3. Tab 2 DataFrame column headers translation & remove duplicate bottom blue button; organize top toolbar.
  4. Tab 4 secondary navigation into single-row segmented control; unify 017436 naming; fix false 7-day lock-ins on new buy targets in strategy_bridge.py.
  5. Add "📱 手机极简盯盘视图 / 🖥️ 桌面专业模式" toggle in sidebar and render 3-stream cards in mobile mode.

## Current Parent
- Conversation ID: 9a123e21-7525-4c57-9715-710c2a94c199
- Updated: 2026-11-09T15:58:00Z

## Task Summary
- **What to build**: 5 UI/UX and code alignment fixes across app_gui.py, portfolio_manager.py, strategy_bridge.py.
- **Success criteria**: All 5 bugs cleanly fixed; pytest tests/test_infra.py and pytest tests/test_adv_final_closure.py pass 100%.
- **Interface contracts**: PROJECT.md M1 section.
- **Code layout**: AGY2_FundAdvisory/app_gui.py, portfolio_manager.py, strategy_bridge.py, tests/.

## Change Tracker
- **Files modified**: None yet.
- **Build status**: Pending.
- **Pending issues**: None.

## Quality Status
- **Build/test result**: Pending.
- **Lint status**: Clean.
- **Tests added/modified**: Pending.

## Loaded Skills
None
