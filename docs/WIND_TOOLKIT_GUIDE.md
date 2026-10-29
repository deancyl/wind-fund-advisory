# Wind 投顾终端统一工具包 (WindToolkit) 生产使用指南

---

## 1. 架构总览与设计哲学

**WindToolkit** 是面向现代买方投顾、量化研究员与资管机构打造的本地高可用数据访问与量化投研体系。在保障 Wind 客户端（`wmain.exe`, `WBox.exe`）正常登录运行且零干扰的前提下，无缝捕获客户端会话状态、本地持久化配置与全景金融数据，构建轻量级本地湖仓与一体化 Python SDK / CLI 工具链。

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Wind 投顾终端 (活跃运行中)                      │
│  - 客户端主进程: wmain.exe (PID 50956)                                 │
│  - 外壳与工具箱: WBox.exe (PID 1156)                                   │
│  - 本地用户配置: users/W36989091984/ (latestvisit, BBQ, tabs, userline)│
│  - 离线主字典:   FreqUsedCodeFile.codecache (41MB), SysGrp.xml         │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ 纯只读无感探测 (Air-Gapped Safety)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                     WindToolkit 统一 Python SDK                        │
│               (src/toolkit/ 生产级面向对象接口)                        │
├───────────────────┬───────────────────┬────────────────────────────────┤
│ 💼 watchlist      │ 📊 financials     │ 🟢 money_flow                  │
│ 自选与工作台资产  │ F10财务/杜邦分析  │ 行业板块主力资金流             │
├───────────────────┼───────────────────┼────────────────────────────────┤
│ 🏛️ bonds          │ 📦 etf            │ 📈 earnings_forecast           │
│ 中债收益率曲线    │ ETF份额与资金流向 │ 业绩预告与财务高危排雷 (FCF)   │
├───────────────────┼───────────────────┼────────────────────────────────┤
│ 🐉 chips_market   │ 🔒 holder_risk    │ 🧭 institutional_holdings      │
│ 龙虎榜/大宗/筹码  │ 解禁日历/质押预警 │ 北向资金/公募季报重仓抱团      │
├───────────────────┼───────────────────┼────────────────────────────────┤
│ ⚡ derivatives    │ 🌡️ macro_liquidity│ 🔍 lakehouse & query           │
│ 股指期货基差/期权 │ 央行 OMO/DR007利率│ DuckDB + Parquet 统一湖仓      │
└───────────────────┴───────────────────┴────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│               本地时序湖仓 (data/ 100% 隔离安全落盘)                    │
│  - master/user_watchlist.parquet         -> v_user_watchlist           │
│  - mart/stock_financials.parquet         -> v_stock_financials        │
│  - mart/stock_dividends.parquet          -> v_stock_dividends         │
│  - mart/sector_money_flow.parquet        -> v_sector_money_flow        │
│  - macro/chinabond_yield_curve.parquet   -> v_chinabond_yield_curve    │
│  - mart/etf_flows.parquet                -> v_etf_flows                │
│  - mart/earnings_forecast.parquet        -> v_earnings_forecast        │
│  - mart/financial_risk_screen.parquet    -> v_financial_risk_screen    │
│  - mart/dragon_tiger.parquet             -> v_dragon_tiger             │
│  - mart/block_trading.parquet            -> v_block_trading            │
│  - mart/shareholder_count.parquet        -> v_shareholder_count        │
│  - mart/lockup_calendar.parquet          -> v_lockup_calendar          │
│  - mart/pledge_risk.parquet              -> v_pledge_risk              │
│  - mart/holder_trading.parquet           -> v_holder_trading           │
│  - mart/northbound_holdings.parquet      -> v_northbound_holdings      │
│  - mart/fund_heavyweight_stocks.parquet  -> v_fund_heavyweight_stocks  │
│  - derivatives/futures_basis.parquet     -> v_futures_basis            │
│  - derivatives/option_volatility.parquet -> v_option_volatility        │
│  - macro/open_market_operations.parquet  -> v_open_market_operations   │
│  - macro/interbank_rates.parquet         -> v_interbank_rates          │
└────────────────────────────────────────────────────────────────────────┘
```

### 核心安全与设计红线
1. **原厂程序文件零污染 (Zero Impact)**：严格只读探测 `C:\Wind\`，严禁修改、覆盖原厂程序，严禁 kill 或重启任何运行中的终端进程。
2. **多轨故障自愈架构 (Multi-Tier Resilience)**：
   - **Track 1**: 在线官方接口与高速数据通道
   - **Track 2**: 本地 Chromium CEF / LevelDB 缓存逆向解析
   - **Track 3**: 本地 Parquet 湖仓历史时序与增量合并
   - **Track 4**: 离线纯脱机基准兜底
3. **100% 数据隔离沉淀**：所有数据均标准化存储在 `data/` 下，严禁污染原厂客户端目录。

---

## 2. 投顾核心能力全景矩阵

| 核心能力模块 | 数据载体与协议 | 核心输出指标 | 湖仓文件与 DuckDB 视图 |
| :--- | :--- | :--- | :--- |
| **投顾自选与工作台** (`watchlist`) | `latestvisit.hqv`, `smart_history.txt`, `windtabsex1.xml`, `BBQ/5ZBMW.ini` | 最近调阅标的、智能搜索流、工作台激活标签、BBQ 债券报价方案、用户技术指标画线 | `master/user_watchlist.parquet`<br>`v_user_watchlist` |
| **F10 财务核心指标** (`financials`) | 上市公司季报/中报/年报宽表 | 营业总收入、营收同比、归母净利润、净利同比、加权 ROE、销售毛利率、每股指标 (EPS, BPS) | `mart/stock_financials.parquet`<br>`v_stock_financials` |
| **杜邦三因子拆解** (`financials`) | 杜邦分析模型计算引擎 | 净利率 (Net Margin) × 总资产周转率 (Asset Turnover) × 权益乘数 (Leverage) = ROE | 动态计算透视 |
| **分红送配与股息率** (`financials`) | 权益分配与除息日历 | 每10股派息(元)、送转股、分红预案方案、股息率(%)、股权登记日、除权除息日、实施进度 | `mart/stock_dividends.parquet`<br>`v_stock_dividends` |
| **行业主力资金流向** (`money_flow`) | 申万/万得一级行业与概念板块 | 今日主力净流入额(亿元)、净占比、超大单/大单/中单/小单订单拆解、行业领涨龙头股 | `mart/sector_money_flow.parquet`<br>`v_sector_money_flow` |
| **中债收益率曲线** (`bonds`) | 中债国债与高等级信用债官方定价 | 3M, 1Y, 3Y, 5Y, 7Y, 10Y, 30Y 收益率、10Y-1Y 期限利差、30Y-10Y 超长端利差、3Y AAA 信用利差 | `macro/chinabond_yield_curve.parquet`<br>`v_chinabond_yield_curve` |
| **ETF 份额与资金流动** (`etf`) | 上交所 (SSE) + 深交所 (SZSE) 全量穿透 | 最新份额(亿份)、单位净值、最新规模(亿元)、单日份额变动(万份)、估算单日净流入额(亿元) | `mart/etf_flows.parquet`<br>`v_etf_flows` |
| **业绩预告与财务排雷** (`earnings_forecast`) | 上市公司业绩预告与快报大表 | 预告类型 (预增/略增/扭亏/预减)、净利润区间、变动幅度、变动原因、自由现金流 (FCF)、商誉占比、应收天数、存贷双高探测 | `mart/earnings_forecast.parquet`<br>`v_earnings_forecast`<br>`v_financial_risk_screen` |
| **微观筹码面与资金分布** (`chips_market`) | 交易所龙虎榜、大宗交易与中登结算 | 龙虎榜游资与机构买卖净额、买卖席位、大宗交易溢折价率、股东户数环比变动率、户均持股市值与筹码集中趋势 | `mart/dragon_tiger.parquet`<br>`mart/block_trading.parquet`<br>`mart/shareholder_count.parquet` |
| **股东信用与风险日历** (`holder_risk`) | 上市公司限售解禁与中登质押数据 | 未来解禁日历、解禁股份类型、估算解禁市值、大股东股权质押比例、平仓线预警状态、董监高增减持与公司股份回购 | `mart/lockup_calendar.parquet`<br>`mart/pledge_risk.parquet`<br>`mart/holder_trading.parquet` |
| **机构持仓与聪明钱穿透** (`institutional_holdings`) | 香港交易所陆股通与公募基金季报 | 北向资金个股持股量与持股市值、近1日/5日增减持变动、公募基金重仓持股数量、持股市值、机构抱团拥挤度分级 | `mart/northbound_holdings.parquet`<br>`mart/fund_heavyweight_stocks.parquet` |
| **衍生品基差与期权波动率** (`derivatives`) | 中金所股指期货与上交所/深交所期权 | IF/IC/IM/IH 股指期货主力基差、年化贴水率、50ETF/300ETF 期权隐含波动率 (IV)、历史波动率 (HV)、中国波指 (iVIX)、波动率偏度 | `derivatives/futures_basis.parquet`<br>`derivatives/option_volatility.parquet` |
| **宏观高频流动性** (`macro_liquidity`) | 央行公开市场业务与全国银行间拆借中心 | 每日 7 天逆回购投放/到期/净投放、MLF 净投放、操作利率、DR001、DR007、SHIBOR-1W、GC001、政策利率利差 (bp)、资金面温度 | `macro/open_market_operations.parquet`<br>`macro/interbank_rates.parquet` |

---

## 3. Python SDK 快速上手

### 3.1 初始化与终端状态检测
```python
from src.toolkit import WindToolkit

