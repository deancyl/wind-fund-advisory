# Handoff Report: M1 调仓适宜度裁决、双模式推演与 Tab 2 向导折叠状态对抗实测

## 1. Observation (客观观察与实测数据)

1. **测试用例执行与测试结果**:
   - 编写并执行专用对抗测试套件 `AGY2_FundAdvisory/tests/test_adversarial_m1_challenger_m1_2.py`：
     - 命令：`cd AGY2_FundAdvisory; py -3.11 -m pytest tests/test_adversarial_m1_challenger_m1_2.py -c none -v`
     - 运行结果：`5 passed, 95 warnings in 64.12s` (100% PASS)。
     - 包含 5 项高难度对抗实测：
       1. `test_scenario_1_unmet_7d_penalty_shares_forbidden`: PASSED
       2. `test_scenario_2_approaching_cliff_shares_hold_on`: PASSED
       3. `test_scenario_3_normal_mature_shares_and_breakout_suitable`: PASSED
       4. `test_app_gui_ast_wizard_collapse_expressions`: PASSED
       5. `test_streamlit_apptest_tab2_collapse_when_holdings_exist`: PASSED
   - 运行基础设施只读文件完整性套件 `tests/test_infra.py`：
     - 命令：`cd AGY2_FundAdvisory; py -3.11 -m pytest tests/test_infra.py -c none -v`
     - 运行结果：`15 passed in 5.74s` (100% PASS，4 个核心裁判基建文件无任何修改或篡改)。
   - 运行阶段一核心里程碑套件 `tests/test_milestone_phase1_r1_r5.py`：
     - 命令：`cd AGY2_FundAdvisory; py -3.11 -m pytest tests/test_milestone_phase1_r1_r5.py -c none -v`
     - 运行结果：`11 passed in 14.55s` (100% PASS)。
   - 运行历史挑战者对抗套件 `tests/test_adversarial_orch4_challenger2.py`：
     - 命令：`cd AGY2_FundAdvisory; py -3.11 -m pytest tests/test_adversarial_orch4_challenger2.py -c none -v`
     - 运行结果：`7 passed in 3.06s` (100% PASS)。

2. **Tab 2 调仓适宜度裁决与三色研判实测观测 (StrategyBridge.evaluate_today_rebalance_suitability)**:
   - **场景 1 (未满 7 天惩罚期)**：注入未满 7 天份额（持有 2 天，10000 份，safety_lock=True）。
     - 实测返回值：`verdict_level == "FORBIDDEN"`。
     - `verdict_title`：`"🔴 今日不宜调仓·高损预警：持仓包含未满7天份额，强行卖出将触发1.5%惩罚费"`。
     - `reasons_4d['lockup_fee_reason']`：`"持仓包含未满 7 天批次，强行卖出将全额触发 1.50% 证监会惩罚性赎回费，构成严重收益磨损。"`
   - **场景 2 (临界免赎期 25~29 天)**：注入 C 类持有 28 天份额（7-29天为0.5%，>=30天为0%）。
     - 实测返回值：`verdict_level == "HOLD_ON"`。
     - `verdict_title`：`"🟡 今日建议按兵不动：部分持仓临近免赎阶梯，建议稍作等待以节约摩擦"`。
     - `reasons_4d['lockup_fee_reason']`：`"部分持仓距离免赎回费阶梯仅剩数日，建议稍作等待以节约手续费。"`
   - **场景 3 (正常满期份额 + 向上突破 + 14:30 黄金窗口)**：注入持有 400 天份额，bias_20 = +2.5% (> 1.2%)，d_max = 68.0% (>= 3%)。
     - 实测返回值：`verdict_level == "SUITABLE"`。
     - `verdict_title`：`"🟢 今日适合调仓：大盘形成有效突破，且调仓预期超额显著覆盖摩擦成本"`。
     - `reasons_4d['market_position_reason']`：`"大盘形成右侧向上有效突破 (20日均线乖离率 +2.5%)，脱离均线噪音带，进攻信号明朗。"`
     - `reasons_4d['lockup_fee_reason']`：`"拟卖出份额均已满免赎期 (C类满30天/A类阶梯免赎)，赎回摩擦为零。"`

