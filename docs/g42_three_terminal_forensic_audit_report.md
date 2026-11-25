# AGY2 (v5.21-G42) 三端实机性能、内存、安全与页面显示法证审计报告

> **审计声明**：本报告严格遵循**纯只读原则**完成（源码零修改，四大只读裁判文件 SHA256 校验 100% 未变更），通过 Chrome DevTools Protocol (CDP) 实机探针与独立 Browser 交互走查，从 **桌面网页端**、**手机端**、**电脑客户端 / 跨端 API** 三个真实运行视角采集实测数据。

---

## 一、三端实机总览与核心量化指标

| 探测维度 | 实测观测值 | 风险评级 | 关键瓶颈定位 |
| :--- | :--- | :---: | :--- |
| **桌面网页端** (`1440×900` & `1280×800`) | 首屏冷启动 `5,041.5 ms`（TTFB 3ms，WebSocket/脚本耗时 4.83s）；复盘切页最高 `>30s` / `14.3s`；诊断「投顾底稿」实测 `5.02s`（Browser 首次触发 `21s`） | **P0/P1** | Streamlit 每次点击触发整文件全量重跑 + 多处未隔离重算；客户端 JS Heap/DOM 节点存在累积滞留 |
| **客户端内存 & WebSocket** (CDP `Performance.getMetrics`) | 5 轮 4 Tab 切换循环后，GC 后 JS Heap `31.45 MB → 46.11 MB`（`+46.6%`）；**DOM 节点 `2,765 → 18,746`（GC 后仍滞留 6.8 倍）**；**事件监听器 `429 → 2,225`（GC 后滞留 5.2 倍）**；WebSocket 接收 **`6.50 MB` / 4,973 帧**；服务端 RSS `371.38 → 390.20 MB`（`+18.82 MB`） | **P1** | Streamlit 每次切换挂载/卸载大量组件与 `st.data_editor` / Plotly Canvas/SVG 及 iframe，触发前端 DOM 与 Listener 垃圾回收滞留及 WebSocket 大包增量推送 |
| **Cookie / 安全 / CORS** | Cookie 仅含 `_streamlit_xsrf`（`httpOnly: false`, `secure: false`, `sameSite: Lax`）；`localStorage`/`sessionStorage` 为空；控制台有 **22+ 条 iframe sandbox 安全警告** 与 **8 条 Permissions-Policy 警告**；`api_server.py` 存在 **`Access-Control-Allow-Origin: *`** | **P1** | `api_server.py` 通配符 `*` 放行任意网页跨域读写本地 `/api/v1/holdings` 与 `/api/v1/ledger/export`；内嵌 iframe 同源沙盒告警频发 |
| **手机端** (`390×844` 窄屏 & iPhone UA) | 真实 iPhone UA 首屏加载 `12,891.4 ms`；无移动 UA 的窄屏下**主导航完全消失**；持仓双栏强行并排、顶部副标题溢出至 `512px`、行情条溢出至 `470px`、复盘净值图标签严重重叠 | **P0** | Python 端 `_is_mobile_viewport()` 仅认 UA/URL 参数而不认窄屏视口；CSS 隐藏了侧边栏与展开按钮但未接管窄屏主导航 |
| **电脑客户端** (`api_server.py` & `.exe` 就绪度) | 无独立前端壳（`clients/` 目录尚不存在）；`api_server.py` 冷启动 `3,268.9 ms`，常驻 RSS **`311.79 MB`**；`/api/v1/overview` 首调耗时 **`3,378.5 ms`**、`/api/v1/sectors` **`918.5 ms`**、`/api/v1/rebalance` **`656.5 ms` (80.2 KB)** | **P1** | `import strategy_bridge` 耗时 `1,278.9 ms` + `get_latest_market_snapshot` `927.7 ms` + `calculate_intraday_pnl` `1,126.8 ms` 串行阻塞首帧接口 |

---

## 二、P0 级阻断性问题（直接崩溃或功能不可用）

### 1. 【诊断工作台 -> 重仓重叠 / 极端承压】`_h_items` 作用域缺失引发 Python 运行时崩溃
- **代码铁证**：`AGY2_FundAdvisory/app_gui.py:L9307` 将 `_h_items = tuple(sorted(...))` 定义在 `if active_subview == "资产敞口":` 分支内部，但 `L9518`（`重仓重叠`）与 `L9672`/`L9681`（`极端承压`）直接调用 `_cached_stock_overlap(_h_items)`、`_cached_penetration_risk(_h_items)` 与 `_cached_stocks_df(_h_items)`。
- **实机表现**：切入「重仓重叠」底部及「极端承压」时直接抛出红框异常：
  `Tab 4 穿透工具箱渲染异常: cannot access local variable '_h_items' where it is not associated with a value`。

