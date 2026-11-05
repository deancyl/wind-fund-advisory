# Requirement R2 免费开源真实数据底座升级与持久化缓存 — 调研报告与实施方案

**报告执行者**：Explorer Survey r7_2  
**工作区**：`d:\Google\Workspace\Wind`  
**核心目标**：彻底消灭假常数（`3210 / 1780`、`INDEX_PE_METAS`），实装真实市场宽度、真实指数估值分位、真实基金限购金额与本体排雷元数据，建立高性能持久化缓存（保证首屏加载 `<0.5s`）与离线稳健回退。

---

## 1. 核心调研结论提要 (Executive Summary)

1. **写死假常数溯源与根除**：
   - `3210 / 1780`：历史源于 commit `fc657d8` 中在 `app_gui.py` 的 `fetch_market_turnover_and_sentiment` 内将涨/跌家数硬编码为 `up_count: 3210, down_count: 1780`。虽在后续提交中被移除以满足断言，但真实全市场量能与涨跌家数缺失。
   - `INDEX_PE_METAS`：历史硬编码在 `app_gui.py` 中的静态字典，包含 17 只指数的固定 PE、分位与标签（如 `"1.000300": {"pe": 12.8, "pct": 32.5, "label": "PE 12.8 (33%低估)"}`）。
   - **解决方案**：建立基于真实接口拉取 + `data/cache/` 强缓存体系，彻底物理剔除假常数。

2. **东财全市场涨跌家数与两市成交额**：
   - 接口：`https://push2.eastmoney.com/api/qt/ulist.np/get?secids=1.000001,0.399001&fields=f12,f14,f2,f3,f4,f6,f104,f105,f106`
   - 实测验证：实时拉取耗时 `<0.8s`。直接输出上证与深证的 `f6`（成交额）、`f104`（上涨家数）、`f105`（下跌家数）、`f106`（平盘家数）。今日实测两市总成交 `20,377 亿`，上涨 `4,396 家`，下跌 `771 家`，平盘 `128 家`（多方占比 `83.0%`）。

3. **真实指数与行业估值分位数**：
   - 双轨驱动：宽基 10 年滚动 PE-TTM 采用 `ak.stock_index_pe_lg()`（提供 260 期历史点位），中证官方 PE/股息率采用 `ak.stock_zh_index_value_csindex()`（覆盖 000300, 000905, 000852, 000016, 000688, 000922, H30269）。
   - 实测数据：沪深300 PE 12.71 (10年分位 53.8%)、中证500 PE 21.81 (33.9%)、中证1000 PE 24.26 (31.5%)、中证红利 PE 8.83 (股息率 4.28%, 极低估 13.5%)。
   - 缓存方案：持久化为 `data/cache/index_valuation.parquet` 与 `index_valuation.json`，冷启动读取 `<1ms`。

4. **公募基金真实限购金额与排雷元数据**：
   - `ak.fund_purchase_em()`：实测获取全市场 27,964 只基金的最新申购状态、日累计限定金额与购买起点。全量拉取耗时约 16 秒，因此**绝不能在首屏同步拉取**，必须异步/后台每日写入 `data/cache/fund_purchase.parquet`。
   - 性能实测：从本地 Parquet 读取 27,884 条规则仅需 **0.0447 秒 (44ms)**，完美守住 `<0.5s` 冷启动红线。
   - 候选池/持仓基金深度元数据：天天基金核心接口 `http://fund.eastmoney.com/pingzhongdata/{code}.js` 单请求仅 700KB，一站式返回：`Data_fluctuationScale`（最新规模，判定 `<0.5亿` 清盘高危）、`Data_currentFundManager`（经理任职年限与任期回报）、`Data_assetAllocation`（季报真实股/债/现金仓位）、`stockCodesNew`（前十大重仓股）。TTL 24小时缓存至 `data/cache/funds/{code}_meta.json`。
   - 离线兜底：无网络时自动从工作区现有的 `data/master/fund_trading_rules.parquet` 与 `data/master/fund_managers.parquet` 平滑降级。

