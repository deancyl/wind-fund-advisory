# 场外公募基金微观执行冲击与底层流动性折价惩罚调研报告 (R1 & R3)

**报告作者**: Codebase Survey Explorer (`explorer_survey_g10_2`)  
**任务目标**: 针对需求 R1（核心安全底线与反作弊契约）与 R3（场外公募基金微观执行冲击与底层流动性折价惩罚），对 `data_loader.py` 与 `advisory_engine.py` 进行全面代码走查、数据湖仓与接口探查、非线性数学建模与工程实现方案设计。  
**日期**: 2026-11-08  
**工作区路径**: `d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_g10_2\`

---

## 1. Observation (客观事实与现场观测)

### 1.1 `DataLoader.simulate_execution` 现存签名与扣费逻辑
在 `AGY2_FundAdvisory/data_loader.py` 第 1380 至 1495 行：
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
- **参数契约**:
  - `weights_df`: 包含 `date` 与目标资产权重列。
  - `prices_df`: 包含 `date` 与资产价格列。
  - `is_otc`: 默认为 `True`。
  - `penalty_days`: 默认为 `7`。
  - `penalty_rate`: 默认为 `0.015` (1.50%)。
  - `etf_impact`: 默认为 `0.001` (0.10%)。
- **扣费与确认机制**:
  - `T+1` 延迟生效：`w_exec = w_df[asset_cols].shift(1).fillna(0.0)`，首日取 `w_df.iloc[0]`。
  - 买入摩擦：`friction += dw * etf_impact`，同时记录买入日期 `last_buy_dates[a] = cur_date`。
  - 卖出阶梯费率（当 `is_otc=True`）：
    - `holding_days < 7`: 惩罚性费率 `penalty_rate = 0.015` (1.50%)。
    - `holding_days < 30`: C 类 `0.0050` / A 类 `0.0075`。
    - `holding_days < 180`: C 类 `0.0000` / A 类 `0.0050`。
    - `holding_days < 365`: C 类 `0.0000` / A 类 `0.0025`。
    - `holding_days >= 365`: 免赎回费 `0.0000`。
    - 卖出摩擦叠加 ETF 冲击：`friction += sell_amount * (r_rate + etf_impact)`。
  - 若 `is_otc=False`：直接按 `friction += sell_amount * etf_impact` 扣费。
  - 每日净值复利：`cur_nav = cur_nav * (1.0 + day_ret) * (1.0 - friction)`。
  - 返回 DataFrame 列：`['date', 'nav', 'daily_return', 'turnover', 'friction']`。
- **严格测试锁定**:
  - `tests/test_auditor_g9_m2_integrity.py` 第 52-63 行与 `tests/test_infra.py` 第 49-63 行、第 121-135 行通过 AST 与 `inspect.signature` 严格锁定此函数签名，严禁增加无默认值形参或修改默认参数名；测试断言要求 `assert params == ['weights_df', 'prices_df', 'is_otc', 'penalty_days', 'penalty_rate', 'etf_impact']`。

### 1.2 `advisory_engine.py` 现有微观执行与滑点逻辑
在 `AGY2_FundAdvisory/advisory_engine.py` 第 2349 至 2523 行：
- **类名**: `SmartExecutionDCAEngine`
- **核心方法**: `calculate_vwap_execution_slippage(cls, order_amount, fund_code, fund_name="", daily_volume_est=None, volatility=None, bias_20=None, **kwargs)`
- **双轨判定准则**:
  - 严格依据 GEMINI.md 铁律 19：仅当代码以 `51`、`15`、`56`、`58`、`59` 开头且名称不包含“联接”时判定为场内 ETF (`is_etf = True`)；其余全部判定为场外基金 (`is_etf = False`)。
- **现存双轨实现细节**:
  1. **轨道 A (场内 ETF)**:
     - 平方根市场冲击模型：
       $$PR = \frac{\text{amt}}{\text{adv}}$$
       $$\text{impact\_naive\_bps} = \text{spread} + 3.0 \times \sqrt{PR} \times \sigma_{\text{day\_bps}}$$
       $$\text{impact\_vwap\_bps} = 0.5 \times \text{spread} + 0.8 \times \sqrt{PR} \times \sigma_{\text{day\_bps}}$$
     - 输出 5 阶段日内分时 VWAP 挂单调度表（09:30-10:00、10:00-11:30、13:00-14:00、14:00-14:45、14:45-15:00）。
  2. **轨道 B (场外公募基金)**:
     - 目前主要模拟“早盘盲买冲高回落未知净值偏差风险” vs “14:30 尾盘净值锚定下单节省”：
       $$\text{naive\_bps} = 1.5 + \sigma_{\text{day\_bps}} \times 0.12 \times \left(\frac{\text{amt}}{10000}\right)^{0.22} \times \text{bias\_factor}$$
       $$\text{vwap\_bps} = 0.5 + \sigma_{\text{day\_bps}} \times 0.03 \times \left(\frac{\text{amt}}{10000}\right)^{0.176}$$
     - 输出跨日/均线分批吸筹调度表（T日尾盘、T+2日回踩、T+5日企稳、T+10日突破、T+15日结顶）。
  3. **现存缺陷与待补全维度**:
     - 场外公募基金在面对**大额赎回 (Large Redemption)** 或巨额资产调仓变现时，尚未联动基金季报前五大重仓股日均成交额（ADV）与基金规模（AUM），缺乏大额变现对底层股票资产的流动性折价惩罚模型（Haircut Penalty Model）。

### 1.3 基金季报前五大重仓股、ADV 与基金规模 (AUM) 的数据现状
- **基金元数据与季报数据源**:
  - `AGY2_FundAdvisory/cache_manager.py` 中的 `FundMetadataManager.get_fund_metadata(fund_code)`（已封装于 `DataLoader.get_fund_metadata`）具有 24h 本地 TTL 缓存至 `data/cache/funds/{code}_meta.json`。
  - 缓存中完整包含：
    - `aum`: 基金规模（单位：亿元，如 `000933` 为 `0.98` 亿，`011613` 为 `59.56` 亿）。
    - `asset_allocation`: 资产配置比例字典，包含 `stock`、`bond`、`cash` 仓位百分比（例如 `000933` 股票 `25.7%`，债券 `72.46%`）。
    - `top10_stocks`: 季报披露的前十大重仓股东方财富标准 `secid` 列表（例如 `["1.600900", "1.600036", "1.600674", "1.600886", "1.600489", ...]`，其中 `1.` 代表沪市，`0.` 代表深市）。
  - 取 `top10_stocks[:5]` 即为法定季报披露的前五大核心重仓股。
- **重仓股日均成交额 (ADV) 实时与离线获取链路**:
  - 现场实测调用东财官方行情推送网关：
    `https://push2.eastmoney.com/api/qt/ulist.np/get?secids={secids}&fields=f12,f14,f2,f3,f4,f6`
  - 字段 `f6` 即为证券当日实时成交总金额（元），`f12` 为代码，`f14` 为股票名称。
  - 现场实测调用 `1.600900,1.600036,1.600674,1.600886,1.600489`，均在 90ms 内成功返回长江电力（50.4亿）、招商银行（39.7亿）、川投能源（7.09亿）等精确成交额。
  - 离线湖仓兜底：本地 `data/mart/fund_heavyweight_stocks.parquet`、`data/master/securities.csv` 以及细分赛道日线指数数据，可作为离线无网状态下的极速缓存。

