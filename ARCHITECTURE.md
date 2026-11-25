# AGY2_FundAdvisory 项目架构导览

## 1. 目录职责边界（唯一权威声明）

- `AGY2_FundAdvisory/`：**现役核心投顾系统唯一权威后端与界面源码目录**。所有业务修改仅在此目录发生：
  - `api_server.py`：跨端无头 FastAPI 引擎（对外提供 `/api/v1/*` 标准化 JSON 契约与 `docs/openapi_v1.json`，为桌面 `.exe` 与安卓 `.apk` 客户端唯一后端）。
  - `app_gui.py`：Streamlit 本地运维工作台（G43 后进入功能冻结维护期，仅修崩溃，不加新 UI 扩展）。
  - `runtime_paths.py`：全局唯一运行时数据、缓存、备份与冻结打包路径解析器（消除 CWD 相对路径漂移）。
  - `portfolio_manager.py`（主账本外观）、`advisory_engine.py`、`strategy_bridge.py`、`data_loader.py`：核心引擎与编排层，其中 `portfolio_manager.py` 已按领域拆分为 4 个独立子模块：
    * `ocr_importer.py`：智能文本粘贴解析、长截图高清切片 OCR 与 28,177 基金模糊匹配；
    * `valuation_engine.py`：官方净值主权判定、四级穿透实时估值、东财批量并发拉取与限购替补；
    * `lookthrough_analyzer.py`：重仓穿透、行业暴露、重合度矩阵、六维体检与调仓路由（`LookthroughAnalyzerMixin`）；
    * `scenario_rebalancer.py`：情景推演调仓、渐进加仓、日内盈亏核算与在途订单交收（`ScenarioRebalanceMixin`）。
  - 其余根目录 11 个同名 `.py` 文件仅作为 `<= 20` 行的极薄向后兼容转发入口，严禁再复制业务代码。
- `src/` 与 `wind_cli.py`：早期历史 CLI 数据采集与分析工具树，与现役 `AGY2_FundAdvisory/` 相互独立，不在跨端 API 链路中。
- `tests/`：pytest 自动化单元测试与契约回归测试集（`py -3 -m pytest -q`）。
- `scripts/`：实机端到端验收活跃门禁脚本（G41+）；历史淘汰脚本归档于 `scripts/archive/`。
- `data/`：本地运行期实盘/缓存数据与账本（动态审计日志 `.jsonl` 与运行快照不纳入 Git 版本控制）。

## 2. 只读红线文件（严禁修改）

- `AGY2_FundAdvisory/judge_engine.py`
- `AGY2_FundAdvisory/holdout_vault.py`
- `AGY2_FundAdvisory/AGENT_SPEC.md`
- `tests/test_infra.py`
- 以及 `DataLoader.simulate_execution` 默认签名与扣费实现。

## 3. 本地常用命令

- 启动无头 API 服务：`py -3 -m uvicorn api_server:app --app-dir AGY2_FundAdvisory --host 127.0.0.1 --port 8000`
- 导出 OpenAPI 契约：`py -3 AGY2_FundAdvisory/api_server.py --export-openapi`
- 启动本地工作台：`py -3 -m streamlit run AGY2_FundAdvisory/app_gui.py --server.port 8585`
- 运行核心与门禁验证：`py -3 scripts/verify_readonly_hashes.py`、`py -3 -m pytest -q tests/test_infra.py tests/test_api_server_decoupled.py`
