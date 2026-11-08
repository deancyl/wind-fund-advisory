# Task Assignment: Project Orchestrator Gen 2 (orchestrator_16)

## Identity
- Archetype: Project Orchestrator (orchestrator_16, generation 2)
- Working directory: `d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_16\`
- Parent Agent Conversation ID: `b8ca5e6a-3eb7-49b1-84a9-fa00c4c28e15` (YOUR PARENT — use this ID for all escalation and status reporting)
- Predecessor: `orchestrator_15` (conversation ID: `c6b4ebd0-c5f1-4175-8ba5-3bd0979b970d`)

## Context & Inputs
- Handoff from Predecessor: `d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_15\handoff.md`
- Predecessor Briefing: `d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_15\BRIEFING.md`
- Predecessor Progress: `d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_15\progress.md`
- Predecessor Gate Status: `d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_15\GATE_STATUS.md`
- Project Milestone Document: `d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_15\PROJECT.md`
- Authoritative User Request: `d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md`

## Completed Milestones
- Phase 0: Survey & Codebase Exploration [DONE]
- Milestone 1: Top Area & Tab 1 Three-Block Refactoring [DONE - Gate PASS]
- Milestone 2: Tab 2 Three-Block Refactoring [DONE - Gate PASS]
- Milestone 3: Test Suite Alignment & Invariant Verification [DONE - Gate PASS]

## Remaining Milestones to Execute
1. **Milestone 4: Service Restart & Browser Visual Inspection**
   - Terminate old 8501 port process cleanly.
   - Launch Streamlit service in silent background mode (`py -3 -m streamlit run AGY2_FundAdvisory/app_gui.py --server.port 8501 --server.headless true`).
   - Probe `http://127.0.0.1:8501/_stcore/health` for HTTP 200.
   - Use `/browser` to visit `http://localhost:8501` and take multi-modal screenshots:
     - Verify first screen (zero scroll) shows top 4 cards (82px) + wing expander + Tab 1 input/plan.
     - Switch to Tab 2 and verify top bar + holdings table in first screen.
     - Verify Light and Dark mode.
     - Verify 640px mobile viewport (no overflow, no clipping).
2. **Milestone 5: Hygiene, Versioning, Victory Audit & G12 Directive Generation**
   - Run full regression suites: `pytest tests/test_infra.py tests/test_adv_final_closure.py tests/test_g3_evolution_loop.py tests/test_gui_multi_ledger_stress.py` (ensure 100% green).
   - Ensure clean data files: `data/ledgers_index.json` only tracks `main_live`, clean any temporary scripts (e.g. `scripts/refactor_tab1_modules.py`).
   - Update `GEMINI.md` and `PROGRESS_LOG.md` in workspace root (G11 three-block rules & permanent bracketed slashCommand tag format invariant).
   - Git commit G11 development progress and tag `v4.1-G11` (`git tag -a v4.1-G11 -m "..."`).
   - Push to origin (`git push origin HEAD` and `git push origin --tags`). Zero GitHub releases.
   - Dispatch independent Victory Auditor (`victory_auditor`) to verify all acceptance criteria.
   - Output G12 generation directive with strict bracketed slashCommand tags.
