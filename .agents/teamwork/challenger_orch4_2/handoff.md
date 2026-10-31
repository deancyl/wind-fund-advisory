# Handoff Report — Adversarial Stress Challenge 2 (challenger_orch4_2)

## 1. Observation
本挑战者作为第二位独立对抗测试员 (Adversarial Stress Challenger 2)，针对 R3 三段式攻防闭环、R4 调仓适宜度裁决器与四大后果推演器、以及重合度矩阵双红利底仓协同豁免进行极限实证施压测试。直接观测数据如下：

1. **物理安全红线与文件不变性观测**：
   - 检查系统 4 个只读裁判基建文件：
     - `AGY2_FundAdvisory/judge_engine.py` (Mode: -ar---, 0 lines changed)
     - `AGY2_FundAdvisory/holdout_vault.py` (Mode: -ar---, 0 lines changed)
     - `AGY2_FundAdvisory/AGENT_SPEC.md` (Mode: -ar---, 0 lines changed)
     - `AGY2_FundAdvisory/tests/test_infra.py` (Mode: -ar---, 0 lines changed)
   - 经 `git status` 与 `git diff` 验证，4 大裁判基建文件严格保持 0 篡改、只读属性完好。

2. **核心算法源码定位观测**：
   - `strategy_bridge.py:3344-3767`：`compute_dynamic_tier_weights` 实现了：
     - 行 3656-3666：左侧超卖极限点（`erp_percentile >= 75.0` 且 `bias_20 <= -4.5%`）触发纯债划拨，以 60% : 40% 配比增配华夏科创50 (`011613`) 与创金中证500 (`001053`)；
     - 行 3452-3454 及 3764-3765：施密特迟滞缓冲带 `[-1.5%, +1.2%]` 内锁定 `_prev_hysteresis_weights`；
     - 行 3681-3695：右侧极端超买（`bias_20 >= 6.5%` 或 `crowding_warning == True`）触发成长仓位主动削减 35%，并以 50% / 50% 比例转入纯债 (`002351`) 与红利低波 (`005561`)。
   - `strategy_bridge.py:4892-5048`：`evaluate_today_rebalance_suitability` 实现了：
     - 行 4948-4951 & 5021-5024：持仓中包含未满 7 天批次需卖出时，强制裁决为 `verdict_level = "FORBIDDEN"`，标题提示 7 天惩罚费；
     - 行 5013-5018：输出包含 `market_position_reason`, `clock_window_reason`, `deviation_utility_reason`, `lockup_fee_reason` 的完整 `reasons_4d` 字典。
   - `strategy_bridge.py:5051-5463`：`simulate_rebalance_modes_and_consequences` 实现了：
     - 行 5155-5160 & 5224-5227：`mode_gentle` 模式下仅卖出 `penalty_free_shares`，`penalty_fee_7d` 强制归零；
     - 行 5209-5215：`mode_forced` 模式下强平未满 7 天批次，如实全额计提 1.50% 证监会惩罚费；
     - 行 5359-5449：输出四大后果字典（`fee_loss`, `in_transit_risk`, `risk_shift`, `lockup_reset`）。
   - `portfolio_manager.py:4026-4115`：`calculate_stock_overlap_matrix` 实现了：
     - 行 4028：将推荐双红利底仓对 `frozenset({"100032", "005561"})` 与限购伴生对 `frozenset({"050025", "001071"})` 列入 `EXEMPT_OVERLAP_PAIRS`；
     - 行 4087-4096：豁免对不进入 `unexcused_overlaps`，不触发 `alerts`，记录在 `exempt_pairs`；
     - 行 4097-4112：非豁免且重叠度 $\ge 0.40$ 的组合必须进入 `unexcused_overlaps` 并触发黄色假分散警告。

