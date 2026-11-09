## 2026-11-09T15:08:10Z
You are explorer_g15_survey_3, a read-only exploration agent.
Your working directory is: d:\Google\Workspace\Wind\.agents\teamwork\explorer_g15_survey_3\

MANDATORY FIRST STEP:
Read the full user specification at:
d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md

YOUR MISSION:
Survey the codebase for G15 Phase 3 requirements: Long Screenshot Slicing OCR Import, Tail Fund Cleaner, and 29-Fund Real Combat Portfolio in AGY2_FundAdvisory/portfolio_manager.py, multi_ledger_manager.py, app_gui.py, and test suites:
1. Long Screenshot Slicing OCR/Multimodal Import Engine:
- In Tab 2 top toolbar, design "📸 截图导入持仓" modal dialog.
- Implement algorithm slice_long_screenshot_for_ocr(image_bytes): 100% original width without compression, height 1000px per segment, 150px vertical overlap.
- Check python environment for available OCR engines (RapidOCR / PaddleOCR / EasyOCR / Windows OCR or multimodal fallback).
- Design fuzzy_match_fund_by_name(raw_name): strip ellipsis and suffixes, fuzzy match 6-digit fund code.
- Auto-extract fund name, holding amount, yesterday PnL, holding total PnL. Compute cost = holding amount - holding PnL. Generate editable preview table, one-click write to ledger.
- Inspect the actual user long screenshot: C:/Users/deanc/.gemini/antigravity/brain/1395b6f9-733c-4446-9cdb-f33a19e5f711/.user_uploaded/media_1794236135877_65af68f3.jpg.
2. Tail Fund / "Wool" Fund Cleaner:
- In ActiveRiskSentry and Tab 2, design tail fund cleaner: scan holding amount < ¥200 or < 1.0% with holding days >= redemption fee-free threshold.
- In Tab 2, generate "🧹 碎片尾仓一键瘦身建议卡", count tail funds, calculate zero-fee recoverable capital, support simulated clearing and consolidation to core foundation funds.
3. Real 29-Fund Portfolio (¥26,615.10):
- In MultiLedgerManager, preconfigure / update ledger "实战存量组合（29只·¥2.66万）".
- Exactly mirror the 29 holdings from user screenshot: top 7 core (5681.55, 5279.05, 4536.85, 4101.71, 2432.90[-332.54], 2072.52[-428.48], 1023.71), 3 waist (524.24[-175.76], 395.73, 124.14), 19 tail fractions (89.60 down to 0.59, sum ¥442.70), holding days > 365.
- Support switching to this portfolio in Tab 2 dropdown, displaying:
  ① 19 tail funds (¥442.70) zero-fee sweep plan;
  ② Deep loss sources #5, #6, #8 (sum loss -¥936.78) replacement & grid breakeven;
  ③ Pre- vs post-optimization full-cycle NAV and drawdown comparison.
4. Test suites & physical redlines:
- Check existing tests in tests/, test_infra.py (read-only), test_adv_final_closure.py, etc.
- Detail what new unit tests need to be added for OCR slicing, tail cleaner, 29-fund ledger, etc.
5. Reference audit reports:
- c:\Users\deanc\Downloads\agy2_v9_comprehensive_audit_and_real_portfolio_combat.md

PHYSICAL REDLINES:
Remember you are read-only. Do NOT modify source files. Never touch judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py.
Write your full findings and concrete code recommendations into:
d:\Google\Workspace\Wind\.agents\teamwork\explorer_g15_survey_3\handoff.md
Update progress.md as you work.
When done, send a completion message back to the orchestrator.
