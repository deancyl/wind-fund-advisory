# BRIEFING — 2026-11-11T02:41:00Z

## Mission
Implement Milestone 3: Multi-ledger idempotent mount & test isolation, Tab 2 3-step refactor prescription & holding days copy reconcile, strategy bridge impact estimation & dynamic rebalance backtest, and Tab 3 29-vs-6 backtest preset UI.

## 🔒 My Identity
- Archetype: implementer
- Roles: implementer, qa, specialist
- Working directory: d:\Google\Workspace\Wind
- State folder: d:\Google\Workspace\Wind\.agents\teamwork\worker_m3
- Original parent: 97fbe156-e8f7-47df-8b1d-f8a8c1c69a5e
- Milestone: Milestone 3

## 🔒 Key Constraints
- File ownership: Exclusively own:
  1. `AGY2_FundAdvisory/multi_ledger_manager.py`
  2. `AGY2_FundAdvisory/strategy_bridge.py`
  3. `AGY2_FundAdvisory/app_gui.py`
  4. Unit test additions in `tests/`
- PHYSICAL REDLINE INVARIANTS:
  - NEVER modify the 4 read-only referee files: `AGY2_FundAdvisory/judge_engine.py`, `AGY2_FundAdvisory/holdout_vault.py`, `AGY2_FundAdvisory/AGENT_SPEC.md`, `tests/test_infra.py`.
  - NEVER modify `DataLoader.simulate_execution` signature or default fee/delay parameters!
  - NEVER modify `data/ledgers/combat_29_funds.json` static holding_days (keep 400).
- Rules 27, 28: HTML in app_gui must pass through `_clean_html` and `safe_markdown_html`. CommonMark 4+ spaces defense.
- Rule 13: Test pruning and agile delivery. Workspace-only GEMINI.md.

## Current Parent
- Conversation ID: 97fbe156-e8f7-47df-8b1d-f8a8c1c69a5e
- Updated: not yet

## Task Summary
- **What to build**:
  - Task 1: `multi_ledger_manager.py` Idempotent Mount & Test Isolation (`if str(self.root.resolve()).lower() == str(WORKSPACE_ROOT.resolve()).lower():`).
  - Task 2: `app_gui.py` reconcile holding days copy, Tab 2 4-dimensional comparative metric grid, 3-step refactor prescription button & state machine binding.
  - Task 3: `strategy_bridge.py` extend `estimate_rebalance_impact`, add `get_combat_29_rebalance_prescription()`, expand `code_to_col_alpha` for 29 funds, add `get_combat_29_vs_reconstructed_6_preset()`, add `dynamic_rebalance` in `run_historical_time_machine_backtest`.
  - Task 4: `app_gui.py` Tab 3 preset for 29 vs reconstructed 6 funds, dynamic rebalance toggle.
  - Verification & tests: 6 test suites + 2 new test files (`tests/test_m3_item2_rebalance_impact.py`, `tests/test_m3_item3_tab3_backtest.py`).
- **Success criteria**: All tests pass (including test_infra 14/14), 100% genuine logic, clean UI.

## Change Tracker
- **Files modified**: [TBD]
- **Build status**: pending
- **Pending issues**: none

## Quality Status
- **Build/test result**: pending
- **Lint status**: clean
- **Tests added/modified**: pending

## Loaded Skills
- None loaded.

## Artifact Index
- `.agents/teamwork/worker_m3/DISPATCH.md` — assignment
- `.agents/teamwork/worker_m3/progress.md` — heartbeat & progress
- `.agents/teamwork/worker_m3/changes.md` — detailed changes
- `.agents/teamwork/worker_m3/handoff.md` — handoff report
