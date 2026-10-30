# Reviewer 2 (Milestone 2) Handoff Report

## 1. Observation (客观事实与观测数据)

### 1.1 代码变更审查 (Target Files)
- **`AGY2_FundAdvisory/data_loader.py`**:
  - 在第 435–484 行实现静态算子 `DataLoader.compute_ewma_volatility_and_correlation(df, window=60, span=60, asset_cols=None) -> Tuple[pd.Series, pd.DataFrame]`。
  - 使用 `ret_df = sub_df.pct_change().dropna()` 计算日度收益率，`ret_df.ewm(span=span, adjust=True).var().iloc[-1]` 计算 EWMA 方差，配合 `ewma_var.clip(lower=1e-8)` 避免数值下溢或零除错误，以 $\sqrt{\sigma^2 \times 252}$ 输出年化波动率。相关性矩阵使用 `ret_df.corr().fillna(0.0)`。
  - 针对 `df is None`、长度 `< 10` 或有效收益率 `< 5` 提供了先验波动率平滑兜底（纯债 3.5%、红利 14%、黄金 13%、宽基 18%），相关性矩阵退化为单位阵 `np.eye`。
- **`AGY2_FundAdvisory/strategy_bridge.py`**:
  - 在第 134–146 行新增基金代码与全收益代理指数映射表 `FUND_TO_PROXY_INDEX`，并在全局设置 `_CACHED_EWMA_VOLS` 与 `_CACHED_CORR_MAT` 加速重复运算。
  - 在第 3562–3650 行 `compute_dynamic_tier_weights` 中：
    - 波动率倒数缩放因子公式为 `scaling = min(1.0, 0.18 / max(vol, 0.08))`，通过分母下限 `0.08` 杜绝零除风险，通过 `min(1.0, ...)` 杜绝低波盲目放大杠杆。
    - 将权益缩放扣减的预算 `trimmed_budget` 100% 转移至低波纯债压舱石（`002351` 或 `000086`）。
    - 设立分市场环境（BULL、OSCILLATING、BEAR）严格互斥的权益区间约束 `equity_bounds`，若总权益超出区间则按比例缩放并将差额补入/扣减纯债，严格守护 C1–C5 风险单调性与深度熊市止损硬边界（$Equity(C4) \le 55\%, Equity(C5) \le 70\%$）。
- **`AGY2_FundAdvisory/portfolio_manager.py`**:
  - 在第 4648–4768 行实现核心算子 `calculate_rebalance_net_utility(from_fund_code, to_fund_code, amount, expected_alpha_20d=None, market_snapshot=None) -> Dict[str, Any]`：
    - 净效用公式严格遵循：$\Delta U = \text{ExpectedAlphaGain}_{20d} - \text{ExactRedemptionFee(FIFO)} - \text{SubscriptionFee} - \text{InTransitOpportunityCost}(\Delta t, \sigma_{\text{index}})$。
    - 同公司 T+1 SWITCH 判定：当两基金所属公司一致时，$\Delta t_{\text{arrive}} = 0 \implies \text{InTransitOpportunityCost} = 0.0$。
    - 跨公司国内基金 $\Delta t_{\text{arrive}} = 2$，QDII/海外基金 $\Delta t_{\text{arrive}} = 4$，按当前市场指数年化波动率计算在途风险折价：$\text{Amount} \times \sigma_{\text{index}} \times \sqrt{\Delta t / 250}$。
    - 赎回费调用 `FeeMatrixCalculator` 穿透 FIFO 持仓批次，严格计提 7 天惩罚费（1.50%）及 A/C 份额梯度费率。
    - 判定 $\Delta U \le 0$ 时输出徽章 `"🛡️ 摩擦/在途损耗大于预期收益，建议原地持仓不动"`，且 `should_intercept = True`。
  - 在第 4923–4948 行（Priority 1 同司转换）与第 4995–5035 行（Priority 3 跨司两阶段分步换仓）全面集成净效用核算，将换仓路由拆分为 `executable_routes` 与 `intercepted_routes`。
  - 在第 5250–5252 行 `submit_rebalance_orders` 中，显式加入防御屏障：`if r.get("should_intercept", False): continue`，彻底阻断劣质调仓进入实际挂单。
  - 在第 3768–3786 行 `_do_compute_six_dimension_score` 中，动态扫描用户已有持仓公司集合，若候选基金属同司则额外奖励 +5.0 分的“同司极速转换便利性红利”（封顶 100.0 分）。

