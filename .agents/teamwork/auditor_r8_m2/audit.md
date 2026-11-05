## Forensic Audit Report

**Work Product**: Milestone 2 (`AGY2_FundAdvisory/advisory_engine.py`, `AGY2_FundAdvisory/app_gui.py`)
**Profile**: General Project (Integrity Mode: development per `ORIGINAL_REQUEST.md`)
**Verdict**: CLEAN

### Phase Results
- **Physical Safety Redlines (Referee Hashes)**: PASS — All 4 readonly referee files (`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`) match their expected SHA256 hashes exactly.
- **Hardcoded Fake Constant Purge in Catalog**: PASS — `RADAR_SECTOR_CATALOG` in `advisory_engine.py` was thoroughly verified via AST and programmatic inspection. 0 out of 14 sectors contain `base_val_pct`, `er_20`, `bias_20`, `slope_20`, or `crowding_score`.
- **Dynamic Sector Metrics Authenticity**: PASS — `_calc_dynamic_sector_metrics()` authentically reads `data/processed/aligned_matrix_total_return.parquet` (and fallback index parquets) to compute genuine Kaufman ER20, MA20 Bias, momentum slope, and crowding score across all 14 sectors.
- **Valuation Percentile Single Source of Truth**: PASS — Benchmark valuation percentiles queried by `OpportunityRadarEngine` from `IndexValuationEngine` match sidebar values with `diff == 0.0 < 1e-4` (e.g., CSI Dividend `000922` = 91.3% in both).
- **ActiveRiskSentry 6-Dimensional Logic Authenticity**: PASS — AST and regex analysis confirmed 0 hardcoded test fund code branches (`011612`, `011613`, `013841`) in condition checks. All 6 dimensions operate via generalized quantitative rules (holding days, share class, Bias20, PnL%, sector concentration, AUM, market lines).
- **Facade & Dummy Implementation Detection**: PASS — AST scan of `advisory_engine.py`, `app_gui.py`, and `data_loader.py` detected 0 empty pass functions, 0 dummy constant return stubs, and 0 `NotImplementedError` methods.
- **Pre-populated Artifact Detection**: PASS — No fabricated test result or pre-baked attestation logs found in workspace.
- **Test Integrity & Non-Regression**: PASS — All existing tests in `AGY2_FundAdvisory/tests/` and `tests/` were untouched (0 diff in test suites). 20/20 advisory unit/AppTest tests and 14/14 readonly referee tests executed and passed cleanly.

### Evidence

#### 1. Referee Hash Verification
```
$ py -3 scripts/verify_referee_hashes.py
PASS: AGY2_FundAdvisory/judge_engine.py matches expected hash.
PASS: AGY2_FundAdvisory/holdout_vault.py matches expected hash.
PASS: AGY2_FundAdvisory/AGENT_SPEC.md matches expected hash.
PASS: tests/test_infra.py matches expected hash.
ALL 4 READONLY REFEREE FILES ARE INTACT AND UNMODIFIED.
```

#### 2. RADAR_SECTOR_CATALOG Cleanliness Check
```python
>>> from AGY2_FundAdvisory.advisory_engine import RADAR_SECTOR_CATALOG
>>> banned = ['base_val_pct', 'er_20', 'bias_20', 'slope_20', 'crowding_score']
>>> found = {s: [k for k in banned if k in m] for s, m in RADAR_SECTOR_CATALOG.items() if any(k in m for k in banned)}
>>> print(found)
{}
PASS: RADAR_SECTOR_CATALOG is completely clean of static fake constants.
```

