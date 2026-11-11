# BRIEFING — 2026-11-11T22:38:00+08:00

## Mission
带领完成 G17 世代五维/十维全息投顾决策大脑、真实数据湖仓穿透、手机端 2x2 响应式重构、首屏裁决台合流、存量账本自动路由、长截图双因子验真与 Tab 3 全真公募摩擦扣减明细栏落地并验证。

## 🔒 My Identity
- Archetype: Lead Implementation Worker
- Roles: implementer, qa, specialist
- Working directory: d:\Google\Workspace\Wind
- State folder: d:\Google\Workspace\Wind\.agents\teamwork\worker_g17_1
- Original parent: f28642b6-8afb-4f49-b855-13ffba6400aa
- Milestone: M1, M2, M3, M4

## 🔒 Key Constraints
- 严禁修改四个只读裁判文件：judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py
- 严禁修改 DataLoader.simulate_execution 的默认函数签名与默认扣费逻辑
- 严禁创建 GitHub Release（仅允许 git tag）
- 在任何报告或指令中，绝对禁止输出带冒号的 slashCommand: 格式，仅允许纯文本标签（/goal, /boost, /teamwork, /browser）
- 严禁使用硬编码假常数 (628.5, -0.25%, 7.2450, 1.6258, 4.40%)
- 遵循工作区 GEMINI.md 规则，所有学习沉淀局域化，严禁外溢全局
- 遵循多角色规范，完整实现并测试验证

## Current Parent
- Conversation ID: f28642b6-8afb-4f49-b855-13ffba6400aa
- Updated: 2026-11-11T14:36:15Z

## Task Summary
- **What to build**: 拔除五维备忘录静态假常数、实装十维投顾量化投票与因果公式、重构首屏裁决台(<=110px)、实装手机端2x2导航与田字格指标卡、存量账本自动路由Tab 1、表格核心列优先、长截图双因子验真、Tab 3 全真公募摩擦扣减明细栏、编写针对性测试并验证。
- **Success criteria**: 所有假常数消除，十维模型与因果链生成正确，CSS 2x2 主导航生效无截断，账本自动路由生效，长截图双因子匹配正确，Tab 3 扣费账单与回测优势呈现，Delta 测试通过，test_infra 14项通过。
- **Interface contracts**: PROJECT.md
- **Code layout**: PROJECT.md § Code Layout

## Key Decisions Made
- 将五维备忘录与今日参谋合并为单一「🧭 首席投顾今日裁决台」，默认直显区 <= 110px
- 顶层主导航在 max-width 768px 下设为 2x2 网格，彻底消除「🔍 穿透工具」截断
- 存量账本切换自动注入跨 Tab 跳转指令至 Tab 1 并展开实战诊断
- 长截图识别从 OCR 文本中提取 yesterday_pnl 并推导昨日收益率以双因子交叉锁定
- Tab 3 增加「中国公募交易规则全真摩擦扣减明细栏」

## Artifact Index
- DISPATCH.md - Task assignment from orchestrator
- BRIEFING.md - Persistent working memory
- progress.md - Liveness heartbeat
- handoff.md - Final completion report

## Change Tracker
- **Files modified**: pending
- **Build status**: pending
- **Pending issues**: none

## Quality Status
- **Build/test result**: pending
- **Lint status**: clean
- **Tests added/modified**: pending

## Loaded Skills
- **Source**: d:\Google\Workspace\Wind\.agents\skills\lidaxiao-advisory\SKILL.md
- **Local copy**: none
- **Core methodology**: 李大霄投资分析系统、股债差(ERP)与资产配置、个股/基金投资价值体检、做好人买好股