### 1.2 裁判基础设施文件物理红线检查
- `judge_engine.py`、`holdout_vault.py`、`AGENT_SPEC.md`、`tests/test_infra.py` 四大基础设施文件通过 `git status` 确认未被修改（UNTOUCHED）。

### 1.3 独立测试运行与观测结果
1. **指令 1 (专项测试与挑战者测试)**:
   ```powershell
   python -m pytest tests/test_m2_r4_r5_optimization.py tests/test_stress_quant_model_challenger.py tests/test_dynamic_risk_and_metrics.py -v
   ```
   - 结果：**38 passed, 40 warnings in 24.75s**。
2. **指令 2 (全套既有与回归测试)**:
   ```powershell
   python -m pytest tests/test_trading_clock_fee.py tests/test_portfolio_manager.py tests/test_infra.py tests/test_strategy_bridge.py -v
   ```
   - 结果：**56 passed, 84 warnings in 46.83s**。
3. **指令 3 (M2 红队对抗挑战者测试)**:
   ```powershell
   python -m pytest tests/test_adversarial_m2_challenger.py tests/test_adversarial_m2_challenger2.py -v
   ```
   - 结果：**24 passed, 179 warnings in 56.74s**。
4. **指令 4 (极端随机扰动与单调性压力测试)**:
   - 编写对抗脚本测试 100 组随机行情网格（指数 2000~6000 点，各周期均线上下扰动 $\pm 20\%$，波动率 0.001~1.5，包含常数序列、缺失 NaN 序列、极值序列）：
   - 结果：全部 100 组测试均满足 $Equity(C1) < Equity(C2) < Equity(C3) < Equity(C4) < Equity(C5)$，权重和严格为 1.0000。

---

## 2. Logic Chain (推理与推导逻辑链)

1. **R4 数学严密性与数值稳定性**:
   - 波动率倒数权重调整：基于金融学 Risk Parity 思想，高波收缩敞口、低波保持配置。通过 `min(1.0, 0.18 / max(vol, 0.08))` 确保缩放因子 $0.0 < \text{scaling} \le 1.0$。分母下界 0.08 有效防御了极低波动（或常数价格）时的除零发散；`min(1.0, ...)` 防御了顺周期加杠杆爆仓风险。
   - 纯债压舱石机制：扣减的风险预算 100% 转移至纯债 `002351` / `000086`，保证资产配置总权重恒等于 1.0000，不会发生无风险敞口漂移。
   - 严格分层非重叠投影区间：
     - BULL 区间：C1 [0.18, 0.22] < C2 [0.45, 0.55] < C3 [0.68, 0.76] < C4 [0.80, 0.84] < C5 [0.88, 0.94]
     - OSCILLATING 区间：C1 [0.18, 0.22] < C2 [0.45, 0.53] < C3 [0.65, 0.75] < C4 [0.77, 0.82] < C5 [0.86, 0.92]
     - BEAR 区间：C1 [0.08, 0.12] < C2 [0.20, 0.28] < C3 [0.30, 0.38] < C4 [0.45, 0.53] < C5 [0.60, 0.68]
     各层级间存在严格正的间隙（至少 200 bps），即使经过单资产波动率倒数收缩与浮点舍入，投影后依然在数学上绝对杜绝了 C1–C5 档位倒挂。同时在熊市中，C4 权益上限 53% 严格满足 $\le 55\%$，C5 权益上限 68% 严格满足 $\le 70\%$，实现了算法级硬止损。

