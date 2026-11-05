## 2026-11-05T02:24:38Z
You are Worker Remediation R8-M1.
Your working directory is d:\Google\Workspace\Wind\.agents\teamwork\worker_remediation_r8_m1\.
Read the original user request at: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md.
Read the project plan at: d:\Google\Workspace\Wind\.agents\teamwork\orchestrator\PROJECT.md.
Read Challenger 1 handoff at: d:\Google\Workspace\Wind\.agents\teamwork\challenger_r8_m1_1\handoff.md.
Read Challenger 2 handoff at: d:\Google\Workspace\Wind\.agents\teamwork\challenger_r8_m1_2\handoff.md.
Also review the project rules at: d:\Google\Workspace\Wind\GEMINI.md.

YOUR TARGET: Milestone 1 Remediation - Fix Scale Decoupling and Dimension Mismatch in data_loader.py

FILE WRITE OWNERSHIP:
You have exclusive write ownership of:
- `AGY2_FundAdvisory/data_loader.py`

PHYSICAL SAFETY REDLINE:
NEVER touch or modify the 4 readonly referee files:
`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

SPECIFIC DEFECT REPAIR INSTRUCTIONS:
1. Fix Critical Bug 1 (calc_offline_2day_return scale decoupling):
   - The total return parquet `aligned_matrix_total_return.parquet` must ONLY be used to calculate the relative percentage return `off_pct` (i.e. `(p_curr - p_prev) / p_prev * 100.0`).
   - Point `off_pt` must NOT use total return index points! Instead:
     - For indices in `EXPANDED_INDEX_CATALOG`, anchor `off_pt` to `EXPANDED_INDEX_CATALOG[code]["fb_point"]` (or read price index from DuckDB/parquet price files).
     - For CSI Dividend (`000922`), strictly ensure `5000.0 <= off_pt <= 6500.0` (e.g., 5500.0 or actual price close), fully complying with Rule 16!
     - For ETFs (such as gold ETF 518880 ~8.45, S&P 500 ETF 513500 ~2.65), anchor `off_pt` to actual ETF prices from DuckDB `v_etfs` or catalog, NEVER using commodity spot AU9999 points (1465.0) or US index points (7812.0).
     - Calculate `off_chg = round(off_pt * (off_pct / 100.0), 3 if is_etf else 2)`.
     - Do not prematurely round tiny returns (e.g. 0.002%) to 0.0.
2. Fix Critical Bug 2 (fetch_custom_realtime_indices ETF chg dimension mismatch):
   - In `fetch_custom_realtime_indices`:
     - When `pt <= 0.0`: set `pt = off_pt`.
     - When weekend/offline quotes return `change_pct == 0.0` and fallback is triggered:
       - Set `chg_pct = off_pct`.
       - Recalculate `chg = round(pt * (off_pct / 100.0), 3 if is_etf else 2)`! NEVER blindly assign `chg = off_chg`.
3. Verification:
   Run verification commands:
   - `py -3 scripts/verify_referee_hashes.py`
   - `py -3 -m pytest AGY2_FundAdvisory/tests/test_challenger_r8_m1_2_stress.py -v` (must be 15/15 PASS!)
   - `py -3 scripts/test_challenger_r8_m1_empirical.py` (must be 119/119 PASS!)
   - `py -3 -m pytest AGY2_FundAdvisory/tests/test_sidebar_remodel_and_bugfixes.py` (must be 6/6 PASS!)

When finished, write a detailed handoff report to `d:\Google\Workspace\Wind\.agents\teamwork\worker_remediation_r8_m1\handoff.md` and send a message to the orchestrator.
