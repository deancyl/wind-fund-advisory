# 对抗性质量审查与法证核验交接报告 (Handoff Report)

- **审查员**: `reviewer_g16_m3_2` (Reviewer & Adversarial Critic)
- **审查目标**: Milestone 3 UI/UX 实现与前端交互逻辑 (`AGY2_FundAdvisory/app_gui.py` 及联动模块)
- **目标交付**: 
  1. Tab 2 29基实战三阶瘦身手术面板 (`combat_29_funds`)、四维量化对比与操作按钮链路
  2. Tab 3 专属回测预设对比 (`🎯 实战存量组合：原始29基 vs 投顾重构6基`) 与时光机动态再平衡开关 (`tgl_dynamic`)
- **审查裁决**: **REQUEST_CHANGES (要求变更并驳回)**

---

## 1. 观察记录 (Observation)

### 1.1 Tab 2 三步重构处方面板代码观察 (`AGY2_FundAdvisory/app_gui.py:6117-6194`)
1. **静态 HTML 文本脱节与基金数量矛盾**:
   - `app_gui.py:6170`:
     ```html
     <div style="font-size: 12px; font-weight: 600; color: #16a34a;">✅ 调仓优化后 7 只全天候压舱石</div>
     <div style="font-size: 11.5px; color: var(--text-secondary); margin-top: 4px;">
         • 年化复合收益率: <b>+11.92%</b> (提升 +5.80% / +94.8%)<br>
         • 历史最大回撤: <b>-14.80%</b> (大幅收敛 5.49%，完全合规在控)<br>
         • 持仓标的数量: <b>7 大核心底仓</b> (纯粹精炼)
     </div>
     ```
     代码中硬编码为“7 只全天候压舱石”与“7 大核心底仓”，而任务契约、`StrategyBridge.get_combat_29_rebalance_prescription()` 以及 `reconstructed_6_weights` 均明确定义为 **6 只重构标的** (`005561`, `110020`, `017436`, `002351`, `011612`, `000216`)。
   - `StrategyBridge.estimate_rebalance_impact` 与 `StrategyBridge.get_combat_29_rebalance_prescription` 在 `app_gui.py` 中**完全未被调用**，四维对比数据（持仓 29->6 只、盘活免赎资金 ¥442.70~¥962.57、零赎回费 ¥0.00、回本天数 0 天）未能在对比卡中真实渲染呈现。

2. **操作按钮虚设与状态机空挂 (Integrity Violation / Facade Implementation)**:
   - `app_gui.py:6184-6192`:
     ```python
     if st.button("🧹 一键执行三步瘦身重构模拟（清扫 19 只免赎尾仓 + 置换深套出血点）", key="btn_apply_combat29_rx", type="primary", use_container_width=True):
         st.session_state.tab2_sweep_tail = True
         st.session_state.tab2_c_replace = "011613"
         st.session_state.tab2_diagnosed = True
         st.session_state.tab2_rebalanced = True
         st.session_state.tab2_trigger_rebalance = True
         st.session_state.tab2_rebal_cache = None
         st.rerun()
     ```
   - 全局搜索 `tab2_sweep_tail`：
     ```powershell
     Select-String -Path "*.py","*/*.py","*/*/*.py" -Pattern "tab2_sweep_tail"
     # 结果仅在 app_gui.py:6185 出现一次赋值，全工程从未读取！
     ```
   - 现场对抗探针验证（`scripts/test_m3_review_probe.py`）：
     当点击该按钮时，由于未设置 `st.session_state.rad_tab2_scenario_mode = "🧹 尾部碎片与C类一键归拢 (清理<3%碎片与满期高费率C类至底仓)"`，调仓引擎以 `scenario_mode="standard"` 运行。在标准再平衡模式下，温和缓冲带（3%）不仅没有清扫 19 只碎片尾仓，反而对大市值核心标的 `110020 易方达沪深300` 抛出 `-¥5,279.05`、对 `017436 华安纳指100` 抛出 `-¥4,536.85` 的全额平仓卖单，彻底违背处方“保留核心底仓、归拢碎片”的承诺！

