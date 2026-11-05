## 2026-11-05T16:16:18Z
You are Explorer 3 (UI/UX & NAV Tracking & Verification Explorer).
Working directory: d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r10_3
Original user request path: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md

[HARD CONSTRAINTS]
- Read-only technical investigation. DO NOT write or modify source code files.
- DO NOT run build/test execution yourself.
- Write your investigation findings to handoff.md and analysis.md in your working directory.
- When done, call send_message to report back to caller with a clear summary and the absolute path to your handoff.md.

[SURVEY OBJECTIVES]
Investigate Section 3 & Section 4 of ORIGINAL_REQUEST.md (UI/UX 关键体验痛点治理 & 自动化测试与交付验证):
1. First-screen visual elevation (首屏视觉提权):
   - In app_gui.py, inspect the top dashboard ("双翼智能投顾看板", left wing pulse/radar, right wing risk sentry).
   - How to implement a compact single-line high-density summary bar at the top:
     「📢 今日脉搏晨报 + 🎯 Top 3 机会赛道胶囊 + 🚨 风险预警汇总徽章（如：发现 X 项风险）」
   - How to support one-click folding/unfolding of the dual-wing detailed cards, allowing users to free up precious screen space for Tabs 1-4.
2. Tab 2 st.data_editor unsaved modification auto-commit mechanism:
   - Investigate how `st.data_editor` edits are handled in Tab 2.
   - Design `_auto_commit_pending_table_edits(edited_table, pm)`:
     a. How to detect diffs between `edited_table` and `pm.holdings`.
     b. How to display a prominent warning "检测到表格内有未保存的修改".
     c. When user clicks "💾 保存修改并入库", "🔍 诊断今日调仓时机", or "🚀 一键执行全案", automatically invoke `_auto_commit_pending_table_edits` before diagnosis/rebalancing so zero user edits are lost.
3. Realized Account NAV History Curve (实盘账本历史净值记账曲线) & One-click order follow:
   - In portfolio_manager.py:
     - Check `save_state` and how `nav_history` can be recorded: date, total_assets, unit_nav, benchmark HS300 index level on `save_state(record_snapshot=True)` or NAV sync.
     - Where ledger JSON stores `nav_history`.
   - In app_gui.py Tab 2:
     - In "🗄️ 账本环境与实盘档案" sub-page, how to plot the 《实盘账户累计净值 vs 沪深300基准走势图》.
     - In Tab 2 step 3 rebalance order execution sheet bottom, add button:
       「✅ 我已在手机端按此方案下单 -> 一键将调仓单同步至当前账本持仓」 and how to update holdings.
4. Test Baseline & Verification Plan (Section 4):
   - Review existing tests and `tests/test_infra.py` (MUST NOT MODIFY).
   - Formulate test design for new assertions:
     * RADAR_SECTOR_CATALOG["dividend_low_vol"]["benchmark_index"] is H30269 (NOT 000978).
     * No "保本率" in UI source code (all replaced by "正收益概率 (≥0%)" or "本金安全率").
     * QDII fund (050025) identified as cross-timezone T+2 confirm, T+6+ redeem, excluded from same-company T+1 conversion.
     * Streamlit AppTest tests all 4 tabs with 0 exceptions.

Produce a detailed, structured handoff.md in your working directory.