2. **R5 调仓摩擦拦截与在途成本因果演绎**:
   - 真实摩擦成本包含直接费用（赎回费 + 申购费）与在途踏空风险折价。
   - 同司基金转换在基金公司内部份额系统封闭运行，交收无时滞（T+1 确认，在途时差 $\Delta t = 0$），故在途风险折价为 0.0。
   - 跨司换仓存在赎回款跨行交收与再申购资金时差（A股基金 2 天，跨境 QDII 4 天），其间面临标的指数随机扩散波动，通过 $\text{Amount} \times \sigma_{\text{index}} \times \sqrt{\Delta t / 250}$ 量化在途风险敞口符合标准随机漫步模型，避免了传统模型忽略在途踏空导致的实盘亏损。
   - 当 20 日预期 Alpha 收益不足以覆盖全部摩擦损耗时，$\Delta U \le 0$。双轨拦截机制生效：在沙盒规划阶段剥离至 `intercepted_routes` 并打上醒目标记，在报单执行阶段直接拒绝提交 `pending_orders`，形成了端到端闭环防护。
   - 同司转换便利度 +5.0 分机制在基金评分阶段自然提升同司标的排序，正向激励交易系统撮合同司 T+1 SWITCH，从源头上减少跨司调仓摩擦。

3. **Integrity Mandate 审计**:
   - 源代码中无任何硬编码测试结果、无虚拟桩实现、无绕过逻辑。
   - 4 个裁判基建文件只读属性完好，测试执行均来自真实计算。

---

## 3. Caveats (注意事项与边界考量)

1. **同司转换覆盖范围**:
   - 目前同司转换检测依赖 `resolve_fund_meta` 获取的 `company` 字段一致性。若极少数三方基金元数据中公司名称存在缩写差异（例如“易方达” vs “易方达基金”），系统将退化为跨司处理，计提 2 日在途折价。该退化策略符合风险厌恶原则，不会造成过度乐观低估摩擦。
2. **市场波动率代理选取**:
   - 当外部传入的快照缺失 `c300_annualized_vol` 时，系统自动回退至期权隐含波动率或行业基准值 0.18，保证任何数据缺失情况下不会抛出未捕获异常。

---

## 4. Conclusion (评审裁决)

- **Verdict**: **APPROVE** (通过)。
- Milestone 2（R4 与 R5）各项功能与算法已达到生产级量化标准：
  - R4 滚动 60 日 EWMA 波动率与相关性矩阵算子计算严密，倒数配权和纯债吸收逻辑稳健，C1–C5 全市场状态下单调性定理严格成立。
  - R5 调仓净效用 $\Delta U$、真实 FIFO 阶梯费率、T+1 SWITCH vs 跨司/QDII 在途踏空折价、双层拦截屏障以及同司 +5.0 便利度加分均精确落地。
  - 累计通过 118 项单元、压力与对抗测试，4 个裁判基础设施文件完全未受影响，完全符合所有金融合规与物理安全红线。

---

## 5. Verification Method (独立复现与验证方法)

在工作区目录执行以下指令可完全独立复现本报告结论：

```powershell
cd d:\Google\Workspace\Wind\AGY2_FundAdvisory
$env:PYTHONPATH="d:\Google\Workspace\Wind\AGY2_FundAdvisory;d:\Google\Workspace\Wind"

# 1. 验证 R4 与 R5 专用测试、挑战者测试与动态风险测试 (38 项通过)
python -m pytest tests/test_m2_r4_r5_optimization.py tests/test_stress_quant_model_challenger.py tests/test_dynamic_risk_and_metrics.py -v

# 2. 验证全套业务逻辑、交易时钟、持仓管理与裁判基石测试 (56 项通过)
python -m pytest tests/test_trading_clock_fee.py tests/test_portfolio_manager.py tests/test_infra.py tests/test_strategy_bridge.py -v

# 3. 验证对抗挑战者极限测试 (24 项通过)
python -m pytest tests/test_adversarial_m2_challenger.py tests/test_adversarial_m2_challenger2.py -v

# 4. 验证 4 大裁判基础设施只读红线
git status -s AGY2_FundAdvisory/judge_engine.py AGY2_FundAdvisory/holdout_vault.py AGY2_FundAdvisory/AGENT_SPEC.md AGY2_FundAdvisory/tests/test_infra.py
```
若上述测试中出现任何测试未通过，或 4 大裁判文件状态非 clean，则本裁决自动失效。
