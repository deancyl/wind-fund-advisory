# G43 性能修复验证闭环与客户端研发前代码可维护性终审报告

> **审计基准快照**：基于工作区 `d:\Google\Workspace\Wind`（Git HEAD `88101aa` + G43 非 CI 本地修复增量），于真实 Windows 11 + Python 3.11 + Streamlit `http://127.0.0.1:8585` + FastAPI 独立进程 + Chromium/Playwright CDP 环境下实测完成。  
> **红线声明**：① GitHub Actions（`.github/`、`clients/`、`requirements-api.txt`）严格遵守「仅只读探查」，未新建或改动任何工作流/客户端脚手架文件；② 四大只读裁判文件与 `DataLoader.simulate_execution` 签名保持 100% 原始 SHA-256 校验通过。

---

## 第一部分：G43 修复落地与多视角核验结论（已除 GitHub Actions）

### 1. 代码与契约落地清单（根工作区与 `AGY2_FundAdvisory/` 100% 字节同步）
1. **Tab 4 诊断子视图 `UnboundLocalError` P0 崩溃彻底根除**（`app_gui.py` `render_tab4_toolbox_content`）：
   - 将 `_h_items = list(...)` 提升至 `if active_subview == "资产敞口":` 分支之外的公共区域，并移除内部分支的重复定义，确保「重仓重叠」「极端承压」「投顾底稿」均可安全读取持仓列表。
2. **首席投顾今日裁决台 5 胶囊溢框修复**（`app_gui.py` `render_chief_advisor_memo_card`）：
   - 为 `.advisor-capsule-row` 增加 `gap: 4px;`，为 `.advisor-capsule` 增加 `min-width: 0; overflow: hidden; text-overflow: ellipsis;`，第 4/5 颗胶囊不再冲出边框。
3. **Tab 3 复盘五大子视图严格互斥隔离 + 英文冗余列清洗**（`app_gui.py` `render_tab3_backtest_content`）：
   - 采用早期返回（Early Return）重构 5 大子视图（`历史时光机` / `近三年胜率` / `全周期PK` / `样本外前瞻` / `影子账本`），仅在进入对应分支时按需计算（如 `trial29_kpi` 仅在「全周期PK」中惰性读取）；抽出 `_render_rolling_dca_3y_section()` 封装滚动三年胜率模块；为「样本外前瞻」明细表施加严格中文列白名单，消除 `days_elapsed`、`excess_alpha_pct`、`horizon_bucket` 等原始英文字段泄露。
4. **390×844 窄屏普通桌面 UA 无导航修复 + 窄屏深色抽屉适配**（`app_gui.py` `@media (max-width: 768px)` 与侧边栏样式层）：
   - 移除 `@media (max-width: 768px)` 隐藏侧边栏与折叠按钮的旧规则；将私人银行曜石蓝深色侧边栏（`#0F1C2E`）与高对比度文本/按钮/选择器 CSS 移出 `@media (min-width: 769px)` 限制使全视口生效（仅桌面定宽 `256px` 与 `100vh` 锁滚动保留在 `>=769px`）；删除无效的 `[aria-expanded="false"]` 选择器（Streamlit 1.38+ 使用 `transform` 而非 `aria-expanded`），改为 `max-width: 82vw` 抽屉与 `stSidebarCollapseButton` / `stExpandSidebarButton` 双向常驻可见。
5. **FastAPI 服务端安全加固与冷启动/高频并发提速**（`api_server.py` + `docs/openapi_v1.json` 重导出）：
   - 移除 `allow_origins=["*"]` 裸奔配置，收紧为 `localhost` / `127.0.0.1` / `tauri://localhost` / `https://tauri.localhost` / `capacitor://localhost` / `http://localhost:1420` 等明确白名单并支持 `AGY2_CORS_ORIGINS` 环境变量；
   - `_get_active_context` 改用 `MultiLedgerManager.get_instance()` 复用单例索引与上下文；
   - 新增 `@asynccontextmanager async def _lifespan` 守护线程后台预热 `MultiLedgerManager` 与 `MarketStrategyBridge`；
   - 重写 `api_v1_overview`：引入 30 秒 TTL 缓存 `_OVERVIEW_CACHE` + 4 线程 `ThreadPoolExecutor` 并发拉取 `prefetch_batch_fund_quotes` 与 3 大指数行情，并用 `FundQuote.gszzl` 实时汇总盘中日盈亏；重新运行 `py -3 api_server.py --export-openapi` 零警告同步 `docs/openapi_v1.json`。

