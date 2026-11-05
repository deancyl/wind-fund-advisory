# Milestone 2 Adversarial Challenge Report

**Target**: Milestone 2 (Features 7, 8, 9, 10) Single Source of Truth & Thermometer Data Sanity
**Tester**: Challenger R8-M2-1 (critic, specialist)
**Date**: 2026-11-05
**Verdict**: **APPROVE**

---

## Challenge Summary

**Overall risk assessment**: **LOW**

The implementation of Milestone 2 (Single Source of Truth, Parquet Dynamic Metrics, Left Wing Opportunity Radar & Pulse Brief, Right Wing 6D Risk Sentry, and Interactive Action Buttons) was rigorously subjected to empirical adversarial testing across 6 test suites and 16 individual stress tests, in addition to existing regressions. All tests passed with zero failures and zero unhandled exceptions.

---

## Challenges & Stress Scenarios

### [Low] Challenge 1: Single Source of Truth & Benchmark Discrepancy
- **Assumption challenged**: The opportunity radar and sidebar corridor might diverge due to caching differences, different symbol keys, or stale fallbacks (especially for CSI Dividend `000922`, which previously had hardcoded `base_val_pct: 25.0` in `RADAR_SECTOR_CATALOG`).
- **Attack scenario**:
  - Compare `OpportunityRadarEngine.evaluate_sector` vs `IndexValuationEngine.fetch_or_calc_index_valuations` across all 14 sectors.
  - Stress test whether any sector benchmark in `val_map` has `abs(radar_val_pct - corridor_val_pct) >= 1e-4`.
  - Target CSI Dividend (`000922`): verify if old `25.0%` fake constant persists or if it correctly returns the overheated corridor value.
- **Empirical Findings**:
  - `RADAR_SECTOR_CATALOG` has been completely purged of static fake constants (`base_val_pct`, `er_20`, `bias_20`, `slope_20`, `crowding_score`).
  - Parity is exact (`diff == 0.000000 < 1e-4`) across all overlapping sectors (e.g., `000978/H30269` 87.9%, `000922` 91.3%, `000300` 66.7%, `000905` 64.2%, `000852` 50.0%, `000688` 68.0%, `513500` 72.0%).
  - CSI Dividend (`000922`) returns `91.3%` in both sidebar and radar, firmly in the realistic overheat zone (>85%), completely rejecting the old fake `25.0%`.
- **Status**: PASSED.

---

### [Low] Challenge 2: Parquet Matrix Dynamic Calculations & Fallback Degradation
- **Assumption challenged**: Dynamic metric calculations might raise exceptions if columns are missing or if the matrix file is moved; or they might produce NaN, infinite values, or out-of-bound Kaufman ER ($ER \notin [0, 1]$).
- **Attack scenario**:
  - Verify that `_calc_dynamic_sector_metrics` locates `data/processed/aligned_matrix_total_return.parquet`.
  - Stress test numerical validity of ER20, Bias20, Slope20, and Crowding Score across all 14 sectors.
  - Test engine resilience against corrupted/malformed cache files (`index_valuation.json`).
- **Empirical Findings**:
  - All 14 sectors have valid numeric metrics.
  - Kaufman ER20 values range from $0.10$ to $0.66$, strictly satisfying $0.0 \le ER \le 1.0$.
  - Bias20 and Slope20 reflect true price time-series behavior without NaN.
  - Engine handles corrupted cache JSON files gracefully without unhandled exceptions.
- **Status**: PASSED.

---

### [Low] Challenge 3: Morning Market Pulse Word Count Invariant
- **Assumption challenged**: Long sector names, extreme turnover values (e.g. `999999999999999万亿元`), or edge-case ERP values might inflate the morning market pulse brief beyond the UI budget of 80 Chinese characters.
- **Attack scenario**:
  - Test 5 adversarial cases: normal turnover/ERP, ultra-long sector names ("超级超长赛道名称测试..."), depressed turnover with near-zero ERP, zero turnover/market closed, and astronomical turnover with 100% ERP.
- **Empirical Findings**:
  - All generated briefs strictly respect `len(pulse_brief) <= 80` (lengths observed: 64, 80, 62, 54, 79 chars).
  - Truncation logic cleanly clips at index 79 and appends a Chinese full-stop (`。`), guaranteeing character count bounded by 80.
- **Status**: PASSED.

---

### [Low] Challenge 4: 6-Dimensional Risk Sentry Coverage & Clean Portfolio False Positives
- **Assumption challenged**:
  - Risk sentry might fail to detect specific demo portfolio risks (`011612`, `011613`, `013841`).
  - False positive risk alerts might fire on clean, mature, diversified portfolios.
