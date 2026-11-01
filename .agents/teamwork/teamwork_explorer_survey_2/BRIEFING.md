# BRIEFING — 2026-10-31T23:38:50Z

## Mission
只读调查阶段一已实现的后端量化算法与数据接口，详细梳理其在 `app_gui.py` 中的装配与调用方式，输出详尽契约与对接伪代码。

## 🔒 My Identity
- Archetype: explorer
- Roles: investigation, synthesis
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\teamwork_explorer_survey_2
- Original parent: 15a3e419-5e4d-47c4-a669-7f8d1a1ddcee
- Milestone: survey_phase2_backend_contracts

## 🔒 Key Constraints
- Read-only investigation — do NOT implement or modify source code
- Strictly write metadata/reports in d:\Google\Workspace\Wind\.agents\teamwork\teamwork_explorer_survey_2\
- Comply with all Windows desktop rules & Wind advisory domain rules
- Reply in Chinese

## Current Parent
- Conversation ID: 15a3e419-5e4d-47c4-a669-7f8d1a1ddcee
- Updated: 2026-10-31T23:38:50Z

## Investigation State
- **Explored paths**:
  - `AGY2_FundAdvisory/strategy_bridge.py`: lines 1295-1330, 1995-2070, 2193-2320, 2336-2750, 4050-4465, 4890-5465.
  - `AGY2_FundAdvisory/portfolio_manager.py`: lines 1624-1685, 3185-3354, 3920-4080, 5967-6015.
  - `AGY2_FundAdvisory/data_loader.py`: structure & full returns matrix loading.
  - `AGY2_FundAdvisory/app_gui.py`: top header, cards 1-4, tab structure, 9-column tables, overlap matrix call.
- **Key findings**:
  1. `evaluate_today_rebalance_suitability` returns `verdict_level` (SUITABLE/HOLD_ON/FORBIDDEN), `verdict_title`, and `reasons_4d` (`market_position_reason`, `clock_window_reason`, `deviation_utility_reason`, `lockup_fee_reason`).
  2. `simulate_rebalance_modes_and_consequences` returns `mode_gentle` and `mode_forced`, each containing `orders` (with SWITCH/BUY/SELL and routes) and `consequences` (fee_loss, in_transit_risk, risk_shift, lockup_reset).
  3. `generate_zero_start_blueprint` dynamically generates `action_guide` (e.g. `单日限额¥X·已拆单`, `承接超额·不限购正常买`) and `dca_plan`. `app_gui.py` previously hardcoded `"现金分红·限额买500"`, which must be replaced by reading `it.get("action_guide")`.
  4. Top 4 Wide Cards data sources:
     - Card 1: `TradingClock.get_market_window_status` + `StrategyBridge.get_rebalance_grid_status` (`days_to_next`, `countdown_str`).
     - Card 2: `StrategyBridge.get_latest_market_snapshot` (`market_state`, `c300_price`, `m20_price`, `m60_price`, `trigger_lines["surge_line"]`, `trigger_lines["breakdown_line"]`).
     - Card 3: `snapshot` (`erp_percentile`, `dr007`, `dr007_spread_bp`, `option_iv_pct`, `ic_annualized_basis_rate`).
     - Card 4: `pm.total_equity` (or recalculated) + `pm.calculate_intraday_pnl()` (`total_est_pnl`, `total_est_pnl_pct`).
  5. `calculate_stock_overlap_matrix` provides `max_non_diag_unexcused`, `exempt_pairs`, `alerts`, `matrix_notes`. Currently `app_gui.py` incorrectly computes `max_non_diag` over the raw matrix without exempting standard pairs (`100032+005561`, `050025+001071`), causing false positive warnings.
- **Unexplored areas**: None. All survey tasks fully covered.

## Key Decisions Made
- Fully documented contract specs and frontend pseudocode for the implementer agent.

## Artifact Index
- DISPATCH.md — incoming instructions
- BRIEFING.md — working memory and identity
- progress.md — liveness heartbeat
- handoff.md — final survey report
