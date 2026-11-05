# Phase 0 技术调研报告：R5、R6 与 R8 深度架构剖析与整改方案

**调研时间**: 2026-11-05  
**调研范围**: 
1. **R5**: Tab 4 穿透工具底层切换与资产分类精准化
2. **R6**: 14 大赛道温度计动态指标与估值分位真实化
3. **R8**: 物理安全红线与自动化防作弊测试基线

---

## 1. Tab 4 穿透工具底层切换与资产分类精准化 (R5)

### 1.1 `portfolio_manager.py` 穿透底层函数现状与参数改造

在 `AGY2_FundAdvisory/portfolio_manager.py` 中，4 个核心底层穿透函数目前完全硬编码依赖 `self.holdings`，未暴露持仓注入接口，导致前端切换组合时后端计算脱靶。

#### 1) `calculate_look_through_industry_exposure`
- **文件路径**: `AGY2_FundAdvisory/portfolio_manager.py:4162-4206`
- **现状代码**:
  ```python
  def calculate_look_through_industry_exposure(self) -> pd.DataFrame:
      total_market_val = sum(h.market_value for h in self.holdings.values())
      if total_market_val <= 0:
          return pd.DataFrame(columns=["行业", "暴露金额", "暴露占比(%)"])
      for code, h in self.holdings.items():
          ...
  ```
- **改造方案**:
  ```python
  def calculate_look_through_industry_exposure(
      self, 
      holdings_override: Optional[Dict[str, Any]] = None
  ) -> pd.DataFrame:
      target_holdings = holdings_override if holdings_override is not None else self.holdings
      total_market_val = sum(h.market_value for h in target_holdings.values())
      if total_market_val <= 0:
          return pd.DataFrame(columns=["行业", "暴露金额", "暴露占比(%)"])
      for code, h in target_holdings.items():
          ...
  ```

#### 2) `calculate_stock_overlap_matrix`
- **文件路径**: `AGY2_FundAdvisory/portfolio_manager.py:4263-4417`
- **现状代码**:
  ```python
  def calculate_stock_overlap_matrix(self) -> Dict[str, Any]:
      active_funds = [code for code, h in self.holdings.items() if h.market_value > 0]
      ...
      fund_labels = [f"{c} {self.holdings[c].fund_name[:6]}" for c in active_funds]
      ...
      for c in pending_external_funds:
          fund_n = self.holdings[c].fund_name if c in self.holdings else c
  ```
- **改造方案**:
  ```python
  def calculate_stock_overlap_matrix(
      self, 
      holdings_override: Optional[Dict[str, Any]] = None
  ) -> Dict[str, Any]:
      target_holdings = holdings_override if holdings_override is not None else self.holdings
      active_funds = [code for code, h in target_holdings.items() if h.market_value > 0]
      ...
      fund_labels = [f"{c} {target_holdings[c].fund_name[:6]}" for c in active_funds]
      ...
      for c in pending_external_funds:
          fund_n = target_holdings[c].fund_name if c in target_holdings else c
  ```

#### 3) `get_portfolio_look_through_stocks` 与 `get_portfolio_look_through_stocks_df`
- **文件路径**: `AGY2_FundAdvisory/portfolio_manager.py:4419-4520`
- **现状代码**:
  ```python
  def get_portfolio_look_through_stocks(self, as_df: bool = False) -> Any:
      active_holdings = [h for h in self.holdings.values() if h.market_value > 0]
      total_mv = sum(h.market_value for h in active_holdings)
      ...
  def get_portfolio_look_through_stocks_df(self) -> pd.DataFrame:
      return self.get_portfolio_look_through_stocks(as_df=True)
  ```
- **改造方案**:
  ```python
  def get_portfolio_look_through_stocks(
      self, 
      as_df: bool = False,
      holdings_override: Optional[Dict[str, Any]] = None
  ) -> Any:
      target_holdings = holdings_override if holdings_override is not None else self.holdings
      active_holdings = [h for h in target_holdings.values() if h.market_value > 0]
      total_mv = sum(h.market_value for h in active_holdings)
      ...
  def get_portfolio_look_through_stocks_df(
      self, 
      holdings_override: Optional[Dict[str, Any]] = None
  ) -> pd.DataFrame:
      return self.get_portfolio_look_through_stocks(as_df=True, holdings_override=holdings_override)
  ```

