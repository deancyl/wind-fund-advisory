# Explorer 3 (Integration & Gap Explorer) 调研与集成设计报告

## 摘要 (Executive Summary)
本报告对 AGY2 基金实盘组合接管与智能投顾管理系统（`AGY2_FundAdvisory`）接入底层时序湖仓与 Wind 投顾统一工具包（`WindToolkit`）的进阶投研能力（R1 穿透排雷、R2 宏观流动性温度计、R3 聪明钱与拥挤度监控、R4 生产质量与只读底座）进行全面的现状审计、代码定位、缺口分析与落地集成方案设计。

---

## 一、 Observation (现状直接观测与代码审计)

### 1.1 核心代码与架构现状直接观测
1. **现有测试套件全量基线与运行验证**：
   - 运行命令：`$env:PYTHONPATH="AGY2_FundAdvisory;."; python -m pytest AGY2_FundAdvisory/tests`
   - 观测结果：`collected 112 items`, `112 passed in 38.59s` (100% 通过，涵盖 `test_portfolio_manager.py`、`test_strategy_bridge.py`、`test_dynamic_risk_and_metrics.py`、`test_e2e_gui_render.py` 等 9 大测试模块)。
2. **只读保护底座安全性校验**：
   - 运行命令：`Get-Item AGY2_FundAdvisory/judge_engine.py, AGY2_FundAdvisory/holdout_vault.py, AGY2_FundAdvisory/AGENT_SPEC.md | Select-Object Name, IsReadOnly, Length`
   - 观测结果：
     - `judge_engine.py` (42,175 bytes, `IsReadOnly: True`)
     - `holdout_vault.py` (5,685 bytes, `IsReadOnly: True`)
     - `AGENT_SPEC.md` (8,237 bytes, `IsReadOnly: True`)
     - 确认严格物理只读，未被篡改。
3. **WindToolkit 统一 Python SDK 与本地湖仓存在性观测**：
   - 入口模块：`src/toolkit/unified_sdk.py`，类 `WindToolkit` 具备懒加载单例属性：
     - `wk.earnings_forecast` (`EarningsForecastCollector`, `src/toolkit/earnings_forecast.py`)
     - `wk.holder_risk` (`HolderRiskCollector`, `src/toolkit/holder_risk.py`)
     - `wk.macro_liquidity` (`MacroLiquidityCollector`, `src/toolkit/macro_liquidity.py`)
     - `wk.institutional_holdings` (`InstitutionalHoldingsCollector`, `src/toolkit/institutional_holdings.py`)
     - `wk.chips_market` (`ChipsMarketCollector`, `src/toolkit/chips_market.py`)
     - `wk.query(sql)` (DuckDB SQL 引擎即席查询)
   - 本地 Parquet 湖仓文件完备性：
     - `data/macro/open_market_operations.parquet` (8,501 bytes)
     - `data/macro/interbank_rates.parquet` (6,960 bytes)
     - `data/macro/chinabond_yield_curve.parquet` (12,796 bytes)
     - `data/mart/financial_risk_screen.parquet` (9,063 bytes)
     - `data/mart/earnings_forecast.parquet` (7,133 bytes)
     - `data/mart/pledge_risk.parquet` (9,275 bytes)
     - `data/mart/lockup_calendar.parquet` (7,602 bytes)
     - `data/mart/northbound_holdings.parquet` (9,792 bytes)
     - `data/mart/fund_heavyweight_stocks.parquet` (6,194 bytes)
     - `data/mart/dragon_tiger.parquet` (13,918 bytes)
     - `data/mart/shareholder_count.parquet` (8,223 bytes)
     - `data/mart/block_trading.parquet` (16,335 bytes)
4. **`portfolio_manager.py` 现状与穿透缺口**：
   - 观察点：第 690-760 行定义了静态前十大重仓与行业画像字典 `FUND_LOOK_THROUGH_DATA: Dict[str, Dict[str, Any]]`，覆盖核心基金（如 100032、005561、011612、011613、016634、001053、007339、013841、000216、002351、050025 等）。
   - 观察点：第 2446 行 `calculate_look_through_industry_exposure()` 实现了加权行业穿透。
   - 观察点：第 2492 行 `_fetch_external_fund_holdings()` 实现了本地 SQLite 缓存与外部基金穿透。
   - 观察点：第 2547 行 `calculate_stock_overlap_matrix()` 实现了基于 Jaccard 系数的前十大重仓股重合度交叉矩阵与伪分散预警。
   - **核心缺口 (Gap)**：当前穿透仅停留在“重仓股重合度与行业占比”层面，**完全缺失对重仓股财务健康度（商誉、存贷双高）、信用风险（大股东质押爆仓）、限售股大额解禁抛压的量化排雷与组合穿透风险指数计算**。
