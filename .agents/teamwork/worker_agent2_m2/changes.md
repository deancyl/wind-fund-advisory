# Agent-2 Changes Report: Milestone 2 (R4 & R5)

## Modified Files
- `d:\Google\Workspace\Wind\AGY2_FundAdvisory\data_loader.py`
- `d:\Google\Workspace\Wind\AGY2_FundAdvisory\strategy_bridge.py`
- `d:\Google\Workspace\Wind\AGY2_FundAdvisory\portfolio_manager.py`
- `d:\Google\Workspace\Wind\AGY2_FundAdvisory\tests\test_m2_r4_r5_optimization.py` (New test suite)

---

## Summary of Changes

### 1. R4: Rolling EWMA Volatility & Correlation Operator (`data_loader.py`)
- Implemented `DataLoader.compute_ewma_volatility_and_correlation(df, window=60, span=60, asset_cols=None) -> Tuple[pd.Series, pd.DataFrame]`:
  - Dynamically calculates 60-day exponentially weighted moving average variance (`ret_df.ewm(span=60, adjust=True).var()`).
  - Annualizes standard deviation with $\sqrt{252}$ scaling factor.
  - Computes rolling correlation matrix (`ret_df.corr().fillna(0.0)`).
  - Graceful fallback for empty or short dataframes with robust prior vol baselines (pure bond 3.5%, dividend 14%, gold 13%, equity 18%).

### 2. R4: Inverse Volatility Dynamic Risk Budgeting & Monotonicity Preservation (`strategy_bridge.py`)
- Built `FUND_TO_PROXY_INDEX` code mapping for precision benchmark alignment.
- Added static caching `_CACHED_EWMA_VOLS` and `_CACHED_CORR_MAT` to accelerate repetitive backtests and grid searches.
- In `compute_dynamic_tier_weights`:
  - Applied inverse volatility scaling: $\text{scaling} = \min(1.0, 0.18 / \max(\sigma_{\text{asset}}, 0.08))$.
  - Transferred 100% of trimmed risk budget into low-vol pure bond ballast (`002351` / `000086`).
  - Enforced regime-based non-overlapping equity bounds (BULL, OSCILLATING, BEAR) guaranteeing:
    - $\text{Equity}(C1) < \text{Equity}(C2) < \text{Equity}(C3) < \text{Equity}(C4) < \text{Equity}(C5)$
    - Deep bear stop-loss hard bounds: $\text{Equity}(C4) \le 55\%, \text{Equity}(C5) \le 70\%$
    - Defensive asset monotonicity: $\text{Defensive}(C1) > \text{Defensive}(C2) > \dots > \text{Defensive}(C5)$.

### 3. R5: Net Utility Interceptor, In-Transit Discount & Same-Company Bonus (`portfolio_manager.py`)
- Implemented `calculate_rebalance_net_utility(from_fund_code, to_fund_code, amount, expected_alpha_20d=None, market_snapshot=None) -> Dict[str, Any]`:
  - Calculates net utility $\Delta U = \text{ExpectedAlpha}_{20d} - (\text{FIFO\_RedemptionFee} + \text{SubscriptionFee} + \text{InTransitCost})$.
  - Same-company T+1 SWITCH: $\Delta t_{\text{arrive}} = 0 \implies \text{InTransitOpportunityCost} = 0.0$.
  - Cross-company transfer: $\Delta t_{\text{arrive}} = 2 \sim 4$ days with volatility opportunity discount: $\text{Cost} = \text{Amount} \times \sigma_{\text{index}} \times \sqrt{\Delta t / 250}$.
  - When $\Delta U \le 0$, badges with `"🛡️ 摩擦/在途损耗大于预期收益，建议原地持仓不动"`, flags `should_intercept = True`.
- In `generate_rebalance_plan`:
  - Evaluates net utility for all proposed routes (Priority 1 SWITCH and Priority 3 Two-Step).
  - Segregates routes into `executable_routes` and `intercepted_routes`.
- In `submit_rebalance_orders`:
  - Drops routes flagged with `should_intercept = True`, preventing execution of friction-destructive orders.
- In `_do_compute_six_dimension_score`:
  - Added same-company switching convenience bonus (+5.0 points) when candidate fund shares management company with existing user holdings.
- Exported module-level alias `calculate_rebalance_net_utility = PortfolioManager.calculate_rebalance_net_utility`.

### 4. Comprehensive Test Suite (`tests/test_m2_r4_r5_optimization.py`)
- 9 dedicated unit tests validating:
  1. `test_r4_data_loader_ewma_volatility_and_correlation_empty_and_fallback`
  2. `test_r4_data_loader_ewma_volatility_and_correlation_real_matrix`
  3. `test_r4_strategy_bridge_inverse_volatility_weighting_and_bond_ballast`
  4. `test_r4_c1_c5_risk_monotonicity_across_all_regimes`
  5. `test_r5_same_company_switch_zero_in_transit_cost`
  6. `test_r5_cross_company_in_transit_opportunity_cost_and_interception`
  7. `test_r5_qdii_overseas_four_day_in_transit_discount`
  8. `test_r5_same_company_convenience_bonus_in_fund_scoring`
  9. `test_r5_interception_prevents_executable_orders`

### 5. Strict Read-Only Safety Redlines
- All 4 referee files remained 100% untouched:
  - `judge_engine.py` (UNTOUCHED)
  - `holdout_vault.py` (UNTOUCHED)
  - `AGENT_SPEC.md` (UNTOUCHED)
  - `tests/test_infra.py` (UNTOUCHED)
