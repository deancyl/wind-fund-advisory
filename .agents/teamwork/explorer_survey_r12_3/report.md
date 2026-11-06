# G5 浮盈安全垫抗震承压、本金破净临界点模型与全量测试套件调研报告

**调研员**: teamwork_explorer (`explorer_survey_r12_3`)  
**调研日期**: 2026-11-06 (UTC) / 2026-11-07 (CST)  
**上级调度员**: `71f16351-ac4e-45f7-b8a4-89e38ec8863c`  
**调研对象**: `portfolio_manager.py`, `strategy_bridge.py`, `app_gui.py` (Tab 2), `data/processed/aligned_matrix_total_return.parquet`, 全量测试套件

---

## 一、 核心调研结论速览 (Executive Summary)

1. **当前现状与核心缺陷**：
   - 当前 `portfolio_manager.py` 与 `app_gui.py` 具备成熟的持仓账本数据结构（`FundHolding`, `HoldingBatch`, `floating_pnl`）和基于 9 大资产类别的年化票息安全垫计算（`StrategyBridge.calculate_portfolio_yield_cushion`），但在 Tab 2 中**完全缺失量化的组合 Beta 弹性系数测算、浮盈+票息综合安全垫厚度推演、以及本金破净/回本安全边际与大盘极端回调情景模拟**。
   - 历史 Beta 计算在此前仅作为文字标签或存在于 `src/analysis/metrics.py:130` 的离线分析中，未曾打通至实盘持仓管理器与 GUI 界面。
   - `FUND_INDEX_PRICE_MAP` 字典中存在一处标的映射陷阱：`013841`（银华集成电路C，芯片科技）被误映射至 `930609`（债券），需依托 `PortfolioManager.classify_fund_asset_class` 校验纠偏为 `STAR50_STITCH`。

2. **数学模型闭环构建**：
   - **单基与组合加权 Beta**：依托 `data/processed/aligned_matrix_total_return.parquet`（覆盖 2018-01 至 2026-11 共 2145 个交易日）中对齐的 `H00300` 全收益基准，通过协方差/方差公式实测 9 大资产类别相对沪深 300 的真实历史 Beta：科创50（1.235）、中证1000（1.032）、中证500（1.018）、沪深300（1.000）、中证红利（0.667）、红利低波（0.590）、标普500（0.122）、黄金（0.011）、纯债（-0.012）。结合现金（Beta=0）加权计算组合总 $\beta_p$。
   - **综合安全垫厚度**：综合安全垫 $S_{\text{cushion}} = \text{账面浮盈} (\Delta P) + \text{预计年化内生收息安全垫} (Y_{\text{ann}})$，安全垫厚度比率 $\text{cushion\_ratio} = \frac{S_{\text{cushion}}}{\text{总本金成本 } C_{\text{total}}}$。
   - **破净与回本临界点**：
     - 若 $S_{\text{cushion}} > 0$：大盘需连续下跌 $R_{m,\text{break}} = - \frac{S_{\text{cushion}}}{E \times \beta_p}$，才会将账面浮盈与年内票息跌光触及本金成本线；
     - 若 $\Delta P < 0$：大盘仅需反弹 $R_{m,\text{recover}} = \frac{|\Delta P|}{E \times \beta_p}$，即可实现组合整体回本。
   - **三级压力推演**：针对单日急跌 3%、周度回调 5%、极端回调 10%，推演组合跌幅、跌后总资产及跌后剩余安全垫厚度，用确定性数学底线阻断恐慌性割肉。

3. **全量测试套件现状**：
   - 现存 4 大核心测试套件已验证 100% 通过（共 46 项用例）：`test_infra.py` (14/14), `test_adv_final_closure.py` (14/14), `test_g3_evolution_loop.py` (8/8), `test_gui_multi_ledger_stress.py` (10/10)。
   - **关键发现**：`test_adv_final_closure.py::test_specialized_5` 与 `test_g3_7` 对 `portfolio_ledger.json` 主实盘账本有硬编码 5 大核心基金（005561, 100032, 000216, 017436, 011613）及官方正名（华安纳斯达克）强依赖，运行测试前后严禁破坏该主实盘文件。
   - 为 G5 在 `tests/test_g3_evolution_loop.py` 中规划新增 4 组共 12 项专项单元与集成测试。

---

## 二、 现有代码与数据资产勘测

