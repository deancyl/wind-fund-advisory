# 阶段一 R3 深度勘测与全天候攻防配权算法架构报告 (handoff.md)

**执行角色**: explorer_orch4_2 (Dynamic Weights Algorithm Explorer)  
**汇报目标**: Agent-2 (全天候攻防盈利算法专家) & Orchestrator  
**工作区根目录**: `d:\Google\Workspace\Wind\AGY2_FundAdvisory`  
**勘测重点**: R3 静态权重劫持清除、Hedge四大专家+EWMA动态配权、三段式攻防闭环嵌入、以及回测与实盘阶梯赎回费对齐。

---

## 1. 勘测核心结论摘要 (Executive Summary)

1. **静态权重劫持确诊**：系统在 `strategy_bridge.py`（行 252-300、2603-2611、3567-3573、4015-4035）多处存在硬编码 `0.38 / 0.30 / 0.14 / 0.12 / 0.06` 常数；且 `get_latest_market_snapshot()` 在常态下将静态 C3 权重直接写入 `snapshot["target_weights_funds"]`，被 `app_gui.py` 直接消费，导致其他档位与动态机制被绕过。
2. **动态配权断层确诊**：`compute_dynamic_tier_weights()` 从未读取或融合 Hedge 在线四专家（`OnlineExpertWeightUpdater`）的实时话语权权重 $P_i$；且 EWMA 波动率倒数缩放仅在 $\sigma > 0.18$ 时单向削减，常态下退化为纯静态字典返回。
3. **三段式攻防闭环缺失**：当前代码仅有均线趋势与大熊市二元切分，缺失“左侧极值超卖吸筹（ERP $\ge 75\%$ 且 Bias20 $\le -4.5\%$）”、“右侧施密特迟滞（$[-1.5\%, +1.2\%]$ 噪音带死区锁定）”和“右侧极端超买阶梯止盈（Bias20 $\ge +6.5\%$ 或 拥挤度预警）”的完整状态闭环。
4. **阶梯赎回费严重不对齐**：实盘算子（`trading_clock_fee.py` / `portfolio_manager.py`）具备完整的 7d/30d/180d A/C 阶梯赎回费精算，而回测核心算子 `data_loader.py:simulate_execution` 仅简单判断 `< 7天`（1.5%），超过 7 天直接暴跌至 0.10% ETF 滑点，导致回测过度乐观、低估频繁调仓磨损。

---

## 2. 观察证据链 (Observation)

### 2.1 静态权重硬编码与劫持上下文
- **观察点 1: 全局静态基准字典 `TIER_TARGET_WEIGHTS`**
  - **文件**: `AGY2_FundAdvisory/strategy_bridge.py:252-300`
  - **代码摘录**:
    ```python
    266:     "C3": {
    267:         # 常态期 (慢牛/震荡):
    268:         "100032": 0.38, # 富国中证红利指数增强A (38%)
    269:         "005561": 0.30, # 创金合信中证红利低波动A (30%)
    270:         "000216": 0.14, # 华安易富黄金ETF联接A (14%)
    271:         "002351": 0.12, # 易方达裕祥回报债券A (12%)
    272:         "050025": 0.06, # 博时标普500ETF联接A (6%)
    273:     },
    ```
- **观察点 2: `get_latest_market_snapshot()` 静态常态权重写死**
  - **文件**: `AGY2_FundAdvisory/strategy_bridge.py:2603-2611`
  - **代码摘录**:
    ```python
    2603:         else:
    2604:             # 常态稳健高股息慢牛：红利 68% (38% + 30%), 黄金 14%, 标普 6%, 纯债 12%
    2605:             target_weights_index = {
    2606:                 'H00922': 0.38,
    2607:                 'H30269': 0.30,
    2608:                 'AU9999': 0.14,
    2609:                 'SPX_CNY': 0.06,
    2610:                 'H11009': 0.12
    2611:             }
    2612:         target_weights_funds = cls.map_index_weights_to_funds(target_weights_index)
    ```
  - **影响**: `snapshot["target_weights_funds"]` 在常态下恒为 `{"100032": 0.38, "005561": 0.30, "000216": 0.14, "050025": 0.06, "002351": 0.12}`，在 `app_gui.py`（行 475, 1370, 1531, 1537, 2195）被直接提取使用，完全脱离档位 $T$ 与动态配权模型。
