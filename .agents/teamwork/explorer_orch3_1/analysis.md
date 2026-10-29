# AGY2_FundAdvisory 量化核心引擎深度勘测与无硬编码架构重构分析报告 (analysis.md)

**勘测者**: Core Quant Engine Explorer (`explorer_orch3_1`)  
**勘测对象**: `AGY2_FundAdvisory/strategy_bridge.py` (3,870 lines) 与 `AGY2_FundAdvisory/portfolio_manager.py` (5,340 lines)  
**勘测日期**: 2026-10-30  
**勘测属性**: 100% 只读勘测 (Zero-Code Modification)  

---

## 1. 勘测目标与系统全貌

本次勘测针对投顾系统架构级进化重构需求，重点排查既有代码中所有为了应付测试或特定用例而编写的**硬编码补丁、静态股票/基金代码白名单、固定静态权重字典、伪造打分**，并对核心量化模型（C1~C5 动态风险预算模型、攻防状态机自适应、双向变盘触发点位计算、三层财务排雷、统一资产分类解析器、六维量化选基评分）与跨模块接口契约进行全方位梳理，为后续 Agent-1 与 Agent-2 的无硬编码重构提供精确的现状基线图谱。

---

## 2. `strategy_bridge.py` 现状与硬编码排查点

### 2.1 `compute_dynamic_tier_weights` 实现逻辑现状与缺陷

#### 现状核查
- **该方法当前在 `strategy_bridge.py` 中尚未实现**（方法缺失）。
- 当前系统处理 C1~C5 档位权重存在两个互相割裂且均为**硬编码**的旧实现：
  1. **生产/建仓端硬编码**：`TIER_TARGET_WEIGHTS` (第 232~275 行) 与 `StrategyBridge.get_tier_target_weights` (第 2824~2845 行)
     ```python
     # strategy_bridge.py:232-275
     TIER_TARGET_WEIGHTS: Dict[str, Dict[str, float]] = {
         "C1": {"002351": 0.50, "000086": 0.20, "005561": 0.20, "000216": 0.10},
         "C2": {"002351": 0.35, "005561": 0.25, "100032": 0.20, "000216": 0.14, "050025": 0.06},
         "C3": {"100032": 0.38, "005561": 0.30, "000216": 0.14, "002351": 0.12, "050025": 0.06},
         "C3_ATTACK": {"011613": 0.30, "001053": 0.15, "100032": 0.25, "005561": 0.15, "000216": 0.10, "002351": 0.05},
         "C4": {"011613": 0.30, "001053": 0.18, "100032": 0.24, "000216": 0.14, "002351": 0.08, "050025": 0.06},
         "C5": {"011613": 0.38, "016634": 0.22, "013841": 0.15, "100032": 0.10, "000216": 0.10, "050025": 0.05}
     }
     ```
     在 `get_tier_target_weights(tier, market_state_code)` (第 2837~2845 行) 中：
     ```python
     t = str(tier).upper().strip() if tier else "C3"
     if t == "C3":
         if market_state_code in ["GROWTH_BULL", "STRUCTURAL_500"]:
             return dict(TIER_TARGET_WEIGHTS["C3_ATTACK"])
         return dict(TIER_TARGET_WEIGHTS["C3"])
     elif t in TIER_TARGET_WEIGHTS:
         return dict(TIER_TARGET_WEIGHTS[t])
     return dict(TIER_TARGET_WEIGHTS["C3"])
     ```
  2. **历史回测端硬编码**：`strategy_fn_for_tier` (第 966~1087 行)
     为回测引擎针对不同档位返回写死的指数配置字典（如 C1 直接在不同条件分支返回 `{'H11009': 0.72, 'AU9999': 0.15, ...}`，C5 在进攻期返回 `{'STAR50_STITCH': 0.65, ...}`）。

#### 核心架构缺陷与风险
1. **完全缺失目标波动率与最大回撤边界约束**：
   `RISK_TIERS_CONFIG` (第 135~229 行) 虽然声明了 `target_return_min/max`、`max_tolerated_loss`、`max_drawdown_limit`，但所有档位的权重完全是人工写死的固定百分比，并未由目标波动率（如 C1: 4%, C2: 8%, C3: 14%, C4: 20%, C5: 28%）或最大回撤容忍边界经由风险预算（Risk Budgeting）优化算法动态求解。
