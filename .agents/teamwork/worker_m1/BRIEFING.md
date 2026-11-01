# BRIEFING — 2026-10-31T23:45:00Z

## Mission
在专属独占写权限下对 `d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py` 进行 Milestone 1 重构，实现反偷懒工程治理、顶部全局看板大瘦身、重塑四大主导航 Tab，并通过测试与编译验证。

## 🔒 My Identity
- Archetype: implementer, qa, specialist
- Roles: implementer, qa, specialist
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\worker_m1
- Original parent: 15a3e419-5e4d-47c4-a669-7f8d1a1ddcee
- Milestone: Milestone 1 - GUI Architecture Refactoring & Antilaziness Cleanup

## 🔒 Key Constraints
- 专属独占写权限：仅修改 `d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py`。
- 严禁修改 4 个系统只读裁判文件（`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`）。
- 严禁造假，不硬编码测试结果，不建立虚假实现，彻底移除所有 `time.sleep` 与虚假延迟，毫秒级真实计算。
- 彻底移除硬编码 `"限额买500"`、`"现金分红·限额买500"`。
- 保持 `cols_9 = [...]` 变量名与 9 个列名兼容。
- 遵循 Windows 桌面交互规范与工作区投顾风控准则。

## Current Parent
- Conversation ID: 15a3e419-5e4d-47c4-a669-7f8d1a1ddcee
- Updated: not yet

## Task Summary
- **What to build**: 重构 `app_gui.py`：顶部看板瘦身为 1 行 4 宽卡 + 1 紧凑刷新按钮；Tab 1 新资金从 0 建仓推演（白盒抽屉摘要、动态操作指引、DCA超额定投计划）；Tab 2 我的当前持仓与今日调仓建议（垂直排布三层：AI调仓裁决卡、双模式后果账单与执行单、实时持仓明细）；Tab 3 组合深度体检与算费工具箱；Tab 4 策略历史回测与胜率档案；清除所有 time.sleep 与假延迟。
- **Success criteria**: py_compile 无语法错误，既有测试全部通过，无硬编码与假延迟，界面结构与需求契约 100% 对齐。
- **Interface contracts**: 见 survey_1 & survey_2 handoff.md。
- **Code layout**: `AGY2_FundAdvisory/app_gui.py`。

## Key Decisions Made
- [TBD]

## Artifact Index
- `d:\Google\Workspace\Wind\.agents\teamwork\worker_m1\handoff.md` — 最终交付报告
- `d:\Google\Workspace\Wind\.agents\teamwork\worker_m1\progress.md` — 执行进度跟踪

## Change Tracker
- **Files modified**: `AGY2_FundAdvisory/app_gui.py`
- **Build status**: Pending
- **Pending issues**: None

## Quality Status
- **Build/test result**: Pending
- **Lint status**: Pending
- **Tests added/modified**: Pending

## Loaded Skills
None