#### 4) `calculate_portfolio_penetration_risk`
- **文件路径**: `AGY2_FundAdvisory/portfolio_manager.py:5315-5404`
- **现状代码**:
  ```python
  def calculate_portfolio_penetration_risk(self) -> Dict[str, Any]:
      active_holdings = [h for h in self.holdings.values() if h.market_value > 0]
      total_mv = sum(h.market_value for h in active_holdings)
      ...
  ```
- **改造方案**:
  ```python
  def calculate_portfolio_penetration_risk(
      self, 
      holdings_override: Optional[Dict[str, Any]] = None
  ) -> Dict[str, Any]:
      target_holdings = holdings_override if holdings_override is not None else self.holdings
      active_holdings = [h for h in target_holdings.values() if h.market_value > 0]
      total_mv = sum(h.market_value for h in active_holdings)
      ...
  ```

---

### 1.2 `HoldingItem` 类型定义与 `app_gui.py` 导入防御

#### 现状断层原因
在 `AGY2_FundAdvisory/portfolio_manager.py:259-279` 中，持仓类名为 `FundHolding`，不存在 `HoldingItem` 类。然而在 `app_gui.py:5210, 5228, 5245` 中：
```python
from portfolio_manager import HoldingItem
active_examine_holdings[fc] = HoldingItem(fund_code=fc, fund_name=fn, shares=m_val, cost_nav=1.0, current_nav=1.0)
```
当用户选择“新建仓组合”或“调仓后组合”或“实盘空仓”时，代码会抛出 `ImportError: cannot import name 'HoldingItem' from 'portfolio_manager'`！此外，`FundHolding` 的构造函数入参为 `cost_price` 与 `market_value`，而 `app_gui.py` 传入的是 `cost_nav=1.0` 且未显式传入 `market_value`，导致若没有 `__post_init__`，`market_value` 为 0.0，使穿透计算直接归零。

#### 解决方案
在 `portfolio_manager.py` 中显式声明 `HoldingItem` 类（或兼容 `FundHolding`），支持属性互通：
```python
@dataclass
class HoldingItem:
    fund_code: str
    fund_name: str
    shares: float = 0.0
    cost_nav: float = 1.0
    current_nav: float = 1.0
    cost_price: float = 1.0
    market_value: float = 0.0
    share_class: str = "A"

    def __post_init__(self):
        if self.cost_nav != 1.0 and self.cost_price == 1.0:
            self.cost_price = self.cost_nav
        if self.market_value <= 0.0 and self.shares > 0:
            self.market_value = round(self.shares * self.current_nav, 2)
```

---

### 1.3 Tab 4 前后端数据流打通 (`app_gui.py`)

#### 1) 缓存包装函数传递 `holdings_override`
在 `AGY2_FundAdvisory/app_gui.py:1871-1886` 中，缓存函数签名虽然接收了 `holdings_repr: str`，但函数体内部完全忽略了持仓内容，硬编码调用了 `pm` 无参方法：
- **现状代码**:
  ```python
  @st.cache_data(ttl=300)
  def _cached_look_through_industry(holdings_repr: str):
      return pm.calculate_look_through_industry_exposure()

  @st.cache_data(ttl=300)
  def _cached_stock_overlap(holdings_repr: str):
      return pm.calculate_stock_overlap_matrix()

  @st.cache_data(ttl=300)
  def _cached_penetration_risk(holdings_repr: str):
      return pm.calculate_portfolio_penetration_risk()

  @st.cache_data(ttl=300)
  def _cached_stocks_df(holdings_repr: str):
      return pm.get_portfolio_look_through_stocks_df()
  ```
- **改造方案**:
  由于 Streamlit 缓存序列化机制，可将字典以 JSON/元组形式作为缓存 key，并由 helper 函数将 `active_examine_holdings` 字典传入 `pm` 方法：
  ```python
  # 在 Tab 4 渲染逻辑中直接传入 active_examine_holdings
  df_ind = pm.calculate_look_through_industry_exposure(holdings_override=active_examine_holdings)
  overlap_res = pm.calculate_stock_overlap_matrix(holdings_override=active_examine_holdings)
  port_risk = pm.calculate_portfolio_penetration_risk(holdings_override=active_examine_holdings)
  df_scr = pm.get_portfolio_look_through_stocks_df(holdings_override=active_examine_holdings)
  ```
  或者将 `_cached_*` 调整为接收 `(holdings_dict_tuples)` 并调用 `pm.*(holdings_override=holdings_dict)`。

