# Project: G12 Generation Wind Control & GP Evolution Closure

## Architecture
- Streamlit GUI Layer (`AGY2_FundAdvisory/app_gui.py`): Three-Block Minimalist Architecture, Double-Wing Header, Popover 🧬 Factor Evolution, Right-Wing Active Risk Sentry, Tab 1 Smart DCA, Tab 2 Rebalance.
- Quantitative Decision Engine (`AGY2_FundAdvisory/advisory_engine.py`): OnlineHeuristicFactorEvolver (7D GP Rule Tree, Real-time cross-section injection), ActiveRiskSentry (Dimensions 4, 8, 9), SmartExecutionDCAEngine (Portfolio-weighted bias & ERP), OpportunityRadarEngine.
- Portfolio & Execution Management (`AGY2_FundAdvisory/portfolio_manager.py`): Correlation mutation defense, Index & Feeder fund valuation calibration (`_apply_fund_valuation_calibration` with 0.95 factor), Intraday PnL.
- Data Loader & Sensor Layer (`AGY2_FundAdvisory/data_loader.py`): Parquet daily line auto-heal (`auto_heal_sector_parquets`), 14 Sector ETF volume surge & discount/premium sensors, Macro cross-market indicators (10Y bond, gold, Nasdaq), Financial news sentiment scoring (0-100).
- Referee & Invariant Protection: `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py` (STRICTLY READ-ONLY).

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| F1 | Bug 1: Correlation Card Key Alignment | Fix `app_gui.py:2987` key check to `is_triggered` / `is_liquidity_shift_triggered` + add double-insurance aliases in `portfolio_manager.py:8628` | M1 | Survey 1 & 3 [DONE] |
| F2 | Bug 2: Sentry Parameter Penetration | Pass `investor_risk_tier` and inject `fund_quotes` into `snapshot_dict` in `app_gui.py:2725` to activate Dimensions 8 & 9 | M1 | Survey 1 & 3 [DONE] |
| F3 | Bug 3: Index & Feeder Valuation Calibration | Implement `_apply_fund_valuation_calibration` in `portfolio_manager.py` with 0.95 factor for feeder funds against live ETF/index changes | M1 | Survey 1 [DONE] |
| F4 | Bug 4: Tab 1 DCA Portfolio Target Alignment | Compute portfolio weighted MA20 bias & ERP across selected funds in `SmartExecutionDCAEngine` & `app_gui.py` | M1 | Survey 1 [DONE] |
| F5 | Trailing Stop-Profit & Right-Side Breakdown Exit | Sentry Dimension 4: red warning on pnl >= 10% + breaks MA20 + (slope < 0 or drop > 1.5*vol) for 50% profit lock; 60d HWM drawdown >= 8% yellow alert | M2 | Survey 2 |
| F6 | Parquet Daily Line Auto-Heal | `data_loader.py:auto_heal_sector_parquets` to detect lag and fetch missing trading days atomically | M2 | Survey 2 |
| F7 | Multi-Source Leading Indicators & Sentiment | 14 ETF Volume Surge Ratio & discount/premium, macro indicators (10Y bond, gold, Nasdaq), 0-100 financial news sentiment score & morning brief | M2 | Survey 2 |
| F8 | 7D Online Heuristic GP Event Rule Tree | Real-time cross-section price injection at sequence tail + 7D chromosome (4 weights + 3 event operators: adaptive momentum 5d/20d, vol pulse penalty, sudden drop safe boost) + dual 4D/7D vectorization | M3 | Survey 3 |
| F9 | Double-Wing Popover 🧬 Factor Evolution UI | Display market emergency mode badge (smooth, vol-pulse, panic-oversold) + evolved optimal rule expression string in `app_gui.py` popover | M3 | Survey 3 |
| F10 | Service Restart & /browser Visual Inspection | Restart 8501 headless service, health probe HTTP 200, `/browser` multi-modal walkthrough (desktop/mobile, light/dark, 3-block layout, popover, alerts) | M4 | Survey 1, 2, 3 |
| F11 | Full Test Regression, Victory Audit, Git Sync & G13 Directive | Pytest 100% green, 4 referee files untouched, clean ledgers_index, update GEMINI.md & PROGRESS_LOG.md, git commit & tag v4.2-G12, push origin HEAD & tags (no releases), Victory Audit, strict G13 directive | M5 | Survey 1, 2, 3 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | 4 Circuit-Breaker Bugs & Sentry Penetration | F1, F2, F3, F4 | none | DONE |
| M2 | Trailing Stop-Profit, Auto-Heal & Leading Indicators | F5, F6, F7 | M1 | IN_PROGRESS |
| M3 | 7D GP Event Rule Tree & Popover UI | F8, F9 | M1, M2 | PLANNED |
| M4 | Service Restart & Browser Visual Inspection | F10 | M1, M2, M3 | PLANNED |
| M5 | Regression, Victory Audit, Git Sync & G13 Directive | F11 | M4 | PLANNED |