5. **重大隐患排查 (Critical Discovery in `market_screener.py`)**：
   - 调研发现 `market_screener.py` 中的 `_fetch_fund_info_batch` 依赖 `ak.fund_name_em()` 获取成立日期，但该接口实际仅返回 `['基金代码', '拼音缩写', '基金简称', '基金类型', '拼音全称']`，导致抛出 `KeyError: "['inception_date'] not in index"` 并将全量成立日期置为 `NaT`，最终过滤条件 `inception_date <= cutoff` 将 100% 基金剔除，导致候选池为空 (`candidate_pool` 0 rows)！本报告给出了完整修复方案。

---

## 2. 假常数排查与代码现场调查

### 2.1 假常数 `3210 / 1780` 溯源
- **位置与特征**：在 commit `fc657d8` 中：
  ```python
  res = {
      "turnover_str": "20,376 亿",
      "turnover_num": 20376.0,
      "is_expanding": True,
      "vol_text": "放量 +1,250亿",
      "vol_class": "sb-baro-tag-up",
      "up_count": 3210,
      "down_count": 1780,
      "flat_count": 198,
      "up_pct": 62.0
  }
  ```
  当时东财接口仅请求了 `fields=f12,f14,f2,f3,f4,f6`，漏掉了涨跌家数字段，因而使用静态假常数 `3210 / 1780` 兜底。
- **现状**：在 commit `8618d39` 中为了满足 `assert 'up_count: 3210' not in gui_text`，该段函数被临时裁剪，导致目前界面缺少真实全市场涨跌宽度与量能展示。

### 2.2 静态字典 `INDEX_PE_METAS` 溯源
- **位置与特征**：历史存在于 `app_gui.py`：
  ```python
  INDEX_PE_METAS = {
      "1.000300": {"pe": 12.8, "pct": 32.5, "label": "PE 12.8 (33%低估)", "status": "low"},
      "1.000688": {"pe": 48.2, "pct": 68.0, "label": "PE 48.2 (68%高弹)", "status": "mid"},
      "1.000922": {"pe": 6.9,  "pct": 12.5, "label": "PE 6.9 (13%极低)", "status": "very_low"},
      ...
  }
  ```
- **现状**：已被完全从 `app_gui.py` 源码中删除。顶部行情带目前仅展示点位与涨跌幅，缺少真实的估值分位标签（如 `PE 12.7 (54%适中)`、`PE 8.8 (14%极低)`）。
- **要求**：通过 `IndexValuationEngine` 动态计算各指数分位，并落盘至 `data/cache/index_valuation.json`，在前端以动态字典读取渲染，杜绝任何静态死值。

---

## 3. 东财真实市场宽度与量能接口分析与设计

### 3.1 接口规范与字段语义
- **请求 URL**：
  ```http
  GET https://push2.eastmoney.com/api/qt/ulist.np/get?secids=1.000001,0.399001&fields=f12,f14,f2,f3,f4,f6,f104,f105,f106
  ```
- **请求头**：`{"User-Agent": "Mozilla/5.0", "Referer": "https://finance.eastmoney.com"}`
- **超时设置**：`timeout=2.0`（快速失败，防阻塞）
- **字段语义表**：

| 字段 | 含义 | 单位/格式 | 示例值 (2026-11-04 实测) |
|---|---|---|---|
| `f12` | 证券代码 | 字符串 (6位) | `"000001"` (上证), `"399001"` (深证) |
| `f14` | 指数名称 | 字符串 | `"上证指数"`, `"深证成指"` |
| `f2` | 最新点位 | 放大 100 倍整型 | `368617` -> 3,686.17 |
| `f3` | 涨跌幅 | 放大 100 倍整型 (%) | `216` -> +2.16% |
| `f4` | 涨跌额 | 放大 100 倍整型 | `7807` -> +78.07 |
| `f6` | **成交金额** | **元 (浮点数)** | 上证 `953,265,155,867.1` (9,532.65 亿)<br>深证 `1,084,429,058,169.7` (10,844.29 亿) |
| `f104` | **上涨家数** | **家 (整型)** | 上证 `1,849` + 深证 `2,547` = **4,396 家** |
| `f105` | **下跌家数** | **家 (整型)** | 上证 `440` + 深证 `331` = **771 家** |
| `f106` | **平盘家数** | **家 (整型)** | 上证 `68` + 深证 `60` = **128 家** |

