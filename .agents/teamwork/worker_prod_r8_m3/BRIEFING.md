# BRIEFING — 2026-11-05T03:15:00Z

## Mission
实现 Milestone 3: 7 大机构级量化定权模型实装、宏观推荐路由更新、历史黑天鹅压力测试器与 UI 渲染 (Features 11-13)。

## 🔒 My Identity
- Archetype: worker_prod
- Roles: implementer, qa, specialist
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\worker_prod_r8_m3\
- Original parent: 3ef18151-e1aa-4330-83a1-353aa7bcc35e
- Milestone: M3 (Features 11, 12, 13)

## 🔒 Key Constraints
- Exclusive write ownership: `AGY2_FundAdvisory/winrate_engine.py`, `AGY2_FundAdvisory/portfolio_optimizer.py`, `AGY2_FundAdvisory/app_gui.py`.
- DO NOT touch referee files: `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`.
- DO NOT cheat, fake, or hardcode test outputs. Mathematical solvers must genuinely compute non-negative weights summing to 1.0 (`abs(sum(weights.values()) - 1.0) < 1e-6`).
- Follow Windows PowerShell, GEMINI.md workspace-only rules, and anti-vanity testing guidelines.

## Current Parent
- Conversation ID: 3ef18151-e1aa-4330-83a1-353aa7bcc35e
- Updated: not yet

## Task Summary
- **What to build**:
  1. Feature 11: 实装 7 大机构量化定权求解算子 (hrp_robust/hrp_cvar, core_satellite, all_weather, black_litterman, conditional_winrate/cond_winrate, cvar_tail/min_cvar, kelly_momentum) 于 `QUANT_MODELS_CATALOG` 与 `WinRateOptimizer`。
  2. Feature 12: 更新 Tab 1 步骤一 7 大模型对比卡片与宏观自适应推荐路由逻辑。
  3. Feature 13: 实现历史黑天鹅压力测试器 `simulate_black_swan_stress` (2018贸易摩擦, 2022杀估值, 2024微盘股危机) 并在 Tab 1 步骤二与 Tab 3 推演结果卡片中渲染。
- **Success criteria**:
  - 所有 7 大模型权重非负且和严格等于 1.0 (`abs(sum - 1.0) < 1e-6`)。
  - 黑天鹅回撤与回本天数测算真实准确无 NaN。
  - Tab 1 和 Tab 3 界面渲染无异常，深浅主题 0 报错。
  - 裁判文件哈希完好无损。
- **Interface contracts**: `d:\Google\Workspace\Wind\.agents\teamwork\orchestrator\PROJECT.md`
- **Code layout**: `AGY2_FundAdvisory/`

## Key Decisions Made
- [TBD]

## Artifact Index
- `d:\Google\Workspace\Wind\.agents\teamwork\worker_prod_r8_m3\DISPATCH.md` — 初始派发指令
- `d:\Google\Workspace\Wind\.agents\teamwork\worker_prod_r8_m3\BRIEFING.md` — 状态感知与工作记忆
- `d:\Google\Workspace\Wind\.agents\teamwork\worker_prod_r8_m3\progress.md` — 步骤推进心跳

## Change Tracker
- **Files modified**: None yet
- **Build status**: Untested
- **Pending issues**: None

## Quality Status
- **Build/test result**: Pending
- **Lint status**: Clean
- **Tests added/modified**: Pending

## Loaded Skills
- None explicitly requested for loading; domain rules loaded from GEMINI.md.
