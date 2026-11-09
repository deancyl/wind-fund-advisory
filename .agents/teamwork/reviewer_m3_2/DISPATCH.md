# DISPATCH — reviewer_m3_2
## Mission
Independent code and UX review of G15 Phase 3 implementation: Long screenshot slicing OCR import, tail fund cleaner (Dimension 13), and real 29-fund combat portfolio diagnosis.

## Instructions
1. Read `d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md` (lines 206-248).
2. Read worker report: `d:\Google\Workspace\Wind\.agents\teamwork\worker_m3\handoff.md`.
3. Check code quality, robustness, boundary edge cases, and UI/UX alignment:
   - Check `slice_long_screenshot_for_ocr`: verify image slicing algorithm maintains 100% width, target_height=1000, overlap=150.
   - Check `fuzzy_match_fund_by_name`: verify fuzzy matching logic with 28,177 fund dictionary, handling ellipsis and suffixes.
   - Check `combat_29_funds`: verify 29 funds, market value 26,615.10 yuan, holding days >= 365.
   - Check `ActiveRiskSentry` Dimension 13: verify 19 tail funds and 442.70 yuan recoverable cash correctly flagged.
4. Run tests:
   `py -3 -m pytest tests/test_g15_phase3_ocr_and_combat29.py tests/test_infra.py -v`
5. Verify 4 read-only referee files are untouched: `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`.
6. Write your structured verdict (`APPROVE` or `REQUEST_CHANGES`) to `handoff.md` and send message to parent.


## 2026-11-09T19:18:44Z
You are reviewer_m3_2. Your working directory is d:\Google\Workspace\Wind\.agents\teamwork\reviewer_m3_2.
Read d:\Google\Workspace\Wind\.agents\teamwork\reviewer_m3_2\DISPATCH.md and d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md.
Review G15 Phase 3 implementation in portfolio_manager.py, advisory_engine.py, multi_ledger_manager.py, app_gui.py, and tests/test_g15_phase3_ocr_and_combat29.py.
Check algorithm edge cases, fuzzy matching precision, accounting consistency, and UI integration.
Run tests and write your verdict (APPROVE or REQUEST_CHANGES) with rationale to handoff.md, then send a message to parent (ID: 9a123e21-7525-4c57-9715-710c2a94c199).
