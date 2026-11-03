# BRIEFING — 2026-11-03T06:58:00Z

## Mission
Lead production-grade deep refactoring of Wind advisory system: global UI/UX redesign, optimizer degradation fix, and win rate statistics expansion.

## 🔒 My Identity
- Archetype: orchestrator
- Roles: orchestrator, user_liaison, human_reporter, successor
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_1
- Original parent: parent (sentinel)
- Original parent conversation ID: affddc2f-4348-4b2a-896b-c02e3b236adb

## 🔒 My Workflow
- **Pattern**: Project Pattern (Dual Track: Implementation + E2E Testing)
- **Scope document**: d:\Google\Workspace\Wind\PROJECT.md
1. **Decompose**: Survey codebase -> define PROJECT.md architecture & milestones -> decompose into M1 (Optimizer Degradation & Weight Conservation Fix), M2 (Win Rate Statistics & Sample Expansion), M3 (UI/UX Information Architecture & Visual Redesign), M4 (E2E Verification & Service Restart) + E2E Testing Track
2. **Dispatch & Execute**: Direct iteration loop or delegate
3. **On failure**: Retry -> Replace -> Skip -> Redistribute -> Redesign
4. **Succession**: At 16 spawns, write handoff.md, spawn successor
- **Work items**:
  1. Survey & Codebase Exploration [pending]
  2. Architecture & PROJECT.md Definition [pending]
  3. Milestone 1: Optimizer Degradation & Weight Conservation Fix (R1.1) [pending]
  4. Milestone 2: Win Rate Statistics Expansion & Dual Modes (R1.2) [pending]
  5. Milestone 3: Global UI/UX Redesign & Information Architecture (R2) [pending]
  6. Milestone 4: Full Regression & Service Restart (R3, R4) [pending]
- **Current phase**: 0 (Survey)
- **Current focus**: Launching parallel Explorers to investigate optimizer, win rate, and UI codebases.

## 🔒 Key Constraints
- NEVER write, modify, or create source code files directly.
- NEVER run build/test commands yourself — require workers to do so.
- NEVER touch or unlock read-only files: judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py.
- Mathematical Invariants: Total allocated_amount == total_capital, target_weight_pct == 100.0%, models must produce differentiated weights (no 1/N collapse).
- UI Requirements: Sidebar restored as navigation desk, top indices full-width single line, 4 models as responsive cards, 6-dim scoring popover, 3 core logic cards dynamic, titles <= 7 Chinese chars.
- Path to ORIGINAL_REQUEST.md must be provided to every subagent.

## Current Parent
- Conversation ID: affddc2f-4348-4b2a-896b-c02e3b236adb
- Updated: 2026-11-03T06:55:20Z

## Key Decisions Made
- Starting Phase 0 Survey with 3 parallel Explorers:
  1. Explorer 1: portfolio_optimizer.py, strategy_bridge.py, generate_zero_start_blueprint, mathematical invariants.
  2. Explorer 2: win rate calculation, historical index and net value datasets, dual-mode win rate implementation.
  3. Explorer 3: app_gui.py, sidebar restoration, top index tickers, model card layout, 3-card attribution, <=7 char title audit.

## Team Roster
| Agent | Type | Work Item | Status | Conv ID |
|-------|------|-----------|--------|---------|
| teamwork_explorer_prod_1 | teamwork_explorer | R1.1 Optimizer Degradation & Purchasing Limit | in-progress | e9ac7099-11e4-40e2-aadd-bba3cdd04e81 |
| teamwork_explorer_prod_2 | teamwork_explorer | R1.2 Win Rate Statistics & Sample Expansion | in-progress | 213e0bae-c23f-4bc7-836d-75d05840382c |
| teamwork_explorer_prod_3 | teamwork_explorer | R2 UI/UX Architecture & Visual Redesign | completed | df3c5016-ec84-4ee8-9421-9e15d655776e |
| worker_prod_m1 | teamwork_worker | M1 Optimizer Degradation & Invariants | in-progress | d6348e9b-6db9-41e6-a24a-f7ca4bcfd539 |

## Succession Status
- Succession required: no
- Spawn count: 4 / 16
- Pending subagents: d6348e9b-6db9-41e6-a24a-f7ca4bcfd539
- Predecessor: none
- Successor: not yet spawned

## Active Timers
- Heartbeat cron: 79413d19-45ad-4a69-b696-81c549751856/task-34
- Safety timer: 79413d19-45ad-4a69-b696-81c549751856/task-233

## Artifact Index
- d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md — User requirements
- d:\Google\Workspace\Wind\PROJECT.md — Master project architecture and milestones
- d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_1\progress.md — Progress tracker
- d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_1\GATE_STATUS.md — Gate status log