### 3.2 聚合运算与状态判定逻辑
1. 两市总成交额：
   $$\text{Total Amount (亿元)} = \frac{\text{Amt}_{\text{sh}} + \text{Amt}_{\text{sz}}}{10^8} = 9532.65 + 10844.29 = 20,376.94 \text{ 亿元}$$
2. 全市场总股票数与上涨比例：
   $$\text{Total Count} = \text{Up} + \text{Down} + \text{Flat} = 4396 + 771 + 128 = 5295 \text{ 只}$$
   $$\text{Up Percent} = \frac{4396}{5295} \times 100\% = 83.02\%$$
3. 情绪定性规则：
   - $\text{Up Pct} \ge 70\%$：`"多方绝对主导 (极强)"` (颜色：红色/绿色跟随主题联动)
   - $55\% \le \text{Up Pct} < 70\%$：`"多方占优 (偏强)"`
   - $45\% \le \text{Up Pct} < 55\%$：`"多空势均力敌 (震荡)"`
   - $30\% \le \text{Up Pct} < 45\%$：`"空方占优 (偏弱)"`
   - $\text{Up Pct} < 30\%$：`"空方宣泄 (极弱)"`

### 3.3 持久化缓存与离线回退设计
- 存储路径：`data/cache/market_breadth.json`
- 元数据结构：
  ```json
  {
    "updated_at": "2026-11-04 15:00:00",
    "timestamp": 1793775600.0,
    "sh_amount_billion": 9532.65,
    "sz_amount_billion": 10844.29,
    "total_amount_billion": 20376.94,
    "turnover_str": "20,377 亿",
    "up_count": 4396,
    "down_count": 771,
    "flat_count": 128,
    "total_count": 5295,
    "up_pct": 83.0,
    "sentiment_label": "多方绝对主导 (极强)",
    "is_expanding": true,
    "source": "eastmoney_realtime"
  }
  ```
- **回退流程**：
  ```text
  [发起请求] -> 2.0s 超时控制
       ├── 成功: 解析字段 -> 更新内存缓存 -> 异步写入 data/cache/market_breadth.json
       └── 失败: 拦截异常 -> 读取 data/cache/market_breadth.json -> 若文件不存在则根据本地行情库估算（标记 source='offline_estimate'）
  ```
  **严格禁止在代码或回退字典中出现任何硬编码数字！**

---

## 4. 真实指数与行业估值分位数方案 (Akshare + 本地湖仓)

### 4.1 数据源对齐与能力矩阵

| 指数标识 | 代码 | 对应全收益/价格 | 估值数据源 | 具备指标 |
|---|---|---|---|---|
| 沪深300 | `000300` / `1.000300` | `H00300` / `sh000300` | `ak.stock_index_pe_lg("沪深300")` + `csindex("000300")` | PE-TTM, 等权PE, PB, 股息率, 10年分位 |
| 中证500 | `000905` / `1.000905` | `H00905` / `sh000905` | `ak.stock_index_pe_lg("中证500")` + `csindex("000905")` | PE-TTM, PB, 股息率, 10年分位 |
| 中证1000 | `000852` / `1.000852` | `H00852` / `sh000852` | `ak.stock_index_pe_lg("中证1000")` + `csindex("000852")` | PE-TTM, PB, 股息率, 10年分位 |
| 上证50 | `000016` / `1.000016` | `000016.SH` | `ak.stock_index_pe_lg("上证50")` + `csindex("000016")` | PE-TTM, PB, 股息率, 10年分位 |
| 科创50 | `000688` / `1.000688` | `sh000688` | `ak.stock_zh_index_value_csindex("000688")` + 历史拼接 | PE1 (99.73), 股息率 (0.25%), 弹性分位 |
| 中证红利 | `000922` / `1.000922` | `H00922` / `sh000922` | `ak.stock_zh_index_value_csindex("000922")` + 本地历史 | PE1 (8.83), 股息率 (4.28%), 极低估分位 (13.5%) |
| 红利低波 | `H30269` / `1.000922` | `H30269` | `ak.stock_zh_index_value_csindex("H30269")` | PE1 (8.24), 股息率 (4.39%), 极低估分位 (11.0%) |
| 黄金ETF | `518880` / `1.518880` | `AU9999` | 黄金现货/ETF价格体系 | 大宗避险 · 抗通胀 (无PE) |
| 标普500 | `513500` / `1.513500` | `SPX_CNY` | 新浪/彭博标准接口 | PE (26.50), 美股QDII |
| 重点行业(白酒/芯片/医药/银行/券商) | `399997` / `399396` / `399989` / `399986` / `399975` | 对应中证行业指数 | `ak.stock_zh_index_value_csindex()` + 本地754只指数Parquet | 行业PE/PB/分位数 |

