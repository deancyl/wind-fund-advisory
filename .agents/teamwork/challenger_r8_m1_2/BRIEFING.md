# BRIEFING — 2026-11-05T02:25:00Z

## Mission
Adversarial stress testing for Milestone 1: Rule 16 Invariant & Catalog Integrity, Watchlist Cold-Start & Corruption Resistance, AppTest Geometry & Visual Integrity, and Referee Hashes.

## 🔒 My Identity
- Archetype: challenger
- Roles: critic, specialist
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\challenger_r8_m1_2\
- Original parent: 3ef18151-e1aa-4330-83a1-353aa7bcc35e
- Milestone: Milestone 1
- Instance: 2 of 2

## 🔒 Key Constraints
- Review-only — do NOT modify implementation code
- Empirical challenge: write and execute stress tests directly
- If cannot reproduce a bug empirically, it does not count
- State verdict: APPROVE or REQUEST_CHANGES

## Current Parent
- Conversation ID: 3ef18151-e1aa-4330-83a1-353aa7bcc35e
- Updated: 2026-11-05T02:13:48Z

## Review Scope
- **Files to review**:
  - `AGY2_FundAdvisory/data_loader.py` (Rule 16 CSI Dividend 000922 mapping, baseline 5000-6500, EXPANDED_INDEX_CATALOG, validate_and_fetch_code, offline returns)
  - `AGY2_FundAdvisory/app_gui.py` (CSS rules & DOM in Streamlit AppTest, `.val-very-low`, `.val-very-high`, `button[kind="primary"]`)
  - `data/cache/custom_watchlist.json` handling
  - `scripts/verify_referee_hashes.py`
- **Interface contracts**: PROJECT.md, GEMINI.md
- **Review criteria**: Empirical stress test edge cases, cold-start corruption resistance, CSS and geometry invariants, referee hash compliance

## Attack Surface
- **Hypotheses tested**:
  - Rule 16 000922 vs 000015 mapping & point sanity
  - Expanded catalog 38+ entries across 12 sectors
  - Code validator resilience against malformed inputs
  - Watchlist cold start on missing, empty, or corrupted JSON
  - AppTest DOM and CSS rules (.val-very-low, .val-very-high, button[kind="primary"])
  - Offline network fallback point scale
  - Weekend flat fallback change amount scale
- **Vulnerabilities found**:
  - `calc_offline_2day_return("000922")` returns 12189.99 (H00922 total return) instead of price point, violating Rule 16 (5000~6500)
  - In `fetch_custom_realtime_indices`, weekend flat fallback sets `chg = off_chg`, injecting +40.33 yuan into 8-yuan 518880 ETF
- **Untested angles**:
  - Real-time websocket pushes (non-HTTP protocol)

## Loaded Skills
- None requested in dispatch

## Key Decisions Made
- Formulated verdict: REQUEST_CHANGES
- Wrote reproducible test suite `AGY2_FundAdvisory/tests/test_challenger_r8_m1_2_stress.py`
- Documented findings in `challenge.md` and `handoff.md`

## Artifact Index
- `DISPATCH.md` — incoming dispatch instructions
- `BRIEFING.md` — persistent state and context
- `progress.md` — liveness heartbeat
- `challenge.md` — stress test report
- `handoff.md` — 5-component handoff report
- `AGY2_FundAdvisory/tests/test_challenger_r8_m1_2_stress.py` — empirical stress test suite
