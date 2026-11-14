# BRIEFING — 2026-11-14T09:00:20Z

## Mission
针对 Wind 投顾系统启动 G18 世代生产环境迭代：修复首屏裁决台手机端高度溢出重叠、打通十维投票与定权优化器知行合一闭环、校准汇率与美债真实最新数据、实装存量账本首屏自动路由，并升级截图导入双因子匹配引擎与完成端到端双视口实测验收。

## 🔒 My Identity
- Archetype: orchestrator
- Roles: orchestrator, user_liaison, human_reporter, successor
- Working directory: d:\Google\Workspace\Wind
- State folder: d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_g18\
- Original parent: caller agent
- Original parent conversation ID: a51b57dc-55d4-4cd5-88e7-feee0deb6896

## 🔒 My Workflow
- **Pattern**: Project
- **Scope document**: d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_g18\PROJECT.md
1. **Decompose**: Decompose G18 into milestones based on 4 requirement phases
2. **Dispatch & Execute**:
   - **Direct (iteration loop)**: Explorer -> Worker -> Reviewer -> Challenger -> Auditor gate
3. **On failure**: Retry -> Replace -> Skip -> Redistribute -> Redesign -> Escalate
4. **Succession**: At 16 spawns, write handoff.md, spawn successor
- **Work items**:
  1. Survey & Map scope [in-progress]
  2. M1: UI Overflow & Mobile Routing (R1) [pending]
  3. M2: Ten-dim votes to optimizer closed loop & real macro data (R2) [pending]
  4. M3: Screenshot OCR + Yesterday Return dual-factor engine (R3) [pending]
  5. M4: Physical redlines, automated tests, browser verification, git tag (R4) [pending]
- **Current phase**: 0 (Survey)
- **Current focus**: Map scope and current codebase state via 3 parallel Explorers

## 🔒 Key Constraints
- NEVER write, modify, or create source code files directly.
- NEVER run build/test commands yourself — require workers to do so.
- NEVER investigate or explore the problem at the code level — dispatch Explorers for technical investigation.
- You MAY use file-editing tools ONLY for metadata/state files (.md) in your .agents/teamwork/ folder.
- 严禁修改四个只读裁判文件 judge_engine.py、holdout_vault.py、AGENT_SPEC.md、tests/test_infra.py
- 严禁修改 DataLoader.simulate_execution 的默认函数签名与默认扣费逻辑
- 绝对禁止输出带冒号的 slashCommand: 格式
- 严禁创建 GitHub Release
- Audit verdict is a BINARY VETO
- Never reuse a subagent after it has delivered its handoff — always spawn fresh

## Current Parent
- Conversation ID: a51b57dc-55d4-4cd5-88e7-feee0deb6896
- Updated: 2026-11-14T08:58:00Z

## Key Decisions Made
- Initiated G18 Project Orchestration.
- Starting Step 0 Survey with 3 parallel Explorers to investigate R1, R2, R3 in codebase.

## Team Roster
| Agent | Type | Work Item | Status | Conv ID |
|-------|------|-----------|--------|---------|
| explorer_survey_r1 | teamwork_explorer | Survey R1: UI Overflow & Mobile Routing | in-progress | b65d0630-20dc-438b-b0d1-9ae9eacfb48d |
| explorer_survey_r2 | teamwork_explorer | Survey R2: Macro data & 10-dim closed loop | in-progress | 888e2b64-1398-4bf9-86b6-f29627001f4d |
| explorer_survey_r3 | teamwork_explorer | Survey R3: OCR dual-factor & R4 constraints | in-progress | b3718ee3-f51a-4ec4-b6df-5d77e9aaeb02 |

## Succession Status
- Succession required: no
- Spawn count: 3 / 16
- Pending subagents: b65d0630-20dc-438b-b0d1-9ae9eacfb48d, 888e2b64-1398-4bf9-86b6-f29627001f4d, b3718ee3-f51a-4ec4-b6df-5d77e9aaeb02
- Predecessor: none
- Successor spawned: not yet spawned
- Successor generation: none
- Successor state folder: none

## Active Timers
- Heartbeat cron: bceeab71-9282-4c25-93c4-63a5a7504316/task-12
- Safety timer: bceeab71-9282-4c25-93c4-63a5a7504316/task-20

## Artifact Index
- d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md — Original user request
- d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_g18\DISPATCH.md — Dispatch log
- d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_g18\BRIEFING.md — Working memory
- d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_g18\progress.md — Liveness & status tracking
