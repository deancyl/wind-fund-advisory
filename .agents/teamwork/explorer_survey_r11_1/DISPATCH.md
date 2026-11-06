## 2026-11-06T01:03:35Z
[Task: Code Survey on PortfolioManager (R2 & R5)]
You are an Explorer. You do NOT write implementation code or modify codebase files. You investigate the codebase and write your findings to `d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r11_1\survey_pm.md` and complete a structured `handoff.md`.

You MUST read the authoritative user request first:
`d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md`

Your working directory: `d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r11_1\`

Investigation targets:
1. `portfolio_manager.py`:
   - Inspect the current definition of `classify_fund_asset_class(self, fund_code: str, fund_name: str = "") -> str` (exact line numbers, current logic, fallback logic).
   - How does it handle `fund_name` lookup if empty? Check existing catalogs in `portfolio_manager.py`: `self.holdings`, `CORE_STRATEGY_POOL`, `EXTENDED_FUND_CATALOG`, `SECTOR_FUND_SELECTION`, `resolve_fund_meta`. How are they defined and imported? Verify that `strategy_bridge` is NOT imported at top-level to prevent circular imports.
   - Test the proposed 9 asset class rules against the 9 key test funds:
     161726, 161725, 160418, 013402, 008888, 050025, 005561, 002351, 000216.
     Confirm which category each maps to, and ensure none maps to "其他权益资产".
   - Inspect `PortfolioManager.__init__` and state loading: Where is `self.initial_baseline_snapshot` best initialized? (e.g. `{fund_code: shares}` and `initial_cash`). How are initial holdings loaded (e.g. from file or defaults)?
   - Inspect `pm.total_equity`, `self.holdings`, `self.cash`: How are current holdings and net asset value tracked?
   - Design the exact implementation for `pm.evaluate_rebalance_audit() -> Dict[str, Any]`:
     1) `current_actual_equity`: `self.total_equity`
     2) `shadow_hold_equity`: calculated by taking `self.initial_baseline_snapshot` shares * latest `current_nav` + `initial_cash`
     3) `rebalance_value_add`: `current_actual_equity - shadow_hold_equity`
     4) `saved_penalty_and_buffer_fees`: how to accurately calculate the saved 1.50% penalty on locked (<7 days) lots and 0.50% on C-shares based on current holdings and lots. Check how `HoldingItem` / lots store holding days and fee tiers.
2. Check if any existing unit tests in `tests/` or `AGY2_FundAdvisory/tests/` currently test `classify_fund_asset_class` or `evaluate_rebalance_audit`.
