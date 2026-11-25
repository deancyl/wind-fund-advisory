# AGY2 G44/G45 改后功能、性能、A11y、内存与剩余技术债全面审计报告（外部审计包）

> **审计基准**：Git HEAD `28f3621`（含 `G44` 提交 `d44dcd8` 与 `G45` 四刀拆解提交 `28f3621`），于 Windows 11 + Python 3.11 + Streamlit `http://127.0.0.1:8585` + FastAPI 独立进程（`:18198`）+ `/browser` 实机子代理 + 无头 Chromium CDP 环境下实测完成。  
> **红线状态**：4 个只读裁判文件保持 100% SHA-256 未改动；`.github/` 与 `clients/` 目录不存在（未提前新建）。

---

## 一、诊断通道与 Troubleshooting 实况

1. **MCP 配置排查（`/troubleshooting` Step 1）**：
   - 经逐一检查 `.mcp.json`、`gemini-extension.json`、`.gemini/settings.json`、`C:\Users\deanc\.gemini\settings.json`、`C:\Users\deanc\.gemini\antigravity\mcp_config.json`，均返回 `False`（未配置独立的 `chrome-devtools-mcp` 服务进程，因此不存在 `list_pages` / `new_page` / `lighthouse_audit` MCP 原生工具）。
2. **等价全链路实测通道**：
   - **`/browser` 实机子代理**（`66031e12`，宿主机 `BROWSER_HOST_FACTS` 已核验访问 `http://127.0.0.1:8585`，`blocked_origins: none`，实拍截图见同包 `browser_live_screenshot.png`）；
   - **Playwright + Chrome DevTools Protocol (CDP)** 直连 `http://127.0.0.1:8585` 与独立 FastAPI `:18198`，执行 `Performance`、`HeapProfiler.collectGarbage`、A11y DOM/对比度/热区/键盘焦点、Cookie 与 CORS 探针（完整原始数据见同包 `cdp_a11y_cookie_memory_api_metrics.json`）；
   - **AST 静态全库扫描**（完整模块与函数指标见同包 `static_tech_debt_inventory.json`）。

---

## 二、G44 / G45 改后功能影响核查

### 1. 实机捕获 1 处 P0 级回归缺陷（G45 Cut 3 拆离遗漏）
- **复现路径**：`Tab 2（调仓 · 清单与打卡）` -> 子分段 `存量重塑`。
- **`/browser` 实机报错信息**：界面弹出局部告警框：  
  `【🌱 新资建仓】渲染出现局部异常: name 'SECTOR_FUND_SELECTION' is not defined`
