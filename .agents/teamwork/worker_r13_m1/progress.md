# Progress Tracker — Worker r13-m1 (G6 Core Implementation)

Last visited: 2026-11-07T14:20:00Z
Status: IN_PROGRESS

## Phase 1: Environment & Baseline Check
- [x] Read DISPATCH.md, ORIGINAL_REQUEST.md, SCOPE.md, explorer reports 1, 2, 3
- [x] Initialize DISPATCH.md, BRIEFING.md, progress.md
- [ ] Baseline test run (verify clean test status and 0 diff on referee files)

## Phase 2: Data Loader & Advisory Engine Implementation
- [ ] Implement `data_loader.fetch_realtime_market_news_and_catalysts` with timeout, cache, Eastmoney & Sina fallback, and tagging
- [ ] Implement `OpportunityRadarEngine._calc_dynamic_sector_metrics` realtime K-line quote splicing
- [ ] Implement `OnlineHeuristicFactorEvolver` pure NumPy vectorized genetic evolver (<50ms, 32 pop, 8 gen, elite preservation)
- [ ] Abolish lines 575-578 static weights (0.30/0.30/0.25/0.15) and wire `self.factor_weights`
- [ ] Implement `OpportunityRadarEngine.get_evolution_badge_data()`

## Phase 3: Risk Control & Portfolio Optimization
- [ ] Define `TARGET_VOLATILITY_BY_TIER` and implement `apply_target_volatility_risk_control` in `portfolio_optimizer.py`
- [ ] Implement `evaluate_dividend_cash_rebalancing` in `portfolio_manager.py`

## Phase 4: GUI Front-End Fusion
- [ ] Update `app_gui.py`: Online GP evolution badge component
- [ ] Update `app_gui.py`: Morning report pulse (second-level ts, turnover, sentiment, flash news, ruler preserved)
- [ ] Update `app_gui.py`: Top 3 sector cards (realtime change pill, 4D factor score breakdown, qualitative/quantitative rationale)
- [ ] Update `app_gui.py`: Risk Patrol cleanup (remove `[主动风险预警哨 · 四维巡检升级版]`, height 360px, padding fix)
- [ ] Update `app_gui.py`: Tab 1 & Tab 2 target volatility card & Tab 2 dividend cash switching card

## Phase 5: Test Suite Expansion & Verification
- [ ] Add 3 tests in `tests/test_g3_evolution_loop.py`
- [ ] Run full test suite (`test_infra.py`, `test_adv_final_closure.py`, `test_g3_evolution_loop.py`, `test_gui_multi_ledger_stress.py`)
- [ ] Verify referee files zero diff (`git diff --exit-code HEAD -- AGY2_FundAdvisory/judge_engine.py ...`)
- [ ] Generate comprehensive handoff report `handoff.md`