2. **三态自适应调节在 C1/C2/C4/C5 严重缺失**：
   - 现有的 `get_tier_target_weights` 仅对 `C3` 判断了 `market_state_code`；
   - 对于 **C1、C2、C4、C5**，完全不响应任何市场状态！即使进入【破位防御态 / 深度大熊市】（`SEVERE_BEAR`，跌破中长期均线且均线向下发散），C4 和 C5 依旧保持 85% 以上高弹性权益，毫无止损降仓与黄金债券避险动作。
3. **C1~C5 风险单调性发生倒挂 (Monotonicity Inversion Bug)**：
   - 当市场处于 `GROWTH_BULL` 时，C3 档位触发 `C3_ATTACK`，其权益仓位达 **85%** (011613 30% + 001053 15% + 100032 25% + 005561 15%)；
   - 然而高一级的 C4 成长进攻型，静态权益仓位仅为 **72%** (011613 30% + 001053 18% + 100032 24%)；
   - **导致出现严重荒谬的倒挂：平衡进取型 C3 的股票风险敞口（85%）反而大于进攻型 C4（72%）！** 无法满足 `C1 < C2 < C3 < C4 < C5` 的风险预算单调性约束。

---

### 2.2 `get_rebalance_grid_status` 点位计算现状与双向触发倒挂排查

#### 现存源码分析 (第 1571~1647 行)
```python
# strategy_bridge.py:1610-1620
q_300 = fetch_realtime_index_quote("sh000300", use_cache=True)
c300_price = float(q_300.get("point", 4053.0)) if q_300.get("point", 0) > 0 else 4053.0
if 3500.0 <= c300_price <= 4800.0:
    breakdown_c300 = round(c300_price * (4180.5 / 4053.0), 1)
else:
    scale = (c300_price / c300_curr) if c300_curr > 0 else (4053.0 / 6100.0)
    breakdown_c300 = round(m20 * scale, 1)

surge_c300 = round(c300_price * (1.0 + 0.039), 1)
```

#### 致命点位倒挂缺陷剖析 (Fatal Defect)
1. **防守线与现价倒挂 (Breakdown Line Inversion)**：
   - 观察公式：`breakdown_c300 = round(c300_price * (4180.5 / 4053.0), 1)`
   - 其中的常量 `4180.5 / 4053.0 ≈ 1.031458` (即 +3.15%)；
   - **当当前指数点位为 4,053.0 时，算出的“向下跌破防守线”居然是 4,180.5 点！**
   - 4,180.5 严格大于 4,053.0。文案提示：“若今日盘中沪深300跌破 4,180.5 点...触发盘中紧急调仓！”——然而当前指数现价就在 4,053.0，早已在 4,180.5 之下！
   - **逻辑成因**：开发者误把上方的 MA20 阻力线（4180.5）当作了下方的防守线（breakdown），并写死了静态倍率。
2. **基准点位硬编码伪线性插值 (第 1929~1940 行)**：
   - 在 `get_latest_market_snapshot` 中写死了基准常数：
     ```python
     BASE_C300 = 4053.0
     BASE_M20 = 4180.5
     BASE_M60 = 3962.0
     BASE_M120 = 3850.0
     if 3200.0 <= c300_price <= 5200.0:
         m20_price = round(BASE_M20 + (c300_price - BASE_C300) / 20.0, 1)
         m60_price = round(BASE_M60 + (c300_price - BASE_C300) / 60.0, 1)
         m120_price = round(BASE_M120 + (c300_price - BASE_C300) / 120.0, 1)
     ```
   - 没有利用全量历史真实价格序列去计算滚动 20/60/120 日均线在真实指数点位上的真实位置，而是采用静态基准加偏移量的生硬拟合，完全失真。
3. **向上进攻线生硬写死**：
   - `surge_c300 = round(c300_price * (1.0 + 0.039), 1)` 仅为固定 +3.9% 单日涨幅，并未结合 MA20、MA60 压力位或前期高点动态推导。

---

### 2.3 宏观状态与衍生品桥接现状

