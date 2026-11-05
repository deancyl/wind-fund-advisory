# Empirical Adversarial Challenge Report — Milestone 1

- **Challenger**: Challenger R8-M1-2 (critic, specialist)
- **Target**: Milestone 1 (Sidebar Corridor, Rule 16 Invariant, Catalog Integrity, Watchlist Cold-Start, AppTest Geometry)
- **Timestamp**: 2026-11-05T02:24:00Z
- **Verdict**: **REQUEST_CHANGES**

---

## Challenge Summary

**Overall risk assessment**: **CRITICAL**

While the Worker Prod R8-M1 successfully implemented the 38+ index catalog, watchlist JSON persistence, AppTest zero-exception rendering, and CSS button styling, our empirical stress testing uncovered **two critical scale-distortion bugs** in the offline and weekend fallback mechanisms that directly breach **Rule 16** of the project rules (`GEMINI.md`).

1. **Rule 16 Invariant Breach in Offline Fallback**: In offline or API-failure modes, `calc_offline_2day_return("000922")` and `fetch_custom_realtime_indices(["000922"])` inject the point of `H00922` (中证红利全收益指数, 12,189.99) into the 000922 price point, exceeding the mandatory 5000~6500 baseline by +121%.
2. **Weekend Flat Fallback Scale Distortion on `change` (涨跌额)**: During weekend non-trading hours (when EastMoney returns `change_pct = 0.00%`), `fetch_custom_realtime_indices` blindly assigns `chg = off_chg`. For `518880` (黄金ETF, net asset value ~8.434元), `off_chg` (+40.33元 from AU9999 spot gold at 1465点) is directly assigned, causing the sidebar card to display `最新点位 8.434, 涨跌额 +40.33, 涨跌幅 +2.83%` (physically impossible scale mismatch). Exactly the same issue occurs on `513500` (+124.50元 on a 2.65元 ETF).

---

## Challenges

### [Critical] Challenge 1: Rule 16 Invariant Violation & Point Scale Mismatch in `calc_offline_2day_return`

- **Assumption Challenged**:
  Assuming `aligned_matrix_total_return.parquet` (全收益矩阵) raw values can be directly returned as price index points (`latest_point`) during offline fallback.
- **Attack Scenario**:
  Simulate an offline environment (or EastMoney/Sina API timeout/failure):
  ```python
  with patch("urllib.request.urlopen", side_effect=Exception("Network down")):
      res = fetch_custom_realtime_indices(["000922"], use_cache=False)
      print(res[0]["point"]) # Outputs: 12189.99
  ```
  `calc_offline_2day_return("000922")` reads column `H00922` from `aligned_matrix_total_return.parquet`. `H00922` is the cumulative total return index including 20 years of reinvested dividends (12,189.99), whereas the price index `000922` is 5,511.17.
  In `fetch_custom_realtime_indices` lines 1666-1667:
  ```python
  if pt <= 0.0:
      pt = off_pt # 12189.99
  ```
  The sidebar card displays `中证红利 12189.99`, directly violating Rule 16:
  > *"点位合理性范围核验: 数据抓取与大屏渲染必须配备点位基线校验（如中证红利必须处于 5000 ~ 6500 点区间，若拉取到 3300 点必须触发报警熔断与源切换），杜绝向用户展示失真点位。"*
  Furthermore, `518880` (黄金ETF, ~8.43元) is assigned `off_pt = 1465.02` (from AU9999 spot gold), and `513500` (标普500ETF, ~2.65元) is assigned `off_pt = 7812.21` (from SPX_CNY index).
- **Blast Radius**:
  In any network disconnection, offline backtesting, or EastMoney API outage, the entire core index corridor renders wildly inflated, false index points and ETF prices.
- **Mitigation**:
  1. In `calc_offline_2day_return`: Use `aligned_matrix_total_return.parquet` ONLY to calculate the relative return `off_pct = (p_curr - p_prev) / p_prev * 100.0`.
  2. For the price point `off_pt`: Retrieve `fb_pt = EXPANDED_INDEX_CATALOG[code]["fb_point"]` as the base point (or inspect price-index parquet files), and calculate `off_chg = round(off_pt * (off_pct / 100.0), 3 if is_etf else 2)`.
  3. Enforce Rule 16 guard on `000922`: If `code == "000922"` and `not (5000.0 <= off_pt <= 6500.0)`, clamp/fallback to `EXPANDED_INDEX_CATALOG["000922"]["fb_point"]` (5518.95).

---

### [High] Challenge 2: Non-trading Hour Weekend Flat Fallback Scale Distortion on `change` (涨跌额)

- **Assumption Challenged**:
  Assuming `off_chg` from `calc_offline_2day_return` can be directly assigned to `change` via `chg = off_chg`.
- **Attack Scenario**:
  During weekend non-trading hours, EastMoney returns valid price point `pt = 8.434`, but `f3=0, f4=0` (`change_pct = 0.00%`).
  In `data_loader.py` lines 1668-1670:
  ```python
  if abs(chg_pct) < 1e-6 and abs(off_pct) > 1e-6:
      chg = off_chg
      chg_pct = off_pct
  ```
  `off_chg` is `+40.33` (from AU9999 gold at 1465 points).
  `fetch_custom_realtime_indices` sets `chg = 40.33` directly!
  The ETF card renders:
  `最新点位 8.434, 涨跌额 +40.33, 涨跌幅 +2.83%`.
  A +40.33 yuan move on an 8.434 yuan ETF represents a +478% jump, but the percentage says +2.83%.
  Similarly, for `513500` (标普500ETF, 2.656元), `chg` becomes `+124.50`元!