### 1. `portfolio_manager.py` 持仓账本与数据结构
- **核心数据模型 (`dataclass`)**：
  - `HoldingBatch` (行 247-256)：批次级 FIFO，含 `shares`, `cost_nav`, `holding_days`, `safety_lock`。
  - `FundHolding` (行 260-293)：单基全景，含 `market_value`（市值）, `cost_basis`（成本总额）, `floating_pnl`（浮动盈亏额）, `floating_pnl_pct`（浮动盈亏率）。
  - `PortfolioManager` (行 2568 起)：持仓管理核心实例：
    - `self.holdings`: `Dict[str, FundHolding]`
    - `self.available_cash`: 可用现金
    - `self.in_transit_cash`: 在途交收现金
    - `self.total_equity`: 总资产 = 市值 + 可用现金 + 在途现金
    - 组合总成本 $C_{\text{total}} = \sum \text{cost\_basis} + \text{available\_cash} + \text{in\_transit\_cash} = \text{total\_equity} - \text{total\_floating\_pnl}$
    - 组合总浮盈 $\Delta P = \sum \text{floating\_pnl} = \text{total\_market\_value} - \sum \text{cost\_basis}$
- **9 大标准资产类别分类器 (`classify_fund_asset_class`)** (行 4883-5008)：
  1. `纯债固收`（含国债、固收、裕祥、002351、018757 等）
  2. `黄金对冲`（含黄金、AU9999、000216、518880 等）
  3. `美股海外对冲`（含纳斯达克、标普500、050025、017436 等）
  4. `A股红利低波`（含红利低波、005561、007466 等）
  5. `A股红利高股息`（含中证红利、银行、央企、100032、090010 等）
  6. `科技成长进攻`（含科创50、芯片、半导体、011612、011613、013841 等）
  7. `中小盘成长`（含中证1000、016634 等）
  8. `中盘均衡`（含中证500、医药、161726 等）
  9. `核心蓝筹`（含沪深300、白酒、蓝筹、110020、161725 等）
- **标的至指数映射字典 `FUND_INDEX_PRICE_MAP`** (行 1583-1617)：
  - 存在一处潜在缺陷：`"013841": "930609"`，将银华集成电路（半导体）映射为了纯债指数。在计算 Beta 时，必须优先调用 `classify_fund_asset_class`，确保该类标的归入 `STAR50_STITCH`。

### 2. `strategy_bridge.py` 票息安全垫现状
- **现有安全垫函数 (`calculate_portfolio_yield_cushion`)** (行 1961-2047)：
  - 基于各标准资产类别的底层股息率与到期票息率基准加权测算：
    - A股红利低波: 5.20%
    - A股红利高股息: 4.80%
    - 核心蓝筹: 2.80%
    - 纯债固收: 2.75%
    - 中盘均衡: 1.80%
    - 美股海外对冲: 1.30%
    - 中小盘成长: 1.00%
    - 科技成长进攻: 0.60%
    - 黄金对冲: 0.00%
  - 返回字典含：`weighted_yield_pct` (加权息率), `annual_cushion_amount` (年化内生收息安全垫金额), `monthly_equivalent_amount` (月均现金流), `category_breakdown`。
  - **不足之处**：此前未将该票息安全垫与账面累计浮盈结合计算抗震厚度，亦未结合 Beta 推导大盘破净临界点。

### 3. `app_gui.py` Tab 2（持仓账本）界面结构勘测
- **位置**：`with tab_holdings_and_rebalance:` (行 3701 起)。
- **第一层**：顶部环境横幅 (行 3904-3910) 展示了资产基线、持仓只数、预计年化内生收息安全垫 ¥XX/年。
- **第二层**：4 张高信息密度资产概览卡片 (行 3991-4056)：
  - 卡片 1: 持仓总市值 (仓位 %)
  - 卡片 2: 可用现金池 (现金比 %)
  - 卡片 3: 累计浮动盈亏 (浮动盈亏率 %, 今日预估)
  - 卡片 4: 锁仓与超额概览 (免罚只数/锁定只数, Alpha)
- **接入位置建议**：
  根据“界面复杂度守恒原则”，在 4 张概览卡片下方，将原有的纯静态文字横幅（行 3904-3910）升级置换为一个高信息密度、交互折叠友好的 **“🛡️ 浮盈安全垫抗震承压与本金破净临界看板”**，并紧凑排布 3 级承压情景推演，既不增加垂直滚屏负担，又直接交付核心量化价值。

