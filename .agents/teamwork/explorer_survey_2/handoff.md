# AGY2_FundAdvisory 现有架构、测试套件与只读底座综合调查报告 (Handoff Report)

- **调查员**: Explorer 2 (AGY2 Architecture Explorer)
- **调查时间**: 2026-10-29T09:15:00Z
- **工作目录**: `d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_2`
- **对标任务**: ORIGINAL_REQUEST.md (R1~R4) 进阶金融能力全面接入调研

---

## 1. Observation (客观事实与直接观测)

### 1.1 核心业务代码模块结构

#### (1) `portfolio_manager.py` (共 3,816 行，175 KB)
- **候选基金池 (Tab 1) 与选基漏斗**:
  - `SECTOR_FUND_SELECTION` (行 263-354): 定义了 5 大核心赛道（`CORE_DIVIDEND` 高股息红利、`BOND_SHIELD` 纯债固收、`GOLD_HEDGE` 黄金对冲、`TECH_GROWTH` 硬科技成长、`GLOBAL_HEDGE` 海外跨市场），每个赛道包含 1 只金牌标的（`champion_code`）与 3 只备选标的（`top_alternatives`）。金牌标的依次为：`100032` (富国中证红利指数增强A)、`002351` (易方达裕祥回报债券A)、`000216` (华安易富黄金ETF联接A)、`011613` (华夏科创50ETF联接C)、`050025` (博时标普500ETF联接A)。
  - `get_fund_selection_funnel_stats()` (行 357-387): 读取本地 `data/master/fund_catalog.parquet` (行 362) 获取全市场基金数（28,177 只），构造四级筛选漏斗：全市场 28,177 只 ➔ 硬指标初筛（成立>3年/规模>2亿）6,850 只 ➔ 5大赛道精选 20 只入围池 ➔ 5 只最终金牌标的。
- **存量持仓诊断 (Tab 2) 与底层资产穿透**:
  - `FUND_LOOK_THROUGH_DATA` (行 690-775): 静态维护了 21 只典型公募基金的前十大重仓股（`top_stocks`，如中芯国际、海光信息、贵州茅台、中国神华等）及细分行业暴露百分比（`industries`）。
  - `_fetch_external_fund_holdings(fund_code)` (行 2492-2545): 针对非预设外部基金，双轨穿透：先查本地 SQLite 数据库表 `cached_fund_holdings`；若未命中，在保护沙箱中调用 `akshare.fund_portfolio_hold_em(symbol=code, date=year)` 在线获取最新前十大重仓股并入库缓存。
  - `calculate_look_through_industry_exposure()` (行 2446-2490): 对所有市值 > 0 的持仓按基金规模加权，输出组合在各行业的真实穿透暴露 DataFrame。
  - `calculate_stock_overlap_matrix()` (行 2547-2632): 提取组合内各持仓基金的前十大重仓股集合，计算两两之间的 Jaccard 重合度系数（$|S_1 \cap S_2| / |S_1 \cup S_2|$）；当重合度 $\ge 0.40$ 时触发高重合度假分散预警，并独立隔离待穿透的主动基。
  - FIFO 赎回核算与 7 天安全锁: `get_penalty_free_redeemable_shares` (行 2634-2650) 严格依据先进先出批次，仅对 `holding_days >= 7 and not safety_lock` 的份额释放免惩罚赎回。

