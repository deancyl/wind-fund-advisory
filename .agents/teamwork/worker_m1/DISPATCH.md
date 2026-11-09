## 2026-11-09T15:55:43Z
You are worker_m1, an implementation worker agent.
Your working directory is: d:\Google\Workspace\Wind\.agents\teamwork\worker_m1\

MANDATORY FIRST STEP:
Read the full user specification at:
d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md

Read the project scope and architecture at:
d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_18\PROJECT.md

Read the complete Explorer 1 blueprint and exact code proposals at:
d:\Google\Workspace\Wind\.agents\teamwork\explorer_g15_survey_1\handoff.md

YOUR MISSION (Milestone 1: Fix 5 UI/UX & Code Alignment Bugs + Remove 3D/RuleTree Vanity):
Follow the exact code solutions provided in explorer_g15_survey_1/handoff.md:
1. Chart Vanity Removal:
   - In AGY2_FundAdvisory/app_gui.py, replace render_monte_carlo_3d_chart with render_monte_carlo_stress_table (2D 3-crisis scenario comparison table + plain human conclusion), keeping render_monte_carlo_3d_chart as alias for compatibility.
   - In factor evolution popover, delete the RuleTree code box (st.code), replacing with a clean 2D parameter mechanism table explaining Mom_Win, Vol_Pulse, and Panic_Safe.
2. Right-Wing Alert Sentry Bug:
   - In app_gui.py render_dual_wing_advisory_dashboard (lines 2905-2909 & 3097-3115), fix condition to al_lvl in ("red", "critical", "CRITICAL") for red badge 🔴, al_lvl in ("yellow", "warning", "WARNING") for yellow badge 🟡.
   - Extract detail text via alert.get("desc") or alert.get("detail") or alert.get("message", "").
   - Extract action via alert.get("action") or alert.get("suggested_action", "").
   - Sort alerts by severity so red critical warnings are never drowned out by scale check warnings.
3. Tab 2 DataFrame Column Headers & Buttons Layout:
   - In app_gui.py (lines 4410 and 5732), map English columns phase, label, vol_ratio, slice_amount, strategy to 执行阶段, 窗口类型, 分配比例, 建议挂单金额(元), 微观执行策略 with percentage and currency formatting.
   - Delete the duplicate full-width blue overwrite button at the bottom of Tab 2 (line 5809).
   - In Tab 2 top toolbar, organize the 6-key action toolbar (quick fund entry, batch text, screenshot import, undo, sync, ledger settings).
4. Tab 4 Secondary Navigation & Fund Name Consistency:
   - In Tab 4 (lines 6976-6983), replace multi-row st.tabs with a single-row compact st.segmented_control (or horizontal radio fallback).
   - Unify 017436 name to "华安纳斯达克100ETF联接A" across portfolio_manager.py and strategy_bridge.py.
   - In strategy_bridge.py (lines 3758-3770), search CORE_STRATEGY_POOL / EXTENDED_FUND_CATALOG / resolve_fund_meta to eliminate 存量标的_XXXXXX, and fix false 7-day lock-ins on new buy targets.
5. "📱 手机极简盯盘视图 / 🖥️ 桌面专业模式" Toggle:
   - Add the toggle in sidebar (app_view_layout_mode).
   - In mobile mode, skip heavy wide tables and render the 3 clean single-column card streams: ① Today's total equity & estimated PnL, ② 14:30 action instructions, ③ Critical red/yellow risk alerts & mobile screenshot upload entry.
6. Build & Test Verification:
   - Run tests: py -3 -m pytest tests/test_infra.py
   - Run tests: py -3 -m pytest tests/test_adv_final_closure.py
   - If tests fail due to old button text or old 3D expander title assertions, update the non-read-only test assertions to match the new clean UI.
   - Verify 100% test pass.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

PHYSICAL SAFETY REDLINES:
严禁修改四个只读裁判文件 judge_engine.py、holdout_vault.py、AGENT_SPEC.md、tests/test_infra.py，严禁修改 DataLoader.simulate_execution 的默认函数签名与默认扣费逻辑。

OUTPUT:
Write your complete implementation report, including modified file paths, git diff summary, test execution commands, and test output into:
d:\Google\Workspace\Wind\.agents\teamwork\worker_m1\handoff.md
Update progress.md as you work.
When done, send a completion message back to the orchestrator.

## 2026-11-09T16:15:35Z
**Context**: Milestone 1 Implementation (UI/UX Bugs, 3D Chart Removal, Tab 2/4 Layout & Mobile View)
**Content**: Liveness query. It has been 19 minutes since dispatch. Please report your current progress, files modified, test status, and whether you are preparing handoff.md.
**Action**: Update your progress.md immediately with your current implementation status and finalize handoff.md.