5. **`strategy_bridge.py` 现状与宏观流动性缺口**：
   - 观察点：第 1025 行 `get_latest_market_snapshot()` 动态计算了 MA20/MA60/MA120 均线偏离、风格动量比拼（科创50 vs 中证红利）、大小盘结构动量差（500 vs 300）及中债 10Y 国债利率与 ERP 股债性价比。
   - **核心缺口 (Gap)**：
     - 未接入 `WindToolkit.macro_liquidity`；
     - 缺乏高频 OMO 逆回购投放数据与 DR007 偏离政策利率偏离度 (bp) 的高频温度计；
     - 状态机尚未与流动性温度计做双轨融合（当资金面极端收紧时未触发防御动作）；
     - 选基漏斗与调仓订单生成时未融合北向聪明钱动态与机构抱团松动预警。
6. **`app_gui.py` 界面看板现状与渲染槽位**：
   - 观察点：第 288-363 行顶部状态栏采用 6 列指标卡 (`status_col1` ~ `status_col6`：申赎时钟、AI策略大脑、沪深300实时点位、股债性价比 ERP、今日预估浮盈亏、全组合总资产)。
   - 观察点：第 419 行定义了 4 大主 Tab：
     - Tab 1: `tab_brain` (AI 投顾大脑与今日建议，包含步骤一风险锚点、步骤二现场推演/选基漏斗 `SECTOR_FUND_SELECTION`、步骤三建仓/调仓执行单)
     - Tab 2: `tab_backtest` (策略胜率、回测与风控档案)
     - Tab 3: `tab_ledger` (我的持仓账本与傻瓜式接管向导)
     - Tab 4: `tab_toolbox` (组合穿透诊断、在途对账与 A/C 算费工具箱，含双环配置与行业暴露)
   - **核心缺口 (Gap)**：
     - 顶部看板缺少宏观流动性温度计徽章与偏离度卡片；
     - Tab 1 候选金牌基金池及建仓清单缺少三色风险标签（🟢/🟡/🔴）；
     - Tab 1 场景二（存量持仓诊断）及 Tab 4 底层穿透诊断缺少重仓股穿透排雷大宽表与组合整体穿透风险指数卡片。

---

## 二、 Logic Chain (从观测到集成设计的推理链条)

### 2.1 R1：基金底层前十大重仓股穿透排雷引擎设计
```
[观测到 FUND_LOOK_THROUGH_DATA 具备 top_stocks 股票清单]
    + [观测到 WindToolkit 具备 screen_financial_risks 与 fetch_pledge_risk / fetch_lockup_calendar]
    ==> 设计 1: 在 portfolio_manager.py 中建立股票代码与名称智能解析器 (Name-to-Symbol Resolver)
    ==> 设计 2: 建立单标的底层穿透排雷评分器 screen_fund_look_through_risk(fund_code)
    ==> 设计 3: 构建组合级穿透风险指数算法 calculate_portfolio_penetration_risk()
    ==> 设计 4: 在 Tab 1 (候选池) 和 Tab 2/4 (存量组合) 渲染三色标签与排雷明细表
```

#### 2.1.1 标的风险特征识别标准与量化打分
针对基金前十大重仓股票，依次探测 4 大雷点：
1. **商誉占净资产比重**：
   - 阈值：`goodwill_ratio_pct > 30.0%` 触发 🔴 高危减值雷；`20.0% ~ 30.0%` 触发 🟡 关注。
   - 依据：A股历史商誉减值多发生于年报季，重仓股商誉超 30% 极易导致净利润腰斩式暴跌。
2. **存贷双高财务粉饰造假特征**：
   - 识别逻辑：货币资金 $\ge 100$ 亿，同时有息负债 $\ge 150$ 亿，且负债/货币资金 $> 1.2$。
   - 判定：触发即标记 🔴 严重财务粉饰造假风险（康美、康得新典型特征）。
