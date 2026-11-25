# AGY2_FundAdvisory 项目架构导览

## 1. 五层单向依赖架构（5-Layer Unidirectional DAG）

现役核心代码统一位于 `AGY2_FundAdvisory/`，严格遵循自底向上的单向依赖，严禁底层叶模块反向依赖高层编排：

```text
Layer 4  展示与跨端接口层 : api_server.py (FastAPI /api/v1/*)  |  app_gui.py (Streamlit 运维台·冻结维护)
   │
   ▼
Layer 3  投顾决策与策略层 : strategy_bridge.py  |  advisory_engine.py  |  portfolio_optimizer.py  |  winrate_engine.py
   │
   ▼
Layer 2  持仓账本与分析层 : portfolio_manager.py (外观门面)  |  multi_ledger_manager.py  |  ledger_backup_vault.py
                            ├─ ocr_importer.py          (智能文本粘贴 + 高清切片 OCR + 28,177 基金匹配)
                            ├─ lookthrough_analyzer.py  (重仓穿透、行业暴露、重合度矩阵、六维体检与调仓路由)
                            ├─ scenario_rebalancer.py   (四大情景调仓推演、渐进定投、日内盈亏与在途对账)
                            ├─ cashflow_planner.py / execution_tracker.py / rebalance_grouping.py
                            └─ forward_audit_logger.py / shadow_portfolio_tracker.py / sector_watchlist.py
   │
   ▼
Layer 1  行情估值与数据层 : data_loader.py  |  valuation_engine.py  |  trading_clock_fee.py  |  data_resilience_guard.py
   │
   ▼
Layer 0  零依赖基础叶子层 : domain_models.py (纯标准库数据结构与基金静态词典)  |  runtime_paths.py (唯一路径解析器)
```

### 核心设计契约
- **`domain_models.py`（零业务依赖叶子层）**：仅允许导入 Python 标准库，集中承载 `HoldingBatch`、`FundHolding`、`HoldingItem`、`PendingOrder`、`FundQuote` 以及 `CORE_STRATEGY_POOL`、`EXTENDED_FUND_CATALOG`、`SECTOR_FUND_SELECTION`，彻底消除子模块反向回导 `portfolio_manager`。
- **`runtime_paths.py`（跨平台与打包唯一路径入口）**：所有读写数据目录统一通过 `get_data_dir()`、`get_cache_dir()`、`get_backup_dir()` 与 `resolve_data_file()` 解析，支持 `AGY2_DATA_DIR` 环境变量测试隔离与桌面客户端冻结打包寻址。
- **根目录单实例兼容入口**：仓库根目录下的 11 个同名 `.py` 文件均为 `<= 20` 行的极薄向后兼容转发入口，所有业务开发仅在 `AGY2_FundAdvisory/` 内进行。

## 2. 仓库目录职责边界

- `AGY2_FundAdvisory/`：现役核心投顾引擎、子域模块、无头 FastAPI 服务与 Streamlit 工作台唯一权威目录。
- `tests/`：`pytest` 自动化单元测试与解耦契约回归套件。
- `scripts/`：当前活跃的实机与架构验收门禁（顶层保持 `<= 10` 个活跃门禁脚本，历史归档脚本统一存放于 `scripts/archive/`）。
- `data/`：本地 Parquet/DuckDB 湖仓、多账本持久化与运行期缓存（动态运行日志 `.jsonl` 与缓存已纳入 `.gitignore`）。
- `src/` 与 `wind_cli.py`：早期 CLI 数据采集工具，不在跨端 `/api/v1/*` 服务端运行链路中。

## 3. 只读红线文件（严禁修改）

- `AGY2_FundAdvisory/judge_engine.py`
- `AGY2_FundAdvisory/holdout_vault.py`
- `AGY2_FundAdvisory/AGENT_SPEC.md`
- `tests/test_infra.py`
- 以及 `DataLoader.simulate_execution` 默认签名与扣费实现。

## 4. 本地常用开发与验收命令

- 启动跨端无头 API 服务：`py -3 -m uvicorn api_server:app --app-dir AGY2_FundAdvisory --host 127.0.0.1 --port 8000`
- 导出最新 OpenAPI 契约：`py -3 AGY2_FundAdvisory/api_server.py --export-openapi`
- 启动本地 Streamlit 工作台：`py -3 -m streamlit run AGY2_FundAdvisory/app_gui.py --server.port 8585`
- 执行只读红线与架构清债门禁：
  - `py -3 scripts/verify_readonly_hashes.py`
  - `py -3 scripts/verify_g46_tech_debt_closure_gate.py`
  - `py -3 -m pytest -q tests/test_infra.py tests/test_api_server_decoupled.py`
