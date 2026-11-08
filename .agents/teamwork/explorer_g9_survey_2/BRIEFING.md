# BRIEFING — 2026-11-08T06:04:00Z

## Mission
Deeply investigate and survey R2: 全局交互降噪、HTML 纯化与傻瓜化操作流重构 (L1 傻瓜层 + L2 机构白盒层)，为后续代码实施提供完备的代码级证据链、架构方案与精确行级重构建议。

## 🔒 My Identity
- Archetype: explorer
- Roles: GUI Architecture Explorer
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\explorer_g9_survey_2
- Original parent: e2e9b1b9-848d-4b67-b5e8-3f65177957b7
- Milestone: G9 R2 GUI Architecture Survey

## 🔒 Key Constraints
- Read-only investigation — do NOT implement / modify source code directly
- Strict CommonMark 4+ spaces HTML purification rule compliance (Rule 27)
- Preserve all session_state keys, function signatures, and UI elements asserted by existing tests
- Absolute read-only barrier on judge files (judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py)
- Workspace-only isolation for GEMINI.md

## Current Parent
- Conversation ID: e2e9b1b9-848d-4b67-b5e8-3f65177957b7
- Updated: 2026-11-08T06:03:09Z

## Investigation State
- **Explored paths**:
  - `d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md`
  - `d:\Google\Workspace\Wind\.agents\teamwork\explorer_g9_survey_2\DISPATCH.md`
  - `c:\Users\deanc\Downloads\agy2_fundadvisory_ui_architecture_evaluation.md`
  - `c:\Users\deanc\Downloads\agy2_app_gui.md`
  - `d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py` (lines 180-250, 1599-2040, 2750-3170, 3200-4350, 4630-5060, 5270-5620, 6010-6200)
  - `d:\Google\Workspace\Wind\tests\test_g7_architecture_and_decoupling.py`
  - `d:\Google\Workspace\Wind\tests\test_g8_ux_and_realtime_fusion.py`
  - `d:\Google\Workspace\Wind\tests\test_streamlit_apptest_run.py`
  - `d:\Google\Workspace\Wind\.agents\teamwork\explorer_g9_survey_1\handoff.md`
  - `d:\Google\Workspace\Wind\.agents\teamwork\explorer_g9_survey_3\handoff.md`
- **Key findings**:
  1. HTML Leakage: Identified 20+ places in `app_gui.py` where `st.markdown(..., unsafe_allow_html=True)` bypassed `safe_markdown_html` inside indented blocks (lines 2985, 3002, 3044, 4221, etc.). Also verified `render_historical_inflection_ruler_html` and other HTML builders. Designed two-tier defense (`_clean_html` strip and `safe_markdown_html` wrapper).
  2. Top Wing Dashboard: Identified current clutter. Designed "今日投顾行动总开关" status logic + 1-click jump via `pending_cross_tab_jump`. Kept 14-sector thermometer and 60d trajectory in popover/expander. Cleaned right wing slogan suffix and adjusted height.
  3. Tab 1 New Capital: Simplified Step 1 to Principal + C1-C5 tier, auto-selected HRP model, num_funds, horizon, and quota filter, with collapsible expert fine-tuning panel. Merged simulation and execution generation into 1 click. Collapsed 16 cards into 3 L1 human-readable cards and L2 white-box drawer.
  4. Tab 2 Portfolio Rebalancing: Merged 4 overview cards + cushion watchdog card; collapsed -3%/-5%/-10% stress scenarios. Converted 5-column quick fund entry bar into a popover inside the table toolbar. Maintained strict dual-view isolation and verified buffer slider single-source.
- **Unexplored areas**: None for R2 scope.

## Key Decisions Made
- Reconstruct UI strictly via progressive disclosure (L1 conclusion layer + L2 white-box evidence layer) without adding dual-mode toggle switch.
- Preserve 100% test contract compatibility (all session_state keys, function signatures, widget keys, and static string assertions).

## Artifact Index
- `d:\Google\Workspace\Wind\.agents\teamwork\explorer_g9_survey_2\progress.md` — Liveness & step tracking
- `d:\Google\Workspace\Wind\.agents\teamwork\explorer_g9_survey_2\handoff.md` — Comprehensive survey and recommendation report
