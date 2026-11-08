# BRIEFING — 2026-11-08T06:10:00Z

## Mission
实现 Milestone 2 (M2): GUI 交互降噪、HTML 纯化与傻瓜化操作流重构 (L1 傻瓜层 + L2 机构白盒层)，并在 app_gui.py 中落地“今日投顾行动总开关”、Tab 1 双输入+3人话大卡+合流建仓、Tab 2 紧凑看板+Popover录基+双视图隔离，100% 保持契约与测试兼容。

## 🔒 My Identity
- Archetype: worker
- Roles: implementer, qa
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\worker_g9_m2_12
- Original parent: e2e9b1b9-848d-4b67-b5e8-3f65177957b7 (orchestrator_12)
- Milestone: M2 - GUI 交互降噪、HTML 纯化与傻瓜化操作流重构

## 🔒 Key Constraints
- 严禁修改 4 个只读裁判文件：judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py。
- 严禁修改 DataLoader.simulate_execution 的默认函数签名与默认扣费逻辑。
- 严禁触碰全局 GEMINI.md。
- 严禁作弊、硬编码测试结果或伪造输出。
- 独占修改所有权：仅修改 AGY2_FundAdvisory/app_gui.py，不触碰其他源码。
- 严格保留 13 个 session_state 键名与 18 个 Widget Keys / 文本断言标记。
- Rule 27：彻底清剿裸调 st.markdown(..., unsafe_allow_html=True)，收口至 safe_markdown_html，零 CommonMark 4+ 空格泄露。

## Current Parent
- Conversation ID: e2e9b1b9-848d-4b67-b5e8-3f65177957b7
- Updated: not yet

## Task Summary
- **What to build**:
  1. app_gui.py HTML 纯化与安全渲染收口 (Rule 27)
  2. 首屏双翼看板“今日投顾行动总开关”+左翼 Top 3 优选卡+右翼预警哨自适应
  3. Tab 1 新资建仓：L1 极简双输入（本金+C1-C5）+ L2 专家折叠面板 + 模拟与建仓合流 + 3人话大结论卡 + L2 白盒证据抽屉
  4. Tab 2 持仓调仓：紧凑顶栏概览与安全垫看板 + 极速录基 Popover 化 + 严格双视图物理隔离
- **Success criteria**:
  - pytest tests/test_gui_multi_ledger_stress.py tests/test_g8_ux_and_realtime_fusion.py tests/test_adv_final_closure.py 100% 通过
  - 静态检查 0 unsafe raw st.markdown(..., unsafe_allow_html=True)
- **Interface contracts**: explorer_g9_survey_2/handoff.md & SCOPE.md
- **Code layout**: AGY2_FundAdvisory/app_gui.py

## Key Decisions Made
- 遵循 explorer_g9_survey_2 的架构设计与具体行号建议。
- 确保所有测试断言的关键 DOM 文本、键名、CSS class 及 session_state 完美保留。

## Artifact Index
- AGY2_FundAdvisory/app_gui.py — 主 GUI 文件
- d:\Google\Workspace\Wind\.agents\teamwork\worker_g9_m2_12\progress.md — 进度与心跳记录
- d:\Google\Workspace\Wind\.agents\teamwork\worker_g9_m2_12\handoff.md — 最终交接报告

## Change Tracker
- **Files modified**: TBD
- **Build status**: pending
- **Pending issues**: none

## Quality Status
- **Build/test result**: pending
- **Lint status**: pending
- **Tests added/modified**: pending

## Loaded Skills
- None
