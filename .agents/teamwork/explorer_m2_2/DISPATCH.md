# Explorer M2-2 Dispatch
Assigned task: Investigate Features 9, 10 (Rolling DCA blind test table, dynamic friction bill, full fee backtest in strategy_bridge.py & app_gui.py).


## 2026-11-15T08:50:00Z
You are Explorer 2 for Milestone 2.
Your working directory: d:\Google\Workspace\Wind
Your state folder: d:\Google\Workspace\Wind\.agents\teamwork\explorer_m2_2
Read the authoritative user request: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
Read the project plan: d:\Google\Workspace\Wind\PROJECT.md
Read the scope document: d:\Google\Workspace\Wind\.agents\teamwork\sub_orch_m2\SCOPE.md
Read previous survey findings: d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_2\handoff.md
Read E2E test file: d:\Google\Workspace\Wind\tests\test_g19_m2_routing_and_rolling_dca.py

Your specific mission is to deeply investigate and provide concrete, exact implementation blueprints for Features 9 and 10:
1. Feature 9: 近 3 年滚动发车盲测胜率实证表 (strategy_bridge.py, app_gui.py)
   - Inspect strategy_bridge.py and app_gui.py for backtest and rolling DCA implementations.
   - Investigate how rolling DCA (滚动发车) should be implemented:
     * Over past 3 years, rolling start dates by bi-monthly (双月) or quarterly (季度) intervals.
     * Holding periods: 180 days and 365 days.
     * Cut off any lookahead bias (未来函数).
     * Strictly deduct: real purchase fees (申购费), tiered redemption fees (阶梯赎回费, e.g. <7d 1.5%, <30d, <180d), sales service fee (C类销售服务费), and purchase limit splitting rules (限购拆单).
     * Calculate: real positive return win rate (正收益胜率), average net return (平均到手净收益率), average excess return vs CSI 300 benchmark (相对沪深300平均超额收益).
   - In app_gui.py, locate the blind backtest section (盲测模块) and plan how to render the empirical results table and summary card cleanly.
   - Inspect tests in test_g19_m2_routing_and_rolling_dca.py for Feature 9 to ensure all expected function names, return dict keys, and assertion criteria are met.

2. Feature 10: 摩擦账单动态精算与回测全额扣费 (strategy_bridge.py)
   - Find `calculate_mutual_fund_friction_bill` in strategy_bridge.py.
   - Identify the hardcoded pseudo constants: `cagr_val=16.85, mdd_all=-16.76, mdd_1y=-4.52, recovery_days=22, dividend_yield=3.42`.
   - Formulate how to dynamically compute these metrics from actual `weights` and the portfolio's underlying funds/holdings historical data or benchmark metrics without hardcoding.
   - Find `run_historical_time_machine_backtest` in strategy_bridge.py.
   - Implement complete fee deductions:
     * Public fund daily management fee + custody fee: 0.75% / 250 trading days deducted daily.
     * Class A redemption fee for holdings < 180 days (e.g. 0.5% or tiered).
     * Purchase fee friction (申购费率).
   - Inspect tests in test_g19_m2_routing_and_rolling_dca.py for Feature 10 to ensure exact calculation formulas and assertions pass.

Output:
Write a comprehensive, precise technical handoff report to `d:\Google\Workspace\Wind\.agents\teamwork\explorer_m2_2\handoff.md` with:
- Exact line numbers and code snippets in existing files
- Concrete proposed code modifications and diffs
- Verification against test_g19_m2_routing_and_rolling_dca.py
Send a message back when complete.
