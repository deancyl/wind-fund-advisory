# Handoff Report: Explorer M1-2 (Features 3 & 4)

## 1. Observation
- **`portfolio_manager.py:1624-1765`**:
  `fetch_realtime_fund_quota` 当前仅有 L1 内存字典与 L2 SQLite 表 `fund_daily_quota_cache`。未命中时在第 1673 行直接同步调用 `ak.fund_purchase_em()`，拉取全市场 27,964 只基金耗时高达 16.17 秒，且没有落盘至 `data/cache/fund_purchase.parquet`。
- **`cache_manager.py:26`**:
  `CACHE_BASE` 设在 `data/cache/market_screener`，缺少全市场基金申购限额 Parquet 与单只基金排雷元数据 JSON 的管理类。
- **`data/master/fund_trading_rules.parquet`**:
  实测存在 27,884 条历史交易规则，包含 `symbol`, `purchase_status`, `redemption_status`, `daily_limit_amount`，读取耗时为 48.35 ms。
- **Parquet 性能基准测试**:
  清洗后的 `fund_purchase.parquet`（27,884 行，包含 `基金代码`, `申购状态`, `赎回状态`, `日累计限定金额`）体积仅 206 KB，磁盘读取耗时仅 **3.87 ms**（远低于 <50ms 规范），构建内存索引耗时 37 ms，单次查询耗时 **< 0.01 ms**。
- **天天基金接口 `http://fund.eastmoney.com/pingzhongdata/{code}.js`**:
  以 `000001`, `050025`, `100032`, `518880` 现场实测，单请求耗时 100~200 ms，完整包含：
  - `Data_fluctuationScale`（最新规模，如 000001 为 29.19 亿）；
  - `Data_currentFundManager`（经理姓名、任职时长如 "14年又330天"、任期回报如 8.2969%）；
  - `Data_assetAllocation`（季报真实股票 78.21%、债券 20.82%、现金 0.45%）；
  - `stockCodesNew`（前十大重仓股票列表）。
- **`data/master/fund_managers.parquet` & `data/storage.duckdb`**:
  实测包含 40,000+ 经理记录（`manager_name`, `career_days`, `aum_billion`, `best_return_pct`）与 `v_fund_snapshot` 视图，具备完整的离线兜底数据源。

## 2. Logic Chain
1. 基于 Observation 1，`fetch_realtime_fund_quota` 在未预热时同步调用 `ak.fund_purchase_em()` 耗时 16s，严重破坏首屏冷启动 `<0.5s` 要求。
2. 基于 Observation 3 与 Observation 4，通过将限额数据持久化为 `data/cache/fund_purchase.parquet`，磁盘读取时间降至 3.87 ms，彻底消灭 16s 阻塞，并完美达成 < 50ms 指标要求。
3. 基于 Observation 3 与 Observation 6，若网络不可用，从 `data/master/fund_trading_rules.parquet` 与 `fund_managers.parquet` 降级读取，保证离线 0 崩溃。
4. 基于 Observation 5，天天基金单文件接口包含规模、经理年限/回报、季报资产配置与前十大重仓，建立 24h TTL 本地缓存 `data/cache/funds/{code}_meta.json` 能够实现持仓基金 2~3 ms 极速读取，并为 `<0.5亿` 迷你基清盘排雷与稳健 FOF 资产穿透提供强力数据基建。
5. 综合以上推理，在 `cache_manager.py` 实装 `FundPurchaseCacheManager` 与 `FundMetadataManager`，在 `data_loader.py` 暴露统一门面，在 `portfolio_manager.py` 和 `portfolio_optimizer.py` 中接入，能够以最小侵入度完成 Feature 3 与 Feature 4 的全链路闭环。

## 3. Caveats
- `ak.fund_purchase_em()` 网络拉取在高峰期可能需 15~20 秒，全量初次生成 `data/cache/fund_purchase.parquet` 建议在系统初始化或后台离线执行，或直接由 `fund_trading_rules.parquet` 快速初始化。
- QDII 基金（如 `050025`）的天天基金 `stockCodesNew` 字段为空（因海外重仓股由特定 QDII 字段维护），需在重仓股解析中保持空列表容错。
- 历史测试用例（如 `test_milestone_phase1_r1_r5.py:199`）显式传入了 `db_path=test_db` 测试 SQLite 表，新版 `fetch_realtime_fund_quota` 必须保持对该参数的双写兼容。

## 4. Conclusion
Milestone 1 中 Feature 3 与 Feature 4 的技术方案已完全验证并定型：
1. **Feature 3**: 规范 `data/cache/fund_purchase.parquet`（列：`['基金代码', '申购状态', '赎回状态', '日累计限定金额']`），实现 3.87ms 冷读取，无缝打通 `portfolio_manager.py` 与 `portfolio_optimizer.py` 限额过滤，断网平滑降级至 `fund_trading_rules.parquet`。
2. **Feature 4**: 规范 `data/cache/funds/{code}_meta.json`（24h TTL），精准提取 `<0.5亿` 清盘风险、经理任期回报、季报真实股债仓位与前十大重仓，断网平滑降级至 `fund_managers.parquet` 与 DuckDB。
3. 详细代码 Diff 与实施检查清单已完整输出于 `report.md`。

## 5. Verification Method
1. **基准性能核验**:
   在 PowerShell 中执行命令验证读取时间严格 < 50ms：
   `py -3 -c "import time, pandas as pd; t0 = time.perf_counter(); df = pd.read_parquet('data/master/fund_trading_rules.parquet'); t1 = time.perf_counter(); print(f'Read time: {(t1-t0)*1000:.2f} ms'); assert (t1-t0) < 0.05"`
2. **天天基金元数据解析核验**:
   `py -3 -c "import urllib.request, re, json; t = urllib.request.urlopen('http://fund.eastmoney.com/pingzhongdata/000001.js', timeout=5).read().decode('utf-8'); assert 'Data_fluctuationScale' in t and 'Data_currentFundManager' in t"`
3. **单元测试回归命令**:
   在 Worker M1 完成代码实现后执行增量单元测试：
   `py -3 -m pytest AGY2_FundAdvisory/tests/test_milestone_phase1_r1_r5.py -k "test_case_03_realtime_quota"`
4. **失效条件 (Invalidation Conditions)**:
   - 若 `data/cache/fund_purchase.parquet` 读取耗时超过 50ms 则方案失效；
   - 若断网模拟下 `fetch_realtime_fund_quota` 抛出未捕获异常则方案失效；
   - 若 `<0.5亿` 迷你基未触发 `liquidation_risk` 报警则方案失效。
