## 2026-11-05T03:02:16Z
You are Challenger R8-M2-1.
Your working directory is d:\Google\Workspace\Wind\.agents\teamwork\challenger_r8_m2_1\.
Read the original user request at: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md.
Read the project plan at: d:\Google\Workspace\Wind\.agents\teamwork\orchestrator\PROJECT.md.
Read Worker handoff at: d:\Google\Workspace\Wind\.agents\teamwork\worker_prod_r8_m2\handoff.md.
Also review the project rules at: d:\Google\Workspace\Wind\GEMINI.md.

YOUR FOCUS: Milestone 2 Adversarial Stress Test - Single Source of Truth & Thermometer Data Sanity
Write an empirical test script (or run python directly) to stress test:
1. Single Source of Truth Strict Parity:
   - For all 14 sectors in `RADAR_SECTOR_CATALOG`: compare valuation percentiles returned by `OpportunityRadarEngine.evaluate_sector` against `IndexValuationEngine.fetch_or_calc_index_valuations()`;
   - Assert `abs(radar_val_pct - corridor_val_pct) < 1e-4` for every sector where benchmark exists in valuation map;
   - Specifically verify CSI Dividend (`csi_dividend` / `000922`): confirm corridor and radar match 100%, and value is in the realistic overheat zone (>85%), completely rejecting the old hardcoded 25.0%.
2. Parquet Path & Fallback Stress:
   - Test that `_calc_dynamic_sector_metrics` loads from `data/processed/aligned_matrix_total_return.parquet` without raising exceptions;
   - Verify all 14 sectors have valid numeric Kaufman ER (0 <= ER <= 1), numeric MA20 Bias, and numeric momentum slope (none are NaN or hardcoded fake constants).
3. Morning Pulse Word Count:
   - Verify generated morning market pulse brief is strictly <= 80 Chinese characters.
4. Run referee check: `py -3 scripts/verify_referee_hashes.py`.

Write your findings to `d:\Google\Workspace\Wind\.agents\teamwork\challenger_r8_m2_1\challenge.md` and handoff report to `d:\Google\Workspace\Wind\.agents\teamwork\challenger_r8_m2_1\handoff.md`. State your verdict: APPROVE or REQUEST_CHANGES. When finished, send a message to the orchestrator.