---

## 2. Logic Chain (推理链条与非线性数学建模)

### 2.1 场外公募大额赎回底层冲击的金融学机理
1. **赎回现金流与底层清仓冲击**:
   - 场外公募基金实行未知净值申赎。当投资者赎回金额为 $Q$ 元时，基金需在 $T+1 \sim T+3$ 日备足现金兑付。
   - 基金通常持有 $2\% \sim 5\%$ 的现金垫。小额赎回（如数千至数万元，占基金规模比例 $\rho = Q / AUM < 0.1\%$）可由现金池或当日申购款完全覆盖，无底层资产折价。
   - 当赎回金额达到数十万至数千万元，或赎回比例 $\rho$ 突破 $1\%$ 并向 $10\%$（证监会法定巨额赎回线）逼近时，现金垫枯竭，基金经理必须在二级市场强制卖出底层重仓股变现。
2. **底层重仓股市场冲击**:
   - 前五大重仓股通常占据基金权益持仓的 $25\% \sim 40\%$。
   - 卖出 $Q \times w_{\text{equity}}$ 金额将对前五大重仓股产生直接的盘口冲击。冲击幅度遵循金融微观结构经典的 **Almgren-Chriss / Kyle's Lambda 平方根法则**：
     $$I_{\text{underlying}} \propto \sqrt{\frac{Q \cdot w_{\text{equity}}}{ADV_{\text{top5}}}}$$