- **为什么既有自动化门禁未提前拦截**：[app_gui.py#L6810](file:///d:/Google/Workspace/Wind/AGY2_FundAdvisory/app_gui.py#L6810) 使用 `try ... except Exception as e: st.error(...)` 将异常降级渲染为 `stAlert` 提示条，未生成 `[data-testid="stException"]` 红框；且既有 G43/G44/G45 门禁未覆盖点击 Tab 2 `存量重塑` 子分段。
- **AST 精确定位根因**：`SECTOR_FUND_SELECTION` 仍定义于 `AGY2_FundAdvisory/portfolio_manager.py:762`，而在 G45 Cut 3 抽离 `LookthroughAnalyzerMixin` 至 `AGY2_FundAdvisory/lookthrough_analyzer.py` 时，以下 3 处方法内漏绑 `SECTOR_FUND_SELECTION = __pm_mod.SECTOR_FUND_SELECTION`：
  - `AGY2_FundAdvisory/lookthrough_analyzer.py:913`（`_compute_asset_class_category`）
  - `AGY2_FundAdvisory/lookthrough_analyzer.py:1208`（`screen_fund_look_through_risk`）
  - `AGY2_FundAdvisory/lookthrough_analyzer.py:1702`（`get_fund_smart_money_crowding`）
- **其他 3 个新拆模块校验**：全文件 AST 扫描确认 `ocr_importer.py`、`valuation_engine.py`、`scenario_rebalancer.py` 均无其它缺失顶层全局变量引用。

### 2. 其余功能面与 FastAPI 真实引擎全部正常
- **Web 端（1440×900 & 390×844）**：Tab 1（持仓明细/估值对账/在途限购）、Tab 2（今日调仓/新钱定投）、Tab 3（历史时光机/近三年胜率/样本外前瞻）、Tab 4（风险体检/资产敞口/重仓重叠/极端承压）`[data-testid="stException"]` 均为 **0**，50 个网络请求失败数为 **0**，Console `error` 为 **0**。
- **FastAPI 独立后端（`:18198`）**：实测 10 个核心 `/api/v1/*` 路由全部返回 **HTTP 200**，原 4 处 Mock 端点已全部输出真实计算字段：
  - `/api/v1/diagnose/exposure`（27.3 ms）
  - `/api/v1/diagnose/overlap`（71.1 ms）
  - `/api/v1/diagnose/stress_test`（227.9 ms）
  - `/api/v1/diagnose/ten_dim_votes`（3.2 ms）
  - `/api/v1/backtest/summary`（4.3 ms）

---

## 三、性能、内存泄漏、Cookie 与 A11y 无障碍体检

### 1. 性能实测（`/chrome-devtools` CDP + FastAPI）
| 测项 | 实测值 | 结论 |
| :--- | :---: | :--- |
| 首屏 `ttfb` / `domInteractive` / `FCP` / 冷稳态总耗时 | `2 ms` / `16 ms` / `2732 ms` / `7955 ms` | ✅ 正常 |
| 主 Tab 切换延迟（持仓/调仓/复盘/诊断） | `506.9 ~ 1420.4 ms` | ✅ 无退化 |
| Tab 3 隔离切换（`近三年胜率` / `样本外前瞻`） | `527.8 ms` / `495.7 ms` | ✅ 严格隔离且秒切 |
| Tab 4 子视图（`资产敞口` / `重仓重叠` / `极端承压`） | `532.4 ms` / `575.4 ms` / `479.2 ms` | ✅ 0 崩溃且 < 0.6s |
| FastAPI 路由耗时（除 `/watchlist`） | `3.2 ~ 561.9 ms` | ✅ 高效 |
| FastAPI `/api/v1/watchlist` | **`828.1 ms`** | ⚠️ 偏慢（内部循环串行拉行情） |

### 2. Cookie 与 CORS 安全（`/cookie-debugging`）
- **浏览器 Cookie / Storage**：仅含 Streamlit 原生 `_streamlit_xsrf`（`SameSite=Lax`, `path=/`），`localStorageKeys = []`，`sessionStorageKeys = []`，无敏感业务明文 Cookie。
- **FastAPI CORS / Cookie**：全部 10 个端点 `Set-Cookie = null`；合法源 `Origin: http://localhost:1420` 正确返回 `Access-Control-Allow-Origin: http://localhost:1420`；恶意源 `Origin: https://evil-attacker.example.com` 被拦截（`Access-Control-Allow-Origin = null`）。

### 3. 内存泄漏检查（`/memory-leak-debugging` CDP GC 对比）
连续执行 5 轮 4-Tab 完整来回切换并调用 `HeapProfiler.collectGarbage`：
- **JS Heap（`jsHeapUsedSize`）**：基线 `37.92 MB` -> 第 3 轮峰值 `119.14 MB` -> 第 5 轮 GC 后 **`39.10 MB`**（净增仅 **+1.18 MB**，无实质 JS 对象泄漏）。
- **DOM 节点与事件监听器残留**：DOM `Nodes` 从 `6,718` 增至 **`14,595`**（+117.3%），`JSEventListeners` 从 `978` 增至 **`1,218`**，伴随 28 条 `allow-scripts` + `allow-same-origin` iframe 沙盒告警（属 Streamlit 架构固有特性，非单业务代码改动引入，进一步验证客户端需基于 FastAPI 解耦研发）。

### 4. A11y 无障碍与多视口布局审计（`/a11y-debugging` + `/browser`）
- **全局文档声明与标题树**：`<html lang="en">` 与中文内容不匹配；页面缺乏语义化 `<h1>~<h4>` 结构（桌面首屏 `headings_count = 0` 或仅含空 `<h3>`/`<h5>` 局部样式标题）。
- **可访问名称与表单**：未发现孤立无关联 `input`（`orphaned_count = 0`）；但 `⚙️` / `🔄` 等纯图标按钮缺少 `aria-label` / `title`，存在 `1` 个无可见文本主按钮；`Tab` 键导航会落入非交互外层容器（`<main>` 及指数走廊条出现焦点框）。
- **触摸热区与对比度**：共 **35** 个可见交互控件高或宽 `< 40px`；CDP 检测到 **9** 处低对比度文本（`ratio < 4.5`），最显著为深色侧栏标签 **`账本与设置`** 呈暗色文字 `rgb(15, 23, 42)` 叠加深底 `rgb(15, 28, 46)`，对比度仅 **`1.04`**；主导航选中态金底白字对比度 **`2.71`**。
- **局部溢出与裁剪**：`390×844` 移动端页面总宽零溢出（`xOverflow = 0`），但上区副标题（`| 查看今`）、指数走廊最右卡片、领涨/跌第 3 颗胶囊及 667px 数据表格内部存在右侧裁剪；`1440×900` 下「极端承压」宽表最右列存在轻微右侧裁剪，Tab 3 `样本外前瞻` 表格下方出现一块空框边界容器。

---

## 四、G44 / G45 之后当前仍剩余的技术债清单

| 优先级 | 类别 | 现存技术债具体事实与数据 | 对后续客户端研发/维护的影响 |
| :---: | :--- | :--- | :--- |
| **P0** | G45 回归修补 | `lookthrough_analyzer.py` L913 / L1208 / L1702 漏绑 `SECTOR_FUND_SELECTION` | Tab 2「存量重塑」点击触发局部报错 |
| **P1** | 路径治理未收口 | `AGY2_FundAdvisory/` 24 个模块中仅 5 个已接入 `runtime_paths.py`；仍有大量原始 `data/` 字符串：`data_loader.py`（47 处）、`advisory_engine.py`（25 处）、`strategy_bridge.py`（12 处）、`multi_ledger_manager.py`（6 处）、`forward_audit_logger.py`/`shadow_portfolio_tracker.py`/`scenario_rebalancer.py`（各 2 处）、`portfolio_manager.py`（1 处） | PyInstaller/Android 打包启用 `AGY2_DATA_DIR` 后，未迁移模块会读写错误工作目录 |
| **P1** | 单体体积与延迟互导 | 仍存四大超大文件：`app_gui.py`（10,118 行，已冻结）、`strategy_bridge.py`（7,750 行，最长函数 687 行）、`advisory_engine.py`（5,105 行，`inspect_portfolio` 达 1,021 行）、`data_loader.py`（4,027 行）；模块顶层启动期循环已清零（`top_level_cycles = []`），但函数内延迟互导仍有 **12 对**（缺独立零依赖 `domain_models.py` 承载 `CORE_STRATEGY_POOL` 与 dataclass） | 长期维护认知负担偏高，多团队并行改动 `strategy_bridge` / `advisory_engine` 仍易冲突 |
| **P1** | 接口性能细节 | `GET /api/v1/watchlist` 耗时 **828.1 ms** | 客户端首页轮询若直连该接口会拖慢首屏体感 |
| **P2** | 宽泛异常捕获 | `AGY2_FundAdvisory/*.py` 合计仍有 **466 处** `except` 块 | 掩盖深层结构/数据源报错堆栈，排障困难 |
| **P2** | 脚本与杂项整洁度 | `scripts/` 顶层仍有 **227 个** `.py`（仅归档 28 个，其中旧 `verify_g26_valuation_vs_official_reconciliation.py` 仍断言已删 `rebal_cols_10`）；`verify_g43`/`g44`/`g45` 仍在 `scripts/` 与 `AGY2_FundAdvisory/scripts/` 双份并存；根目录另有未跟踪杂散 `test_dyn.py`（79 行）及 `data/test_brinson_pm.json` | 容易让新协作者误跑已废弃门禁或混淆测试脚本入口 |
| **P2** | Web UI 无障碍与窄屏细节 | `<html lang="en">`、`账本与设置` 对比度 `1.04`、图标按钮无 `aria-label`、390px 上区副标题/指数卡局部裁剪（若后续全面切换 Tauri/Capacitor 新前端，本项可在新端原生规避；仅维护老 Streamlit 运维台需择机微调） | 仅影响 Streamlit 过渡运维台无障碍评分与窄屏观感 |

---

## 五、外部审计包文件清单（`docs/g45_audit_bundle/` 及同级 `.zip`）

- `docs/g45_post_audit_verification_and_debt_report.md`（本终审报告全文）
- `docs/g45_audit_bundle/cdp_a11y_cookie_memory_api_metrics.json`（CDP 性能、内存 GC 快照、A11y、Cookie、FastAPI 实测全量遥测 JSON）
- `docs/g45_audit_bundle/static_tech_debt_inventory.json`（`AGY2_FundAdvisory/` 24 模块行数/复杂度/互导图/原始路径扫描 JSON）
- `docs/g45_audit_bundle/browser_live_screenshot.png`（实机 `/browser` 验证截图）
- `docs/g45_audit_bundle/ARCHITECTURE.md` 与 `docs/g45_audit_bundle/g43_pre_client_maintainability_audit.md`（架构导览与历史 G43 基准对比）
- `docs/AGY2_G45_External_Audit_Bundle.zip`（以上完整文件的一键打包归档文件）
