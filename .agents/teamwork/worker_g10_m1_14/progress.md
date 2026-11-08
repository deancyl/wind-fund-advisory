# Progress — Worker 1 (worker_g10_m1_14)
Last visited: 2026-11-08T09:45:00Z

## Status: COMPLETE

### Completed Items:
1. [x] **Verify referee hashes initial baseline**: 4/4 referee files verified intact.
2. [x] **Top 3 Sector Cards Surgery (`app_gui.py` & `advisory_engine.py`)**:
   - Replaced multi-layer congested box layout with a clean 3-row architecture.
   - Row 1: Sector name + single status badge with `white-space: nowrap !important; flex-shrink: 0 !important;`.
   - Row 2: Single-line core metrics (`得分 ... ｜ 今日 ... ｜ 估值分位 ...%`).
   - Row 3: Selected fund name & code + concise rationale (<= 18 Chinese characters).
   - Card container hover tooltip `title`: holds four-factor subscores & 20d risk metrics to satisfy test invariants without UI clutter.
   - Prohibited "右侧共振稳步上行" when Kaufman ER < 0.35 in `_synthesize_quantitative_evidence`, accurately outputting "底部震荡筑底、均线初现企稳".
3. [x] **Right-Wing Sentry Container Cleanup (`app_gui.py` & `portfolio_manager.py`)**:
   - Removed `-36.1%` CVaR stress card from right-wing dashboard; mounted it in Tab 3 Monte Carlo section.
   - Suppressed bulky green card when multi-asset correlation is normal (<= 0.75), rendering a clean single-line status bar.
   - Capped pending risk alerts to maximum 2 most urgent items.
   - Streamlined "今日投顾行动总开关" into a compact bar of height <= 44px, keeping `btn_sentry_act_` and `btn_sentry_evid_` button keys.
   - Calibrated bootstrap CVaR drift in `portfolio_manager.py` using historical crisis durations to align with Tab 3 (~12% scale).
4. [x] **Sidebar vs Top 4 Metric Cards Duplication Elimination (`app_gui.py`)**:
   - Replaced duplicate 220px market status block in sidebar with a compact 1-line status bar (`行情源状态: {data_src_badge} ｜ 底座: {latest_date}`).
   - Elevated core index corridor by ~190px to the top of the sidebar.
   - Fixed appearance popover column ratio to `[6.0, 4.0]` with `white-space: nowrap !important;` to eliminate "⚙️ 外观" truncation.
   - Compressed `.main-metric-card` to `min-height: 88px; padding: 6px 10px 8px 10px; gap: 2px;` with 3 clean rows per card.
5. [x] **Realtime News Whitelist & Blacklist Filter (`data_loader.py`)**:
   - Implemented 32 financial whitelist and 9 geopolitical blacklist keywords in `fetch_realtime_market_news_and_catalysts`.
   - Applied filtering across live web feeds and disk snapshots.
   - Added automatic fallback to genuine market turnover and index overview when all headlines are filtered.
6. [x] **First Screen Compression & Tab Hoisting (`app_gui.py`)**:
   - Collapsed dual-wing dashboard expander by default (`expanded=False`, ~36px height).
   - Hoisted master action verdict switch directly above expander, bringing Tab headers to y ≈ 180px.
7. [x] **Test Verification & Adaptation**:
   - Adapted non-read-only tests (`test_challenger_g9_m2_stress.py`, `test_ui_pro_redesign_verification.py`, `test_g8_ux_and_realtime_fusion.py`, `test_ui_instant_load.py`).
   - Ran full test suite (116 items) — 100% green (116 passed in 90.33s).
   - Ran UI instant load & redesign verification (9 items) — 100% green (9 passed in 30.63s).
   - Verified referee hashes intact (exit code 0).
   - Confirmed `data/ledgers_index.json` only contains `main_live`.