#### (2) `strategy_bridge.py` (共 2,569 行，120 KB)
- **宏观指标、均线系统与 ERP 计算**:
  - `get_latest_market_snapshot(...)` (行 1025-1180):
    1. **沪深300 均线生命线**: 基于 `df['H00300']` 计算当前点位 `c300`、MA20、MA60、MA120 以及 120 日均线斜率 `m120_slope`，并结合实时点位估算 Bias20、Bias60 与突破变盘临界距离 `dist_to_m20_breakout`。
    2. **风格动量比拼 (60日)**: 计算科创50 (`STAR50_STITCH`) 与中证红利 (`H00922`) 的 60 日收益差 `diff_star_div`，判定科技成长或高股息占优。
    3. **大小盘结构温度 (60日)**: 计算中证500 (`H00905`) 与沪深300 (`H00300`) 的 60 日收益差 `diff_500_300`。
    4. **宏观股债性价比 (ERP)**: 读取 `data/macro/chinabond_yield_curve.parquet` 获取 10 年期中债国债收益率（最新截面 1.6258%），读取 `data/mart/index_valuations.parquet` 获取沪深300 PE-TTM（12.23倍），计算真实 ERP ($100 / \text{PE} - Y_{10Y} = 6.54\%$)，并在 `data/macro/bond_zh_us_rate.parquet` 历史序列上推导 ERP 历史分位数（81.9% 极高估值性价比分位）。
- **指数至基金代码映射与交易单生成**:
  - `INDEX_TO_FUND_MAP` (行 44-100): 将宏观资产指数映射为真实公募基金，常驻底仓（红利、纯债、黄金、标普）映射 A 类份额，波段进攻仓（科创50、中证1000）强制映射 C 类份额以规避短期赎回摩擦。
  - `generate_zero_start_blueprint` (行 500+) 与 `generate_ai_rebalance_orders` (行 1400+): 产生建仓小抄与智能调仓执行指令。

#### (3) `app_gui.py` (共 2,026 行，107 KB)
- **页面布局与端口规范**:
  - 启动配置 (行 58-63): `st.set_page_config(page_title="AGY2 智能投顾与实盘组合接管工作台", page_icon="🧭", layout="wide")`。
  - 端口 8501: `launch_gui.vbs` 与 `launch_gui.bat` 规范在本地 `127.0.0.1:8501` 监听，通过探测 `http://127.0.0.1:8501/_stcore/health` 进行健康检查，以 `CREATE_NO_WINDOW` 静默唤起 Streamlit 并通过 `msedge.exe --app=http://localhost:8501` 无边框独立应用模式呈现。
- **顶部状态栏 (Top Status Bar, 行 268-363)**:
  - 包含调仓网格倒计时与破位预警横幅。
  - 6 个核心指标卡片：
    - Col 1: 申赎时钟 (15:00 生死线倒计时)
    - Col 2: AI 策略大脑 (当前市场状态与持续交易日数)
    - Col 3: 沪深300实时行情与 MA20/MA60 偏离度
    - Col 4: 宏观股债性价比 (ERP 历史分位数与 10Y 国债)
    - Col 5: 今日预估浮盈亏
    - Col 6: 全组合总资产与现金/在途状态
- **核心 4 大工作区标签页 (Tabs, 行 419-424)**:
  - Tab 1: `🧭 AI 投顾大脑与今日建议`（含从0建仓场景一、存量持仓诊断场景二、4步推演进度、全市场量化选基透明漏斗与 5 张大字号人话指标卡片）
  - Tab 2: `📈 策略胜率、回测与风控档案`（回测净值曲线、水下回撤、风格切片评估、DSR 门槛记录）
  - Tab 3: `💼 我的持仓账本与接管向导`（持仓明细、FIFO 批次拆解、30层 Undo 恢复）
  - Tab 4: `🔍 组合穿透诊断、对账与工具箱`（资产大类条形图 `px.bar`、加权行业暴露 `px.bar`、重仓股重合度热力图 `px.imshow`、在途订单 T+1 对账、A/C 算费器、场内 ETF IOPV 监控）

---

### 1.2 测试套件架构与通过率核验

