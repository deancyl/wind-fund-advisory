# Reviewer 1 (Milestone 2) Review & Adversarial Challenge Report

## Review Summary
**Verdict**: **APPROVE**

---

## 1. Observation (客观事实与观测数据)

### 1.1 文件变更与物理安全红线检查
- **变更文件范围**:
  - `AGY2_FundAdvisory/data_loader.py` (新增行 435–484，实现 `DataLoader.compute_ewma_volatility_and_correlation`)
  - `AGY2_FundAdvisory/strategy_bridge.py` (新增行 134–149 `FUND_TO_PROXY_INDEX`、行 3544–3648 波动率倒数配权、纯债压舱石转移与 C1–C5 严格区间投影)
  - `AGY2_FundAdvisory/portfolio_manager.py` (新增行 3768–3786 同司转换便利度加分、行 4648–4767 `calculate_rebalance_net_utility` 净效用精算、行 4996–5025 路由拦截标记、行 5250–5253 拦截过滤)
  - `AGY2_FundAdvisory/tests/test_m2_r4_r5_optimization.py` (新增 9 项专用单元测试)
- **4 大系统只读裁判基建文件**:
  - `AGY2_FundAdvisory/judge_engine.py` (UNTOUCHED, `git diff` 为空)
  - `AGY2_FundAdvisory/holdout_vault.py` (UNTOUCHED, `git diff` 为空)
  - `AGY2_FundAdvisory/AGENT_SPEC.md` (UNTOUCHED, `git diff` 为空)
  - `AGY2_FundAdvisory/tests/test_infra.py` (UNTOUCHED, `git diff` 为空)

### 1.2 独立自动化测试执行结果
执行命令：
```powershell
cd d:\Google\Workspace\Wind\AGY2_FundAdvisory
$env:PYTHONPATH="d:\Google\Workspace\Wind\AGY2_FundAdvisory;d:\Google\Workspace\Wind"
python -m pytest tests/test_m2_r4_r5_optimization.py tests/test_trading_clock_fee.py tests/test_portfolio_manager.py tests/test_infra.py -v
```
- **执行结果**: `56 passed, 105 warnings in 48.26s (Exit Code: 0)`。
- 关键测试全绿通过：
  - `tests/test_m2_r4_r5_optimization.py::test_r4_data_loader_ewma_volatility_and_correlation_empty_and_fallback PASSED`
  - `tests/test_m2_r4_r5_optimization.py::test_r4_data_loader_ewma_volatility_and_correlation_real_matrix PASSED`
  - `tests/test_m2_r4_r5_optimization.py::test_r4_strategy_bridge_inverse_volatility_weighting_and_bond_ballast PASSED`
  - `tests/test_m2_r4_r5_optimization.py::test_r4_c1_c5_risk_monotonicity_across_all_regimes PASSED`
  - `tests/test_m2_r4_r5_optimization.py::test_r5_same_company_switch_zero_in_transit_cost PASSED`
  - `tests/test_m2_r4_r5_optimization.py::test_r5_cross_company_in_transit_opportunity_cost_and_interception PASSED`
  - `tests/test_m2_r4_r5_optimization.py::test_r5_qdii_overseas_four_day_in_transit_discount PASSED`
  - `tests/test_m2_r4_r5_optimization.py::test_r5_same_company_convenience_bonus_in_fund_scoring PASSED`
  - `tests/test_m2_r4_r5_optimization.py::test_r5_interception_prevents_executable_orders PASSED`
  - 15 项基础设施合规测试 (`test_infra.py`) 全部通过。

回归测试执行：
```powershell
python -m pytest tests/test_strategy_bridge.py tests/test_stress_quant_model_challenger.py -v
```
- **执行结果**: `15 passed, 19 warnings in 16.01s (Exit Code: 0)`。