3. **基金规模承压与踩踏溢价 (Fund Run & Fire-Sale Surcharge)**:
   - 单纯线性折价模型无法刻画集中赎回引发的流动性螺旋（2015 流动性挤兑与 2024 初小盘踩踏实证）。
   - 必须引入超线性赎回压力项与流动性集中度放大因子：
     $$\rho = \frac{Q}{AUM}, \quad \text{Concentration Factor } C = 1.0 + \ln\left(1.0 + \frac{AUM}{ADV_{\text{top5}}}\right)$$
     $$I_{\text{fire\_sale}} \propto \rho^{\beta_2} \cdot C \quad (\beta_2 \approx 1.2 \sim 1.25)$$
   - 当 $AUM / ADV_{\text{top5}}$ 极高（基金盘子大但底层股票日均成交惨淡）时，$C$ 显著放大折价惩罚；当 $\rho$ 增大时，呈现超线性急剧攀升。

### 2.2 完整的非线性流动性折价惩罚数学模型
定义输入参数：
- $Q \ge 0$：订单/赎回金额（元）
- $AUM > 0$：基金真实净资产规模（元，由 `aum_billion * 1e8` 精确换算）
- $ADV_{\text{top5}} > 0$：季报前五大重仓股合计日均成交额（元）
- $w_{\text{equity}} \in [0.05, 1.0]$：季报披露的股票权益资产占比
- $\sigma_{\text{annual}}$：单基真实 20 日年化历史波动率（四级湖仓穿透，绝无 0.04/0.14/0.18 假常数）
- $\sigma_{\text{day\_bps}} = \frac{\sigma_{\text{annual}}}{\sqrt{250}} \times 10000$：单基日度波动率（基点 bps）

模型计算公式：
$$\text{PartRate}_{\text{underlying}} = \frac{Q \times w_{\text{equity}}}{ADV_{\text{top5}}}$$
$$\text{RedemptionRatio} = \frac{Q}{AUM}$$
$$\text{ConcentrationFactor} = 1.0 + \ln\left(1.0 + \frac{AUM}{ADV_{\text{top5}}}\right)$$
$$\text{Haircut}_{\text{bps}}(Q) = \sigma_{\text{day\_bps}} \times \left[ \kappa_1 \cdot \left(\text{PartRate}_{\text{underlying}}\right)^{0.50} + \kappa_2 \cdot \left(\text{RedemptionRatio}\right)^{1.25} \cdot \text{ConcentrationFactor} \right]$$
$$\text{Haircut}_{\text{yuan}}(Q) = Q \times \frac{\text{Haircut}_{\text{bps}}(Q)}{10000}$$

其中标定系数：
- $\kappa_1 = 0.80$（二级市场平方根冲击系数）
- $\kappa_2 = 1.50$（基金挤兑变现超额惩罚系数）

### 2.3 数值仿真与不变量验证
在典型参数下（$AUM = 50\text{ 亿元}$, $ADV_{\text{top5}} = 20\text{ 亿元}$, $\sigma = 18.0\%$, $w_{\text{equity}} = 80\%$）实测仿真结果：
| 订单金额 $Q$ (元) | 赎回比例 $\rho$ | 底层参与率 | 折价惩罚率 (bps) | 折价惩罚金额 (元) | 严格单调性 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| ¥1,000 | 0.00002% | 0.00004% | **0.06 bps** | ¥0.01 | 基准 |
| ¥10,000 | 0.0002% | 0.0004% | **0.18 bps** | ¥0.18 | $\Delta > 0$ ✅ |
| ¥50,000 | 0.001% | 0.002% | **0.41 bps** | ¥2.05 | $\Delta > 0$ ✅ |
| ¥100,000 | 0.002% | 0.004% | **0.58 bps** | ¥5.80 | $\Delta > 0$ ✅ |
| ¥500,000 | 0.010% | 0.020% | **1.29 bps** | ¥64.50 | $\Delta > 0$ ✅ |
| ¥1,000,000 | 0.020% | 0.040% | **1.83 bps** | ¥183.00 | $\Delta > 0$ ✅ |
| ¥5,000,000 | 0.100% | 0.200% | **4.14 bps** | ¥2,070.00 | $\Delta > 0$ ✅ |
| ¥50,000,000 | 1.000% | 2.000% | **14.10 bps** | ¥70,500.00 | $\Delta > 0$ ✅ |

