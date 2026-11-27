# Changelog

## [v2.3.0] - 2026-11-28

### Phase 2：中国场外公募「赚钱 + 保收益」实操闭环与私人银行级 WebUI 美化
- **四大核心赚钱与守收益工作流引擎（`AGY2_FundAdvisory/phase2_workflow_engine.py` + `api_server.py`）**：
  - **智能分批建仓向导（`POST /api/v1/plan/staged_entry` + `StagedEntryModal.tsx`）**：按计划投入资金、当前宏观温度与估值位置生成 3~6 期分批建仓节奏、每期触发阈值与分标的金额明细；
  - **14:30 截单速览条（`GET /api/v1/trading/cutoff_brief`）**：紧贴中国场外公募 T 日 15:00 申赎截单规则，在市场与信号/调仓执行页直观呈现当日动作、7 天免罚红线与 T+1/T+2 确认日历；
  - **持仓级三阶移动止盈雷达（集成至 `/api/v1/holdings` + `HoldingsPage.tsx`）**：逐只追踪持仓收益率与高点回撤，按「浮盈达标 / 回撤预警 / 分批落袋」三阶触发止盈守护，防范“坐过山车”；
  - **精确 XIRR 资金加权年化收益与私有现金流账本（`GET/POST/DELETE /api/v1/ledger/cashflows` + `CashflowModal.tsx`）**：支持按账本独立记录申购/赎回/分红流水（`data/cashflows_*.json` 本地私有、`.gitignore` 隔离），牛顿法精确求解个人真实 XIRR。
- **全站私人银行级制度化视觉打磨（`web/src/index.css` + 4 大页面与组件）**：
  - 统一温润画布 `#F4F7FB`、无单位行高、`rem` 流式 KPI 字号、`color-mix(in oklab, ...)` 语义高亮、`forced-colors` 无障碍回退与原生 `<dialog>` 弹窗交互；
  - 量化实验室矩阵表合并配比/建议金额列，实测 `1440×900` 桌面端 `0px` 横向滚动条、`390×844` 移动端零页面溢出；优化顶栏账本选择器宽度与 ECharts 拥挤度四象限坐标轴间距，彻底消除标签重叠。
- **测试与 CI 升级**：
  - 新增 `tests/test_phase2_money_making_workflow.py`（5 项全覆盖），并接入 `.github/workflows/ci-quality-gate.yml`；全量回归 **41/41 PASS**，GitHub Actions 前端构建与后端量化门禁双绿通过。

## [v2.2.0] - 2026-11-27

### Phase 1：中国场外公募量化底座加固、真 Walk-Forward 样本外验证与云端每日数据管道
- **中国场外公募主数据与 13 大类净值湖仓净化**：
  - 引入 `data/master/fund_catalog.parquet` 与 `data/master/fund_trading_rules.parquet`，将场外基金精细划分为 13 个资产风格桶（新增独立 `short_bond` 短债盾）；
  - 全链路剔除锁定期/持有期封闭基、仅场内 ETF、挂羊头卖狗肉伪海外与伪黄金基金，清洗出 269 只纯净场外真复权净值湖仓，确保买入建议 100% 可在银行/支付宝/天天基金直接申购。
- **严格样本外防泄漏与宏观择时内核对齐**：
  - `winrate_engine.py` 实现严格 70/30 样本外切分与真 Walk-Forward 滚动盲测，彻底隔离样本内调参与样本外绩效评估；
  - `advisory_engine.py`、`goal_driven_selector.py` 与 `portfolio_optimizer.py` 对齐宏观信号内核，新增熊市左尾降仓阻尼与 A/C 类份额申赎费率真实映射。
