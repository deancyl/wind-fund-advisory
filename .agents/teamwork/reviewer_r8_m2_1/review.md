# Milestone 2 Review Report: Single Source of Truth & Left Wing Opportunity Radar (Features 7, 8)

**Reviewer**: Reviewer R8-M2-1  
**Working Directory**: `d:\Google\Workspace\Wind\.agents\teamwork\reviewer_r8_m2_1\`  
**Target Milestone**: Milestone 2 (Features 7, 8)  
**Date**: 2026-11-05  

---

## Review Summary

**Verdict**: **APPROVE**

Worker `worker_prod_r8_m2` has implemented Features 7 and 8 with high mathematical rigor and architectural clarity:
1. `RADAR_SECTOR_CATALOG` in `AGY2_FundAdvisory/advisory_engine.py` is 100% purged of static hardcoded constants (`base_val_pct`, `er_20`, `bias_20`, `slope_20`, `crowding_score`), preserving only pure metadata.
2. Dynamic metric computation is robustly bound to `data/processed/aligned_matrix_total_return.parquet` (2143 rows, 13 columns) and verified index fallback files, dynamically deriving Kaufman ER20, MA20 Bias, momentum slope, and crowding score for all 14 sectors.
3. Single Source of Truth is strictly implemented: `OpportunityRadarEngine` fetches valuation percentiles directly from `IndexValuationEngine.fetch_or_calc_index_valuations()`. For CSI Dividend (`000922`), both sidebar corridor and radar return identical valuation percentile (`91.3%`, floating difference strictly `0.0 < 1e-4`).
4. Left wing opportunity radar in `app_gui.py` successfully presents:
   - 今日市场脉搏晨报 (Morning Market Pulse Brief): 64 characters (strictly <= 80 characters limit), linking market turnover, ERP percentile zone, and leading opportunity sectors.
   - 14 大赛道量化温度计总表 (Quantitative Thermometer Table in `st.expander`): exactly 8 required columns (`赛道名称`, `估值分位`, `趋势信噪比`, `20日乖离率`, `拥挤度评分`, `综合得分`, `状态标签`, `优选基金`).
5. Zero integrity violations detected: no hardcoded test answers, no dummy facades, no bypassed tasks, no altered referee files. All 4 referee hashes match SHA256 baselines.

---

## Verified Claims

| # | Claim | Verification Method | Result |
|---|---|---|---|
| 1 | `RADAR_SECTOR_CATALOG` contains 0 hardcoded constants | Programmatic key audit across all 14 sector dictionaries in `advisory_engine.py` | **PASS** (14/14 metadata-only) |
| 2 | Dynamic calculation from `aligned_matrix_total_return.parquet` | Ran `scripts/verify_m2_radar_review.py` inspecting `radar.dynamic_metrics` | **PASS** (14/14 dynamically computed) |
| 3 | Single Source of Truth valuation percentile parity | Compared `val_map['000922']['percentile']` vs `radar.evaluate_sector('csi_dividend', ...)` | **PASS** (both 91.3%, diff = 0.000000) |
| 4 | Rule 16 invariant (CSI Dividend == 000922, never 000015) | AST/Config inspection of `csi_dividend` in `RADAR_SECTOR_CATALOG` | **PASS** (exclusively 000922) |
| 5 | Morning market pulse brief <= 80 characters & links turnover/ERP | Ran format and character count probe on simulated and actual pulse briefs | **PASS** (64 chars, <=80 limit, defensive slice) |
| 6 | 14-sector thermometer table in expander with 8 columns | Inspected `app_gui.py:1820-1838` and verified DataFrame columns in test | **PASS** (14 rows, 8 columns) |
| 7 | Readonly referee files unaltered | `py -3 scripts/verify_referee_hashes.py` | **PASS** (all 4 files SHA256 verified) |
| 8 | Unit tests for M3 advisory modules pass | `py -3 -m pytest AGY2_FundAdvisory/tests/test_m3_advisory_modules.py` | **PASS** (11/11 passed in 1.59s) |
| 9 | Streamlit AppTest integration passes with 0 exceptions | `py -3 -m pytest AGY2_FundAdvisory/tests/test_m3_full_integration_apptest.py` | **PASS** (3/3 passed in 8.91s) |
| 10| Sidebar and regression tests pass | `py -3 -m pytest AGY2_FundAdvisory/tests/test_sidebar_remodel_and_bugfixes.py` | **PASS** (6/6 passed in 11.89s) |

---

## Adversarial Stress Testing Results

We executed `scripts/stress_test_m2_adversarial.py` to challenge edge cases and failure modes:
1. **Extreme Market Volatility**:
   - Ultra Bubble (`Bias20 = +45%`, `Slope = +150%`, `Crowd = 96.0`): Total score 55.4, bounded in [0, 100], 0 NaN, 0 Inf. Anti-overbought penalty activated correctly.
   - Deep Crash (`Bias20 = -45%`, `Slope = -200%`, `Crowd = 45.0`): Total score 26.7, bounded in [0, 100], 0 NaN, 0 Inf.
   - Zero ER Noise (`ER = 0.0`, `Slope = 0.0`): Total score 32.5, bounded in [0, 100], 0 division-by-zero errors.
   - Max Slope (`Slope = +1000.0`, `Bias20 = +5.0%`): Total score 78.5, bounded in [0, 100], 0 overflow errors.
2. **Missing / Empty Metadata Resilience**:
   - Empty metadata dictionary `{"name": "空赛道"}` evaluated safely with score 72.1, 0 crash.
   - Mocked complete failure of `IndexValuationEngine` (empty dict): fallback logic seamlessly activated default neutral percentiles (`pure_bond` = 40.0, `domestic_gold` = 50.0).
3. **Adversarial Pulse Brief Truncation**:
   - Injected 120-character text with extreme turnover numbers and ultra-long sector names: code sliced to exact 79 chars + period (`pulse_brief[:79] + "。"`), guaranteeing <= 80 characters under any circumstances.

---

## Findings

No critical or major findings were discovered. Code quality conforms to all project conventions and `GEMINI.md` rules.

- **Minor Observation**:
  - In `app_gui.py:1754-1758`, `erp_pct` is formatted with `.1f` while `sec['val_percentile']` in Top 3 cards is formatted with `.0f`. This is completely acceptable and common in UI card design to save visual space on compact badges.

---

## Conclusion
The implementation of Milestone 2 (Features 7 and 8) is thorough, robust, and verified.
Verdict is **APPROVE**.
