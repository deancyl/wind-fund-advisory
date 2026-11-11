# BRIEFING — 2026-11-11T01:16:00Z

## Mission
修复 `advisory_engine.py` 中 `generate_chief_advisor_memo` 的持仓成本属性 Bug，并重构首屏「十维感知·五维横向投顾情报矩阵」(`render_chief_advisor_memo_card`)。

## 🔒 My Identity
- Archetype: teamwork_worker
- Roles: implementer, qa, specialist
- Working directory: d:\Google\Workspace\Wind
- State folder: d:\Google\Workspace\Wind\.agents\teamwork\worker_m1
- Original parent: a4d409c2-aeca-47df-a18c-528d9465a6c8
- Milestone: M1

## 🔒 Key Constraints
- 独占所有权文件：
  1. `d:\Google\Workspace\Wind\AGY2_FundAdvisory\advisory_engine.py`
  2. `d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py` (仅限 memo 卡片函数与首屏调用位置)
- 严禁作弊 (DO NOT CHEAT)，真实逻辑实现。
- 修复 `generate_chief_advisor_memo`：
  - 多字段兼容读取成本与盈亏率（修复 cost_value 不存在问题，计入 deep_loss_list，deep_loss_count >= 3）；
  - Tab 1 权重字典误判修复；
  - 19 只免赎碎片与 ¥442.70 严格对齐；
  - 强化五维决策备忘录因果叙事；
- 重构 `app_gui.py`：
  - 提权至首屏主视野（移出 wing_expander，放于全局指标卡后、双翼展开栏前）；
  - 1 行 5 列横向等高响应式矩阵网格；
  - 严格遵循规则 27 使用 `_clean_html()` 与 `safe_markdown_html()`；
- 编写测试并验证。

## Current Parent
- Conversation ID: a4d409c2-aeca-47df-a18c-528d9465a6c8
- Updated: 2026-11-11T01:16:00Z

## Task Summary
- **What to build**: 修复持仓成本计算 Bug，精确识别深套标的与碎片尾仓，重构 5 维情报矩阵卡片并在首屏顶层呈现。
- **Success criteria**:
  - `generate_chief_advisor_memo` 正确解析 HoldingItem 对象与 dict；
  - 29 基账本 deep_loss_count >= 3（011613, 100032, 161725 等）；
  - Tab 1 权重字典不会报出碎片；
  - 19 只免赎碎片识别对齐（¥442.70）；
  - 首屏卡片 5 列等高，且无 HTML 语法泄露。
- **Interface contracts**: `d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_g16_gen2\SCOPE.md`
- **Code layout**: `d:\Google\Workspace\Wind\AGY2_FundAdvisory\`

## Key Decisions Made
- `advisory_engine.py`: 实现多层级成本读取降级链 (`cost_basis` -> `cost_price * shares` -> `cost_value`)，结合 `floating_pnl_pct` 与 `pnl_pct`，彻底消除 `cost_value` 缺失导致的深套漏检，同时保持对旧 mock 桩的向后兼容。
- `is_weight_dict` 识别：当检测到目标权重字典时，转为“拟建仓组合结构校验”，坚决跳过碎片尾仓和深套检查，杜绝 Tab 1 误报“6只碎片合计¥1.00”。
- 碎片尾仓严格与 `ActiveRiskSentry` 保持一致规则：`<100` 或 `100~200` 且（C类或指数/联接/红包），实战 29 基精确识别 19 只免赎碎片合计 ¥442.70（排除 #10 005827 易方达蓝筹）。
- `app_gui.py`: 将 `render_chief_advisor_memo_card` 提权至 `wing_expander` 之前，重构为 1 行 5 列横向网格 (`repeat(5, minmax(0, 1fr))`，在 `<768px` 窄屏自适应折行)，每张高度约 115px，无 CommonMark 4 空格泄露。

## Artifact Index
- `d:\Google\Workspace\Wind\.agents\teamwork\worker_m1\handoff.md` — 最终交付报告
- `d:\Google\Workspace\Wind\.agents\teamwork\worker_m1\progress.md` — 进度状态跟踪
- `tests/test_g16_phase1_memo_and_combat29.py` — M1 专用全量验收单测

## Change Tracker
- **Files modified**:
  - `AGY2_FundAdvisory/advisory_engine.py`: 修复成本属性 Bug，增加中美利差，增加权重字典建仓校验，对齐 19 只碎片尾仓
  - `AGY2_FundAdvisory/app_gui.py`: 重构 `render_chief_advisor_memo_card` 为 1 行 5 列等高横向网格并提权至首屏主视野
  - `tests/test_g16_phase1_memo_and_combat29.py`: 新增针对 M1 的 6 项全面回归测试
- **Build status**: Pass (42/42 tests passing across all memo suites + 14/14 test_infra)
- **Pending issues**: None

## Quality Status
- **Build/test result**: Pass (42/42 memo tests pass, 14/14 test_infra pass)
- **Lint status**: Clean
- **Tests added/modified**: `tests/test_g16_phase1_memo_and_combat29.py` (6 new test cases)

## Loaded Skills
- None
