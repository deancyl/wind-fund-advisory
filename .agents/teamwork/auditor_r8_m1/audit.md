# Forensic Audit Report — Milestone 1

**Work Product**: Milestone 1 Implementation (`AGY2_FundAdvisory/app_gui.py`, `AGY2_FundAdvisory/data_loader.py`, `data/cache/custom_watchlist.json`)
**Profile**: General Project (Integrity Mode: Development per ORIGINAL_REQUEST.md)
**Verdict**: **CLEAN**

---

### Executive Summary
Forensic Auditor R8-M1 对 Milestone 1 进行独立法医级审计。本次审计全面核验了物理安全红线、核心计算逻辑真伪、全市场指数/ETF 目录真实性、CSS 并集选择器、测试用例完整性以及是否存在作弊、伪装（facade）、硬编码欺骗或预制虚假测试产物等行为。

**最终判决**：**CLEAN (合规无瑕疵)**。未发现任何欺骗、硬编码假数据或规避测试的行为，4 大只读裁判文件 100% 完好无损。

---

### Phase Results

#### Phase 1: Physical Safety Redlines & Hash Verification
- **裁判文件完整性核验**: **PASS**
  - `AGY2_FundAdvisory/judge_engine.py`: SHA256 `76F930371176DE7EE6A413174B030101E3210AC6E037F5D10FE229AF31CC07BE` (100% 匹配)
  - `AGY2_FundAdvisory/holdout_vault.py`: SHA256 `88122EAF647040A410E2FD95DA81077DB10149A498A47340FF40B670BD031D2A` (100% 匹配)
  - `AGY2_FundAdvisory/AGENT_SPEC.md`: SHA256 `A346586F9BD2DC0EE83E665BD18E7A6471464C9F7B658E392B989B800CD63957` (100% 匹配)
  - `tests/test_infra.py`: SHA256 `48BEE0DA300D7C0A0848EC1376E4B9B2E55224D2736081713B4340F0362CD100` (100% 匹配)
  - 运行 `py -3 scripts/verify_referee_hashes.py` 退出码 0，4/4 通过。

#### Phase 2: Authentic Logic & Anti-Cheat Forensics
- **离线双日真实涨跌幅计算 (`calc_offline_2day_return`)**: **PASS**
  - 源码实测读取 `aligned_matrix_total_return.parquet`（映射 H00300, H00905, H00852, H00922, H30269, STAR50_STITCH, AU9999 等）、`data/processed/indices/*.parquet` 以及 DuckDB `v_etfs`。
  - 实测输出真实浮点涨跌幅（如 000300 输出 `(6175.66, 139.86, 2.32%)`，与 parquet 底表 tail 数据逐比特数学吻合），杜绝了 0.00% 假平盘，不存在硬编码欺骗。
- **高可用批量行情拉取 (`fetch_batch_realtime_indices` / `fetch_custom_realtime_indices`)**: **PASS**
  - 实装三轨互备：东财 push2 批量接口 -> 新浪备用接口 -> 本地 parquet 离线双日收盘价真实涨跌幅回退。
  - 断网与异常注入实测：在模拟断网下 100% 平滑降级至本地 parquet，返回真实计算指标，0 异常、0 崩溃。
- **全市场 38+ 目录与 Rule 16 基准真实性 (`EXPANDED_INDEX_CATALOG`)**: **PASS**
  - 内置 40 只标的，覆盖 14 大赛道板块（宽基核心、红利高股息、科技精选、医药生物、消费核心、金融大盘、绿色能源、国防军工、周期资源、大宗商品、港股海外、美股跨境、债券固收、现金管理）。
  - **Rule 16 红线校验**：中证红利严格且仅映射为 `000922`（secid: `1.000922`，点位 5500+），上证红利独立映射为 `000015`（secid: `1.000015`，点位 3200+），绝无张冠李戴。
- **CSS 并集选择器与 Primary 白字修复**: **PASS**
  - 样式表中已实装 `.val-very-low, .val-very_low` 与 `.val-very-high, .val-very_high` 并集选择器，极低估与过热徽章边框底色正常生效。
  - `button[kind="primary"], button[kind="primary"] *, button[kind="primary"] p, button[kind="primary"] span` 显式强制设置 `color: #ffffff !important`，在全主题下对比度完备。
- **预制虚假测试产物与 Facade 假实现排查**: **PASS**
  - 扫描全库未发现预置伪造日志或测试结果文件。
  - AST 语法树与源码正则未检出任何伪装常量（无 `INDEX_PE_METAS`、无 3210/1780 市场假常数）。

#### Phase 3: Test Authenticity & Weakening Inspection
- **既有测试完整性**: **PASS**
  - `git diff AGY2_FundAdvisory/tests/` 为空，测试套件未被削弱、绕过或恶意 mock。
- **独立执行验证**: **PASS**
  - `py -3 -m pytest AGY2_FundAdvisory/tests/test_sidebar_remodel_and_bugfixes.py` -> 6 passed (含 Streamlit AppTest 4-Tab 0 异常)。
  - `py -3 -m pytest AGY2_FundAdvisory/tests/test_m1_open_data_and_cache.py AGY2_FundAdvisory/tests/test_challenger_m1_adversarial.py tests/test_infra.py` -> 38 passed。

---

### Empirical Evidence

#### Evidence 1: Referee Hash Check
```
PASS: AGY2_FundAdvisory/judge_engine.py matches expected hash.
PASS: AGY2_FundAdvisory/holdout_vault.py matches expected hash.
PASS: AGY2_FundAdvisory/AGENT_SPEC.md matches expected hash.
PASS: tests/test_infra.py matches expected hash.
ALL 4 READONLY REFEREE FILES ARE INTACT AND UNMODIFIED.
```

#### Evidence 2: calc_offline_2day_return Parquet Verification
```python
# parquet tail 数据比对:
# Row 2141: H00300 = 6035.7963, Row 2142: 6175.6600
# chg = 6175.66 - 6035.7963 = 139.8637 -> 139.86
# chg_pct = 139.8637 / 6035.7963 * 100 = 2.317% -> 2.32%
# calc_offline_2day_return('000300') -> (6175.66, 139.86, 2.32)
```

#### Evidence 3: Full Regression Output
```
collected 6 items
AGY2_FundAdvisory\tests\test_sidebar_remodel_and_bugfixes.py ...... [100%]
======================= 6 passed, 3 warnings in 21.81s ========================

collected 38 items
AGY2_FundAdvisory\tests\test_m1_open_data_and_cache.py ......            [ 15%]
AGY2_FundAdvisory\tests\test_challenger_m1_adversarial.py .............. [ 52%]
....                                                                     [ 63%]
tests\test_infra.py ..............                                       [100%]
============================= 38 passed in 6.20s ==============================
```
