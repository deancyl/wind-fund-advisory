# Milestone 3 Dispatch: Long Screenshot Slicing OCR Import, Tail Cleaner & 29-Fund Portfolio

## Mission
Implement G15 Milestone 3 (Phase 3):
1. `slice_long_screenshot_for_ocr(image_bytes)` in `AGY2_FundAdvisory/portfolio_manager.py`:
   - 100% original width without compression
   - Height 1000px, vertical overlap 150px
2. `fuzzy_match_fund_by_name(raw_name)` & `parse_screenshot_ocr_holdings(image_bytes)` in `portfolio_manager.py`:
   - Use local `rapidocr_onnxruntime` + 28,177 fund catalog in `data/master/fund_catalog.parquet`
   - Accounting identity: cost_value = market_value - floating_pnl
   - Fix negative PnL abs() bug (preserve negative float sign) and fix <100 drop bug
3. Tab 2 Top Toolbar "📸 截图导入" popover / dialog in `AGY2_FundAdvisory/app_gui.py`:
   - File uploader, slice OCR parsing, `st.data_editor` preview & edit table, and 1-click write to ledger buttons
4. ActiveRiskSentry Dimension 13 "碎片尾仓清理" in `AGY2_FundAdvisory/advisory_engine.py`:
   - Identify holdings < ¥200 or < 1.0% that have satisfied fee-free redemption periods
   - Tab 2 "🧹 碎片尾仓一键瘦身建议卡" with 1-click simulation sweep to core ballast fund (002351)
5. `combat_29_funds` combat ledger in `AGY2_FundAdvisory/multi_ledger_manager.py`:
   - Exact penny-level accounting to ¥26,615.10 across 29 funds
   - Holding days set to 400 days (>365d fee-free)
   - Tab 2 ledger selector and specialized diagnosis:
     ① 19 tail funds (¥442.70) fee-free sweep
     ② 3 core deep loss sources (#5 Fuguo Dividend -332.54, #6 Huaxia STAR50C -428.48, #8 Zhaoshang Liquor -175.76, total -936.78) surgery plans (e.g. Huaxia same-company C to A zero in-transit switch)
     ③ Pre/post rebalance full-cycle comparison (2018-2026 return and MDD)
6. Write test suite `tests/test_g15_phase3_ocr_and_combat29.py` and run full regression tests.

## Reference Blueprint
- Authoritative Blueprint: `d:\Google\Workspace\Wind\.agents\teamwork\explorer_g15_survey_3\handoff.md`
- Project Document: `d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_18\PROJECT.md`
- Original Request: `d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md`

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Safety Redlines
- NEVER touch the 4 read-only referee files: `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`.
- NEVER modify `DataLoader.simulate_execution` default signature and default fee logic.

## 2026-11-09T18:32:39Z
[Message] timestamp=2026-11-09T18:32:39Z sender=9a123e21-7525-4c57-9715-710c2a94c199 priority=MESSAGE_PRIORITY_HIGH
Task: G15 Generation Milestone 3 (Phase 3): "实装手机长截图高清切片识别导入、碎片尾仓免赎清理器与 29 基真实存量账本".
Reference: explorer_g15_survey_3/handoff.md, ORIGINAL_REQUEST.md lines 206-248, orchestrator_18/PROJECT.md.
