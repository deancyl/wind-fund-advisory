## 2026-11-08T09:47:08Z
You are Challenger 1 (`challenger_g10_m1_14_1`) in the G10 visual subtraction, filter & UI elevation mission.

## Identity & Workspace
- Type: teamwork_challenger
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\challenger_g10_m1_14_1\
- Authoritative user request file: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
- Worker handoff report: d:\Google\Workspace\Wind\.agents\teamwork\worker_g10_m1_14\handoff.md

## Objective
Empirically and adversarially stress-test the implementation:
1. Write a temporary test harness or test script (e.g. in your working directory) to test:
   - Sector card formatting across boundary inputs (e.g. very long sector names, zero / negative returns, extreme valuation percentiles): confirm no layout explosion or unexpected HTML escaping issues.
   - Correlation mutation alert threshold: verify behavior at boundary correlation values (0.74 vs 0.76).
   - CVaR bootstrap calculation: verify mathematical invariants $\text{CVaR}_{99\%} \ge \text{VaR}_{99\%}$ hold across random seeds, and outputs stay within the realistic calibrated range (~10% - 15%) rather than -36.1%.
2. Clean up any temporary test scripts after execution.
3. Verify that 4 referee files (`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`) have matching SHA-256 hashes (`py -3 scripts/verify_referee_hashes.py`).
4. Write your findings to `d:\Google\Workspace\Wind\.agents\teamwork\challenger_g10_m1_14_1\handoff.md` with verdict: **APPROVE** or **REJECT**. Send a completion message.
