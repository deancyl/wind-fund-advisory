# BRIEFING — 2026-11-03T14:35:00Z

## Mission
Read-only architecture & code investigation for R3: Tab 2「步骤一：持仓账本」人体工学深度重构 (4 metric cards, refined st.data_editor, direct market value editing & shares recalculation, action bar alignment, and consolidated 账本工具坞).

## 🔒 My Identity
- Archetype: explorer
- Roles: investigator, synthesis
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r6_2
- Original parent: 4b9235fc-5501-4c70-bc98-8ac4f7ce5f18
- Milestone: exploration_phase_r6_r3

## 🔒 Key Constraints
- Read-only investigation — do NOT implement / modify source code
- Chinese replies only
- Adhere to GEMINI.md and workspace guidelines
- 5-component handoff report and survey_report.md

## Current Parent
- Conversation ID: 4b9235fc-5501-4c70-bc98-8ac4f7ce5f18
- Updated: not yet

## Investigation State
- **Explored paths**:
  - `AGY2_FundAdvisory/app_gui.py` (lines 1735-2030: Tab 2 Step 1)
  - `AGY2_FundAdvisory/portfolio_manager.py` (lines 2561-3960, 5460-5520: holdings, export_snapshot_df, recalculate totals, penalty-free checks)
  - `AGY2_FundAdvisory/tests/test_deep_remodel_final.py` (baseline test execution verified: 7 passed)
  - `AGY2_FundAdvisory/tests/test_live_rebalance_upgrades.py` & `test_portfolio_manager.py` (snapshot export contracts)
- **Key findings**:
  - Top 4 buttons in Step 1 can be cleanly migrated (demo/undo to sidebar, sync to table action bar, cash to Card 2 popover).
  - 4 aligned metric cards designed: Market Value + Position %, Cash Pool + Popover, PnL + Intraday Quote Est, Lock/Free stats + Alpha.
  - Table can be trimmed from 19 columns to 10 columns by moving intraday totals to Card 3 and merging holding days + fee badge into 1 column.
  - Direct editing of "当前市值(元)" unlocked and bidirectional sync with "持仓份额" mapped via state machine and `pm.add_or_update_holding()`.
  - Equal-height 4-button action bar designed with delete moved into Popover.
  - 3 expanders consolidated into single "🛠️ 账本工具坞" with 3 tabs, state-adaptive expand/collapse, preserving existing title test assertions.
- **Unexplored areas**: None, full scope explored.

## Key Decisions Made
- `pm.export_snapshot_df()` must retain full columns to avoid breaking test assertions; table column trimming occurs in `app_gui.py` display layer.
- Merged holding days/fee status column uses regex `re.search(r'\d+', ...)` for resilient natural integer extraction on user edit.
- Retained exact title substrings `"实盘接管档案"` and `"FIFO批次透视"` in tool dock sub-tabs to satisfy existing `test_deep_remodel_final.py`.

## Artifact Index
- `survey_report.md` — Complete architecture survey and implementation blueprint for R3
- `handoff.md` — 5-component handoff report
- `progress.md` — Liveness heartbeat and milestone tracker
- `DISPATCH.md` — Dispatch record