- **流动性温度计**：`_refresh_liquidity_thermometer` (第 1649~1743 行)
  - 接入 `WindToolkit.macro_liquidity.get_liquidity_thermometer()`，获取 DR007、7D 逆回购政策利率（1.50%）、利差（bp）、7D 净投放与央行姿态；
  - 具备 `liquidity_badge`（🟢宽松 / 🟡中性 / 🔴收紧）与估值趋势定性（`trend_stance`: BULL / STABLE / BEAR）；
- **衍生品数据接入**：`_refresh_derivatives_data` (第 1745~1887 行)
  - 成功接入本地 `data/derivatives/futures_basis.parquet` 与 `option_volatility.parquet`；
  - 提取了 IC、IM、IF、IH 的年化基差贴水率与 50/300/科创 ETF 的期权隐含波动率 IV；
- **桥接割裂现状**：
  - 目前这些高价值宏观与衍生品信号仅被用来生成一段展示文案（`snapshot["advisory_takeaway"]`）以及在选基评分中对个别写死基金增加 ±2 分；
  - **完全没有桥接至资产配置权重的计算逻辑中**！当 DR007 暴增或期权 IV 极端飙升（>32% 尾部波动预警）时，仓位引擎没有任何自适应降仓或加配纯债黄金的动作。

---

## 3. `portfolio_manager.py` 现状与硬编码排查点

### 3.1 `screen_fund_look_through_risk` 当前排雷逻辑与硬编码审计

#### 严重硬编码白名单排查发现
1. **金融机构股票代码写死列表 (第 3581~3596 行)**：
   ```python
   # portfolio_manager.py:3581-3596
   financial_codes = {
       # 银行
       "600000", "600015", "600016", "600036", "600908", "600919", "600926", "600928", "601009",
       "601077", "601128", "601166", "601169", "601187", "601229", "601288", "601328", "601398",
       "601577", "601658", "601665", "601818", "601825", "601838", "601860", "601916", "601939",
       "601963", "601988", "601997", "601998", "603323", "000001", "002142", "002807", "002839",
       "002936", "002948", "002958", "002966", "001227", "001337",
       # 保险与综合金融
       "601318", "601601", "601628", "601336", "601319", "601995", "600061", "000627", "000712",
       "000987", "600864",
       # 证券
       "600030", "601688", "600837", "601211", "000776", "600999", "000166", "601881", "601066",
       "601788", "600958", "601901", "601377", "601108", "601198", "002736", "601878", "000783",
       "600109", "600918", "601059", "601136", "601456", "002926", "002939", "002945", "601877",
       "601236", "601099"
   }
   ```
   **此处硬编码了 77 只特定金融机构股票代码！** 严重违背了“严禁在代码中通过穷举特定股票代码免检”的架构红线。
2. **非 A 股基金代码写死列表 (第 3491~3495 行)**：
   ```python
   NON_ASHARE_CODES = {
       "002351", "002352", "018757", "000086",
       "000216", "000217", "002610", "002611",
       "050025", "006075", "001071", "017436"
   }
   ```
3. **伴生基金核心策略标签写死 (第 3056 行)**：
   `code in ("001071", "090010", "000086", "013841", "011613", "016634", "001053", "008682", ...)` 包含 18 只基金硬编码。
4. **同源份额与限购拆单豁免写死对 (第 3244~3264 行)**：
   `EXEMPT_OVERLAP_PAIRS` 中硬编码了 16 组 `frozenset({"050025", "001071"})` 等静态配对。

#### 三层通用基本面排雷模型的差距与落地方案
目前 `screen_fund_look_through_risk` 对存贷双高的判定极其粗糙：直接取 `fin_data.get("double_high_risk", False)`，只要非金融即扣 40 分。
**三层落地要求**：
- **第一层（标准金融业态动态识别）**：彻底剔除 77 只股票代码集合，改为基于申万一级行业属性（行业分类包含“银行”、“非银金融”）或个股主营业务金融属性动态判定，对金融机构豁免存贷双高审查；
- **第二层（重资产硬科技/公用事业现金流校验）**：目前完全缺失！在 `v_stock_financials` 中查询其经营现金流净额 `ocf_per_share` 或 `fcf_billion`。对于半导体制造、新能源电网、公用事业等重资产行业，若固定资产及在建工程占比较高且经营活动现金流 `CFO > 0`、利息保障倍数安全，自动判定为“重资产正常经营/现金流健康”，杜绝误判；
- **第三层（高现金高息融资真伪造假识别）**：仅当企业账面货币资金充裕但有息负债畸高，**同时**经营活动现金流持续恶化（CFO < 0）或存在大额受限资金/虚假存款时，才亮起存贷双高红灯。

