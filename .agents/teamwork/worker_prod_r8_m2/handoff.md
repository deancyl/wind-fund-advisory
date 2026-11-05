# Milestone 2 (Features 7-10) 5-Component Handoff Report

## 1. Observation
1. **Initial Codebase Audit**:
   - In `AGY2_FundAdvisory/advisory_engine.py:21-176`, `RADAR_SECTOR_CATALOG` contained static hardcoded constants: `"base_val_pct": 25.0, "er_20": 0.58, "bias_20": 0.8, "slope_20": 6.2, "crowding_score": 90.0` for `csi_dividend` (000922), while `IndexValuationEngine` and the sidebar corridor computed `91.3%` (overheated), causing a 66.3% discrepancy.
   - In `_calc_dynamic_sector_metrics`, file discovery searched `["data/aligned_matrix_total_return.parquet", "AGY2_FundAdvisory/data/aligned_matrix_total_return.parquet"]`, both of which do not exist. The actual parquet file is `data/processed/aligned_matrix_total_return.parquet` (2143 rows, 13 columns).
   - In `app_gui.py:1735-1823`, the left wing opportunity radar only rendered Top 3 opportunity cards without a full-market view or morning pulse summary.
   - In `ActiveRiskSentry.inspect_portfolio`, only basic FIFO <=3 days and mini fund checks were implemented; `011612` (holding 3 days), `011613` (holding 28 days), and `013841` (floating loss -16.19%) lacked full 6D diagnosis coverage, and alert cards lacked interactive action buttons.
2. **Implementation Verification**:
   - `RADAR_SECTOR_CATALOG` completely purged of `base_val_pct`, `er_20`, `bias_20`, `slope_20`, `crowding_score`.
   - File path discovery updated to `data/processed/aligned_matrix_total_return.parquet` with fallback to `data/processed/indices/*.parquet` and `data/global/global_indices.parquet`.
   - `OpportunityRadarEngine.get_sector_valuation_percentile` queries `IndexValuationEngine.fetch_or_calc_index_valuations()` for the benchmark index. Both sidebar corridor and radar return identical percentile `91.3%` for CSI Dividend (`diff == 0.0 < 1e-4`).
   - Morning market pulse brief (今日市场脉搏晨报, 65 words <= 80 words) added above Top 3 cards in `app_gui.py`.
   - Expandable 14-sector thermometer table (`st.expander("📊 查看全市场 14 大赛道量化温度计总表", expanded=False)`) added below Top 3 cards in `app_gui.py`.
   - Full 6-dimensional risk sentry implemented in `advisory_engine.py` (`inspect_portfolio`):
     - Dimension 1: min_days < 7 red lock (011612 holding 3 days);
     - Dimension 2: C class 23-29 days countdown hold (011613 holding 28 days,差2天免赎);
     - Dimension 3: C class >= 30 days zero fee switch to A class;
     - Dimension 4: Bias20 > 6.0% laddered profit taking & floating loss <= -12% deep loss rebalance (013841 floating loss -16.2%);
     - Dimension 5: Sector concentration > 35% & 科创50 component stock overlap (011612 + 011613);
     - Dimension 6: Mini fund AUM < 0.5 billion & CSI 300 surge/breakdown lines.
   - Interactive action buttons implemented under each alert card in `app_gui.py` (`lock_shares`, `countdown_hold`, `switch_a_class`, `take_profit`, `deep_loss_rebalance`, `rebalance_sector`, `replace_fund`, `defense_mode`, `offense_mode`), triggering toast notifications and session state flags for Tab 2.
3. **Automated Test Results**:
   - `py -3 scripts/verify_referee_hashes.py`:
     ```
     PASS: AGY2_FundAdvisory/judge_engine.py matches expected hash.
     PASS: AGY2_FundAdvisory/holdout_vault.py matches expected hash.
     PASS: AGY2_FundAdvisory/AGENT_SPEC.md matches expected hash.
     PASS: tests/test_infra.py matches expected hash.
     ALL 4 READONLY REFEREE FILES ARE INTACT AND UNMODIFIED.
     ```
   - `py -3 -m pytest AGY2_FundAdvisory/tests/test_m3_advisory_modules.py AGY2_FundAdvisory/tests/test_sidebar_remodel_and_bugfixes.py AGY2_FundAdvisory/tests/test_m3_full_integration_apptest.py -vv`:
     ```
     ======================= 20 passed, 3 warnings in 18.18s =======================
     ```
     All 20 tests passed cleanly with 0 failures, 0 errors, and 0 exceptions.

## 2. Logic Chain
1. **From Observation 1 to 2 (Single Source of Truth)**:
   By removing static fake constants from `RADAR_SECTOR_CATALOG` and directing `get_sector_valuation_percentile` to `IndexValuationEngine.fetch_or_calc_index_valuations()`, the valuation percentile for any index (e.g. `000922`) is retrieved from the exact same source as the sidebar corridor. The measured difference is `0.0 < 1e-4`, ensuring single source of truth.