3. **控股股东高比例质押与平仓线预警**：
   - 识别逻辑：控股股东及一致行动人质押比例 $> 80.0\%$ 或 `warning_close_line_status == "击穿平仓线"` 触发 🔴 爆仓高危；质押比例在 $50.0\% \sim 80.0\%$ 触发 🟡 临界预警线。
4. **未来 30~90 天大额限售股解禁**：
   - 识别逻辑：未来 90 天内解禁市值 $> 20$ 亿元且占流通盘比重 $> 8\%$ 触发 🔴/🟡 减持套现抛压预警。

#### 2.1.2 组合整体穿透风险指数 (Portfolio Penetration Risk Index) 计算公式
1. **单只股票风险扣分 ($S_{stock}$)**：
   - 初始健康分 100 分。
   - 触发商誉 $>30\%$：扣 30 分；
   - 触发存贷双高：扣 40 分；
   - 质押击穿平仓线/质押率 $>80\%$：扣 35 分（临界预警扣 15 分）；
   - 大额解禁抛压：扣 20 分；
   - 自由现金流 FCF 为负：扣 10 分。
   - 股票单体风险得分 $R_{stock} = \max(0, 100 - \sum \text{扣分})$。
   - 股票风险状态：
     - $R_{stock} \ge 80$：🟢 健康 (Healthy)
     - $60 \le R_{stock} < 80$：🟡 关注 (Watch)
     - $R_{stock} < 60$：🔴 预警 (Danger)
2. **单只基金穿透风险指数 ($Index_{fund}$)**：
   - 对非权益资产（纯债基金如 002351、黄金 ETF 联接 000216、QDII 美股如 050025），默认穿透信用风险为 0，即 $Index_{fund} = 0$（🟢 100% 健康）。
   - 对 A 股权益基金，提取其前十大重仓股（每只假定权重或均分）：
     $$Index_{fund} = \frac{1}{K} \sum_{k=1}^K (100 - R_{stock, k})$$
     （范围 0 ~ 100，0 表示零风险，值越高风险越大）。
3. **组合全资产穿透风险指数 ($Index_{portfolio}$)**：
   $$Index_{portfolio} = \sum_{i} w_i \times Index_{fund, i}$$
   其中 $w_i$ 为各持仓基金在组合总市值中的实际占比。
   - **分级三色风险标签**：
     - 🟢 **健康 (Healthy)**：$Index_{portfolio} \le 20$ 且无任何 🔴 高危重仓股；
     - 🟡 **关注 (Watch)**：$20 < Index_{portfolio} \le 45$ 或存在 1 只 🔴 风险标的；
     - 🔴 **预警 (Danger)**：$Index_{portfolio} > 45$ 或持仓中存在 $\ge 2$ 只 🔴 高危重仓股（商誉暴雷或存贷双高）。

#### 2.1.3 UI 渲染与落地交互设计
1. **Tab 1（AI 投顾大脑与候选基金池）**：
   - 在步骤一/步骤二的 5 大赛道金牌标的卡片 (`SECTOR_FUND_SELECTION`) 中，在基金名称旁渲染徽章：
     `🏆 富国中证红利指数增强A 🟢 穿透排雷健康 (商誉0%, 质押0%)`
     若备选标的命中商誉或质押风险，呈现 `🟡 关注` 或 `🔴 预警`，鼠标悬停 Tooltip 显示具体雷点。
   - 在步骤三从 0 建仓执行单 (`df_bp` 表格) 中，新增 `"底层穿透体检"` 列，以色块徽章直观呈现。
2. **Tab 2 / Tab 1 场景二（存量持仓诊断）与 Tab 4（组合穿透工具箱）**：
   - 在决策信号灯卡片中增加第 ⑤ 张决策卡：
     `⑤ 组合穿透排雷指数: 🟢 12.8 (健康安全)`，标注商誉高危只数、质押平仓预警只数。
   - 在 Tab 4 `box_tab1` 下方新增：**【🏭 前十大重仓股穿透排雷与信用体检大宽表】**：
     列：`基金代码`、`基金简称`、`重仓股票`、`商誉占净资产`、`存贷双高探测`、`控股股东质押率`、`90天解禁市值`、`体检评级 (🟢/🟡/🔴)`、`排雷诊断详情`。

---

