# Explorer M2-1 Dispatch
Assigned task: Investigate Features 7, 8, 12, 13 (UI Routing, CSS Styling, Mobile Responsive, Tab 2 Tool Dock & Narrative Cards in app_gui.py).


## 2026-11-15T08:49:23Z
[Message] timestamp=2026-11-15T08:49:23Z sender=14ba2224-f6f2-408b-8da5-a5ce3b8fff98 priority=MESSAGE_PRIORITY_HIGH content=You are Explorer 1 for Milestone 2.
Your working directory: d:\Google\Workspace\Wind
Your state folder: d:\Google\Workspace\Wind\.agents\teamwork\explorer_m2_1
Read the authoritative user request: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
Read the project plan: d:\Google\Workspace\Wind\PROJECT.md
Read the scope document: d:\Google\Workspace\Wind\.agents\teamwork\sub_orch_m2\SCOPE.md
Read previous survey findings: d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_2\handoff.md
Read E2E test file: d:\Google\Workspace\Wind\tests\test_g19_m2_routing_and_rolling_dca.py

Your specific mission is to deeply investigate and provide concrete, exact implementation blueprints for Features 7, 8, 12, and 13:
1. Feature 7: 首次加载存量持仓账本自动路由 (app_gui.py)
   - Inspect app_gui.py around line 2715 where `pm` is initialized.
   - Analyze how to add the initial loading check: when session state has not performed initial routing and current ledger has >= 10 holdings (`len(pm.portfolio) >= 10` or similar), set initial routing completed flag, set `tab2_view_mode = "持仓诊断与智能调仓 (主流程)"` (or whatever the exact string is in app_gui.py), write `pending_cross_tab_jump = 1` (or the exact index for Tab 2), and set `tab2_diagnosed = True` and `tab2_rebalanced = True`.
   - Inspect tests in test_g19_m2_routing_and_rolling_dca.py for Feature 7 to match exact variable names and session state keys.

2. Feature 8: 样式集中合并与手机端列选择器 (app_gui.py)
   - Find `render_chief_advisor_memo_card` and its internal CSS (e.g. `chief-memo-container` style).
   - Find the master CSS block in app_gui.py and plan how to move this style into the global CSS cleanly so it is not injected multiple times.
   - Inspect the mobile button group CSS rule in global CSS, check where `stColumn` selector is missing, and how to add `:not(:has([data-testid="stNumberInput"]))` to exclude number input +/- buttons.
   - Check test assertions in test_g19_m2_routing_and_rolling_dca.py for Feature 8.

3. Feature 12: IS_MOBILE_VIEW 激活与响应式布局 (app_gui.py)
   - Check where `IS_MOBILE_VIEW` is defined in app_gui.py and how it is determined (e.g., query params, screen width detection, or viewport detection).
   - Check where critical multi-column layouts (like `st.columns`) should adaptively switch to single-column containers when `IS_MOBILE_VIEW` is True.
   - Inspect test assertions in test_g19_m2_routing_and_rolling_dca.py for Feature 12.

4. Feature 13: Tab 2 工具坞扁平化与前置人话解读卡片 (app_gui.py)
   - Locate Tab 2 tool dock three-level nesting in app_gui.py. Plan how to flatten `st.tabs` into horizontal `st.radio` without breaking any sub-tool functionality.
   - Locate Tab 2 Brinson attribution, Tab 4 cross-holding heatmap, and Tab 4 trend deviation vs crowding four-quadrant scatter in app_gui.py. Plan the pre-positioned narrative cards ("前置人话解读卡片") for each of them.
   - Check test assertions in test_g19_m2_routing_and_rolling_dca.py for Feature 13.

Output:
Write a comprehensive, precise technical handoff report to `d:\Google\Workspace\Wind\.agents\teamwork\explorer_m2_1\handoff.md` with:
- Exact line numbers and code snippets in existing files
- Concrete proposed code modifications and diffs
- Verification against test_g19_m2_routing_and_rolling_dca.py
Send a message back when complete.
