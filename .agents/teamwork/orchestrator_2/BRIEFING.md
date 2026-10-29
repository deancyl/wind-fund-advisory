# BRIEFING — 2026-10-29T14:45:00Z

## Mission
Coordinate 4 specialized subagents (Agent-1, Agent-2, Agent-3, Agent-4) plus Forensic Auditor to implement R1-R7 and satisfy all Acceptance Criteria for AGY2_FundAdvisory.

## 🔒 My Identity
- Archetype: orchestrator
- Roles: orchestrator, user_liaison, human_reporter, successor
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_2
- Original parent: parent
- Original parent conversation ID: 32aa8f5a-9883-4d9f-9fe1-9f1733eb1cc3

## 🔒 My Workflow
- **Pattern**: Project
- **Scope document**: d:\Google\Workspace\Wind\PROJECT.md
1. **Decompose**:
   - **Work Item 1 (Agent-1)**: Ledger & Risk Control Fixes in `portfolio_manager.py` (R1 drawdown/baseline reset, R3 bank double-high exemption & deduplication, R4 split items & overlap exemption).
   - **Work Item 2 (Agent-2)**: Strategy Bridge & Dynamic Selection in `strategy_bridge.py` and `portfolio_manager.py` (R5 derivatives.py IV/discount integration, R2 C1-C5 dynamic fund pools & 6D scoring funnel).
   - **Work Item 3 (Agent-3)**: Streamlit UI/UX Slimming in `app_gui.py` (R2 slider mode A/B decoupling, R3 stock table, R5 funnel UI, R6 9 columns & collapsed drawers).
   - **Work Item 4 (Agent-4)**: End-to-End Tests & Service Restart in `tests/` (Acceptance Criteria, 100% tests pass, Streamlit 8501 service restart).
   - **Work Item 5 (Forensic Auditor)**: Forensic integrity audit of all modified files.
2. **Dispatch & Execute**:
   - Phased execution enforcing single-writer discipline per file.
   - Workers run tests and provide reports; Reviewers and Auditor verify integrity and correctness.
3. **On failure**:
   - Retry -> Replace -> Skip -> Redistribute -> Redesign -> Escalate
4. **Succession**:
   - Self-succeed at 16 spawns.
- **Work items**:
  1. Agent-1: Ledger & Risk Fixes (`portfolio_manager.py`) [pending]
  2. Agent-2: Quant Selection & Strategy Bridge (`strategy_bridge.py`, `portfolio_manager.py`) [pending]
  3. Agent-3: UI/UX Slimming (`app_gui.py`) [pending]
  4. Agent-4: Red Team E2E Tests & Service Restart (`tests/`) [pending]
  5. Auditor: Forensic Integrity Audit [pending]
- **Current phase**: Phase 1 (Agent-1 Dispatch)
- **Current focus**: Agent-1 Ledger & Risk Control Fixes

## 🔒 Key Constraints
- NEVER write, modify, or create source code files directly.
- NEVER run build/test commands yourself — require workers to do so.
- NEVER investigate or explore the problem at the code level — dispatch workers/explorers.
- Write ownership: single worker per file to prevent merge conflicts.
- Strict Read-Only Invariants: `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py` must remain strictly untouched.
- Audit Enforcement: If Forensic Auditor reports INTEGRITY VIOLATION, milestone fails unconditionally.
- Respond in Chinese to user/parent messages.

## Current Parent
- Conversation ID: 32aa8f5a-9883-4d9f-9fe1-9f1733eb1cc3
- Updated: 2026-10-29T14:41:16Z

## Key Decisions Made
- Phased pipeline: Agent-1 -> Agent-2 -> Agent-3 -> Agent-4 -> Forensic Auditor to prevent concurrent file conflicts on `portfolio_manager.py`.

## Team Roster
| Agent | Type | Work Item | Status | Conv ID |
|-------|------|-----------|--------|---------|
| worker_agent1 | teamwork_worker | R1, R3, R4 Ledger & Risk Control Fixes | completed | 5acaf4c1-025d-4ae4-a661-7648f1fda79a |
| worker_agent2 | teamwork_worker | R5, R2 Derivatives & Quant Funnel Bridge | completed | c30c920b-bbd0-4d97-ba42-0d51858f358d |
| worker_agent3 | teamwork_worker | R2, R3, R5, R6 UI/UX Slimming & Overhaul | completed | 7c631971-0181-44d6-8664-b5d6f76edd49 |
| worker_agent4 | teamwork_worker | E2E Red Team Tests & Service Restart | completed | 3a82b92a-cb4c-46de-b7f8-e4d39bbf96e5 |
| auditor_final | teamwork_auditor | Forensic Integrity Audit | completed | 902bae9e-765e-4471-8a28-f9ff646e7642 |

## Succession Status
- Succession required: no
- Spawn count: 5 / 16
- Pending subagents: []
- Predecessor: orchestrator_1
- Successor: not yet spawned

## Active Timers
- Heartbeat cron: not started
- Safety timer: none

## Artifact Index
- `d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md` — Authoritative requirements
- `d:\Google\Workspace\Wind\PROJECT.md` — Project architecture and milestones
- `d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_2\progress.md` — Progress tracking
- `d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_2\GATE_STATUS.md` — Gate verdicts