### 2. 实机验证与门禁通过情况
| 验证项 | 实测方式 | 关键结果 |
| :--- | :--- | :--- |
| 只读文件 SHA-256 与 API 解耦单测 | `verify_readonly_hashes.py` + `pytest tests/test_api_server_decoupled.py -q` | **全部通过**：4 个裁判文件 100% 校验一致；2 passed in 6.79s |
| G43 专项性能、崩溃、安全与多视口门禁 | `py -3 scripts/verify_g43_perf_and_p0_gate.py` | **11/11 断言全绿**：CORS 拦截恶意 Origin 放行 Tauri 源；`/api/v1/overview` 缓存命中 **3.7 ms**；`重仓重叠` 404.8 ms / `极端承压` 5234.9 ms 均 0 崩溃；`近三年胜率` 切换 **2589.1 ms**（< 5000 ms）；5 胶囊 0 溢框；`390x844` 桌面 UA 与 Mobile UA 均 **xOverflow = 0** 且折叠/展开/深色 `#0F1C2E` 正常 |
| G41 / G42 既有跨端与视觉回归门禁 | `verify_g41_pixel_and_contrast_gate.py` + `verify_g42_final_closure_gate.py` | **全部通过**（注：历史遗留脚本 `verify_g40_visual_craft_gate.py` 因引用已删除的 `ui_daily_brief.py` 报错退出，详见第二部分卡点 8） |
| CDP 性能、Cookie、内存与多端响应探针 | `scratch/audit_3env_probe.py`（Chromium CDP + FastAPI 实机） | Cookie 仅含 `_streamlit_xsrf`（SameSite=Lax），WebSocket 零报错 `page_errors=[]`；API 12 个 `/api/v1/*` 端点全 200（`holdings` 193.5 ms、`rebalance` 571.9 ms、`funds/search` 29.4 ms、`sectors` 686.2 ms）；5 轮 4-Tab 切换后 `jsHeapUsedMB` GC 后 **44.28 MB**（仅 +7.46 MB），但 DOM 节点从 3,482 增至 17,147（Streamlit 跨切换节点累积特性） |
| 内置 `/browser` 子代理与 Playwright 截图目视复核 | `invoke_subagent(browser)` + Playwright 4 张实拍截图目视 | 内置 `webview_browser` 因当前会话未挂载 Hub 窗口返回 `BLOCKED / WEBVIEW_UNAVAILABLE`；已通过无头 Chromium 实拍 4 张复核图（1440x900 持仓、诊断重仓重叠、复盘近三年胜率、390x844 窄屏深色侧栏）目视确认渲染正常 |

---

## 第二部分：GitHub Actions 仅只读探查结论

对 `.github/`、`clients/`、`requirements*.txt` 进行了只读检查，结论如下：
1. 仓库根目录与 `AGY2_FundAdvisory/` 下**均不存在 `.github/` 工作流目录**，**不存在 `clients/` 前端壳目录**，亦**不存在 `requirements-api.txt`**。
2. 仓库根目录仅有一份 `requirements.txt`（15 行，13 个有效依赖：`pandas>=2.0.0`, `polars>=1.0.0`, `numpy>=1.24.0`, `duckdb>=1.0.0`, `requests>=2.28.0`, `urllib3>=1.26.0`, `httpx>=0.24.0`, `pydantic>=2.0.0`, `rich>=13.0.0`, `pywin32>=306`, `psutil>=5.9.0`, `pefile>=2023.2.7`, `scipy>=1.10.0`, `pytest>=8.0.0`），`AGY2_FundAdvisory/` 下没有任何 `requirements*.txt`。
3. **直接阻断未来 CI 打包的两个客观缺陷**：
   - `requirements.txt` 中包含 Windows 专用包 `pywin32>=306` 与 `pefile>=2023.2.7`，在 `ubuntu-latest`（Android Capacitor APK / Linux 容器任务）上 `pip install -r requirements.txt` 会直接失败；
   - `requirements.txt` **缺失** `fastapi`、`uvicorn`、`streamlit`、`plotly`、`akshare`、`python-multipart`、`orjson` 与 `pyinstaller`，直接按现有依赖文件构建 Sidecar 必败。

---

## 第三部分：进入客户端开发前——最高标准代码可维护性终审清单

> 本节站在**“任何新开发者或外部团队接手并基于本仓库开发 Windows `.exe`（Tauri）+ Android `.apk`（Capacitor）双端客户端”**的最高工程标准下，客观列出当前所有**卡点、困惑点与不可维护点**（所有行号与数据均来自本轮实测扫描，无任何推测）。

### 【P0 级硬阻塞】进入客户端开发前必须先解决的契约与架构失真

