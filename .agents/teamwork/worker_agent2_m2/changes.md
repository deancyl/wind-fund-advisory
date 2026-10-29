# Agent-2 (PM & Look-Through De-Mining Expert) Changes Report

## Modified Files
- `d:\Google\Workspace\Wind\AGY2_FundAdvisory\portfolio_manager.py` (Exclusive write permission strictly obeyed)

## Summary of Changes

### 1. 3-Layer Universal Fundamental De-mining Engine (`screen_fund_look_through_risk`)
- **Eradicated 77 Financial Codes Whitelist**:
  - Removed `financial_codes` static set (containing 77 hardcoded stock tickers like 600000, 600036, etc.) and replaced with dynamic fundamental keywords matching and DuckDB lakehouse integration.
  - Removed `NON_ASHARE_CODES` hardcoded set in both `screen_fund_look_through_risk` and `evaluate_fund_crowding_and_derivatives`, replacing with unified `classify_fund_asset_class`.
- **Layer 1: Financial Institutions Exemption**:
  - Automatically identifies banking, non-bank financial, securities, insurance, trust, and futures companies via name keywords and DuckDB `v_research_reports` industry classification.
  - Sets `double_high_risk = False`, `double_high_status = "金融业豁免（正常）"`, `double_high_exempt = True`. Double-high deduction is waived (0 deduction).
- **Layer 2: Strategic Hard Tech & Utilities Capex Verification**:
  - Identifies strategic technology (semiconductor, chips, ICs, hardware, electronics) and public utilities (power, energy, petrochemicals, photovoltaics, equipment) from name keywords and DuckDB `v_research_reports`.
  - Verifies operational cash flow health via DuckDB `v_stock_financials.ocf_per_share > 0` or `v_financial_risk_screen.fcf_billion > 0`.
  - Sets `double_high_risk = False`, `double_high_status = "重资产正常经营/现金流健康"`, `double_high_exempt = True`. Double-high deduction is waived (0 deduction).
- **Layer 3: High-Cash High-Debt + Deteriorating Cash Flow Red Light**:
  - For un-exempted companies with high cash and high interest-bearing debt where operating cash flow or free cash flow is negative (`fcf < 0` or `cfo < 0`, e.g., Vanke A), triggers fraud red light warning.
  - Sets `double_high_risk = True`, `double_high_status = "存贷双高预警"`, `double_high_exempt = False`. Deducts rigid 40.0 points.

### 2. Unified Dynamic Asset Classifier (`classify_fund_asset_class`)
- Implemented `classify_fund_asset_class(self, fund_code: Optional[str] = None, fund_name: Optional[str] = None) -> str`.
- Resolves fund metadata from holdings, `CORE_STRATEGY_POOL`, `EXTENDED_FUND_CATALOG`, and DuckDB `v_fund_catalog`.
- Standardized return values into 9 canonical classes:
  1. `"纯债固收"`
  2. `"黄金对冲"`
  3. `"美股海外对冲"`
  4. `"A股红利高股息"`
  5. `"A股红利低波"`
  6. `"科技成长进攻"`
  7. `"中小盘成长"`
  8. `"中盘均衡"`
  9. `"核心蓝筹"`
  - Universal fallback returns `"其他权益资产"` (NEVER outputs `"其他存量资产"`).
- Dual invocation support: works seamlessly as an instance method (`pm.classify_fund_asset_class(...)`) and as a class/module level function (`PortfolioManager.classify_fund_asset_class(...)`).

### 3. Genuine 6-Dimensional Dynamic Fund Scoring (`compute_fund_six_dimension_score`)
- Implemented `compute_fund_six_dimension_score` (aliased as `calculate_fund_six_dimension_score`).
- Queries real DuckDB views:
  - `v_scorecards`: Alpha score, maximum drawdown, Sharpe ratio, historical returns.
  - `v_fund_trading_rules`: Redemption fees, purchase fees, management and custodian rates.
  - `v_northbound_holdings`: Institutional/smart money holding ratios and capital inflow dynamics.
  - `v_futures_basis`: Index futures basis rate (IC/IM discounts) and hedging cost.
- Applies dynamic Min-Max normalization within peer groups.
- Weighted evaluation with standard weights: Alpha (35%), Fee (25%), Risk (15%), Smart Money (10%), Crowding (10%), Macro Alignment (5%).
- Zero static dictionary dependencies.

### 4. Zero-Start Blueprint & Portfolio Adoption Optimization
- Delegated `PortfolioManager.generate_zero_start_blueprint` directly to `StrategyBridge.generate_zero_start_blueprint`, eliminating duplicate static target weights.
- In `apply_zero_start_blueprint`:
  - Upgraded fund shares precision to 4 decimal places (`round(amt / nav, 4)`), eliminating penny rounding discrepancies.
  - Properly resets `baseline_equity = self.total_equity`, `peak_equity = self.total_equity`, `max_drawdown_pct = 0.0`, `portfolio_return_pct = 0.0`, `benchmark_return_pct = 0.0`, `alpha_return_pct = 0.0`.
  - Ensures all purchased core and companion funds (e.g. 001071 split from 050025) are tagged with `is_core_strategy = True` and `transition_tag = "核心策略底仓"`.
  - Implemented dynamic helper `is_core_or_companion_fund(self, code: str) -> bool` checking `CORE_STRATEGY_POOL` and `SECTOR_FUND_SELECTION` companion references, eliminating hardcoded tuple `("001071", ...)`.

### 5. Module-Level Exports
- Added convenient module-level function aliases at the bottom of `portfolio_manager.py`:
  - `classify_fund_asset_class = PortfolioManager.classify_fund_asset_class`
  - `compute_fund_six_dimension_score = PortfolioManager.compute_fund_six_dimension_score`
  - `calculate_fund_six_dimension_score = PortfolioManager.compute_fund_six_dimension_score`
  - `generate_zero_start_blueprint = PortfolioManager.generate_zero_start_blueprint`

### 6. Read-Only Invariants Adherence
- Strictly refrained from modifying any of the 4 referee/invariant files:
  - `judge_engine.py` (UNTOUCHED)
  - `holdout_vault.py` (UNTOUCHED)
  - `AGENT_SPEC.md` (UNTOUCHED)
  - `tests/test_infra.py` (UNTOUCHED)