### 1.2 Tab 3 时光机动态再平衡开关丢失 (`AGY2_FundAdvisory/app_gui.py:7242-7248`)
1. **任务要求与工单规定**:
   - `worker_m3_rep/DISPATCH.md` Task 4: `Add dynamic rebalance toggle tgl_dynamic = st.toggle("启用时光机动态再平衡（按日/周信号敏捷调仓）", value=True) passed into run_historical_time_machine_backtest.`
   - `reviewer_g16_m3_2/DISPATCH.md`: `Verify Tab 3 backtest preset: ... Dynamic rebalance toggle tgl_dynamic in time machine.`
2. **实际代码实现 (`app_gui.py:7242-7248`)**:
   ```python
   tm_res = StrategyBridge.run_historical_time_machine_backtest(
       target_date=curr_chosen_date,
       tier=st.session_state.get("active_tier_val", "C3"),
       capital=float(st.session_state.get("plan_capital", 100000.0))
   )
   ```
   - 全工程搜索 `tgl_dynamic`：在 `app_gui.py` 中为 0 处匹配，该组件**完全被遗漏**！
   - `run_historical_time_machine_backtest` 的入参 `dynamic_rebalance` 在前端永远处于缺省值 `False`，用户在 UI 上根本无法切换或体验 2024.09 拐点的动态再平衡，前端功能处于缩水状态。

### 1.3 Tab 3 专属预设对比实现核验 (`app_gui.py:7321, 7406`)
- `bt_mode` 成功加入 `"🎯 实战存量组合：原始29基 vs 投顾重构6基（近1年真规则回测对比）"`，且正确联动 `StrategyBridge.get_combat_29_vs_reconstructed_6_preset()`，权重归一化与平账无误（29基 vs 6基）。
- `StrategyBridge.build_custom_portfolio_backtest` 成功接入 `primary_weights` (6基) 与 `secondary_weights` (29基) 绘制同屏双曲线。

### 1.4 自动化单测与裁判红线核验
1. **调度命令指定单测**:
   - 编排指令给出 `py -3 -m pytest tests/test_e2e_gui_render.py tests/test_g16_phase1_memo_and_combat29.py -v`。
   - 法证发现：`test_e2e_gui_render.py` 实际位于 `AGY2_FundAdvisory/tests/test_e2e_gui_render.py`。
   - 修正路径后运行：**14 passed in 105.51s (100% 通过)**。
2. **M3 专项单测与对抗套件**:
   - `tests/test_m3_item2_rebalance_impact.py`: 2 passed
   - `tests/test_m3_item3_tab3_backtest.py`: 3 passed
   - `tests/test_adversarial_m3_combat29_challenger.py`: 9 passed
   - 合计 14 passed in 7.48s。
3. **物理只读红线**:
   - `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py` 均保持零修改，哈希完全一致。
   - `DataLoader.simulate_execution` 签名与默认扣费参数未变。
   - `tests/test_infra.py` 全量 14 项基建单测 100% 绿灯。
   - `tests/test_multi_ledger_manager.py` 与 `test_multi_ledger_manager_stress.py` 全量 16 项隔离单测 100% 绿灯。

---

## 2. 推理逻辑链 (Logic Chain)

1. **前提 1（契约规范）**: 用户原始需求 §三.3、SCOPE.md Feature 7 & 8 及 worker DISPATCH 明确要求：
   - Tab 2 提供一键执行三步重构处方模拟按钮，清扫 19 只免赎尾仓（回收 ¥442.70~¥962.57 并增持核心底仓）并置换深套出血点；
   - 处方卡需呈现 29->6 只、零费率、回本天数等四维对比；
   - Tab 3 时光机需实装 `tgl_dynamic` 动态再平衡开关。