#### 2) 修复“聪明钱与机构抱团监控”遍历错误
- **文件路径**: `AGY2_FundAdvisory/app_gui.py:5450-5452`
- **现状代码**:
  ```python
  if len(active_examine_holdings) > 0:
      crowd_rows = []
      for code, h in pm.holdings.items():  # 严重 Bug：明明判定了 active_examine_holdings，却去遍历 pm.holdings
          c_info = pm.get_fund_smart_money_crowding(code)
  ```
- **改造方案**:
  ```python
  if len(active_examine_holdings) > 0:
      crowd_rows = []
      for code, h in active_examine_holdings.items():  # 修复为遍历 active_examine_holdings.items()
          c_info = pm.get_fund_smart_money_crowding(code)
  ```

---

### 1.4 `PortfolioManager.classify_fund_asset_class` 精准化映射与消灭“其他权益资产”

#### 1) 现状与“61.5% 其他权益资产”成因剖析
- 在历史代码中（如 `app_gui.py:194-218` 的临时 monkey-patch），当基金未能命中关键字时，粗暴返回 `"其他权益资产"`。
- 在 `portfolio_manager.py:4526-4745` 中，虽然实现了 `_compute_asset_class_category`，但当仅传入 `fund_code`（未传入 `fund_name`）时：
  1. `CORE_STRATEGY_POOL`（36只标的）仅覆盖红利、美股、宽基，不包含白酒、医药、证券、恒科；
  2. `EXTENDED_FUND_CATALOG` 仅有 1 只基金（`005827`）；
  3. `UNIVERSE_18_CHAMPION_POOL` 与 `SECTOR_FUND_SELECTION`（在 `strategy_bridge.py` 中）未在 `_compute_asset_class_category` 中被完整反查；
  4. 导致当输入外部或细分赛道代码（如 161726 医药、161725 白酒、160418 银行、013402 恒科、008888 芯片）且无名称输入时，反查名称失败或匹配规则漏洞，最终滑入通用兜底。
  5. 此外，老旧单测（`test_adversarial_orch3_challenger2.py`）仍在断言未入围基金返回 `"其他权益资产"`，而新规范与 `test_ui_pro_redesign_verification.py` 严格要求升级为 10 大专业分类且零“其他权益资产”。

#### 2) 核心全市场基金资产大类精准映射规则表

必须建立以下标准多级反查与分类字典：
反查优先级：
1. `CORE_STRATEGY_POOL`
2. `EXTENDED_FUND_CATALOG`
3. `UNIVERSE_18_CHAMPION_POOL` (定义在 `strategy_bridge.py:170`)
4. `SECTOR_FUND_SELECTION` (定义在 `portfolio_manager.py:715` 与 `strategy_bridge.py:833`)
5. 本地 DuckDB `v_fund_catalog` / `v_fund_snapshot` 真实元数据反查