3. **对抗测试套件运行实测数据**：
   - 编写专门对抗测试脚本：`AGY2_FundAdvisory/tests/test_adversarial_orch4_challenger2.py`（包含 7 个深度对抗用例）。
   - 执行命令：`C:\Users\deanc\AppData\Local\Programs\Python\Python311\python.exe -m pytest tests/test_adversarial_orch4_challenger2.py -v`
   - 实测输出：
     ```text
     tests\test_adversarial_orch4_challenger2.py::test_adversarial_three_stage_left_oversold PASSED [ 14%]
     tests\test_adversarial_orch4_challenger2.py::test_adversarial_three_stage_schmitt_hysteresis_noise PASSED [ 28%]
     tests\test_adversarial_orch4_challenger2.py::test_adversarial_three_stage_right_overbought_profit_taking PASSED [ 42%]
     tests\test_adversarial_orch4_challenger2.py::test_adversarial_rebalance_suitability_and_consequences_7d_penalty PASSED [ 57%]
     tests\test_adversarial_orch4_challenger2.py::test_adversarial_rebalance_consequences_4d_accounting_balance PASSED [ 71%]
     tests\test_adversarial_orch4_challenger2.py::test_adversarial_stock_overlap_dual_dividend_exemption PASSED [ 85%]
     tests\test_adversarial_orch4_challenger2.py::test_adversarial_stock_overlap_malicious_false_diversification PASSED [100%]
     ============================== 7 passed in 3.06s ==============================
     ```
   - 阶段一关联全量测试套件执行：
     `pytest tests/test_milestone_phase1_r1_r5.py tests/test_portfolio_manager.py tests/test_strategy_bridge.py tests/test_adversarial_orch4_challenger2.py -v`
     输出：`====================== 52 passed, 84 warnings in 44.31s =======================`。

---

## 2. Logic Chain
1. **三段式攻防闭环推演**：
   - **左侧超卖极限点**：输入 `erp_percentile=95.0%`, `bias_20=-8.0%`。`is_left_oversold = True` 触发。算法从纯债（`002351`）中削减 0.03 仓位，分别增配 0.018 华夏科创50 (`011613`) 与 0.012 创金中证500 (`001053`)，增配比例严格为 60% : 40%。且在 C1~C5 全档位压力测试下，C1 坚守纯债防守（权益 $\le 25\%$），C2~C5 满足严格单调递增性（`Equity(C1) < Equity(C2) < Equity(C3) < Equity(C4) < Equity(C5)`）。在极限崩盘（`-25.0%`）下，纯债保留底仓不被穿透掏空。
   - **施密特迟滞 50 步高频噪音锁定**：构造 50 步三角波与随机噪音复合时间序列，`bias_20` 在 `[-1.4%, +1.1%]` 范围内剧烈摆动。算法通过 `_prev_hysteresis_weights` 锁定死区仓位。实测 50 个步长内，每一步返回权重与初值完全一致，单步换手率均为 0.0，累计 50 步总换手率严格为 0.0，彻底消除均线高频打脸摩擦。
   - **右侧极端超买阶梯止盈**：输入 `bias_20=+9.0%` 或 `crowding_warning=True`。成长类标的（`011613`, `001053`, `016634`, `013841`, `007339`）主动被削减 35% 敞口（实测削减比例 35.0%），削减所得资金以 50% : 50% 平分划拨至纯债（`002351`）与红利低波（`005561`），且总权重严格归一化为 1.0000。

2. **调仓适宜度四维裁决与双模式后果推演精算推演**：
   - **适宜度裁决**：当持仓中存在未满 7 天批次需卖出时，裁决器准确识别 `penalty_free_shares <= 1e-4`，输出 `verdict_level="FORBIDDEN"`，并在 `reasons_4d["lockup_fee_reason"]` 中明确告知 1.50% 证监会惩罚费。
   - **温和免伤模式 (`mode_gentle`)**：调用 `get_penalty_free_redeemable_shares` 裁剪拟卖出份额，未满 7 天份额严禁卖出，`penalty_fee_7d == 0.0` 严格为 0。
   - **强行对齐模式 (`mode_forced`)**：强平全部偏离，真实计提 1.50% 惩罚费（`penalty_fee_7d >= 150.0` 元）。
   - **分厘平账断言**：
     - 手续费平账：`total_fee == round(redemption_fee + penalty_fee_7d + subscription_fee, 2)`（分厘不差）；
     - 净资产平账：`equity_after == round(max(0.0, equity_before - total_fee), 2)`（分厘不差）；
     - 在途比例平账：`in_transit_pct == round((in_transit_amount / total_equity) * 100.0, 2)`；
     - 锁定期重置平账：`new_buy_amount` 精准反映买入订单合计，且警告文案明确提示 7 天 1.5% 惩罚期与 A 类 180 天持有期清零。

