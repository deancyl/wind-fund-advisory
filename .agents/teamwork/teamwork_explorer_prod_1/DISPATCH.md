## 2026-11-03T07:01:06Z
**Context**: You are Explorer 1 for the Production Deep Refactoring of Wind Advisory System.
**Working Directory**: d:\Google\Workspace\Wind\.agents\teamwork\teamwork_explorer_prod_1
**Authoritative Request File**: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
**Project Root**: d:\Google\Workspace\Wind

**Mission**: Investigate R1.1 — Optimizer Degradation, Mathematical Invariants, and Purchasing Limit Splitting Logic.

**Specific Tasks**:
1. Read `ORIGINAL_REQUEST.md` completely before starting.
2. Inspect `portfolio_optimizer.py`, `strategy_bridge.py`, and related modules in `AGY2_FundAdvisory/` or project root.
3. Investigate why multi-fund optimization collapses into 1/N equal weights or fails to differentiate among the four models (`hrp_cvar`, `cond_winrate`, `min_cvar`, `kelly_momentum`).
   - Check objective functions, gradients, initial weights (`w0`), bounds/constraints, and penalty terms.
   - Analyze how risk budget, score tilting, and core+satellite tiering should be mathematically formulated.
4. Investigate `generate_zero_start_blueprint`:
   - Trace how daily purchasing limits (单日限购) and companion fallback funds are handled.
   - Pinpoint why total allocated amount exceeds 100% or total capital, and where companion allocations fail to subtract from original allocations.
5. Define the exact mathematical formulations and code changes needed to guarantee:
   - Invariant 1: Sum of `allocated_amount` == `total_capital`, sum of `target_weight_pct` == `100.0%`.
   - Invariant 2: Differentiated weight distributions for all 4 models across different `num_funds` (e.g. 6, 12).
6. Note any read-only constraints: DO NOT modify `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`.
