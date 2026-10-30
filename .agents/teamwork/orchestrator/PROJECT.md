# Project: AGY2_FundAdvisory Self-Evolving Heuristic Quant Engine

## Architecture
- **Language & Runtime**: Python 3.11, Streamlit 1.32+, DuckDB / Parquet lakehouse.
- **Pure Mathematical Invariant**: 100% causal deduction (No Look-Ahead Bias), AST calendar anti-cheating, 0 external LLM APIs.
- **Physical Safety Invariants (Strict Read-Only)**:
  - `judge_engine.py` (AST checks, causal probe, style slice regression)
  - `holdout_vault.py` (blind holdout vault after 2025-07-01, max 3 attempts)
  - `AGENT_SPEC.md` (50/50 benchmark, asset bounds, CAGR >= 11.5%, MaxDD <= 15.5%)
  - `tests/test_infra.py` (15 regression tests)
- **Core Modules**:
  - `strategy_bridge.py`: Hedge online multi-expert weights (`OnlineExpertWeightUpdater`), Schmidt hysteresis buffer (`SchmidtHysteresisBuffer`), Sigmoid continuous position gating, dynamic tier weights with EWMA inverse vol.
  - `data_loader.py`: Parquet lakehouse loading, `DataLoader.compute_ewma_volatility_and_correlation()`, T+1 trade simulation.
  - `portfolio_manager.py`: FIFO A/C redemption fee calculation, rebalance net utility interceptor (`calculate_rebalance_net_utility`), CUSUM champion fund decay & auto-promotion (`CUSUMFundChangePointDetector`), same-company switching convenience bonus (+5.0 pts).
  - `app_gui.py`: Streamlit workstation with 4-step transparent white-box panels, 3-sentence summary card, anti-inversion bidirectional breakout lines, 1080p zero-scrollbar layout.
  - `tests/`: Automated unit & E2E tests, AppTest GUI validation, Red Team stress testing.

## Code Layout & Write Boundaries
| Milestone | Worker Role | Primary Owned Files | Read-Only Files |
|-----------|-------------|---------------------|-----------------|
| M1 | Agent-1 (Online Learning & State Machine) | `strategy_bridge.py` | `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py` |
| M2 | Agent-2 (Risk Parity & Friction Utility) | `data_loader.py`, `strategy_bridge.py`, `portfolio_manager.py` | Same read-only invariants |
| M3 | Agent-3 (CUSUM Fund Selection & UI) | `portfolio_manager.py`, `app_gui.py`, `strategy_bridge.py` | Same read-only invariants |
| M4 | Agent-4 (Red Team Tester & E2E Verifier) | `tests/*.py` | Same read-only invariants |

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Physical Safety Invariant & No Look-Ahead Bias | 4 referee files untouched, no external LLM APIs, no calendar hardcoding | M1-M4 | R1, Survey |
| 2 | Hedge Online Multi-Expert Multiplicative Weight Update | `OnlineExpertWeightUpdater` with K=4 streams, rolling gamma=0.985, utility u_{i,t}, learning rate eta | M1 (DONE) | R2, Explorer 1 |
| 3 | Schmidt Hysteresis Buffer Ring & Sigmoid Continuous Gating | Dual threshold (+1.2% / Z>=0.60 vs -1.5% / Z<0.20), noise lock in [-1.5%, +1.2%], g(Z_t)=1/(1+exp(-k*Z_t)) | M1 (DONE) | R3, Explorer 1 |
| 4 | Rolling 60-day EWMA Volatility Reciprocal Risk Budgeting | `DataLoader.compute_ewma_volatility_and_correlation`, inverse vol risk budgeting, excess budget transfer to bond ballast, C1-C5 monotonicity | M2 (DONE) | R4, Explorer 2 |
| 5 | Rebalance Net Utility Interceptor & In-Transit Friction Discount | Delta U = Alpha - ExactRedemptionFee(FIFO) - SubFee - InTransitOpportunityCost, same-company SWITCH (Delta t=0), cross-company Delta t=2~4d, intercept badge, same-company convenience bonus (+5.0 pts) | M2 (DONE) | R5, Explorer 2 |
| 6 | CUSUM Change-Point Track Champion Dynamic Selection | `CUSUMFundChangePointDetector` in `portfolio_manager.py` & `strategy_bridge.py`, S_{f,t} score, decay tracking, auto-promote rank 1 with label `🔄 自进化优选` | M3 (DONE) | R6, Explorer 3 |
| 7 | Transparent White-Box UI & Plain Language Refinement | 4-step white-box expanders, 3-sentence summary card, anti-inversion breakout lines, 1080p zero-wrap/zero-scrollbar fit | M3 (DONE) | R7, Explorer 3 |
| 8 | Red Team Causal Verification, AppTest & Service Health | Comprehensive tests in `tests/`, full test suite pass (246+ tests), Streamlit service port 8501 check | M4 | Acceptance Criteria |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Online Learning & Schmidt Hysteresis | R2 (OnlineExpertWeightUpdater) + R3 (SchmidtHysteresisBuffer & Sigmoid) in `strategy_bridge.py` | Survey | DONE |
| M2 | Dynamic Risk Parity & Friction Interceptor | R4 (EWMA volatility in `data_loader.py` & `strategy_bridge.py`) + R5 (Net utility interceptor in `portfolio_manager.py`) | M1 | DONE |
| M3 | CUSUM Fund Selection & White-Box UI | R6 (`CUSUMFundChangePointDetector` in `portfolio_manager.py` & `strategy_bridge.py`) + R7 (Streamlit 4-step white-box, cards, breakout lines in `app_gui.py`) | M2 | DONE |
| M4 | Red Team E2E Verification & Service Health | New tests in `tests/`, full suite regression (523 tests), 4 referee files integrity check, Streamlit service 8501 restart/probe | M3 | DONE |