- **GitHub Actions 云端每日公开数据管道与国内免代理同步**：
  - 新增 `.github/workflows/daily-market-data.yml` 与 `scripts/build_daily_public_bundle.py`，工作日盘后自动构建全量与移动端紧凑二进制数据包，通过量化防泄漏门禁后发布至 `data-latest` Release；
  - 新增 `AGY2_FundAdvisory/remote_bundle_sync.py` 支持国内免代理镜像拉取与 SHA256 校验，并同步更新 `Dockerfile` 预置 `seed_data/master/`；新增 `tests/test_phase1_quant_integrity.py`（11 项全通过）。

## [v2.1.2] - 2026-11-27

### AkShare 1.20+ 全量双版本兼容、无种子容灾重建与 Docker 官方化
- **新增 AkShare 跨版本兼容层（`AGY2_FundAdvisory/akshare_compat.py`）**：
  - 一次性兼容 AkShare `1.14~1.19` 与 `1.20.41~1.20.70+` 的全部 **7 处更名/重构接口**：`index_hist_csindex`（原 `stock_zh_index_hist_csindex`）、`index_value_csindex`（原 `stock_zh_index_value_csindex`）、`index_zh_daily_em`（原 `stock_zh_index_daily_em`）、`index_zh_spot_em`（原 `stock_zh_index_spot_em`，默认查 `沪深重要指数`）、`calendar_trade_date_hist_sina`（原 `tool_trade_date_hist_sina`）、`bond_zh_us_yield_em`（原 `bond_zh_us_rate`）与单基历史净值 `fund_open_fund_info_em`（修复 `market_screener.py` 对 `fund_open_fund_daily_em` 的参数失配）；
  - 彻底根治新机器/容器按 `requirements.txt` 安装新版 AkShare（如 `1.20.70`）后触发 `AttributeError` 导致 6 个核心接口返回 HTTP 500 的问题；并在 `akshare_compat.py`、`trading_calendar.py`、`strategy_bridge.py` 补充进程级并发锁，根治空卷冷启动多线程同时初始化 `py_mini_racer` (V8) 触发 `IsConfigurablePoolInitialized` 崩溃的隐患。
- **彻底解除私有中间表硬依赖 & 引入启动种子自举（Docker 持久化卷免疫）**：
  - `data_loader.py` 的 `_build_matrix_from_source()` 不再硬读 5 个未入库私有中间 Parquet（`000688.SH.parquet`、`399006.SZ.parquet`、`AU9999.SGE.parquet`、`global_indices.parquet`、`fx_rates.parquet`），本地缺失时自动通过公开接口（`sh000688` + `sz399006`、`Au99.99`/`518880`、`513500`）在线重建完整 2018-至今全收益矩阵；
  - `runtime_paths.py` 新增 `AGY2_SEED_DIR` 与幂等原子自举函数 `bootstrap_public_seeds()`，`market_lakehouse.py` 与 `strategy_bridge.py` 全面切换至动态路径解析；
  - 仓库正式内置官方多阶段 `Dockerfile`、`docker-compose.yml`、`.dockerignore`，将 7 个公开市场基准种子预置至镜像只读目录 `/app/seed_data`，彻底杜绝宿主机空白 `- ./data:/app/data` 挂载卷遮盖种子文件，并补齐 `requirements-api.txt` 与 `pyproject.toml` 依赖清单。
- **后端容灾降级与前端边界打磨**：
  - `api_server.py` 根路由 `/` 正式支持 `GET` 与 `HEAD`（消除反向代理/探针 `405 Method Not Allowed` 日志刷屏）；`/api/v1/overview` 在极端无网+空卷故障下优先返回实时指数并输出显式 `DEGRADED` 状态而非 HTTP 500；
  - `QuantLabPage.tsx` 在求解无结果（`0 只`）时不再误显示 `权重 100.0%`，`TopBar.tsx` 补齐总览加载失败后的常驻重试指示；
  - 新增持久化回归测试套件 `tests/test_akshare_compat_and_seed_bootstrap.py`，全链路实测模拟 AkShare 1.20.70 严格模块、空 `AGY2_DATA_DIR` 种子自举与无私有文件在线重建。

