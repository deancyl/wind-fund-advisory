## 2026-10-29T09:16:40Z
You are Worker M1 (worker_m1).
Your working directory is: d:\Google\Workspace\Wind\.agents\teamwork\worker_m1
Your parent conversation ID is: 5fd996d1-bc98-447a-9f35-c5aef5be2e1c (Project Orchestrator).

MANDATORY FIRST STEP:
Read the following authoritative documents before starting work:
1. d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
2. d:\Google\Workspace\Wind\PROJECT.md
3. d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_1\handoff.md
4. d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_2\handoff.md
5. d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_3\handoff.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

EXCLUSIVE WRITE OWNERSHIP:
You own `d:\Google\Workspace\Wind\AGY2_FundAdvisory\portfolio_manager.py`.
DO NOT modify any other production source files or tests.
DO NOT touch read-only files (`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`).

OBJECTIVE (Milestone 1 - R1 Look-Through Risk Screen Engine):
In `d:\Google\Workspace\Wind\AGY2_FundAdvisory\portfolio_manager.py`:
1. Connect with `WindToolkit` (`from src.toolkit import WindToolkit`).
2. Add stock name-to-symbol resolver / mapping (covering common heavy holdings: 贵州茅台->600519.SH, 宁德时代->300750.SZ, 中芯国际->688981.SH, 海光信息->688041.SH, 中国神华->601088.SH, 比亚迪->002594.SZ, 招商银行->600036.SH, 中国平安->601318.SH, 五粮液->000858.SZ, 立讯精密->002475.SZ, 紫金矿业->601899.SH, 恒瑞医药->600276.SH, 迈瑞医疗->300760.SZ, 美的集团->000333.SZ, 长江电力->600900.SH, 东方财富->300059.SZ, etc., with fallback to MasterDictParser or duckdb v_financial_risk_screen lookup).
3. Implement `screen_fund_look_through_risk(self, fund_code: str) -> Dict[str, Any]`:
   - Retrieve top 10 heavy holdings for the fund (from `FUND_LOOK_THROUGH_DATA` or `_fetch_external_fund_holdings`).
   - Distinguish non-A-share assets (pure bond e.g. '002351', gold ETF e.g. '000216', QDII e.g. '050025'): these are non-equity / immune to A-share financial fraud and have penetration_risk_score = 0.0, risk_level = "Safe", risk_badge = "🟢 健康".
   - For A-share equity funds, evaluate each top stock:
     * Goodwill ratio: `goodwill_ratio_pct > 30%` (deduct 30 pts; >40% deduct 40 pts)
     * Double-high fraud: `double_high_risk == True` (deduct 40 pts)
     * Share pledge: `pledge_ratio_controlling_pct > 80%` or `warning_close_line_status == "击穿平仓线"` (deduct 35 pts; 50-80% deduct 15 pts)
     * Lockup expiration: 30~90 days unlock with high risk / large market value (deduct 20 pts)
     * FCF negative: deduct 10 pts
     * Stock score: max(0, 100 - sum(deductions)). Stock risk level: >=80 Safe 🟢, 60~80 Watch 🟡, <60 Danger 🔴.
   - Fund penetration risk score = average(100 - stock_score) across top stocks.
   - Return detailed dict per Interface Contract in PROJECT.md.
4. Implement `calculate_portfolio_penetration_risk(self) -> Dict[str, Any]`:
   - Compute weighted average penetration risk index across active holdings in current portfolio ledger:
     portfolio_risk_index = sum(weight * fund_risk_score)
   - Risk classification:
     * <= 20.0 and no Danger stocks: 🟢 健康 (Safe)
     * 20.0 ~ 45.0 or 1 Danger stock: 🟡 关注 (Watch)
     * > 45.0 or >=2 Danger stocks: 🔴 预警 (Danger)
   - Return structured dict per Interface Contract in PROJECT.md.
5. Verify that existing 112 tests pass without any regression:
   Run: `python -m pytest AGY2_FundAdvisory/tests`
6. Write your handoff report to `d:\Google\Workspace\Wind\.agents\teamwork\worker_m1\handoff.md` and send message to parent.