## Interface Contracts
### `strategy_bridge.py` ↔ `OnlineExpertWeightUpdater`
- Inputs: `history_df: pd.DataFrame`, `window_days: int = 60`, `gamma: float = 0.985`, `eta: float = 10.0`
- Outputs: `Dict[str, Any]` with `weights: Dict[str, float]` (sum=1.0000), `blended_target_weights: Dict[str, float]`, `details: Dict[str, Any]`
- Snapshot injection: `snapshot["expert_weights"]`, `snapshot["expert_details"]`

### `strategy_bridge.py` ↔ `SchmidtHysteresisBuffer`
- Inputs: `bias_20: float`, `composite_z: float`, `is_currently_attack: bool`
- Outputs: `Tuple[bool, str]` (new_is_attack, transition_reason)
- Continuous gating: `compute_sigmoid_gating(z_score: float, k: float = 3.0) -> float`
- Trigger lines: `get_hysteresis_trigger_lines(m20_price: float, c300_price: float) -> Dict[str, float]` with `breakdown_line < c300_price < surge_line`

### `data_loader.py` ↔ `strategy_bridge.py` (EWMA Volatility)
- `DataLoader.compute_ewma_volatility_and_correlation(df, window=60, span=60, asset_cols=None) -> Tuple[pd.Series, pd.DataFrame]`
- In `compute_dynamic_tier_weights`: scales equity weight by `0.18 / max(vol, 0.08)`, trims excess into bond `002351` / `000086`, enforces C1-C5 monotonicity.

### `portfolio_manager.py` ↔ `calculate_rebalance_net_utility`
- Inputs: `from_fund_code: str`, `to_fund_code: str`, `amount: float`, `expected_alpha_20d: Optional[float]`, `market_snapshot: Optional[Dict]`
- Outputs: `Dict[str, Any]` including `is_same_company`, `delta_t_arrive`, `exact_redemption_fee`, `subscription_fee`, `in_transit_opportunity_cost`, `total_friction_and_risk_cost`, `delta_u`, `should_intercept`, `interception_badge`

### `portfolio_manager.py` ↔ `CUSUMFundChangePointDetector`
- Inputs: `sector_id: str`, `default_champion_code: str`, `candidates: List[Dict]`, `snapshot: Optional[Dict]`, `pm: Optional[Any]`
- Outputs: `Dict[str, Any]` with `active_champion_code`, `is_promoted`, `promotion_label`, `scored_candidates`