#### 1. `api_server.py` 存在 4 个“伪造 Mock 端点”与重复路由（直接违背真实数据宪法）
新前端工程师一旦按 `docs/openapi_v1.json` 接入客户端，会在毫不知情下把写死的假数据渲染到客户端界面中：
- **`GET /api/v1/diagnose/exposure`**（`api_server.py` L1133-1140）：忽略实际持仓分析，直接硬编码返回 `{"equity": 0.65, "fixed_income": 0.25, "qdii": 0.10}` 与 `{"电子": 0.22, "银行": 0.18, "医药生物": 0.15}`。
- **`GET /api/v1/diagnose/overlap`**（`api_server.py` L1141-1148）：硬编码返回 `max_overlap_pair: ["000058", "110020"]`、`max_overlap_pct: 0.76`。
- **`GET /api/v1/diagnose/stress_test`**（`api_server.py` L1149-1160）：硬编码返回 `-0.165 / -0.112 / -0.138` 及 `var_95: -0.024`、`cvar_95: -0.038`。
- **`GET /api/v1/backtest/summary`**（`api_server.py` L1173-1186）：忽略当前账本与回测引擎，硬编码返回 `annualized_return_pct: 14.8`、`max_drawdown_pct: -12.4`、`sharpe_ratio: 1.35`、`win_rate_pct: 81.6`。
- **同义重复 API 端点组**：`GET/POST/DELETE /api/v1/sectors`（L1189-1231）与 `GET/POST /api/v1/watchlist`（L1234-1270）重复封装完全相同的 `sector_watchlist` 逻辑，增加客户端调用歧义与维护双份成本。

#### 2. “双镜像目录 + 三套入口体系”导致严重的心智迷宫与打包寻址风险
目前仓库存在极易令新开发者崩溃的结构性分裂：
- **11 个关键文件必须“手工双份完全镜像”**：以下 11 个 Python 文件同时存在于根目录 `Wind/*.py` 与子目录 `AGY2_FundAdvisory/*.py`：
  `api_server.py` (1,326 行)、`app_gui.py` (10,118 行)、`strategy_bridge.py` (7,750 行)、`cashflow_planner.py` (273 行)、`data_resilience_guard.py` (351 行)、`execution_tracker.py` (308 行)、`forward_audit_logger.py` (338 行)、`ledger_backup_vault.py` (311 行)、`rebalance_grouping.py` (156 行)、`sector_watchlist.py` (118 行)、`shadow_portfolio_tracker.py` (247 行)。此外 `docs/openapi_v1.json` 和 `scripts/verify_*.py` 也有部分双份。只要改完一方忘记拷贝另一方，行为就会静默分叉。
- **12 个核心引擎只存在于 `AGY2_FundAdvisory/`，根目录没有**：如 `portfolio_manager.py`（12,240 行）、`advisory_engine.py`（5,105 行）、`data_loader.py`（4,027 行）、`portfolio_optimizer.py`（2,108 行）、`winrate_engine.py`（1,080 行）、`multi_ledger_manager.py`（743 行）、`cache_manager.py`（778 行）等，导致根目录下的 `app_gui.py` 必须依赖运行期向 `sys.path` 强插 `AGY2_FundAdvisory` 才能跑通。
- **第三套并行代码树 `src/` + `wind_cli.py`（2,319 行）**：根目录的 `wind_cli.py` 导入 `from src.analysis... / src.parsers...`（共 129 个文件），与 `AGY2_FundAdvisory/` 功能大量重叠但模块体系独立，新开发者完全分不清核心投顾逻辑到底以 `src/` 为准还是以 `AGY2_FundAdvisory/` 为准。
- **29 处 `sys.path.insert(0, ...)` 与 128 处双目录/CWD 路径猜测**：模块内部遍布 `if CURRENT_DIR.name == "AGY2_FundAdvisory"` 与 `Path("data/...")`、多级备选路径探测（仅 `advisory_engine.py` 对同一个 `aligned_matrix_total_return.parquet` 就有 3 处不同回退写法）。一旦打成 PyInstaller `--onedir`/`--onefile` Sidecar 在系统临时目录或 `Program Files` 只读目录启动，`os.getcwd()` 与 `CURRENT_DIR` 均不再是仓库结构，极易读写错位或抛出 `FileNotFoundError`。

#### 3. 依赖清单缺失与跨平台冲突（见第二部分）
必须拆分为跨平台 `requirements-api.txt`（严格剔除 `pywin32`、`pefile` 等 Windows 专属库）与开发测试 `requirements-dev.txt`，否则无法进行多端 CI 构建。

---

### 【P1 级重大维护卡点】巨石单体、循环依赖、全局状态泛滥与并发隐患

