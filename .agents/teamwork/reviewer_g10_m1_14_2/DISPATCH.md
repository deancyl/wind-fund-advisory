## 2026-11-08T09:46:58Z
You are Reviewer 2 (`reviewer_g10_m1_14_2`) in the G10 visual subtraction, filter & UI elevation mission.

## Identity & Workspace
- Type: teamwork_reviewer
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\reviewer_g10_m1_14_2\
- Authoritative user request file: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
- Worker handoff report: d:\Google\Workspace\Wind\.agents\teamwork\worker_g10_m1_14\handoff.md

## Objective
Independently review the backend quant logic, news filters, and CVaR scaling implemented in `advisory_engine.py`, `data_loader.py`, and `portfolio_manager.py`:
1. `advisory_engine.py`:
   - In `_synthesize_quantitative_evidence`: verify that when Kaufman ER < 0.35, "右侧共振稳步上行" is strictly prohibited; if slope is positive, verify it outputs "底部震荡筑底、均线初现企稳".
   - Verify `core_logic` preserves `【量化因果链】` prefix for test assertions.
   - Verify `concise_logic` is <= 18 Chinese characters.
2. `data_loader.py`:
   - In `DataLoader.fetch_realtime_market_news_and_catalysts`: verify 32 whitelist keywords and 9 blacklist keywords (`无人机, 拦截, 联军, 导弹, 武装, 袭击, 交火, 赛事, 娱乐`).
   - Verify non-financial news is filtered out.
   - Verify turnover/breadth fallback when all news is filtered.
3. `portfolio_manager.py`:
   - In `simulate_portfolio_cvar_bootstrap_instance`: verify calibration of crisis duration drift and daily volatility scaling to align with Tab 3 (~12% scale).
4. Run tests:
   `py -3 -m pytest tests/test_infra.py tests/test_g3_evolution_loop.py tests/test_g10_correlation_liquidity_and_stress.py tests/test_challenger_g9_m1_adversarial.py tests/test_challenger_g9_m2_adversarial.py tests/test_challenger_g9_m2_stress.py tests/test_g8_ux_and_realtime_fusion.py`
5. Write your 5-component report to `d:\Google\Workspace\Wind\.agents\teamwork\reviewer_g10_m1_14_2\handoff.md` and conclude with a clear verdict: **APPROVE** or **REQUEST_CHANGES**. Send a completion message.
