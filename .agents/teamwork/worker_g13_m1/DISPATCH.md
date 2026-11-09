## 2026-11-09T07:15:24Z
You are worker_g13_m1, a teamwork_worker.
Your working directory is: d:\Google\Workspace\Wind\.agents\teamwork\worker_g13_m1\
You MUST read the user's original request file before starting:
d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
Also read the detailed Explorer 1 handoff report:
d:\Google\Workspace\Wind\.agents\teamwork\explorer_g13_survey_1\handoff.md
And reference:
d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_1\PROJECT.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

PHYSICAL SAFETY RED LINES:
- NEVER touch or modify the 4 strictly read-only files:
  `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py` (and `AGY2_FundAdvisory/tests/test_infra.py`).
- `DataLoader.simulate_execution` default signature and default fee deduction logic MUST remain 100% intact.

YOUR SCOPE & WRITE OWNERSHIP (Milestone 1: 痛点 1 引擎层与痛点 4 回测底层打假):
Files you own exclusively:
- `AGY2_FundAdvisory/advisory_engine.py`
- `AGY2_FundAdvisory/strategy_bridge.py`
- `data/cache/`

DETAILED TASKS:
1. 痛点 1（首屏秒开之引擎层与因子进化持久化缓存）:
   - In `AGY2_FundAdvisory/advisory_engine.py`:
     - In `OnlineHeuristicFactorEvolver`: implement disk file caching in `data/cache/factor_evolution_cache.json` (valid for 12 hours = 43200 seconds). Ensure parent directory `data/cache/` is created if not exists.
     - The cached payload should include `weights`, `generation_scores`, `best_fitness`, `nav_trajectory`, `timestamp`.
     - In `get_60d_rolling_nav_and_trajectory`: if cached `nav_trajectory` exists and is <12h old (and `force=False`), directly return cached dict in <5ms! Do NOT run 12 slices of genetic algorithm on every call!
     - In `evolve_factor_weights`: also check and use disk cache when valid, only run GA when cache is missing/expired or `force=True`.
     - In `OpportunityRadarEngine.__init__`: do NOT run heavy 32x15 genetic evolution synchronously if cached weights exist; use cached weights or sensible defaults.
2. 痛点 4（Tab 3 回测底层去假 Alpha 与真实基准日度全收益）:
   - In `AGY2_FundAdvisory/strategy_bridge.py`:
     - In `build_custom_portfolio_backtest`: completely DELETE line ~4929: `r_arr[1:] += (alpha_ann / 250.0)`! Absolutely NO artificial daily addition of fixed alpha!
     - Benchmark series extraction: check how `H11009` (中证综合债全收益) is extracted. Strictly forbid any linear interpolation! Must extract true daily historical total return from `csindex_H11009.parquet` (CAGR +4.81%). Ensure `BENCHMARK_INDICES_MAP["纯债指数"]` maps to `H11009`. Ensure `H30269` (红利低波) maps to `csindex_H30269.parquet` real total return.
     - Static holding backtest look-ahead bias notice: when target is current real ledger (e.g. `is_real_ledger=True` or `target_name == "当前实盘账本"`), include clear metadata / disclaimer:
       `disclaimer`: "当前持仓静态权重历史回溯（含历史后视镜权重效应，非滚动样本外实盘记录）". Also ensure the return structure includes comparison data for "全天候滚动样本外动态策略曲线 (C3)" so the UI can toggle between them.
3. Verification:
   - Run tests for your changes, e.g. `py -3 -m pytest tests/test_adv_final_closure.py tests/test_infra.py tests/test_g3_evolution_loop.py`.
   - Verify that `factor_evolution_cache.json` is generated and loads in <5ms.
   - Verify that fake alpha `(alpha_ann / 250.0)` is completely gone.
   - Verify that 4 read-only files are NOT modified.