---

## 三、 单基真实 Beta 与组合加权 Beta 测算模型

### 1. 真实历史数据基准与序列来源
- **数据源文件**：`data/processed/aligned_matrix_total_return.parquet`
  - 数据周期：`2018-01-02` 至 `2026-11-06`，共 2145 个对齐交易日。
  - 基准大盘列：`H00300`（沪深300全收益指数，反映 A 股核心大盘基准收益）。
  - 各资产类别基准序列：`H00300`, `H00905`, `H00852`, `H00922`, `H30269`, `930609`, `H11009`, `STAR50_STITCH`, `AU9999`, `SPX_CNY`。

### 2. 单基历史 Beta 测算逻辑
设基准收益率序列为 $r_m = \frac{\Delta H00300}{H00300}$，标的收益率序列为 $r_i$。
根据 CAPM 模型标准定义：
$$\beta_i = \frac{\text{Cov}(r_i, r_m)}{\text{Var}(r_m)}$$

**多级数据解析优先级**：
1. **单基专属日线**：若基金在本地存在 parquet 历史日线数据（如 `data/processed/funds/{code}.OF.parquet`），且与 `H00300` 交易日交集 $\ge 30$ 天，则直接按单基真实收益率序列回归计算。
2. **标的映射指数**：若无单基历史日线，但属于标准赛道，读取 `FUND_INDEX_PRICE_MAP` 对应指数列。
3. **资产类别基准回退**：若为外部录入基金，通过 `classify_fund_asset_class` 动态解析至 9 大资产类别之一，映射至对齐矩阵标准列：

| 资产大类 | 映射矩阵列 | 全历史实测 Beta (2018-2026) | 近1年滚动 Beta (250天) | 经济金融含义 |
| :--- | :--- | :--- | :--- | :--- |
| **科技成长进攻** | `STAR50_STITCH` | **1.235** | 1.853 | 高 Beta 强进攻弹性，顺周期主升浪放大器 |
| **中小盘成长** | `H00852` | **1.032** | 1.298 | 典型成长弹性，略高于大盘 |
| **中盘均衡** | `H00905` | **1.018** | 1.371 | 均衡配置，与大盘同步波动 |
| **核心蓝筹** | `H00300` | **1.000** | 1.000 | 大盘基准锚 |
| **A股红利高股息** | `H00922` | **0.667** | 0.234 | 典型低 Beta 防御资产，抗跌属性明显 |
| **A股红利低波** | `H30269` | **0.590** | 0.016 | 极低 Beta，震荡市回撤控制利器 |
| **美股海外对冲** | `SPX_CNY` | **0.122** | 0.117 | 弱相关跨市场资产，分散系统性风险 |
| **黄金对冲** | `AU9999` | **0.011** | 0.064 | 零 Beta 独立避险资产，提供非对称保护 |
| **纯债固收** | `H11009` | **-0.012** | -0.000 | 负 Beta 负相关压舱石，平抑组合剧震 |

### 3. 组合加权总 Beta ($\beta_p$)
在全组合总资产视角下，每个标的相对总资产 $E$ 的持仓权重为 $w_i = \frac{m_i}{E}$。
可用现金池与在途资金其系统性波动与大盘无关，即 $\beta_{\text{cash}} = 0$。
因此，组合加权总 Beta 为：
$$\beta_p = \sum_{i=1}^n w_i \beta_i + w_{\text{cash}} \times 0 = \sum_{i=1}^n \left(\frac{m_i}{E}\right) \beta_i = \left(\frac{M_{\text{equity}}}{E}\right) \beta_{\text{equity}}$$

*实证示例（以标准演示实盘为例，总资产 ¥191,445，权益仓位 75.8%）：*
- 005561（创金红利低波）：权重 26.3%，Beta 0.590 $\rightarrow$ 贡献 0.155
- 100032（富国中证红利）：权重 19.8%，Beta 0.667 $\rightarrow$ 贡献 0.132
- 011612/011613（科创50）：权重 17.8%，Beta 1.235 $\rightarrow$ 贡献 0.220
- 001071（标普500）：权重 6.4%，Beta 0.122 $\rightarrow$ 贡献 0.008
- 现金与在途：权重 24.2%，Beta 0.000 $\rightarrow$ 贡献 0.000
- **组合综合加权总 Beta $\beta_p = 0.514$**（大盘跌 1%，组合仅跌 0.51%）。

