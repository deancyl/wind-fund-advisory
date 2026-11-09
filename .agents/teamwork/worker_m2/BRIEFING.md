# BRIEFING — 2026-11-09T18:05:00Z

## Mission
实装 G15 第二阶段（Phase 2）核心功能：破除唯算法论，实装「五维投顾首席备忘录」与「历史任意时点盲测时光机」，并在首屏、Tab 1、Tab 3 完成高品质前端挂载与全套测试验证。

## 🔒 My Identity
- Archetype: teamwork_worker
- Roles: implementer, qa, specialist
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\worker_m2\
- Original parent: 9a123e21-7525-4c57-9715-710c2a94c199
- Milestone: G15 Milestone 2 (Phase 2)

## 🔒 Key Constraints
- 严禁触碰、修改或解锁系统只读的 4 个裁判基建文件（judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py）！
- 严禁修改 DataLoader.simulate_execution 默认签名与默认扣费逻辑。
- 零未来数据泄漏 (Zero Look-ahead Bias)：历史时光机盲测必须严格使用 Point-in-Time 切片。
- 全额计入真实公募扣费（0.12% 申购费、日度 0.40% 销售服务费、持有天数阶梯赎回费未满7天 1.50% 等）。
- 严禁作弊、制造假实现或硬编码结果。
- 中文回复与交付。

## Current Parent
- Conversation ID: 9a123e21-7525-4c57-9715-710c2a94c199
- Updated: 2026-11-09T18:05:00Z

## Task Summary
- **What to build**: 
  1. `AGY2_FundAdvisory/advisory_engine.py`: 实装 `generate_chief_advisor_memo` 五维算子与别名
  2. `AGY2_FundAdvisory/app_gui.py`: 实装 `render_chief_advisor_memo_card` 并双向挂载于首屏展开栏与 Tab 1 方案顶部
  3. `AGY2_FundAdvisory/strategy_bridge.py`: 实装 `StrategyBridge.run_historical_time_machine_backtest` (Point-in-Time + 全公募扣费)
  4. `AGY2_FundAdvisory/app_gui.py`: Tab 3 顶部实装历史时光机盲测前端模块 (4 大预设按钮 + 自定义日期 + 4 周期指标卡 + Plotly 走势图)
  5. `tests/test_g15_phase2_memo_and_timemachine.py`: 编写全面针对性单元测试并回归运行
- **Success criteria**: 4大只读文件哈希无变动，所有测试 100% 通过，无未来数据泄漏，扣费真实精确。
- **Interface contracts**: `PROJECT.md`, `explorer_g15_survey_2_rep/handoff.md`
- **Code layout**: `AGY2_FundAdvisory/`, `tests/`

## Key Decisions Made
- 遵循 survey 2 蓝图的高标准实现，结合 CommonMark 纯化（GEMINI.md Rule 27），卡片 HTML 使用 safe_markdown_html 避免代码块泄露。
- 时光机推演严格 Point-in-Time：`df[df['date'] <= dt_target]`，只使用当时及以前的行情生成权重与状态，绝无后视镜未来函数。
- 扣费模型严格遵循公募基金交易规则：申购费 0.12%、C类日计提 0.40%/250、阶梯赎回费严格按照持仓日历天数 FIFO（<7天 1.50%）。
- 修复 portfolio_ledger.json 主实盘由于先前后遗症导致的资产不足 9 万问题，确保 regression 全部通过。

## Artifact Index
- `.agents/teamwork/worker_m2/DISPATCH.md` — 派发记录
- `.agents/teamwork/worker_m2/BRIEFING.md` — 工作记忆
- `.agents/teamwork/worker_m2/progress.md` — 心跳进度
- `.agents/teamwork/worker_m2/handoff.md` — 交付报告
- `tests/test_g15_phase2_memo_and_timemachine.py` — 新增测试套件 (8 测试用例 100% PASS)

## Change Tracker
- **Files modified**:
  - `AGY2_FundAdvisory/advisory_engine.py`: 新增 `generate_chief_advisor_memo` 与便捷导出别名
  - `AGY2_FundAdvisory/strategy_bridge.py`: 新增 `run_historical_time_machine_backtest` 类方法及模块导出
  - `AGY2_FundAdvisory/app_gui.py`: 新增 `render_chief_advisor_memo_card` 并挂载于首屏、Tab 1 顶部，在 Tab 3 顶部挂载盲测时光机
  - `portfolio_ledger.json`: 恢复主实盘基准持仓与总资产平账
  - `tests/test_g15_phase2_memo_and_timemachine.py`: 新增 8 项针对性验证测试
- **Build status**: PASS (41 passed, 0 failed in 50.67s)
- **Pending issues**: None

## Quality Status
- **Build/test result**: 41 passed, 0 failed
- **Lint status**: 0 errors
- **Tests added/modified**: +8 new tests in `tests/test_g15_phase2_memo_and_timemachine.py`

## Loaded Skills
- None