| 赛道大类类别 | 规范资产分类名称 | 典型基金代码 | 覆盖关键词 / 重仓行业判定特征 |
| :--- | :--- | :--- | :--- |
| **医药医疗健康** | `医药医疗健康` | `161726` (招商医药), `003095` (中欧医疗) | 医药、医疗、生物、健康、创新药、中药、疫苗、器械、恒瑞医药、迈瑞医疗 |
| **大消费与白酒** | `大消费与白酒` | `161725` (招商白酒), `000248` (汇添富消费) | 白酒、酒、消费、食品、饮料、主要消费、贵州茅台、五粮液、山西汾酒 |
| **银行与高股息金融** | `高股息价值` | `160418` (华安银行), `100032` (富国红利) | 银行、金融、证券、保险、红利、股息、高股息、央企红利、招商银行、工商银行 |
| **港股与恒生科技** | `全球海外配置` | `013402` (华夏恒科), `006327` (易方达恒生) | 恒生、港股、互联、中概、离岸、腾讯、美团、阿里巴巴 |
| **半导体与硬科技** | `硬科技与半导体` | `008888` (华夏芯片), `013841` (银华芯片), `011612` (科创50) | 半导体、芯片、集成电路、科创、信息技术、算力、中微公司、北方华创、中芯国际 |
| **美股与全球QDII** | `全球海外配置` | `050025` (博时标普), `001071` (摩根标普), `017436` (华宝纳指) | 标普、纳斯达克、美股、纳指、QDII、S&P、NASDAQ、AAPL、NVDA、MSFT |
| **红利低波防守** | `红利低波防守` | `005561` (创金红利低波), `007466` (华泰红利低波) | 红利低波、红利低波动、红利质量低波、低波红利 |
| **宽基核心蓝筹** | `核心蓝筹基石` | `110020` (易方达300), `510300`, `110003` (上证50) | 300、沪深300、上证50、大盘、蓝筹、核心资产、A500 |
| **中小盘均衡成长** | `中盘与中小成长` | `000478` (中证500), `004194` (中证1000), `018043` (国证2000) | 500、中证500、1000、2000、中盘、小盘、中小盘、创业板 |
| **纯债与固定收益** | `纯债固收` | `002351` (易方达裕祥), `000086` (工银纯债), `003003` | 纯债、国债、中短债、短债、信用债、理财、货币、裕祥、稳益 |
| **黄金现货对冲** | `黄金抗通胀` | `000216` (华安黄金), `518880`, `002610` (博时黄金) | 黄金、AU9999、金ETF、贵金属、上海金 |

---

## 2. 14 大赛道温度计动态指标与估值分位真实化 (R6)

### 2.1 赛道目录定义与兜底回退现象溯源

在 `AGY2_FundAdvisory/advisory_engine.py:25-223` 中，定义了全市场 14 大核心赛道 `RADAR_SECTOR_CATALOG`：
1. `dividend_low_vol` (红利低波, 005561)
2. `csi_dividend` (中证红利, 100032)
3. `csi_300` (沪深300, 110020)
4. `csi_500` (中证500, 000478)
5. `csi_1000` (中证1000, 004194)
6. `star_50` (科创50, 011612)
7. `semiconductor` (半导体芯片, 008888)
8. `pharma_health` (医药医疗, 161726)
9. `consumer_liquor` (消费白酒, 161725)
10. `banking_dividend` (银行高股息, 160418)
11. `domestic_gold` (国内黄金, 000216)
12. `us_sp500_nasdaq` (美股标普纳指, 050025)
13. `hstech` (恒生科技, 013402)
14. `pure_bond` (纯债固收, 002351)

#### 兜底常量来源 (`advisory_engine.py:440-443`):
```python
dyn = self.dynamic_metrics.get(sec_id, {})
er = float(dyn.get("er_20", meta.get("er_20", 0.50)))
bias_20 = float(dyn.get("bias_20", meta.get("bias_20", 1.0)))
slope_20 = float(dyn.get("slope_20", meta.get("slope_20", 5.0)))
s_crowd = float(dyn.get("crowding_score", meta.get("crowding_score", 85.0)))
```
当 `self.dynamic_metrics` 无法为某个赛道解析出足够长度的价格序列时，该赛道会全部回退至 `0.50 / +1.0% / 85.0`！

---

### 2.2 本地数据源分层读取方案 (DuckDB + NAV Cache + 对齐矩阵)

为确保 14 个赛道 100% 具备动态计算能力，构建四级安全回退提取流水线：

```
[Level 1: 细分赛道独立日线 Parquet]
data/processed/indices/<index_code>.parquet
(已覆盖: 000685半导体, 000933医药, 000932白酒, 399986银行)
          │ (若不存在或长度 < 25)
          ▼
[Level 2: 本地 DuckDB 视图离线快速拉取]
data/storage.duckdb -> SELECT close FROM v_indices WHERE index_code LIKE '%<idx>%' ORDER BY date
(涵盖 754 个指数，包含 000933, 000932, 399986, 000685 等数千条日线)
          │ (若不存在或长度 < 25)
          ▼
[Level 3: 代表性基金 NAV 缓存]
data/cache/market_screener/nav_cache/<top_fund_code>.parquet 或 data/processed/funds/<code_OF>.parquet
(直接拉取 161726, 161725, 160418, 013402, 008888 等真实基金复权净值序列)
          │ (若不存在或长度 < 25)
          ▼
[Level 4: 大盘全景对齐矩阵]
data/processed/aligned_matrix_total_return.parquet
(覆盖 H00300, H00905, H00852, H00922, H30269, 930609, H11009, STAR50_STITCH, AU9999, SPX_CNY)
```

