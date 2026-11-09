# Progress — explorer_g13_survey_1

Last visited: 2026-11-09T07:08:30Z

## Status
- [x] Initialized DISPATCH.md and BRIEFING.md
- [x] Read ORIGINAL_REQUEST.md and audit markdown files
- [x] Deep code investigation of Pain Point 1: `app_gui.py` and `advisory_engine.py`
  - [x] Identified all 7 heavy synchronous calls in `render_dual_wing_advisory_dashboard`
  - [x] Designed pure in-memory advisory tip bar (<20ms, <1ms actual) using only `snapshot` & `pm.holdings`
  - [x] Designed disk cache `data/cache/factor_evolution_cache.json` (12h TTL) for `OnlineHeuristicFactorEvolver`
  - [x] Verified relocation of 5 nested modules out of expander into Tab 4 and Tab 1
- [x] Deep code investigation of Pain Point 4: `app_gui.py`, `strategy_bridge.py`, parquet benchmarks
  - [x] Located Plotly layout collision, margin `t=75`, `legend` placement `y=1.06`, `bgcolor="rgba(0,0,0,0)"`, and `apply_theme_to_plotly_figure` overwrite root cause
  - [x] Located artificial alpha addition `r_arr[1:] += (alpha_ann / 250.0)` at line 4929 of `strategy_bridge.py`
  - [x] Verified `H11009` daily series in `aligned_matrix_total_return.parquet` (CAGR +4.81%) vs `930609` (CAGR +3.23%)
  - [x] Designed static holding disclaimer card and one-click toggle for OOS dynamic strategy comparison
- [x] Validated test baseline (50 passed in 146s)
- [ ] Write 5-component `handoff.md`
- [ ] Update `BRIEFING.md`
- [ ] Send report to caller agent
