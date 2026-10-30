# Empirical Challenge Report — Milestone 1 (M1)

**Challenger**: Challenger 1 (`challenger_m1_1`)  
**Role**: Empirical Challenger (critic, specialist)  
**Date**: 2026-10-30T01:53:00Z  
**Target Milestone**: Milestone 1 (R2 OnlineExpertWeightUpdater & R3 SchmidtHysteresisBuffer in `strategy_bridge.py`)  
**Verdict**: **APPROVE**  

---

## 1. Observation

### 1.1 核心代码审查与实现观察 (`strategy_bridge.py`)
1. **`OnlineExpertWeightUpdater` (Lines 926–1170)**:
   - 流派定义：$K=4$ 个独立正交模型 `["trend_momentum", "erp_macro", "ma_contrarian", "liquidity_basis"]` (L939)。
   - 效用计算：$u_{i, t} = r_{i, t} - 0.5 \lambda \sigma_{i, t}^2 - c \cdot \text{Turnover}_{i, t}$ (L1106)，考虑了收益、方差惩罚与换手摩擦。
   - 乘性更新对数平滑防溢出：
     $$\log P_{i, t+1} \propto \gamma \log P_{i, t} + \eta u_{i, t}$$
     采用减去 $\max_j(\log P_j)$ 后求指数归一化 (L1113–1121)。
   - 严格尾差修正 (L1123–1127)：
     ```python
     rounded_weights = {k: round(v, 4) for k, v in P.items()}
     diff = 1.0 - sum(rounded_weights.values())
     max_k = max(rounded_weights, key=rounded_weights.get)
     rounded_weights[max_k] = round(rounded_weights[max_k] + diff, 4)
     ```
     确保 `sum(rounded_weights.values()) == 1.0000`，误差绝对值严格 $< 10^{-5}$。
   - 异常输入兜底：当 `history_df is None` 或 `len(history_df) < 5` 时，安全降级为等权 `0.25`，避免崩溃。

2. **`SchmidtHysteresisBuffer` (Lines 1202–1331)**:
   - 双阈值施密特非对称迟滞带：
     - 从防守/震荡切换至进攻态：要求 $\text{bias\_20} \ge +1.2\%$ 或 $Z_t \ge +0.60$ (L1258)。
     - 从进攻切换退出至防守态：要求 $\text{bias\_20} \le -1.5\%$ 或 $Z_t < +0.20$ (L1271)。
     - 死区容差范围 $[-1.5\%, +1.2\%]$ 内：锁定前一状态不变 (L1266, L1280)。
   - Sigmoid 连续仓位门控 (L1287–1294)：
     $$g(Z_t) = \frac{1}{1 + \exp(-k \cdot Z_t)}$$
     对 $k \cdot Z_t$ 执行 `np.clip(..., -50.0, 50.0)`，彻底杜绝浮点上溢。
   - 双向变盘触发线 (L1297–1330)：
     - `surge_line = round(max(m20_up, c300_price * 1.012), 1)`，并强制校验 `surge_line > c300_price`。
     - `breakdown_line = round(min(m20_down, c300_price * 0.985), 1)`，并强制校验 `breakdown_line < c300_price`。

3. **`StrategyBridge` 桥接与快照集成 (Lines 1762–1793, 2392, 2512–2519)**:
   - 暴露 `StrategyBridge.get_online_expert_weights()` 接口，返回 `ExpertWeightsDict`。
   - 在 `StrategyBridge.get_latest_market_snapshot()` 中自动注入 `expert_weights`、`expert_details`、`composite_z`、`sigmoid_gate`、`trigger_lines`。

---

### 1.2 实证测试套件设计与执行观察
Challenger 1 自行编写了对抗性严苛实证测试集 `tests/test_adversarial_m1_stress.py`，涵盖以下 6 大类挑战场景：

