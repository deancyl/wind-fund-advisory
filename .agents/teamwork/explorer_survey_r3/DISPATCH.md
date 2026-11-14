## 2026-11-14T08:59:52Z
You are Explorer 3 for the G18 iteration of the Wind project.
Working directory: d:\Google\Workspace\Wind
Your state folder: d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r3\
Original request path: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md

READ `ORIGINAL_REQUEST.md` FIRST.
Your focus is R3 (Screenshot OCR + Yesterday Return Mathematical Fingerprint Dual-Factor Matching Engine) and R4 constraints:
1. In `AGY2_FundAdvisory/portfolio_manager.py` and `AGY2_FundAdvisory/app_gui.py`:
   - Inspect `parse_long_screenshot_holdings` and `fuzzy_match_fund_by_name`.
   - How are holdings extracted from OCR text? Where are market value $M$ and yesterday PnL $dM$ parsed?
   - How to implement the formula $r_{imp} = dM / (M - dM)$?
   - How to query local fund net asset value database for the latest trading day return, and compute closeness to $r_{imp}$ (error < 0.05%)?
   - How to combine 60% OCR name keyword similarity + 40% return closeness for joint scoring and ranking to lock the 6-digit fund code?
   - Check fallback logic: when $dM$ is missing or $(M - dM) \le 0$, fallback to 100% OCR text similarity and mark "无收益率指纹" in preview table.
   - Inspect preview table columns in `app_gui.py`: how to present 「匹配置信度」 and 「隐含昨日涨跌幅核验结果」.
2. In R4:
   - Check `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py` (ensure they are untouched).
   - Check `DataLoader.simulate_execution` signature and fee logic.
   - Check test suite runner commands and existing test files.
3. Write your detailed technical findings to `analysis.md` in your state folder (`d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r3\analysis.md`), and write `handoff.md` in the same folder.
4. Send a message to the orchestrator when complete with summary and artifact path.

REMINDER: You are read-only. Do NOT modify source code files. You must NOT modify judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py, nor alter DataLoader.simulate_execution.
