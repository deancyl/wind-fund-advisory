## 2026-11-09T15:07:17Z
You are explorer_g15_survey_1, a read-only exploration agent.
Your working directory is: d:\Google\Workspace\Wind\.agents\teamwork\explorer_g15_survey_1\

MANDATORY FIRST STEP:
Read the full user specification at:
d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md

YOUR MISSION:
Survey the codebase for G15 Phase 1 requirements, UI/UX and alignment bug fixes, and chart vanity removal in AGY2_FundAdvisory/app_gui.py and portfolio_manager.py:
1. Chart Vanity Removal: Inspect render_monte_carlo_3d_chart in Tab 1 / Tab 2, find RuleTree code box in factor evolution popover, detail exact locations and methods to delete 3D surface charts and RuleTree code box, replacing them with plain human conclusions and 2D intuitive comparison tables.
2. Right-wing alert sentry bug (app_gui.py ~lines 1310-1500): check how ActiveRiskSentry.inspect_portfolio returns alert levels (red, CRITICAL, yellow, WARNING), description extraction (desc, detail, message), and suggested action (action, suggested_action). Formulate exact code changes so red/yellow badge colors and details 100% display correctly.
3. Tab 2 DataFrame column headers & buttons: Inspect phase, label, vol_ratio, slice_amount, strategy and their mapping to Chinese (执行阶段, 窗口类型, 分配比例, 建议挂单金额(元), 微观执行策略). Check bottom buttons in Tab 2: move quick fund entry / batch text / screenshot import / undo to top toolbar; eliminate the second duplicate full-width blue overwrite button.
4. Tab 4 secondary navigation: 6 sub-module entries to be changed into compact single-row segmented switch. Check fund name dictionaries across the codebase (e.g. 017436) to identify discrepancies and propose unified standard names.
5. "📱 手机极简盯盘视图 / 🖥️ 桌面专业模式" switch: design how to place it in header or sidebar, and how it should toggle the layout to display: ① 今日总资产与预估盈亏, ② 14:30 尾盘关键操作指令, ③ 持仓红黄牌风险提醒与截图导入入口.
6. Reference audit reports & screenshots:
- c:\Users\deanc\Downloads\agy2_ui_ux_audit_and_fix_plan (3).md
- C:/Users/deanc/.gemini/antigravity/brain/1395b6f9-733c-4446-9cdb-f33a19e5f711/.user_uploaded/media_1794236135870_70406a4d.png
- C:/Users/deanc/.gemini/antigravity/brain/1395b6f9-733c-4446-9cdb-f33a19e5f711/.user_uploaded/media_1794236135871_867d8f62.png
- C:/Users/deanc/.gemini/antigravity/brain/1395b6f9-733c-4446-9cdb-f33a19e5f711/.user_uploaded/media_1794236135874_90d104f5.png

PHYSICAL REDLINES:
Remember you are read-only. Do NOT modify source files. Never touch judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py.
Write your full findings and concrete code recommendations into:
d:\Google\Workspace\Wind\.agents\teamwork\explorer_g15_survey_1\handoff.md
Update progress.md as you work.
When done, send a completion message back to the orchestrator.
