## 2026-11-07T15:25:40Z

You are Explorer G8-3 (Role: Real-Time Radar & Test Explorer).
Your working directory is: d:\Google\Workspace\Wind\.agents\teamwork\explorer_g8_3\
You must read ORIGINAL_REQUEST.md before starting work: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
Also reference external audit documents:
- c:\Users\deanc\Downloads\agy2_ui_ux_audit_and_fix_plan.md
- c:\Users\deanc\Downloads\agy2_fundadvisory_ux_audit_and_fix_plan.md

Your mission is technical investigation (DO NOT edit source code or run build/test commands):
1. Item 6 (P1): 打通机会雷达盘中实时行情融合、实时快讯感知与四维评分证据链（涉及 data_loader.py, advisory_engine.py, app_gui.py）。
   - Investigate data_loader.py: How are real-time index quotes and market news currently fetched or cached? Design the implementation of real-time market news / macro pulse crawler and parser with 2-second timeout and local persistent cache fallback.
   - Investigate advisory_engine.py: Examine OpportunityRadarEngine and its calculation of 14 major sector dynamic metrics. How to infuse intraday real-time index quotes (change pct and points) into the sector metrics calculation?
   - Investigate app_gui.py:
     a) Front page "今日市场脉搏晨报": Locate where it is rendered. How to display a second-precision timestamp (e.g. 数据感知时间: YYYY-MM-DD HH:MM:SS) and latest market news/flash summary.
     b) Top 3 sector cards: Locate where they are rendered. How to display today's real-time intraday change pct, the 4-dimensional sub-score breakdown (Valuation, Momentum, Kaufman SNR, Anti-Crowding) from the genetic evolution model, and the core selection logic justification.
2. Examine Existing Tests and Design G8 Test Suite:
   - Check tests in tests/: test_infra.py (REMEMBER: STRICTLY READ-ONLY), test_adv_final_closure.py, test_g3_evolution_loop.py, test_gui_multi_ledger_stress.py, test_g7_architecture_and_decoupling.py.
   - Design new dedicated tests for G8 (e.g. tests/test_g8_ux_and_realtime_fusion.py or additions to test_g7/test_gui):
     a) Tab 2 physical view mode strict isolation (is_t2_main_mode branch test);
     b) Holdings table uncommitted edits automatic protection & commit before other actions;
     c) Real-time intraday radar quote fusion and 4D score breakdown;
     d) Large capital Chinese numeral formatting;
     e) Overwrite undo snapshot & rollback logic.
3. Verify read-only constraints: Four read-only files (judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py) and DataLoader.simulate_execution signature/deduction logic.

Write your complete analysis with exact line numbers, code structures, test blueprints, and recommended implementation strategy to d:\Google\Workspace\Wind\.agents\teamwork\explorer_g8_3\analysis.md and handoff.md. Report back via send_message when complete.