#### 4. “三座巨石神像”级超大单文件（仅核心 5 文件即超 39,200 行）
| 文件路径 | 代码行数 | 文件大小 | 函数数 | 最长单函数 | 核心可读性/维护病灶 |
| :--- | :---: | :---: | :---: | :--- | :--- |
| `AGY2_FundAdvisory/portfolio_manager.py` | **12,240** | 599 KB | 174 | `prefetch_batch_fund_quotes` (**730行**)、`screen_fund_look_through_risk` (**390行**)、`fetch_realtime_fund_quote` (**385行**)、`generate_scenario_rebalance_plan` (**373行**) | 把持仓账本 CRUD、网络爬虫、多源对账、重仓穿透、OCR 解析、情景调仓、CVaR Bootstrap、限购探测全部堆进 1 个文件 |
| `app_gui.py`（及镜像） | **10,118** | 567 KB | 70 | `render_tab4_toolbox_content` (**915行**)、`render_tab3_backtest_content` (**793行**)、`render_dual_wing_advisory_dashboard` (**353行**) | 内联 2,000+ 行 CSS/JS f-string 与业务逻辑、状态初始化、网络刷新混写，修改一处极易误伤其他 Tab |
| `strategy_bridge.py`（及镜像） | **7,750** | 396 KB | 80 | `generate_ai_rebalance_orders` (**687行**)、`simulate_rebalance_modes_and_consequences` (**603行**)、`get_latest_market_snapshot` (**566行**) | AI 调仓状态机、全真摩擦账单、动态权重、情绪引擎高度耦合 |
| `AGY2_FundAdvisory/advisory_engine.py` | **5,105** | 265 KB | 50 | `inspect_portfolio` (**1,021行**！)、`generate_chief_advisor_memo` (**527行**)、`compute_ten_dimension_votes` (**378行**) | 单函数 `inspect_portfolio` 超过 1,000 行，所有风控哨规则耦合在一个巨型过程式函数内 |
| `AGY2_FundAdvisory/data_loader.py` | **4,027** | 190 KB | 47 | `fetch_or_calc_index_valuations` (**291行**)、`fetch_macro_cross_market_indicators` (**267行**)、`fetch_custom_realtime_indices` (**250行**) | 数据抓取、本地 Parquet 自愈、DuckDB 湖仓读取与业务口径纠偏混合 |

#### 5. 环形交叉引用与导入耦合网络
AST 导入图扫描显示核心模块之间存在密集闭环互导：
- `portfolio_manager` ↔ `advisory_engine` ↔ `data_loader` ↔ `strategy_bridge` ↔ `portfolio_optimizer` ↔ `winrate_engine` 两两或三向互导；
- 上述模块全靠函数体内部零散执行延迟 `import` 来规避启动期 `ImportError`，新开发者极难追踪究竟谁是底层基础库（Domain/Data Layer）、谁是上层编排（Service/Application Layer）。

#### 6. 碎片化状态（81 个 `session_state` 键）与多套零散缓存/存储无统一边界
- **前端状态失控**：`app_gui.py` 内包含 **81 个**不同前缀的 `st.session_state` 键（共 **513 处**访问），无集中式 State Schema 或重置方法；同一语义甚至并存多键（如 `desktop_nav_tab` / `desktop_main_nav` / `active_main_nav`、`app_theme_mode` / `app_color_mode`）。
- **磁盘持久化介质碎片化**：扫描发现各模块自行向零散路径读写 **50+ 个**不同文件（`.json`、`realtime_quotes.json`、`fund_look_through_cache.json`、`custom_sector_watchlist.json`、`daily_execution_checklist.json`、`daily_intraday_est_archive.json`、`factor_evolution_cache.json`、`.pkl`、`.db` SQLite、`storage.duckdb`、大量 `.parquet`），缺少统一 `AppConfig / StorageRegistry`，打包成桌面或移动端只读应用沙箱后数据目录治理会非常痛苦。
- **FastAPI 与核心引擎并发线程安全薄弱**：`api_server.py` 存在后台预热线程 `_warmup_engine_background()` 与请求线程并发读写模块级缓存/JSON 账本的问题（`MultiLedgerManager`、`realtime_quotes.json` 缺少统一文件锁/读写锁）；此外 `api_v1_import_ocr` 为 `async def` 却同步执行 CPU/IO 密集型 `parse_screenshot_ocr_holdings` 与 `save_state()`，并发时会阻塞事件循环（应改为 `def` 或 `run_in_threadpool`，且避免 `except Exception: parsed = []` 吞错）。