wk = WindToolkit()

# 1. 毫秒级探测终端活跃状态与投顾画像
status = wk.get_terminal_status()
print(f"终端运行状态: {status['is_running']}")
print(f"登录投顾用户: {status['user']} ({status['company']})")
print(f"主进程 PID: {status['wmain_pid']}")

# 2. 深度离线解析投顾实名档案 (从 usermap.ini / UserWdid.dat)
profile = wk.watchlist.get_advisor_profile()
print(f"投顾姓名: {profile['name']} ({profile['en_name']}), 电话: {profile['phone']}, WDID: {profile['wdid']}")
```

### 3.2 投顾自选标的与工作台探索
```python
# 提取投顾全景自选大宽表 (聚合最新调阅、搜索关注、技术指标标的)
df_wl = wk.watchlist.build_consolidated_watchlist()
print(df_wl[["symbol", "name", "asset_class", "source"]].head())

# 提取终端最近打开的标签页与功能指令
tabs = wk.watchlist.get_workbench_tabs()
for t in tabs:
    print(f"标签: {t['caption']}, 指令: {t['command_code']}, 时间: {t['close_time']}")

# 提取用户技术画线与价格盯盘预警线
marks = wk.watchlist.get_marked_userlines()
for m in marks:
    print(f"标的: {m['symbol']}, 类型: {m['mark_type']}, 参数: {m['params']}")
