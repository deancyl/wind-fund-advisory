# BRIEFING — 2026-11-07T14:34:30Z

## Mission
Investigate Tab 2 in AGY2_FundAdvisory/app_gui.py and test suites for G7 Generation dual-view mode switcher and code sinking.

## 🔒 My Identity
- Archetype: Explorer
- Roles: Investigation, Synthesis
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\explorer_g7_1
- Original parent: edefabf5-5abf-4405-bb80-202032d71b10
- Milestone: G7 Generation Survey

## 🔒 Key Constraints
- Read-only investigation — do NOT implement
- Reply in Chinese to all messages
- Strictly respect GEMINI.md and user rules
- Self-contained handoff.md with 5 components

## Current Parent
- Conversation ID: edefabf5-5abf-4405-bb80-202032d71b10
- Updated: 2026-11-07T14:27:00Z

## Investigation State
- **Explored paths**:
  - `AGY2_FundAdvisory/app_gui.py` (Tab 2: lines 3894-5765)
  - `tests/test_gui_multi_ledger_stress.py`
  - `tests/test_infra.py`
  - `tests/test_adv_final_closure.py`
  - `tests/test_g3_evolution_loop.py`
  - `tests/test_anticheat_full_closure.py`
  - `tests/test_ui_pro_redesign_verification.py`
  - `AGY2_FundAdvisory/strategy_bridge.py`
- **Key findings**:
  - Tab 2 lines 3894-5765 contains Step 1 (3894-5071), Step 2 (5072-5193), Step 3 (5194-5765).
  - Mode 2 tools (dock_tab1-6) currently sit inside an expander in Step 1 (lines 4631-5032, 401 lines).
  - Decoupling Mode 1 and Mode 2 via `tab2_view_mode` removes 401 lines of secondary tool widgets from Mode 1 DOM, cutting vertical height by >30%.
  - Critical static test assertions discovered: `<b>{len(pm.holdings)} 只</b>` (closure test 13), `if "edited_table" in locals() and edited_table is not None:` (closure test 3), `sel_tab2_vwap_schedule_item` (g3 test 7).
  - All 50 existing tests currently pass 100%.
- **Unexplored areas**: None, survey fully covers task scope.

## Key Decisions Made
- Tab 2 switcher placed directly below multi-ledger bar.
- Switcher options: `["持仓诊断与智能调仓", "账本运维与实盘复盘档案"]`, default Mode 1.
- Bidirectional jump between Mode 1 quick entry bar and Mode 2.
- Preserve all test-imported functions in `app_gui.py` via re-export if sunken to `strategy_bridge.py`.

## Artifact Index
- DISPATCH.md — Dispatch history
- BRIEFING.md — Persistent context
- progress.md — Heartbeat and progress tracking
- handoff.md — Final investigation report
