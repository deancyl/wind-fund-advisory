# Project: AGY2 Fund Advisory - Stage 2 Web GUI Overhaul

## Architecture
- Presentation Layer: `AGY2_FundAdvisory/app_gui.py` (Streamlit Web GUI, 1080p optimized, zero-ellipsis, zero-sleep, 4 wide cards, 4 tabs).
- Quant Strategy Bridge: `AGY2_FundAdvisory/strategy_bridge.py` (`evaluate_today_rebalance_suitability`, `simulate_rebalance_modes_and_consequences`, `evaluate_intraday_signal`, `get_latest_market_snapshot`, `compute_dynamic_tier_weights`).
- Portfolio Management Engine: `AGY2_FundAdvisory/portfolio_manager.py` (`generate_zero_start_blueprint` with dynamic `action_guide` & `dca_plan`, `fetch_realtime_fund_quota`, `calculate_stock_overlap_matrix`).
- E2E Testing Suite: `AGY2_FundAdvisory/tests/` (`test_phase2_apptest_gui.py`, `test_e2e_gui_render.py`, full pytest suite).
- Launcher & Desktop Host: `AGY2_FundAdvisory/launch_gui.vbs`, Windows detached process management, port 8501 health probe.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| F1 | Anti-Laziness & Strict Constraints | Remove all 4 `time.sleep` calls, remove synthetic elapsed time padding, remove all hardcoded "限额买500" / "现金分红·限额买500" | M1 | R1, Survey |
| F2 | Top Dashboard Slimdown | Compress 3 layers into 1 row of 4 wide cards + 1 compact refresh button; Card 1: Clock & Window, Card 2: Market Tone & Trigger Lines, Card 3: Valuation & Liquidity Temperatures, Card 4: Total Equity & Intraday PnL; all quant formulas moved to `ⓘ` tooltip | M1 | R2, Survey |
| F3 | Tab 1: New Money Zero-Start | Remove scenario dropdown; Step 1: Mode A & Mode B; Step 2: 4 whitebox drawers with dynamic quantitative digests in titles; Step 3: 9-column execution table with dynamic `action_guide` and `dca_plan` banner | M1 | R3, Survey |
| F4 | Tab 2: Holdings & Rebalance Cockpit | Layer 1: Today suitability AI verdict card with 4D pills; Layer 2: Gentle vs Forced dual rebalance modes radio + 4 consequences cards + 9-column orders table + execute button; Layer 3: Holdings table + 3 tools collapsed when holdings exist | M1 | R3, Survey |
| F5 | Tab 3 & Tab 4 Structural Reorganization | Tab 3: Deep checkup & fee toolbox (with overlap matrix exemption); Tab 4: Backtest curves & win rates | M1 | R3, Survey |
| F6 | Streamlit AppTest & Pytest Suite | Add `test_phase2_apptest_gui.py` covering all 8 acceptance test cases (top cards, no ellipsis, 4 tabs navigation, suitability card, dual rebalance modes, 4 consequences, collapsed tools, dynamic guide, AST checks); fix test_bug3 Sunday mock; update legacy test_adversarial_m3_challenger2 assertions | M2 | R4, Survey |
| F7 | Service Restart & Health Verification | Windows native detached restart of Streamlit on port 8501 via `launch_gui.vbs`, health probe `_stcore/health`, verify 100% pytest pass rate | M2 | R4, Survey |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Web GUI Refactoring (`app_gui.py`) | Implement F1, F2, F3, F4, F5 in `app_gui.py` | Survey complete | DONE |
| M2 | Test Suite & Service Restart (`tests/` & 8501) | Implement F6, F7, full test suite pass & service restart | M1 | DONE |

## Interface Contracts
### `app_gui.py` <-> `strategy_bridge.py`
- `StrategyBridge.evaluate_today_rebalance_suitability(pm, active_tier="C3") -> dict`:
  - `verdict_level`: "SUITABLE" | "HOLD_ON" | "FORBIDDEN"
  - `verdict_title`: str
  - `reasons_4d`: `{"market_position_reason": str, "clock_window_reason": str, "deviation_utility_reason": str, "lockup_fee_reason": str}`
  - `d_max`: float
  - `bias_20`: float
- `StrategyBridge.simulate_rebalance_modes_and_consequences(pm, active_tier="C3") -> dict`:
  - `mode_gentle`: `{"mode_name": str, "orders": list, "consequences": {"fee_loss": dict, "in_transit_risk": dict, "risk_shift": dict, "lockup_reset": dict}}`
  - `mode_forced`: `{"mode_name": str, "orders": list, "consequences": {"fee_loss": dict, "in_transit_risk": dict, "risk_shift": dict, "lockup_reset": dict}}`

### `app_gui.py` <-> `portfolio_manager.py`
- `pm.generate_zero_start_blueprint(total_amount, tier) -> dict`:
  - `blueprint["items"]`: each item has `action_guide` (e.g. `单日限额¥500·已拆单`, `承接超额·不限购正常买`, `正常买入`)
  - `blueprint.get("dca_plan")`: str or None

## Code Layout
- `AGY2_FundAdvisory/app_gui.py`: Main Streamlit Web GUI entrypoint
- `AGY2_FundAdvisory/strategy_bridge.py`: Strategy bridge & quant algorithms
- `AGY2_FundAdvisory/portfolio_manager.py`: Portfolio manager & execution logic
- `AGY2_FundAdvisory/tests/test_phase2_apptest_gui.py`: New Stage 2 AppTest suite
- `AGY2_FundAdvisory/tests/test_e2e_gui_render.py`: Existing E2E render tests
- `AGY2_FundAdvisory/tests/test_adversarial_m3_challenger2.py`: Legacy tests to align