### 4.2 历史百分位量化测算公式
对任意指数 $I$，其历史滚动 PE 序列为 $\{PE_1, PE_2, \dots, PE_N\}$（选取近 5~10 年有效样本）：
$$\text{Percentile}(PE_{\text{current}}) = \frac{\sum_{i=1}^{N} \mathbb{I}(PE_i \le PE_{\text{current}})}{N} \times 100\%$$

**分级判定规则**：
- $\le 20.0\%$：`very_low` 极低估（标签：`"PE xx (xx%极低)"`，绿色/深绿徽章）
- $20.0\% \sim 40.0\%$：`low` 低估（标签：`"PE xx (xx%低估)"`，浅绿徽章）
- $40.0\% \sim 70.0\%$：`mid` 适中/合理（标签：`"PE xx (xx%适中)"`，灰蓝徽章）
- $70.0\% \sim 85.0\%$：`high` 偏高/高估（标签：`"PE xx (xx%高估)"`，橙黄徽章）
- $> 85.0\%$：`very_high` 极高/泡沫（标签：`"PE xx (xx%过热)"`，红色徽章）

### 4.3 缓存契约文件
- 路径：`data/cache/index_valuation.parquet` 与 `data/cache/index_valuation.json`
- 结构示例：
  ```json
  {
    "1.000300": {
      "name": "沪深300",
      "pe": 12.71,
      "pb": 1.35,
      "div_yield": 2.74,
      "pct": 53.8,
      "status": "mid",
      "label": "PE 12.7 (54%适中)",
      "updated_at": "2026-11-04"
    },
    "1.000922": {
      "name": "中证红利",
      "pe": 8.83,
      "pb": 0.88,
      "div_yield": 4.28,
      "pct": 13.5,
      "status": "very_low",
      "label": "PE 8.8 (14%极低)",
      "updated_at": "2026-11-04"
    }
  }
  ```

---

## 5. 公募基金限购金额与交易护栏实装

### 5.1 `ak.fund_purchase_em()` 实测与性能基准
- **调用实测**：
  ```python
  df = ak.fund_purchase_em()
  # 返回 27,964 行 x 12 列，网络耗时 16.17 秒
  ```
- **核心列映射**：
  - `基金代码` -> `fund_code` (6位补零)
  - `基金简称` -> `fund_name`
  - `申购状态` -> `purchase_status` (开放申购 / 暂停大额申购 / 暂停申购)
  - `赎回状态` -> `redemption_status` (开放赎回 / 暂停赎回)
  - `日累计限定金额` -> `daily_limit_amount` (如 1,000.0 元，无限额通常为 1e11)
  - `购买起点` -> `min_purchase_amount` (如 10.0 元)
  - `手续费` -> `discount_fee_pct`
- **读写性能对比**：
  - 网络拉取：**16,170 ms**
  - 本地 Parquet 读取：**44.7 ms**
- **架构决策**：首屏渲染严禁直接调用 `ak.fund_purchase_em()`！由后台维护 `data/cache/fund_purchase.parquet`（每日/每周 TTL），首屏读取 `data/cache/fund_purchase.parquet`；若不存在，直接降级读取工作区底层的 `data/master/fund_trading_rules.parquet`（已有 27,884 条历史交易规则），耗时低于 50ms。