## Interface Contracts
### `app_gui.py` ↔ `portfolio_manager.py` (Correlation & Feeder Valuation)
- `evaluate_dynamic_correlation_mutation_instance(threshold=0.75, stress_threshold=0.80)`: Returns dictionary with keys `is_triggered`, `is_liquidity_shift_triggered`, `is_mutation_alarm`, `is_regime_shift_risk`. [VERIFIED]
- `fetch_realtime_fund_quote(fund_code, use_cache=True)`: Returns `FundQuote` object with `valuation_corrected: bool`, `gszzl: float`, calibrated against benchmark ETF/index with 0.95 factor for feeder funds. [VERIFIED]

### `app_gui.py` ↔ `advisory_engine.py` (Sentry Inspection & DCA)
- `ActiveRiskSentry.inspect_portfolio(holdings, snapshot, fund_metadata, investor_risk_tier)`: Requires `investor_risk_tier` and `snapshot["fund_quotes"]` to trigger Dimension 8 (suitability) and Dimension 9 (intraday cushion transmission). [VERIFIED]
- `SmartExecutionDCAEngine.compute_portfolio_weighted_bias_and_erp(allocations, snapshot)`: Returns `(weighted_erp_pct: float, weighted_bias_20: float)`. [VERIFIED]
- `ActiveRiskSentry.inspect_portfolio`: Dimension 4 returns alerts with `action_type: "take_profit"`, `take_profit_ratio: 0.50` (or `0.40`), `level: "red"` (or `"yellow"`), and dimension `"移动止盈"`.

### `advisory_engine.py` ↔ `data_loader.py` & Internal GP
- `OnlineHeuristicFactorEvolver.evolve_factor_weights(lookback_days=60, realtime_quotes=None, force_refresh=False)`: Returns dict containing:
  - `"weights"`: 4D list `[w_val, w_mom, w_snr, w_crowd]` (guarantees backward compatibility with existing tests),
  - `"chromosome_7d"`: 7D list including the 3 event operators,
  - `"market_emergency_mode"`: `"smooth"` | `"vol_pulse"` | `"panic_oversold"`,
  - `"evolved_rule_expression"`: human-readable mathematical rule string,
  - `"elapsed_ms"`: float (< 250.0 ms).
- `DataLoader.auto_heal_sector_parquets()`: Heals missing trading day records in fallback sector parquet files atomically.
- `DataLoader.fetch_sector_core_etf_metrics()`: Returns dict of 14 core ETF realtime metrics (`volume_surge_ratio`, `discount_premium_pct`).
- `DataLoader.fetch_macro_cross_market_indicators()`: Returns dict of 10Y bond yield, gold ETF, Nasdaq linkage.
- `DataLoader.calc_financial_news_sentiment(news_items)`: Returns `(sentiment_score: float, sentiment_label: str)`.

## Code Layout
- `AGY2_FundAdvisory/app_gui.py`: GUI front-end, double-wing header, popover, Tab 1 & Tab 2 wiring.
- `AGY2_FundAdvisory/advisory_engine.py`: GP evolver, risk sentry, DCA engine, radar engine.
- `AGY2_FundAdvisory/portfolio_manager.py`: Correlation mutation, fund quotes calibration, portfolio manager.
- `AGY2_FundAdvisory/data_loader.py`: Market data loader, parquet auto-heal, multi-source sensors.
- `tests/test_g12_circuit_breakers_and_sentry.py`: M1 unit test suite.
- `tests/test_empirical_challenger_m1.py`: M1 challenger 49-test suite.
- `tests/test_g12_m1_challenge.py`: M1 challenger 49-test suite.
- `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`: READ-ONLY REFEREE FILES.