3. **Tab 2 双模式调仓推演与四大后果精算观测 (StrategyBridge.simulate_rebalance_modes_and_consequences)**:
   - **温和免伤模式 (mode_gentle)**：
     - 在场景 1 下，`consequences["fee_loss"]["penalty_fee_7d"]` 严格等于 `0.0`；
     - 卖出订单 `orders` 中严格过滤了持有未满 7 天的批次标的（`013841` 零卖出），杜绝任何 1.50% 惩罚费发生。
   - **强行调仓模式 (mode_forced)**：
     - 在场景 1 下，`consequences["fee_loss"]["penalty_fee_7d"] == 150.00`，严格精确等于 `10,000 * 1.00 * 1.50%`；
     - `consequences["fee_loss"]["total_fee"] == redemption_fee + penalty_fee_7d + subscription_fee`；
     - `consequences["risk_shift"]["equity_after"] == equity_before - total_fee`，实现了分厘级数学平账。
   - **四大后果字典完整性**：
     - `fee_loss` 包含：`redemption_fee`, `penalty_fee_7d`, `subscription_fee`, `total_fee`, `payback_days`；
     - `in_transit_risk` 包含：`in_transit_amount`, `in_transit_pct`, `lock_days`, `switch_saved_amount`, `missed_rally_cost_est`；
     - `risk_shift` 包含：`equity_before`, `equity_after`, `vol_before`, `vol_after`, `mdd_before`, `mdd_after`, `div_yield_before`, `div_yield_after`；
     - `lockup_reset` 包含：`new_buy_amount`, `reset_warning_text`。
     - 字段完全对齐接口契约，无任何缺失。

4. **Tab 2 第三层向导折叠状态静态 AST 与 AppTest 渲染观测 (app_gui.py)**:
   - AST 静态源码验证：
     - 第 1620 行：`has_holdings = len(pm.holdings) > 0`
     - 第 1622 行：`with st.expander("✨ 零门槛持仓接管向导 (支持微信文本自由粘贴、中文拼音搜索、标准模板导入与冷启动)", expanded=(not has_holdings)):`
     - 第 1846 行：`with st.expander("📦 【点击展开：全组合 FIFO 批次透视与免赎回费倒计时汇总表】", expanded=False):`
     - 当 `len(pm.holdings) > 0` 时，`has_holdings` 为 `True`，`not has_holdings` 计算为 `False`，接管向导与 FIFO 向导全部折叠收起。
     - 持仓编辑面板（第 1553 行）采用 `st.data_editor` 嵌入主屏呈现，无额外展开的弹窗或常开 expander 遮挡视线。
   - Streamlit AppTest 动态渲染：
     - 注入真实账本运行 `AppTest.from_file("app_gui.py")`；
     - 读取 DOM 树中 Tab 2 expanders 的 protobuf 状态：`proto.expanded` 均为 `False`。

---

## 2. Logic Chain (推理链条)

1. **关于适宜度裁决器 (R4 闭环)**:
   - 依赖关系：裁决器输入依赖 `TradingClock`（交易时钟）、`get_latest_market_snapshot`（宏观均线与估值）以及 `PortfolioManager` 持仓的 FIFO 批次持有天数。
   - 推理逻辑：
     - 若组合中拟调出的任一标的包含持有天数 `< 7` 天批次，依据证监会公募基金销售费用管理规定，必触发 1.50% 惩罚性扣款，故系统直接顶格裁决为 `FORBIDDEN`；
     - 若持有天数在阶梯免赎期临界带（如 C 类 25~29 天），强行赎回产生 0.5% 损耗，而等待数日即可 0 成本卖出，故裁决为 `HOLD_ON`；
     - 仅当全部份额满免赎期、大盘脱离噪音带有效突破、交易窗口位于 14:30 黄金窗口且持仓偏离度 `d_max >= 3%` 时，预期 Alpha 显著超越摩擦，系统裁决为 `SUITABLE`。
   - 结论支持：实测 3 种场景与四维 `reasons_4d` 诊断字典均 100% 验证通过。