```

### 3.3 股票/基金 F10 财务指标与杜邦拆解
```python
# 调阅历史财报指标
df_fin = wk.financials.fetch_stock_financials("600519", limit=4)
print(df_fin[["report_date", "total_revenue_billion", "net_profit_billion", "roe_pct", "eps"]])

# 杜邦三因子分析
dupont = wk.financials.get_dupont_analysis("600519")
print(dupont["dupont_formula"])
print(f"净利率: {dupont['net_margin_pct']}% | 周转率: {dupont['asset_turnover']} | 权益乘数: {dupont['equity_multiplier']}")

# 历史现金分红流水
df_div = wk.financials.fetch_dividends("600519", limit=5)
print(df_div[["report_date", "plan_desc", "cash_dividend_10", "dividend_yield_pct"]])
```

### 3.4 行业板块主力资金流向
```python
# 获取主力资金净流入榜前 5 行业
df_inflow = wk.money_flow.get_top_inflow_sectors(top_n=5)
print(df_inflow[["sector_name", "main_net_inflow_billion", "change_pct", "top_stock_name"]])

# 获取主力资金净流出警示榜前 5 行业
df_outflow = wk.money_flow.get_top_outflow_sectors(top_n=5)
print(df_outflow[["sector_name", "main_net_inflow_billion", "change_pct"]])

# 单向精准下潜查询指定行业资金流向
coal_flow = wk.money_flow.get_sector_flow("煤炭")
print(f"煤炭主力净流入: {coal_flow['main_net_inflow_billion']} 亿元, 领涨龙头: {coal_flow['top_stock_name']}")
```

### 3.5 中债收益率曲线与固收利差
```python
# 获取最新中债收益率曲线快照 (覆盖 3M, 6M, 1Y, 3Y, 5Y, 7Y, 10Y, 30Y)
curve = wk.bonds.get_latest_yield_curve()
print(f"定价日: {curve['date']}, 1Y: {curve['y_1y']}%, 10Y: {curve['y_10y']}%, 30Y: {curve['y_30y']}%")

