## 2026-11-07T15:37:49Z

You are Worker G8-1 (Role: Lead Implementation & QA Worker).
Your working directory is: d:\Google\Workspace\Wind\.agents\teamwork\worker_g8_1\

MANDATORY: You MUST read ORIGINAL_REQUEST.md before starting work:
d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md

You must also read the master project scope:
d:\Google\Workspace\Wind\.agents\teamwork\orchestrator\PROJECT.md

And read the complete technical analysis and specifications from the 3 Explorers:
- d:\Google\Workspace\Wind\.agents\teamwork\explorer_g8_1\analysis.md (and handoff.md)
- d:\Google\Workspace\Wind\.agents\teamwork\explorer_g8_2\analysis.md (and handoff.md)
- d:\Google\Workspace\Wind\.agents\teamwork\explorer_g8_3\analysis.md (and handoff.md)
- c:\Users\deanc\Downloads\agy2_ui_ux_audit_and_fix_plan.md
- c:\Users\deanc\Downloads\agy2_fundadvisory_ux_audit_and_fix_plan.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT
hardcode test results, create dummy/facade implementations, or
circumvent the intended task. A teamwork_auditor will independently
verify your work. Integrity violations WILL be detected and your
work WILL be rejected.

FOUR STRICTLY READ-ONLY REFEREE FILES (ZERO CHARACTERS MODIFIED):
1. judge_engine.py / AGY2_FundAdvisory/judge_engine.py
2. holdout_vault.py / AGY2_FundAdvisory/holdout_vault.py
3. AGENT_SPEC.md / AGY2_FundAdvisory/AGENT_SPEC.md
4. tests/test_infra.py
Also STRICTLY UNTOUCHED: DataLoader.simulate_execution default function signature and deduction logic.

YOUR WRITE OWNERSHIP:
- AGY2_FundAdvisory/app_gui.py
- AGY2_FundAdvisory/portfolio_manager.py
- AGY2_FundAdvisory/data_loader.py
- AGY2_FundAdvisory/advisory_engine.py
- tests/test_g8_ux_and_realtime_fusion.py

DETAILED TASKS TO IMPLEMENT:

1. Task 1: Tab 2 Dual-View Strict Physical Branch Isolation (Item 1) & Slider/Slogan Cleanup (Item 5) in app_gui.py:
   - Rewrite is_t2_main_mode branch around line 4213-5776:
     * When is_t2_main_mode == True: render multi-ledger bar, cushion stress card, 4 metric cards, quick add fund bar, holdings detail table, Step 1 bottom buttons, Step 2 timing diagnosis, Step 3 rebalance execution orders. Strictly DO NOT render the bottom ledger tools expander (st.expander("🛠️ 账本工具坞..."))!
     * When is_t2_main_mode == False: hide Step 1 holdings table, Step 2, and Step 3; directly on the wide canvas, render the 6 tool tabs (dock_tab1 to dock_tab6) without expander wrapper.
     * When user clicks btn_tab2_diagnose or btn_tab2_all from maintenance mode, auto-heal tab2_view_mode to main mode so diagnosis renders.
   - Clean up duplicate "免折腾调仓缓冲带 (%)" sliders:
     * Delete slider in Step 1 top (around lines 4260-4279).
     * Delete slider in Step 1 bottom (around lines 5060-5077), keeping compatibility comment: `# tab2_rebal_buf_slider_bot`.
     * Keep single control point in Step 3 (around lines 5363-5379).
   - Delete duplicate demo/undo/refresh buttons in dock_tab3 (around lines 4798-4835), preserving the verified static contract `<b>{len(pm.holdings)} 只</b>`.
   - In right-wing sentry header: remove leftover slogan `[主动风险预警哨 · 四维巡检升级版]`, optimize sentry container height to 380px (`with st.container(height=380):`), and ensure no vertical button truncation.

