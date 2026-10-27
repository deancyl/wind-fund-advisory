# Wind 投顾终端统一工具包 (WindToolkit) 生产使用指南

---

## 1. 架构总览与设计哲学

**WindToolkit** 是面向现代买方投顾、量化研究员与资管机构打造的本地高可用数据访问与量化投研体系。在保障 Wind 客户端（`wmain.exe`, `WBox.exe`）正常登录运行且零干扰的前提下，无缝捕获客户端会话状态、本地持久化配置与全景金融数据，构建轻量级本地湖仓与一体化 Python SDK / CLI 工具链。

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Wind 投顾终端 (运行中)                          │
│  - 客户端主进程: wmain.exe (PID 34508)                                 │
│  - 外壳与工具箱: WBox.exe (PID 15692)                                  │
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
│ 🏛️ bonds          │ 📦 etf            │ 🔍 lakehouse & query           │
│ 中债收益率曲线    │ ETF份额与资金流向 │ DuckDB + Parquet 湖仓          │
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

# 提取用户技术画线与价格盯盘预警线 (全量扫描 Config 目录下 .Mark 与 .NewMark)
marks = wk.watchlist.get_marked_userlines()
for m in marks:
    print(f"标的: {m['symbol']}, 类型: {m['mark_type']}, 参数: {m['params']}")

# 提取 BBQ 债券报价与自选方案
schemes = wk.watchlist.get_bbq_schemes()
print(schemes)
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

# 单向精准下潜查询指定行业资金流向 (双轨在线容灾 + 31 申万一级行业全覆盖)
coal_flow = wk.money_flow.get_sector_flow("煤炭")
print(f"煤炭主力净流入: {coal_flow['main_net_inflow_billion']} 亿元, 领涨龙头: {coal_flow['top_stock_name']}")
```

### 3.5 中债收益率曲线与固收利差
```python
# 获取最新中债收益率曲线快照 (覆盖 3M, 6M, 1Y, 3Y, 5Y, 7Y, 10Y, 30Y)
curve = wk.bonds.get_latest_yield_curve()
print(f"定价日: {curve['date']}, 6M: {curve['y_6m']}%, 1Y: {curve['y_1y']}%, 10Y: {curve['y_10y']}%, 30Y: {curve['y_30y']}%")

# 获取宏观期限利差与投顾配置建议
analysis = wk.bonds.get_term_spreads_analysis()
print(f"10Y-1Y 利差: {analysis['term_spread_10y_1y_bp']} bp, 10Y-3Y 利差: {analysis.get('term_spread_10y_3y_bp')} bp")
print(f"形态: {analysis['curve_regime']} | 投顾建议: {analysis['advisory_recommendation']}")
```

### 3.6 场内 ETF 份额规模与资金流动
```python
# 估算资金净流入榜前 5 名 ETF
df_etf_in = wk.etf.get_top_inflow_etfs(top_n=5)
print(df_etf_in[["etf_code", "etf_name", "category", "shares_billion", "est_net_inflow_billion"]])

# 大类资产 (宽基 vs 行业主题 vs 策略红利 vs 固收商品) 流向聚类统计
df_cat = wk.etf.get_category_flow_summary()
print(df_cat)
```

### 3.7 一键全景增量入湖与 DuckDB SQL 即席查询
```python
# 一键同步全量扩展数据集
sync_report = wk.sync_all(force=True)

# 统一 SQL 即席查询
df_sql = wk.query("""
    SELECT symbol, name, asset_class 
    FROM v_user_watchlist 
    WHERE asset_class = 'index'
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
- 输出板块代码、行业名称、最新指数、涨跌幅、主力净流入、超大单/大单细分拆解及领涨龙头股。
- 支持 `--sector` 按申万一级行业名称单向精准下潜。

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
- 输出 ETF 代码、简称、交易所、分类、最新份额、单位净值、规模、单日份额变动与估算净流入。
- 输出五大大类属性资金聚类看板。

### 4.7 一键增量入湖：`sync-toolkit`
```bash
python wind_cli.py sync-toolkit [--force]
```
- 一键批量将自选资产、F10 财务、分红流水、行业资金流、中债曲线与 ETF 份额增量更新入本地湖仓，并刷新 DuckDB 视图。

---

## 5. 本地湖仓与 DuckDB 视图字典

工作区本地湖仓基于 **DuckDB + Parquet** 构建，存储于 `data/` 下。通过统一视图提供纯 SQL 查询体验：

### 5.1 视图清单

| 视图名 | 底层 Parquet 路径 | 说明 | 推荐查询字段 |
| :--- | :--- | :--- | :--- |
| `v_user_watchlist` | `master/user_watchlist.parquet` | 用户自选与工作台监控标的 | `symbol`, `name`, `asset_class`, `source`, `extra_info` |
| `v_stock_financials` | `mart/stock_financials.parquet` | 上市公司 F10 财务指标宽表 | `symbol`, `stock_name`, `report_date`, `total_revenue_billion`, `net_profit_billion`, `roe_pct` |
| `v_stock_dividends` | `mart/stock_dividends.parquet` | 历史分红送配与股息率记录 | `symbol`, `stock_name`, `report_date`, `cash_dividend_10`, `dividend_yield_pct`, `progress` |
| `v_sector_money_flow` | `mart/sector_money_flow.parquet` | 申万/万得行业板块资金流向 | `sector_code`, `sector_name`, `latest_index`, `change_pct`, `main_net_inflow_billion`, `top_stock_name` |
| `v_chinabond_yield_curve`| `macro/chinabond_yield_curve.parquet` | 中债国债与信用债收益率曲线 | `date`, `y_1y`, `y_10y`, `y_30y`, `term_spread_10y_1y_bp`, `credit_spread_3y_aaa_bp`, `curve_regime` |
| `v_etf_flows` | `mart/etf_flows.parquet` | 场内 ETF 份额与资金流动 | `etf_code`, `etf_name`, `market`, `category`, `shares_billion`, `nav`, `aum_billion`, `est_net_inflow_billion` |

### 5.2 常用关联查询示例

#### 示例 1: 穿透投顾自选股票的最新财务含金量与分红率
```sql
SELECT 
    w.symbol, 
    w.name, 
    f.report_date, 
    f.total_revenue_billion, 
    f.net_profit_billion, 
    f.roe_pct, 
    d.dividend_yield_pct,
    d.cash_dividend_10
FROM v_user_watchlist w
JOIN v_stock_financials f ON w.symbol = f.symbol
LEFT JOIN v_stock_dividends d ON w.symbol = d.symbol AND f.report_date = d.report_date
WHERE w.asset_class IN ('stock', 'other')
ORDER BY f.roe_pct DESC;
```

#### 示例 2: 行业板块主力资金净流入与对应行业 ETF 资金流动交叉验证
```sql
SELECT 
    f.sector_name,
    f.main_net_inflow_billion AS sector_inflow_billion,
    f.change_pct AS sector_change_pct,
    e.etf_code,
    e.etf_name,
    e.est_net_inflow_billion AS etf_inflow_billion
FROM v_sector_money_flow f
LEFT JOIN v_etf_flows e ON e.etf_name LIKE '%' || f.sector_name || '%'
WHERE f.main_net_inflow_billion > 5.0
ORDER BY f.main_net_inflow_billion DESC;
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
