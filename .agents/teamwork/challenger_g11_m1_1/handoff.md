# G11 Milestone 1 (Top Area & Tab 1) 对抗性压力测试与实证正确性审计报告

> **Agent**: `challenger_g11_m1_1` (Roles: critic, specialist)  
> **Target**: `AGY2_FundAdvisory/app_gui.py` (Top Area & Tab 1 新资建仓参数与推演引擎)  
> **Timestamp**: 2026-11-08T13:25:00Z  
> **Test Harness**: `d:\Google\Workspace\Wind\tests\test_challenger_m1_stress.py` (24 项自动化压力测试)

---

## Challenge Summary

**Overall risk assessment**: **LOW** (底层数学逻辑极其健壮，仅在极端脱机直调且传入零本金时暴露一处除零隐患，已被前端控件纵深防御有效封堵；Tab 1 交互与核心推演引擎在 100元 至 1亿元、全部 5 档风险策略、3 种节奏、7 大机构模型下均实证 100% 保持数学守恒与 0 崩溃渲染)。

---

## 1. Observation (直观观测事实与证据)

### 1.1 实证复现的底层除零缺陷 (Vulnerability Discovery)
- **触发路径与命令**:
  ```powershell
  py -3 -c "import sys; sys.path.insert(0, 'AGY2_FundAdvisory'); from strategy_bridge import StrategyBridge; StrategyBridge.generate_zero_start_blueprint(total_capital=0.0)"
  ```
- **控制台逐字异常与堆栈**:
  ```python
  Traceback (most recent call last):
    File "<string>", line 1, in <module>
    File "D:\Google\Workspace\Wind\AGY2_FundAdvisory\strategy_bridge.py", line 5725, in generate_zero_start_blueprint
      it["target_weight_pct"] = round((it["allocated_amount"] / total_capital) * 100.0, 2)
                                       ~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~
  ZeroDivisionError: float division by zero
  ```
- **前端纵深防护观测**:
  在 `AGY2_FundAdvisory/app_gui.py` 第 3262–3270 行：
  ```python
  plan_capital = st.number_input(
      "拟投资总本金 (元)",
      min_value=1000.0,
      max_value=100000000.0,
      value=float(st.session_state.get("plan_capital_input", 100000.0)),
      step=10000.0,
      format="%.0f",
      key="plan_capital_input"
  )
  ```
  交互界面通过 `min_value=1000.0` 构筑了硬前置边界，普通用户在 UI 无法输入低于 1,000 元的本金，避免了前端界面直接被穿透。

### 1.2 本金边界与分厘平账实证结果
在自动化测试套件 `tests/test_challenger_m1_stress.py` 中：
- `test_capital_fractional_cents_reconciliation` (本金 12,345.67 元): 分配总额 `12,345.67`，误差 `< 0.01` 元，百分比闭合为 `100.00%`，**PASSED**。
- `test_capital_extreme_large_100_million` (本金 100,000,000.00 元): 分配总额 `100,000,000.00`，成功触发 QDII 标的单日大额限额拆单（`has_split=True`），**PASSED**。
- `test_capital_small_100_yuan` (本金 100.00 元): 分配总额 `100.00`，各标的金额非负且平账，**PASSED**。

### 1.3 风险策略档位 C1 至 C5 单调性实证
- 对 `C1`, `C2`, `C3`, `C4`, `C5` 全部五档测试运行 `compute_n_funds_model_portfolio` 与 `generate_zero_start_blueprint`，标的只数均 $\ge 3$ 只，各档位权重严格归一化。
- C1 保守型防守固收（纯债）占比达 `54.0%`（$\ge 50\%$），C5 追击型防守固收占比为 `0.0%`，高弹性权益资产占比最高。C1 防守比例显著大于 C5 防守比例，风险频谱单调递增性成立（`test_tier_risk_spectrum_monotonicity` **PASSED**）。

### 1.4 三大建仓节奏数学守恒实证
- **⚡ 一次性建仓**: `sum(order_amount) == total_capital`，最后一只标的精准吸收尾差，守恒误差 0.00 元（`test_lump_sum_conservation` **PASSED**）。
- **🌊 稳健三步分批**: 拆解为 50% 底仓 + 30% 逢低网格 + 20% 右侧趋势，各批次金额及批次内订单金额总和与总本金严格吻合，守恒误差 0.00 元（`test_three_step_batches_conservation` **PASSED**）。
- **📅 估值自适应智能定投**:
  - 极度低估水下（ERP=85%, Bias=-5%）：扣款乘数自适应放大至 `1.83x`（$\ge 1.5\text{x}$，触发逆向猛扣）；
  - 严重超买高估（ERP=20%, Bias=+8%）：扣款乘数自适应压降至 `0.00x`（$\le 0.5\text{x}$，触发暂停扣款）；
  - 单基真实波动率穿透计算的 VWAP 微观优化节省金额与节省基点均为正值（`test_smart_dca_multiplier_and_vwap_optimization` **PASSED**）。

### 1.5 七大机构量化定权模型实证
对以下 7 个模型分别求解 6 只基金最优配比：
1. `hrp_cvar` (鲁棒双核HRP)
2. `core_satellite` (核心-卫星杠铃)
3. `all_weather` (全天候风险平价)
4. `black_litterman` (BL主客观观点融合)
5. `cond_winrate` (条件胜率最优)
6. `min_cvar` (尾部风控CVaR)
7. `kelly_momentum` (凯利动量增强)
- 7 个模型求解出的资产配置权重向量均满足：$\forall w_i \ge 0$ 且 $\sum w_i = 1.0000 \pm 0.0001$；
- 各模型输出的 KPI（1年达标胜率、历史至暗浮亏、最长水下回本天数）全部为有效有限浮点数（`test_model_solving_and_kpi_synthesis` 7 项全部 **PASSED**）。