### 2.2 R2：宏观高频流动性温度计与双轨宏观雷达设计
```
[观测到 WindToolkit.macro_liquidity 产出 OMO 净投放与 DR007/OMO 利差 bp]
    + [观测到 strategy_bridge.py 现有 HS300 均线与 ERP 估值模型]
    ==> 设计 1: 在 strategy_bridge.py 接入 get_liquidity_thermometer()
    ==> 设计 2: 建立利差测算与动态定性规则 (宽松 / 中性 / 收紧)
    ==> 设计 3: 构建“估值技术面 × 宏观流动性”双轨雷达决策矩阵
    ==> 设计 4: 在极端流动性收紧时触发防御性资产配置 (Defensive Allocation Trigger)
    ==> 设计 5: 在 app_gui.py 顶部状态栏渲染第 7 列“流动性温度计”指标卡与状态徽章
```

#### 2.2.1 DR007 vs 7D OMO 政策利率偏离度与状态划分
- **公式**：
  $$\text{Spread}_{bp} = (\text{DR007} - \text{PolicyRate}_{7D}) \times 100$$
- **宏观流动性三态动态判定**：
  - 🟢 **宽松 (Loose)**：$\text{Spread}_{bp} \le +5.0\text{ bp}$（资金面充裕，银行间加权回购成本紧贴或低于政策利率，央行净投放对冲充分）。
  - 🟡 **中性 (Neutral)**：$+5.0\text{ bp} < \text{Spread}_{bp} \le +25.0\text{ bp}$（资金面处于合理平衡区间，资金供求平稳）。
  - 🔴 **收紧 (Tight)**：$\text{Spread}_{bp} > +25.0\text{ bp}$（跨季/跨月或缴税期资金面边际趋紧；若 $> +45.0\text{ bp}$ 判定为**结构性极端偏紧**）。

#### 2.2.2 双轨宏观雷达融合机制 (Dual-Track Macro Radar)
结合既有沪深300 MA均线系统、动量差与股债性价比 ERP：
| 轨道一：技术趋势与估值 (ERP / MA) | 轨道二：宏观流动性温度计 (DR007 Spread) | 双轨融合雷达判定 | 投顾资产配置决策导向 |
| :--- | :--- | :--- | :--- |
| **BULL (进攻科技牛 / 突破站上MA20)** | **🟢 宽松 / 🟡 中性** | 🚀 **天时地利·顺风主升** | 全力进攻科创50与中盘成长，按既定比例全额增配 |
| **BULL (进攻科技牛 / 突破站上MA20)** | **🔴 收紧 (Spread > 25bp)** | ⚠️ **估值扩张受阻·流动性摩擦** | 启动流动性约束罩：限制弹性高 Beta 标的冲动追高，保留 10% 现金缓冲 |
| **STABLE (常态高股息慢牛 / 震荡)** | **🟢 宽松** | 🟢 **股息再投·底仓稳健** | 高股息央企红利低波为压舱石，吃息持股，波动可控 |
| **STABLE (常态高股息慢牛 / 震荡)** | **🔴 结构性偏紧 (Spread > 35bp)** | 🟡 **防御升温·短端避险** | 适度增加固收纯债比重，降低浮动杠杆，防范流动性传导波动 |
| **BEAR (跌破均线 / 弱势整理)** | **🔴 极端收紧 (Spread > 45bp)** | 🛡️ **极端防御触发 (Extreme Defense)** | **触发防御性资产配置**：强制上调纯债（`H11009`）与黄金（`AU9999`）比重至 65%~70%，压降权益风险敞口 |
| **ERP 极高分位 (>80%) 底部磨底** | **🟢 宽松** | 💎 **戴维斯双击潜伏区** | 估值底与资金面共振，坚定禁止割肉，引导增量资金定投收集低估筹码 |

#### 2.2.3 顶部状态栏渲染规范
在 `app_gui.py` 顶部看板：
- 状态栏列扩展为 7 列（或优化整合）：新增 **【宏观流动性温度计】** 卡片。
- 卡片内容：
  - 标题：`流动性温度计 (DR007)`
  - 主数值：`+8.0 bp` (颜色：宽松 `#16a34a` 绿，中性 `#d97706` 橙，收紧 `#dc2626` 红)
  - 副文本：`🟢 合理充裕 ｜ 7D净投放 +120亿`
  - 悬停提示：`DR007: 1.58% ｜ 7D OMO: 1.50% ｜ 央行操作：净投放扶助流动性`
- 调仓网格横幅联动展示：
  `🌡️ 宏观流动性雷达：DR007 利差 +8.0 bp【🟢 合理充裕】，未对权益估值构成制约。`