---

### 3.2 统一资产分类解析器现状 (`classify_fund_asset_class`)

- **当前缺失状态**：在整个项目中搜索 `classify_fund_asset_class`，结果为 **0 项匹配**。
- **现存最大漏洞**：`app_gui.py` (第 1869~1874 行) 手工维护了一个仅包含 16 只基金的硬编码静态字典：
  ```python
  cat_map = {
      "100032": "A股红利高股息", "005561": "A股红利低波", "011612": "科技成长进攻", "011613": "科技成长进攻",
      "016633": "中小盘成长", "016634": "中小盘成长", "161017": "中盘均衡", "001053": "中盘均衡",
      "110020": "核心蓝筹", "007339": "核心蓝筹", "000216": "黄金对冲", "000217": "黄金对冲",
      "002351": "纯债固收", "018757": "纯债固收", "050025": "美股海外对冲", "001071": "美股海外对冲"
  }
  ```
  - **严重恶果**：C1 核心基金 `000086 工银纯债A`、C5 核心基金 `013841 银华集成电路`、高股息备选 `090010 大成红利` 等不在该字典中，直接全部被 `cat_map.get(c, "其他存量资产")` 归入了“其他存量资产”，导致界面上资产大类柱状图严重失真！
- **重构规划**：在 `portfolio_manager.py` 中实现通用的 `classify_fund_asset_class(fund_code, fund_name=None)`：
  1. 通过名称特征词、投资类型（`fund_type`）、跟踪指数名称、底层重仓行业动态智能推导；
  2. 统一定义大类：`纯债固收`、`黄金对冲`、`美股海外对冲`、`A股红利高股息`、`A股红利低波`、`科技成长进攻`、`中小盘成长`、`中盘均衡`、`核心蓝筹`；
  3. 彻底取代 `app_gui.py` 中的静态 `cat_map`。

---

### 3.3 六维量化选基评分实现方式与正规化现状

#### 伪造与硬编码现状
- 在 `strategy_bridge.py` 第 285~325 行：
  `FUND_SIX_DIMENSION_PROFILE` 完全是一个**人工手写的静态字典**，给 25 只基金分配了 `alpha`、`fee`、`risk`、`smart_money`、`crowding`、`macro` 的固定分值（例如 95.0, 98.0, 100.0 等）；
- `calculate_fund_six_dimension_score` (第 2905~2978 行) 仅仅是从该硬编码字典中 `.get(code)` 取出数值计算加权和；
- **完全没有进行任何真实数据的 Min-Max 或 Z-Score 正规化数学计算**，属于典型的“伪造打分”。

#### 湖仓真实量化数据源已具备条件
经勘测，本地 `data/storage.duckdb` 中已有完整视图支撑真实评分：
1. **Alpha 得分**：来自 `v_scorecards`（夏普比率、卡玛比率、年化超额收益率）或 `v_fund_snapshot`（近1年超额收益）；
2. **费率成本得分**：来自 `v_fund_trading_rules`（`est_total_operating_fee` 综合运作费率，低费率得分高，Min-Max 逆向归一化）；
3. **底层排雷健康分**：直接联动 `screen_fund_look_through_risk` 产出的 `100.0 - avg_risk`；
4. **北向聪明钱得分**：来自 `v_northbound_holdings` 与 `v_fund_heavyweight_stocks` 关联穿透后的北向增持比例与持股市值分位；
5. **反拥挤度得分**：来自 `v_market_temperature` 及基金规模与前十大重仓集中度；
6. **衍生品宏观契合度**：来自 `v_futures_basis`（IC/IM 贴水率）与 `v_option_volatility`（期权 IV）。

---

### 3.4 `apply_zero_start_blueprint` 等建仓/调仓函数接口契约现状