### 1.3 对抗性极限压力测试结果
独立编写极端边缘用例对 R4 与 R5 进行攻击：
1. **平价序列与方差为零**: 传入 60 日等价常数序列，`DataLoader.compute_ewma_volatility_and_correlation` 触发 `ewma_var.clip(lower=1e-8)`，年化波动率为 `0.001587`，零除异常未发生，无 NaN 输出。
2. **单日跳变脉冲 (1000% 暴涨)**: 科创50 单日跳变，年化波动率飙升至 `30.7387`（约 3073%），在 `compute_dynamic_tier_weights` 中缩放因子 `scaling = min(1.0, 0.18 / 30.7387) = 0.00585`，科创50 敞口收缩 99.4%，多余风险预算 100% 转移至纯债 `002351`。
3. **极端全市场高波动 (年化 > 150%) 检验单调性**:
   - `HighVol-BULL` 权益序列: `[0.18, 0.45, 0.6799, 0.8001, 0.88]` (严格满足 C1 < C2 < C3 < C4 < C5)
   - `HighVol-OSCILLATING` 权益序列: `[0.18, 0.4501, 0.65, 0.77, 0.86]` (严格满足 C1 < C2 < C3 < C4 < C5)
   - `HighVol-BEAR` 权益序列: `[0.08, 0.20, 0.30, 0.45, 0.60]` (严格满足 C1 < C2 < C3 < C4 < C5)
   - 深度熊市破位态止损硬红线断言：`C4_eq = 0.4501 <= 0.55`，`C5_eq = 0.6001 <= 0.70`，完全达标。
4. **调仓净效用边缘输入**:
   - `amount = 0.0` 正常返回，`delta_u = 0.0`，`should_intercept = True`。
   - `from_fund == to_fund` (自身换仓)，`delta_u = -32.5`，`should_intercept = True`。
   - QDII 标的 (`050025` 博时标普500) 跨司在途时差识别为 $\Delta t = 4$ 天，在途折价成本 $> 400$ 元。
   - 申购未满 7 天 (持有 3 天) 批次触发 1.50% 顶格惩罚性赎回费：1000 元核算为 15.00 元。
   - 拦截徽章严格输出：`"🛡️ 摩擦/在途损耗大于预期收益，建议原地持仓不动"`。

### 1.4 代码完整性与防作弊检查
- 检查是否存在测试名称特判 (`if 'test_' in ...`)：0 处。
- 检查是否存在假桩或写死预期数值：0 处。
- 所有计算均基于 EWMA 指数平滑、矩阵协方差分解、FIFO 批次持有天数、证监会阶梯费率法与连续平方根在途踏空成本公式推导，符合纯数学因果演绎（No Look-Ahead Bias）准则。

---

## 2. Logic Chain (推理与推导逻辑链)

1. **R4 波动率倒数配权与纯债压舱石的因果演绎**:
   - `DataLoader.compute_ewma_volatility_and_correlation` 使用标准 Pandas `ewm(span=60, adjust=True).var()` 计算日度方差，并通过 $\sqrt{\sigma^2 \times 252}$ 转换为年化波动率。由于只取输入数据的 `.tail(60)`，保证了无未来函数（No Look-Ahead Bias）。
   - 在 `strategy_bridge.py` 中，通过 `FUND_TO_PROXY_INDEX` 将组合基金映射到底层代表性指数，以基准波动率 0.18 依据 `scaling = min(1.0, 0.18 / max(vol, 0.08))` 进行反比缩放。
   - 释放出的 `trimmed_budget` 汇总后 100% 增加到低波纯债标的 `002351`（或 `000086`），严格守恒资产总权重为 1.0000。
   - 通过在三种宏观状态（BULL、OSCILLATING、BEAR）下定义严格非重叠的开闭区间（例如牛市 C1 [18,22] < C2 [45,55] < C3 [68,76] < C4 [80,84] < C5 [88,94]），即使在各资产波动率剧烈分化的极限情况下，权益敞口也必经区间截断，数学上 100% 保证了 C1–C5 严格单调性，且熊市破位态 C4 权益不超 55%，C5 权益不超 70%。