1. **测试用例集结构 (`tests/test_adversarial_m1_stress.py`)**:
   - `TestOnlineExpertWeightUpdaterNormalization`:
     - 历史全周期全景切片网格测试（切片长度 10 到 1000 天，滚动窗口 10 到 120 天，共 28 种参数组合）：验证 `abs(sum(weights) - 1.0) < 1e-5`。
     - 极值输入安全兜底：空 DataFrame、None、len < 5。
     - 极端合成行情：极牛（每日+3%）、极熊（每日-3%）、高频锯齿（每日±5%）、非核心资产列缺失。
     - 极端超参数组合：$\gamma \in [0.5, 0.999]$, $\eta \in [0.1, 50.0]$。
   - `TestOnlineExpertWeightUpdaterMonotonicity`:
     - 纯数学乘性迭代单调性：30 步递推断言优势专家权重严格单调上升（$P_0: 0.25 \to >0.70$），劣势专家权重严格单调下降（$P_3: 0.25 \to <0.05$）。
     - 受控市场全流程模拟：动量专家标的稳步上涨时，随时间推移其权重单调累积抬升。
   - `TestSchmidtHysteresisBufferNoiseAndStateLock`:
     - 防守态下指数在 $\text{MA20} \pm 0.5\%$ 剧烈反复震荡（如 `[+0.3%, -0.4%, +0.5%, -0.3%, +0.48%, -0.50%]`），断言状态横跳次数为 0 (0 flips)，全程锁定防守态。
     - 进攻态下指数在 $\text{MA20} \pm 0.5\%$ 震荡回踩，断言状态横跳次数为 0 (0 flips)，全程锁定进攻态。
     - 死区边界包络测试：$[-1.49\%, +1.19\%]$ 全测试点零状态泄露。
     - 精确翻转点测试：$\ge +1.20\%$ 突破，$\le -1.50\%$ 破位。
   - `TestSchmidtBreakoutTriggerLinesGrid`:
     - 现价网格 $c300 \in [800, 12000]$ 与均线偏离比率 $m20/c300 \in [0.70, 1.30]$（共 121 个网格点）：断言 `surge_line > c300_price` 且 `breakdown_line < c300_price` 100% 成立。
     - 极端暴涨超买与暴跌超卖缺口自愈保护。
   - `TestSigmoidGatingAndCompositeZ`:
     - Sigmoid 零点 $g(0) = 0.50$，严格单调，$\pm 1000$ 极值防溢出。
     - Composite Z 在 $[-3.0, +3.0]$ 严格截断。
   - `TestStrategyBridgeIntegrationSnapshot`:
     - 市场快照字典字段完整性与契约合规性。

2. **实测执行结果**:
   - 执行命令：
     ```powershell
     $env:PYTHONPATH='d:\Google\Workspace\Wind\AGY2_FundAdvisory;d:\Google\Workspace\Wind'
     python -m pytest tests/test_adversarial_m1_stress.py -v
     ```
     **结果**: `186 passed in 8.18s` (100% 通过)。
   - 全套回归与基建测试命令：
     ```powershell
     python -m pytest tests/test_strategy_bridge.py tests/test_infra.py tests/test_adversarial_m1_stress.py -v
     ```
     **结果**: `210 passed, 2 warnings in 27.58s` (100% 通过)。

3. **物理安全红线与文件隔离观察**:
   - `git status -s` 确认：4 个只读裁判基建文件（`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`）未受任何修改。
   - `.agents/teamwork/` 目录下仅包含元数据文档，无源代码或数据泄露。

---

## 2. Logic Chain

1. **归一化与概率公理有效性 (Based on Obs 1.1 & 1.2)**:
   - 在历史不同市场周期（牛市、熊市、震荡市、切片长度 10~1000 天）以及合成极端行情下，`OnlineExpertWeightUpdater.compute_expert_weights()` 输出的四大专家权重经尾差调整后，和严格恒等于 1.0000（误差绝对值 $< 10^{-5}$），且每个权重严格处于 $[0.0, 1.0]$，满足概率分布公理。
2. **净效用驱动单调性确立 (Based on Obs 1.1 & 1.2)**:
   - 乘性更新公式 $P_{i, t+1} \propto P_{i, t}^\gamma \exp(\eta u_{i, t})$ 在对数空间呈现凸组合与增量累加特性：$\log(P_{i, t+1}/P_{j, t+1}) = \gamma \log(P_{i, t}/P_{j, t}) + \eta(u_{i, t} - u_{j, t})$。在 30 步递推与连续市场模拟中，只要专家维持相对净效用优势，其权重序列严格单调递增，无振荡钝化现象。
3. **施密特迟滞缓冲环防打脸有效性 (Based on Obs 1.1 & 1.2)**:
   - 在构造的 $\text{MA20} \pm 0.5\%$ 高频震荡序列下，迟滞状态机准确识别进入区与退出区的非对称性。在防守态下，未达 $+1.2\%$ 突破上轨（或 $Z < 0.60$）绝不触发进攻；在进攻态下，未达 $-1.5\%$ 跌破下轨（或 $Z \ge 0.20$）绝不退出进攻。全程 0 次横跳（0 flips），彻底根除了传统单均线硬阈值系统在锯齿震荡市的反复打脸换手损耗。
