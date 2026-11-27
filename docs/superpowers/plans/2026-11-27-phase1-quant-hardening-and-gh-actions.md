# AGY2-FundAdvisory Phase 1 Quant Hardening & GitHub Actions Implementation Plan

> **For agentic workers:** Execute task-by-task with strict TDD (failing test -> minimal clean implementation -> green test verification) and end-to-end live verification before claiming completion.

**Goal:** Eliminate all 4 P0 & 4 P1 quantitative integrity defects (fake overseas/gold, lockup funds, pseudo-OOS leakage, 11.7σ kernel mismatch, macro split-brain, stale trading rules, missing short-bond duration shield), expose transparent dual-universe selection (`index_only` default on frontend vs `full_market`) with A/C fee-saving mapping, and ship GitHub Actions daily public market bundle + CI quality gates with domestic proxy-free sync fallback.

**Architecture:** Unify asset classification, lockup/exchange-only exclusion, and index-eligibility into `market_lakehouse.py` as the single source of truth (12 buckets including `short_bond` and `hk_offshore`), clean & top-up the local public lakehouse with open short-bonds and real open global QDII funds, fix strict 70/30 OOS isolation in `portfolio_optimizer.py` + multi-cutoff Walk-Forward OOS in `goal_driven_selector.py`, align historical macro features in `winrate_engine.py`, enforce bear-regime damping & zero hardcoded breadth in `advisory_engine.py`, wire quota/A-C hints & forward-audit auto-logging in `api_server.py`, add zero-clutter universe trade-off hints in React, and ship reproducible `scripts/build_daily_public_bundle.py`, `remote_bundle_sync.py`, and `.github/workflows/{daily-market-data,ci-quality-gate}.yml`.

**Tech Stack:** Python 3.11, pandas/numpy/scipy/pyarrow, FastAPI, pytest, React 19 + TypeScript + Tailwind v4 + Vite, GitHub Actions (`ubuntu-latest`, `TZ: Asia/Shanghai`).

