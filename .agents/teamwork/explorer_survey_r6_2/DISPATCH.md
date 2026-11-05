## 2026-11-03T14:18:07Z
You are Explorer 2 for the production-grade remodel of Wind Fund Advisory system.
Working directory: d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r6_2\

Read ORIGINAL_REQUEST.md first:
d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md

Your mission is read-only code and architecture exploration focused on R3 (Tab 2「步骤一：持仓账本」人体工学深度重构):
1. 第一层：4 张高信息密度资产概览卡：
   - Investigate the top section of Tab 2 Step 1 in `AGY2_FundAdvisory/app_gui.py`. Find the existing 4 full-width buttons / components that need to be removed.
   - Design the 4 aligned metric cards:
     Card 1: 持仓总市值 (附仓位占比)
     Card 2: 可用现金池 (含 `💰 修改现金` popover)
     Card 3: 累计浮动盈亏 (附盈亏率与今日盘中预估盈亏)
     Card 4: 锁仓与超额概览 (动态统计已满 7 天免罚赎回数与未满 7 天处于 1.5% 惩罚锁定期数，以及接管期 Alpha)
   - Identify existing calculations in `portfolio_manager.py` or `app_gui.py` for holding days, 7-day penalty lock check, and cash balance.
2. 第二层：一屏尽览的精炼可编辑持仓表：
   - Inspect the current `st.data_editor` in Tab 2 Step 1.
   - List all current columns. Show how to trim and consolidate to under 10 columns without horizontal scrolling.
   - Show how to merge "持有天数" (editable int) and "赎回费状态" (🟢 0.00% 免赎 / 🟡 0.50% / 🔴 1.50% 禁卖) into a single column.
   - Investigate allowing direct editing of "当前市值(元)":
     - How `st.data_editor` column configuration currently disables it.
     - When user edits and saves market value, how to compute `new_shares = new_market_val / current_nav` and update the portfolio, and conversely when shares are edited, update market value.
     - Trace how portfolio weights, total portfolio value, and session_state are updated.
   - Table action bar alignment:
     - Check current save, sync NAV, export CSV, and delete fund mechanisms.
     - Design a clean, single-line, equal-height action bar with delete as a Popover.
3. 第三层：合并底部折叠框为单一「🛠️ 账本工具坞」：
   - Locate the 3 existing expanders at the bottom of Tab 2 Step 1 (实盘接管档案, 快速录入持仓, FIFO 批次透视).
   - Show how to consolidate them into a single container or tabbed dock (`st.tabs`), where if portfolio is empty it expands/defaults to quick entry, and if portfolio has holdings it is compactly organized.

Write your complete structured survey report to:
`d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r6_2\survey_report.md`
Also produce `handoff.md` in your directory.
Send a completion message back with the report summary and file path when finished.
Remember: DO NOT modify any source code files. You are strictly read-only.
