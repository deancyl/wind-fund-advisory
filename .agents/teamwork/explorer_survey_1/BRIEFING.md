# BRIEFING — 2026-11-11T00:36:00Z

## Mission
只读深度走查 G16 世代第一阶段涉及的代码（advisory_engine.py 与 app_gui.py），产出详尽的调查与分析报告 handoff.md。

## 🔒 My Identity
- Archetype: explorer
- Roles: investigation, synthesis
- Working directory: d:\Google\Workspace\Wind
- State folder: d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_1
- Original parent: a4d409c2-aeca-47df-a18c-528d9465a6c8
- Milestone: G16 Phase 1 Codebase Survey & Analysis

## 🔒 Key Constraints
- Read-only investigation — do NOT implement
- 严禁修改任何业务代码（只在自己的 state folder 中写入报告与状态文件）
- 严禁修改全局 GEMINI.md
- 输出遵守中文规则与 5-Component Handoff Protocol

## Current Parent
- Conversation ID: a4d409c2-aeca-47df-a18c-528d9465a6c8
- Updated: not yet

## Investigation State
- **Explored paths**:
  - `AGY2_FundAdvisory\advisory_engine.py`: 行 4170~4375 (`generate_chief_advisor_memo`)、行 1545~1705 (`evaluate_opportunity` 动量与信噪比)、行 2190~2230 (`ActiveRiskSentry` 成本读取)、行 3100~3135 (维度 13 碎片尾仓规则)
  - `AGY2_FundAdvisory\app_gui.py`: 行 249~329 (`render_chief_advisor_memo_card`)、行 2948~3028 (顶部 4 张全局指标卡)、行 3072~3205 (`render_dual_wing_advisory_dashboard` 与 `wing_expander`)、行 4055~4066 (Tab 1 建仓备忘录调用)
  - `AGY2_FundAdvisory\portfolio_manager.py`: 行 261~305 (`FundHolding` 属性定义)、行 322~323 (`HoldingItem = FundHolding`)
  - `AGY2_FundAdvisory\multi_ledger_manager.py`: 行 189~265 (`_init_preset_combat_29_ledger` 数据结构)
  - `AGY2_FundAdvisory\data_loader.py`: 行 2938~3030 (`fetch_macro_cross_market_indicators`)
  - `tests\test_adversarial_m2_challenger2_timemachine_and_memo.py`: 行 46~61 (`MockFundHolding` 仅有 `cost_value` 的历史原因)
- **Key findings**:
  1. `generate_chief_advisor_memo` 实际位于 `advisory_engine.py` 第 4170~4375 行；第 1545~1705 行为赛道评估算子。
  2. `pl_ratio` 漏检深套标的根因：第 4284 行读取了不存在的 `cost_value`，而 `FundHolding`/`HoldingItem` 与账本 JSON 字段为 `cost_basis`、`cost_price`、`floating_pnl_pct`。需做多层降级兼容。
  3. Tab 1 误报“6只碎片合计¥1.00”根因：传入的 `opt_weights` 为浮点权重字典，若直接将 value 视作市值，0.35 会触发 `0 < mv < 200`；且 Tab 1 属于拟建仓方案校验，应展示建仓结构校验而非存量病灶。
  4. 碎片尾仓计数对齐：`generate_chief_advisor_memo` 原先按 `mv < 200` 统计会误将 `005827 易方达蓝筹` (¥124.14, A类偏股腰部仓) 计入变成 20 只；对齐 `ActiveRiskSentry`（不足100元，或100~200元且为C类/联接/尾仓）后精确匹配 19 只、¥442.70。
  5. `render_chief_advisor_memo_card` 提权位置：从 `render_dual_wing_advisory_dashboard` 的 `with wing_expander:`（第 3168 行）移至 `wing_expander = st.expander(...)`（第 3166 行）正上方，即指标卡正下方、折叠框正上方。
  6. CSS 重构方案：从纵向 `grid-template-columns: 1fr` 重构为 1 行 5 列横向等高网格 `grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 8px;`，高约 115px，顶置鲜明色标与结论胶囊。
- **Unexplored areas**: None (全量调研完毕)

## Key Decisions Made
- 实地运行 probe 脚本验证了 `combat_29_funds` 与 `opt_weights` 的行为与输出。
- 梳理出精确修改代码行号、数据结构兼容链与测试方案，输出最终 handoff.md。

## Artifact Index
- d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_1\DISPATCH.md — 任务派发记录
- d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_1\BRIEFING.md — 运行记忆与状态
- d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_1\progress.md — 进度与存活心跳
- d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_1\probe_combat29.py — 实盘29基走查脚本
- d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_1\probe_tab1.py — Tab 1 opt_weights 走查脚本
- d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_1\probe_fixed_logic.py — 修复后盈亏识别模拟验证脚本
- d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_1\test_tail_rule.py — 19基碎片尾仓规则精确平账验证脚本
- d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_1\handoff.md — 最终调查报告
