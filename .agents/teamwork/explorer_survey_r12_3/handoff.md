# Handoff Report: G5 浮盈安全垫抗震承压、本金破净临界点模型与全量测试套件调研

**工作目录**: `d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r12_3\`  
**智能体角色**: `teamwork_explorer`  
**交接对象**: 上级调度员 (`71f16351-ac4e-45f7-b8a4-89e38ec8863c`)

---

## 1. Observation (观测事实)

1. **持仓结构与现有安全垫机制**：
   - `AGY2_FundAdvisory/portfolio_manager.py` 行 247-293 定义了 `HoldingBatch` 与 `FundHolding`，其中单基浮盈 `floating_pnl` 与浮盈率 `floating_pnl_pct` 已完整持久化。
   - `AGY2_FundAdvisory/portfolio_manager.py` 行 4883-5008 定义了 `classify_fund_asset_class`，支持将基金自动精准归类至 9 大标准类别。
   - `AGY2_FundAdvisory/strategy_bridge.py` 行 1961-2047 实现了 `calculate_portfolio_yield_cushion`，基于 9 大类别底层资产股息率/票息率基准加权输出 `annual_cushion_amount`（年化内生收息安全垫金额）。
   - `AGY2_FundAdvisory/portfolio_manager.py` 行 1583-1617 中的 `FUND_INDEX_PRICE_MAP` 字典存在异常映射：`"013841": "930609"`，将银华集成电路（科技半导体）误映射为债券指数；但 `classify_fund_asset_class` 行 4982 正确判定为“科技成长进攻”。

2. **对齐矩阵与真实 Beta 实测**：
   - `data/processed/aligned_matrix_total_return.parquet` 覆盖 2018-01-02 至 2026-11-06（2145 行），包含基准 `H00300` 及全部核心大类资产全收益指数。
   - 运行脚本实测各资产相对 `H00300` 的全历史 Beta（$\frac{\text{Cov}(r_i, r_{300})}{\text{Var}(r_{300})}$）：
     - `STAR50_STITCH` (科创50): **1.235**
     - `H00852` (中证1000): **1.032**
     - `H00905` (中证500): **1.018**
     - `H00300` (沪深300): **1.000**
     - `H00922` (中证红利): **0.667**
     - `H30269` (红利低波): **0.590**
     - `SPX_CNY` (标普500人民币): **0.122**
     - `AU9999` (黄金): **0.011**
     - `H11009` (纯债): **-0.012**
   - 现金与在途资产 Beta 严格为 0.000。

3. **前端展示现状**：
   - `AGY2_FundAdvisory/app_gui.py` 行 3701 起为 Tab 2（持仓调仓）。行 3904-3910 存在一个静态文字横幅展示“预计年化内生收息安全垫”，行 3991-4056 渲染了 4 张资产概览卡片。当前 Tab 2 尚无任何关于组合加权 Beta、破净临界下跌幅度、回本反弹幅度及 3/5/10% 承压推演的看板展示。

4. **全量自动化测试基线结果**：
   - 执行 `py -3 -m pytest tests/test_infra.py`：**14 passed** in 5.67s。
   - 执行 `py -3 -m pytest tests/test_adv_final_closure.py`：**14 passed** in 28.07s。
   - 执行 `py -3 -m pytest tests/test_g3_evolution_loop.py`：**8 passed** in 2.70s。
   - 执行 `py -3 -m pytest tests/test_gui_multi_ledger_stress.py`：**10 passed** in 32.03s。
   - 发现测试陷阱：`test_adv_final_closure.py::test_specialized_5`（行 218）断言主实盘账本 `portfolio_ledger.json` 必须保留五大核心标的 `["005561", "100032", "000216", "017436", "011613"]`，且 `test_g3_7`（行 383）断言其中不得出现“华宝”而必须为“华安纳斯达克”。

---

## 2. Logic Chain (推理链条)

1. **由 Observation 1 & 2**：
   - 组合的总资产 $E$ 包含权益资产与现金类资产。由于各资产相对沪深300具有明确且差异化的真实历史 Beta（从纯债的 -0.012 到科创50的 1.235），且现金 Beta=0，组合加权 Beta $\beta_p = \sum \frac{m_i}{E} \beta_i$ 能够精确反映市场变动对组合总资产的真实传导比例。
2. **由 Observation 1**：
   - 组合总成本 $C_{\text{total}} = E - \Delta P$，其中账面浮盈 $\Delta P = \sum \text{floating\_pnl}_i$。年化票息安全垫 $Y_{\text{ann}}$ 是持仓未来一年确定性内生分红现金流。二者之和构成综合抗震安全垫 $S_{\text{cushion}} = \Delta P + Y_{\text{ann}}$。
3. **由 Observation 2 & Logic Step 1-2**：
   - 当大盘下跌 $R_m$ 时，组合总资产缩水 $\Delta E = E \times \beta_p \times R_m$。
   - 当 $S_{\text{cushion}} > 0$ 时，安全垫全被抹平触及本金线的条件为 $\Delta E = -S_{\text{cushion}}$，解出大盘破净临界跌幅 $R_{m,\text{break}} = - \frac{S_{\text{cushion}}}{E \times \beta_p}$。由于低波红利与纯债使 $\beta_p \approx 0.5$，安全垫厚度被放大近一倍耐受度（如 6% 安全垫可抵御大盘下跌 12%）。
   - 当 $\Delta P < 0$ 时，填补浮亏所需的大盘回本反弹幅度为 $R_{m,\text{recover}} = \frac{|\Delta P|}{E \times \beta_p}$。
4. **由 Observation 3**：
   - 在 Tab 2 中，替换原有的纯静态文字横幅为包含加权 Beta、安全垫厚度、破净安全边际与 3 档（-3%, -5%, -10%）承压情景的一行紧凑对比卡，既满足 ORIGINAL_REQUEST.md 的三项推演要求，又严格遵守“界面复杂度守恒原则”。
5. **由 Observation 4**：
   - 现存 46 项自动化测试全部完好，测试套件处于健康绿色基线。在 `test_g3_evolution_loop.py` 末尾扩展 `test_g5_1` 至 `test_g5_4` 专项用例，可无缝衔接 G5 验收。

---

## 3. Caveats (潜在风险与未探明区域)

1. **场外外部非标基金的日线覆盖度**：若用户手动输入极小众的非标基金代码且无本地日线，模型将自适应回退至 9 大资产类别的标准矩阵列 Beta（已能满足绝大多数金融场景，但个股暴露型主动权益可能会有残差）。
2. **实时大盘点位获取**：若外部实时行情接口因网络限制无法拉取当日盘中 000300 实时点位，模型需兜底使用矩阵最新有效收盘点位（`df_mat['H00300'].iloc[-1]`）。
3. **主实盘账本隔离**：开发和测试过程中切勿执行将 demo_portfolio 覆盖写入 `portfolio_ledger.json` 的操作，以防触发 `test_adv_final_closure.py` 断言失败。

---

## 4. Conclusion (调研结论)

1. 浮盈安全垫抗震承压与破净临界点模型具有严谨、完备的数学解析解，所依赖的全部底层日线与基准序列在本地湖仓中 100% 存在，零伪造常数。
2. 测算逻辑应统一实装在 `portfolio_manager.py`（增加 `calculate_asset_historical_beta` 与 `calculate_portfolio_cushion_and_stress_model`），并通过 `StrategyBridge` 提供统一静态包装，在 `app_gui.py` Tab 2 中紧凑渲染。
3. 现存 4 大测试套件 100% 通过，为后续实施提供了稳固的工程防护网。

---

## 5. Verification Method (独立核验方法)

1. **测试基线验证**：
   ```powershell
   py -3 -m pytest tests/test_infra.py
   py -3 -m pytest tests/test_adv_final_closure.py
   py -3 -m pytest tests/test_g3_evolution_loop.py
   py -3 -m pytest tests/test_gui_multi_ledger_stress.py
   ```
   **期望结果**：全部 46 项用例 100% 通过（exit code 0）。

2. **对齐矩阵与 Beta 测算原型验证**：
   运行以下命令验证真实 Beta 与安全垫数学推演：
   ```powershell
   py -3 -c "import pandas as pd, numpy as np; df = pd.read_parquet('data/processed/aligned_matrix_total_return.parquet'); rets = df.set_index('date').pct_change().dropna(); b = rets['H00300']; vb = np.var(b); print('H30269 beta:', np.cov(rets['H30269'], b)[0,1]/vb, 'STAR50 beta:', np.cov(rets['STAR50_STITCH'], b)[0,1]/vb)"
   ```
   **期望结果**：H30269（红利低波）输出约 0.590，STAR50_STITCH（科创50）输出约 1.235。

3. **文档产物检查**：
   - 检查 `d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r12_3\report.md`
   - 检查 `d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r12_3\handoff.md`