# 获取宏观期限利差与投顾配置建议
analysis = wk.bonds.get_term_spreads_analysis()
print(f"10Y-1Y 利差: {analysis['term_spread_10y_1y_bp']} bp, 形态: {analysis['curve_regime']}")
```

### 3.6 场内 ETF 份额规模与资金流动
```python
# 估算资金净流入榜前 5 名 ETF
df_etf_in = wk.etf.get_top_inflow_etfs(top_n=5)
print(df_etf_in[["etf_code", "etf_name", "category", "shares_billion", "est_net_inflow_billion"]])

# 大类资产 (宽基 vs 行业主题 vs 策略红利 vs 跨境QDII vs 固收商品) 流向聚类统计
df_cat = wk.etf.get_category_flow_summary()
print(df_cat)
```

### 3.7 业绩预告与财务高危排雷 (FCF)
```python
# 1. 查询全市场或指定个股最新业绩预告
df_fore = wk.earnings_forecast.fetch_earnings_forecast("600519", limit=5)
print(df_fore[["symbol", "stock_name", "forecast_type", "profit_min_million", "profit_change_min_pct"]])

# 2. 深度财务排雷扫描 (FCF, 商誉, 应收账款天数, 存贷双高探测)
risk = wk.earnings_forecast.screen_financial_risks("600519")
print(f"排雷评级: {risk['risk_level']}, 自由现金流: {risk['fcf_billion']} 亿, 存贷双高: {risk['double_high_risk']}")

# 3. 自由现金流 (FCF) 历史成色推演
fcf_eval = wk.earnings_forecast.get_fcf_analysis("600519", periods=4)
print(f"平均自由现金流: {fcf_eval['average_fcf_billion']} 亿, 成色: {fcf_eval['fcf_quality']}")
```

### 3.8 微观筹码面与市场资金分布
```python
# 1. 每日龙虎榜席位与机构专用净买卖额
df_dt = wk.chips_market.fetch_dragon_tiger_daily(limit=10)
print(df_dt[["symbol", "stock_name", "change_pct", "net_buy_million", "institution_net_million"]])

# 2. 机构博弈综合情绪
inst_summary = wk.chips_market.get_institutional_dragon_tiger_summary()
print(f"机构席位总体情绪: {inst_summary['institution_sentiment']}, 净买入合计: {inst_summary['institution_net_total_million']} 百万")

# 3. 每日大宗交易流水与折溢价率
df_bt = wk.chips_market.fetch_block_trading(limit=5)
print(df_bt[["symbol", "stock_name", "deal_price", "discount_rate_pct", "deal_amount_ten_thousand"]])

# 4. 股东户数环比变动与筹码集中趋势
df_sh = wk.chips_market.fetch_shareholder_concentration("600519", limit=4)
print(df_sh[["end_date", "holder_count", "holder_change_pct", "avg_market_value_ten_thousand", "concentration_trend"]])
```

### 3.9 股东信用与风险日历
```python
# 1. 未来限售股解禁日历与抛压测算
df_lock = wk.holder_risk.fetch_lockup_calendar(days_ahead=30, limit=10)
print(df_lock[["unlock_date", "symbol", "stock_name", "unlock_market_value_billion", "risk_level"]])

# 2. 大股东股权质押比例与平仓线预警
df_pledge = wk.holder_risk.fetch_pledge_risk("600519")
print(df_pledge[["symbol", "pledge_ratio_total_pct", "warning_close_line_status", "risk_level"]])

# 3. 董监高增减持与公司股份回购流水
df_trade = wk.holder_risk.fetch_holder_trading(limit=10)
print(df_trade[["trade_date", "symbol", "holder_name", "trade_type", "change_amount_ten_thousand"]])
```

### 3.10 机构持仓与聪明钱穿透
```python
# 1. 北向资金 (陆股通) 持股市值与近期调仓时序
df_nb = wk.institutional_holdings.fetch_northbound_holdings("600519", limit=5)
print(df_nb[["symbol", "holding_market_value_billion", "float_ratio_pct", "change_5d_value_million"]])

# 2. 筛选聪明钱近 5 日加速加仓龙头
df_smart_top = wk.institutional_holdings.get_smart_money_inflow_top(top_n=5)
print(df_smart_top[["symbol", "stock_name", "change_5d_value_million"]])