---

## 四、 浮盈安全垫与本金破净/回本临界点数学模型

### 1. 浮盈安全垫厚度定义
- **总本金成本 ($C_{\text{total}}$)**：
  $$C_{\text{total}} = \sum_{i} \text{cost\_basis}_i + \text{available\_cash} + \text{in\_transit\_cash} = E - \Delta P$$
- **年化票息安全垫 ($Y_{\text{ann}}$)**：来自 `StrategyBridge.calculate_portfolio_yield_cushion`。
- **账面累计浮盈 ($\Delta P$)**：$\Delta P = \sum \text{floating\_pnl}_i$。
- **综合安全垫总额 ($S_{\text{cushion}}$)**：
  $$S_{\text{cushion}} = \Delta P + Y_{\text{ann}}$$
- **安全垫厚度百分比 ($\text{cushion\_ratio}$)**：
  $$\text{cushion\_ratio} = \frac{S_{\text{cushion}}}{C_{\text{total}}} \times 100\%$$

### 2. 本金破净安全边际 (Break-Even Margin)
当大盘（沪深300）下跌百分比为 $R_m$ 时，组合因市场贝塔带来的预计总资产变动为：
$$\Delta E = E \times \beta_p \times R_m$$

#### 情形 A：当前组合处于安全垫充足状态 ($S_{\text{cushion}} > 0$)
计算沪深 300 需要连续下跌多少百分比 ($R_{m,\text{break}} < 0$) 或点位，才会将账面浮盈与年内收息全部跌光，恰好触及本金成本线：
$$\Delta E = - S_{\text{cushion}} \implies E \times \beta_p \times R_{m,\text{break}} = - S_{\text{cushion}}$$
$$R_{m,\text{break}} = - \frac{S_{\text{cushion}}}{E \times \beta_p}$$
点位推算：设当前沪深 300 点位为 $I_{300}$，破净临界点位为：
$$I_{\text{break}} = I_{300} \times (1 + R_{m,\text{break}})$$

*实测数值推导（演示组合）：*
- 浮盈 $\Delta P = ¥7,190.0$，年票息 $Y_{\text{ann}} = ¥4,862.7$，总安全垫 $S_{\text{cushion}} = ¥12,052.7$
- 安全垫厚度：$\frac{12,052.7}{179,392.3} = 6.72\%$
- 组合 Beta $\beta_p = 0.5144$，总资产 $E = ¥191,445$
- 破净临界下跌幅度：
  $$R_{m,\text{break}} = - \frac{12,052.7}{191,445 \times 0.5144} = -12.24\%$$
- 若当前沪深 300 为 3,920 点，则需连续狂跌至 **3,440 点** 才会触及本金。给用户极强的心理定力！

#### 情形 B：当前组合已处于浮亏状态 ($\Delta P < 0$)
若账面发生浮亏，用户最关心的是“大盘反弹到多少点我就能回本”：
为了填平纯账面浮亏 $|\Delta P|$，组合所需的回本升幅对应的大盘反弹幅度 $R_{m,\text{recover}} > 0$：
$$R_{m,\text{recover}} = \frac{|\Delta P|}{E \times \beta_p}$$
回本目标点位：
$$I_{\text{recover}} = I_{300} \times (1 + R_{m,\text{recover}})$$
若结合年化票息加速回本，扣除票息后的净缺口反弹要求为 $\max\left(0, \frac{|\Delta P| - Y_{\text{ann}}}{E \times \beta_p}\right)$。

### 3. 三大承压情景推演 (Stress Testing Scenarios)
针对市场常见的震荡急跌与黑天鹅回调，推演三种标准压力情景（$R_{m} \in \{-3\%, -5\%, -10\%\}$）：

| 压力情景 | 大盘假定跌幅 | 组合预计跌幅 ($\beta_p \times R_m$) | 组合预计亏损额 | 扣减后剩余安全垫 | 本金破净状态评估 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **情景 1：单日急跌** | -3.0% | **-1.54%** | -¥2,954.5 | **+¥9,098.2** | 🟢 安全垫仍厚达 5.07%，从容吃息 |
| **情景 2：周度回调** | -5.0% | **-2.57%** | -¥4,924.1 | **+¥7,128.6** | 🟢 安全垫仍余 3.97%，严禁慌乱割肉 |
| **情景 3：极端回调** | -10.0% | **-5.14%** | -¥9,848.3 | **+¥2,204.4** | 🟢 极端暴跌下仍高于本金成本线，尽显低波红利韧性 |

