# BRIEFING — 2026-11-09T15:08:00Z

## Mission
Survey codebase for G15 Phase 1: chart vanity removal, UI/UX and alignment bug fixes, mobile/desktop toggle, Tab 2/Tab 4 optimizations in AGY2_FundAdvisory.

## 🔒 My Identity
- Archetype: explorer
- Roles: explorer, survey
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\explorer_g15_survey_1
- Original parent: 9a123e21-7525-4c57-9715-710c2a94c199
- Milestone: G15 Phase 1 Codebase Survey & Fix Proposal

## 🔒 Key Constraints
- Read-only investigation — do NOT implement / modify source code
- Never touch judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py
- Output structured findings and concrete code recommendations in handoff.md
- Send message to parent orchestrator upon completion

## Current Parent
- Conversation ID: 9a123e21-7525-4c57-9715-710c2a94c199
- Updated: 2026-11-09T15:27:00Z

## Investigation State
- **Explored paths**:
  - `d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md`
  - `c:\Users\deanc\Downloads\agy2_ui_ux_audit_and_fix_plan (3).md`
  - `d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py` (lines 40-100, 2147-2189, 2228-2320, 2440-2790, 2860-3115, 4245-4270, 4400-4415, 4698-4726, 5035-5060, 5200-5271, 5540-5820, 6970-7050)
  - `d:\Google\Workspace\Wind\AGY2_FundAdvisory\portfolio_manager.py` (lines 280-295, 600-650, 840-850, 2595-2615, 9185-9515)
  - `d:\Google\Workspace\Wind\AGY2_FundAdvisory\advisory_engine.py` (lines 830-860, 2137-2450, 3600-3670)
  - `d:\Google\Workspace\Wind\AGY2_FundAdvisory\strategy_bridge.py` (lines 490-500, 3740-3780)
- **Key findings**:
  1. `render_monte_carlo_3d_chart`: 3D Plotly Surface chart defined at `app_gui.py:2147-2189`, called at line 4258 and 5045. Flat along X-axis because `portfolio_manager.py:9464` appends identical MDD 5 times for C1-C5. Can be completely replaced by `render_monte_carlo_stress_table` (2D table + plain human conclusion).
  2. RuleTree code box: `st.code(rule_expr_txt, language="text")` at `app_gui.py:2974`. Replaced by 2D table explaining Mom_Win, Vol_Pulse, Panic_Safe in human terms.
  3. Right-wing alert sentry bug: `app_gui.py:2907` and `3098` only check `lvl == "CRITICAL"`, missing `"red"`. `detail_str = alert.get("detail", alert.get("message", ""))` misses `"desc"`, losing all descriptions. Action key is `"action"`. `alerts_list` lacks severity sorting, getting flooded by scale warnings.
  4. Tab 2 DataFrame column headers: `vwap_slices` displayed with raw English keys `phase, label, vol_ratio, slice_amount, strategy` at `app_gui.py:4410` and `5732`. Mapping to `执行阶段, 窗口类型, 分配比例, 建议挂单金额(元), 微观执行策略` required.
  5. Tab 2 duplicate execute button: line 5809 has duplicate full-width blue button under primary action buttons. Move quick fund entry, batch text, screenshot upload, undo to top toolbar, delete the duplicate full-width button.
  6. Tab 4 secondary navigation: `st.tabs` wrapped in 2 rows. Convert to compact single-row `st.segmented_control` or `st.radio(horizontal=True)`.
  7. Fund name discrepancies: `017436` has multiple variations (`华安纳斯达克100A`, `华安纳指100`, `华宝...`). Unify to standard `华安纳斯达克100ETF联接A`. Also update `strategy_bridge.py:3758` to search `CORE_STRATEGY_POOL` etc. to eliminate `存量标的_XXXXXX`.
  8. Mobile view switch: Add `global_view_layout_mode` toggle ("🖥️ 桌面专业模式" vs "📱 手机极简盯盘"), rendering 3 dedicated components when mobile mode is selected.
- **Unexplored areas**: None for G15 Phase 1 scope.

## Key Decisions Made
- Fully documented exact file paths, line numbers, and before/after code blocks.
- Ready to author complete 5-component `handoff.md`.

## Artifact Index
- DISPATCH.md — Initial dispatch record
- BRIEFING.md — Persistent context & identity
- progress.md — Heartbeat and status
- handoff.md — Final 5-component survey report
