# BRIEFING — 2026-11-08T04:55:05Z

## Mission
Lead G10 generation: multi-asset correlation stress mutation defense, extreme liquidity dynamic slippage compensation, see-through Monte Carlo stress testing, UI visual verification, full test suite pass, and v3.10-G10 git release.

## 🔒 My Identity
- Archetype: teamwork_orchestrator
- Roles: orchestrator, user_liaison, human_reporter, successor
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_11\
- Original parent: sentinel
- Original parent conversation ID: 7c35d6a9-f9de-4c34-a30e-7fbaf2d6b753

## 🔒 My Workflow
- **Pattern**: Project
- **Scope document**: d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_11\SCOPE.md
1. **Decompose**:
   - M1: 金融量化与流动性风控核心整改 (相关性突变防御 + 场外执行冲击折价 + 蒙特卡洛压力测试) [DONE]
   - M2: 本地服务平滑重启与多模态视觉走查闭环 (双翼看板 + Tab 1/2 + 亮暗主题/移动端) [DONE]
   - M3: 全量自动化测试、只读裁判核验、Git 打标归档与 G11 指令自举 [IN_PROGRESS]
2. **Dispatch & Execute**:
   - Survey via 3 parallel explorers to map current codebase state against G10 requirements.
   - For each milestone, execute Worker -> Reviewer -> Challenger -> Auditor cycle.
3. **On failure**:
   - Retry -> Replace -> Skip -> Redistribute -> Redesign
4. **Succession**: at 16 spawns, write handoff.md, spawn successor
- **Work items**:
  1. Survey & Architecture Alignment [done]
  2. M1: Financial Quant & Liquidity Risk Core [done]
  3. M2: Service Restart & Browser Visual Walkthrough [done]
  4. M3: Test Verification, Git Tagging & Victory Audit [in-progress]
- **Current phase**: 3 (M3 Regression, Documentation, Git & Victory Audit)
- **Current focus**: Running full regression tests, updating GEMINI.md/PROGRESS_LOG.md, committing and tagging v3.10-G10

## 🔒 Key Constraints
- NEVER write, modify, or create source code files directly.
- NEVER run build/test commands yourself — require workers to do so.
- NEVER investigate or explore the problem at the code level — dispatch Explorers.
- Four read-only judge files strictly protected: judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py
- DataLoader.simulate_execution default signature and fee logic strictly protected
- Zero look-ahead bias (T-day close signal executes at T+1), mandatory 2.0% risk-free rate deduction for Sharpe ratio
- No pseudo-random numbers, linear interpolation pseudo-series, or static constants for financial metrics
- Strict workspace-only rule for GEMINI.md / PROGRESS_LOG.md; never touch global GEMINI.md
- No GitHub Releases; tag v3.10-G10 only
- Victory Audit is MANDATORY before reporting completion
- Never reuse a subagent after it has delivered its handoff — always spawn fresh

## Current Parent
- Conversation ID: 7c35d6a9-f9de-4c34-a30e-7fbaf2d6b753
- Updated: 2026-11-08T04:55:05Z

## Key Decisions Made
- Milestone M1 and M2 fully completed and verified.
- Dispatched worker_g10_m3 for full regression testing, GEMINI.md/PROGRESS_LOG.md updating, and Git commit/tagging.

## Team Roster
| Agent | Type | Work Item | Status | Conv ID |
|-------|------|-----------|--------|---------|
| explorer_survey_g10_1 | teamwork_explorer | Survey R2 Correlation & Liquidity Shift | completed | d87c978c-7be6-4877-bdd6-ba3b301c6fb1 |
| explorer_survey_g10_2 | teamwork_explorer | Survey R3 OTC Execution & Haircut Penalty | completed | 0937bb1e-e1ec-481f-b11e-7a1ae634dd0e |
| explorer_survey_g10_3 | teamwork_explorer | Survey R4/R5/R6 Monte Carlo, UI & Tests | completed | 5a934c02-4ddb-4f25-bbce-90f2cb18bd7e |
| worker_g10_m1 | teamwork_worker | Implement M1 Quant, Liquidity & Stress Test | completed | b6e9a469-e4c4-44c2-962d-674e2e1ef0f3 |
| reviewer_g10_m1_1 | teamwork_reviewer | Review M1 Correctness & Interfaces | completed (APPROVE) | f8863ae1-fecf-416a-aa1b-fc6413676ee1 |
| reviewer_g10_m1_2 | teamwork_reviewer | Review M1 Robustness & Regression | completed (APPROVE) | d59b992a-95ee-48e2-8941-36a3e6c591dc |
| challenger_g10_m1_1 | teamwork_challenger | Empirical Stress: Correlation & Slippage | completed (APPROVE) | ba241326-02e6-4c09-ad34-15bfefa583c6 |
| challenger_g10_m1_2 | teamwork_challenger | Empirical Stress: Monte Carlo Risk Axioms | completed (REJECT) | e4458d67-f4b1-4373-bfef-956ee0bb89c7 |
| auditor_g10_m1 | teamwork_auditor | Forensic Integrity Audit | completed (CLEAN) | c9e9a26d-59ac-4c0b-9b55-8d2eaec20de0 |
| worker_remediation_g10_m1 | teamwork_worker | Remediate FIFO lock & pm_instance in M1 | completed | 61ef3085-86f8-4e9a-93ca-a31ec8577f0e |
| challenger_remediation_g10_m1 | teamwork_challenger | Re-verify FIFO lock & pm_instance fixes | completed (APPROVE) | 47ac1635-e0a5-49e6-b8f5-1dbacf47bdab |
| worker_g10_m2 | teamwork_worker | Milestone M2 Service Restart & UI Walkthrough | completed | 5b32a8b1-dcb8-4774-9cd0-32948220e59f |
| worker_g10_m3 | teamwork_worker | Milestone M3 Regression, Docs, Git & Tag | in-progress | edfc7e9b-5926-4714-b7e1-d9b2aaeaf035 |

## Succession Status
- Succession required: no
- Spawn count: 13 / 16
- Pending subagents: edfc7e9b-5926-4714-b7e1-d9b2aaeaf035
- Predecessor: none
- Successor: not yet spawned

## Active Timers
- Heartbeat cron: task-36 (*/10 * * * *)
- Safety timer: none

## Artifact Index
- .agents/teamwork/ORIGINAL_REQUEST.md — Authoritative user request record
- .agents/teamwork/orchestrator_11/DISPATCH.md — G10 dispatch instructions
- .agents/teamwork/orchestrator_11/progress.md — Progress tracker
- .agents/teamwork/orchestrator_11/SCOPE.md — Global architecture and milestone decomposition
- .agents/teamwork/orchestrator_11/GATE_STATUS.md — Gate verification verdicts
- .agents/teamwork/worker_g10_m2/handoff.md — M2 UI walkthrough report