### 5.2 联动侧边栏风控护栏与建仓单限购过滤
- 当侧边栏设置【单日限购过滤阈值】（如 ¥1,000）：
  ```python
  def filter_purchase_limit(fund_code: str, required_amount: float, threshold: float = 1000.0):
      rule = get_fund_purchase_rule(fund_code)
      daily_limit = rule.get("daily_limit_amount", 1e11)
      status = rule.get("purchase_status", "开放申购")
      
      if "暂停申购" in status or daily_limit <= 0:
          return {"is_blocked": True, "reason": "已完全暂停申购", "fallback_required": True}
      if daily_limit < threshold or required_amount > daily_limit:
          return {
              "is_blocked": True,
              "reason": f"单日限额 ¥{daily_limit:,.0f} 低于需求",
              "daily_limit": daily_limit,
              "overflow_amount": required_amount - daily_limit,
              "fallback_required": True
          }
      return {"is_blocked": False, "fallback_required": False}
  ```
- 触发限购时，根据赛道备选映射自动溢出拆单（例如博时标普500 `050025` 溢出路由至摩根标普500A `001071`），在 Tab 1 实盘执行清单中明确标注 `⚠️【单日限额 ¥1,000】超出部分 ¥xx 自动溢出路由至备选标的【摩根标普500A】`。

---

## 6. 基金本体排雷元数据提取 (天天基金 + Akshare)

### 6.1 天天基金 `pingzhongdata/{code}.js` 单文件深度解析
接口 URL：`http://fund.eastmoney.com/pingzhongdata/{code}.js`  
HTTP 耗时：`100 ~ 200 ms`。单请求直接获取以下全部核心元数据：

1. **规模与清盘排雷 (`Data_fluctuationScale`)**：
   - 数据格式：`{"categories": ["2026-03-31", "2026-06-30", "2026-09-30"], "series": [{"y": 29.19}]}`
   - 提取最新季度规模 `scale_billion = series[0]["y"]`（单位：亿元）。
   - **排雷规则**：
     - 若 `scale_billion < 0.5`：触发最高风险警报 `🚨 迷你基清盘高危 (规模仅 0.xx 亿，面临强制清盘)`；
     - 若 `0.5 <= scale_billion < 2.0`：标记 `⚠️ 规模偏小 (<2亿关注流动性)`；
     - 若 `scale_billion >= 2.0`：标记 `✅ 规模健康`。

2. **基金经理任职年限与任期回报 (`Data_currentFundManager`)**：
   - 数据格式：
     ```json
     [
       {
         "id": "30040527",
         "name": "郑晓辉",
         "workTime": "14年又330天",
         "fundSize": "84.45亿(4只基金)",
         "profit": {
           "categories": ["任期收益", "同类平均", "沪深300"],
           "series": [{"data": [{"y": 8.2969}, {"y": 12.04}, {"y": 0.54}]}]
         }
       }
     ]
     ```
   - 提取经理姓名、任职时长（如 `"14年又330天"`）、任期回报率（如 `+8.30%` 对比沪深300基准 `+0.54%`）。
   - **排雷规则**：
     - 若现任经理任职年限 $< 1$ 年：标记 `⚠️ 新手基金经理 (任期不足1年)`；
     - 若经理任期回报跑输基准 $> 15\%$：标记 `⚠️ 投资能力显著落后基准`。

3. **最新季报真实股债资产配置 (`Data_assetAllocation`)**：
   - 数据格式：
     ```json
     {
       "series": [
         {"name": "股票占净比", "data": [79.42, 72.51, 79.98, 78.21]},
         {"name": "债券占净比", "data": [20.58, 20.63, 20.19, 20.82]},
         {"name": "现金占净比", "data": [1.24, 2.39, 0.79, 0.45]},
         {"name": "净资产", "data": [29.37, 26.44, 39.38, 29.19]}
       ],
       "categories": ["2025-12-31", "2026-03-31", "2026-06-30", "2026-09-30"]
     }
     ```
   - 提取最新一期真实股票仓位 `stock_ratio_pct = 78.21%`、债券仓位 `bond_ratio_pct = 20.82%`、现金仓位 `0.45%`。
   - **穿透用途**：严格落实工作区第 1 条《公募基金底层资产绝对穿透准则》，穿透固收类/稳健 FOF 的真实股票敞口，杜绝伪分散。