---

### 2.3 R3：聪明钱与机构抱团拥挤度监控设计
```
[观测到 WindToolkit 具备 northbound_holdings、fund_heavyweight_stocks 与 chips_market]
    + [观测到 选基与调仓决策流位于 strategy_bridge.py 与 portfolio_manager.py]
    ==> 设计 1: 获取重仓股北向陆股通近 1日 / 5日持仓市值增减额
    ==> 设计 2: 提取股东户数环比变动率与筹码集中度趋向
    ==> 设计 3: 提取龙虎榜机构专用席位买卖净额与情绪
    ==> 设计 4: 构建热门赛道“公募抱团度 + 聪明钱动向 + 筹码发散度”综合松动风险预警
    ==> 设计 5: 在调仓方案与选基详情中呈现拥挤度提示与分批减亏/止盈建议
```

#### 2.3.1 聪明钱与微观筹码特征指标
1. **北向资金 (陆股通 / 聪明钱) 动态**：
   - 单股与赛道聚合：统计目标基金前五大权重股近 1 日、近 5 日北向净增减市值（亿元）。
   - 信号定性：
     - 近 5 日净增持 $> 0$ 且近 1 日持续加仓 $\rightarrow$ **聪明钱主力加仓 🟢**；
     - 近 5 日净减持 $< -10$ 亿元 $\rightarrow$ **聪明钱持续流出 🔴**。
2. **股东户数环比变动与筹码集中度**：
   - 提取最新季度/半年度股东户数变动率 `holder_change_pct`：
     - `holder_change_pct < -2.0%` $\rightarrow$ **筹码高度集中 🟢** (主力吸筹)；
     - `holder_change_pct > +5.0%` $\rightarrow$ **筹码快速发散 🔴** (散户接盘，主力派发)。
3. **公募基金抱团拥挤度与龙虎榜机构席位**：
   - 依据重仓持有该股的基金数量（如 $>500$ 家为极度拥挤，$>150$ 家为中度抱团）。
   - 龙虎榜机构净买入额为正表示机构逆势承接。

#### 2.3.2 抱团松动风险预警模型 (Crowding Loosening Warning)
针对赛道与个基，满足以下复合条件时触发预警：
- **🔴 抱团松动踩踏高危**：
  $$\text{公募抱团} == \text{"极度拥挤"} \quad \text{AND} \quad (\text{北向5日净流出} < -15\text{亿} \quad \text{OR} \quad \text{筹码快速发散})$$
  - **投顾建议**：该资产估值处于高位拥挤区，机构浮盈丰厚，一旦遭遇微观利空极易出现踩踏式出逃。在调仓执行单中提示：**“严禁单笔重仓追高！建议执行分批定投或下调目标增配上限至舒适阈值。”**
- **🟡 中度抱团跟踪**：
  公募中度抱团，北向资金小幅流入或平稳，提示顺势持有吃息。
- **🟢 筹码扎实健康**：
  股东户数持续减少（筹码向机构集中），聪明钱坚定增持。

---

### 2.4 R4：生产质量、零回归与离线底座防御设计
```
[观测到现有 112 项测试 100% 通过]
    + [观测到只读文件 judge_engine.py / holdout_vault.py / AGENT_SPEC.md 具有 IsReadOnly 属性]
    + [观测到 data/ 下存储有完整的 DuckDB 湖仓 Parquet 镜像文件]
    ==> 设计 1: 在 AGY2_FundAdvisory/tests/ 建立全新的 test_toolkit_integration.py
    ==> 设计 2: 保持既有 112 项测试零回归且全量通过
    ==> 设计 3: 设计四轨容灾防御保证离线/断网环境下 100% 零崩溃
    ==> 设计 4: 排查并解决边界条件 (非A股标的穿透、缺失报告、空湖仓、除以零)
```