#### 3. Dynamic Sector Metrics Calculation
```
Computed dynamic metrics keys count: 14
  dividend_low_vol: {'er_20': 0.11, 'bias_20': 0.76, 'slope_20': 50.77, 'crowding_score': 95.6}
  csi_dividend: {'er_20': 0.1, 'bias_20': 0.8, 'slope_20': 33.85, 'crowding_score': 95.6}
  csi_300: {'er_20': 0.29, 'bias_20': -0.74, 'slope_20': -106.28, 'crowding_score': 94.8}
  csi_500: {'er_20': 0.27, 'bias_20': -1.93, 'slope_20': -197.8, 'crowding_score': 94.9}
  csi_1000: {'er_20': 0.26, 'bias_20': -2.35, 'slope_20': -201.82, 'crowding_score': 95.0}
  star_50: {'er_20': 0.59, 'bias_20': -12.4, 'slope_20': -361.67, 'crowding_score': 93.7}
  semiconductor: {'er_20': 0.58, 'bias_20': 0.13, 'slope_20': 3.93, 'crowding_score': 93.7}
  pharma_health: {'er_20': 0.1, 'bias_20': 0.49, 'slope_20': -1.07, 'crowding_score': 95.6}
  consumer_liquor: {'er_20': 0.14, 'bias_20': 1.74, 'slope_20': 16.92, 'crowding_score': 95.5}
  banking_dividend: {'er_20': 0.19, 'bias_20': 1.1, 'slope_20': 22.78, 'crowding_score': 95.2}
  domestic_gold: {'er_20': 0.2, 'bias_20': 1.73, 'slope_20': 87.25, 'crowding_score': 95.2}
  us_sp500_nasdaq: {'er_20': 0.21, 'bias_20': -1.09, 'slope_20': -19.29, 'crowding_score': 95.1}
  hstech: {'er_20': 0.21, 'bias_20': -3.47, 'slope_20': -12.79, 'crowding_score': 95.2}
  pure_bond: {'er_20': 0.66, 'bias_20': 0.22, 'slope_20': 6.92, 'crowding_score': 93.3}
```

#### 4. ActiveRiskSentry AST & Regex Inspection
`scripts/audit_m2_sentry_integrity.py` executed AST condition check:
- Pattern matches for fund code equality/membership (`code == '...'` or `code in [...]`): `[]`
- No hardcoded condition checks for test funds `011612`, `011613`, `013841`.

#### 5. Behavioral Execution on Real Demo Portfolio
```
Total alerts generated: 6
  [RED] Dim: 未满7天锁仓 | Fund: 011612 | Action: lock_shares | Title: 【华夏科创50ETF联接A (011612)】持有仅 3 天（≤3天）
  [YELLOW] Dim: 临免赎期倒计时 | Fund: 011613 | Action: countdown_hold | Title: 【华夏上证科创板50成份ETF联接C (011613)】距30天免赎仅差 2 天（当前第 28 天）
  [YELLOW] Dim: C类零费率置换 | Fund: 013841 | Action: switch_a_class | Title: 【银华集成电路混合C (013841)】C类份额已满 30 天（第 40 天）
  [YELLOW] Dim: 深套诊断 | Fund: 013841 | Action: deep_loss_rebalance | Title: 【银华集成电路混合C (013841)】深套诊断预警 (浮亏 -16.2%)
  [YELLOW] Dim: 赛道集中度 | Fund: None | Action: rebalance_sector | Title: 【红利高股息赛道】持仓占比达 60.8% (>35%集中度红线)
  [YELLOW] Dim: 重仓股重叠 | Fund: 011613 | Action: switch_a_class | Title: 【科创50】重仓股高度重叠预警 (011612 与 011613)
Targeted funds check: PASSED!
```

#### 6. Test Suite Runs
- `py -3 -m pytest AGY2_FundAdvisory/tests/test_m3_advisory_modules.py AGY2_FundAdvisory/tests/test_sidebar_remodel_and_bugfixes.py AGY2_FundAdvisory/tests/test_m3_full_integration_apptest.py -vv`:
  `20 passed, 3 warnings in 16.56s`
- `py -3 -m pytest tests/test_infra.py -vv`:
  `14 passed in 7.18s`
- `git diff AGY2_FundAdvisory/tests/`: empty output (0 test lines modified).