4. **变盘触发线不倒挂防线确立 (Based on Obs 1.1 & 1.2)**:
   - 经 $11 \times 11 = 121$ 组全价格与均线偏离度组合压测，`surge_line` 恒大于 `c300_price`，`breakdown_line` 恒小于 `c300_price`，距离百分比符号恒成立，彻底杜绝了 UI 界面中进攻线反而低于现价或防守线高于现价的逻辑倒挂。
5. **裁判与基建测试零回归 (Based on Obs 1.2 & 1.3)**:
   - `test_infra.py` 15 项裁判基建测试（日历反作弊、因果探针、风格切片抗回撤）与 `test_strategy_bridge.py` 9 项既有测试全量通过，证明 M1 升级未引入任何前瞻偏差或架构破坏。

---

## 3. Caveats

1. **底层正交资产列依赖假设**:
   - `OnlineExpertWeightUpdater` 依赖底层四岛策略计算专家权重，输入 DataFrame 必须包含基本基准指数列（如 `STAR50_STITCH`, `H00300`, `H00922`, `H00905`, `H11009`）。若传入缺少这些核心列的残缺 DataFrame，底层策略函数会抛出 `KeyError`。在实际工程中，`StrategyBridge.load_matrix()` 始终返回完整全量宽表，该假设在实盘运行时完全受保障。
2. **下游模块集成未完待续**:
   - 本次评估范围为 Milestone 1（`strategy_bridge.py` 中的 R2 在线学习与 R3 迟滞状态机）。Milestone 2（EWMA 风险平价与在途摩擦效用拦截）与 Milestone 3（CUSUM 选基与 Streamlit 4-step 白盒 UI）属于后续里程碑作业。

---

## 4. Conclusion

**Verdict: APPROVE**

经 Challenger 1 独立编写 186 项对抗性严苛实证测试压测：
1. `OnlineExpertWeightUpdater` 在历史与合成切片下权重之和严格等于 1.0000（误差 $< 10^{-5}$），高净效用专家权重严格单调递增，对极端行情与超参数表现出优秀的数值稳定性；
2. `SchmidtHysteresisBuffer` 在 $\text{MA20} \pm 0.5\%$ 噪音带内实现 0 次横跳状态锁定，双向变盘触发线在全价格空间严格满足 `surge_line > c300 > breakdown_line`；
3. 全套回归测试（210 项用例）100% 通过，未触碰任何受保护文件，无日历或未来函数作弊。

Milestone 1 满足验收标准与实盘风控铁律，正式予以**批准通过 (APPROVE)**，建议推进至 Milestone 2。

---

## 5. Verification Method

独立复现与验证步骤：
1. **执行 Challenger 1 严苛对抗性测试套件**:
   ```powershell
   Set-Location "d:\Google\Workspace\Wind\AGY2_FundAdvisory"
   $env:PYTHONPATH="d:\Google\Workspace\Wind\AGY2_FundAdvisory;d:\Google\Workspace\Wind"
   python -m pytest tests/test_adversarial_m1_stress.py -v
   ```
   **预期断言**: `186 passed` in < 15s.

2. **执行全套回归测试与基建安全校验**:
   ```powershell
   Set-Location "d:\Google\Workspace\Wind\AGY2_FundAdvisory"
   $env:PYTHONPATH="d:\Google\Workspace\Wind\AGY2_FundAdvisory;d:\Google\Workspace\Wind"
   python -m pytest tests/test_strategy_bridge.py tests/test_infra.py tests/test_adversarial_m1_stress.py -v
   ```
   **预期断言**: `210 passed, 2 warnings` in < 35s.

3. **失效判定条件 (Invalidation Conditions)**:
   - 任何切片下 `abs(sum(weights) - 1.0) >= 1e-5`；
   - 施密特迟滞环在 $\text{MA20} \pm 0.5\%$ 噪音震荡测试中发生状态切换 (`flips > 0`)；
   - 变盘触发线出现 `surge_line <= c300_price` 或 `breakdown_line >= c300_price`；
   - `test_infra.py` 裁判基建测试出现任何失败。
