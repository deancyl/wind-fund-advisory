# BRIEFING — 2026-11-07T15:38:00Z

## Mission
启动 G8 世代深度 UI 与 UX 金融防错整改、Tab 2 物理视图真隔离、跨 Tab 真实路由跳转与实时多源感知进化任务。落实七大 UI/UX 审计缺陷整改（P0-P2），实施多模态 /browser 视觉走查与全量回归测试验证，打上 v3.8-G8 标签归档。

## 🔒 My Identity
- Archetype: orchestrator
- Roles: orchestrator, user_liaison, human_reporter, successor
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\orchestrator\
- Original parent: parent
- Original parent conversation ID: f43b429c-6a00-4cf8-ab0f-794def5a308c

## 🔒 My Workflow
- **Pattern**: Project Pattern
- **Scope document**: d:\Google\Workspace\Wind\.agents\teamwork\orchestrator\PROJECT.md
1. **Decompose**:
   - Step 0: Survey codebase with 3 Explorers in parallel (R1-R7 + UX plans) [COMPLETED]
     - Explorer 1 (Items 1, 4, 5, 7): COMPLETED
     - Explorer 2 (Items 2, 3): COMPLETED
     - Explorer 3 (Item 6 + Test Design): COMPLETED
   - Step 1: Synthesize survey results and update PROJECT.md Feature Inventory & Milestones [COMPLETED]
   - Step 2: Milestone Iteration Loops (Worker -> Reviewers (2) -> Challengers (2) -> Forensic Auditor -> Gate)
     - Milestone 1: P0/P1 Tab 2 物理视图隔离、持仓表未保存保护、重复滑块清理与大额本金防错 (Items 1, 4, 5, 7) [IN_PROGRESS via Worker G8-1]
     - Milestone 2: P0 高危覆写良性摩擦与回滚、首屏跨Tab真路由跳转与承接横幅 (Items 2, 3) [IN_PROGRESS via Worker G8-1]
     - Milestone 3: P1 机会雷达盘中实时行情融合、秒级资讯感知与四维评分证据链 (Item 6) [IN_PROGRESS via Worker G8-1]
     - Milestone 4: G8 针对性测试套件实现、全量自动化回归测试与只读裁判审计 (Feature 8) [PLANNED]
     - Milestone 5: 服务重启、多模态 /browser 视觉走查与交互核验、Git 提交打标 v3.8-G8 与 G9 指令生成 (Features 9, 10) [PLANNED]
2. **Dispatch & Execute**: Direct iteration loop using subagents per milestone
3. **On failure**: Retry -> Replace -> Skip -> Redistribute -> Redesign
4. **Succession**: Self-succeed at 16 spawns
- **Work items**:
  1. Survey & Architecture Mapping [COMPLETED]
  2. Implementation of Features 1-7 & G8 Tests [IN_PROGRESS: Worker G8-1]
  3. Review, Challenge, Forensic Audit Gate [pending]
  4. Service Restart & /browser Visual Inspection [pending]
  5. Full Regression, Git Archive & G9 Directive [pending]
- **Current phase**: 2 (Worker Implementation)
- **Current focus**: Worker G8-1 executing Tasks 1-7

## 🔒 Key Constraints
- DISPATCH-ONLY orchestrator: MUST delegate ALL work to subagents via invoke_subagent.
- NEVER write, modify, or create source code files directly.
- NEVER run build/test commands yourself — require workers to do so.
- NEVER investigate or explore the problem at the code level — dispatch Explorers for technical investigation.
- You MAY use file-editing tools ONLY for metadata/state files (.md) in your .agents/teamwork/ folder.
- 物理安全红线：严禁触碰、修改只读裁判文件（judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py）。
- 严禁修改 DataLoader.simulate_execution 的默认函数签名与默认扣费逻辑。
- If Forensic Auditor reports INTEGRITY VIOLATION, milestone FAILS UNCONDITIONALLY.
- 严格遵循 GEMINI.md 全部准则，严禁外溢至全局配置。
- Never reuse a subagent after it has delivered its handoff — always spawn fresh.
- 严格禁止创建 GitHub Release（仅允许 git tag）。

## Current Parent
- Conversation ID: f43b429c-6a00-4cf8-ab0f-794def5a308c
- Updated: 2026-11-07T15:22:55Z

## Key Decisions Made
- Dispatched Lead Worker G8-1 (`f1c3a702-fb58-40ce-8cb0-fae478e997b5`) with consolidated exclusive write ownership to implement Features 1-7 and G8 test suite, avoiding concurrent write collisions on `app_gui.py`.
- Formatted exact interface contracts and AST protection rules (`# tab2_rebal_buf_slider_bot`, `<b>{len(pm.holdings)} 只</b>`).

## Team Roster
| Agent | Type | Work Item | Status | Conv ID |
|-------|------|-----------|--------|---------|
| explorer_g8_1 | teamwork_explorer | Tab 2 Dual-View, Table Protection, Slider Cleanup, Chinese Numeral | completed | 13202795-b9d2-4689-88e5-14b483abdd8d |
| explorer_g8_2 | teamwork_explorer | Overwrite Popover/Undo & Cross-Tab DOM Navigation | completed | 0ad0e896-a3fa-443a-8972-b1330646a39b |
| explorer_g8_3 | teamwork_explorer | Real-time Radar Quotes, News Crawl & 4D Evidence, Test Design | completed | 746d2421-235d-4385-9ee3-7ab6c87a85f1 |
| worker_g8_1 | teamwork_worker | Lead Implementation: Features 1-7 & tests/test_g8_ux_and_realtime_fusion.py | in-progress | f1c3a702-fb58-40ce-8cb0-fae478e997b5 |

## Succession Status
- Succession required: no
- Spawn count: 4 / 16
- Pending subagents: f1c3a702-fb58-40ce-8cb0-fae478e997b5
- Predecessor: none
- Successor: not yet spawned

## Active Timers
- Heartbeat cron: 9e61e1d7-9eb6-4227-b899-75a22db1e25b/task-40 (*/10 * * * *)
- Safety timer: 9e61e1d7-9eb6-4227-b899-75a22db1e25b/task-92 (600s)

## Artifact Index
- d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md — Original User Request
- d:\Google\Workspace\Wind\.agents\teamwork\orchestrator\DISPATCH.md — Dispatch log
- d:\Google\Workspace\Wind\.agents\teamwork\orchestrator\BRIEFING.md — Persistent briefing
- d:\Google\Workspace\Wind\.agents\teamwork\orchestrator\progress.md — Progress tracker
- d:\Google\Workspace\Wind\.agents\teamwork\orchestrator\PROJECT.md — Master Architecture & Milestones
- d:\Google\Workspace\Wind\.agents\teamwork\explorer_g8_1\analysis.md — Explorer G8-1 Analysis
- d:\Google\Workspace\Wind\.agents\teamwork\explorer_g8_2\analysis.md — Explorer G8-2 Analysis
- d:\Google\Workspace\Wind\.agents\teamwork\explorer_g8_3\analysis.md — Explorer G8-3 Analysis
- c:\Users\deanc\Downloads\agy2_ui_ux_audit_and_fix_plan.md — UI/UX Audit & Fix Plan
- c:\Users\deanc\Downloads\agy2_fundadvisory_ux_audit_and_fix_plan.md — Fund Advisory UX Audit Plan