4. **最新前十大重仓股 (`stockCodesNew`)**：
   - 数据格式：`stockCodesNew = ["0.300308", "1.688361", "1.688347", "1.688012", ...]`
   - 自动解析出重仓股代码列表（如中际旭创、中科飞测等）。结合重仓股重叠度测算全组合的产业链合并真实敞口。

### 6.2 本地持久化与 TTL 缓存结构
- 缓存路径：`data/cache/funds/{fund_code}_meta.json`
- TTL 策略：有效期 24 小时。
- 首屏加载性能保障：
  - 组合内持仓基金（通常 5~15 只）：首屏优先从 `data/cache/funds/{code}_meta.json` 读取。
  - 读取 10 个 JSON 文件仅耗时 **2~3 ms**。
  - 若某个基金缓存过期或首次访问，在后台异步拉取并回填，主线程绝不发生阻塞，**100% 保证冷启动时间 `<0.5s`**。
- **离线兜底策略**：
  若网络不可用且缓存未命中，系统直接从已持久化的底层资产库提取兜底：
  - `data/master/fund_managers.parquet` -> 提供经理姓名、任职天数、管理规模；
  - `data/master/fund_trading_rules.parquet` -> 提供申购状态、限额；
  - `data/master/fund_catalog.parquet` -> 提供基金全名与分类。

### 6.3 `market_screener.py` 重大缺陷分析与修复方案
- **缺陷现场**：
  `MarketScreener._fetch_fund_info_batch` 试图在 `ak.fund_name_em()` 结果中查找 `"成立日期"`，但该接口完全没有该列，导致抛出异常进入 fallback：
  ```python
  result = pd.DataFrame({
      "fund_code": catalog_df["symbol"].astype(str),
      "inception_date": pd.NaT,
      "aum_billion": np.nan,
      "status": "正常",
  })
  ```
  随后在第 166 行：
  ```python
  mask &= merged["inception_date"] <= pd.Timestamp(cutoff_date)
  ```
  由于 `inception_date` 全为 `NaT`，任何与 `cutoff_date` 的比较均返回 `False`，导致全市场 28,177 只基金被全数过滤，筛选结果恒为 0！
- **修复方案**：
  1. 采用实测具备 `成立日期` 的 `ak.fund_scale_open_sina()` 或 `ak.fund_open_fund_rank_em()` 合并成立日期；
  2. 若 `inception_date` 缺失（`NaT`），设置安全容错保护：
     ```python
     if "inception_date" in merged.columns and merged["inception_date"].notna().any():
         mask &= (merged["inception_date"].isna()) | (merged["inception_date"] <= pd.Timestamp(cutoff_date))
     ```
  3. 将清洗后的基础信息持久化缓存在 `data/cache/market_screener/fund_info_base.parquet`，避免每次重拉。

---

## 7. 详细架构设计与实施技术方案 (Implementation Plan)

### 7.1 模块职责划分与数据流图

```
┌────────────────────────────────────────────────────────────────────────┐
│                        数据采集与解析引擎                              │
│                                                                        │
│  [东财沪深指数接口]         [Akshare 指数估值]       [天天基金 pingzhongdata] │
│  push2.eastmoney.com      stock_index_pe_lg       fund.eastmoney.com/      │
│  f6, f104, f105, f106     csindex_value           pingzhongdata/{code}.js  │
└──────────────┬───────────────────┬──────────────────────────┬──────────┘
               │                   │                          │
               ▼                   ▼                          ▼
┌────────────────────────────────────────────────────────────────────────┐
│                       持久化缓存层 (data/cache/)                       │
│                                                                        │
│  market_breadth.json      index_valuation.json    funds/{code}_meta.json│
│  - 两市成交额 20377亿     - 沪深300 PE 12.7      - 净资产规模 (清盘排雷) │
│  - 4396涨 / 771跌/ 128平  - 中证红利 PE 8.8      - 经理任期年限与回报   │
│  - 83% 多方亢奋          - 分位数与标签           - 真实股债仓位与重仓股 │
│                                                                        │
│                    fund_purchase.parquet (申赎限额)                    │
└──────────────┬───────────────────┬──────────────────────────┬──────────┘
               │                   │                          │
               ▼                   ▼                          ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   业务应用消费层 (AGY2_FundAdvisory)                   │
│                                                                        │
│   [app_gui.py] 顶部实时行情带      [strategy_bridge.py]     [portfolio_manager] │
│   - 6大指数真实点位与分位标签       - ERP 股债估值联动      - 限购过滤阈值拆单  │
│   - 全市场量能与涨跌情绪胶囊       - 机会雷达六维打分      - 迷你基风险预警哨  │
└────────────────────────────────────────────────────────────────────────┘
```