2. **关于双模式调仓推演与后果精算**:
   - 推理逻辑：
     - 温和模式（mode_gentle）的防御基石是保护持有人免受非理性调仓惩罚，因此其算法中对持有期不满 7 天的份额强制执行安全裁剪（`sell_shares = 0`），并将 `penalty_fee_7d` 严格锁定为 0；
     - 强行模式（mode_forced）满足用户“一步到位”强平需求，如实将 1.50% 惩罚费与阶梯赎回费计入 `fee_loss`，并如实计算在途资金时滞、攻防波动率变迁与新买入资金 7 天清零重算；
     - 两模式的数学分项求和与总权益变动均严格守恒：`total_fee == redemption_fee + penalty_fee_7d + subscription_fee`，`equity_after == equity_before - total_fee`。
   - 结论支持：实测数据分厘平账，无偏差。

3. **关于 Tab 2 向导折叠状态**:
   - 推理逻辑：
     - 当用户已有持仓时（`len(pm.holdings) > 0`），核心诉求为看盘、看裁决、看调仓建议，若接管向导展开会占据大半屏严重干扰体验；
     - 因此源码中设置 `expanded=(not has_holdings)`，有持仓时自动收起为 1 行紧凑条目，无持仓时自动展开供用户录入；
     - FIFO 透视表由于数据较多，默认统一设为 `expanded=False`，按需展开；
     - 编辑持仓直接通过双击 `st.data_editor` 单元格完成并提供一键保存按钮，无需嵌套展开器。
   - 结论支持：AST 静态推演与 AppTest 渲染测试均证实折叠逻辑正确无误。

---

## 3. Caveats (注意事项与假设说明)

1. **Streamlit AppTest 运行耗时**:
   - 由于 Streamlit AppTest 加载 `app_gui.py` 时会执行多赛道量化选基评分、动态风险配权矩阵计算，在单进程冷启动下耗时约 60~70 秒，在运行 AppTest 时需配置 `default_timeout >= 120`，避免被过短的测试超时阻断。
2. **非交易日与周末的时钟行为**:
   - 在非交易日或休市期间调用 `TradingClock.get_market_window_status` 时，`window_type` 会真实返回 `NON_TRADING_DAY` 或 `POST_MARKET_DELAYED`，此时系统默认偏向保守判定为 `HOLD_ON`。在测试 `SUITABLE` 场景时，需合理注入交易日 14:30 黄金窗口的环境快照。

---

## 4. Conclusion (对抗结论)

**裁决结论**: **APPROVE (完全批准通过)**

- **Tab 2 调仓适宜度裁决器**：3 种持仓场景（未满 7 天、临界免赎、突破满期）的研判等级（FORBIDDEN、HOLD_ON、SUITABLE）与 `reasons_4d` 诊断字典逻辑完全自洽且实测通过；
- **Tab 2 双模式调仓推演器**：温和模式 `penalty_fee_7d` 严格为 0，强行模式精确计提 1.50% 惩罚费与阶梯赎回费，四大后果字典（fee_loss, in_transit_risk, risk_shift, lockup_reset）字段完整无缺失，分厘平账；
- **Tab 2 第三层向导折叠状态**：在已有持仓状态下，接管向导与 FIFO 透视向导均严格默认折叠收起，不抢占主屏视觉空间；
- **安全红线**：4 个裁判基建文件 100% 保持只读未篡改，代码中 0 处伪造延迟、0 处硬编码常数；
- **全量测试套件**：全量对抗用例 100% 通过。

---

## 5. Verification Method (独立复现验证命令)

任何 Agent 或用户均可通过以下命令在终端直接复现验证：

```powershell
# 1. 运行本轮对抗验证测试套件 (包含 3 场景裁决实测、双模式精算与 AppTest 折叠验证)
cd AGY2_FundAdvisory
py -3.11 -m pytest tests/test_adversarial_m1_challenger_m1_2.py -c none -v

# 2. 运行系统只读裁判与红线基建测试
cd AGY2_FundAdvisory
py -3.11 -m pytest tests/test_infra.py -c none -v

# 3. 运行阶段一核心里程碑测试
cd AGY2_FundAdvisory
py -3.11 -m pytest tests/test_milestone_phase1_r1_r5.py -c none -v
```
