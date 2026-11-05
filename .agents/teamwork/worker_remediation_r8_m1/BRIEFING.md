# BRIEFING — 2026-11-05T02:35:00Z

## Mission
Milestone 1 Remediation: Fix scale decoupling and dimension mismatch in `AGY2_FundAdvisory/data_loader.py` to satisfy Rule 16 and all Challenger empirical & stress tests.

## 🔒 My Identity
- Archetype: worker
- Roles: implementer, qa, specialist
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\worker_remediation_r8_m1\
- Original parent: 3ef18151-e1aa-4330-83a1-353aa7bcc35e
- Milestone: Milestone 1 Remediation

## 🔒 Key Constraints
- Exclusive write ownership: `AGY2_FundAdvisory/data_loader.py`
- Physical safety redline: NEVER touch referee files (`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`)
- Rule 16 Invariant: CSI Dividend (000922) baseline point strictly in [5000.0, 6500.0]
- Integrity mandate: No hardcoding test results, genuine logic only
- Rule user_global & GEMINI.md compliance

## Current Parent
- Conversation ID: 3ef18151-e1aa-4330-83a1-353aa7bcc35e
- Updated: 2026-11-05T02:35:00Z

## Task Summary
- **What to fix**:
  1. `calc_offline_2day_return`:
     - Total return parquet used ONLY for `off_pct`.
     - Point `off_pt` anchored to price index / ETF base points from catalog or DuckDB, never total return points.
     - `000922` point in 5000~6500.
     - ETF points (e.g. 518880 ~8.45, 513500 ~2.65) anchored to actual ETF prices, not commodity/US index points.
     - `off_chg` calculated from `off_pt * (off_pct / 100.0)`.
     - Do not prematurely round tiny returns (e.g. 0.002%) to 0.0.
  2. `fetch_custom_realtime_indices`:
     - Recalculate `chg = round(pt * (off_pct / 100.0), 3 if is_etf else 2)` when fallback is triggered.
- **Success criteria**:
  - `verify_referee_hashes.py` passes (4/4 PASS)
  - `test_challenger_r8_m1_2_stress.py` 15/15 PASS
  - `test_challenger_r8_m1_empirical.py` 119/119 PASS
  - `test_sidebar_remodel_and_bugfixes.py` 6/6 PASS

## Key Decisions Made
- Total return matrix in `calc_offline_2day_return` is strictly used only for relative percentage change `off_pct`.
- Point `off_pt` is anchored to actual prices: for ETFs, queried from DuckDB `v_etfs` or `EXPANDED_INDEX_CATALOG`, never using underlying commodity/US index points.
- Rule 16 invariant explicitly guarded so `000922` point is strictly bounded in [5000.0, 6500.0].
- Tiny returns (< 0.01%) format with higher precision (`_format_offline_return_pct`) to eliminate false 0.00% flat rows (such as 511360).
- In `fetch_custom_realtime_indices`, `chg` is recalculated via `round(pt * (off_pct / 100.0), 3 if (is_etf or pt < 100.0) else 2)`, eliminating cross-dimension leakage.

## Change Tracker
- **Files modified**: `AGY2_FundAdvisory/data_loader.py` (fixed scale decoupling in `calc_offline_2day_return` and dimension recalculation in `fetch_custom_realtime_indices`)
- **Build status**: All verification suites pass
- **Pending issues**: None

## Quality Status
- **Build/test result**:
  - `verify_referee_hashes.py`: 4/4 PASS
  - `test_challenger_r8_m1_2_stress.py`: 15/15 PASS
  - `test_challenger_r8_m1_empirical.py`: 119/119 PASS
  - `test_sidebar_remodel_and_bugfixes.py`: 6/6 PASS
- **Lint status**: clean
- **Tests added/modified**: Challenger test suites now 100% green

## Loaded Skills
None