### 1.6 Streamlit AppTest 真实运行时渲染实证
- 默认初始化模式下：无未捕获异常，`plan_capital_input`, `tab1_tier_selector`, `radio_capital_deployment_mode`, `tab1_sel_model_type` 等关键控件均挂载到位（**PASSED**）。
- 点击「⚡ 生成实盘建仓方案」触发推演全流程：
  - 3 项核心决策大卡（`收益与胜率`, `风险底线`, `攻防定权`）高对比度渲染成功；
  - 实盘合规铁律文案（`不满 7 天严禁赎回防 1.5% 惩罚费` 及 `1年达标胜率`）100% 存在；
  - 执行数据表 `st.dataframe` 正常展示并包含 9 大关键列；
  - 页面底部单一白盒抽屉（`展开机构级量化压力测试与选基白盒证据`）正常呈现；
  - `radio_capital_deployment_mode` 切换为稳健三步时，3 批订单卡片与列扩展正确渲染；
  - 切换为智能定投时，实盘牛熊拐点对照尺、3 项定投指标与 VWAP 滑点优化卡片正确渲染；
  - 全过程 `assert not at.exception`，无任何 Python 异常（4 项 AppTest 全部 **PASSED**）。

---

## 2. Logic Chain (推理链条与因果溯源)

1. **除零缺陷推理 (基于 1.1)**:
   - 在 `strategy_bridge.py` 第 5725 行，代码执行：
     `it["target_weight_pct"] = round((it["allocated_amount"] / total_capital) * 100.0, 2)`
   - 当调用方显式传入 `total_capital = 0` 时，分母直接为零触发 `ZeroDivisionError`。
   - 尽管前端通过 `st.number_input(min_value=1000.0)` 阻断了非法本金进入，但防御机制应具备多层韧性（Defense-in-depth）。后端接口若未做 `max(1e-4, total_capital)` 或空方案退化保护，在未来任何外部脚本或离线测试直调时均构成脆性点。
2. **三块式架构与极简交互正确性推理 (基于 1.2 ~ 1.6)**:
   - Worker 将原本繁杂的 Step 1 -> Step 2 -> Step 3 拆解为：
     - 单行控制栏（5 控件）
     - 3 核心决策指标卡 + 执行数据表置顶
     - 底部 4 操作 + 单一白盒证据抽屉
   - 压力测试证实，此项重构未对底层量化计算引擎造成任何断裂或状态脱靶：7 大定权模型的矩阵计算、黑天鹅承压、蒙特卡洛 10,000 次推演及分批/定投调度完全无损运行。
   - 资金分厘平账算法在各种边界下运转稳健，能够精准处理 1 亿元大额 QDII 限额拆单与 12,345.67 元小数吸收。

---

## 3. Caveats (注意事项与假设)

1. **测试边界与范围**:
   - 本次压力测试范围严格聚焦于 Milestone 1 所交付的代码（`AGY2_FundAdvisory/app_gui.py` Top Area、全局 CSS 及 Tab 1 新资建仓全流程）；
   - Tab 2 持仓调仓、账本运维及 Tab 3 组合穿透回测属于后续里程碑范围，未在此处包含。
2. **关于历史工作区账本断言的发现说明**:
   - 在全库普查中发现 `tests/test_adv_final_closure.py` 中有一项断言因本地主实盘账本 `portfolio_ledger.json` 中示范基金调整（缺失 `000216`）而未绿灯；
   - 根据 `PROJECT.md` 规划，该项属于 Milestone 3 的测试对齐（Test Suite Alignment）与 Milestone 5 的账本清洁（Clean Ledgers）范围，不属于 Milestone 1 的交付阻断项。

---

## 4. Conclusion (结论与实证判定)

- **对抗裁定**: **PASS (通过，伴随 1 项低危防御性改进建议)**。
- Worker `worker_g11_m1` 在 `app_gui.py` 中实施的 Top Area 与 Tab 1 三块式极简重构在数学因果律、金额守恒性、风险策略单调性及前端渲染健壮性上均**真实有效**。
- 建议后续在底层 `StrategyBridge.generate_zero_start_blueprint` 入口处追加针对 `total_capital <= 0` 的保护性兜底（例如 `total_capital = max(1000.0, float(total_capital))` 或安全返回空项），进一步增强核心库的防守深度。

---

## 5. Verification Method (独立核验与验收指令)

任何团队成员或审计员均可执行以下命令对本报告结论进行 100% 独立复现：

```powershell
# 1. 运行 Challenger 1 专门编写的 24 项对抗压力测试套件 (包含本金边界、5档风险、3大节奏、7大模型与 AppTest 渲染)
py -3 -m pytest tests/test_challenger_m1_stress.py -v

# 2. 独立复现除零边界与防护断言
py -3 -m pytest tests/test_challenger_m1_stress.py -k test_capital_zero_division_guard

# 3. 验证 7 大模型在 AppTest 真实界面的挂载与黑天鹅测试渲染
py -3 -m pytest tests/test_anticheat_full_closure.py -k test_apptest_tab1_seven_models_and_black_swan_rendering

# 4. 验证四大只读裁判文件与基建反作弊 100% 保持只读
py -3 -m pytest tests/test_infra.py
```

### Invalidation Conditions (失效判定)
- 若运行 `tests/test_challenger_m1_stress.py` 出现除已受控除零断言外的任何崩溃或失败，则判定失效；
- 若输入本金为带分厘小数时，建仓分配总额与输入本金产生大于 0.02 元的偏差，则判定失效；
- 若在 C1 至 C5 任意档位下未能输出不少于 3 只标的或权重和不等于 100%，则判定失效。
