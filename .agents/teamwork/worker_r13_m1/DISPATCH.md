## 2026-11-07T14:19:13Z
You are Worker r13-m1 for G6 Core Implementation.
Working directory: d:\Google\Workspace\Wind\.agents\teamwork\worker_r13_m1\

MANDATORY FIRST STEP:
Read the authoritative user request at:
d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md

Also read the Scope specification at:
d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_8\SCOPE.md
And the three detailed implementation blueprints provided by Explorers:
- d:\Google\Workspace\Wind\.agents\teamwork\explorer_r13_m1_1\report.md
- d:\Google\Workspace\Wind\.agents\teamwork\explorer_r13_m1_2\report.md
- d:\Google\Workspace\Wind\.agents\teamwork\explorer_r13_m1_3\report.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

CRITICAL READ-ONLY INVARIANT:
- NEVER modify the 4 referee files: AGY2_FundAdvisory/judge_engine.py, AGY2_FundAdvisory/holdout_vault.py, AGY2_FundAdvisory/AGENT_SPEC.md, tests/test_infra.py
- NEVER modify DataLoader.simulate_execution default signature or fee calculation rules.
- Rule isolation: Do NOT touch C:\Users\deanc\.gemini\GEMINI.md.

YOUR IMPLEMENTATION SCOPE:
Files you own exclusively:
1. AGY2_FundAdvisory/data_loader.py
   - Implement fetch_realtime_market_news_and_catalysts(timeout: float = 2.0) -> Dict[str, Any] with Eastmoney & Sina flash news, 2s timeout, caching, and regex/keyword tagging for macro liquidity, broad market, and 14 sectors.
2. AGY2_FundAdvisory/advisory_engine.py
   - Splicing intraday real-time prices & change_pct to OpportunityRadarEngine K-line in _calc_dynamic_sector_metrics: formula p_today = s[-1] * (1.0 + change_pct / 100.0) so sector scores and rankings update dynamically.
   - Abolish lines 575-578 static weights (0.30, 0.30, 0.25, 0.15).
   - Implement OnlineHeuristicFactorEvolver (<50ms pure NumPy vectorized rolling backtest over past 60 trading days of 14 tracks, 32 individuals, 8 generations, tournament selection, crossover, mutation, baseline weight anchoring in individual 0 with elite retention for non-negative excess fitness).
   - Implement OpportunityRadarEngine.get_evolution_badge_data() for front-end consumption.
3. AGY2_FundAdvisory/portfolio_optimizer.py
   - Add TARGET_VOLATILITY_BY_TIER = {"C1": 0.05, "C2": 0.08, "C3": 0.12, "C4": 0.16, "C5": 0.22}.
   - Implement apply_target_volatility_risk_control(current_holdings, user_risk_tier) using 20-day weighted rolling annualized volatility, reduction ratio = (current_vol - target_vol) / current_vol, scale down high-vol (>8%) holdings, reallocate to 002351 or cash buffer, strictly normalize weights to sum = 1.000000. Strictly protect <7 days locked batches!
4. AGY2_FundAdvisory/portfolio_manager.py
   - Implement evaluate_dividend_cash_rebalancing(holdings_or_ledger) identifying funds held >= 365 days, calculating saved 0.50% redemption fee + 0.20% transit loss, structured recommendation for Tab 2.
5. AGY2_FundAdvisory/app_gui.py
   - Morning report pulse (lines 2411-2456): render second-level perception timestamp, 2-market trading volume, sentiment breadth, top 2-3 flash news headlines, clear stance and quantitative rationale; preserve historical 3 inflection points comparative ruler (render_historical_inflection_ruler_html).
   - Top 3 sector cards (lines 2457-2498): display intraday realtime change rate pill, 4D factor score breakdown (valuation, momentum, SNR, anti-crowding), and qualitative/quantitative selection rationale.
   - Right-wing Risk Patrol (line 2521 & 2531): remove gray suffix "[主动风险预警哨 · 四维巡检升级版]", adjust container height (360px) and padding to completely eliminate scrollbar clipping on the first card.
   - Online GP whitebox badge: place above Opportunity Radar (below line 2406), showing 60-day real data evolution, dynamic factor weights, and OOS excess fitness gain.
   - Tab 1 & Tab 2: Target volatility alert and reduction card, and Tab 2 Dividend Cash Switching Rebalancing recommendation card.
6. tests/test_g3_evolution_loop.py
   - Add test_g6_1_realtime_news_and_quotes_fusion
   - Add test_g6_2_online_heuristic_factor_evolver
   - Add test_g6_3_target_volatility_risk_control_and_dividend_mode
