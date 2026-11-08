# DISPATCH for worker_g9_m2_12

## Objective
Implement and verify Milestone 2 (M2): GUI 交互降噪、HTML 纯化与傻瓜化操作流重构 (L1 傻瓜层 + L2 机构白盒层).

## Inputs
- `d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md`
- `d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_12\SCOPE.md`
- `d:\Google\Workspace\Wind\.agents\teamwork\explorer_g9_survey_2\handoff.md` (CRITICAL: contains line numbers and concrete code templates!)
- `AGY2_FundAdvisory/app_gui.py`

## Exclusive Write Ownership
- `AGY2_FundAdvisory/app_gui.py` (Exclusively owned by this worker. Do NOT touch any other source file).

## Hard Constraints
- DO NOT touch the 4 read-only judge files: `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`.
- DO NOT touch global `GEMINI.md`.
- Preserve all 13 `session_state` keys: `active_ledger_id`, `active_tier_val`, `mlm`, `pm`, `sel_tab2_active_ledger`, `slider_target_return`, `tab1_step_reached`, `tab1_trigger_sim`, `tab2_diag_cache`, `tab2_diagnosed`, `tab2_rebal_cache`, `tab2_rebalanced`, `target_return_val`.
- Preserve all 18 Widget Keys & compatibility comments: `btn_apply_bp_tier`, `chk_confirm_t1_overwrite`, `btn_undo_t1_overwrite`, `btn_run_simulation_now`, `btn_t1_run_all`, `btn_bar_add_holding`, `btn_tab2_diagnose`, `btn_tab2_all`, `rad_tab2_view_mode`, `is_t2_main_mode`, `tab2_rebal_buf_slider`, `# tab2_rebal_buf_slider_bot`.

## Specific Implementation Tasks (per explorer_g9_survey_2 handoff)
1. **HTML 彻底纯化与安全渲染全域收口 (Rule 27)**:
   - Ensure `_clean_html(...)` strips all leading/trailing whitespace and blank lines.
   - Replace all ~20 occurrences of raw `st.markdown(..., unsafe_allow_html=True)` with `safe_markdown_html(...)` (see lines 2955, 2985, 3002, 3044, 3554, 4221, etc.).
   - Remove pseudo-wrapping raw html divs around containers (lines 1972, 1987, 2008, 2033).
   - Ensure `render_historical_inflection_ruler_html` and all rich-text components produce 0 CommonMark 4+ space indented code leaks.
2. **首屏双翼看板瘦身与“今日投顾行动总开关”实装**:
   - At the top of `render_dual_wing_advisory_dashboard`, render the high-visibility "今日投顾行动总开关" banner: dynamic 1 plain sentence recommendation (🔴/🟡/🟢/🚀 based on ActiveRiskSentry and holdings) + 1-click jump button (`key="btn_master_action_switch"`, setting `st.session_state["pending_cross_tab_jump"]`).
   - Left wing: keep refined market pulse and Top 3 cards; keep 14 sectors thermometer & 60d trajectory in Popover/Expander.
   - Right wing: remove marketing slogan suffix; make container height adaptive to eliminate scrollbar clipping.
3. **Tab 1 新资建仓 L1 极简双输入 + L2 专家面板 + 3 人话大卡**:
   - Step 1 L1: only expose principal input (`key="plan_capital_input"` + `format_chinese_amount`) and C1-C5 risk tier selector; auto-manage model (HRP) and fund count (4-8); wrap expert fine-tuning into `st.expander("⚙️ 机构级模型与高级参数微调 (已由 AI 智能托管)", expanded=False)`.
   - Merge simulation & execution: main button `key="btn_run_simulation_now"` triggers simulation and directly reveals the execution sheet (step 3 reached). Also preserve `key="btn_t1_run_all"`.
   - Step 2 L1: replace the 16-card vertical sprawl with 3 human-readable big conclusion cards side-by-side (💰 怎么赚钱 / 🛡️ 风险底线 / 🏆 为什么能赢); wrap 10k Monte Carlo, black swan stress, and 28k fund funnel tables into `st.expander("🔬 展开机构级量化压力测试与选基白盒证据", expanded=False)`.
4. **Tab 2 持仓调仓降噪、极速录基 Popover 化与双视图隔离**:
   - Combine top overview cards with floating cushion card into a compact top banner; collapse -3%/-5%/-10% stress scenarios into expandable details.
   - Convert the 5-column quick fund bar into a `st.popover("➕ 极速录基")` in the holdings table toolbar (preserve `btn_bar_add_holding`, `bar_fund_input`, `bar_amt_input`, `bar_pnl_input`, `bar_dur_choice`).
   - Maintain strict dual-view mode physical branch (`rad_tab2_view_mode`), ensuring main mode does not render the bottom 6 tool docks. Maintain single-source `tab2_rebal_buf_slider` and `# tab2_rebal_buf_slider_bot`.
5. **Verification**:
   Run tests to verify zero regressions:
   ```powershell
   py -3 -m pytest tests/test_gui_multi_ledger_stress.py tests/test_g8_ux_and_realtime_fusion.py tests/test_adv_final_closure.py
   ```
   Run static check to verify 0 unsafe raw `st.markdown(..., unsafe_allow_html=True)` remaining.

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Output
Write your completion handoff report to:
`d:\Google\Workspace\Wind\.agents\teamwork\worker_g9_m2_12\handoff.md`
Report: Observation, Logic Chain, Caveats, Conclusion, Verification Commands & Results.

## 2026-11-08T06:09:45Z
You are worker_g9_m2_12 (Role: GUI Implementation Worker).
Your working directory is: d:\Google\Workspace\Wind\.agents\teamwork\worker_g9_m2_12
Read d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md before starting work.
Read d:\Google\Workspace\Wind\.agents\teamwork\worker_g9_m2_12\DISPATCH.md for your detailed task requirements.
Also read d:\Google\Workspace\Wind\.agents\teamwork\explorer_g9_survey_2\handoff.md for exact line numbers, architectural designs, and implementation templates.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your task:
1. Purify HTML in AGY2_FundAdvisory/app_gui.py (Rule 27): replace raw st.markdown(..., unsafe_allow_html=True) with safe_markdown_html(...).
2. Implement "今日投顾行动总开关" at the top of the dual-wing dashboard, left wing Top 3 cards, adaptive right wing sentry container.
3. Tab 1 L1/L2 progressive disclosure: principal + C1-C5 risk, AI auto parameters, collapsible expert panel, one-click simulate + generate execution sheet, 16 cards collapsed to 3 human-readable big conclusion cards + L2 white-box evidence drawer.
4. Tab 2: compact top overview + floating cushion banner, "➕ 极速录基" Popover in table toolbar, strict dual-view mode separation.
5. Preserve all 13 session_state keys and 18 widget keys.
6. Run tests:
   py -3 -m pytest tests/test_gui_multi_ledger_stress.py tests/test_g8_ux_and_realtime_fusion.py tests/test_adv_final_closure.py

Write your report to:
d:\Google\Workspace\Wind\.agents\teamwork\worker_g9_m2_12\handoff.md

When complete, send a message to orchestrator_12 notifying completion.
