# BRIEFING — 2026-11-03T07:37:00Z

## Mission
Investigate R1.1 — Optimizer Degradation, Mathematical Invariants, and Purchasing Limit Splitting Logic.

## 🔒 My Identity
- Archetype: explorer
- Roles: investigation, synthesis
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\teamwork_explorer_prod_1
- Original parent: 79413d19-45ad-4a69-b696-81c549751856
- Milestone: Production Deep Refactoring R1.1

## 🔒 Key Constraints
- Read-only investigation — do NOT implement in production source code.
- Write only to working directory: d:\Google\Workspace\Wind\.agents\teamwork\teamwork_explorer_prod_1
- DO NOT modify judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py
- Reply in Chinese to user/messages.

## Current Parent
- Conversation ID: 79413d19-45ad-4a69-b696-81c549751856
- Updated: 2026-11-03T07:37:00Z

## Investigation State
- **Explored paths**:
  - `AGY2_FundAdvisory/portfolio_optimizer.py` (`WinRateOptimizer`, `_slsqp_optimize`, `_compute_hrp_weights`, `_local_search`, `_optimize_fixed_n`)
  - `AGY2_FundAdvisory/strategy_bridge.py` (`compute_n_funds_model_portfolio`, `generate_zero_start_blueprint`)
  - `AGY2_FundAdvisory/portfolio_manager.py` (`generate_zero_start_blueprint`)
  - `AGY2_FundAdvisory/app_gui.py` (Tab 1 consumption of blueprints and model weights)
  - Existing tests: `test_portfolio_manager.py`, `test_strategy_bridge.py`, `test_phase2_apptest_gui.py`, `test_acceptance_r1_r7.py`
- **Key findings**:
  - **Optimizer 1/N Collapse Root Cause 1**: Win rate objective in `_slsqp_optimize` uses non-differentiable indicator `(ann_ret >= target_return)`. Its finite-difference gradient is identically zero ($\nabla_w \text{WR} \equiv \mathbf{0}$). SLSQP starting at $x_0 = [1/n, \dots, 1/n]$ terminates immediately with 0 iterations, returning equal weights.
  - **Optimizer 1/N Collapse Root Cause 2**: `_local_search` line 959 calls `_slsqp_optimize` directly instead of `_optimize_by_model_type`, completely replacing HRP weights with equal weights whenever a swap is evaluated.
  - **Optimizer 1/N Collapse Root Cause 3**: Hardcoded 1/N fallback in `strategy_bridge.py:4363` (`eq = round(1.0 / n_target, 4)`).
  - **Invariant 1 Drift Root Cause 1 (Float Rounding & Drift)**: Rounding weights `round(w, 4)` and items `round(total_capital * w, 2)` without last-penny/residual reconciliation causes 6 funds to sum to 100,020.0 (100.02%) and 12 funds to sum to 99,960.0 (99.96%).
  - **Invariant 1 Drift Root Cause 2 (Purchasing Limit & Companion Drift)**: In `strategy_bridge.py:4928`, adding SPX companion fund `050025` with 0.06 only decrements `002351` if `002351 >= 0.20`. When `< 0.20`, nothing is decremented, resulting in 106% weight. In `portfolio_manager.py`, exhausted alternatives leave unallocated cash in `remaining_cash`, causing item sums to drop below 100%. If companion fund was already in portfolio, it is counted twice.
  - **Mathematical Solution**: Smooth Sigmoid surrogate for conditional win rate, model-specific score-tilted initial prior $x_0$, convex CVaR tail risk penalty, Half-Kelly log growth with momentum, and strict Penny & Percentage reconciliation algorithm for Invariant 1.
- **Unexplored areas**: None for R1.1 scope.

## Key Decisions Made
- Formulate complete mathematical specifications and concrete `.patch` proposals for both `portfolio_optimizer.py`, `strategy_bridge.py`, and `portfolio_manager.py`.

## Artifact Index
- `DISPATCH.md` — Initial dispatch message
- `progress.md` — Progress heartbeat
- `BRIEFING.md` — Working memory
- `handoff.md` — 5-component comprehensive handoff report
