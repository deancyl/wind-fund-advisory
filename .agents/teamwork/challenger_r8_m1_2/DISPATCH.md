# Dispatch: Challenger R8-M1-2
Working directory: d:\Google\Workspace\Wind\.agents\teamwork\challenger_r8_m1_2\
Original Request: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
Worker Handoff: d:\Google\Workspace\Wind\.agents\teamwork\worker_prod_r8_m1\handoff.md
Target: Milestone 1 Adversarial Verification - Rule 16 000922 Benchmark Invariant, AppTest Geometry & CSS Collision, Custom Watchlist Cold Start & Invalidation

## 2026-11-05T02:13:48Z
You are Challenger R8-M1-2.
Your working directory is d:\Google\Workspace\Wind\.agents\teamwork\challenger_r8_m1_2\.
Read the original user request at: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md.
Read the project plan at: d:\Google\Workspace\Wind\.agents\teamwork\orchestrator\PROJECT.md.
Read the Worker handoff report at: d:\Google\Workspace\Wind\.agents\teamwork\worker_prod_r8_m1\handoff.md.
Also review the project rules at: d:\Google\Workspace\Wind\GEMINI.md.

YOUR FOCUS: Adversarial Stress Testing for Milestone 1
Write an empirical test script (e.g. in your working directory or execute via python) to stress test:
1. Rule 16 Invariant & Catalog Integrity:
   - Verify CSI Dividend is strictly `000922` and mapped points are in the 5000~6500 range, rejecting `000015`;
   - Verify `EXPANDED_INDEX_CATALOG` contains at least 38 valid entries across 12 sectors;
   - Test `validate_and_fetch_code` with edge-case invalid codes (e.g. `999999`, `000000`, alpha codes, truncated strings) and valid 6-digit codes.
2. Watchlist Cold-Start & Corruption Resistance:
   - Test behavior when `data/cache/custom_watchlist.json` is missing, empty, or corrupted JSON: does the system safely fall back to default symbols without throwing an unhandled exception?
   - Test save & reload round-trip preserves selection order and custom added entries.
3. AppTest Geometry & Visual Integrity:
   - Run Streamlit AppTest to verify that `.val-very-low, .val-very_low` and `.val-very-high, .val-very_high` CSS rules are present in the DOM;
   - Verify `button[kind="primary"]` styles enforce `#ffffff !important`;
   - Verify no collision or overflow crashes occur in the sidebar layout.
4. Run referee hash check: `py -3 scripts/verify_referee_hashes.py`.

Write your findings to d:\Google\Workspace\Wind\.agents\teamwork\challenger_r8_m1_2\challenge.md and handoff report to d:\Google\Workspace\Wind\.agents\teamwork\challenger_r8_m1_2\handoff.md. State your verdict: APPROVE or REQUEST_CHANGES. When finished, send a message to the orchestrator.