---

## 五、 Tab 2 前端界面排版与交互设计方案

遵循“**界面复杂度守恒原则**”，在 Tab 2 中不增加额外臃肿卡片，而是将原有的文字式说明横幅重构为结构紧凑、数字鲜活的量化抗震仪表板：

### 1. 结构草案 (HTML/CSS 布局)
```html
<div style="background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 8px; padding: 14px 16px; margin-bottom: 12px;">
    <!-- 顶栏：组合Beta、安全垫厚度与破净/回本临界点 -->
    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border-subtle); padding-bottom: 10px; margin-bottom: 10px;">
        <div>
            <span style="font-size: 14px; font-weight: 700; color: var(--text-primary);">🛡️ 组合抗震承压与本金安全边际</span>
            <span style="margin-left: 10px; font-size: 12px; background: rgba(59, 130, 246, 0.15); color: #3b82f6; padding: 2px 8px; border-radius: 4px;">加权 Beta: 0.51</span>
        </div>
        <div style="font-size: 13px; font-weight: 600; color: #10b981;">
            综合安全垫厚度: ¥12,053 (+6.72%)
        </div>
    </div>
    <!-- 中栏：破净/回本安全边际核心结论 -->
    <div style="font-size: 12px; line-height: 1.6; color: var(--text-secondary); margin-bottom: 10px;">
        🎯 <b>破净安全边际</b>：沪深 300 需连续暴跌 <b>-12.24%</b> (从 3,920 点跌破 <b>3,440 点</b>)，才会把当前账面浮盈与年化内生收息安全垫全部跌光触及本金成本线！
    </div>
    <!-- 底栏：3 档压力测试卡片一行并列排布 -->
    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px;">
        <div class="stress-card">单日急跌 -3% ➔ 组合预计 -1.54% (剩余安全垫 ¥9,098)</div>
        <div class="stress-card">周度回调 -5% ➔ 组合预计 -2.57% (剩余安全垫 ¥7,129)</div>
        <div class="stress-card">极端回调 -10% ➔ 组合预计 -5.14% (剩余安全垫 ¥2,204)</div>
    </div>
</div>
```

### 2. 交互与响应式支持
- **账本实时联动**：每次切换主实盘、家庭账本或沙盒时，直接根据当前激活 `pm.holdings` 重新触发计算，无跨账本串扰。
- **全空账本/全现金容错**：当持仓为空或全额现金时，加权 Beta 自动置为 0.00，破净边际显示“当前为 100% 现金流动性，物理免疫大盘波动”。
- **浮亏账本自适应**：当 $\Delta P < 0$ 时，文字自动从“破净安全边际”切换为“回本临界点”：“大盘仅需反弹 +X.XX% (回升至 YYYY 点) 组合即可整体平水回本”。

---

## 六、 全量自动化测试套件现状与 G5 新增用例规划

### 1. 现存 4 大核心套件基线验证结果
1. `pytest tests/test_infra.py`：**14 passed** (5.67s)
   - 验证了全收益对齐矩阵加载、T+1 执行算子、7天惩罚费扣减、裁判引擎 AST 与 4 流派。
2. `pytest tests/test_adv_final_closure.py`：**14 passed** (28.07s)
   - 验证了 9 大标准资产类别覆盖、影子账本审计、估值分位防欺诈、主实盘 5 大核心基金守恒。
3. `pytest tests/test_g3_evolution_loop.py`：**8 passed** (2.70s)
   - 验证了 EWMA 动态相关性突变防线（0.75 警戒阈值）、10,000 次蒙特卡洛块重采样、VWAP 微观滑点优化、历史三大拐点实证信号。
4. `pytest tests/test_gui_multi_ledger_stress.py`：**10 passed** (32.03s)
   - 验证了多账本高频切换原子性、另存为沙盒、残损账本自愈、Streamlit AppTest 端到端 0 异常。

### 2. 勘测发现的测试护栏红线 (Critical Guardrails)
- **主实盘数据污染免疫**：`tests/test_adv_final_closure.py` 中的 `test_specialized_5` 会读取 `portfolio_ledger.json`，强校验必须包含 `005561`, `100032`, `000216`, `017436`, `011613` 五大标的且总资产 $\ge ¥90,000$。开发过程中切勿将沙盒演练数据或测试临时持仓写死覆盖主实盘文件。