#### 动态指标数学公式与实现规范
从获取的日度价格/净值序列 $S = [p_1, p_2, \dots, p_T]$（$T \ge 25$）中计算：
1. **20 日考夫曼效率系数 (Kaufman Efficiency Ratio, ER20)**:
   $$\text{ER}_{20} = \text{clip}\left(\frac{|p_T - p_{T-20}|}{\sum_{k=1}^{20} |p_{T-k+1} - p_{T-k}|}, 0.10, 0.95\right)$$
2. **20 日均线乖离率 (MA20 Bias)**:
   $$\text{MA}_{20} = \frac{1}{20}\sum_{i=0}^{19} p_{T-i}, \quad \text{Bias}_{20} = \frac{p_T - \text{MA}_{20}}{\text{MA}_{20}} \times 100\%$$
3. **20 日均线斜率 (MA20 Slope)**:
   $$\text{MA}_{20,\text{prev}} = \frac{1}{20}\sum_{i=5}^{24} p_{T-i}, \quad \text{Slope}_{20} = \frac{\text{MA}_{20} - \text{MA}_{20,\text{prev}}}{\text{MA}_{20,\text{prev}}} \times 50 \times 100\%$$
4. **结合 5日/60日波动率比值的动态拥挤度 (Crowding Score)**:
   - 计算 5 日与 60 日对数收益率波动率：
     $$\sigma_5 = \text{std}(r_{T-4:T}), \quad \sigma_{60} = \text{std}(r_{T-59:T}), \quad R_{\text{vol}} = \frac{\sigma_5}{\sigma_{60} + 10^{-6}}$$
   - 基础拥挤度与波动率惩罚：
     $$\text{Crowd} = \text{clip}\left(92.0 - 2.5 \cdot \max(0, \text{Bias}_{20} - 2.0) + 4.0 \cdot (1.0 - \text{ER}_{20}) - 5.0 \cdot \max(0, R_{\text{vol}} - 1.2), 40.0, 96.0\right)$$

---

### 2.3 `get_sector_valuation_percentile` 空 pass 与假常量重构

#### 现状分析 (`advisory_engine.py:350-357`)
```python
# 特殊无 PE 与固收赛道专业中枢锚定
if sec_id in ("pure_bond", "bond"):
    return 40.0  # 利率稳健·防守底仓，严禁拿长牛收盘价算出 99%
elif sec_id in ("domestic_gold", "gold"):
    return 52.0  # 抗通胀对冲·无PE
elif sec_id in ("dividend_low_vol", "csi_dividend", "banking_dividend"):
    # 结合 PB 与股息风险溢价 (DRP) 校准至低估/适中区间 (32%~45%)
    pass
```
- **问题 1**: `pure_bond` 硬编码返回 `40.0`，`domestic_gold` 硬编码返回 `52.0`。
- **问题 2**: `dividend_low_vol`, `csi_dividend`, `banking_dividend` 分支下为空 `pass`，属于典型迎合性未完成假代码。

#### 动态真实计算方案设计
1. **纯债赛道 (`pure_bond`)**:
   - 提取国债期限利差或中债综合指数均线偏离度：
     从 `v_chinabond_yield_curve` 中提取最新 10Y-1Y 利差（基线 50 bp）与当前 10Y 国债收益率在历史区间的位置；或由 `H11009` 的 120 日均线偏离度动态折算：
     $$\text{Bias}_{120} = \frac{p - \text{MA}_{120}}{\text{MA}_{120}} \times 100\%$$
     $$\text{ValuationPercentile}_{\text{bond}} = \text{round}\left(\text{clip}\left(40.0 + \text{Bias}_{120} \times 5.0, 15.0, 80.0\right), 1\right)$$
     当债市连续单边暴涨偏离均线时，估值分位上升至 60%~70%（提示过度拥挤）；当回调时回到 30%~40%，具备灵敏感知。