## [v2.1.1] - 2026-11-27

### 初次部署加固与专业量化口径一致性修复
- **初次部署与跨平台依赖完整补齐**：
  - `requirements.txt` 补齐 `fastapi`、`uvicorn`、`python-multipart`、`pyarrow`、`akshare`、`pypinyin`、`Pillow`，并为 `pywin32` / `pefile` 添加 `; sys_platform == "win32"` 平台约束，解决干净机器及 macOS/Linux 安装报错与拼音检索缺包问题；
  - `api_server.py` 根路由在 `web/dist` 未编译时返回中文构建指引页（替代裸 `{"detail":"Not Found"}`）；
  - `start-agy2-web.vbs` 改用纯 ASCII 注释并自动探测 `py -3` / `python`，同时清除遗留 `launch_gui.vbs` 与 `start_silent_service.vbs` 中的个人本机路径硬编码。
- **宏观定调全链路仲裁与全天候风格桶分散加固**：
  - `api_server.py` 提取 `_arbitrate_market_verdict(snap)` 统一仲裁技术均线与十维量化投票，消除顶部/总览与蓝图/报告中“均线报深度大熊市 vs 十维投票 6多1空”自相矛盾问题，全接口一致输出 `左侧筑底分歧 / 均衡分批布局` 及完整 `vote_summary`；
  - `goal_driven_selector.py` 升级 `_enforce_exact_fund_bounds`，新增分档纯债固收总权重下限（`C1: 48%` ~ `C5: 5%`）与非债单一风格桶总上限（`C1: 25%` ~ `C5: 56%`），使 `C3 均衡 · 全天候 (ERC)` 单一风格桶集中度由 `69.3%` 降至 `42.0%`、纯债底仓由 `11.2%` 升至 `31.0%`、单基最大 PCR 由 `51.5%` 降至 `42.8%`。
- **数据透明度与专业交互细节完善**：
  - `scenario_rebalancer.py` 与 `/api/v1/tools/etf_premiums` 彻底移除离线兜底中的伪实时 `datetime.now()`，改用真实文件 `mtime` 或标明 `"离线参考样本"` 并透传 `is_offline_snapshot` / `snapshot_timestamp` / `source_label`，前端「热门场内 ETF 溢价预警」卡片头部显式渲染琥珀色离线快照徽章；
  - `WorkbenchContext.tsx` 解除初始 `activeLedgerId='combat_29_funds'` 硬编码，并在 `HoldingsPage.tsx`、`MarketSignalPage.tsx`、`RebalancePage.tsx` 补齐未就绪守卫（消除首屏重复请求）与调仓页空账本专业引导态；
  - `RebalancePage.tsx` 针对「稳健低换手」模式下达标率小幅收敛补充专业归因条与一键切换「对齐实验室方案」入口；
  - `QuantLabPage.tsx` 矩阵表与 `BacktestCharts.tsx` 资金占比 vs PCR 分组柱状图均针对负 PCR 纯债标的增加翠绿高亮与「负相关对冲」语义注解。

## [v2.1.0] - 2026-11-27

### 机构级投研工作台重构（宽屏顶栏 × 实验室可折叠分栏 × 可操控量化终端）
- **一级信息架构彻底重构（4 大互斥工作区 + 34px 实盘状态 Ticker）**：
  - 全新 `48px` 极简深海墨蓝顶栏 + `34px` 实盘状态 Ticker 带（宏观定调、沪深300/科创50/中证红利、本地真净值湖仓与盘后安全日更），彻底取代旧首页占 1/3 屏高的大块广告牌英雄区与 6 屏无限瀑布流；
  - 拆分为 **量化实验室（默认首屏）**、**市场与信号**、**实盘与风控**、**调仓执行** 4 大纯粹工作区，正式移除原 `448px` 垃圾桶式 `ProAnalysisDrawer`，将十维量化投票矩阵、场内 ETF 溢价预警（吸顶限高滚动表）、底层重仓股交叉重叠穿透、A/C 类份额费率精算器全部按专业投研工作流无损归位。
