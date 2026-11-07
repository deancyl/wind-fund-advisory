## 2026-11-07T14:07:10Z
You are Explorer M1-3 for Milestone 1 (Frontend GUI & Test Plan).
Working directory: d:\Google\Workspace\Wind\.agents\teamwork\explorer_r13_m1_3\

MANDATORY FIRST STEP:
Read the authoritative user request at:
d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md

Also read the Scope specification at:
d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_8\SCOPE.md
And reference survey report at:
d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r13_3\report.md

Your mission:
Formulate the exact implementation plan and production-ready code design for GUI Front-end integration in app_gui.py and new tests in tests/test_g3_evolution_loop.py.
Specifically detail:
1. app_gui.py modifications:
   - Morning report pulse (lines 2411-2456): render second-level perception timestamp, 2-market trading volume, sentiment breadth, top 2-3 flash news headlines, clear stance and quantitative rationale; preserve historical 3 inflection points comparative ruler (render_historical_inflection_ruler_html).
   - Top 3 sector cards (lines 2457-2498): display intraday realtime change rate pill, 4D factor score breakdown (valuation, momentum, SNR, anti-crowding), and qualitative/quantitative selection rationale.
   - Right-wing Risk Patrol (line 2521 & 2531): remove gray suffix "[主动风险预警哨 · 四维巡检升级版]", adjust container height (e.g. 360px) and padding to completely eliminate scrollbar clipping on the first card.
   - Online GP whitebox badge: place above Opportunity Radar (below line 2406), showing 60-day real data evolution, dynamic factor weights, and OOS excess fitness gain.
   - Tab 1 & Tab 2: Target volatility alert and reduction card, and Tab 2 Dividend Cash Switching Rebalancing recommendation card.
2. tests/test_g3_evolution_loop.py additions:
   - Specific assertions for realtime news & intraday quotes fusion.
   - Specific assertions for OnlineHeuristicFactorEvolver (NumPy speed <50ms, non-negative excess fitness, dynamic weights sum to 1.0).
   - Specific assertions for apply_target_volatility_risk_control and evaluate_dividend_cash_rebalancing.
3. Hard constraints:
   - Four referee files (judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py) MUST NOT be modified.
   - DataLoader.simulate_execution signature and fee rules MUST NOT be modified.

Outputs:
Write your full technical strategy to d:\Google\Workspace\Wind\.agents\teamwork\explorer_r13_m1_3\report.md and a self-contained handoff to d:\Google\Workspace\Wind\.agents\teamwork\explorer_r13_m1_3\handoff.md.
Then send a completion message with summary to your caller.