# 3. 公募基金季报重仓股穿透与抱团度
df_heavy = wk.institutional_holdings.fetch_fund_heavyweight_stocks(report_period="2024Q4", limit=10)
print(df_heavy[["symbol", "stock_name", "fund_count", "holding_value_billion", "crowding_degree"]])
```

### 3.11 衍生品基差与期权波动率
```python
# 1. 股指期货主力基差与年化贴水率
df_basis = wk.derivatives.fetch_futures_basis()
print(df_basis[["contract_code", "index_name", "spot_price", "futures_price", "annualized_basis_rate_pct", "hedge_cost_assessment"]])

# 2. 贴水套利与多头增强策略机会测算
opps = wk.derivatives.get_arbitrage_opportunities()
for op in opps:
    print(f"合约: {op['contract']}, 年化贴水: {op['annualized_discount_pct']}%, 建议: {op['recommendation']}")

# 3. ETF 期权隐含波动率 (IV) 与中国波指 (iVIX)
df_iv = wk.derivatives.fetch_option_volatility()
print(df_iv[["underlying_symbol", "underlying_name", "iv_pct", "hv_20d_pct", "ivix_index", "market_sentiment"]])
```

### 3.12 宏观高频流动性与央行公开市场业务
```python
# 1. 央行 7 天逆回购与 MLF 净投放时序
df_omo = wk.macro_liquidity.fetch_open_market_operations(days=7)
print(df_omo[["date", "repo_7d_injection_billion", "repo_7d_net_billion", "total_net_injection_billion", "liquidity_stance"]])

# 2. 银行间质押式回购加权利率 (DR001, DR007)
df_dr = wk.macro_liquidity.fetch_interbank_rates(days=7)
print(df_dr[["date", "dr001", "dr007", "policy_rate_7d", "dr007_spread_bp", "liquidity_status"]])

# 3. 资金面高频温度计与政策态度研判
thermo = wk.macro_liquidity.get_liquidity_thermometer()
print(f"资金面状态: {thermo['liquidity_status']}, DR007利差: {thermo['dr007_spread_bp']} bp")
print(f"投顾结论: {thermo['advisory_takeaway']}")
```

### 3.13 一键全景增量入湖与 DuckDB SQL 即席查询
```python
# 一键同步全量 11 大数据集
sync_report = wk.sync_all(force=True)

# 统一 SQL 即席查询全量视图
df_sql = wk.query("""
    SELECT 
        b.contract_code,
        b.index_name,
        b.annualized_basis_rate_pct,
        l.dr007,
        l.liquidity_status
    FROM v_futures_basis b, v_interbank_rates l
    ORDER BY l.date DESC
    LIMIT 4
""")
print(df_sql)
```

---

## 4. 生产级 CLI 统一命令行手册

统一入口：`python wind_cli.py <subcommand> [options]`

### 4.1 终端工作台与自选标的：`watchlist`
```bash
python wind_cli.py watchlist
```
- 输出投顾终端在线状态、进程 PID、登录机构与用户画像。
- 展示自选池、高频调阅池、技术标记池的大宽表及关闭时间。

### 4.2 F10 财务指标与杜邦分析：`f10`
```bash
python wind_cli.py f10 600519 --limit 4
```
- 输出历期营业收入、净利润、同比增速、ROE、毛利率、每股指标。
- 自动渲染杜邦三因子分析透视看板。

### 4.3 现金分红送配与股息率：`dividends`
```bash
python wind_cli.py dividends 600519 --limit 5
```
- 输出分红预案方案、每10股派现金额、股息率、登记日与实施进度。

### 4.4 行业板块主力资金流向：`money-flow`
```bash
# 查看今日主力资金净流入榜前 15 行业
python wind_cli.py money-flow --top 15

# 精准查询指定行业资金博弈与订单拆解
python wind_cli.py money-flow --sector 煤炭

# 查看今日主力资金净流出避险榜前 15 行业
python wind_cli.py money-flow --top 15 --outflow
```

### 4.5 中债国债收益率曲线与利差：`yield-curve`
```bash
python wind_cli.py yield-curve
```
- 输出各关键期限（3M, 6M, 1Y, 3Y, 5Y, 7Y, 10Y, 30Y）官方国债收益率。
- 输出 10Y-1Y 期限利差、10Y-3Y 利差、30Y-10Y 超长端利差、3Y AAA 信用利差及投顾宏观配置指引。

### 4.6 场内 ETF 份额规模与资金流动：`etf-flow`
```bash
# 查看净流入前 15 名 ETF
python wind_cli.py etf-flow --top 15