#### 7. Git 仓库与运行期可变状态高度混杂
运行期会自动改写的十余个 JSON/JSONL 状态文件及根目录测试截图被直接纳入 Git 版本追踪（如本轮仅启动一次服务与门禁即导致 `data/forward_decision_audit.jsonl`、`data/oos_verdict_ledger.jsonl`、`data/portfolio_watchdog.json`、`data/daily_execution_checklist.json`、`data/daily_intraday_est_archive.json`、`AGY2_FundAdvisory/data/*`、`g41_desktop_verified.png` 全部标红修改），严重干扰代码 Review 与 CI 洁净度检查。

---

### 【P2 级工程效率与长期稳定性债】门禁熵增与异常黑洞

#### 8. “门禁脚本坟场”：62 个历史验证脚本中至少 12 个已失效崩溃
- 根目录 `tests/` 已有 95 个文件（**1,141 个** pytest 用例），而 `scripts/` 中还堆积了 **62 个** `verify_*.py` 独立验证脚本。
- 本轮实测发现 `verify_g40_visual_craft_gate.py` 直接抛出 `FileNotFoundError: ui_daily_brief.py`；静态扫描证实**共有 12 个 `scripts/*.py`**（包括 `test_ast_insertion.py`、`test_intent_grouping*.py`、`verify_g30`~`verify_g36`、`verify_g40_visual_craft_gate.py`、`verify_g41_production_closure_gate.py`）仍在硬检查已被重构删除的 `ui_daily_brief.py`，处于“无人维护但继续躺在仓库误导新人”的状态。

#### 9. 异常静默吞没遍地（5 大核心模块共 387 处宽泛捕获）
- 统计 `except:` / `except Exception:` 捕获次数：`portfolio_manager.py` **131 处**、`data_loader.py` **81 处**、`app_gui.py` **62 处**、`strategy_bridge.py` **59 处**、`advisory_engine.py` **54 处**（加上 `api_server.py` 多处 `except Exception: return []`）。
- 许多网络拉取或量化算子出错后直接静默兜底返回默认值而不输出结构化告警或错误码，给后续桌面/移动客户端排查真实接口超时、格式变更或空数据问题埋下极深隐患。

#### 10. Streamlit 架构天花板（已由本轮 CDP 内存/DOM 探针实测验证）
- 本轮 CDP 连续 5 轮 4-Tab 切换显示：`jsHeapUsedMB` 在 GC 后虽可回落至 44.28 MB，但页面 DOM 节点数仍从 **3,482 持续攀升至 17,147**、事件监听器从 **646 增至 1,836**，并伴随 22 次 iframe 沙盒安全告警。这从实测层面证明：绝不能以套壳 Streamlit 方式上线 `.exe`/`.apk`，**坚持「FastAPI 本地引擎 + 原生轻量前后端分离（Tauri/React 或 Capacitor）」是唯一正确方向**。

---

## 第四部分：给外部审计的客户端研发前清理建议（分阶段准入门槛）

建议外部审计评估是否在**启动 Tauri/Capacitor 客户端编码前**，优先安排一个精简的 **“G43.5 代码整洁与契约真实化前置脉冲”**：
1. **必做准入项（Blockers before UI）**：
   - 将 `api_server.py` 中 4 个硬编码 Mock 端点（`/diagnose/exposure`、`/diagnose/overlap`、`/diagnose/stress_test`、`/backtest/summary`）全部接通真实引擎，合并 `/sectors` 与 `/watchlist` 重复路由，并重签 `openapi_v1.json`；
   - 确立**唯一数据与运行时根路径解析器**（支持环境变量 `AGY2_DATA_DIR` / `sys._MEIPASS` 冻结打包模式），消除 128 处相对路径猜测；
   - 拆分 `requirements-api.txt`（跨平台无 `pywin32`）与 `requirements-dev.txt`；
   - 将运行期变动文件（`data/*.jsonl`、`daily_*`、`*_watchdog.json`、验证截图 `.png`）从 Git 追踪列表移除并纳入 `.gitignore`。
2. **结构性减负项（High ROI Refactor）**：
   - 确立**单一权威源码目录（Single Source of Truth）**，用包导入或极薄启动入口取代 11 个文件的手工复制镜像与 29 处 `sys.path.insert`；明确 `src/` 与 `AGY2_FundAdvisory/` 的归属边界；
   - 归档 `scripts/verify_g1..g40` 已过期脚本至 `scripts/archive/`，保留少量权威活跃门禁清单；
   - 优先按领域拆薄 `portfolio_manager.py`（12k 行）与 `advisory_engine.inspect_portfolio`（1k 行单函数），同时为 `api_server.py` 增加共享读写锁与结构化错误码响应，避免把问题带入双端调试期。