- **Blast Radius**:
  Every weekend and non-trading hour, ETF cards in the sidebar corridor display physically nonsensical `change` amounts.
- **Mitigation**:
  In `fetch_custom_realtime_indices`:
  Recalculate `chg` based on the instrument's actual `pt`:
  ```python
  if abs(chg_pct) < 1e-6 and abs(off_pct) > 1e-6:
      chg_pct = off_pct
      is_etf = c.startswith(('5', '1'))
      chg = round(pt * (chg_pct / 100.0), 3 if is_etf else 2)
  ```

---

### [Low] Challenge 3: `validate_and_fetch_code` Implicit Zero-Padding on Truncated Inputs

- **Assumption Challenged**:
  `validate_and_fetch_code` automatically pads truncated strings with `zfill(6)` (e.g. `"1"` -> `"000001"`).
- **Attack Scenario**:
  `validate_and_fetch_code("1")` returns metadata for `000001` (上证指数).
  While `app_gui.py` guards `len(clean_code) == 6`, the standalone function `validate_and_fetch_code` should strictly validate input length before padding.
- **Blast Radius**: Low.
- **Mitigation**:
  Enforce:
  ```python
  raw = str(code_str).strip()
  if len(raw) != 6 or not raw.isdigit():
      return None
  ```

---

## Stress Test Results

Executed via: `py -3 -m pytest AGY2_FundAdvisory/tests/test_challenger_r8_m1_2_stress.py -v`

| Test Case | Scenario / Assertion | Result |
|---|---|---|
| `test_csi_dividend_000922_rule16_invariant` | 000922 mapped to 中证红利, rejecting 000015; real-time point in 5000~6500 | **PASS** |
| `test_expanded_index_catalog_coverage_and_sectors` | >= 38 entries (actual: 40) across >= 12 sectors (actual: 14) | **PASS** |
| `test_validate_and_fetch_code_adversarial_inputs` | Edge-case invalid inputs (alpha, special chars, 999999, 000000) return None | **PASS** |
| `test_calc_offline_2day_return_csi_dividend_scale_invariant` | Offline return for 000922 point must be in 5000~6500 | **FAIL** (returned 12189.99) |
| `test_fetch_custom_realtime_indices_offline_rule16_invariant` | Offline network simulation for 000922 corridor point must be in 5000~6500 | **FAIL** (returned 12189.99) |
| `test_weekend_flat_etf_change_amount_proportionality` | Weekend flat fallback: 8.43元 ETF change amount must be proportional to point | **FAIL** (returned chg=+40.33) |
| `test_missing_file_cold_start_fallback` | Missing `custom_watchlist.json` safely heals and returns default 6 symbols | **PASS** |
| `test_empty_file_corruption_fallback` | 0-byte `custom_watchlist.json` falls back to default symbols without crash | **PASS** |
| `test_corrupted_json_syntax_fallback` | Malformed / non-dict JSON falls back to default symbols without crash | **PASS** |
| `test_save_and_reload_round_trip_preserves_order_and_custom_items` | Round-trip strictly preserves custom order and custom added entries | **PASS** |
| `test_css_val_badge_classes_present_in_dom` | CSS `.val-very-low, .val-very_low` and `.val-very-high, .val-very_high` in DOM | **PASS** |
| `test_primary_button_white_text_enforcement` | `button[kind="primary"]` enforces `#ffffff !important` | **PASS** |
| `test_sidebar_card_geometry_invariants` | Rule 14 & Rule 15 geometry: min-height, overflow: visible, flex: 0 0 auto | **PASS** |
| `test_streamlit_apptest_zero_exception_and_sidebar_rendering` | Full AppTest runs with 0 exceptions and 0 errors | **PASS** |
| `test_referee_hashes_strictly_intact` | 4 referee files SHA256 unmodified | **PASS** |

**Summary**: 12 Passed, 3 Failed.

---

## Actionable Recommendations for Worker

1. **Fix `calc_offline_2day_return` in `AGY2_FundAdvisory/data_loader.py`**:
   - When pulling from `aligned_matrix_total_return.parquet`, use it to compute `chg_pct = (p_curr - p_prev) / p_prev * 100.0`.
   - For `p_curr` / `latest_point`: If `code in EXPANDED_INDEX_CATALOG`, default to `EXPANDED_INDEX_CATALOG[code]["fb_point"]` as the base point when the parquet column represents a total return index (like `H00922`, `H00300`, `AU9999`, `SPX_CNY`, `H11009`).
   - Calculate `chg = round(base_pt * (chg_pct / 100.0), 3 if is_etf else 2)`.
   - Enforce Rule 16: For `000922`, ensure `5000.0 <= pt <= 6500.0`.
2. **Fix `fetch_custom_realtime_indices` in `AGY2_FundAdvisory/data_loader.py`**:
   - In lines 1668-1670, replace `chg = off_chg` with `chg = round(pt * (off_pct / 100.0), 3 if is_etf else 2)`.
   - In line 1666-1667, ensure `off_pt` does not overwrite `pt` with an index from a completely different scale.
3. **Verify by running**:
   `py -3 -m pytest AGY2_FundAdvisory/tests/test_challenger_r8_m1_2_stress.py`