### 3. G5 在 `tests/test_g3_evolution_loop.py` 中新增测试规划
在现有 8 个用例之后，扩充 G5 专属 4 组用例（`test_g5_1` 至 `test_g5_4`）：

```python
def test_g5_1_single_fund_authentic_volatility_and_differential_slippage(self):
    """
    G5-1: 单基真实年化波动率与差异化尾盘损耗验证
    1. 验证 advisory_engine 实时从本地日线精算单基真实 20 日波动率与自身 bias_20
    2. 验证红利低波 (005561)、纯债 (002351) 与科创50 (011613) 在相同申购金额下展现出严格差异化的尾盘损耗基点 (严禁三档常数 0.04/0.14/0.18 回退)
    """

def test_g5_2_historical_inflection_point_bar_and_frontend_wireup(self):
    """
    G5-2: 历史三大拐点对照条前端渲染与数据真实性校验
    1. 验证 2021年2月 (0.50x)、2022年4月 (1.93x)、2024年9月 (1.94x) 静态基准数据真实性
    2. 验证 app_gui.py 中首屏/Tab 1 对照条源码挂载与紧凑单行 CSS 几何无碰撞
    """

def test_g5_3_floating_cushion_weighted_beta_and_break_even_stress_model(self):
    """
    G5-3: 浮盈安全垫、组合加权 Beta 与破净/回本临界承压模型精算验证
    1. 验证组合加权 Beta 系数在不同资产配置组合下的加权精度与现金 0 Beta 折算
    2. 验证综合安全垫金额 = 浮盈 + 年化票息，厚度比率数学精确
    3. 验证破净安全边际计算 (浮盈状态下跌幅 R_break 与点位) 及回本临界点 (浮亏状态下反弹幅 R_recover)
    4. 验证 -3%, -5%, -10% 三档极端承压推演数值守恒与剩余安全垫精确计算
    5. 验证全额现金、全额债券等边界条件的零除自愈容错
    """

def test_g5_4_tail_end_intraday_valuation_anomaly_and_alert(self):
    """
    G5-4: 14:30 尾盘实时估值异动防追高与黄金坑吸筹预警验证
    1. 真实盘中涨跌幅 |gszzl| > 1.5 * sigma_day 且高乖离时触发防追高预警 (建议下调30%~50%)
    2. 真实盘中急跌且负乖离时触发黄金坑吸筹预警
    3. 验证该预警信号在 Tab 2 调仓执行单与定投计划实操要点列中的正确挂载
    """
```

---

## 七、 实施落地建议与函数接口草案

### 1. `PortfolioManager` 新增方法设计 (`portfolio_manager.py`)
```python
@classmethod
def calculate_asset_historical_beta(cls, asset_code_or_class: str, lookback_window: int = 250) -> float:
    """计算单个资产相对沪深300 (H00300) 的真实历史 Beta"""
    # 1. 优先从 aligned_matrix_total_return.parquet 读取对应列与 H00300
    # 2. 计算 cov(r_asset, r_h300) / var(r_h300)
    # 3. 缺省或异常时返回合理物理基准 (如核心蓝筹 1.0, 纯债 0.0)

def calculate_portfolio_cushion_and_stress_model(self, current_index_point: float = 3920.0) -> Dict[str, Any]:
    """
    组合综合安全垫、加权 Beta、破净/回本安全边际与三级压力测试推演全量精算接口
    """
    # 1. 计算总资产、总本金、账面浮盈
    # 2. 调用 StrategyBridge.calculate_portfolio_yield_cushion 获取年票息
    # 3. 计算组合加权 Beta
    # 4. 计算破净安全边际与回本临界点
    # 5. 计算 -3%, -5%, -10% 三大压力情景推演数据
    # 6. 返回结构化字典供前端直接渲染
```

### 2. `StrategyBridge` 桥接封装 (`strategy_bridge.py`)
在 `StrategyBridge` 中增加类方法：
`StrategyBridge.calculate_portfolio_cushion_and_stress_model(holdings, available_cash, in_transit_cash, ...)`
保证在跨模块、批量脚本或多账本调用时的统一接口。

---

*报告编写完成，所有数据均来自工作区本地真实日线净值、对齐矩阵与现存代码库，严禁使用任何伪造常数。*