#### 现有测试用例清单与分布 (`AGY2_FundAdvisory/tests/`)
通过 `pytest --collect-only AGY2_FundAdvisory/tests` 及 `python -m pytest tests` 统计：
- `test_dynamic_risk_and_metrics.py`: 23 项测试（风险错配、人话指标、选基赛道画像等）
- `test_e2e_gui_render.py`: 8 项测试（端到端 GUI 渲染与组件完整性）
- `test_infra.py`: 15 项测试（数据对齐矩阵、T+1摩擦算子、因果探针、四岛接口、只读底座等）
- `test_live_rebalance_upgrades.py`: 12 项测试（动态调仓网格、尾盘变盘信号）
- `test_portfolio_manager.py`: 19 项测试（双模接管、FIFO队列、分红除权、Undo回滚等）
- `test_realtime_and_upgrades.py`: 11 项测试（盘中估值、时钟防抖、IOPV预警）
- `test_strategy_bridge.py`: 9 项测试（Trial 29 桥接、切片映射、回测时序）
- `test_trading_clock_fee.py`: 10 项测试（申赎时钟、A/C费率矩阵、惩罚费扣减）
- `test_ui_and_logic_refinements.py`: 5 项测试（选基漏斗统计、建仓小抄格式化）
- **测试总数**: **112 项测试**。

#### 测试运行命令与实测结果
- **执行命令**:
  ```powershell
  cd d:\Google\Workspace\Wind\AGY2_FundAdvisory
  python -m pytest tests
  ```
- **控制台输出记录**:
  ```text
  ============================= test session starts =============================
  platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0
  rootdir: D:\Google\Workspace\Wind
  configfile: pyproject.toml
  plugins: anyio-4.13.0, asyncio-1.4.0, cov-7.1.0
  collected 112 items

  tests\test_dynamic_risk_and_metrics.py .......................           [ 20%]
  tests\test_e2e_gui_render.py ........                                    [ 27%]
  tests\test_infra.py ...............                                      [ 41%]
  tests\test_live_rebalance_upgrades.py ............                       [ 51%]
  tests\test_portfolio_manager.py ...................                      [ 68%]
  tests\test_realtime_and_upgrades.py ...........                          [ 78%]
  tests\test_strategy_bridge.py .........                                  [ 86%]
  tests\test_trading_clock_fee.py ..........                               [ 95%]
  tests\test_ui_and_logic_refinements.py .....                             [100%]

  ============================ 112 passed in 36.13s =============================
  ```
- **实测通过率**: **100% (112/112 passed, 0 failed, 0 warning error)**。

---

### 1.3 只读底座与不可变量核验 (Read-Only Invariants)

#### 文件系统物理只读属性核验
通过 PowerShell 执行 `Get-ChildItem -Recurse AGY2_FundAdvisory | Where-Object { $_.IsReadOnly }` 检验：
| 关键文件路径 | IsReadOnly | Mode | Attributes | 说明 |
| :--- | :---: | :---: | :---: | :--- |
| `AGY2_FundAdvisory\AGENT_SPEC.md` | **True** | `-ar--` | `ReadOnly, Archive` | A股策略裁判与风格切片规范 |
| `AGY2_FundAdvisory\holdout_vault.py` | **True** | `-ar--` | `ReadOnly, Archive` | 盲测熔断锁 (上限3次) |
| `AGY2_FundAdvisory\judge_engine.py` | **True** | `-ar--` | `ReadOnly, Archive` | 铁血裁判防作弊引擎 |
| `AGY2_FundAdvisory\tests\test_infra.py` | **True** | `-ar--` | `ReadOnly, Archive` | 裁判基建单元测试集 |

#### 代码级防御机制与约束逻辑
1. **日历字面量静态 AST 锁 (`judge_engine.py:58-112`)**:
   `scan_ast_for_calendar_cheating` 解析策略函数 AST 语法树，凡出现 `'2018'`~`'2025'` 或 `YYYY-MM-DD` 形式的日历字符串常量，立即判定 `FATAL: Calendar Date Hardcoding Detected`。
2. **因果探针探漏 (`judge_engine.py` & `test_infra.py:55-71`)**:
   在 10 个随机截面点对比 $T$ 与 $T+20$ 权重输出，浮点绝对差 $> 10^{-7}$ 判定前瞻作弊。
