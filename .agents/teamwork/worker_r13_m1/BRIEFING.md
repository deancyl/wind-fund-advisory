# BRIEFING — 2026-11-07T14:20:00Z

## Mission
G6 Core Implementation: Multi-source realtime news & quote perception, online heuristic factor genetic evolution engine (<50ms NumPy), portfolio target volatility risk control (C1~C5), zero-friction dividend cash rebalancing, and GUI twin-wing upgrade.

## 🔒 My Identity
- Archetype: Worker / Implementer
- Roles: implementer, qa, specialist
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\worker_r13_m1\
- Original parent: 970e6279-6781-4b89-b765-9b8036125fe8
- Milestone: G6 Core Implementation (Features 1-11 & 14)

## 🔒 Key Constraints
- NEVER modify referee files: `AGY2_FundAdvisory/judge_engine.py`, `AGY2_FundAdvisory/holdout_vault.py`, `AGY2_FundAdvisory/AGENT_SPEC.md`, `tests/test_infra.py`.
- NEVER modify `DataLoader.simulate_execution` default signature or fee calculation logic.
- DO NOT CHEAT: Genuine implementations maintaining real state and behavior, zero dummy/facade data, zero fake constants.
- Rule isolation: Do NOT touch `C:\Users\deanc\.gemini\GEMINI.md`. All learnings go into workspace `GEMINI.md`.
- Strict Chinese mutual fund regulations: 15:00 single unknown NAV confirmation, <7 days 1.50% redemption fee penalty strictly protected.

## Current Parent
- Conversation ID: 970e6279-6781-4b89-b765-9b8036125fe8
- Updated: 2026-11-07T14:20:00Z

## Task Summary
- **What to build**:
  1. `data_loader.py`: `fetch_realtime_market_news_and_catalysts(timeout=2.0)` with Eastmoney/Sina flash news, 2s timeout, caching, keyword categorization.
  2. `advisory_engine.py`: Intraday price/change_pct splicing `p_today = s[-1]*(1+chg/100)`, abolish static 0.30/0.30/0.25/0.15 weights, `OnlineHeuristicFactorEvolver` (<50ms NumPy vectorized rolling backtest over 60 days, 32 individuals, 8 generations, elite retention), `get_evolution_badge_data()`.
  3. `portfolio_optimizer.py`: `TARGET_VOLATILITY_BY_TIER` (C1:0.05 ~ C5:0.22), `apply_target_volatility_risk_control` scaling down high-vol assets (>8%), reallocating to 002351, strictly normalizing weights to 1.000000, protecting <7d locked batches.
  4. `portfolio_manager.py`: `evaluate_dividend_cash_rebalancing` identifying funds >= 365 days, calculating saved 0.50% redemption fee + 0.20% transit loss.
  5. `app_gui.py`: Morning report pulse (second precision, volume, sentiment, 2-3 flash news, inflection ruler preserved), Top 3 sector cards (realtime change pill, 4D factor score breakdown, rationale), Risk Patrol header cleanup & padding/height fix (360px), Online GP whitebox badge, Tab 1 & Tab 2 target vol and dividend rebalancing cards.
  6. `tests/test_g3_evolution_loop.py`: Add `test_g6_1_realtime_news_and_quotes_fusion`, `test_g6_2_online_heuristic_factor_evolver`, `test_g6_3_target_volatility_risk_control_and_dividend_mode`.
- **Success criteria**:
  - Full test suite passes 100% (pytest tests/test_infra.py, test_adv_final_closure.py, test_g3_evolution_loop.py, test_gui_multi_ledger_stress.py).
  - Git diff on 4 referee files is strictly zero.
  - Performance: Online genetic factor evolution executes in <50ms.
- **Interface contracts**: `d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_8\SCOPE.md`

## Change Tracker
- **Files modified**: None yet
- **Build status**: Ready to begin
- **Pending issues**: None

## Quality Status
- **Build/test result**: Pending execution
- **Lint status**: Clean
- **Tests added/modified**: 3 new tests planned

## Loaded Skills
- None