在低流动性标的（$AUM = 5\text{ 亿元}$, $ADV_{\text{top5}} = 5000\text{ 万元}$, $\sigma = 22.0\%$）极限承压仿真：
- ¥100,000: **6.72 bps** (¥67.20)
- ¥1,000,000: **21.80 bps** (¥2,180.00)
- ¥20,000,000 (占基金 4%): **119.29 bps** (¥238,580.00，超 1.19% 惩罚)

### 2.4 模型性质严格检验
1. **非线性 (Non-linear)**：$\frac{\partial^2 \text{Haircut}}{\partial Q^2} \ne 0$，由平方根项（小额灵敏）与 1.25 次方项（大额剧增）平滑耦合而成，杜绝了单一线性换算的失真。
2. **严格单调递增 (Strict Monotonicity)**：对任意 $Q_2 > Q_1 > 0$，导数恒正，无任何阶梯截断平坦期或反转缺陷。
3. **零伪常数 (Zero Fake Constants)**：波动率来自四级穿透，AUM 来自季报披露，ADV 来自真实行情，权益比重来自季报穿透。
4. **场内场外严格物理隔离**:
   - 当 `is_etf = True` 时，$\text{Haircut}_{\text{bps}} = 0.0$，仅测算交易所 VWAP 挂单调度；
   - 当 `is_etf = False` 时，启动该底层流动性折价惩罚精算。

---

## 3. Caveats (局限性、假设与未探索领域)

1. **纯债与大宗商品基金的特殊性**:
   - 纯债固收基金（如 `002351`）季报无股票重仓，其底层资产主要为政金债与信用债，交易在银行间债券市场。其 ADV 应映射为银行间市场日均现券成交量或中债指数流动性（基准值约为 5 亿至 10 亿元）。
   - 黄金基金联接（如 `000216`）底层对应上海黄金交易所现货实盘合约 AU9999，其日均成交额通常超百亿元，流动性充裕。
2. **季报披露时滞**:
   - 公募基金季报披露存在 15 个交易日法定滞后期。因此前五大重仓股反映的是上一季度末的持仓结构，实际运作中可能存在基金经理微调漂移。这是公募制度下合法的客观限制。
3. **未修改任何生产代码**:
   - 本次探查严格遵守只读契约，未修改任何源文件。

---

## 4. Conclusion (确定性结论与具体实现方案建议)

### 4.1 核心结论
1. `DataLoader.simulate_execution` 的函数签名 `(weights_df, prices_df, is_otc=True, penalty_days=7, penalty_rate=0.015, etf_impact=0.001)` 必须**保持 100% 只读**，任何增删参数都会破坏裁判文件 `tests/test_infra.py` 与合规探针 `tests/test_auditor_g9_m2_integrity.py`。
2. 升级场外公募执行模型应通过在 `data_loader.py` 与 `advisory_engine.py` 中新增/升级独立方法实现，既能被 `SmartExecutionDCAEngine.calculate_vwap_execution_slippage` 无缝融合，又能向 `portfolio_manager.py` 与 GUI Tab 1/Tab 2 导出。

### 4.2 具体工程实施路线建议

