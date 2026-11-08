# DISPATCH for explorer_g9_survey_1

## Objective
Survey and deeply investigate R3: 底层量化因果律与数据真实性严苛纠偏.

## Inputs
- `advisory_engine.py`
- `portfolio_manager.py`
- `data_loader.py`
- `AGENT_SPEC.md` (read-only reference)
- `.agents/teamwork/ORIGINAL_REQUEST.md`

## Specific Investigation Tasks
1. `OnlineHeuristicFactorEvolver._evaluate_population`:
   - Check current implementation of weights $P[t]$ and returns $R[t]$. Verify how to lag $P[t]$ by 1 period to act on $R[t+1]$ ($P[:-1]$ vs $R[1:]$).
   - Check deduction of 10 bps turnover friction cost in `nav_dynamic`.
   - Check Sharpe ratio calculation: verify how 2.0% annual risk-free rate (`0.02 / 250.0`) is deducted from daily mean return.
2. `get_60d_rolling_nav_and_trajectory`:
   - Inspect current `lam = (t + 1) / 60.0` linear interpolation.
   - Design the 5-day walk-forward rolling evolution mechanism.
3. `_extract_sector_price_matrix`:
   - Check calendar alignment using A-share calendar (H00300).
   - Check line 235 or where `np.linspace(1.0, 1.05, window_days)` exists, how to replace with 0 return and missing state flag.
   - Check `_build_factor_tensor_and_returns` valuation score `s_val`.
4. `ActiveRiskSentry.inspect_portfolio`:
   - Check where `else: aum = 2.5` fallback exists.
   - Plan penetration to `DataLoader.get_fund_metadata` or catalogs.
   - Plan C1-C5 appropriateness boundary alert.
5. `evaluate_sector`:
   - Inspect intraday chg handling and recalculation of MA20, Bias20, Slope20, ER20.
   - Dynamic quantitative evidence generation.
6. `evaluate_rebalance_audit`:
   - Brinson 3D excess attribution (Allocation Effect, Selection Effect, Friction Saving).

## Output
Write comprehensive survey and technical recommendations to:
`d:\Google\Workspace\Wind\.agents\teamwork\explorer_g9_survey_1\handoff.md`


## 2026-11-08T05:51:12Z
From: e2e9b1b9-848d-4b67-b5e8-3f65177957b7 (orchestrator_12)
Task: Investigate R3: 底层量化因果律与数据真实性严苛纠偏:
1. OnlineHeuristicFactorEvolver._evaluate_population: lag P[t] by 1 period to act on R[t+1] (P[:-1] vs R[1:]), deduct 10 bps turnover friction in nav_dynamic, deduct 2.0% annual risk-free rate (0.02 / 250.0) from mean return in Sharpe ratio.
2. get_60d_rolling_nav_and_trajectory: replace lam linear interpolation with 5-day walk-forward rolling evolution.
3. _extract_sector_price_matrix: align with A-share calendar (H00300), remove np.linspace(1.0, 1.05, window_days) and use 0 return with missing flag, verify valuation score s_val in _build_factor_tensor_and_returns.
4. ActiveRiskSentry.inspect_portfolio: remove else: aum = 2.5 fallback, implement real AUM lookup via DataLoader and catalogs, plan C1-C5 appropriateness boundary alert.
5. evaluate_sector: append intraday chg to end of price series to recompute MA20, Bias20, Slope20, ER20, generate dynamic quantitative evidence text.
6. evaluate_rebalance_audit: plan Brinson 3D excess attribution (Allocation, Selection, Friction Saving).