2. **黄金赛道 (`domestic_gold`)**:
   - 黄金无 PE/PB，采用 AU9999 真实价格的 60 日均线负乖离及历史 5 年滚动价格分位加权：
     $$\text{Bias}_{60} = \frac{p - \text{MA}_{60}}{\text{MA}_{60}} \times 100\%$$
     $$\text{ValuationPercentile}_{\text{gold}} = \text{round}\left(\text{clip}\left(50.0 + \text{Bias}_{60} \times 2.0, 15.0, 90.0\right), 1\right)$$
3. **红利与银行赛道 (`dividend_low_vol`, `csi_dividend`, `banking_dividend`)**:
   - 彻底删除 `pass` 分支！
   - 统一由 `data_loader.fetch_or_calc_index_valuations()` 提取真实单源同真数据（中证红利 000922 目前真实分位为 42.0%，红利低波 H30269 真实分位为 42.0%，银行 399986 真实分位为 92.1%）。

---

## 3. 物理安全红线与自动化防作弊测试基线 (R8)

### 3.1 四大裁判文件基线 SHA256 哈希值清单

经现场工具哈希核算，4 大物理受控文件绝对只读基线如下（实施任何功能开发时**严禁发生任何修改**）：

| 文件路径 | 现行 SHA256 哈希值 |
| :--- | :--- |
| `AGY2_FundAdvisory/judge_engine.py` | `76f930371176de7ee6a413174b030101e3210ac6e037f5d10fe229af31cc07be` |
| `AGY2_FundAdvisory/holdout_vault.py` | `88122eaf647040a410e2fd95da81077db10149a498a47340ff40b670bd031d2a` |
| `AGY2_FundAdvisory/AGENT_SPEC.md` | `a346586f9bd2dc0ee83e665bd18e7a6471464c9f7b658e392b989b800cd63957` |
| `tests/test_infra.py` | `48bee0da300d7c0a0848ec1376e4b9b2e55224d2736081713b4340f0362cd100` |
| *(备用) `AGY2_FundAdvisory/tests/test_infra.py`* | `b8d781be8135be05cf61e62e4b534e359985ad880f27ffb61228a33df6b02a6a` |

---

### 3.2 `DataLoader.simulate_execution` 默认签名与扣费逻辑受控核验

- **文件位置**: `AGY2_FundAdvisory/data_loader.py:1095-1150`
- **默认签名不变性**:
  ```python
  @staticmethod
  def simulate_execution(
      weights_df: pd.DataFrame,
      prices_df: pd.DataFrame,
      is_otc: bool = True,
      penalty_days: int = 7,
      penalty_rate: float = 0.015,
      etf_impact: float = 0.001
  ) -> pd.DataFrame:
  ```
- **核心逻辑红线**:
  1. `is_otc=True` 时默认场外交易扣费逻辑：持有天数 $< 7$ 天严格扣除 $1.50\%$ 惩罚性赎回费。
  2. 场内 ETF 冲击成本固定为单边 $0.10\%$。
  3. 执行算子中的 T+1 延迟确认机制（`w_exec = w_df[asset_cols].shift(1)`）保持原样，严禁篡改测试基线。

---

### 3.3 专项防作弊测试 A、B、C、D 规范设计

为了杜绝任何偷工减料与迎合性假实现，后续实现必须通过以下 4 项专项目标测试：

#### 测试 A：14 大赛道真动态检验 (`test_anticheat_test_a_genuine_sectors.py`)
- **调用入口**: `OpportunityRadarEngine().scan_all_sectors()`
- **断言要求**:
  1. 返回列表长度严格等于 14；
  2. 提取所有赛道的 `(er_20, bias_20, s_crowd)` 元组，断言**没有任何一个赛道**同时等于默认兜底值 `(0.50, 1.0, 85.0)`；
  3. 断言 `er_20` 的不同取值个数 $> 5$，`bias_20` 不同取值个数 $> 5$；
  4. 断言 `val_percentile` 中没有任何硬编码常数，且 `pure_bond` 与 `domestic_gold` 的估值分位不等于固定的 `40.0` 和 `52.0`。

