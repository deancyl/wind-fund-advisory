# DISPATCH for worker_g9_m1_12

## Objective
Implement and verify Milestone 1 (M1): 底层量化因果律与数据真实性严苛纠偏.

## Inputs
- `d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md`
- `d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_12\SCOPE.md`
- `d:\Google\Workspace\Wind\.agents\teamwork\explorer_g9_survey_1\handoff.md`
- `AGY2_FundAdvisory/advisory_engine.py`
- `AGY2_FundAdvisory/portfolio_manager.py`
- `AGY2_FundAdvisory/data_loader.py`

## Exclusive Write Ownership
- `AGY2_FundAdvisory/portfolio_manager.py`
- `AGY2_FundAdvisory/advisory_engine.py`
- `AGY2_FundAdvisory/data_loader.py`
(Do NOT modify `AGY2_FundAdvisory/app_gui.py` - owned by M2).

## Hard Constraints
- DO NOT touch the 4 read-only judge files: `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`.
- DO NOT modify `DataLoader.simulate_execution` default function signature or default deduction logic.
- DO NOT touch global `GEMINI.md`.

## Specific Implementation Tasks
1. In `AGY2_FundAdvisory/portfolio_manager.py`, add `@holding_days.setter` to `FundHolding` to support batch-aware holding days assignment and resolve `AttributeError: property 'holding_days' of 'FundHolding' object has no setter` in `test_friction_saving_7day_and_class_c_penalties`.
   ```python
   @holding_days.setter
   def holding_days(self, val: int):
       val = int(val)
       if getattr(self, "batches", None):
           for b in self.batches:
               b.holding_days = val
       else:
           self.batches = [
               HoldingBatch(
                   batch_id=f"B_{self.fund_code}_001",
                   buy_date="",
                   shares=self.shares,
                   cost_nav=self.cost_price,
                   holding_days=val,
                   safety_lock=(val < 7)
               )
           ]
   ```
2. Verify all R3 requirements in `advisory_engine.py`:
   - `OnlineHeuristicFactorEvolver._evaluate_population`: $P[:-1]$ acts on $R[1:]$, 10 bps turnover friction deduction in `nav_dynamic`, 2.0% risk-free rate deduction (`0.02 / 250.0`) in Sharpe ratio calculation.
   - `get_60d_rolling_nav_and_trajectory`: 12 slices of 5-day walk-forward rolling evolution, no `lam` linear interpolation.
   - `_extract_sector_price_matrix`: A-share calendar alignment, zero `np.linspace` fake series.
   - `ActiveRiskSentry.inspect_portfolio`: 3-tier AUM lookup, no `else: aum = 2.5` fallback, C1-C5 appropriateness boundary alert.
   - `evaluate_sector`: append intraday chg, recalculate MA20, Bias20, Slope20, ER20, dynamic quantitative evidence text.
   - `evaluate_rebalance_audit`: Brinson 3D excess attribution (allocation, selection, friction saving) with strict mathematical identity check.
3. Run and verify all targeted tests:
   ```powershell
   py -3 -m pytest tests/test_g9_causal_brinson_and_suitability.py
   py -3 -m pytest tests/test_causality_adversarial_m1.py
   py -3 -m pytest tests/test_challenger_g9_m1_adversarial.py tests/test_challenger_g9_m2_adversarial.py
   ```
   Ensure 100% green pass!

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Output
Write your completion handoff report to:
`d:\Google\Workspace\Wind\.agents\teamwork\worker_g9_m1_12\handoff.md`
Report: Observation, Logic Chain, Caveats, Conclusion, Verification Commands & Results.

## 2026-11-08T06:07:50Z
You are worker_g9_m1_12 (Role: Quant Implementation Worker).
Your working directory is: d:\Google\Workspace\Wind\.agents\teamwork\worker_g9_m1_12
Read d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md before starting work.
Read d:\Google\Workspace\Wind\.agents\teamwork\worker_g9_m1_12\DISPATCH.md for your detailed task requirements.
Also read d:\Google\Workspace\Wind\.agents\teamwork\explorer_g9_survey_1\handoff.md for code locations and the holding_days setter fix.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your task:
1. Implement the @holding_days.setter in FundHolding in AGY2_FundAdvisory/portfolio_manager.py.
2. Verify all R3 quant causality requirements in advisory_engine.py, portfolio_manager.py, and data_loader.py.
3. Run tests:
   py -3 -m pytest tests/test_g9_causal_brinson_and_suitability.py
   py -3 -m pytest tests/test_causality_adversarial_m1.py
   py -3 -m pytest tests/test_challenger_g9_m1_adversarial.py tests/test_challenger_g9_m2_adversarial.py
4. Ensure 4 read-only judge files and DataLoader.simulate_execution are 100% untouched.

Write your report to:
d:\Google\Workspace\Wind\.agents\teamwork\worker_g9_m1_12\handoff.md

When complete, send a message to orchestrator_12 notifying completion.