# 筛选策略红利 ETF
python wind_cli.py etf-flow --category 策略红利 --top 10

# 查看净流出赎回榜
python wind_cli.py etf-flow --top 10 --outflow
```

### 4.7 业绩预告与财务排雷：`forecast`
```bash
# 查看全市场最新业绩预告流
python wind_cli.py forecast --limit 15

# 对指定个股执行商誉/应收账款/存贷双高/FCF 排雷扫描
python wind_cli.py forecast 600519 --screen

# 输出机器友好的 JSON 格式
python wind_cli.py forecast 600519 --screen --json
```

### 4.8 微观筹码面与市场分布：`chips`
```bash
# 1. 每日龙虎榜席位与机构博弈
python wind_cli.py chips dragon-tiger --top 15

# 2. 每日大宗交易流水与折溢价率
python wind_cli.py chips block-trade --top 15

# 3. 股东户数环比变动与筹码集中趋势
python wind_cli.py chips concentration --code 600519 --top 6

# 4. JSON 导出
python wind_cli.py chips dragon-tiger --top 5 --json
```

### 4.9 股东信用与风险日历：`holder-risk`
```bash
# 1. 查看未来 30 天限售股解禁日历与抛压测算
python wind_cli.py holder-risk lockup --days 30 --top 15

# 2. 监测大股东股权质押比例与平仓线预警
python wind_cli.py holder-risk pledge --code 600519

# 3. 董监高增减持与公司股份回购流水
python wind_cli.py holder-risk trading --top 15
```

### 4.10 机构持仓与聪明钱穿透：`smart-money`
```bash
# 1. 北向资金 (陆股通) 个股持股时序与调仓
python wind_cli.py smart-money northbound --top 15

# 2. 公募基金季报重仓股与抱团拥挤度
python wind_cli.py smart-money fund-heavy --period 2024Q4 --top 15

# 3. 筛选抱团极度拥挤的标的
python wind_cli.py smart-money crowding --top 10
```

### 4.11 衍生品基差与期权波动率：`derivatives`
```bash
# 1. 股指期货主力基差与年化贴水率
python wind_cli.py derivatives basis

# 2. 主流 ETF 期权隐含波动率 (IV) 与中国波指 (iVIX)
python wind_cli.py derivatives volatility

# 3. 期货基差贴水套利与多头增强策略评估
python wind_cli.py derivatives arbitrage
```

### 4.12 宏观高频流动性：`liquidity`
```bash
# 1. 资金面高频温度计与 DR007 政策利差
python wind_cli.py liquidity thermometer

# 2. 央行公开市场操作 (OMO) 逆回购/MLF 流水
python wind_cli.py liquidity omo --days 15