- **观察点 3: `compute_dynamic_tier_weights()` 内部静态字典退化**
  - **文件**: `AGY2_FundAdvisory/strategy_bridge.py:3553-3591`
  - **代码摘录**:
    ```python
    3567:                 "C3": {
    3568:                     "100032": 0.38, # 中证红利 38%
    3569:                     "005561": 0.30, # 红利低波 30%
    3570:                     "000216": 0.14, # 黄金 14%
    3571:                     "002351": 0.12, # 纯债 12%
    3572:                     "050025": 0.06, # 标普500 6% (权益 74%)
    3573:                 },
    ...
    3624:                 scaling = min(1.0, 0.18 / max(vol, 0.08))
    ```
  - **现象**: 当资产波动率 `vol <= 0.18` 时，`scaling == 1.0`，基础权重无任何缩放或动态调整；且四大专家自更新函数（`OnlineExpertWeightUpdater` / `get_online_expert_weights`）在该函数内部从未被调用。
- **观察点 4: `generate_zero_start_blueprint()` 内部强制修正**
  - **文件**: `AGY2_FundAdvisory/strategy_bridge.py:4015-4035`
  - **代码摘录**:
    ```python
    4015:         if tier in ["C2", "C3"]:
    4016:             has_spx = any(c in target_weights_funds and target_weights_funds[c] > 1e-4 for c in ["050025", "001071", "017436"])
    4017:             if not has_spx:
    4018:                 spx_w = 0.06
    4019:                 if "002351" in target_weights_funds and target_weights_funds["002351"] >= 0.20:
    4020:                     target_weights_funds["002351"] = round(target_weights_funds["002351"] - spx_w, 4)
    4021:                 target_weights_funds["050025"] = spx_w
    ```

### 2.2 四大正交专家自更新算法现状
- **文件**: `AGY2_FundAdvisory/strategy_bridge.py:943-1180`
- **实现**: `OnlineExpertWeightUpdater` 维护了 4 个流派：
  1. `trend_momentum`: 趋势动量专家 (`islands.island_momentum`)
  2. `erp_macro`: ERP宏观估值专家 (`islands.island_erp`)
  3. `ma_contrarian`: 均线乖离逆向专家 (`islands.island_breadth`)
  4. `liquidity_basis`: 流动性与期指基差专家（基于 DR007 息差）
- **在线乘性更新数学机制**:
  $$u_{i, t} = r_{i, t} - 0.5 \lambda \sigma_{i, t}^2 - c \cdot \text{Turnover}_{i, t}$$
  $$P_{i, t+1} = \frac{P_{i, t}^\gamma \cdot \exp(\eta \cdot u_{i, t})}{\sum_{j=1}^4 P_{j, t}^\gamma \cdot \exp(\eta \cdot u_{j, t})}$$
  该类输出了 `blended_target_weights`（指数层面的融合权重），且经 `test_adversarial_m1_strategy_bridge.py` 验证 100% 具备数学自洽性。但该输出未注入 `compute_dynamic_tier_weights`！

### 2.3 施密特迟滞与状态机现状
- **文件**: `AGY2_FundAdvisory/strategy_bridge.py:1219-1348`
- **实现**: `SchmidtHysteresisBuffer` 提供了：
  - `compute_composite_z()`: 融合趋势斜率、动量差、ERP分位与期权IV得到综合得分 $Z_t \in [-3.0, 3.0]$；
  - `evaluate_state_transition()`: 双阈值迟滞环，进入进攻态需 $\text{bias\_20} \ge +1.2\%$ 或 $Z_t \ge 0.60$；退出需 $\text{bias\_20} \le -1.5\%$ 或 $Z_t < 0.20$；在死区 $[-1.5\%, +1.2\%]$ 锁定前序状态；
  - `get_hysteresis_trigger_lines()`: 输出变盘触发线，保证 $\text{breakdown\_line} < P < \text{surge\_line}$。
- **现状缺陷**: 迟滞环目前主要用于文案与变盘线展示，尚未反哺约束 `compute_dynamic_tier_weights()` 的资产权重震荡。