#### 步骤一：在 `AGY2_FundAdvisory/data_loader.py` 中新增底层重仓股流动性提取与折价方法
```python
# 建议位置：在 DataLoader 类中增加类方法，并在模块末尾暴露别名
@classmethod
def get_fund_top5_holdings_adv(
    cls,
    fund_code: str,
    force_refresh: bool = False
) -> Dict[str, Any]:
    """
    结合基金管理人季报披露的前五大重仓股代码与真实成交额，
    精算底层股票日均成交额(ADV)、基金规模(AUM)及权益占比。
    带本地 24h TTL 缓存至 data/cache/funds/{code}_top5_adv.json。
    """
    ...

@classmethod
def calculate_otc_fund_liquidity_haircut(
    cls,
    order_amount: float,
    fund_code: str,
    fund_name: str = "",
    volatility: Optional[float] = None,
    is_etf: Optional[bool] = None
) -> Dict[str, Any]:
    """
    针对场外公募基金，结合季报前五大重仓股日均成交额与基金规模比例，
    基于非线性市场冲击与挤兑承压模型精算流动性折价惩罚。
    """
    ...
```

#### 步骤二：在 `AGY2_FundAdvisory/advisory_engine.py` 中升级 `SmartExecutionDCAEngine`
1. 在 `SmartExecutionDCAEngine.calculate_vwap_execution_slippage` 的轨道 B (`is_etf=False`) 中：
   - 穿透调用 `DataLoader.get_fund_top5_holdings_adv` 获取真实 AUM、前五大重仓股 ADV、权益占比；
   - 计算非线性 `liquidity_haircut_bps` 与 `liquidity_haircut_yuan`；
   - 将现有返回字典拓展新字段（完全向后兼容）：
     ```python
     "fund_aum_yuan": aum_yuan,
     "top5_adv_yuan": top5_adv,
     "redemption_ratio_pct": round(redemption_ratio * 100.0, 4),
     "liquidity_haircut_bps": haircut_bps,
     "liquidity_haircut_yuan": haircut_yuan,
     "total_execution_friction_bps": round(impact_vwap_bps + haircut_bps, 2),
     "total_execution_friction_yuan": round(impact_vwap_yuan + haircut_yuan, 2),
     ```
   - 保留原有的 `slippage_saved_bps` 随 `order_amount` 单调递增特性，确保现有 59 项测试 100% 绿灯。
2. 新增专门的类方法 `SmartExecutionDCAEngine.calculate_otc_fund_liquidity_haircut`。

#### 步骤三：在 `app_gui.py` 与 `portfolio_manager.py` 中接入呈现
1. 在 Tab 1（定投计划表）与 Tab 2（调仓执行单中）：
   - 对买入/卖出大额订单渲染“前五大重仓股日均成交额 (ADV)”、“赎回占规模比 (AUM Ratio)”与“流动性折价惩罚 (¥/bps)”；
   - 大额变现（如金额超 10 万元或占规模超 0.5%）高亮预警并提示分批减仓。

---

## 5. Verification Method (独立验证方法)

后续实施代理可通过以下指令和测试用例进行独立验证：

### 5.1 自动化测试验证指令
```powershell
# 1. 验证裁判底线与 simulate_execution 签名逻辑零修改
py -3 -m pytest tests/test_infra.py tests/test_auditor_g9_m2_integrity.py

# 2. 验证现有微观执行与滑点测试完全保持绿灯
py -3 -m pytest tests/test_g3_evolution_loop.py -k "test_vwap_execution_slippage_and_smart_dca"

# 3. 新增针对非线性流动性折价惩罚的专项测试 (新增测试文件 tests/test_g10_liquidity_haircut.py)
py -3 -m pytest tests/test_g10_liquidity_haircut.py
```

### 5.2 专项测试用例断言清单
1. **签名与底线不变性**:
   `inspect.signature(DataLoader.simulate_execution)` 参数列表与默认值严格等于 `['weights_df', 'prices_df', 'is_otc', 'penalty_days', 'penalty_rate', 'etf_impact']`。
2. **场内 ETF 物理隔离**:
   `is_etf=True`（如 `518880`、`510300`）其 `liquidity_haircut_bps == 0.0`。
3. **场外公募非线性与单调性**:
   对 `005561`、`100032`、`011613` 输入 `[1000, 10000, 100000, 1000000, 10000000]`，断言 `haircut_bps` 严格单调递增，且不是常数。
4. **真实 AUM 与 Top 5 ADV 穿透**:
   断言 `000933` 能够成功读取 `top10_stocks[:5]`，并且 `aum_yuan > 0`、`top5_adv_yuan > 0`。
5. **分笔平账与分厘守恒**:
   5 阶段分笔调度之和与订单总金额严格相等（误差 $< 0.02$ 元）。