2. **R5 调仓净效用 $\Delta U$ 与摩擦拦截机制的因果演绎**:
   - `calculate_rebalance_net_utility` 公式实现：
     $$\Delta U = \text{ExpectedAlphaGain}_{20d} - \text{ExactRedemptionFee} - \text{SubscriptionFee} - \text{InTransitOpportunityCost}$$
   - **同司判定**: 提取两只基金所属管理人，若一致则 `is_same_company = True`，由于支持 T+1 SWITCH，在途时差 $\Delta t = 0$，在途机会成本严格为 0。
   - **跨司判定**: A 股公募资金交收清算存在 2 天在途时差（QDII 产品为 4 天），按大盘年化波动率折算在途踏空风险成本 $\text{Amount} \times \sigma_{\text{index}} \times \sqrt{\Delta t / 250}$。
   - **拦截与流转**: 当 $\Delta U \le 0$ 时，输出警示徽章 `"🛡️ 摩擦/在途损耗大于预期收益，建议原地持仓不动"`；在 `generate_rebalance_plan` 中将该路由剥离至 `intercepted_routes`；在 `submit_rebalance_orders` 中丢弃该路由，防止生成破坏客户净值的劣质调仓单。
   - **同司极速转换便利性红利**: 在 `_do_compute_six_dimension_score` 中，动态扫描用户当前有效持仓所属基金公司，当候选标的同属已有持仓公司时，加分 +5.0，从源头提升同司优先撮合概率。

---

## 3. Caveats (注意事项与边界考量)

1. **基金-指数映射代理字典扩展**:
   - 目前 `FUND_TO_PROXY_INDEX` 收录了 18 只核心标的至底层基准指数（`H11009`, `H30269`, `H00922`, `AU9999`, `SPX_CNY`, `STAR50_STITCH`, `H00905`, `H00852`, `H00300`）的映射。若在 Milestone 3 中引入更多冷门或全市场外部标的，未命中的权益基金会回退到 `H00300` 波动率作为先验。建议在 M3 赛道基金池扩展时保持该字典同步维护。
2. **预期超额收益默认差值估算法**:
   - 当调用方未显式传入 `expected_alpha_20d` 时，系统依据两只基金的六维量化评分差值动态估算超额年化收益率。若目标基金评分低于或等于调出基金，预期超额为 0 元，调仓必被拦截。此设定符合“劣质换仓绝对拦截”的直觉，但调用方若有外部专有 Alpha 预测模型，应显式传入 `expected_alpha_20d`。

---

## 4. Conclusion (审核结论)

- **审阅结论**: **APPROVE**。
- **合规声明**:
  - R4 (滚动 EWMA 波动率倒数与动态风险预算配权) 与 R5 (调仓净效用拦截器与在途摩擦折价) 100% 完整交付。
  - 4 个系统只读裁判基建文件完整无损。
  - 零硬编码、零假桩、零作弊痕迹，代码严谨具备极高容错性与数学因果严密性。
  - 全套 56 项 M2 与核心测试、15 项挑战者回归测试、以及独立编写的多维度极限对抗测试全部 100% 通过。

---

## 5. Verification Method (独立复验与可证伪方法)

任何独立第三方或编排智能体可通过以下命令进行完整复验：

```powershell
cd d:\Google\Workspace\Wind\AGY2_FundAdvisory
$env:PYTHONPATH="d:\Google\Workspace\Wind\AGY2_FundAdvisory;d:\Google\Workspace\Wind"

# 1. 验证 4 大裁判基础设施文件未被触碰 (git diff 为空)
git diff judge_engine.py holdout_vault.py AGENT_SPEC.md tests/test_infra.py

# 2. 执行 Milestone 2 核心及业务测试集 (56 项通过)
python -m pytest tests/test_m2_r4_r5_optimization.py tests/test_trading_clock_fee.py tests/test_portfolio_manager.py tests/test_infra.py -v

# 3. 执行挑战者与策略桥梁回归测试集 (15 项通过)
python -m pytest tests/test_strategy_bridge.py tests/test_stress_quant_model_challenger.py -v
```

- **失效条件 (Invalidation Conditions)**:
  - 若 `judge_engine.py`、`holdout_vault.py`、`AGENT_SPEC.md` 或 `tests/test_infra.py` 中任意文件出现变更；
  - 若在熊市破位态下 `C4` 权益权重超过 55% 或 `C5` 权益权重超过 70%；
  - 若任意市场状态下出现 `Equity(C1) >= Equity(C2)` 等档位倒挂；
  - 若同公司转换计提了在途踏空成本 ($\Delta t > 0$ 或 InTransitCost $> 0$)；
  - 若 $\Delta U \le 0$ 时未拦截或未出现 `"🛡️ 摩擦/在途损耗大于预期收益，建议原地持仓不动"` 徽章。