3. **盲测金库额度熔断 (`holdout_vault.py:17-88`)**:
   在 `evolution.db` 中维护 `holdout_attempts` 计数器，达到 3 次强行抛出 `HoldoutVaultExhaustedError` 终止程序。
4. **本土纯度与防套利红线 (`AGENT_SPEC.md` & `test_infra.py:96-254`)**:
   - 黄金+美股外援仓位硬上限 $\le 20.0\%$（美股 $\le 10\%$）；
   - 本土 A 股权益平均仓位底线 $\ge 55.0\%$；
   - 纯债全周期平均仓位上限 $\le 50.0\%$；
   - 扣除 $Rf = 2.0\%$ 真实无风险利率；
   - CAGR 必须 $\ge 11.5\%$；
   - 牛市切片 Slice 2 收益 $\ge 38\%$，Slice 6 收益 $\ge 18\%$，跑输基准不超过 $-5\%$。

---

### 1.4 本地 DuckDB 时序湖仓与数据资产核验

#### 湖仓文件与架构
- **DuckDB 数据库文件**: `d:\Google\Workspace\Wind\data\storage.duckdb` (文件大小: 274,432 字节)。
- **Parquet 底层存储**: 共有 122 个 Parquet 时序文件分布在以下目录：
  - `data/processed/aligned_matrix_total_return.parquet` (全收益指针对齐矩阵，覆盖 2018-至今)
  - `data/master/fund_catalog.parquet` (全市场公募基金库，实测 28,177 行)
  - `data/macro/`: `open_market_operations.parquet`, `interbank_rates.parquet`, `chinabond_yield_curve.parquet`, `bond_zh_us_rate.parquet`, `margin_trading.parquet`, `money_supply.parquet`, `pmi.parquet`
  - `data/mart/`: `financial_risk_screen.parquet`, `earnings_forecast.parquet`, `lockup_calendar.parquet`, `pledge_risk.parquet`, `northbound_holdings.parquet`, `fund_heavyweight_stocks.parquet`, `dragon_tiger.parquet`, `shareholder_count.parquet`, `block_trading.parquet`, `index_valuations.parquet`
  - `data/derivatives/`: `futures_basis.parquet`, `option_volatility.parquet`

#### DuckDB 注册视图核验
经实测查询 `SHOW TABLES`，`storage.duckdb` 内已成功注册 **41 个核心 SQL 视图**，其中与本次升级直接相关的视图及其关键字段包括：
1. `v_financial_risk_screen`: `symbol`, `stock_name`, `goodwill_ratio_pct`, `ar_turnover_days`, `double_high_risk`, `risk_level`, `risk_reasons`
2. `v_pledge_risk`: `symbol`, `stock_name`, `pledge_ratio_controlling_pct`, `warning_close_line_status`, `risk_level`
3. `v_lockup_calendar`: `symbol`, `stock_name`, `unlock_date`, `days_to_unlock`, `unlock_ratio_total_pct`, `risk_level`
4. `v_open_market_operations`: `date`, `repo_7d_injection_billion`, `repo_7d_expiry_billion`, `repo_7d_net_billion`, `total_net_injection_billion`, `liquidity_stance` (最新记录至 2026-10-28)
5. `v_interbank_rates`: `date`, `dr007`, `policy_rate_7d`, `dr007_spread_bp`, `liquidity_status` (最新 DR007 1.389%, 政策利率 1.50%, 偏离度 -11.1 bp, 状态：流动性泛滥)
6. `v_northbound_holdings`: `symbol`, `stock_name`, `trade_date`, `change_1d_value_million`, `change_5d_value_million`, `float_ratio_pct`
7. `v_shareholder_count`: `symbol`, `stock_name`, `end_date`, `holder_change_pct`, `concentration_trend`
8. `v_dragon_tiger`: `symbol`, `stock_name`, `institution_net_million`, `top_buy_seats`, `top_sell_seats`