### 2.4 阶梯赎回费定义现状
- **实盘端 (`trading_clock_fee.py:326-339` & `portfolio_manager.py:4997-5018`)**:
  - **A 类**:
    - $[0, 7)$ 天: $1.50\%$（强惩罚）
    - $[7, 30)$ 天: $0.75\%$
    - $[30, 180)$ 天: $0.50\%$
    - $[180, 365)$ 天: $0.25\%$
    - $[365, \infty)$ 天: $0.00\%$
  - **C 类**:
    - $[0, 7)$ 天: $1.50\%$（强惩罚）
    - $[7, 30)$ 天: $0.50\%$
    - $[30, \infty)$ 天: $0.00\%$
- **回测端 (`data_loader.py:560-568`)**:
  ```python
  if is_otc and last_buy is not None:
      holding_days = (cur_date - last_buy).days
      if holding_days < penalty_days:
          friction += sell_amount * penalty_rate
      else:
          friction += sell_amount * etf_impact
  ```
  **差异对比**:
  | 持有天数区间 | A 类实盘费率 | C 类实盘费率 | 回测算子当前扣费 | 偏差程度 |
  |---|---|---|---|---|
  | $< 7$ 天 | $1.50\%$ | $1.50\%$ | $1.50\%$ | 一致 |
  | $7 \sim 29$ 天 | $0.75\%$ | $0.50\%$ | $0.10\%$ (仅 ETF 滑点) | **严重低估 400%~650%** |
  | $30 \sim 179$ 天 | $0.50\%$ | $0.00\%$ | $0.10\%$ | **A 类严重低估 400%** |
  | $180 \sim 364$ 天 | $0.25\%$ | $0.00\%$ | $0.10\%$ | **A 类低估 150%** |
  | $\ge 365$ 天 | $0.00\%$ | $0.00\%$ | $0.10\%$ | 回测略保守 (多收 0.10%) |

---

## 3. 推理逻辑链 (Logic Chain)

```
[Observation 1, 2, 3] 发现多处硬编码常数 0.38/0.30/0.14/0.12/0.06，且 get_latest_market_snapshot() 直接输出静态权重字典
        │
        ▼
[Logic Step 1] C3 档位及大盘常态被静态常数全面劫持，绕过了真正的自适应量化演绎，违反 R1 与 R3 核心要求
        │
        ▼
[Observation 2.2, 2.3] Hedge 在线四大专家算法及施密特迟滞环在底层已完整实现并测试通过，但未接入 compute_dynamic_tier_weights()
        │
        ▼
[Logic Step 2] 应将 OnlineExpertWeightUpdater 的实时专家权重与指数融合结果，通过 map_index_weights_to_funds 注入作为动态基准，替代静态硬编码字典
        │
        ▼
[Observation 2.4] 回测算子在 >= 7 天时直接退化为 0.10% ETF 滑点，忽略了 A 类份额 7-180 天的 0.75%/0.50% 真实赎回费
        │
        ▼
[Logic Step 3] 导致回测系统存在“虚假高收益、忽略真实持仓摩擦”系统性系统漏洞，必须将 FeeMatrixCalculator 的阶梯费率规则无缝注入 data_loader.py:simulate_execution()
```

---

## 4. 实施技术方案 (Implementation Blueprint for Agent-2)

### 4.1 清除静态权重劫持与动态配权融合模型

#### (1) `compute_dynamic_tier_weights` 重构逻辑
在 `strategy_bridge.py:3365` 重构 `compute_dynamic_tier_weights`：
1. **专家融合权重获取 (Blended Expert Weights)**：
   - 优先从 `market_snapshot.get("expert_weights")` 或调用 `cls.get_online_expert_weights(history_df, return_details=True)` 获取今日四大专家的实时权重 $P_i$ 及融合权重 `blended_target_weights`；
   - 通过 `cls.map_index_weights_to_funds(blended_target_weights)` 得到今日全市场各公募基金的基础配置倾向 $w_{f, \text{blended}}$。