2. **前提 2（实测代码行为）**: 
   - 按钮 `btn_apply_combat29_rx` 仅仅设置了一个从未被任何函数读取的虚构变量 `st.session_state.tab2_sweep_tail = True`，未设定场景模式，未设定归集底仓；
   - 调仓引擎在接收该按钮事件后，走入默认的标准再平衡分支，对核心资产 `110020` 和 `017436` 触发了全仓清盘卖单，而 19 只免赎碎片却未被清扫；
   - 处方文本仍停留在旧版的“7 只全天候压舱石”文案，与 6 只重构标的产生事实冲突；
   - 时光机控件中压根没有创建 `tgl_dynamic` 控件。
3. **依据审查员铁律 (Integrity Violation Invariant)**:
   - "Dummy or facade implementations that look correct but implement no real logic"
   - "Shortcuts that bypass the intended task"
   - 一旦发现上述模式，审查裁决**必须 (MUST)** 判定为 `REQUEST_CHANGES`，并在 Finding 中打上 `INTEGRITY VIOLATION` 标签，绝不可因测试通过而放行。
4. **结论导出**: 尽管底层算法库与单测套件通过，但前端 UI 交互层存在虚设状态机、关键控件缺失与文案不符，构成严重的功能伪实现与交付缺陷，必须立即驳回并要求修复。

---

## 3. 局限与注意事项 (Caveats)

- 本次审查未修改任何代码（严格遵循 Review-only 约束）。
- 后端计算函数 `get_combat_29_rebalance_prescription`、`get_combat_29_vs_reconstructed_6_preset`、`estimate_rebalance_impact` 及 `dynamic_rebalance` 算法本身逻辑严密且单测完备，缺陷完全集中在前端 `app_gui.py` 的绑定与装配层。

---

## 4. 审查报告与缺陷清单 (Review Findings)

### Review Summary
- **Verdict**: **REQUEST_CHANGES**

### Findings

#### [Critical] [INTEGRITY VIOLATION] Finding 1: Tab 2 处方模拟按钮状态机虚设 (Dummy Facade Implementation)
- **What**: 按钮 `[🧹 一键执行三步瘦身重构模拟（清扫 19 只免赎尾仓 + 置换深套出血点）]` 设置了全工程未被引用的死变量 `tab2_sweep_tail = True`，未配置 `scenario_mode` 与 `sel_sc_anchor`，导致实际执行了错误的标准再平衡，反向清仓了核心资产而漏掉了 19 只碎片。
- **Where**: `AGY2_FundAdvisory/app_gui.py:6184-6192`
- **Why**: 属于典型的外表看似实现但内部无有效逻辑支撑的“假装实现 (Facade/Dummy)”，误导用户且破坏调仓安全。
- **Suggestion**: 
  在按钮点击回调中正确对接状态机：
  ```python
  st.session_state.rad_tab2_scenario_mode = "🧹 尾部碎片与C类一键归拢 (清理<3%碎片与满期高费率C类至底仓)"
  st.session_state.sel_sc_anchor = "002351 - 易方达裕祥回报债券A"
  st.session_state.tab2_c_replace = "011613"
  st.session_state.tab2_diagnosed = True
  st.session_state.tab2_rebalanced = True
  st.session_state.tab2_trigger_rebalance = True
  st.session_state.tab2_rebal_cache = None
  st.rerun()
  ```

#### [Major] Finding 2: Tab 3 时光机前端缺少 `tgl_dynamic` 动态再平衡开关
- **What**: 前端界面完全缺失任务书与工单明确规定的 `tgl_dynamic = st.toggle("启用时光机动态再平衡（按日/周信号敏捷调仓）", value=True)` 控件，`dynamic_rebalance` 无法从 Web UI 启用。
- **Where**: `AGY2_FundAdvisory/app_gui.py:7210-7248`
- **Why**: 后端已开发完备的动态再平衡算法在前端界面被物理架空，用户在 UI 上遭遇 2024.09 踏空无法自愈。
- **Suggestion**:
  在时光机参数配置栏（如日期选择器旁或上方）加入：
  ```python
  tgl_dynamic = st.toggle("启用时光机动态再平衡（按日/周信号敏捷调仓）", value=True, key="tm_tgl_dynamic", help="开启后在历史盲测中实施 Point-in-Time 动态调仓，消除 2024.09 政策底踏空")
  ```
  并将 `dynamic_rebalance=tgl_dynamic` 传入 `StrategyBridge.run_historical_time_machine_backtest(...)`。

