# Handoff Report — Milestone 1 (M1) 量化核心算法升级与穿透计算

**执行工程师**: teamwork_worker (`worker_prod_r12_m1`)  
**任务目标**: 实装 G5 世代四大核心量化投顾计算底座，消除伪常数与伪随机数，实现纯净真实时序驱动的量化引擎。  
**目标上级调度员**: `71f16351-ac4e-45f7-b8a4-89e38ec8863c`  

---

## 1. Observation (客观事实与直接观测)

### 1.1 代码变更前现存缺陷与常数观测
1. **固定常数与调用断层**：
   - 在 `AGY2_FundAdvisory/advisory_engine.py:1324` 中直接硬编码了场内 ETF 波动率回退常量 `else 0.18`；
   - 在 `AGY2_FundAdvisory/advisory_engine.py:1367-1372` 中直接硬编码了三档公募基金波动率常数：
     ```python
     elif any(k in fn for k in ["债", "固收", "纯债"]) or fc == "002351":
         vol = 0.04
     elif any(k in fn for k in ["黄金"]) or fc == "000216":
         vol = 0.14
     else:
         vol = 0.18
     ```
   - 在 `AGY2_FundAdvisory/advisory_engine.py:1488-1489` 的 `plan_smart_dca` 循环中，各标的未传入自身波动率，且 `bias_20` 统一传入了大盘的宏观 `bias`，导致单基自身均线特征被抹杀；
   - 在 `AGY2_FundAdvisory/portfolio_manager.py:1613-1614` 中，`FUND_INDEX_PRICE_MAP` 字典将 `013841` 与 `013840`（银华集成电路芯片科技）错误映射为 `930609`（纯债指数）。

### 1.2 本地时序湖仓直接测算数据
通过读取本地 `data/processed/` 湖仓中的真实 21 个交易日日线序列测算：
- 纯债固收 (`002351` / `csindex_H11009.parquet`)：真实 20 日年化波动率 = `0.68%` (0.0068)，$\text{bias}_{20} = +0.31\%$，$\sigma_{\text{day}} = 0.0432\%$；
- 黄金对冲 (`000216` / `indices/AU9999.SGE.parquet`)：真实 20 日年化波动率 = `13.86%` (0.1386)，$\text{bias}_{20} = +2.29\%$，$\sigma_{\text{day}} = 0.8766\%$；
- 红利低波 (`005561` / `csindex_H30269.parquet`)：真实 20 日年化波动率 = `14.89%` (0.1489)，$\text{bias}_{20} = +0.91\%$，$\sigma_{\text{day}} = 0.9417\%$；
- 中证红利 (`100032` / `csindex_H00922.parquet`)：真实 20 日年化波动率 = `16.01%` (0.1601)，$\text{bias}_{20} = -0.21\%$，$\sigma_{\text{day}} = 1.0128\%$；
- 美股海外 (`017436` / `SPX_CNY`)：真实 20 日年化波动率 = `19.14%` (0.1914)，$\text{bias}_{20} = -5.02\%$，$\sigma_{\text{day}} = 1.2106\%$；
- 科技成长 (`011613` / `indices/000688.SH.parquet`)：真实 20 日年化波动率 = `31.75%` (0.3175)，$\text{bias}_{20} = -11.76\%$，$\sigma_{\text{day}} = 2.0082\%$。

### 1.3 历史三大拐点实证数据观测
调用 `verify_historical_inflection_signals()` 提取：
- `2021-02-18`（核心资产见顶）：ERP 分位 28.9%，Bias20 +4.30%，乘数 `0.50x` (`🟡 0.5x 防守微扣`)；
- `2022-04-26`（跌破2900恐慌底）：ERP 分位 76.0%，Bias20 -8.27%，乘数 `1.93x` (`🚀 2.0x 逆向猛扣`)；
- `2024-09-18`（924政策反转前夕）：ERP 分位 90.6%，Bias20 -2.60%，乘数 `1.94x` (`🚀 2.0x 逆向猛扣`)；
- 今日实时（2026-11-06）：ERP 分位 82.6%，Bias20 -2.07%，乘数 `1.76x` (`⚡ 1.5x 加速吸筹`)。

### 1.4 真实持仓账本历史 Beta 与抗震承压观测
在主实盘账本（总资产 ¥171,729.5，持仓成本 ¥100,000.0，累计浮盈 ¥71,729.5）下：
- 单基历史 Beta 测算（相对 `H00300`）：
  - `005561`（创金红利低波A）：0.5900
  - `100032`（富国中证红利增强A）：0.6667
  - `011613`（华夏科创50联接C）：1.2346
  - `013841`（银华集成电路混合C）：1.2346（纠偏后真实映射 `STAR50_STITCH`）
  - `017436`（华安纳斯达克100联接A）：0.1214
  - `000216`（华安黄金ETF联接A）：0.0111
  - `002351`（易方达裕祥纯债A）：-0.0118
  - `cash`（流动资金）：0.0000
