# Forensic Audit Report: Milestone 2 (data_loader.py, strategy_bridge.py, portfolio_manager.py)

**Work Product**: `AGY2_FundAdvisory/data_loader.py`, `AGY2_FundAdvisory/strategy_bridge.py`, `AGY2_FundAdvisory/portfolio_manager.py`  
**Profile**: General Project (Integrity mode: development)  
**Verdict**: **CLEAN**

---

## 1. Observation (客观事实与直接观测数据)

### 1.1 物理安全基石不变量检验 (Referee Files Untouched Check)
执行 `git diff` 与 `git hash-object` 对比 HEAD 树中的 4 个只读裁判基建文件：
- `git diff AGY2_FundAdvisory/judge_engine.py AGY2_FundAdvisory/holdout_vault.py AGY2_FundAdvisory/AGENT_SPEC.md AGY2_FundAdvisory/tests/test_infra.py` 输出完全为空。
- 磁盘实际文件 Blob Hash 与 `git ls-tree HEAD` 记录的 SHA-1 哈希值 100% 逐字节对齐：
  - `AGY2_FundAdvisory/AGENT_SPEC.md`: `ba58630d67dd77f6da7ee5e7eb5b77a968a96683` (Match)
  - `AGY2_FundAdvisory/holdout_vault.py`: `b96d5791f0eb320b1e9332adf8bc2c07e546f663` (Match)
  - `AGY2_FundAdvisory/judge_engine.py`: `fbdfa8eeb2e38f1f2969c08eea9da32e0efee0fd` (Match)
  - `AGY2_FundAdvisory/tests/test_infra.py`: `d67a32294ed4e11250c759ea6db0b2cf0733e86d` (Match)

### 1.2 源码防作弊与前瞻偏差 (Look-Ahead Bias) 审计
- **`data_loader.py` (Line 435-484)**:
  `DataLoader.compute_ewma_volatility_and_correlation(df, window=60, span=60, asset_cols=None)`：
  截取历史切片 `sub_df = df[cols].tail(window)`，计算 `ret_df = sub_df.pct_change().dropna()`，通过 `ret_df.ewm(span=span, adjust=True).var().iloc[-1]` 和 `np.sqrt(ewma_var * 252.0)` 计算年化波动率与相关性矩阵。所有输入严格限定在 $t \le T$ 的历史窗口，不访问未来数据，零日历硬编码。
- **`strategy_bridge.py` (Line 134-146, 3317-3640)**:
  `FUND_TO_PROXY_INDEX` 建立基金与全收益代理指数基准对齐字典。`compute_dynamic_tier_weights` 接入 60 日滚动 EWMA 波动率，对权益资产执行 `scaling = min(1.0, 0.18 / max(vol, 0.08))` 波动率倒数加权，溢出风险预算 100% 转移至低波纯债压舱石 `002351` / `000086`，并在各类行情状态下严格守护 C1–C5 风险单调性与深度熊市破位态止损约束（`Equity(C4) <= 55%, Equity(C5) <= 70%`）。
- **`portfolio_manager.py` (Line 4648-4768, 4833-4860, 4883-4886, 5067-5072)**:
  `calculate_rebalance_net_utility`:
  穿透持仓批次 `h_from.batches` 执行真实先进先出 (FIFO) 批次持有天数核算与赎回费率阶梯匹配（`FeeMatrixCalculator.get_redemption_fee_rate`）；前端申购费采用真实费率核算（`FeeMatrixCalculator.calculate_subscription_fee`）；同司基金转换 $\Delta t_{\text{arrive}} = 0 \implies \text{Cost} = 0.0$；跨司赎回转申购国内基金 $\Delta t = 2$、海外 QDII $\Delta t = 4$，按指数年化波动率计提 $\text{Amount} \times \sigma_{\text{index}} \times \sqrt{\Delta t / 250}$ 在途折价；当 $\Delta U \le 0$ 时自动拦截（标记 `🛡️ 摩擦/在途损耗大于预期收益，建议原地持仓不动`），在推演沙盒中归入 `intercepted_routes` 并阻止 `submit_rebalance_orders` 生成实盘报单；在选基评分中对同司标的赋予 +5.0 分便利度红利。所有返回值均由真实公式推导产生，无假桩 (Facade) 或硬编码返回值。

