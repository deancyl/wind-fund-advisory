# DISPATCH for auditor_g9_m1_12

## Objective
Forensic integrity audit of Milestone 1 (M1): 底层量化因果律与数据真实性严苛纠偏.

## Inputs
- `d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md`
- `d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_12\SCOPE.md`
- `d:\Google\Workspace\Wind\.agents\teamwork\worker_g9_m1_12\handoff.md`
- `AGY2_FundAdvisory/portfolio_manager.py`
- `AGY2_FundAdvisory/advisory_engine.py`
- `AGY2_FundAdvisory/data_loader.py`
- `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`

## Specific Integrity Checks
1. Judge Files Integrity Check:
   - Calculate SHA-256 hashes of:
     - `AGY2_FundAdvisory/judge_engine.py` (Must match: 76f930371176de7ee6a413174b030101e3210ac6e037f5d10fe229af31cc07be)
     - `AGY2_FundAdvisory/holdout_vault.py` (Must match: 88122eaf647040a410e2fd95da81077db10149a498a47340ff40b670bd031d2a)
     - `AGY2_FundAdvisory/AGENT_SPEC.md` (Must match: a346586f9bd2dc0ee83e665bd18e7a6471464c9f7b658e392b989b800cd63957)
     - `tests/test_infra.py` (Must match: 48bee0da300d7c0a0848ec1376e4b9b2e55224d2736081713b4340f0362cd100)
2. DataLoader.simulate_execution Integrity Check:
   - Verify function signature has default `(weights_df, prices_df, is_otc=True, penalty_days=7, penalty_rate=0.015, etf_impact=0.001)`.
   - Verify deduction logic is not bypassed.
3. Code Authenticity Check:
   - Check `advisory_engine.py` for fake series or shortcuts (`np.linspace`, `else: aum = 2.5`, etc. must be absent).
   - Check `portfolio_manager.py` for genuine `FundHolding.holding_days` implementation.
   - Verify no test-specific if/else hardcoding or dummy implementations.
4. Deliver verdict: CLEAN or INTEGRITY VIOLATION.

## Output
Write your audit report to:
`d:\Google\Workspace\Wind\.agents\teamwork\auditor_g9_m1_12\handoff.md`
Report: Observation, Logic Chain, Caveats, Conclusion (Verdict: CLEAN / INTEGRITY VIOLATION), Verification Method.
