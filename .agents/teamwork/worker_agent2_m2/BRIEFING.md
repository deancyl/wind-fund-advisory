# BRIEFING — 2026-10-30T10:21:00+08:00

## Mission
Implement R4 (EWMA Volatility Inverse & Dynamic Risk Budgeting) and R5 (Rebalance Net Utility Interceptor & Friction Optimization) for Milestone 2 of AGY2_FundAdvisory.

## 🔒 My Identity
- Archetype: worker
- Roles: implementer, qa, specialist
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\worker_agent2_m2\
- Original parent: 7eb668ae-6843-4834-9b3d-3455ac86af88
- Milestone: Milestone 2

## 🔒 Key Constraints
- STRICT READ-ONLY SAFETY REDLINE: NEVER touch, modify, or unlock judge_engine.py, holdout_vault.py, AGENT_SPEC.md, or tests/test_infra.py!
- Only modify allowed files: data_loader.py, strategy_bridge.py, portfolio_manager.py.
- Follow Integrity Mandate: genuine logic, real state and calculations, no hardcoded values or bypasses.
- Preserve C1-C5 risk monotonicity: Equity(C1) < Equity(C2) < Equity(C3) < Equity(C4) < Equity(C5) across all states.
- Ensure deep bear stop-loss limits: Equity(C4) <= 55%, Equity(C5) <= 70%.
- Ensure tests pass 100%.

## Current Parent
- Conversation ID: 7eb668ae-6843-4834-9b3d-3455ac86af88
- Updated: 2026-10-30T10:21:00+08:00

## Task Summary
- **What to build**:
  1. In data_loader.py: implement `DataLoader.compute_ewma_volatility_and_correlation(df, window=60, span=60, asset_cols=None) -> Tuple[pd.Series, pd.DataFrame]`.
  2. In strategy_bridge.py: calculate 60-day EWMA annualized vol & corr; inverse vol weighting proportional to base_vol / max(vol, 0.08); transfer trimmed risk budget 100% to low-vol pure bond ballast (002351 / 000086); preserve C1-C5 monotonicity & deep bear stop-loss.
  3. In portfolio_manager.py: implement `calculate_rebalance_net_utility(...)` with Delta U calculation; same-company T+1 SWITCH Delta t=0 => cost=0; cross-company T+2~4 with volatility discount; Delta U <= 0 interception with badge; same-company switching convenience bonus (+5.0 points) in fund scoring/selection.
- **Success criteria**: All relevant pytest unit tests pass cleanly, 100% genuine implementation.
- **Interface contracts**: PROJECT.md & explorer_survey_2 handoff.md.
- **Code layout**: AGY2_FundAdvisory/

## Key Decisions Made
- `data_loader.py`: Implemented 60-day EWMA annualized volatility and correlation matrix computation on pct_change returns with fallback defaults for missing columns or small sample sizes.
- `strategy_bridge.py`: Implemented asset-to-proxy mapping `FUND_TO_PROXY_INDEX` and caching `_CACHED_EWMA_VOLS`, `_CACHED_CORR_MAT` to prevent repeated disk I/O during heavy grid searches. Enforced non-overlapping equity intervals per market regime (BULL, OSCILLATING, BEAR) ensuring strictly monotonic equity allocations across C1–C5 and deep bear caps (C4 <= 55%, C5 <= 70%).
- `portfolio_manager.py`: Implemented `calculate_rebalance_net_utility` modeling exact FIFO redemption fee, subscription fee (CSRC net purchase price formula), and in-transit opportunity cost ($cost = \text{Amount} \times \sigma_{\text{index}} \times \sqrt{\Delta t_{\text{arrive}} / 250}$). Implemented same-company +5.0 point convenience bonus and integrated net utility gating into `generate_rebalance_plan` and `submit_rebalance_orders`.

## Change Tracker
- **Files modified**:
  - `AGY2_FundAdvisory/data_loader.py`: Added `compute_ewma_volatility_and_correlation`.
  - `AGY2_FundAdvisory/strategy_bridge.py`: Added EWMA inverse-vol budgeting, bond ballast budget transfer, regime monotonicity intervals.
  - `AGY2_FundAdvisory/portfolio_manager.py`: Added same-company bonus, `calculate_rebalance_net_utility`, plan/order interception logic.
- **Build status**: PASS (94/94 tests passed)
- **Pending issues**: None

## Quality Status
- **Build/test result**: All 94 tests passed (65 in baseline & m2 tests, 29 in challenger & dynamic risk tests)
- **Lint status**: Clean
- **Tests added/modified**: Created `tests/test_m2_r4_r5_optimization.py` with 9 dedicated unit tests

## Loaded Skills
- None explicitly loaded. Antigravity finance domain principles applied.

## Artifact Index
- d:\Google\Workspace\Wind\.agents\teamwork\worker_agent2_m2\DISPATCH.md — Dispatch instructions
- d:\Google\Workspace\Wind\.agents\teamwork\worker_agent2_m2\BRIEFING.md — Persistent context & state
- d:\Google\Workspace\Wind\.agents\teamwork\worker_agent2_m2\progress.md — Progress & heartbeat
- d:\Google\Workspace\Wind\.agents\teamwork\worker_agent2_m2\handoff.md — Final handoff report
