# Milestone 2 Reviewer R8-M2-1 5-Component Handoff Report

## 1. Observation
1. **Catalog Metadata Audit (`AGY2_FundAdvisory/advisory_engine.py:21-219`)**:
   - `RADAR_SECTOR_CATALOG` contains exactly 14 sectors.
   - Programmatic inspection confirmed 100% removal of `base_val_pct`, `er_20`, `bias_20`, `slope_20`, `crowding_score` across all 14 sectors.
   - All entries contain only clean structural metadata (`sector_id`, `name`, `benchmark_index`, `symbol`, `index_code`, `cs_code`, `matrix_col` or `fallback_parquet`, `category`, `top_fund_code`, `top_fund_name`, `default_fund`, `core_logic`).
   - `csi_dividend` is strictly mapped to `benchmark_index: "000922"`, satisfying Rule 16.
2. **Parquet Path Resolution & Dynamic Computation (`AGY2_FundAdvisory/advisory_engine.py:247-323`)**:
   - `mat_path` successfully resolves to `data/processed/aligned_matrix_total_return.parquet` (shape: `2143` rows, `13` columns).
   - Dynamic metrics (`er_20`, `bias_20`, `slope_20`, `crowding_score`) are computed for all 14 sectors from real historical price sequences (e.g., `dividend_low_vol`: `er_20: 0.11`, `bias_20: +0.76%`, `slope_20: +50.77%`, `crowding: 95.6`).
3. **Single Source of Truth Verification (`AGY2_FundAdvisory/advisory_engine.py:325-383`)**:
   - `OpportunityRadarEngine.get_sector_valuation_percentile()` invokes `data_loader.fetch_or_calc_index_valuations(force_refresh=False)`.
   - For `000922` (CSI Dividend), `val_map['000922']['percentile']` returns `91.3%`, and `radar.evaluate_sector('csi_dividend', ...)` returns `91.3%`. Floating point difference is `0.000000 < 1e-4`.
4. **Left Wing Opportunity Radar GUI Presentation (`AGY2_FundAdvisory/app_gui.py:1735-1838`)**:
   - Morning market pulse brief (今日市场脉搏晨报): simulated/live output measured 64 characters (strictly <= 80 characters limit). Defensively guarded by `if len(pulse_brief) > 80: pulse_brief = pulse_brief[:79] + "。"`.
   - Thermometer table: wrapped in `st.expander("📊 查看全市场 14 大赛道量化温度计总表", expanded=False)` with all 8 requested columns (`赛道名称`, `估值分位`, `趋势信噪比`, `20日乖离率`, `拥挤度评分`, `综合得分`, `状态标签`, `优选基金`).
5. **Test Executions**:
   - `py -3 scripts/verify_referee_hashes.py`: Output verbatim:
     ```
     PASS: AGY2_FundAdvisory/judge_engine.py matches expected hash.
     PASS: AGY2_FundAdvisory/holdout_vault.py matches expected hash.
     PASS: AGY2_FundAdvisory/AGENT_SPEC.md matches expected hash.
     PASS: tests/test_infra.py matches expected hash.
     ALL 4 READONLY REFEREE FILES ARE INTACT AND UNMODIFIED.
     ```
   - `py -3 -m pytest AGY2_FundAdvisory/tests/test_m3_advisory_modules.py`: Output verbatim:
     ```
     ============================= 11 passed in 1.59s ==============================
     ```
   - `py -3 -m pytest AGY2_FundAdvisory/tests/test_m3_full_integration_apptest.py`: Output verbatim:
     ```
     ============================== 3 passed in 8.91s ==============================
     ```
   - `py -3 -m pytest AGY2_FundAdvisory/tests/test_sidebar_remodel_and_bugfixes.py`: Output verbatim:
     ```
     ======================= 6 passed, 3 warnings in 11.89s ========================
     ```
   - `py -3 scripts/stress_test_m2_adversarial.py`: Passed all 4 adversarial stress test blocks (extreme shock values, missing data resilience, Rule 16 invariant, long pulse brief truncation).

## 2. Logic Chain
1. **Catalog Integrity & Single Source of Truth**:
   From Observation 1 and 3, `RADAR_SECTOR_CATALOG` contains no static mock values. Because `OpportunityRadarEngine` calls `fetch_or_calc_index_valuations()` and extracts `val_map[c_str]["percentile"]`, any benchmark index (such as `000922`, `000300`, `000905`, `000852`, `000688`) uses the identical calculation pipeline as the sidebar corridor. Therefore, single source of truth is established with 0 discrepancy.
2. **Real Dynamic Computation**:
   From Observation 2, `_calc_dynamic_sector_metrics` locates `data/processed/aligned_matrix_total_return.parquet`. For each sector, it computes Kaufman ER20, MA20 Bias, and momentum slope from actual historical daily closes. No hardcoded or dummy values are used.
3. **UI Conformance**:
   From Observation 4, the morning pulse brief links real-time turnover, ERP status, and leading sectors, fitting within 80 characters. The thermometer table exposes all 14 sectors with 8 complete columns in an expander.
4. **Codebase Safety & Physical Boundary**:
   From Observation 5, all 4 referee files remain bitwise identical to their SHA256 baselines. Full test suite passes without errors or exceptions.

## 3. Caveats
- Non-equity benchmark assets (e.g., pure bond `H11009`, domestic gold `518880`) do not have PE/PB valuation percentiles from equity index valuation APIs; they properly fall back to asset-class neutral percentiles (40.0% and 50.0%) as designed.
- No other caveats.

## 4. Conclusion
Milestone 2 (Features 7, 8) satisfies all acceptance criteria, maintains strict architectural and data integrity, and passes all unit, integration, AppTest, and adversarial stress tests.
**Verdict: APPROVE**.

## 5. Verification Method
To independently verify:
```powershell
# 1. 验证 4 大只读裁判文件哈希基线
py -3 scripts/verify_referee_hashes.py

# 2. 运行投顾业务模块单元测试
py -3 -m pytest AGY2_FundAdvisory/tests/test_m3_advisory_modules.py -vv

# 3. 运行双翼看板 Streamlit AppTest 集成测试
py -3 -m pytest AGY2_FundAdvisory/tests/test_m3_full_integration_apptest.py -vv

# 4. 运行侧边栏与回归测试
py -3 -m pytest AGY2_FundAdvisory/tests/test_sidebar_remodel_and_bugfixes.py -vv

# 5. 运行独立 M2 单源同真与雷达校验脚本
py -3 scripts/verify_m2_radar_review.py

# 6. 运行对抗压力测试脚本
py -3 scripts/stress_test_m2_adversarial.py
```