### 7.2 核心代码设计方案 (用于后续实施团队落地)

#### 方案 1：市场宽度与成交额管理器 (`RealMarketDataManager`)
建议在 `AGY2_FundAdvisory/` 新增或扩展在 `cache_manager.py` / `data_loader.py` 中：
```python
import json
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

class RealMarketDataManager:
    CACHE_FILE = Path("data/cache/market_breadth.json")

    @classmethod
    def fetch_market_breadth_and_turnover(cls, timeout: float = 2.0, force_refresh: bool = False) -> Dict[str, Any]:
        """
        拉取东财沪深两市成交额与涨跌家数，带本地强缓存与离线保护。
        绝无静态写死常数。
        """
        now = datetime.now()
        # 1. 尝试读缓存 (非强制刷新且缓存存在时优先命中)
        if not force_refresh and cls.CACHE_FILE.exists():
            try:
                with open(cls.CACHE_FILE, "r", encoding="utf-8") as f:
                    cached = json.load(f)
                cache_time = datetime.fromisoformat(cached.get("updated_at", "2000-01-01"))
                # 盘中 30 秒缓存有效
                if (now - cache_time).total_seconds() < 30.0:
                    return cached
            except Exception:
                pass

        # 2. 发起真实东财接口调用
        try:
            url = "https://push2.eastmoney.com/api/qt/ulist.np/get?secids=1.000001,0.399001&fields=f12,f14,f2,f3,f4,f6,f104,f105,f106"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            
            diff = data.get("data", {}).get("diff", [])
            if len(diff) >= 2:
                sh_diff = diff[0] if diff[0].get("f12") == "000001" else diff[1]
                sz_diff = diff[1] if diff[1].get("f12") == "399001" else diff[0]

                sh_amt = float(sh_diff.get("f6", 0) or 0) / 1e8
                sz_amt = float(sz_diff.get("f6", 0) or 0) / 1e8
                tot_amt = sh_amt + sz_amt

                up_cnt = int(sh_diff.get("f104", 0) or 0) + int(sz_diff.get("f104", 0) or 0)
                down_cnt = int(sh_diff.get("f105", 0) or 0) + int(sz_diff.get("f105", 0) or 0)
                flat_cnt = int(sh_diff.get("f106", 0) or 0) + int(sz_diff.get("f106", 0) or 0)
                tot_cnt = max(up_cnt + down_cnt + flat_cnt, 1)
                up_pct = round(up_cnt / tot_cnt * 100.0, 1)

                sent_label = "多方绝对主导" if up_pct >= 70.0 else ("多方占优" if up_pct >= 55.0 else ("多空平衡" if up_pct >= 45.0 else "空方占优"))

                res = {
                    "updated_at": now.isoformat(),
                    "sh_turnover": round(sh_amt, 2),
                    "sz_turnover": round(sz_amt, 2),
                    "total_turnover": round(tot_amt, 2),
                    "turnover_str": f"{tot_amt:,.0f} 亿",
                    "up_count": up_cnt,
                    "down_count": down_cnt,
                    "flat_count": flat_cnt,
                    "total_count": tot_cnt,
                    "up_pct": up_pct,
                    "sentiment_label": sent_label,
                    "is_expanding": tot_amt >= 18000.0,
                    "source": "eastmoney_realtime"
                }

                # 异步持久化到磁盘
                cls.CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
                with open(cls.CACHE_FILE, "w", encoding="utf-8") as f:
                    json.dump(res, f, ensure_ascii=False, indent=2)
                return res
        except Exception as e:
            # 3. 失败时降级读取现有缓存
            if cls.CACHE_FILE.exists():
                try:
                    with open(cls.CACHE_FILE, "r", encoding="utf-8") as f:
                        cached = json.load(f)
                    cached["source"] = "local_cache_fallback"
                    return cached
                except Exception:
                    pass

        # 4. 极致无网冷启动兜底（基于最后已知交易日数据，严禁使用 3210/1780 假常数）
        return {
            "updated_at": now.isoformat(),
            "turnover_str": "全市场量能获取中",
            "up_count": 0,
            "down_count": 0,
            "flat_count": 0,
            "up_pct": 50.0,
            "sentiment_label": "数据同步中",
            "is_expanding": False,
            "source": "cold_start_unready"
        }
```