2. Task 2: Holdings Table Uncommitted Edits Protection & Auto-Commit Hooks (Item 4) in app_gui.py:
   - Implement `_has_uncommitted_holdings_changes(edited_df, current_df)` comparing market value, shares, cost, or rebalance intent.
   - Above st.data_editor, use `warn_placeholder = st.empty()`. After st.data_editor returns, if uncommitted changes exist, render prominent warning banner in the placeholder.
   - In peripheral action buttons (Quick add fund btn_bar_add_holding, Cash pool edit btn_confirm_cash_pop_tb, Sync real NAV btn_sync_holdings_tab2, Delete holding btn_pop_del_confirm_tab2), prepend auto-commit hook: `self._commit_edited_holdings_table(edited_table, pm)` before logic executes.

3. Task 3: Large Capital Chinese Numeral Formatting Helper (Item 7) in app_gui.py:
   - Implement `format_chinese_amount(val: float) -> str` (e.g. `¥100,000.00 折合 10.00 万元`).
   - Render dynamic st.caption below: Tab 1 拟投资总本金 (both modes), Tab 2 现金池修改, 新增补仓金额, 提现金额, 极速录基持有金额, 新建账本初始现金.

4. Task 4: High-Risk Overwrite Popover Confirmation Guard & Push Undo Snapshot / Rollback (Item 2) in app_gui.py & portfolio_manager.py:
   - In portfolio_manager.py: implement `_push_undo_snapshot(self)` and call it in `apply_zero_start_blueprint` before clearing holdings.
   - In app_gui.py (Tab 1 Step 3 bottom): replace direct st.button with st.popover confirmation dialog displaying target ledger name, current holding count, total equity, in-transit orders, and new plan capital; add `st.checkbox` confirmation gate; on execute record overwrite state; render green card with `↩️ 撤销本次覆盖` (calls pm.undo()) and `👀 前往持仓调仓`.

5. Task 5: Front Page Dual-Wing Cross-Tab Real DOM Navigation Script & Execution Banner (Item 3) in app_gui.py:
   - Import `streamlit.components.v1 as components`.
   - In radar "➕ 入备选池", sentry "🔒 一键批量锁定", single alert actions, and "🔍 穿透到底层", set `st.session_state["pending_cross_tab_jump"]` and complete the 6 missing sentry alert type parameter pass-throughs.
   - Inject lightweight `components.html(height=0, width=0)` script targeting parent `role="tablist"` buttons with smooth scroll and clearing the jump state.
   - Render high-visibility "跨区指令已生效承接横幅" at the bottom of the dual-wing sentry container.

6. Task 6: Real-Time Radar Quotes, Live News Flash Ingestion & 4D Evidence Chain (Item 6) in data_loader.py, advisory_engine.py, app_gui.py:
   - In data_loader.py: bind `fetch_realtime_market_news_and_catalysts` and `fetch_custom_realtime_indices` to DataLoader class with 2s timeout and local cache fallback.
   - In advisory_engine.py: infuse real-time index percentage changes and points into OpportunityRadarEngine dynamic metrics; ensure `evaluate_sector` returns `core_logic`, `realtime_chg_pct`, `realtime_point`, and 4D sub-scores (`valuation`, `momentum`, `kaufman_snr`, `anti_crowding`).
   - In app_gui.py: morning pulse card displays second-level timestamp `⏱️ 数据感知时间: YYYY-MM-DD HH:MM:SS` and latest flash news item; Top 3 sector cards display real-time change pill, 4D micro-badges, and selection logic justification `💡 入选依据: ...`.

7. Task 7: Implement Test Suite & Run Full Verification:
   - Write tests/test_g8_ux_and_realtime_fusion.py covering all G8 features.
   - Execute full test suite:
     py -3 -m pytest tests/test_infra.py tests/test_adv_final_closure.py tests/test_g3_evolution_loop.py tests/test_gui_multi_ledger_stress.py tests/test_g7_architecture_and_decoupling.py tests/test_g8_ux_and_realtime_fusion.py -v
   - Verify 100% pass and verify 4 referee files zero diff.
   - Update progress.md and write complete handoff.md in d:\Google\Workspace\Wind\.agents\teamwork\worker_g8_1\handoff.md.
