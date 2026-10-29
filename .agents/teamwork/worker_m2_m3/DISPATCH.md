## 2026-10-29T10:01:11Z
You are Worker Milestone 2 & 3 (worker_m2_m3).
Your working directory is: d:\Google\Workspace\Wind\.agents\teamwork\worker_m2_m3
Your parent conversation ID is: 5fd996d1-bc98-447a-9f35-c5aef5be2e1c (Project Orchestrator).

MANDATORY FIRST STEP:
Read the following authoritative documents before starting work:
1. d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
2. d:\Google\Workspace\Wind\PROJECT.md
3. d:\Google\Workspace\Wind\TEST_READY.md
4. d:\Google\Workspace\Wind\AGY2_FundAdvisory\tests\test_toolkit_integration.py
5. d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_1\handoff.md
6. d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_2\handoff.md
7. d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_3\handoff.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

EXCLUSIVE WRITE OWNERSHIP:
You own:
- d:\Google\Workspace\Wind\AGY2_FundAdvisory\strategy_bridge.py
- d:\Google\Workspace\Wind\AGY2_FundAdvisory\portfolio_manager.py (adding get_fund_smart_money_crowding)
DO NOT touch read-only files (judge_engine.py, holdout_vault.py, AGENT_SPEC.md, test_infra.py).

OBJECTIVE:
Implement Requirement R2 (Macro High-Frequency Liquidity Thermometer & Dual-Track Radar) and Requirement R3 (Smart Money & Crowding Monitor):

1. In `AGY2_FundAdvisory/strategy_bridge.py`:
   - Connect with `WindToolkit` (`from src.toolkit import WindToolkit`).
   - In `get_latest_market_snapshot(...)`:
     * Call `wk.macro_liquidity.get_liquidity_thermometer()`.
     * Inject into the returned snapshot dictionary:
       `dr007`: float,
       `policy_rate_7d`: float,
       `dr007_spread_bp`: float,
       `liquidity_status`: str ("流动性泛滥" / "合理充裕" / "紧平衡" / "结构性偏紧" / "宽松" / "中性" / "收紧"),
       `liquidity_badge`: str ("🟢 宽松" if spread_bp <= 15.0 else "🟡 中性" if spread_bp <= 35.0 else "🔴 收紧"),
       `recent_7d_net_injection_billion`: float,
       `omo_latest_stance`: str,
       `advisory_takeaway`: str,
       `dual_track_radar`: dict containing:
         - `trend_stance`: "BULL" | "STABLE" | "BEAR" (from MA20/ERP)
         - `liquidity_stance`: "宽松" | "中性" | "收紧"
         - `combined_action`: str (e.g. "天时地利·顺风主升", "估值扩张受阻·流动性摩擦", "股息再投·底仓稳健", "防御升温·短端避险", "极端防御触发")
         - `defensive_triggered`: bool (True when spread_bp > 45.0, or BEAR + 收紧)
     * When `defensive_triggered` is True, in `generate_zero_start_blueprint` and `generate_ai_rebalance_orders`, append defensive allocation advice (e.g. "触发极端防御配置：压降高 Beta 权益，纯债与黄金配置上调至 65%~70%").

2. In `AGY2_FundAdvisory/portfolio_manager.py`:
   - Implement `get_fund_smart_money_crowding(self, fund_code: str) -> Dict[str, Any]`:
     * Query `FUND_LOOK_THROUGH_DATA` or `_fetch_external_fund_holdings` for top heavy stocks.
     * Use `resolve_stock_symbol` to resolve stock symbols.
     * Query `wk.institutional_holdings.fetch_northbound_holdings(symbol)` for top stocks, aggregating 1D / 5D net change value.
     * Query `wk.chips_market.fetch_shareholder_concentration(symbol)` for top stocks, determining concentration trend ("筹码集中" / "筹码分散" / "筹码平稳").
     * Query `wk.institutional_holdings.fetch_fund_heavyweight_stocks()` to get fund crowding degree ("极度拥挤" / "中度抱团" / "相对分散").
     * Query `wk.chips_market.get_institutional_dragon_tiger_summary()` to get institutional sentiment & net inflow.
     * Determine `crowding_warning`: True if crowding_degree == "极度拥挤" and (northbound_5d_net < -1000.0 or concentration_trend == "筹码分散").
     * Return structured dict per PROJECT.md interface contract.

3. In `AGY2_FundAdvisory/strategy_bridge.py`:
   - In `generate_ai_rebalance_orders(...)`:
     * When proposing rebalance orders, query `pm.get_fund_smart_money_crowding(fund_code)`. If `crowding_warning` is True, inject caution advice ("抱团松动踩踏高危：严禁单笔重仓追高！建议执行分批定投或下调增配目标").

VERIFICATION:
Run full tests:
`python -m pytest AGY2_FundAdvisory/tests`
Verify that ALL tests (existing + test_toolkit_integration + adversarial tests) pass 100%!
Verify read-only invariants remain untouched.

Write your handoff report to `d:\Google\Workspace\Wind\.agents\teamwork\worker_m2_m3\handoff.md` and send a message to parent.