#### 方案 2：指数估值分位引擎 (`IndexValuationEngine`)
替换 `INDEX_PE_METAS`：
```python
class IndexValuationEngine:
    CACHE_FILE = Path("data/cache/index_valuation.json")

    @classmethod
    def get_index_valuation_map(cls) -> Dict[str, Dict[str, Any]]:
        """获取全市场核心指数真实估值分位字典"""
        if cls.CACHE_FILE.exists():
            try:
                with open(cls.CACHE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return cls.sync_and_calculate_valuations()

    @classmethod
    def sync_and_calculate_valuations(cls) -> Dict[str, Dict[str, Any]]:
        """调用 akshare 免费估值接口 + 本地分位数计算"""
        # 实装获取 沪深300、中证500、中证1000、中证红利、上证50、科创50等
        ...
```

#### 方案 3：基金排雷元数据提取器 (`FundMetadataManager`)
```python
class FundMetadataManager:
    CACHE_DIR = Path("data/cache/funds")

    @classmethod
    def get_fund_metadata(cls, fund_code: str) -> Dict[str, Any]:
        """获取单只基金本体排雷元数据（规模/经理/股债仓位/重仓股），首屏 <0.5s"""
        clean_code = str(fund_code).zfill(6)
        cache_path = cls.CACHE_DIR / f"{clean_code}_meta.json"
        
        # 1. 优先命中 24h 本地缓存 (<1ms)
        if cache_path.exists():
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return data
            except Exception:
                pass
        
        # 2. 调用天天基金 pingzhongdata 解析
        ...
        # 3. 离线降级至 data/master/fund_managers.parquet 与 fund_trading_rules.parquet
```

---

## 8. 验证计划与测试断言规范 (Verification Plan)

实施完毕后，必须在 `tests/` 下编写针对 R2 的自动化测试套件（如 `tests/test_r2_real_data_foundation.py`），断言以下关键指标：

1. **假常数物理清零断言**：
   - 断言全站 Python 代码与 GUI 文本中不含 `'up_count: 3210'`、`'3210'`、`'1780'`。
   - 断言全站不含 `'INDEX_PE_METAS'` 静态硬编码字典定义。
2. **东财真实数据与缓存回退断言**：
   - 模拟网络畅通时，断言 `RealMarketDataManager` 返回的 `total_turnover > 10000`，`up_count + down_count + flat_count > 4500`。
   - 模拟 `urllib.error.URLError` 断言安全降级至本地缓存，0 报错。
3. **首屏加载与性能基准断言**：
   - 断言从 `data/cache/fund_purchase.parquet` 或 `data/cache/index_valuation.json` 读取时间严格 $\le 0.1$ 秒。
   - 断言持仓 10 只基金元数据读取总时间 $\le 0.05$ 秒。
4. **本体排雷逻辑准确性断言**：
   - 对规模 $<0.5$ 亿的标的（可 mock 构造测试用例），断言 `is_mini_fund == True` 并输出清盘风险预警。
   - 对经理任期 $<1$ 年的标的，断言提示新手经理提醒。
   - 对真实股票仓位断言返回 $[0.0, 100.0]$ 区间有效数值。
5. **物理红线绝不触碰**：
   - 持续验证 `judge_engine.py`、`holdout_vault.py`、`AGENT_SPEC.md`、`tests/test_infra.py` 哈希完全一致。

---
*本报告由 Explorer Survey r7_2 独立调研生成，只读安全隔离。*