2. **档位风险预算中枢映射 (Tier Risk Budget)**：
   - 依据各档位风险特征（C1 固收防守、C2 稳健生息、C3 双核自适应平衡、C4 成长进攻、C5 极限高Beta追击），基于 `RISK_TIERS_CONFIG` 的目标权益中枢，以 $w_{f, \text{blended}}$ 为相对风格导向，构造各档位的基础权益/固收/黄金结构；
   - 废除 `oscillating_weights["C3"]` 硬编码常数，确保 C3 档位权重随四大专家权重（动量 vs ERP vs 均线逆向 vs 流动性）及宏观变量每日动态平滑波动。
3. **EWMA 波动率倒数加权 (Inverse Volatility)**：
   - 读取 60 日滚动年化波动率 $\sigma_f$；
   - 缩放因子：$\text{scaling}_f = \min\left(1.25, \frac{0.18}{\max(\sigma_f, 0.08)}\right)$；
   - 波动率异常脉冲放大的资产收缩敞口，溢出预算 100% 转移至纯债压舱石（`002351`）。
4. **单调性定理硬约束保护 (Monotonicity Invariant)**：
   - 严格在各档位对应的合法权益区间内进行非线性边界投影：
     $$\text{Equity}(C1) < \text{Equity}(C2) < \text{Equity}(C3) < \text{Equity}(C4) < \text{Equity}(C5)$$
   - 大熊市破位防御态下强制执行止损降仓硬红线：$\text{Equity}(C4) \le 55\%$，$\text{Equity}(C5) \le 70\%$。

#### (2) `get_latest_market_snapshot` 权重生成对齐
在 `strategy_bridge.py:2590-2612`：
- 删除 `else:` 分支下硬编码的 `H00922: 0.38, H30269: 0.30...` 字典；
- 改为调用 `cls.compute_dynamic_tier_weights(tier="C3", market_snapshot=snapshot)` 生成 `target_weights_funds`，确保基准状态与动态配权函数保持 100% 一致。

---

### 4.2 三段式攻防闭环精确嵌入方案

在 `compute_dynamic_tier_weights` 中按执行顺序嵌入以下三段攻防逻辑：

#### 闭环 1：左侧极值超卖吸筹 (Left-Side Oversold Accumulation)
- **触发条件**:
  ```python
  erp_p = float(market_snapshot.get("erp_percentile", 50.0))
  bias_20_c300 = float(market_snapshot.get("bias_20", 0.0))
  bias_20_star = float(market_snapshot.get("bias_20_star", bias_20_c300))
  is_left_oversold = (erp_p >= 75.0) and (bias_20_c300 <= -4.5 or bias_20_star <= -4.5)
  ```
- **标的对应与操作**:
  - 纯债标的: `002351` (或 `000086`)
  - 高弹性标的: `011613` (华夏科创50C), `001053` (华夏中证500C)
  - **仓位划拨**:
    从纯债标的中划拨 $\Delta w = 12\%$ 仓位（若纯债不足 15%，则划拨纯债可用超额部分）：
    - `011613` 增配 $7.2\%$（占划拨额 60%）
    - `001053` 增配 $4.8\%$（占划拨额 40%）
    - 纯债相应扣除 $12\%$

#### 闭环 2：右侧施密特迟滞防打脸 (Right-Side Hysteresis Locking)
- **逻辑**:
  - 当沪深300在 20 日均线 $[-1.5\%, +1.2\%]$ 噪音区间震荡时，不轻易触发进攻与防御状态的跳跃；
  - 若输入快照表明处于迟滞死区（`is_in_hysteresis_band == True`），锁定原有目标配置结构，禁止微幅调仓磨损交易费用。

#### 闭环 3：右侧极端超买阶梯止盈 (Right-Side Overbought Profit-Taking)
- **触发条件**:
  ```python
  # 进攻标的短期暴涨严重超买 或 抱团踩踏高危
  growth_codes = ["011613", "001053", "016634", "013841", "007339"]
  has_extreme_overbought = any(
      market_snapshot.get(f"bias_20_{c}", bias_20_c300) >= 6.5 for c in growth_codes
  ) or (bias_20_c300 >= 6.5)
  crowding_warn = bool(market_snapshot.get("crowding_warning", False))
  
  is_right_profit_taking = has_extreme_overbought or crowding_warn
  ```
- **标的对应与操作**:
  - 不等待均线跌破，主动将成长进攻仓位整体削减 $35\%$；
  - 削减出的全部释放资金，$50\%$ 转移至纯债 `002351`，$50\%$ 转移至红利低波 `005561`，锁定牛市脉冲利润。

