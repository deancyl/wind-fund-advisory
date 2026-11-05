# BRIEFING — 2026-11-05T01:34:30Z

## Mission
Coordinate and monitor the execution of market index corridor, 7 quantitative weighting models, 6-dimensional risk sentry, and UI fixes.

## 🔒 My Identity
- Archetype: sentinel
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\sentinel
- Orchestrator: 3ef18151-e1aa-4330-83a1-353aa7bcc35e
- Victory Auditor: to be spawned on victory claim

## 🔒 Key Constraints
- No technical decisions — relay only
- Victory Audit is MANDATORY before reporting completion
- 物理安全红线：严禁修改只读裁判文件（judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py）
- 调仓与风控算法守死先进先出与 1.50% 赎回费硬约束
- Streamlit Tab 独立错误边界隔离与 Windows 瞬态端口非破坏性甄别
- 单源同真（Single Source of Truth）：全站估值与动量数据必须统一由 IndexValuationEngine 动态计算

## Routing Decision
- **Route**: General (`teamwork_orchestrator`)
- **Rationale**: Multi-part software engineering project spanning data pipeline, quantitative algorithms, Streamlit UI, risk engine, and test suites. Does not qualify for Document Review or Math/Proof, and exceeds SWE Light scope.

## User Context
- **Last user request**: Approved task prompt received and recorded in .agents/teamwork/ORIGINAL_REQUEST.md.
- **Pending clarifications**: none
- **Delivered results**: none

## Project Status
- **Phase**: in progress

## Victory Audit Status
- **Triggered**: no
- **Verdict**: pending
- **Retry count**: 0

## Artifact Index
- .agents/teamwork/ORIGINAL_REQUEST.md — Authoritative record of user intent