#### 2.4.1 测试套件规划 (`AGY2_FundAdvisory/tests/test_toolkit_integration.py`)
规划覆盖 12+ 个全新严密测试用例：
1. `test_wind_toolkit_lazy_init_and_lakehouse()`: 验证 WindToolkit 各 Collector 属性懒加载正常，湖仓目录正确映射。
2. `test_earnings_forecast_screen_financial_risks()`: 验证商誉、FCF、应收账款天数、存贷双高判断准确性。
3. `test_holder_risk_pledge_and_lockup()`: 验证股权质押比例、平仓线状态及限售股解禁日历风险评级。
4. `test_macro_liquidity_thermometer_calc()`: 验证 DR007 与 7D OMO 偏离度 (bp) 正确计算，三态（宽松/中性/收紧）判断准确。
5. `test_dual_track_macro_radar_logic()`: 验证双轨宏观雷达在不同行情（牛/震荡/熊）与不同流动性组合下的融合输出。
6. `test_defensive_allocation_trigger_on_tight_liquidity()`: 验证宏观资金面极端紧缩时正确触发纯债/黄金防御仓位配置。
7. `test_institutional_smart_money_and_crowding()`: 验证北向资金 1D/5D 变动、公募抱团度与抱团松动预警。
8. `test_chips_market_shareholder_concentration()`: 验证股东户数环比增减及筹码集中度定性。
9. `test_fund_look_through_risk_screening()`: 验证 `PortfolioManager.screen_fund_look_through_risk()` 正确穿透股票池并输出三色标签。
10. `test_portfolio_penetration_risk_index()`: 验证全组合加权穿透风险指数计算及三色标签区间（0~100）。
11. `test_offline_duckdb_fallback_resilience()`: 断网模拟（mock requests 连接失败），验证 100% 平滑降级至本地 Parquet/DuckDB/静态基线，零异常抛出。
12. `test_non_ashare_look_through_immunity()`: 验证纯债、黄金、QDII 等非 A 股资产免受 A 股财务造假规则误判。

#### 2.4.2 离线 DuckDB 湖仓降级与断网鲁棒性保障
- **Multi-Tier Fallback 架构**：
  - **Tier 1 (在线 API)**：尝试拉取实时网络接口（超时严格设定为 3 秒以内）；
  - **Tier 2 (本地 DuckDB + Parquet 湖仓)**：网络不可用时秒级读取 `data/mart/*.parquet` 与 `data/macro/*.parquet`；
  - **Tier 3 (模块内建离线 Fallback 发生器)**：调用 `_generate_fallback_*()`；
  - **Tier 4 (内存安全缺省)**：保证返回值均为包含合规字段的字典或 DataFrame，绝不返回 None 或抛出未捕获异常。

---

## 三、 Caveats (局限性与假设说明)

1. **非 A 股资产免死原则与范围界定**：
   - 组合中的中债纯债基金（如 `002351`）、黄金 ETF 联接（`000216`）及标普500 美股（`050025`）不属于 A 股财务报表与质押监管口径。在设计穿透排雷引擎时，必须显式将其标记为“非A股权益免检标的”，风险扣分为 0，严禁将其误报为“无财报财务异常”。
2. **季报数据滞后性现实约束**：
   - 公募基金前十大重仓股与持股集中度每季度披露一次，存在法定披露时滞（季度结束后 15 个工作日内）。分析时需在 UI 界面显式标注数据披露基准期（如“基于 2024Q4/2025Q1 最新法定季报数据”），保证投研透明性。
3. **网络与 Wind 客户端探测静默原则**：
   - 即使处于离线网络环境，由于本地 `data/` 目录已沉淀有完整的 Parquet 湖仓数据，必须确保系统在无外网环境下仍能流畅运行并生成完全可读的投研报告与 GUI 渲染。

---

## 四、 Conclusion (最终集成评估与实施蓝图)