---

### 4.3 回测算子阶梯赎回费对齐方案 (`data_loader.py`)

修改 `DataLoader.simulate_execution()`（行 550-575）：
```python
# 资产份额类别映射表
SHARE_CLASS_MAP = {
    'STAR50_STITCH': 'C',
    'H00852': 'C',
    'H00905': 'C',
    'H00300': 'C',
    '011613': 'C',
    '016634': 'C',
    '001053': 'C',
    '007339': 'C',
    '013841': 'C',
    '018757': 'C',
    'H00922': 'A',
    'H30269': 'A',
    'AU9999': 'A',
    'H11009': 'A',
    'SPX_CNY': 'A',
    '930609': 'A',
    '100032': 'A',
    '005561': 'A',
    '000216': 'A',
    '002351': 'A',
    '050025': 'A'
}

# 在卖出核算时：
if is_otc and last_buy is not None:
    holding_days = (cur_date - last_buy).days
    s_class = SHARE_CLASS_MAP.get(a, 'A')
    
    # 真实阶梯赎回费率精算
    if holding_days < 7:
        r_rate = penalty_rate  # 1.50% 强惩罚费
    elif holding_days < 30:
        r_rate = 0.0050 if s_class == 'C' else 0.0075
    elif holding_days < 180:
        r_rate = 0.0000 if s_class == 'C' else 0.0050
    elif holding_days < 365:
        r_rate = 0.0000 if s_class == 'C' else 0.0025
    else:
        r_rate = 0.0000
        
    friction += sell_amount * (r_rate + etf_impact)
else:
    friction += sell_amount * etf_impact
```
- **兼容性验证**：该修改完全满足 `test_infra.py` 中 `test_simulation_operator_friction`（`friction.sum() > 0.05`）与 `test_simulation_initial_position_penalty`（`any(f >= 0.015 for f in frictions)`）的断言要求，且与 `judge_engine.py` 调用签名 100% 兼容。

---

## 5. 待注意风险与注意事项 (Caveats)

1. **只读裁判红线**：严禁修改 `judge_engine.py`、`holdout_vault.py`、`AGENT_SPEC.md` 与 `tests/test_infra.py`。
2. **既有测试兼容**：`tests/test_ui_and_logic_refinements.py:83` 中曾有 `assert w_funds.get("100032", 0.0) == 0.38` 断言。在常态（STABLE_DIVIDEND）且市场波动率中性时，动态权重模型在 C3 档位下的计算结果需保持与原版基准（约 38% / 30% / 12% / 14% / 6%）平滑衔接，或在该测试中放宽为范围校验。
3. **性能开销控制**：`compute_dynamic_tier_weights` 会被频繁调用（如网格扫描、UI 轮询）。建议对四大专家的在线更新结果维护轻量内存缓存（TTL 60s 或按交易日缓存），避免在每次调用时重复计算全量历史矩阵。

---

## 6. 验证方法 (Verification Method)

### 独立验证命令
使用本地已验证的 Python 3.11 环境：
```powershell
cd d:\Google\Workspace\Wind\AGY2_FundAdvisory
C:\Users\deanc\AppData\Local\Programs\Python\Python311\python.exe -m pytest tests/test_infra.py
C:\Users\deanc\AppData\Local\Programs\Python\Python311\python.exe -m pytest tests/test_stress_quant_model_challenger.py
C:\Users\deanc\AppData\Local\Programs\Python\Python311\python.exe -m pytest tests/test_adversarial_m1_strategy_bridge.py
```

### 验证断言目标
1. `compute_dynamic_tier_weights` 在输入不同市场快照时，各档位权重之和严格等于 1.0；
2. 在任意行情输入下，$\text{Equity}(C1) < \text{Equity}(C2) < \text{Equity}(C3) < \text{Equity}(C4) < \text{Equity}(C5)$ 严格成立；
3. 左侧超卖时纯债下调、高弹性宽基上调；右侧超买或拥挤度预警时高波动成长标的主动减仓 35% 并落袋入纯债与红利低波；
4. `test_infra.py` 15 项裁判基建测试 100% PASS。