- **从“静态报表”进化为“可操控量化终端”**：
  - **单基排除 / 锁定全链路闭环**：`goal_driven_selector.py` 与 `api_server.py` 五大端点（`/quant/solve`、`/recommend/blueprint`、`/charts/backtest_curves`、`/charts/scenario_backtest`、`/rebalance`）全面透传 `exclude_codes` / `include_codes` 及缓存键，彻底杜绝下游“幽灵复活”；内置前置大类约束冲突校验与 `index_only` 自动解绑主动基金锁定提示；
  - **高密度组合配置矩阵表**：替代旧版 6 张臃肿卡片，支持按权重/PCR/量化分/MA20乖离排序，直接透传单基真实 `MA20乖离/短线温度`，支持行内一键「锁定 / 排除」立即全市场重算；
  - **A/B 多方案公平对比与投研报告导出**：新增 `SnapshotCompareView`（`localStorage` 持久化最多 4 组方案），强制绑定湖仓截止日与固定「近 1 年 + 全周期」双口径指标（`benchmark_horizons`）防错窗对比，提供标的权重 & PCR 横向 Diff 矩阵及过期快照一键重算刷新；支持一键导出 Markdown 投研报告与结构化 JSON。
- **机构级视觉净化与零原生弹窗交互层**：
  - 清零全站彩虹渐变 KPI 卡、6 色左竖杠、三层叠罗汉异色横幅与常驻 `ChartReadingGuide` 新手教学框，全站统一底线式 Underline Sub-Tabs 与 `?` 专业口径审计浮卡（`MetricTooltip`）；
  - 新增右侧 `520px` 浮层 **Fund Inspector 检查器**（不跳页、不挤压主图表，展示配权公式、精准近 1 年走势、十大重仓与锁定/排除快捷控制，支持一键展开全屏 5 维档案）；
  - 新增统一 **数据与账本中心**（`DataCenterModal`）与自定义 **确认弹窗**（`ConfirmDialog`），文本粘贴与离线 OCR 均先走预览核对表（支持改金额、删误识别行后经 `POST /api/v1/import/commit` 所见即所写落盘），全站彻底清零 `window.prompt / confirm / alert`；
  - 新增 `Ctrl/Cmd + K` **全局命令与全市场基金检索面板**（`CommandPalette`），并通过 `WorkbenchContext` 懒加载保活机制保障跨 Tab 切换零重载、后台求解不中断。
- **质量与三端验证**：
  - 新增 `tests/test_institutional_workbench_api.py`，全套核心回归 **27/27 PASSED**，四大只读裁判文件 SHA256 100% 校验一致；
  - 升级 `scripts/verify_route1_web_six_dim.py` 覆盖单基排除重算、A/B 双方案对比、检查器、数据中心核对表与三端视口（`1440×900` / `1280×800` / `390×844` 均 `0px` 水平溢出，`0` 控制台/网络报错）。

## [v2.0.3] - 2026-11-26

### 全新机器零配置开箱即用热修复
- **彻底解除遗留 `src.parsers.calendar_parser` 依赖**：新增零外部依赖的自包含交易日历模块 `AGY2_FundAdvisory/trading_calendar.py`，并切换 `data_loader.py` 与 `trading_clock_fee.py` 引用，根治新机器部署时因缺失旧 `/src/` 目录导致的 `'CalendarParser' object has no attribute 'get_trade_days'` 崩溃及首页信号加载卡死问题。
- **随仓附带纯公开市场基准种子数据（~4.9 MB，0 个人隐私数据）**：在 `.gitignore` 中精准白名单放行 7 个公开市场指数与 266 只公募基金复权净值基准文件（`aligned_matrix_total_return.parquet`、`market_elite_nav_matrix.parquet`、`market_elite_meta.parquet`、`market_elite_sync_status.json`、`bond_zh_us_rate.parquet`、`chinabond_yield_curve.parquet`、`index_valuations.parquet`），新机器 `git clone` 后首秒即具备完整十维宏观定调与 266 只真净值湖仓，且所有个人账本/持仓继续 100% 隔离不入库。