**Spec:** [2026-11-27-phase1-quant-hardening-and-gh-actions-design.md](file:///d:/Google/Workspace/Wind/docs/superpowers/specs/2026-11-27-phase1-quant-hardening-and-gh-actions-design.md)

## Global Constraints
- 100% 场外开放式基金：严禁将任何场内 ETF（`51xxxx`/`159xxx`/`56xxxx`/`588xxx` 或 `purchase_status == "场内交易"`）选入买单。
- 严禁修改四大只读裁判文件：`judge_engine.py`、`holdout_vault.py`、`AGENT_SPEC.md`、`tests/test_infra.py` 以及 `DataLoader.simulate_execution` 默认签名。
- 严禁修改全局 `c:\Users\deanc\.gemini\GEMINI.md`。
- 公开种子与云端数据包严格零个人隐私（仅白名单 6~9 个纯公开市场文件）。
- 前端零布局混乱：不得新增主 Tab 或大块文字墙，保持左侧参数台紧凑高度。

## Review Focus
1. **Fake overseas / fake gold / China-Internet leakage**: Funds named `标普中国A股红利` (`008163`/`501029`), `中概/海外中国互联` (`006327`/`164906`), `工业有色金属` (`017192`/`016707`), `抗通胀油气FOF` (`161815`), or `美国REIT` (`160140`) must NEVER land in `overseas_qdii` or `commodity_gold`.
2. **All-weather overseas graceful degradation under large capital (`¥200,000+`)**: When OTC overseas passive funds fail the 10-day purchase-limit rule in `index_only`, `solve_goal_driven_portfolio` must gracefully relax with an explicit split-buy warning (or re-anchor to gold/HK/bond if all suspended) and NEVER raise or return empty weights.
3. **True OOS invariance under validation perturbation**: Mutating `val_nav` (tail 30%) in `WinRateOptimizer.optimize()` must produce IDENTICAL `optimal_weights` (bit-for-bit / `<1e-9` diff), proving zero look-ahead leakage.
4. **Macro kernel dimension alignment**: Passing a pure-bond NAV series (`006210`) vs an equity NAV series (`110020`) with `DatetimeIndex` into `compute_historical_feature_matrix` must yield identical aligned macro feature vectors (`|z|` mean `< 2.5`), eliminating the `-11.68σ` distortion.
5. **Existing backward compatibility**: Backend API default `universe_mode` remains `"full_market"`, `compute_ten_dimension_votes` preserves `suggested_equity_ratio == base_equity/100 + equity_tilt_pct` (passing `test_g17`), and all existing tests continue to pass.

---

### Task 1: Asset Classification, Lockup/Exchange Ban, Short-Bond/Global Top-Up & Seed Hygiene

**Files:**
- Modify: `AGY2_FundAdvisory/market_lakehouse.py`
- Modify: `AGY2_FundAdvisory/runtime_paths.py`
- Modify: `.gitignore`
- Test: `tests/test_phase1_quant_integrity.py` (create)

**Interfaces:**
- Produces in `market_lakehouse.py`:
  - `BUCKET_10_CONFIG` (extended with `short_bond`, `hk_offshore`, `other_commodity`)
  - `LOCKUP_NAME_PATTERN` (compiled regex covering `后端|定开|定期开放|封闭|持有期|个月持有|天持有|年持有|滚动持有`)
  - `classify_fund_bucket_10(fund_type: str, fund_name: str, fund_code: str = "", purchase_status: str = "") -> str`
  - `is_index_style_fund(fund_type: str, fund_name: str, bucket_10: str, operating_fee: float = 0.6) -> bool`
  - `is_lockup_or_banned_fund(fund_name: str, fund_code: str = "", purchase_status: str = "") -> bool`
  - `reclassify_and_clean_existing_lakehouse(topup_missing_anchors: bool = False) -> Dict[str, Any]`
  - `topup_targeted_lakehouse_funds(extra_codes: Optional[List[str]] = None) -> Dict[str, Any]`
- Produces in `runtime_paths.py`:
  - `PUBLIC_SEED_FILES` includes `"master/fund_catalog.parquet"` and `"master/fund_trading_rules.parquet"`.

- [ ] **Step 1:** Write failing classification, lockup, exchange-only, and seed tests in `tests/test_phase1_quant_integrity.py`.
- [ ] **Step 2:** Run `pytest tests/test_phase1_quant_integrity.py -v` to confirm failure.
- [ ] **Step 3:** Implement upgraded `market_lakehouse.py`, `runtime_paths.py`, and `.gitignore` whitelist; run `reclassify_and_clean_existing_lakehouse` + targeted fast top-up of ~10–12 open `short_bond` and ~6–8 open global QDII funds into `data/processed/market_elite_*`.
- [ ] **Step 4:** Re-run `pytest tests/test_phase1_quant_integrity.py -v` and confirm all classification/lockup/short-bond/gold/overseas invariants PASS.

---

### Task 2: True OOS Non-Leakage, Real Walk-Forward Verification & Macro Kernel Alignment

**Files:**
- Modify: `AGY2_FundAdvisory/winrate_engine.py`
- Modify: `AGY2_FundAdvisory/portfolio_optimizer.py`
- Modify: `AGY2_FundAdvisory/goal_driven_selector.py`
- Test: `tests/test_phase1_quant_integrity.py`

**Interfaces:**
- Produces in `winrate_engine.py`:
  - `load_aligned_macro_feature_frame() -> Optional[pd.DataFrame]`
  - `compute_historical_feature_matrix(nav_series: pd.Series, holding_days: int) -> np.ndarray` (macro-aligned when `DatetimeIndex` overlaps matrix; returns 4D/5D compatible aligned features without fake `2 * fund_bias20`)
- Produces in `portfolio_optimizer.py`:
  - `WinRateOptimizer.optimize()` strictly fits `_precompute_individual_metrics`, `_select_diverse_candidates`, and `_optimize_fixed_n` on `train_nav` (70%), evaluating blind `oos_win_rate` on `val_nav` (30%).
  - `apply_asset_class_constitutional_limits(...)` enforces `bond_min >= tier_bond_min * 0.6` and `hk_offshore <= 0.15`.
- Produces in `goal_driven_selector.py`:
  - `classify_style_cluster(code: str, meta: Dict[str, Any]) -> str`
  - `solve_goal_driven_portfolio(..., investment_amount: float = 50000.0)` with:
    * live `fund_trading_rules.parquet` merge (suspension removal + `>10d` quota hard-filter + two-stage graceful fallback for overseas)
    * single style-cluster cap (`<= 35%` general, `<= 45%` dividend_defense/barbell_growth) & single pure-bond dedup in C3~C5 (`n<=6`) + `short_bond` priority in C1/C2
    * true all-weather 4-asset diversification guard (C2~C4, `n>=4`)
    * `_evaluate_true_walk_forward_oos(...)` real rolling blind OOS & honest `survivorship_bias_disclaimer` in `solver_audit`.

- [ ] **Step 1:** Add failing tests in `tests/test_phase1_quant_integrity.py` for: (a) `val_nav` mutation invariance (zero OOS leakage), (b) macro kernel alignment (`006210` vs `110020`, `|z|<2.5`), (c) 40-combo matrix (`C1~C5 × 4 models × 2 universes`) zero lockup, zero exchange-only, zero suspended, single-cluster caps, and large-capital (`¥200,000`) graceful degradation.
- [ ] **Step 2:** Run pytest to verify failures.
- [ ] **Step 3:** Implement changes in `winrate_engine.py`, `portfolio_optimizer.py`, and `goal_driven_selector.py`.
- [ ] **Step 4:** Re-run pytest and verify all pass + solve latency `<= 3.5s`.

---

### Task 3: Macro Dual-Brain Unity, Zero Hardcoding, A/C Mapping & Forward Audit Auto-Logging

**Files:**
- Modify: `AGY2_FundAdvisory/advisory_engine.py`
- Modify: `AGY2_FundAdvisory/api_server.py`
- Test: `tests/test_phase1_quant_integrity.py`

**Interfaces:**
- Produces in `advisory_engine.py`:
  - `compute_ten_dimension_votes(...)` removes `"16,763 亿"` / `64.5` hardcoded breadth fallback (returns `NEUTRAL` when missing), updates d7 copy to `"反拥挤安全分"`, and applies `BEAR` trend-valuation damping (50% cut, max `+0.08`) directly inside `compute_ten_dimension_votes` while keeping `suggested_equity_ratio == base_equity/100 + equity_tilt_pct`.
- Produces in `api_server.py`:
  - Passes `investment_amount=cap` to `solve_goal_driven_portfolio`
  - Adds `share_class_tip` & `c_share_code` sibling lookup from `fund_catalog.parquet` when `horizon_months <= 12`
  - Removes misleading `"样本外区间"` purple slice on `mode == "model_live"` (uses `"近阶段结构市"`)
  - Calls `forward_audit_logger.record_daily_verdict_if_needed(...)` idempotently in `_warmup_engine_background()` and `/api/v1/lakehouse/sync_daily`
  - Exposes `universe_comparison` metadata + `survivorship_bias_disclaimer` in blueprint response.

- [ ] **Step 1:** Add failing tests for zero hardcoded breadth, `SEVERE_BEAR` damping invariant, `model_live` slice label, `share_class_tip` C-share lookup, and `forward_audit_logger` wiring.
- [ ] **Step 2:** Implement in `advisory_engine.py` and `api_server.py`.
- [ ] **Step 3:** Run `pytest tests/test_phase1_quant_integrity.py tests/test_akshare_compat_and_seed_bootstrap.py` and verify all pass.

---

### Task 4: Frontend Zero-Clutter Dual-Universe Guidance, Realistic Defaults & C-Class Fee Hint

**Files:**
- Modify: `web/src/context/WorkbenchContext.tsx`
- Modify: `web/src/api/client.ts`
- Modify: `web/src/components/MetricTooltip.tsx`
- Modify: `web/src/pages/QuantLabPage.tsx`

**Interfaces:**
- `WorkbenchContext`: defaults `universeMode` to `'index_only'`, default C3 goal to `24` months / `15%` (auto-adjusting pragmatic tier defaults on risk-tier switch unless user manually edited goal).
- `QuantLabPage`: displays compact 2-line pros/cons hint directly under `选基池范围` toggle + `MetricTooltip` (`specKey="universe_mode"`), shows `share_class_tip` C-share badge cleanly inside the existing `限购与费率` column when `horizonMonths <= 12`, and updates `oos_winrate` tooltip copy to reflect true Walk-Forward blind OOS.

- [ ] **Step 1:** Update `client.ts`, `WorkbenchContext.tsx`, `MetricTooltip.tsx`, and `QuantLabPage.tsx`.
- [ ] **Step 2:** Run `cd web && npm run build` and verify 0 TypeScript / Vite errors.

---

### Task 5: GitHub Actions Daily Public Data Pipeline, CI Gate & Domestic Proxy-Free Sync

**Files:**
- Create: `AGY2_FundAdvisory/remote_bundle_sync.py`
- Create: `scripts/build_daily_public_bundle.py`
- Create: `.github/workflows/daily-market-data.yml`
- Create: `.github/workflows/ci-quality-gate.yml`
- Modify: `AGY2_FundAdvisory/api_server.py` (wire `/api/v1/lakehouse/sync_daily` optional bundle pull with domestic fallback)
- Test: `tests/test_phase1_quant_integrity.py`

**Interfaces:**
- `scripts/build_daily_public_bundle.py --output-dir <dir> [--skip-network]` produces:
  - `agy2-market-bundle-latest.tar.gz` (6 whitelisted public market files, 0 user data)
  - `agy2-mobile-compact-v1.tar.gz` (`nav_f32.bin` row-major little-endian IEEE-754 float32 + `bundle_meta.json`)
  - `manifest.json` (`schema_version`, `generated_at`, `latest_trade_date`, `fund_count`, `sha256`, `files`)
- `remote_bundle_sync.sync_public_bundle_with_fallback(...)`: Priority 1 domestic mirror / `AGY2_BUNDLE_URL` (5s timeout) -> Priority 2 GitHub Release `data-latest` (5s timeout) -> Priority 3 direct domestic EastMoney `incremental_daily_sync()`.

- [ ] **Step 1:** Write failing test for bundle generator (privacy whitelist, SHA256 manifest, `nav_f32.bin` exact byte-length & float32 round-trip accuracy) and `remote_bundle_sync` fallback chain.
- [ ] **Step 2:** Implement `remote_bundle_sync.py`, `scripts/build_daily_public_bundle.py`, and both `.github/workflows/*.yml` files (with `TZ: Asia/Shanghai`).
- [ ] **Step 3:** Dry-run `scripts/build_daily_public_bundle.py --skip-network` and run pytest to verify 100% pass.

---

### Task 6: Full Regression Suite, Live Server Restart & End-to-End Verification

- [ ] Run full Phase 1 integrity suite + existing critical regression tests (`test_phase1_quant_integrity.py`, `test_akshare_compat_and_seed_bootstrap.py`, `test_infra.py`, `test_g17*` if present).
- [ ] Restart local FastAPI `127.0.0.1:8000` serving updated backend + freshly built `web/dist`, probe live `/api/v1/overview`, `/api/v1/quant/solve`, `/api/v1/recommend/blueprint`, `/api/v1/charts/backtest_curves`, `/api/v1/lakehouse/status`, and visually inspect the live default view via browser subagent to confirm zero fake overseas/gold, zero lockup, honest Walk-Forward OOS, and crisp zero-clutter layout!