3. **重合度矩阵双红利与伴生对豁免推演**：
   - **标准推荐底仓组合**：`{"100032", "005561", "002351", "000216", "050025", "001071"}` 中，`{"100032", "005561"}`（红利增强+红利低波）与 `{"050025", "001071"}`（标普500拆单伴生组）命中豁免白名单，被移入 `exempt_pairs`；非豁免对的重叠度均为 0.0，`alerts` 严格为空列表 `[]`，`max_non_diag_unexcused == 0.0 < 0.40`，彻底根除假阳性误报。
   - **恶意伪分散组合**：
     - 科技芯片组合（`011612` + `013841`）：共享中芯国际、海光信息等芯片龙头，重合度达 0.40，坚决触发黄色假分散警告，`max_non_diag_unexcused = 0.40 >= 0.40`；
     - 克隆红利组合（`090010` + `012643`）：跨公司克隆标的，重合度达 1.00，坚决触发假分散警告，`max_non_diag_unexcused = 1.00`。

---

## 3. Caveats
1. **测试运行环境**：测试在本地 Python 3.11.9 + pytest 9.1.1 环境下完成；数据源优先从本地缓存提取，断网与联网双轨运行。
2. **假设条件**：测试假定行情快照由上游 `get_latest_market_snapshot()` 产生，测试中通过注入标准及极限边界快照验证算子的纯数学因果演绎。
3. **未涉猎范围**：阶段一仅聚焦于后端核心量化算法（`portfolio_manager.py`, `strategy_bridge.py`, `data_loader.py` 与 `tests/`），未涉及前端 Streamlit 交互组件渲染（此为阶段二任务）。

---

## 4. Conclusion
基于以上全部 7 项极限对抗实证施压数据与阶段一全量 52 项单元测试套件的 100% 通过验证，本挑战者认定：
- R3 三段式攻防闭环（左侧极值吸筹、施密特迟滞震荡噪音锁定、右侧超买止盈）逻辑闭环、边界严密、防打脸与止盈效果显著；
- R4 调仓适宜度四维裁决器与双模式后果推演器真实计提 7 天 1.50% 惩罚费，四大后果字典全域分厘平账；
- 重合度矩阵双红利与限购伴生对协同豁免机制有效杜绝假阳性，并精准识别非豁免伪分散组合；
- 系统只读裁判文件与物理安全红线 100% 遵守。

**裁决结论：Verdict: CONFIRM_CORRECTNESS**

---

## 5. Verification Method
独立复现与验证步骤：

1. **执行专用对抗测试套件**：
   ```powershell
   cd d:\Google\Workspace\Wind\AGY2_FundAdvisory
   & 'C:\Users\deanc\AppData\Local\Programs\Python\Python311\python.exe' -m pytest tests/test_adversarial_orch4_challenger2.py -v
   ```
   **期望结果**：7 项对抗用例 100% PASSED，执行耗时约 3 秒。

2. **执行阶段一核心全量测试套件**：
   ```powershell
   cd d:\Google\Workspace\Wind\AGY2_FundAdvisory
   & 'C:\Users\deanc\AppData\Local\Programs\Python\Python311\python.exe' -m pytest tests/test_milestone_phase1_r1_r5.py tests/test_portfolio_manager.py tests/test_strategy_bridge.py tests/test_adversarial_orch4_challenger2.py -v
   ```
   **期望结果**：52 项核心测试全部通过 (52 passed in ~45s)。

3. **检验物理裁判文件只读与零篡改**：
   ```powershell
   cd d:\Google\Workspace\Wind\AGY2_FundAdvisory
   git status judge_engine.py holdout_vault.py AGENT_SPEC.md tests/test_infra.py
   ```
   **期望结果**：无任何未提交更改，文件只读属性完好。

---

## Challenge Report

### Overall Risk Assessment: LOW (极低风险·核心算法通过极限施压验证)

### Challenges