## [v2.0.2] - 2026-11-26

### 全市场 28,177 只离线真净值湖仓、极端周期修复引擎与全站图表真联动
- **全市场 28,177 只离线漏斗与防封禁真净值湖仓（`market_lakehouse.py` / `scripts/sync_market_lakehouse.py`）**：
  - 彻底打破固定 12 只基金池限制，从全市场 28,177 只基金经合规初筛、10 大风格桶均衡配额、静态 CDN 断点续传与熔断保护（2 并发 + 随机抖动），提取红利再投资真复权净值（`Data_netWorthTrend.equityReturn`）与单基真实规模（`Data_fluctuationScale`）构建本地精英真净值湖仓；
  - 支持盘后防封禁超轻量增量日更（`FundMNFInfo` 50 只/批，仅需 6~8 次请求，< 1 秒，内置 30 分钟冷却），并提供离线 Wind CSV/Parquet 导入工具（`scripts/import_wind_nav_lakehouse.py`）。
- **真全市场目标驱动求解器与跨周期防偏差引擎（`goal_driven_selector.py`）**：
  - 支持「全市场量化海选（主动精选 + 指增 + 固收+ + 纯债 + QDII + 黄金）」与「仅指数/宽基低费池（0 主动基金）」双模式切换；
  - 统一 1,200 交易日跨周期公平评估窗口（穿越 2022 熊市与 2024 反转，根治 2023 熊底新发基幸存者偏差）+ Pairwise 相关性去冗余（`|corr| <= 0.82`）+ `WinRateOptimizer`（SLSQP/HRP/CVaR/半凯利与局部换基）+ 盒式单基/大类双红线投影；
  - 新增异步 4 阶段实时进度求解接口（`POST /api/v1/quant/solve` + `GET /api/v1/quant/solve/{job_id}`），前端显式「启动全市场量化求解」CTA、脏参数提醒与全市场选基漏斗条；
  - 主回测曲线与双万次蒙特卡洛 100% 采用终选基金自身真实复权净值（绝不静默退化为沪深 300 替身），并输出目标收益 vs 历史回测偏差归因卡。
- **极端行情修复天数、完整周期与三阶量化止盈引擎（`extreme_cycle_analyzer.py` + `ExtremeCyclePanel.tsx`）**：
  - 两阶段无偏 10,000 次蒙特卡洛预计极端修复天数（谷底回本 / 高点回本 / P50 / P75 / P90 vs 沪深 300）+ 历史四大极端行情真实修复天数表（早于共同成立日事件明文标注「同风格基准参考」）；
  - 全历史「高点 → 低点 → 回本 → 下一轮高点」完整周期时长与收益拆解 + 三阶动态止盈锚点与当下宏观周期定位。
- **全站图表真联动与跨页调仓升级（方案 A 全链路闭环）**：
  - 根治全市场新基金 `MA20 乖离 +0.0%` 盲区：`lookthrough_analyzer.py` 优先基于本地真净值湖仓实算每只基金真实近 20 日涨跌与乖离；拥挤度象限默认联动当前推荐方案标的并支持一键切回当前账本持仓；
  - 「历史情景回测」彻底联动当前全市场求解权重与真实复权净值（早于共同成立日透明衔接 10 桶基准并展示顶部提示）；
  - 「累计净值对比」板块第 3 张图升级为「资金占比 vs 真实风险贡献 (PCR)」分组柱状图；
  - 「调仓参考方案」目标收益升级为 `2%~60%` 自由数字输入、动态承接真实风险档位，并新增「稳健低换手（平滑调优·默认）」与「对齐首页全市场方案」双目标模式切换。
