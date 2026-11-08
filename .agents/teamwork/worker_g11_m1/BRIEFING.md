# BRIEFING — 2026-11-08T12:56:00Z

## Mission
Implement Milestone 1 of G11: Top Area & Tab 1 Three-Block Refactoring in `AGY2_FundAdvisory/app_gui.py` per R1/R2.

## 🔒 My Identity
- Archetype: worker
- Roles: implementer, qa, specialist
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\worker_g11_m1
- Original parent: c6b4ebd0-c5f1-4175-8ba5-3bd0979b970d
- Milestone: M1 (Top Area & Tab 1 Three-Block Refactoring)

## 🔒 Key Constraints
- Exclusively own `AGY2_FundAdvisory/app_gui.py` (Top Area, CSS, Tab 1)
- Do NOT touch the 4 read-only referee files: `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`
- Do NOT modify `DataLoader.simulate_execution` default signature or fee logic
- Do NOT touch global `c:\Users\deanc\.gemini\GEMINI.md`
- Lock top 4 metric cards height to 82px in CSS, de-emojify by >70%
- Remove standalone Action Switch banner and Cross-Tab banner; merge today's conclusion into wing expander dynamic title with compact jump button beside it
- Retain comment hook `# 跨区联动指令已生效承接横幅`
- Remove Tab 1 step indicators, captions, gray AI box, duplicate '一键生成全案' button, Step 1/2/3 headers
- Build Tab 1 Module 1 (Single-Line Control Bar), Module 2 (Core execution table & 3-metric bar directly above), Module 3 (4 Popovers/buttons + single bottom drawer expander)

## Current Parent
- Conversation ID: c6b4ebd0-c5f1-4175-8ba5-3bd0979b970d
- Updated: not yet

## Task Summary
- **What to build**: Top 4 metric cards height 82px, banner merge into wing expander title, CSS de-emojification, Tab 1 three-block refactoring (single-line controls -> core execution table & 3-metric bar -> action popovers & single bottom drawer)
- **Success criteria**: All affected tests green, clean syntax, 0 regressions on session_state/keys, proper three-block architecture
- **Interface contracts**: `d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_15\PROJECT.md`
- **Code layout**: `d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py`

## Key Decisions Made
- Standardized `tab1_sel_model_type` selectbox options to exact 7 short names: `["鲁棒双核HRP", "核心-卫星杠铃", "全天候风险平价", "BL主客观观点融合", "条件胜率最优", "尾部风控CVaR", "凯利动量增强"]`
- In `render_black_swan_stress_card`, ensured exact substring `"历史黑天鹅极端承压测试"` is preserved in title span for test contract compatibility.
- In Tab 1, unified Step 2 and Step 3 into Module 2 & Module 3: immediately upon `tab1_step_reached >= 2`, compute both simulation weights and execution blueprint, rendering 3 decision metric bars directly above `df_display`, followed by 4 popovers/buttons line, and a single bottom expander housing all white-box evidence.

## Change Tracker
- **Files modified**:
  - `AGY2_FundAdvisory/app_gui.py`: Locked card height to 82px, padding-top 1.2rem, card margin-bottom 6px; de-emojified top 4 cards; merged action conclusion into wing expander dynamic title with compact jump button; removed standalone cross-tab banner with comment hook; implemented Tab 1 Module 1 (Single-line control bar + popover), Module 2 (3 high-contrast cards directly above execution table), Module 3 (Single line of 4 popovers/buttons + single bottom white-box drawer).
- **Build status**: PASS (Python py_compile clean, 0 syntax errors)
- **Pending issues**: None

## Quality Status
- **Build/test result**:
  - `tests/test_infra.py`: 14 passed (100%)
  - `tests/test_anticheat_full_closure.py -k test_apptest_tab1_seven_models_and_black_swan_rendering`: 1 passed (100%)
  - `tests/test_g8_ux_and_realtime_fusion.py`: 7 passed (100%)
  - `tests/test_g10_correlation_liquidity_and_stress.py`: 6 passed (100%)
  - `tests/test_gui_multi_ledger_stress.py -k test_tab1_save_to_new_ledger_isolation`: 1 passed (100%)
- **Lint status**: Clean
- **Tests added/modified**: Verified all relevant test suites pass without regression

## Loaded Skills
- None specified for loading