#### [Major] Finding 3: Tab 2 处方卡文案数量错位与四维量化对比未动态对齐
- **What**: 处方卡第 3 步仍显示“7 只全天候压舱石”与“7 大核心底仓”，与实际重构 6 只标的事实冲突；且未将 `estimate_rebalance_impact` 算出的四维量化对比（29->6只、回收 ¥442.70~¥962.57、¥0.00费率、0天回本）呈现在对比网格中。
- **Where**: `AGY2_FundAdvisory/app_gui.py:6156-6180`
- **Why**: 文案与重构方案口径脱节，信息传达不准确。
- **Suggestion**:
  将文案修正为“6 只全天候压舱石”；或直接在 HTML 中调用 `StrategyBridge.get_combat_29_rebalance_prescription()["metrics_comparison"]` 进行动态高保真渲染。

#### [Minor] Finding 4: Dispatch 调度指令测试文件路径笔误
- **What**: 指令指定 `tests/test_e2e_gui_render.py`，但实际文件位于 `AGY2_FundAdvisory/tests/test_e2e_gui_render.py`。
- **Where**: `DISPATCH.md`
- **Why**: 执行直抛 `file or directory not found`。
- **Suggestion**: 后续编排指令修正为 `AGY2_FundAdvisory/tests/test_e2e_gui_render.py`。

---

## 5. 对抗性质询与压力测试 (Adversarial Challenges)

- **综合风险评估**: **HIGH (高风险，前端逻辑漏洞导致错误资产处置)**
- **对抗场景 1: 点击一键模拟重构按钮**:
  - *攻击假设*: 假设用户在 `combat_29_funds` 界面点击一键模拟重构，期望清扫 19 只碎片并将 `011613` 转为 A 类。
  - *实际表现*: 系统由于 `scenario_mode="standard"`，开出卖出 `110020` (-¥5279) 与 `017436` (-¥4536) 的错误大单，严重误导投资人操作。
  - *危害半径*: 核心资产被误斩仓，买方信任彻底崩溃。
- **对抗场景 2: 切换时光机 2024.09 底部反转**:
  - *攻击假设*: 用户点击“🔥 2024.09 底部反转前”，预期查看动态调仓消除踏空的最新优化效果。
  - *实际表现*: 前端由于缺少 `tgl_dynamic`，强行执行 `dynamic_rebalance=False`，界面依旧呈现静态滞后表现。

---

## 6. 独立验证方法 (Verification Method)

后续代理可直接在 Windows PowerShell 执行以下命令复核：

```powershell
# 1. 验证虚假变量 tab2_sweep_tail 无读取引用 (输出应仅有定义行 6185)
Select-String -Path "AGY2_FundAdvisory\app_gui.py" -Pattern "tab2_sweep_tail"

# 2. 验证缺失 tgl_dynamic (输出为空)
Select-String -Path "AGY2_FundAdvisory\app_gui.py" -Pattern "tgl_dynamic"

# 3. 运行端到端渲染与 M1 回归 (修正路径)
py -3 -m pytest AGY2_FundAdvisory/tests/test_e2e_gui_render.py tests/test_g16_phase1_memo_and_combat29.py -v

# 4. 运行 M3 专项测试
py -3 -m pytest tests/test_m3_item2_rebalance_impact.py tests/test_m3_item3_tab3_backtest.py tests/test_adversarial_m3_combat29_challenger.py -v
```

**失效判定条件**: 当且仅当 `btn_apply_combat29_rx` 正确绑定 `sweep_tail_and_c_class` 场景、`tgl_dynamic` 成功挂载至时光机 UI 并联动 `dynamic_rebalance`、且处方卡文案严格校准为 6 只标的四维对比时，本驳回结论方可推翻。