- **工程与测试加固**：
  - 修复 `.gitignore` 未锚定 `src/` 导致 Tailwind CSS v4 扫描遗漏的问题；
  - 新增 `test_goal_optimizer_and_extreme_cycles.py`、`test_full_market_lakehouse_and_solver.py`、`test_full_linkage_plan_a.py`，核心回归 25/25 全部通过，4 个只读裁判文件 SHA256 100% 校验一致。

## [v2.0.0] - 2026-11-25

### Major Architecture & Product Upgrade
- **全新现代 Web 前端（React 19 + TypeScript + Tailwind CSS + ECharts）**：
  - 彻底重构信息架构为极简顶栏 + 三大主工作台（「今日信号与选基」「我的持仓与体检」「调仓参考方案」）+「专业分析」右侧工具抽屉；
  - 采用私人银行深海墨蓝与冷雾灰三层视觉体系，首屏加载 `< 1s`，桌面（1440px）与移动端（390px）全页 0 水平溢出；
  - 支持 FastAPI 单端口（`127.0.0.1:8000`）一体化静态托管与 Windows 无黑框一键启动器 `start-agy2-web.vbs`。
- **目标驱动 × 基金详情多因子量化决策引擎（`goal_driven_selector.py`）**：
  - 支持用户设定「目标时间区间（6个月 / 1年 / 2年 / 3年）× 目标收益率（%）」，实算全历史滚动达标概率、中位收益、P05 最差情景与风险-收益碰撞提醒；
  - 并发采集基金详情真数据（夏普、卡玛、最大回撤、波动率、净值新高率、信息比率、跟踪误差、规模、费率、经理稳定性），输出 0~100 多因子得分并对配置权重实施因子倾斜优化；
  - 调仓参考页同步对比「调仓前当前持仓 vs 调仓后目标组合」的目标达标概率变化。
- **10 维度基金深度详情工作台（`fund_detail_service.py` + `FundDetailPage.tsx`）**：
  - 全站任意基金卡片/表格行一键点击进入，涵盖：业绩走势图、单位/累计净值图、历史业绩表、历史净值表、自定义金额定投测算表、4 大类 + 8 小类量化分析指标与雷达图、持仓资产/行业/前十大重仓股、现任与历任基金经理、基金档案与产品概要、交易规则与阶梯费率、最新官方公告。
- **多周期实时联动回测与历史情景回测**：
  - 首页成绩单与净值/回撤曲线支持 `近3个月 / 近6个月 / 近1年 / 近2年 / 全周期` 切换，并与所选量化模型、风险档位、基金只数实时联动；
  - 新增「历史情景回测」（`2021-02 核心资产高位` / `2022-04 底部反弹期` / `2024-09 政策转向期` / `近 1 年区间` 及自定义起点）。
- **10 项老版本高价值功能补齐与专业直白命名统一**：
  - 补齐净值对账、行内编辑份额/成本、CSV 导出、调仓效果追踪、极端行情压力测试、大额限购分批买入计划、基金分红方式建议、自选检索增删、A/C 费率对比器与热门场内 ETF 溢价预警。
- **Clean Layering 技术债收口与隐私脱敏**：
  - 新增 Layer-0 零依赖 `domain_models.py`，全面接入 `runtime_paths.py`，修复写入后缓存脏读、C转A硬编码、勾选持久化与新钱定投字段对齐；
  - 从公开仓库彻底移除个人持仓账本、历史快照与含持仓截图，强化 `.gitignore` 隐私保护。

## [v1.0.7] - 2026-11-19
- 官方净值与盘中双轨对账、秒级批量湖仓引擎、实战组合自洽重塑与三层渐进式终端。