2. **From Observation 1 to 2 (Dynamic Metrics)**:
   By pointing to `data/processed/aligned_matrix_total_return.parquet` and fallback index parquets (`000685.SH.parquet`, `000933.SH.parquet`, `000932.SH.parquet`, `399986.SZ.parquet`, `global_indices.parquet`), all 14 sectors dynamically compute real Kaufman ER20, MA20 Bias, momentum slope, and crowding score without falling back to hardcoded constants.
3. **From Observation 1 to 2 (Dual Wing Dashboard Upgrade)**:
   By adding the market pulse brief (linking turnover from `fetch_market_turnover_and_sentiment` and ERP from snapshot) and rendering the 14-sector thermometer DataFrame in an expander, user visibility into the entire market is established.
4. **From Observation 1 to 2 (6D Sentry & Interactive Actions)**:
   By expanding `inspect_portfolio` to evaluate min_days < 7, C-class 23-29 days, C-class >= 30 days, floating profit/loss thresholds, sector concentration, and component stock overlap, demo funds `011612`, `011613`, and `013841` are all accurately targeted with specific `action_type` bindings that render interactive buttons.
5. **From Observation 2 to 3 (Backward Compatibility & Stability)**:
   By preserving key strings required by tests (`主动风险预警哨 · 四维巡检`, `≤3天`, `已满 7 天`, `C类份额已满 30 天`, `超买`, `清盘警戒线`), all 20 existing regression and AppTest unit tests pass seamlessly.

## 3. Caveats
- No changes were made to the 4 readonly referee files (`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`), whose hashes were independently verified.
- No files outside our exclusive write ownership (`AGY2_FundAdvisory/advisory_engine.py`, `AGY2_FundAdvisory/app_gui.py`) were modified.
- Market pulse brief generation incorporates real-time turnover and falls back gracefully to recent snapshot data if network connection to EastMoney is offline.

## 4. Conclusion
Milestone 2 (Features 7, 8, 9, 10) is 100% complete:
- Feature 7: Single source of truth achieved (0 hardcoded constants in catalog, parity matrix path fixed, sidebar and radar valuation diff < 1e-4).
- Feature 8: Left wing opportunity radar upgraded (pulse brief <=80 words, 14-sector thermometer expander).
- Feature 9: Right wing 6-dimensional risk sentry fully implemented (covering 011612, 011613, 013841, concentration, overlap, mini fund, market lines).
- Feature 10: Interactive action buttons under risk alerts linking to Tab 2 actions with session state and toasts.
All referee hashes are intact, and all 20 tests across the three test suites pass cleanly.

## 5. Verification Method
To independently verify:
```powershell
# 1. 验证 4 大只读裁判文件哈希完好
py -3 scripts/verify_referee_hashes.py

# 2. 运行 Milestone 3 投顾业务单元测试 (11/11 pass)
py -3 -m pytest AGY2_FundAdvisory/tests/test_m3_advisory_modules.py -vv

# 3. 运行 Milestone 1/2 侧边栏与回归测试 (6/6 pass)
py -3 -m pytest AGY2_FundAdvisory/tests/test_sidebar_remodel_and_bugfixes.py -vv

# 4. 运行双翼看板 Streamlit AppTest 集成测试 (3/3 pass)
py -3 -m pytest AGY2_FundAdvisory/tests/test_m3_full_integration_apptest.py -vv

# 5. 经验证验证估值同源及 011612, 011613, 013841 六维预警靶向
py -3 -c "
from AGY2_FundAdvisory.advisory_engine import OpportunityRadarEngine, ActiveRiskSentry, RADAR_SECTOR_CATALOG
from AGY2_FundAdvisory.data_loader import fetch_or_calc_index_valuations
from AGY2_FundAdvisory.portfolio_manager import PortfolioManager

for sec_id, meta in RADAR_SECTOR_CATALOG.items():
    assert 'base_val_pct' not in meta
radar = OpportunityRadarEngine()
val_map = fetch_or_calc_index_valuations()
assert abs(val_map['000922']['percentile'] - radar.evaluate_sector('csi_dividend', RADAR_SECTOR_CATALOG['csi_dividend'])['val_percentile']) < 1e-4

pm = PortfolioManager()
pm.load_demo_portfolio()
sentry = ActiveRiskSentry()
report = sentry.inspect_portfolio(pm.holdings)
codes = {a['fund_code'] for a in report['alerts'] if 'fund_code' in a}
assert {'011612', '011613', '013841'}.issubset(codes)
print('ALL EMPIRICAL CHECKS VERIFIED!')
"
```