### 1.3 字节码编译与自动化测试执行实测
1. `python -m py_compile data_loader.py strategy_bridge.py portfolio_manager.py`：退出码 0，零语法/编译错误。
2. `python -m pytest tests/test_infra.py -v`：15 项裁判基建与因果探针测试 **全部通过** (7.12s)。
3. `tests/test_m2_r4_r5_optimization.py`：9 项 M2 专属优化测试 **全部通过** (15.03s)。
4. `tests/test_stress_quant_model_challenger.py` + `tests/test_dynamic_risk_and_metrics.py`：29 项极限压力与动态风险测试 **全部通过** (15.29s)。
5. `tests/test_portfolio_manager.py` + `tests/test_strategy_bridge.py`：31 项业务逻辑测试 **全部通过** (38.63s)。
6. `tests/test_trading_clock_fee.py`：10 项交易时钟与费率测试 **全部通过** (0.63s)。
7. `tests/test_adversarial_m1_strategy_bridge.py` + `tests/test_adversarial_m1_stress.py`：213 项对抗压力测试 **全部通过** (9.32s)。
累计 307 项测试 100% 通过，无回归缺陷。

---

## 2. Logic Chain (推导逻辑链)

1. **基石防篡改验证**:
   - 观测到 `judge_engine.py`、`holdout_vault.py`、`AGENT_SPEC.md` 与 `tests/test_infra.py` 的 Git 工作区 diff 为空，且 blob hash 与 `git ls-tree HEAD` 完全一致。
   - 裁判基础设施文件未发生任何修改或解除只读行为，满足 R1 物理安全基石不变量要求。
2. **算法真实性与前瞻偏差排除**:
   - 观测到 `DataLoader.compute_ewma_volatility_and_correlation` 基于输入 DataFrame 的 `.tail(window)` 进行 EWMA 方差与年化波动率计算，数学公式为标准因果滚动算子，无未来函数。
   - 观测到 `StrategyBridge.compute_dynamic_tier_weights` 按照真实 EWMA 波动率倒数缩放各资产权重，并在缩放后将预算准确转移至纯债 `002351`，并经 `equity_bounds` 投影强制约束风险单调性，非硬编码常量。
   - 观测到 `PortfolioManager.calculate_rebalance_net_utility` 穿透了批次持有天数并调用 `FeeMatrixCalculator` 进行真实阶梯费率扣减，在途踏空成本严格根据 $t$ 周期与波动率精算，拦截逻辑与执行报单联动完整，非假桩伪造。
3. **经验证据闭环**:
   - 裁判引擎 `test_infra.py` 中 `test_causal_probe_detects_leakage` 与 `test_judge_engine_detects_calendar_cheating` 均正常执行且验证通过，证实当前代码未触动作弊拦截网。
   - M2 新增测试及全量测试套件 307 项全数通过，无预制结果伪造或假测试自证问题。

---

## 3. Caveats (注意事项与边界考量)

- 本次审计专注于 Milestone 2 所交付的 `data_loader.py`、`strategy_bridge.py` 以及 `portfolio_manager.py` 内部改动，以及与裁判基石文件的物理隔离性。后续 Milestone 3 将涉及 `app_gui.py` 与 CUSUM 变点检测算法，届时需进一步审计前端组件与白盒面板数据流。
- `portfolio_ledger.json` 作为运行期账本文件，在自动化测试执行过程中会被测试用例加载并重写，此属测试执行预期行为，不属于代码篡改。

---

## 4. Conclusion (审计裁决结论)

**VERDICT: CLEAN (审计合格)**

Milestone 2 提交的 `data_loader.py`、`strategy_bridge.py` 和 `portfolio_manager.py` 严格遵循了 100% 纯数学因果演绎（No Look-Ahead Bias）准则，未引入任何外部大模型 API，未触碰 4 个只读裁判基建文件，未植入任何日历硬编码作弊或假桩门面，EWMA 波动率与调仓净效用精算逻辑真实有效，全量自动化测试套件通过率 100%。

---

## 5. Verification Method (独立复验命令)

```powershell
cd d:\Google\Workspace\Wind\AGY2_FundAdvisory
$env:PYTHONPATH="d:\Google\Workspace\Wind\AGY2_FundAdvisory;d:\Google\Workspace\Wind"

# 1. 验证 4 大裁判基建文件 Hash 未被篡改
git diff judge_engine.py holdout_vault.py AGENT_SPEC.md tests/test_infra.py

# 2. 验证 Python 字节码编译无误
python -m py_compile data_loader.py strategy_bridge.py portfolio_manager.py

# 3. 运行裁判基建与因果探针测试 (15 项)
python -m pytest tests/test_infra.py -v

# 4. 运行 Milestone 2 核心算子优化测试套件 (9 项)
python -m pytest tests/test_m2_r4_r5_optimization.py -v

# 5. 运行全套压力与动态风险回归测试套件 (29 项)
python -m pytest tests/test_stress_quant_model_challenger.py tests/test_dynamic_risk_and_metrics.py -v
```