- **Attack scenario**:
  - Evaluate demo portfolio: check that `011612` (holding 3 days, min_days < 7), `011613` (holding 28 days, C-class countdown), and `013841` (floating loss -16.2%) are triggered with proper action keys.
  - Evaluate clean portfolio: mature A-class funds (>180 days, low gain, diverse sectors).
  - Evaluate empty portfolio (`{}`).
- **Empirical Findings**:
  - Demo portfolio flags `011612`, `011613`, and `013841` accurately with corresponding interactive actions (`lock_shares`, `countdown_hold`, `deep_loss_rebalance`).
  - Clean portfolio yields `all_passed: True` with 0 alerts.
  - Empty portfolio yields `all_passed: True` with 0 alerts.
- **Status**: PASSED.

---

### [Low] Challenge 5: Streamlit AppTest Runtime Integrity
- **Assumption challenged**: Dual-wing expander, morning pulse brief, 14-sector thermometer dataframe, and interactive buttons might throw runtime DOM or state exceptions under Streamlit `AppTest`.
- **Attack scenario**:
  - Execute full Streamlit `AppTest.from_file(gui_path).run()`.
  - Assert `not at.exception`.
  - Confirm presence of `🔭 全市场机会雷达` and `📊 查看全市场 14 大赛道量化温度计总表`.
- **Empirical Findings**:
  - AppTest executed across all tabs with 0 exceptions.
  - Both expanders are present and active in the component tree.
- **Status**: PASSED.

---

## Stress Test Results

| Test ID | Test Target | Scenario | Expected | Actual | Result |
|---|---|---|---|---|---|
| ST-1 | Static Constants Purge | Scan `RADAR_SECTOR_CATALOG` for fake constants | 0 fake constants found | 0 found | **PASS** |
| ST-2 | Valuation Parity | Compare Radar vs Corridor valuation percentiles | Difference < 1e-4 | Diff == 0.000000 | **PASS** |
| ST-3 | CSI Dividend Invariant | Check `000922` valuation in corridor & radar | Identical & >85%, reject 25.0% | 91.3% vs 91.3% | **PASS** |
| ST-4 | Parquet Dynamic Metrics | Calculate 14 sectors dynamic metrics | Valid numeric $0 \le ER \le 1$, no NaN | All 14 valid ($0.10 \le ER \le 0.66$) | **PASS** |
| ST-5 | Scan All Sectors | `OpportunityRadarEngine.scan_all_sectors()` | 14 items, sorted descending | 14 items, sorted | **PASS** |
| ST-6 | Pulse Brief Length | 5 extreme turnover/ERP/sector name cases | Length $\le 80$ Chinese characters | $54 \le \text{len} \le 80$ | **PASS** |
| ST-7 | Risk Sentry Target 011612 | 3-day holding min_days < 7 | Red penalty lock alert | Alert flagged (`lock_shares`) | **PASS** |
| ST-8 | Risk Sentry Target 011613 | 28-day holding C-class | Yellow countdown alert (差2天免赎) | Alert flagged (`countdown_hold`) | **PASS** |
| ST-9 | Risk Sentry Target 013841 | -16.2% floating loss | Deep loss rebalance alert | Alert flagged (`deep_loss_rebalance`) | **PASS** |
| ST-10 | Clean Portfolio Sentry | Mature diversified portfolio | `all_passed: True`, 0 alerts | `all_passed: True`, 0 alerts | **PASS** |
| ST-11 | Empty Portfolio Sentry | Empty `{}` | `all_passed: True`, 0 alerts | `all_passed: True`, 0 alerts | **PASS** |
| ST-12 | Cache Corruption Resilience | Corrupted `index_valuation.json` | Graceful degradation, no crash | Degraded safely, evaluated | **PASS** |
| ST-13 | Streamlit AppTest Runtime | Full GUI render under AppTest | `assert not at.exception` | 0 exceptions, expanders present | **PASS** |
| ST-14 | Referee Hash Integrity | SHA256 check on 4 readonly files | All 4 SHA256 exact match | 4/4 match expected hashes | **PASS** |

---

## Unchallenged Areas
- Quantitative weight optimization algorithms for Milestone 3 (Models 1-7 in `WinRateOptimizer`) were out of scope for Milestone 2 and will be challenged in Milestone 3.
- Real black swan historical slices (2018, 2022, 2024 stress cards) belong to Milestone 3 scope.

---

## Conclusion & Verdict
Milestone 2 implementation is thoroughly verified, robust, mathematically sound, and compliant with all project and workspace rules. **APPROVE**.