#### Challenge 1: 三段式攻防闭环极端边界与高频震荡稳定性
- **Assumption challenged**: 系统在左侧崩盘超卖、右侧极端暴涨超买与死区高频锯齿震荡下能否稳定运行，不产生穿透、溢出或反复横跳调仓。
- **Attack scenario**: 构造 `erp=99.9%, bias_20=-25.0%` 的黑天鹅极值，以及 `[-1.4%, +1.1%]` 范围内 50 次高频高幅震荡噪音序列。
- **Blast radius**: 若失效，可能导致熊市底部纯债被抽干抛空，或震荡市产生高达 50 次无效换手磨损资金。
- **Mitigation & Verification**: 实测证实 `min(0.03, max(0.0, cur_bond_w - 0.04))` 严守 4% 纯债安全垫；施密特死区 50 步总换手率严格为 0.0。

#### Challenge 2: 7天惩罚费拦截与双模式四大后果分厘平账精算
- **Assumption challenged**: 系统能否在用户持仓包含未满 7 天批次时准确实施安全拦截，且双模式后果推演在费用、净资产、在途资金上是否绝对分厘平账。
- **Attack scenario**: 构造持有仅 1 天与 2 天且带 `safety_lock` 的混合持仓，强制要求调仓。
- **Blast radius**: 若温和模式漏卖触发惩罚费，将给用户造成 1.50% 的真实本金磨损；若四大后果字典不平账，将导致账目混乱。
- **Mitigation & Verification**: 实测证实 `mode_gentle` 惩罚费严格为 0.0，`mode_forced` 足额计提 1.50%（$\ge 150.0$ 元）；四大字典在任何情况下分厘平账。

#### Challenge 3: 重合度矩阵双红利与伴生对豁免与伪分散防作弊
- **Assumption challenged**: 双红利底仓对与限购伴生对在豁免假分散报警的同时，是否会误豁免非推荐的同赛道高重合克隆基金。
- **Attack scenario**: 构造 `011612+013841`（重合度 0.40）与跨公司同赛道克隆基金 `090010+012643`（重合度 1.00）。
- **Blast radius**: 若误判豁免，用户将陷入伪分散集中暴跌风险；若推荐组合误报，将破坏系统推荐一致性。
- **Mitigation & Verification**: 实测证实推荐组合 0 报警且 `max_non_diag_unexcused == 0.0`；恶意克隆基金与高重合科技基金坚决触发黄色报警，无任何作弊或漏判。

### Stress Test Results

| 测试场景编号 | 场景描述 | 预期行为 | 实际行为 | 判定结果 |
|---|---|---|---|---|
| 1.1 | 左侧超卖极限点 (`erp=95%, bias_20=-8.0%`) | 纯债削减，60%/40% 划拨增配宽基 011613/001053 | 纯债削减 0.03，科创50 +0.018，中证500 +0.012，归一化 1.0 | PASS |
| 1.2 | 施密特迟滞高频震荡噪音 (50次在 `[-1.4%, +1.1%]` 摆动) | 仓位严格锁定，50步累计换手率 = 0.0 | 50步权重完全恒定，累计换手率 0.0 | PASS |
| 1.3 | 右侧极端超买阶梯止盈 (`bias_20=+9.0%` 或 `crowding_warning=True`) | 成长仓位削减 35%，对半划拨至纯债与红利低波 | 成长削减 35%，纯债与红利低波各增加 50% 利润，归一化 1.0 | PASS |
| 2.1 | 7天惩罚期持仓适宜度裁决与双模式推演 | 适宜度返回 FORBIDDEN；温和模式惩罚费=0；强行模式计提 1.5% | FORBIDDEN 预警；温和模式惩罚费 0.0；强行模式真实计提 1.5% | PASS |
| 2.2 | 四大后果字典全域平账精算 | 费用、净资产、在途资金、新买入金额全部分厘平账 | 手续费分项求和、净资产扣减、在途比例完全吻合 | PASS |
| 3.1 | 标准推荐底仓协同豁免 (100032+005561) | alerts 为空，max_non_diag_unexcused < 0.40 (0.0) | alerts 数量为 0，max_unexcused = 0.0，双对进入 exempt_pairs | PASS |
| 3.2 | 恶意构造非豁免高重合伪分散组合 (011612+013841, 090010+012643) | 坚决触发黄色假分散警告，max_unexcused >= 0.40 | alerts 数量 $\ge 1$，max_unexcused 分别为 0.40 与 1.00 | PASS |

### Unchallenged Areas
- 前端 Web/Streamlit UI 交互渲染与动画效果（属于阶段二任务，不在阶段一后端算法重构范围内）。