#### 并发只读与锁自愈机制 (`LakehouseManager.query_sql`)
- 默认采用 `duckdb.connect(str(self.db_path), read_only=True)` 进行并发读取；
- 若检测到多进程独占锁冲突（`Cannot open file`），具备 3 次防抖重试机制；
- 重试耗尽时，无缝切换至 `duckdb.connect(":memory:")` 纯内存实例，并基于本地 Parquet 路径动态执行 `_register_views_on_connection`，100% 保证离线降级与只读安全。

---

## 2. Logic Chain (推理链条与结论推导)

1. **前提 1 (R1 穿透排雷支撑点)**:
   - 观测到 `portfolio_manager.py` 已拥有 `FUND_LOOK_THROUGH_DATA` 与 `_fetch_external_fund_holdings` 获取重仓股列表；
   - 观测到 `WindToolkit.earnings_forecast` 与 `WindToolkit.holder_risk` 提供了 `screen_financial_risks(symbol)`、`fetch_pledge_risk(symbol)`、`fetch_lockup_calendar(days_ahead)`；
   - 观测到 `storage.duckdb` 中已有 `v_financial_risk_screen`、`v_pledge_risk`、`v_lockup_calendar` 离线底表。
   - **推论 1**: 可以在 `portfolio_manager.py` 与 `strategy_bridge.py` 中无缝引入重仓股穿透排雷方法，依次对前十大重仓股匹配商誉（>30%）、存贷双高、质押爆仓线与未来解禁天数，产出组合穿透风险评分与三色标签（🟢/🟡/🔴）。

2. **前提 2 (R2 宏观流动性温度计支撑点)**:
   - 观测到 `app_gui.py:288-363` 顶部状态栏由 6 个卡片构成（申赎时钟、AI大脑、沪深300、ERP、当日盈亏、总资产）；
   - 观测到 `strategy_bridge.py:1025-1180` 中 `get_latest_market_snapshot` 集中计算均线、动量、结构与 ERP；
   - 观测到 `WindToolkit.macro_liquidity` 提供了 `get_liquidity_thermometer()`，返回 DR007、7D OMO 利率、利差 bp、流动性状态与 7 日净投放。
   - **推论 2**: 在 `strategy_bridge.py` 中将 `get_liquidity_thermometer()` 结果整合进 `snapshot`，在 `app_gui.py` 顶部状态栏将宏观卡片或状态栏横幅升级为“宏观流动性温度计”，并同 ERP、MA20 形成股债三维雷达。

3. **前提 3 (R3 聪明钱与抱团拥挤度支撑点)**:
   - 观测到 `portfolio_manager.py:263-354` 包含 5 大赛道金牌与候选标的；
   - 观测到 `WindToolkit.institutional_holdings` 与 `WindToolkit.chips_market` 提供了北向持股近 1 日/5 日变动（`v_northbound_holdings`）与股东户数变动（`v_shareholder_count`）；
   - **推论 3**: 在选基推荐理由或持仓诊断详情卡片中，对候选/持仓标的的前十大重仓股聚合北向资金变动与股东户数变化率，生成拥挤度指标与抱团松动预警。

4. **前提 4 (R4 零回归与只读底座支撑点)**:
   - 观测到现有 112 项测试在 `AGY2_FundAdvisory/` 目录下 `python -m pytest tests` 100% 通过（36.13 秒）；
   - 观测到 `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py` 均为物理只读，必须绝对禁止修改；
   - **推论 4**: 新增的工具链集成功能测试必须作为**独立新增测试文件**（如 `tests/test_toolkit_integration.py`）放置在 `AGY2_FundAdvisory/tests/` 中，既有 112 项测试与裁判文件保持 100% 零侵入。

---

## 3. Caveats (局限与边界假设)

