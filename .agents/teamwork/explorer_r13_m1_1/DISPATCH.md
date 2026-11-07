## 2026-11-07T14:06:42Z
You are Explorer M1-1 for Milestone 1 (Data & Advisory Core).
Working directory: d:\Google\Workspace\Wind\.agents\teamwork\explorer_r13_m1_1\

MANDATORY FIRST STEP:
Read the authoritative user request at:
d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md

Also read the Scope specification at:
d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_8\SCOPE.md
And reference survey report at:
d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r13_1\report.md

Your mission:
Formulate the exact implementation plan and production-ready code design for Milestone 1: Data & Advisory Core.
Specifically detail:
1. data_loader.py:
   - Implementation of fetch_realtime_market_news_and_catalysts(timeout: float = 2.0) -> Dict[str, Any].
   - API endpoints for Eastmoney & Sina flash news.
   - 2-second timeout, memory cache with TTL (e.g. 60s) + disk cache fallback (data/cache/realtime_news.json).
   - Regex/keyword parser to tag headlines with macro liquidity, broad market, and 14 sectors.
2. advisory_engine.py:
   - Splicing intraday real-time prices & change_pct to OpportunityRadarEngine's K-line in _calc_dynamic_sector_metrics: formula p_today = s[-1] * (1.0 + change_pct / 100.0).
   - Abolishing lines 575-578 static weights (0.30, 0.30, 0.25, 0.15).
   - Implementation of OnlineHeuristicFactorEvolver:
     * 32 candidate gene individuals, 8 generations.
     * Pure NumPy vectorized rolling backtest over past 60 trading days of 14 tracks (<50ms).
     * Fitness function combining Sharpe ratio, win rate, and MDD control.
     * Elite preservation of baseline weights to guarantee non-negative excess fitness.
   - get_evolution_badge_data() method in OpportunityRadarEngine for front-end consumption.
3. Hard constraints verification:
   - Four referee files (judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py) MUST NOT be modified.
   - DataLoader.simulate_execution signature and fee rules MUST NOT be modified.

Outputs:
Write your full technical strategy to d:\Google\Workspace\Wind\.agents\teamwork\explorer_r13_m1_1\report.md and a self-contained handoff to d:\Google\Workspace\Wind\.agents\teamwork\explorer_r13_m1_1\handoff.md.
Then send a completion message with summary to your caller.
