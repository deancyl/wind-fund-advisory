## 2026-11-07T13:52:23Z
You are Explorer 1 for the G6 codebase survey.
Working directory: d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r13_1\

MANDATORY FIRST STEP:
Read the authoritative user request at:
d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md

Your mission:
Deep technical investigation into Realtime Data, News Perception, and Online Genetic Programming Engine in data_loader.py and advisory_engine.py.

Specifically investigate:
1. OpportunityRadarEngine in advisory_engine.py & data_loader.py:
   - How 14 tracks are loaded and evaluated.
   - Where the historical K-lines come from.
   - How real-time market quotes (intraday latest price and change rate) can be dynamically spliced as the latest K-line bar so bias, momentum slope, and radar score update dynamically.
   - Line numbers, class names, method signatures, return structures.
2. Static Factor Weights around line 456 of advisory_engine.py:
   - Identify the exact lines where 0.30 valuation, 0.30 momentum, 0.25 SNR, 0.15 crowding are hardcoded.
   - Understand the inputs and outputs of the radar scoring logic.
3. Real-time Market News & Catalysts fetcher:
   - Current news fetching facilities in data_loader.py if any.
   - Architecture for fetch_realtime_market_news_and_catalysts: API endpoints (Eastmoney / Sina live flash news), 2-second timeout, local file cache fallback, filtering/tagging keywords for macro liquidity, broad market index, and 14 tracks.
4. OnlineHeuristicFactorEvolver:
   - Mathematical and algorithmic design for vectorized rolling backtest (<50ms) using numpy arrays of the last 60 trading days returns of 14 tracks.
   - Population structure (32 individuals), gene representation (weights for valuation, momentum, SNR, anti-crowding), fitness function (Sharpe, win rate, MDD), selection, crossover, mutation operators.
   - How the evolved optimal weights integrate back into OpportunityRadarEngine.
5. Verify that four read-only files (judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py) are completely untouched.

Outputs:
Write your full findings to d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r13_1\report.md and a self-contained handoff to d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r13_1\handoff.md.
Then send a completion message with summary to your caller.