- 组合加权 Beta：$\beta_p = 0.3152$，权益加权 Beta：$\beta_{\text{equity}} = 0.3347$；
- 综合安全垫总额：$S_{\text{cushion}} = ¥71,729.5 + ¥4,962.98 (\text{票息}) = ¥76,692.48$，厚度比率高达 `76.69%`；
- 破净安全边际：$R_{m,\text{break}} = -141.68\%$（安全垫极厚，大盘即便回调 100% 依然本金安全）；
- 3 级承压推演：
  - 单日急跌 -3.0%：组合跌幅 -0.95%，预估亏损 -¥1,623.87，剩余安全垫 ¥75,068.61 (75.07%) 🟢；
  - 周度回调 -5.0%：组合跌幅 -1.58%，预估亏损 -¥2,706.46，剩余安全垫 ¥73,986.02 (73.99%) 🟢；
  - 极端回调 -10.0%：组合跌幅 -3.15%，预估亏损 -¥5,412.91，剩余安全垫 ¥71,279.57 (71.28%) 🟢。

---

## 2. Logic Chain (推理链条与架构决策)

1. **单基时序多级穿透保障物理纯度**：
   - 根据 Observation 1.1，固定常数导致高波科技成长与低波纯债在相同金额下算出的损耗无差异；
   - 根据 Observation 1.2，本地数据湖已具备单基列式 parquet、754 个赛道指数 parquet 及对齐矩阵；
   - 建立 4 级穿透架构（单基专属湖仓 $\rightarrow$ 赛道标杆 $\rightarrow$ 对齐矩阵 $\rightarrow$ 沪深300基准线），计算出真实波动率与自身均线乖离率，彻底消除 `0.04/0.14/0.18` 假常数；
   - 在 `calculate_vwap_execution_slippage` 与 `plan_smart_dca` 中穿透单基指标，使得 5 万元申购下纯债节省 1.58 bps，红利节省 14.23 bps，科创50 节省 42.78 bps，金融逻辑严密闭环。

2. **历史拐点对照尺结构化输出赋能前端**：
   - 根据 Observation 1.3，底层 `verify_historical_inflection_signals` 检验了三大拐点；
   - 通过 `get_historical_inflection_ruler`，将 2021见顶(0.50x)、2022恐慌底(1.93x)、2024反转底(1.94x) 与今日实时水位 (1.76x) 打包成 4 节点紧凑数组，为 M2 前端渲染提供纯净、无冗余的数据结构。

3. **14:30 尾盘实时估值异动基于真实波幅阈值判定**：
   - 提取 `fetch_realtime_fund_quote` 真实盘中估值 `gszzl`，结合单基真实日均波幅 $\sigma_{\text{day}}$；
   - 设立 $\pm 1.5 \sigma_{\text{day}}$ 动态带：
     - 若 `gszzl > +1.5 * sigma_day` 且 `bias_20 > 0` $\rightarrow$ 触发 `ANTI_CHASING` (减额 40% 留待回踩均线)；
     - 若 `gszzl < -1.5 * sigma_day` 且 `bias_20 < 0` $\rightarrow$ 触发 `GOLDEN_PIT` (建议 14:30~14:50 正常或逆向增配 15%)；
     - 否则 `NORMAL`。

4. **安全垫与抗震承压模型的自适应数学推导**：
   - 纠偏 `FUND_INDEX_PRICE_MAP` 中 013841，确保科技成长标的不会误算为债券负贝塔；
   - 基于 CAPM 协方差/方差公式实测 9 大资产历史 Beta，结合现金 0 Beta，精准精算组合加权总 $\beta_p$；
   - 建立双向自适应模型：
     - 浮盈且安全垫充足时：输出大盘连续暴跌临界跌幅 $R_{m,\text{break}} = - \frac{S_{\text{cushion}}}{E \cdot \beta_p}$ 与点位；
     - 浮亏时：自动切换为回本临界点 $R_{m,\text{recover}} = \frac{|\Delta P|}{E \cdot \beta_p}$ 与回本点位；
     - 纯现金/中性固收时：$\beta_p = 0$，自动提示“物理免疫系统性大盘波动”。

---

## 3. Caveats (局限与边界说明)

