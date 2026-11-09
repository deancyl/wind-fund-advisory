# DISPATCH — explorer_g14_survey_1

## Objective
Technical survey of the 4 code bugs in `advisory_engine.py` and `app_gui.py`:
1. `radar_sectors_cache.json` write-read closure:
   - Check where `OpportunityRadarEngine.scan_all_sectors` is defined and how it scans 14 sectors.
   - Design the exact caching mechanism: serialize results to `data/cache/radar_sectors_cache.json` with timestamp (TTL 4 hours).
   - Check how `scan_all_sectors` checks disk cache on entry and returns cached list in milliseconds unless force_refresh=True.
   - Check `app_gui.py` line 1323 (or actual line) where it attempts to read `radar_sectors_cache.json` and ensure seamless integration.
2. 12-dimensional active risk sentry inspection restoration with 1ms cache:
   - Check `app_gui.py` (around lines 1425-1485 or 2956-3011) where `sentry.inspect_portfolio` was removed or replaced by simple `h_days < 7` / `C >= 30` loops.
   - Check `ActiveRiskSentry.inspect_portfolio` in `advisory_engine.py` to see what parameters it expects and what dict it returns.
   - Design the caching mechanism in `render_dual_wing_advisory_dashboard`: calculate `holdings_hash` (fund codes, shares, latest NAV, min holding days, `active_tier_val`), cache in `st.session_state` and `data/portfolio_watchdog.json`.
   - Design the UI rendering: expandable dual-wing header title & right wing list rendering ALL alerts from `sentry_rep["alerts"]`. Only show green all-passed when `sentry_rep["all_passed"]` is True.
   - Restore left-wing single-line market pulse & `news_source_badge` verification badge, plus compact "刷新雷达与风控" button.
3. Fix `get_60d_rolling_nav_and_trajectory` in `advisory_engine.py`:
   - Inspect lines 475 to 505 (or actual lines) where `np.mean(r_day[:3])` is hardcoded.
   - Implement real dynamic selection: for each OOS day d, use history up to d-1 to compute 4-dim feature vector f_vec for 14 sectors, dot product with dynamic `w_opt` and static `self.static_weights` to pick dynamic Top 3 and static Top 3 sectors.
   - Strictly deduct bilateral 20 bps turnover cost (`0.0020 * turnover_ratio`).
   - Regenerate `data/cache/factor_evolution_cache.json`.
4. Clean up pseudo-trading banner:
   - Find lines in `app_gui.py` rendering `latest_plan` ("采纳并执行此待办预案" / "提交在途单") and plan clean removal.

Read `ORIGINAL_REQUEST.md` at `d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md`.
Output detailed analysis and concrete code modification plans in `handoff.md` in your directory.


## 2026-11-09T11:25:34Z
sender=675b287a-9df2-4040-9227-01d56b1552b2 priority=MESSAGE_PRIORITY_HIGH
You are explorer_g14_survey_1, working in directory: d:\Google\Workspace\Wind\.agents\teamwork\explorer_g14_survey_1\
Read your task assignment in d:\Google\Workspace\Wind\.agents\teamwork\explorer_g14_survey_1\DISPATCH.md and d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md.

Investigate the 4 code bugs in advisory_engine.py and app_gui.py:
1. radar_sectors_cache.json write-read closure (OpportunityRadarEngine.scan_all_sectors)
2. 12-dimensional active risk sentry restoration with 1ms cache (holdings_hash, ActiveRiskSentry.inspect_portfolio, alerts rendering, news_source_badge, refresh button)
3. get_60d_rolling_nav_and_trajectory dynamic factor weight selection and 20 bps turnover cost deduction
4. latest_plan pseudo-trading banner removal in app_gui.py

Document exact file paths, line numbers, current implementations, proposed code fixes, and edge cases.
Write your complete report to handoff.md in your working directory and notify the orchestrator with send_message.