1. **测试运行工作目录要求**:
   若在工作区根目录 `d:\Google\Workspace\Wind` 下直接运行 `pytest tests`，默认会根据 `pyproject.toml` 执行根目录下的 `Wind/tests/`；若要执行 `AGY2_FundAdvisory` 测试集，必须使用：
   `python -m pytest AGY2_FundAdvisory/tests` 或 `cd AGY2_FundAdvisory && python -m pytest tests`。在编排测试套件时需显式配置 CWD 或 PYTHONPATH。
2. **股票代码与中文名称映射**:
   `FUND_LOOK_THROUGH_DATA` 中的重仓股以中文简称形式存储（如“中芯国际”、“贵州茅台”），而 `WindToolkit` 的排雷接口接受证券代码（如 `688981.SH`, `600519.SH`）。因此在穿透排雷引擎中，需要借助 `MasterDictParser` 或内置的标准标的代码映射字典完成中文名到代码的双向解析。
3. **网络离线安全红线**:
   开发和测试环境中不可依赖外部互联网东财或万得 API 实时代现；所有集成模块必须以本地已有的 DuckDB 湖仓 (`data/storage.duckdb` 与相关 Parquet) 为第一优先级兜底。

---

## 4. Conclusion (综合评估结论)

1. **系统架构高度解耦且扩展口完备**:
   `AGY2_FundAdvisory` 的代码组织（`portfolio_manager.py` 处理组合与底层穿透，`strategy_bridge.py` 负责策略推演与宏观整合，`app_gui.py` 负责 Streamlit 视图呈现）非常清晰，预留了与 `WindToolkit` 无缝插拔的标准化接口。
2. **时序湖仓底座完好且数据就绪**:
   底层 `data/storage.duckdb` 与 122 个 Parquet 已经涵盖了 R1、R2、R3 所需的全部字段（商誉、存贷双高、质押、限售解禁、OMO、DR007、北向资金、股东户数、龙虎榜），无需额外冷启动爬取数据即可实现 100% 离线高可用。
3. **既有测试全量通过且基准神圣不可侵犯**:
   现有的 112 项测试全部通过（36.13s），4 个核心裁判与基建文件具备操作系统级的只读保护（`IsReadOnly: True`）。后续实施只需在既有函数上做无损扩展、并在 `tests/` 中新增独立测试模块即可达成需求。

---

## 5. Verification Method (独立验证方法)

后续开发者或审阅者可通过执行以下命令对本报告结论进行 100% 独立复现验证：

### 1. 验证既有 112 项测试通过率
```powershell
cd d:\Google\Workspace\Wind\AGY2_FundAdvisory
python -m pytest tests
```
- **预期结果**: `112 passed in ~36s`，退出码为 `0`。

### 2. 验证核心文件只读不可变量
```powershell
Get-Item d:\Google\Workspace\Wind\AGY2_FundAdvisory\AGENT_SPEC.md, d:\Google\Workspace\Wind\AGY2_FundAdvisory\holdout_vault.py, d:\Google\Workspace\Wind\AGY2_FundAdvisory\judge_engine.py, d:\Google\Workspace\Wind\AGY2_FundAdvisory\tests\test_infra.py | Select-Object Name, IsReadOnly, Mode, Attributes
```
- **预期结果**: 四个文件的 `IsReadOnly` 均为 `True`，`Mode` 为 `-ar--`。

### 3. 验证本地 DuckDB 湖仓及其视图
```powershell
cd d:\Google\Workspace\Wind
python -c "import duckdb; conn = duckdb.connect('data/storage.duckdb', read_only=True); df = conn.execute('SHOW TABLES').df(); print('Total tables/views:', len(df)); assert 'v_financial_risk_screen' in df['name'].values; assert 'v_open_market_operations' in df['name'].values; assert 'v_northbound_holdings' in df['name'].values; print('DuckDB lakehouse verification PASSED!')"
```
- **预期结果**: 输出 `Total tables/views: 41` 并打印 `DuckDB lakehouse verification PASSED!`。