1. **实时盘中估值 `gszzl` 在非交易时段的物理特性**：在 A 股闭市期间（15:00 之后或周末节假日），天天基金网关返回的 `gszzl` 为当日收盘最终估算涨跌幅；若标的为美股 QDII，盘中估值将受隔夜美股休市与期指波动影响，该类标的建议参考夜盘净值更新。
2. **新上市未满 20 日标的**：若用户手动添加上市不满 20 个交易日的全新次新基金，单基湖仓序列无法满足 21 天，系统将自动回退至第二顺位赛道标杆或第三顺位对齐矩阵对应的资产大类基准，不会导致计算中断或抛出异常。
3. **只读文件严格保护**：裁判文件 `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py` 与 `DataLoader.simulate_execution` 默认签名完全保持原始状态，零字符修改。

---

## 4. Conclusion (交付结论)

Milestone 1（M1）所有核心量化算法与数据模型改造已全部高标准竣工：
1. `AGY2_FundAdvisory/advisory_engine.py`：实装 `get_fund_real_volatility_and_bias` 与 `get_fund_20d_metrics`，彻底消除了固定常数 0.04/0.14/0.18 及 else 0.18；`plan_smart_dca` 穿透了各单基真实波动率与乖离率；实装了 `get_historical_inflection_ruler` 与 `evaluate_tail_valuation_anomaly`；
2. `AGY2_FundAdvisory/portfolio_manager.py`：纠偏了 `FUND_INDEX_PRICE_MAP` 中 `013841` 与 `013840` 映射；实装了单基真实历史 Beta 算子 `calculate_asset_historical_beta`；实装了组合综合安全垫、加权 Beta、破净/回本临界点及三级压力推演全量精算模型 `calculate_portfolio_cushion_and_stress_model`；
3. `AGY2_FundAdvisory/strategy_bridge.py`：在 `StrategyBridge` 类及顶层快捷导出完整暴露了上述所有量化方法；
4. 全量回归测试套件 `test_infra.py` (14/14)、`test_adv_final_closure.py` (14/14)、`test_g3_evolution_loop.py` (8/8) 及专属自验脚本 `verify_m1_core.py` (100%) 全部绿灯通过。

---

## 5. Verification Method (独立核验方法)

下游代理（Orchestrator、Worker M2 或 Auditor）可通过以下命令进行完全无歧义的独立验证：

### 5.1 运行 M1 核心功能专项核验脚本
```powershell
py -3 .agents/teamwork/worker_prod_r12_m1/verify_m1_core.py
```
- **预期输出**：
  - 纯债、红利、科创 50 真实年化波动率分别为 `0.0068`, `0.1489`, `0.3175`；
  - 5 万元执行节省基点分别为 `1.58 bps`, `14.23 bps`, `42.78 bps`（严格递增且高波远大于低波）；
  - 历史三大拐点对照尺输出 4 个节点（2021=0.5x, 2022=1.93x, 2024=1.94x, 今日=1.76x）；
  - 尾盘异动预警正确触发 `ANTI_CHASING` (0.60x), `GOLDEN_PIT` (1.15x), `NORMAL` (1.00x)；
  - 013841 纠偏后 Beta 为 `1.2346`；浮亏账本正确自适应切换为“回本临界点”，全现金账本 Beta=0 自适应提示“物理免疫”；
  - 最终打印 `🎉 ALL G5 CORE QUANT TEST ASSERTIONS PASSED WITH 100% SUCCESS!`。

### 5.2 运行基准自动化回归测试
```powershell
py -3 -m pytest tests/test_infra.py tests/test_adv_final_closure.py
py -3 -m pytest tests/test_g3_evolution_loop.py
```
- **预期输出**：`test_infra.py` + `test_adv_final_closure.py` 28 passed，`test_g3_evolution_loop.py` 8 passed，100% 全部通过。

### 5.3 检验只读文件与修改边界
```powershell
git diff --name-only
```
- **预期输出**：仅包含允许写的文件（`advisory_engine.py`, `portfolio_manager.py`, `strategy_bridge.py` 以及 `.agents/teamwork/` 内的工作记忆文件）。四大裁判文件零修改。

### 5.4 关键失效判定条件 (Invalidation Conditions)
若出现以下任一情况，本交付视为失效：
- `calculate_vwap_execution_slippage` 在未传 `volatility` 时依然返回相同基点；
- `013841` 的 Beta 返回负数或纯债值（非 1.23 附近）；
- `tests/test_infra.py` 或 `tests/test_adv_final_closure.py` 中有任何用例挂掉；
- 四大裁判文件有任何 Git 变更记录。
