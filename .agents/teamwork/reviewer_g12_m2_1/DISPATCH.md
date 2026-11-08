## 2026-11-08T16:13:03Z
You are teamwork_reviewer for Milestone 2 of G12 Generation.
Your Identity: teamwork_reviewer
Your Working Directory: d:\Google\Workspace\Wind\.agents\teamwork\reviewer_g12_m2_1\
Authoritative Request: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
Scope Document: d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_16\PROJECT.md
Worker Handoff Report: d:\Google\Workspace\Wind\.agents\teamwork\worker_g12_m2\handoff.md

Review tasks for Milestone 2:
1. Verify ActiveRiskSentry Dimension 4 stop-profit extensions in advisory_engine.py:
   - Right-side breakdown exit: pnl >= 10% + bias_20 < 0 + (slope < 0 or drop > 1.5*daily_vol) -> red alert, take_profit_ratio: 0.50.
   - High-water mark drawdown protection: pnl >= 10% + 60d hwm_dd >= 8% -> yellow alert, take_profit_ratio: 0.40.
   - Existing overbought (>6%), laddered profit (>15% & bias >5%), and deep loss branches preserved.
2. Verify app_gui.py dynamic take_profit_ratio session state injection and morning brief leading indicators.
3. Verify data_loader.py: auto_heal_sector_parquets, fetch_sector_core_etf_metrics, fetch_macro_cross_market_indicators, calc_financial_news_sentiment.
4. Run build/test commands:
   - py -3 -m pytest tests/test_infra.py
   - py -3 -m pytest tests/test_g12_stop_profit_and_sensors.py
   - py -3 -m pytest tests/test_adv_final_closure.py
5. Verify 4 referee files (judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py) are untouched (0 git diff).
6. Issue a definitive verdict: APPROVE or REQUEST_CHANGES.
Write your report to `d:\Google\Workspace\Wind\.agents\teamwork\reviewer_g12_m2_1\handoff.md` and send a message back.