### 4.1 集成架构蓝图
```
┌────────────────────────────────────────────────────────────────────────┐
│               Wind 投顾统一工具包 (src/toolkit/ SDK)                   │
│  - earnings_forecast (商誉/FCF/存贷双高)  - holder_risk (质押/解禁)      │
│  - macro_liquidity (DR007/OMO 利差)       - institutional_holdings (北向)│
│  - chips_market (股东户数/龙虎榜)         - lakehouse (DuckDB 离线湖仓)   │
└───────────────────┬──────────────────────────────────┬─────────────────┘
                    │                                  │
                    ▼                                  ▼
┌──────────────────────────────────────┐ ┌───────────────────────────────┐
│       portfolio_manager.py           │ │      strategy_bridge.py       │
│ 1. screen_fund_look_through_risk()   │ │ 1. get_liquidity_thermometer()│
│    - 前十大重仓股穿透排雷             │ │    - DR007 vs OMO 利差 (bp)   │
│    - 识别商誉/存贷/质押/解禁          │ │ 2. 双轨宏观雷达决策状态机     │
│ 2. calculate_portfolio_penetration_  │ │    - 融合 MA20/ERP/流动性温度 │
│    risk()                            │ │ 3. 极端收紧防御性仓位切换     │
│    - 组合加权穿透风险指数 (0~100)    │ │ 4. 聪明钱与拥挤度风险预警     │
│    - 🟢健康 / 🟡关注 / 🔴预警        │ │    - 北向1D/5D + 筹码集中度   │
└───────────────────┬──────────────────┘ └──────────────┬────────────────┘
                    │                                  │
                    └──────────────────┬───────────────┘
                                       ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        app_gui.py (前端界面渲染)                       │
│  - 顶部状态栏：第 7 列渲染【流动性温度计】徽章与利差 bp (宽松/中性/收紧) │
│  - Tab 1 首屏：候选池与建仓单中渲染 🟢/🟡/🔴 三色排雷标签与聪明钱流入指标 │
│  - Tab 2 / 场景二：渲染组合穿透风险指数卡片与双轨宏观雷达研判结论     │
│  - Tab 4 工具箱：前十大重仓股穿透排雷大宽表与抱团松动警示看板           │
└────────────────────────────────────────────────────────────────────────┘
```

### 4.2 模块修改职责切分清单 (For Implementers)
1. **`portfolio_manager.py` 修改点**：
   - 引入 `WindToolkit`；
   - 新增方法 `screen_fund_look_through_risk(fund_code: str) -> Dict[str, Any]`；
   - 新增方法 `calculate_portfolio_penetration_risk() -> Dict[str, Any]`；
   - 新增方法 `get_fund_smart_money_crowding(fund_code: str) -> Dict[str, Any]`。
2. **`strategy_bridge.py` 修改点**：
   - 在 `get_latest_market_snapshot()` 中接入 `wk.macro_liquidity.get_liquidity_thermometer()`；
   - 计算 `dr007_spread_bp` 并定性流动性状态（宽松/中性/收紧）；
   - 实现双轨宏观雷达融合逻辑，并在极端紧缩（Spread > 45 bp）时触发防御仓位；
   - 在候选基金推荐与调仓说明中附加聪明钱动态与拥挤度提示。
3. **`app_gui.py` 修改点**：
   - 顶部状态栏扩展为包含“流动性温度计”指标卡；
   - Tab 1 候选基金池卡片与建仓清单展示三色穿透排雷标签；
   - Tab 1 场景二决策卡与 Tab 4 穿透工具箱展示穿透排雷大宽表与组合穿透风险指数。
4. **`AGY2_FundAdvisory/tests/test_toolkit_integration.py` 新建**：
   - 编写 12 个以上的单元测试与端到端测试，确保覆盖 R1~R4 全部要求，100% 通过且零回归。

---

## 五、 Verification Method (独立验证方法与命令)

后续实施智能体与质检验证时，必须严格执行以下验证步骤：

### 5.1 自动化测试验证
```powershell
# 1. 确保原有 112 项测试零回归通过
$env:PYTHONPATH="AGY2_FundAdvisory;."
python -m pytest AGY2_FundAdvisory/tests

# 2. 专门运行新增的工具包集成测试
python -m pytest AGY2_FundAdvisory/tests/test_toolkit_integration.py -v

# 3. 全量测试套件执行 (目标：112 + 12 = 124 项测试 100% PASS)
python -m pytest AGY2_FundAdvisory/tests/
```

### 5.2 只读基准防篡改核验
```powershell
# 确保物理只读属性 IsReadOnly 保持为 True
Get-Item AGY2_FundAdvisory/judge_engine.py, AGY2_FundAdvisory/holdout_vault.py, AGY2_FundAdvisory/AGENT_SPEC.md | Select-Object Name, IsReadOnly
```

### 5.3 离线与断网兜底测试 (Mock 断网)
```powershell
# 执行单元测试中的离线断网回退测试用例
python -m pytest AGY2_FundAdvisory/tests/test_toolkit_integration.py -k "test_offline" -v
```

### 5.4 GUI 启动与端到端渲染验证
```powershell
# 验证 app_gui 模块解析与无未捕获异常
python -c "import sys; sys.path.extend(['AGY2_FundAdvisory', '.']); import app_gui; print('app_gui loaded successfully')"
```

---
*报告生成完成。请实施智能体严格依照上述蓝图与逻辑链开展工作。*