# 3. 银行间质押式回购加权利率时序
python wind_cli.py liquidity interbank --days 15
```

### 4.13 一键增量入湖：`sync-toolkit`
```bash
python wind_cli.py sync-toolkit [--force]
```
- 一键批量将自选标的、F10 财务、分红流水、行业资金流、中债曲线、ETF 份额、业绩预告、微观筹码、股东风险、机构持仓、衍生品基差与宏观流动性等 11 大数据集增量更新入本地湖仓，并刷新 DuckDB 全量 20+ 视图。

---

## 5. 本地湖仓与 DuckDB 视图字典

工作区本地湖仓基于 **DuckDB + Parquet** 构建，存储于 `data/` 下。通过统一视图提供纯 SQL 查询体验：

### 5.1 全景视图清单

| 视图名 | 底层 Parquet 路径 | 说明 | 核心字段 |
| :--- | :--- | :--- | :--- |
| `v_user_watchlist` | `master/user_watchlist.parquet` | 用户自选与工作台监控标的 | `symbol`, `name`, `asset_class`, `source` |
| `v_stock_financials` | `mart/stock_financials.parquet` | 上市公司 F10 财务指标宽表 | `symbol`, `stock_name`, `report_date`, `roe_pct` |
| `v_stock_dividends` | `mart/stock_dividends.parquet` | 历史分红送配与股息率记录 | `symbol`, `cash_dividend_10`, `dividend_yield_pct` |
| `v_sector_money_flow` | `mart/sector_money_flow.parquet` | 申万/万得行业板块资金流向 | `sector_name`, `main_net_inflow_billion`, `top_stock_name` |
| `v_chinabond_yield_curve`| `macro/chinabond_yield_curve.parquet` | 中债国债与信用债收益率曲线 | `date`, `y_1y`, `y_10y`, `term_spread_10y_1y_bp` |
| `v_etf_flows` | `mart/etf_flows.parquet` | 场内 ETF 份额与资金流动 | `etf_code`, `etf_name`, `est_net_inflow_billion` |
| `v_earnings_forecast` | `mart/earnings_forecast.parquet` | 业绩预告与业绩快报宽表 | `symbol`, `forecast_type`, `profit_change_min_pct` |
| `v_financial_risk_screen` | `mart/financial_risk_screen.parquet` | 自由现金流与三大排雷指标 | `symbol`, `fcf_billion`, `goodwill_ratio_pct`, `risk_level` |
| `v_dragon_tiger` | `mart/dragon_tiger.parquet` | 龙虎榜每日席位追踪 | `symbol`, `trade_date`, `net_buy_million`, `institution_net_million` |
| `v_block_trading` | `mart/block_trading.parquet` | 大宗交易每日流水 | `symbol`, `deal_price`, `discount_rate_pct`, `deal_amount_ten_thousand` |
| `v_shareholder_count` | `mart/shareholder_count.parquet` | 股东户数与筹码集中度 | `symbol`, `end_date`, `holder_count`, `holder_change_pct` |
| `v_lockup_calendar` | `mart/lockup_calendar.parquet` | 限售股解禁日历 | `symbol`, `unlock_date`, `unlock_market_value_billion`, `risk_level` |
| `v_pledge_risk` | `mart/pledge_risk.parquet` | 大股东股权质押监测 | `symbol`, `pledge_ratio_total_pct`, `warning_close_line_status` |
| `v_holder_trading` | `mart/holder_trading.parquet` | 董监高增减持与公司回购 | `symbol`, `trade_date`, `holder_name`, `trade_type` |
| `v_northbound_holdings` | `mart/northbound_holdings.parquet` | 北向资金个股持股时序 | `symbol`, `holding_market_value_billion`, `change_5d_value_million` |
| `v_fund_heavyweight_stocks` | `mart/fund_heavyweight_stocks.parquet` | 公募基金季报重仓股穿透 | `symbol`, `fund_count`, `holding_value_billion`, `crowding_degree` |
| `v_futures_basis` | `derivatives/futures_basis.parquet` | 股指期货基差与贴水率 | `contract_code`, `spot_price`, `futures_price`, `annualized_basis_rate_pct` |
| `v_option_volatility` | `derivatives/option_volatility.parquet` | ETF 期权隐含波动率与波指 | `underlying_symbol`, `iv_pct`, `hv_20d_pct`, `ivix_index` |
| `v_open_market_operations` | `macro/open_market_operations.parquet` | 央行公开市场操作时序 | `date`, `repo_7d_net_billion`, `total_net_injection_billion` |
| `v_interbank_rates` | `macro/interbank_rates.parquet` | 银行间质押回购与 SHIBOR | `date`, `dr001`, `dr007`, `dr007_spread_bp`, `liquidity_status` |

### 5.2 深度多源关联 SQL 查询范例

#### 范例 1: 穿透公募基金重仓抱团股的“财务排雷与商誉/现金流”健康度
```sql
SELECT 
    h.symbol,
    h.stock_name,
    h.fund_count,
    h.holding_value_billion,
    h.crowding_degree,
    r.fcf_billion,
    r.goodwill_ratio_pct,
    r.ar_turnover_days,
    r.risk_level
FROM v_fund_heavyweight_stocks h
LEFT JOIN v_financial_risk_screen r ON h.symbol = r.symbol
WHERE h.crowding_degree = '极度拥挤'
ORDER BY h.holding_value_billion DESC;
```

#### 范例 2: 股指期货年化贴水率与宏观资金面流动性联动监测
```sql
SELECT 
    f.contract_code,
    f.index_name,
    f.annualized_basis_rate_pct,
    f.hedge_cost_assessment,
    l.dr007,
    l.dr007_spread_bp,
    l.liquidity_status
