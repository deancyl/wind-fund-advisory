## 2026-11-03T14:17:58Z
You are Explorer 1 for the production-grade remodel of Wind Fund Advisory system.
Working directory: d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r6_1\

Read ORIGINAL_REQUEST.md first:
d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md

Your mission is read-only code and architecture exploration focused on R1 and R2:
1. R1 攻防红线数据源对齐：
   - Investigate where the "攻防红线" (surge_line and breakdown_line) are currently calculated and displayed in `AGY2_FundAdvisory/app_gui.py` (both in the main dashboard card 2 and the sidebar).
   - Find how `snapshot["trigger_lines"]` provides `surge_line` and `breakdown_line`, identify the discrepancies or hardcoded calculations, and document the exact lines and changes needed to ensure 100% unified single source of truth.
2. R1 核心指数实时行情条视觉层级提升：
   - Investigate the top 6 core index ticker bar in `AGY2_FundAdvisory/app_gui.py` (CSS classes `.index-pill-point`, `.index-pill`, `.index-badge`, `.index-pill-name`, etc.).
   - Analyze font sizes, weights, padding, font-family (tabular/monospace), and viewport layout.
   - Propose exact CSS modifications to upgrade point values to 15px~16px bold monospace, name/badge to 13px, appropriate padding, and ensuring 0 text truncation or squashing across screen sizes following GEMINI.md Rules 14 & 15.
3. R2 侧边栏功能化重塑（全局控盘与风控护栏中枢）：
   - Investigate the current sidebar implementation in `app_gui.py`.
   - Global Target Sync (🎯 全局目标与档位联动器): How `st.session_state.target_return_val` and `active_tier_val` are managed and how they can be adjusted in the sidebar and bidirectionally synced with Tab 2 and Tab 3.
   - Global Execution Guardrails (🛡️ 实盘交易风控护栏):
     - Single-day purchase limit filter threshold (`["不限 (自动拆单承接)", "过滤日限额 < ¥1,000 标的", "过滤日限额 < ¥5,000 标的"]`): How Tab 1 fund selection and portfolio construction currently handle purchase limits, and where the replacement with alternative candidates in the same category needs to occur.
     - Rebalance Buffer (`min_buffer_pct` slider, 1.0%~5.0%, default 3.0%): How Tab 2 rebalance engine (`rebalance_decision` / `min_buffer_pct`) currently receives buffer parameters and how the sidebar slider should pass to it.
   - Environment and Snapshot Management (🗄️ 账本环境与快照管理): How demo portfolio loading (`🚀 加载演示组合`), snapshot undo (`↩️ 一键撤销快照`), and global sync (`🔄 全局同步行情与估值`) are currently implemented, and how to cleanly relocate them into the sidebar.