### 2. 【手机端 & 窄屏桌面浏览器】主工作台导航彻底失联 + 布局双栏挤死
- **代码铁证**：
  - `AGY2_FundAdvisory/app_gui.py:L265-L285` 中 `_is_mobile_viewport()` 仅根据 `User-Agent`、`?view=mobile` 或 `session_state` 判断，**无法感知浏览器实际视口宽度 `<= 768px`**；
  - 当用户在手机桌面模式、平板分屏或桌面端将浏览器拖窄至 `390×844` 时，CSS `@media (max-width: 768px)` 在 `L1200-L1212` 强制隐藏了 `[data-testid="stSidebar"]` 与 `[data-testid="stExpandSidebarButton"]`，而 Python 端 `L5112` 的 `if _is_mobile_viewport():` 返回 `False` 未渲染移动分段导航 `rad_mobile_main_nav_tab`。
- **实机表现**：CDP 探针实测 `sidebarVisible: false` 且 `allTabsCount: 0`（无任何工作台切换入口）；Browser 实机同样测得 `sidebarVis: false, expandVis: false`，且持仓页仍按桌面 `st.columns([7.0, 3.0])` 并排挤压成两列约 `175px` 窄条，导致 7 列主表仅露一列半、底部按钮被挤成 `84.5px` 截断为 `删除...`，右栏「今日操作路线」与下方「影子账本」折叠框上下压盖。

### 3. 【复盘工作台 -> 近三年胜率】分段失效且引发 14.3s~30s+ 超级卡顿
- **代码铁证**：`AGY2_FundAdvisory/app_gui.py:L8273-L8530` 中 `bt_view` 仅对 `"样本外前瞻"` 和 `"影子账本"` 做了早退 `return`，**`"历史时光机"` 与 `"近三年胜率"` 之间没有任何 `if bt_view == ...` 条件隔离**。
- **实机表现**：无论停留在「历史时光机」还是点击「近三年胜率」，都会把「历史时光机回测 + 净值曲线 + 交易摩擦账单 + 近三年 18 期滚动回测表 + 29基 vs 6基全周期回测（`bt_mode`）」**全量同时算完并平铺输出**，导致切入复盘首次等待超 `30s`、切换「近三年胜率」卡死 `14.3s` 且页面内容几乎完全重复。

---

## 三、P1 级重要性能、内存、安全与显示缺陷

### 1. 网页端显示与交互问题（`1440×900` / `1280×800`）
- **「首席投顾今日裁决台」第 5 胶囊文字冲出红框边界**：`AGY2_FundAdvisory/app_gui.py:L680-L688` 在 5 等分 `grid` 的约 220px 窄卡内对标题行设了 `white-space: nowrap;`，导致 `🎯 今日行动准则` 与右侧红色徽章文案碰撞并冲出容器右侧边界；展开「投研风控」后 3 张机会雷达卡也出现 `今日 +0.3...` 及 6 位基金代码被腰斩。
- **复盘「样本外前瞻」表泄露未清洗的原始英文列名**：`forward_audit_logger.evaluate_forward_performance()` 返回字典同时包含中文键与原始英文键（`date`、`days_elapsed`、`horizon_bucket`、`eval_status`、`portfolio_return_pct`、`benchmark_return_pct`、`excess_alpha_pct`），`L8296` 直接传给 `st.dataframe`，导致表格出现中英文双份冗余列且右侧被裁切。
- **复盘「历史时光机」双列图表垂直不齐**：左右两列说明框一个 3 行、一个 2 行，导致下方「动态回撤对比」与「资产仓位变迁」顶边错位；「资产仓位变迁」Y 轴因顶部图例留空向上拉超 100%；下方 11 列战报宽表右侧溢出需横向滚动。
- **诊断「资产敞口」行业图拥挤抽稀 & 「投顾底稿」跨端套利表宽度截断**：行业暴露图强行塞入 25+ 行业导致 Y 轴标签间隔隐藏近半；「投顾底稿」首次切入耗时 `5.02s ~ 21s`（实测 `513500` 标普500 溢价 `+11.54%`，且部分标的折溢价表最右列「实操建议」被裁切）。
- **笔记本视口（`1280×800`）右缘轻微溢出**：CDP 实测 `viewport_right_overflow` 3 处达 `1290px`（`+10px`），侧边栏此时保持 `800 <= 800` 零滚动。

### 2. 手机端（`390×844`）显示与适配问题
- **全页面多处向右溢出视口**：即使在真实 iPhone UA 下，CDP 实测仍有 **17 处元素右侧超出 `390px`**：顶栏副标题 `｜ 查看今日盈亏、核对估值与体检风险` 伸至 `512px`，指数条 `中证红利 5,446.28 -0.03%` 伸至 `470px`，领涨胶囊 `▲ 华夏上证 +1.65%` 伸至 `399px`，部分卡片内框伸至 `491px`。
- **复盘净值曲线标注密集踩踏**：实机截图可见「2018-2026 全周期累计净值对比」上方牛熊文字标注在 390px 窄屏挤成黑团叠压，且纵向堆叠图例占去近半高度。
- **诊断页胶囊断词 & 指标卡贴死**：5 个分段胶囊被劈成两行断词（`风险体/检`、`资产敞/口`、`重仓重/叠`、`极端承/压`），3 个指标卡排成 `2 + 1` 且上下间距为 0 贴死。