FROM v_futures_basis f, (
    SELECT dr007, dr007_spread_bp, liquidity_status 
    FROM v_interbank_rates 
    ORDER BY date DESC LIMIT 1
) l
ORDER BY f.annualized_basis_rate_pct DESC;
```

#### 范例 3: 未来 30 天巨量解禁高风险股票与大股东质押排查
```sql
SELECT 
    c.unlock_date,
    c.days_to_unlock,
    c.symbol,
    c.stock_name,
    c.unlock_market_value_billion,
    c.risk_level AS lockup_risk,
    p.pledge_ratio_total_pct,
    p.warning_close_line_status
FROM v_lockup_calendar c
LEFT JOIN v_pledge_risk p ON c.symbol = p.symbol
WHERE c.risk_level = 'High'
ORDER BY c.days_to_unlock ASC;
```

---

## 6. 实战投顾量化应用场景

### 场景一：低波红利策略“三合一”安全穿透
- **痛点**：盲目追求高股息率，极易踩雷“利润不可持续、虚假分红、股价阴跌”的“股息陷阱 (Dividend Trap)”。
- **解决范式**：
  1. 调用 `wk.financials.fetch_dividends()` 筛选股息率 > 3.0% 的标的；
  2. 联动 `wk.financials.fetch_stock_financials()` 穿透检验 ROE 是否 > 10%、近 3 年净利润同比是否为正、经营活动现金流是否覆盖资本开支；
  3. 执行杜邦三因子拆解，确认高 ROE 源于“高净利率”而非高负债杠杆。

### 场景二：宏观利率中枢与债市避险调仓
- **痛点**：10年期国债收益率极度下行至历史底部磨底区（< 1.8%），机构盲目追高长债可能在利率反弹中承受巨额资本损失。
- **解决范式**：
  1. 调用 `wk.bonds.get_term_spreads_analysis()` 实时监测 10Y-1Y 期限利差与 30Y-10Y 超长端利差；
  2. 当 10Y 国债收益率 < 2.0% 且利差极度平坦化时，触发投顾组合避险红线，严格限制纯债端久期（优先以中短债/现金底仓为主），拒绝高位接盘长债。

### 场景三：大盘情绪与主力资金逆向监控
- **痛点**：散户投资者在行业板块暴涨后盲目追高，常买在主力机构资金出逃的顶点。
- **解决范式**：
  1. 调用 `wk.money_flow.get_top_outflow_sectors()` 监测行业涨幅较大但主力超大单持续净流出的“背离品种”；
  2. 调用 `wk.etf.get_category_flow_summary()` 观测全市场资金偏好是否正在从“进攻型行业主题”向“稳健型策略红利”迁移，指导投顾客户择机逢高阶梯减亏或获利了结。

### 场景四：中性对冲与股指期货年化贴水多头替代
- **痛点**：中小盘指增或市场中性策略面临昂贵对冲成本，盲目空头对冲常被深度贴水吃掉大量阿尔法。
- **解决范式**：
  1. 调用 `wk.derivatives.fetch_futures_basis()` 测算各合约年化贴水率；
  2. 当 IM (中证1000) 远月年化贴水 > 10% 时，指导多头策略采用“股指期货多头替代 (展期吃贴水)”替代现货持仓，享受无风险基差收敛带来的确定性年化纯超额。

### 场景五：股东信用暴雷与大额解禁前瞻排险
- **痛点**：重仓标的突遭大比例定增解禁或控股股东质押爆仓平仓，引发股价连续跌停。
- **解决范式**：
  1. 调用 `wk.holder_risk.get_high_risk_calendar(days_ahead=30)` 提前 30 天自动扫描组合重仓标的的解禁日程；
  2. 联动 `wk.holder_risk.fetch_pledge_risk()` 检验大股东质押率是否击穿预警线；若解禁占流通盘 > 10% 且质押 > 50%，系统自动亮起红灯并建议逢高减持规避。

### 场景六：高频资金面与央行流动性温度计
- **痛点**：月末/季末或税期资金面突发收紧，债券或权益资产受流动性冲击大幅波动。
- **解决范式**：
  1. 每日调阅 `wk.macro_liquidity.get_liquidity_thermometer()` 追踪 DR007 与 7D 逆回购政策利率偏离度 (bp)；
  2. 当 DR007 偏离度 > 35 bp 且央行连续净回笼时，定性为“结构性偏紧”，指导投顾组合提前收缩杠杆、增加超短端回购头寸吃高息。
