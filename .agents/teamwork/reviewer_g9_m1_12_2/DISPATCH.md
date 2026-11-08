# DISPATCH for reviewer_g9_m1_12_2

## Objective
Independently review Milestone 1 (M1): 底层量化因果律与数据真实性严苛纠偏 (Focus: Edge cases, mathematical invariants & robustness).

## Inputs
- `d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md`
- `d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_12\SCOPE.md`
- `d:\Google\Workspace\Wind\.agents\teamwork\worker_g9_m1_12\handoff.md`
- `AGY2_FundAdvisory/portfolio_manager.py`
- `AGY2_FundAdvisory/advisory_engine.py`

## Specific Review Tasks
1. Inspect `FundHolding.holding_days` setter for edge cases: empty batches, negative days, zero days, safety_lock boundary (<7).
2. Math invariant check in `OnlineHeuristicFactorEvolver`: verify dimensions of `P_eff` and `R_eff`, turnover friction calculation, and Sharpe ratio formula.
3. Math invariant check in `evaluate_rebalance_audit`: Brinson equation `alloc_yuan + select_yuan == total_active_add_yuan`.
4. Verify referee file hashes and `DataLoader.simulate_execution` signature.
5. Run tests:
   ```powershell
   py -3 -m pytest tests/test_g9_causal_brinson_and_suitability.py tests/test_challenger_g9_m2_stress.py tests/test_auditor_g9_m2_integrity.py
   ```
6. Deliver verdict: APPROVE or REQUEST_CHANGES.

## Output
Write your review report to:
`d:\Google\Workspace\Wind\.agents\teamwork\reviewer_g9_m1_12_2\handoff.md`
Report: Observation, Logic Chain, Caveats, Conclusion (Verdict: APPROVE / REQUEST_CHANGES), Verification Method.


## 2026-11-08T06:20:59Z
You are reviewer_g9_m1_12_2 (Role: Quant Reviewer 2).
Your working directory is: d:\Google\Workspace\Wind\.agents\teamwork\reviewer_g9_m1_12_2
Read d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md before starting work.
Read d:\Google\Workspace\Wind\.agents\teamwork\reviewer_g9_m1_12_2\DISPATCH.md for your detailed task requirements.
Also read d:\Google\Workspace\Wind\.agents\teamwork\worker_g9_m1_12\handoff.md.

Independently review M1 with focus on edge cases and mathematical invariants:
1. Inspect FundHolding.holding_days setter edge cases (empty batches, safety_lock boundary <7).
2. Check math invariants in factor evolver (P_eff, R_eff, turnover friction, Sharpe formula).
3. Check Brinson-Fachler attribution mathematical identity (alloc_yuan + select_yuan == total_active_add_yuan).
4. Verify referee files and DataLoader.simulate_execution.
5. Run tests:
   py -3 -m pytest tests/test_g9_causal_brinson_and_suitability.py tests/test_challenger_g9_m2_stress.py tests/test_auditor_g9_m2_integrity.py
6. Write your report with explicit verdict (APPROVE / REQUEST_CHANGES) to:
   d:\Google\Workspace\Wind\.agents\teamwork\reviewer_g9_m1_12_2\handoff.md

When complete, send a message to orchestrator_12 notifying completion.