- **`apply_zero_start_blueprint(self, blueprint, baseline_date=None)`** (第 2653~2767 行)：
  - 参数契约：接收包含 `total_capital` 和 `items` 列表的字典；
  - 内部行为：先清空 `holdings` 与 `pending_orders`，将 `self.peak_equity = 0.0`，`self.max_drawdown_pct = 0.0`，重建持仓并打上核心策略底仓标签，末尾再次强制归零回撤与收益率指标；
  - 状态重置符合验收要求 R1。
- **`generate_zero_start_blueprint` 重复定义缺陷**：
  - 该方法在 `portfolio_manager.py` (第 2494 行) 与 `strategy_bridge.py` (第 3062 行) 两处均被定义，且两处各自复制了一份完全相同的硬编码权重字典。必须收拢并由 `strategy_bridge.py` 统一定义，`portfolio_manager.py` 专注账本执行。

---

## 4. `strategy_bridge.py` 与 `portfolio_manager.py` 接口契约梳理

### 4.1 现有调用依赖图谱

```
   [app_gui.py] (调度中枢)
       │
       ├─► StrategyBridge.get_latest_market_snapshot()
       ├─► StrategyBridge.get_rebalance_grid_status()
       ├─► StrategyBridge.generate_zero_start_blueprint()
       ├─► StrategyBridge.get_tier_quant_selection_table()
       │
       └─► PortfolioManager.apply_zero_start_blueprint()
       └─► PortfolioManager.screen_fund_look_through_risk()
       └─► PortfolioManager.calculate_stock_overlap_matrix()

   [strategy_bridge.py]
       │ (向下轻量依赖行情与账本)
       ├─► portfolio_manager.fetch_realtime_index_quote()
       ├─► portfolio_manager.fetch_realtime_fund_quote()
       └─► portfolio_manager.PortfolioManager (仅在特定回测与冲击测算中)

   [portfolio_manager.py]
       │ (目前不依赖 strategy_bridge.py)
```

### 4.2 职责划分与重构边界建议

| 模块名称 | 规范归属职责 | 严禁跨界行为 |
| :--- | :--- | :--- |
| **`strategy_bridge.py` (Agent-1)** | • 宏观、流动性与衍生品指标桥接 (`get_latest_market_snapshot`)<br>• C1~C5 动态风险预算模型 (`compute_dynamic_tier_weights`)<br>• 技术均线与双向变盘触发点位 (`get_rebalance_grid_status`)<br>• 生成标准建仓蓝图 (`generate_zero_start_blueprint`) | • 严禁内嵌静态权重字典<br>• 严禁直接操作用户持仓账本 SQLite 事务 |
| **`portfolio_manager.py` (Agent-2)** | • 基金穿透前十大重仓三层通用财务排雷 (`screen_fund_look_through_risk`)<br>• 统一通用资产分类解析器 (`classify_fund_asset_class`)<br>• 真实六维选基评分与正规化计算<br>• 账户账本管理与建仓/接管/调仓单执行 (`apply_zero_start_blueprint`) | • 严禁硬编码股票代码白名单 (`financial_codes`)<br>• 严禁重复实现宏观或策略权重推导 |

---

## 5. 重构实施雷区与反硬编码审计关注点

1. **AST 静态语法树审计红线**：
   重构完成后将运行 AST 语法树审计，凡在 `portfolio_manager.py`、`strategy_bridge.py` 或 `app_gui.py` 中出现包含特定股票代码（如 `600000`, `600036` 等）的 `Set`、`List`、`Dict` 或 `If` 语句，一律判定为违规！
2. **变盘点位单调性断言**：
   在任何实时行情与仿真数据下，严格保证：
   $$\text{breakdown\_threshold\_c300} < \text{c300\_price} < \text{breakout\_threshold\_c300}$$
   杜绝任何形式的向下防守线高于现价现象。
3. **C1 至 C5 风险单调性断言**：
   在牛市进攻、震荡收息、熊市破位任意输入下，必须严格满足：
   $$\text{Equity}(C1) < \text{Equity}(C2) < \text{Equity}(C3) < \text{Equity}(C4) < \text{Equity}(C5)$$
4. **4 个裁判基建文件绝对物理安全**：
   `judge_engine.py`、`holdout_vault.py`、`AGENT_SPEC.md`、`tests/test_infra.py` 必须 100% 保持只读未篡改。

---

*勘测报告至此完结，交付后续智能体团队执行架构重构。*