### 3. 内存、WebSocket 与 Cookie/CORS 风险
- **前端内存 & DOM 节点累积滞留**：5 轮 Tab 循环并在 CDP 触发 `HeapProfiler.collectGarbage` 后，DOM 节点仍由 `2,765` 留存至 **`18,746`（6.8 倍）**，事件监听器由 `429` 留存至 **`2,225`（5.2 倍）**，JS Heap 从 `31.45 MB` 升至 `46.11 MB`（峰值 `161.28 MB`），主要源于 Streamlit 单页切 Tab 时前端组件/iframe/Plotly 实例频繁销毁重建但部分引用未即时释放，且产生 `6.50 MB` WebSocket 增量流量。
- **本地 API 通配符 CORS 风险**：`AGY2_FundAdvisory/api_server.py:L44-L49` 配置 `allow_origins=["*"]`。在电脑桌面端运行时，用户浏览器若访问任意第三方恶意网页，后者可通过本地 `fetch("http://127.0.0.1:8000/api/v1/ledger/export")` 或 `POST /api/v1/ledger/import` 窃取或篡改本地实盘账本。
- **桌面端冷启动慢与体量偏重**：独立 `api_server.py` 子进程尚未封装 `clients/` 原生桌面/移动前端壳；单后端子进程即占 `311.79 MB` 内存，冷启动 `3.27s`，`/api/v1/overview` 首调耗时 **`3,378.5 ms`**（分解实测：`import strategy_bridge` `1,278.9 ms` + `get_latest_market_snapshot` `927.7 ms` + `calculate_intraday_pnl` `1,126.8 ms`）。

---

## 四、P2 级细节一致性与交互抛光项

1. **命名与配色语义不统一**：侧边栏叫「诊断 · 深度穿透」，进入后主标题却叫「工具工作台」、胶囊标题叫「工具分段」；「外观」按钮 hover 文案提示可调涨跌红绿，但弹窗内只有主题风格下拉框。
2. **调仓工作台反馈与列名不统一**：「C转A省费」把可勾选 `已下单` 放在最左列，而「清理尾仓」「核心调仓」把非交互文本 `⏳ 待清/待办` 放在最右列；点击「复制小抄」后缺少 Toast 或展开反馈；「新钱定投」分配表缺少基金名称且金额小数位混排。
3. **持仓页按钮与文字微截断**：`领涨/领跌` 仅截前 4 字导致出现两个同名 `华夏上证`；`保存修改`/`导出CSV`/`删除标的` 在部分列宽下被挤成 `保存修...` / `删除...`；侧栏账本下拉框 `[实盘] 实战存量组合（29只` 文本被截断。
4. **控制台安全告警噪声**：Streamlit 运行时累计产生 22+ 条 `allow-scripts` + `allow-same-origin` iframe 沙盒逃逸告警与 8 条过时 Permissions-Policy 告警。

---

## 五、分优先级改进路线图建议

1. **第一优先级（立刻止血 P0）**：
   - 将 `_h_items` 提取到 `render_tab4_toolbox_content` 顶部公共作用域（消除「重仓重叠」「极端承压」的 `UnboundLocalError`）；
   - 为 `render_tab3_backtest_content` 的 `"历史时光机"` 与 `"近三年胜率"` 补齐严格 `if bt_view == ...` 视图隔离与子视图懒加载（单页响应可从 `14~30s` 压降至 `1s` 内）；
   - 窄屏响应式统一：将移动端导航（顶部 4 Tab 或汉堡菜单）与双栏堆叠改为 **CSS 媒体查询 + 窄屏兜底**（不再仅依赖 User-Agent），确保 `<= 768px` 下必有可用主导航且严禁双栏硬挤。
2. **第二优先级（性能与视觉精修 P1）**：
   - 修复「首席投顾今日裁决台」第 5 胶囊文字溢出、`forward_audit_logger` 过滤英文重复列、移动端 Plotly 净值图隐藏过密牛熊注释与底部紧凑图例；
   - 优化 `api_server.py` 首帧：模块级预热 + 异步并发拉取 `snapshot` 与 `calculate_intraday_pnl()`，并将 `allow_origins` 收紧为本地信任源（如 `tauri://localhost`, `http://localhost:*`, `capacitor://localhost`）。
3. **第三优先级（跨端工程演进）**：
   - 按 G42 规划推进独立轻量化 React + Tauri（`.exe`）/ Capacitor（`.apk`）前端，从根源替代 Streamlit 的整页重跑与 DOM 滞留模式。