#### 测试 B：四大调仓场景真实性检验 (`test_anticheat_test_b_rebalance_scenarios.py`)
- **调用入口**: `PortfolioManager.generate_ai_rebalance_orders(...)`
- **断言要求**:
  1. 当 `scenario_mode="new_cash_only"`, `new_cash_amount=50000.0` 时：
     - 生成的所有调仓指令中，卖出动作（SELL）的金额与份额必须严格为 0；
     - 产生的手续费中赎回费必须严格为 0；
     - 所有买入动作（BUY）的调仓金额之和必须等于 50000.0（允许 1 元以内四舍五入容差）。
  2. 当 `scenario_mode="withdraw_cash_only"`, `withdraw_cash_amount=30000.0` 时：
     - 生成的所有调仓指令中，买入动作（BUY）的金额必须严格为 0；
     - 所有卖出动作（SELL）的金额之和必须等于 30000.0；
     - 若持仓中存在持有天数 $< 7$ 天的标的，该标的的卖出份额必须严格为 0（严禁触发 1.5% 惩罚费）。

#### 测试 C：多账本隔离与全站联动检验 (`test_anticheat_test_c_multi_ledger_isolation.py`)
- **调用入口**: `MultiLedgerManager`
- **断言要求**:
  1. 默认主实盘账本 `main_live`（`portfolio_ledger.json`）受物理删除保护，调用 `delete_ledger("main_live")` 必须抛出受控异常或返回 False；
  2. 创建沙盒账本 `sandbox_test`，并在其中增删改持仓，断言主实盘账本文件 `portfolio_ledger.json` 的 SHA256 或内容不发生任何变化；
  3. 克隆账本测试：克隆后新账本与原账本持仓完全独立，修改克隆账本不污染源账本。

#### 测试 D：Tab 4 跨组合穿透检验 (`test_anticheat_test_d_tab4_look_through.py`)
- **调用入口**: 
  - `pm.calculate_look_through_industry_exposure(holdings_override=...)`
  - `pm.calculate_stock_overlap_matrix(holdings_override=...)`
  - `pm.calculate_portfolio_penetration_risk(holdings_override=...)`
  - `pm.get_portfolio_look_through_stocks_df(holdings_override=...)`
  - `pm.classify_fund_asset_class(code, name)`
- **断言要求**:
  1. 传入两个完全不同持仓构成的 `holdings_override`（如纯红利 vs 纯半导体/科技）：
     - 行业暴露 DataFrame 必须完全不同（行业分布差异明显）；
     - 重合度矩阵维度与标的必须随传入字典动态匹配；
     - 穿透排雷大宽表中的关联股票代码必须与传入基金的前十大重仓股严格对应；
  2. 针对常见 50 只基金（涵盖 161726, 161725, 160418, 013402, 008888, 013841, 011612, 050025, 001071, 005561, 100032 等）：
     - `classify_fund_asset_class` 返回的大类必须为 10 大专业分类；
     - 无任何一只基金返回“其他权益资产”或已废弃的“其他存量资产”。

---

## 4. 调研结论与后续实施执行路径

1. **R5 实施重心**:
   - 在 `portfolio_manager.py` 中为 4 个穿透底层函数统一加入 `holdings_override: Optional[Dict[str, Any]] = None`；
   - 新增 `HoldingItem` 类定义，防止 `app_gui.py` 导入时抛 `ImportError`；
   - 彻底重构 `classify_fund_asset_class` 的名称与分类反查引擎，打通对所有核心赛道冠军与备选基金的代码直通解析。
2. **R6 实施重心**:
   - 在 `OpportunityRadarEngine._calc_dynamic_sector_metrics` 中接入 DuckDB `v_indices`、`nav_cache` 与 `global_indices` 多级动态加载流水线，消灭 `0.50 / +1.0% / 85.0`；
   - 在 `get_sector_valuation_percentile` 中删除空 `pass`，并基于真实 120日/60日均线乖离动态精算纯债与黄金的分位数。
3. **R8 实施重心**:
   - 严禁修改 4 个只读裁判文件与 `DataLoader.simulate_execution`；
   - 编写并运行专项防作弊测试 A、B、C、D，确保 100% 自动化测试通过。
