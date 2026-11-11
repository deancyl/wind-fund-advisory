# Handoff Report — reviewer_g16_m3_r2_1

## Review Summary

**Verdict**: APPROVE

本次审查系针对 Milestone 3（实战存量组合 29 基瘦身重构、调仓实盘影响对比、Tab 3 回测图例纠偏与时光机敏捷动态再平衡）第 1 轮审查中提出的 4 项关键问题（包括 1 项假象实现 INTEGRITY VIOLATION、1 项核心数据结构损坏、1 项图例反转缺陷、1 项参数未接通缺陷）进行的全面、客观且具深层对抗压力的复核。

经法证审查与对抗压力测试，所有 4 项问题均已在 `AGY2_FundAdvisory/strategy_bridge.py`、`AGY2_FundAdvisory/app_gui.py` 以及 `tests/test_m3_item2_rebalance_impact.py` 中得到**真实、彻底且合规的整改**。没有任何门面假象（Facade）、硬编码作弊或单测逃逸，裁判基线与多周期实战回测 100% 保持绿灯。

---

## 1. Observation (客观法证观察)

### 观察项 1：`StrategyBridge.get_combat_29_rebalance_prescription` 数据结构已完全规范化
- **文件路径**: `AGY2_FundAdvisory/strategy_bridge.py`，第 6355-6365 行
- **源码实录**:
  ```python
  "step3_core_reconstruction": {
      "title": "第 3 步：重构为 6 只纯 A 类全天候核心压舱石",
      "funds": [
          {"code": "005561", "name": "创金合信中证红利低波动指数A", "weight_pct": 30.49},
          {"code": "110020", "name": "易方达沪深300ETF联接A", "weight_pct": 21.80},
          {"code": "017436", "name": "华安纳斯达克100ETF联接A", "weight_pct": 17.05},
          {"code": "002351", "name": "易方达裕祥回报债券A", "weight_pct": 17.54},
          {"code": "011612", "name": "华夏上证科创板50成份ETF联接A", "weight_pct": 7.79},
          {"code": "000216", "name": "华安黄金ETF联接A", "weight_pct": 5.33}
      ]
  }
  ```
- **法证执行结果**:
  运行 `py -3 -c "from AGY2_FundAdvisory.strategy_bridge import StrategyBridge; rx = StrategyBridge.get_combat_29_rebalance_prescription(); funds = rx['step3_core_reconstruction']['funds']; assert len(funds) == 6; assert all(set(f.keys()) == {'code', 'name', 'weight_pct'} for f in funds); assert sum(f['weight_pct'] for f in funds) == 100.0; print('SUCCESS')"` 输出 `SUCCESS`。
- **单测增强**:
  `tests/test_m3_item2_rebalance_impact.py` 第 42-45 行已增补强校验：
  ```python
  assert all("code" in f and "name" in f and "weight_pct" in f for f in step3["funds"])
  assert all(isinstance(f["code"], str) and len(f["code"]) == 6 for f in step3["funds"])
  assert all(isinstance(f["name"], str) and len(f["name"]) > 0 for f in step3["funds"])
  assert all(isinstance(f["weight_pct"], (int, float)) and f["weight_pct"] > 0 for f in step3["funds"])
  ```

---

### 观察项 2：Tab 2 真实量化联动与执行动作生效 (INTEGRITY VIOLATION 彻底消除)
- **文件路径**: `AGY2_FundAdvisory/app_gui.py`，第 6118-6215 行
- **动态量化调用**:
  第 6118-6134 行真实调用了 `StrategyBridge.get_combat_29_rebalance_prescription`、`StrategyBridge.get_combat_29_vs_reconstructed_6_preset` 与 `StrategyBridge.estimate_rebalance_impact`：
  ```python
  rx_data = StrategyBridge.get_combat_29_rebalance_prescription()
  rx_preset = StrategyBridge.get_combat_29_vs_reconstructed_6_preset()
  rx_impact = StrategyBridge.estimate_rebalance_impact(
      current_holdings=pm.holdings,
      target_weights_funds=rx_preset["reconstructed_6_weights"],
      total_equity=pm.total_equity,
      rebalance_items=[]
  )
  ```
- **四大核心维度动态渲染实测**:
  对 `combat_29_funds` 实盘账本运行 `estimate_rebalance_impact`，返回：
  - `fund_count_before`: 29 只 ➔ `fund_count_after`: 6 只核心底仓 (纯粹精炼 -79%)
  - `revitalized_cash_min`: ¥442.70 ➔ `revitalized_cash_max`: ¥962.57 (零手续费)
  - `total_fee`: ¥0.00 ➔ `payback_days`: 0 天 (`payback_desc`: "即时零损耗")
  - `div_change`: "+1.32% 票息厚度提升" (2.10% -> 3.42%)
- **文案与标题纠正**:
  第 6189 行彻底纠正为 `✅ 调仓优化后 6 只全天候核心压舱石`，原“7 只全天候”错误已在全文件中清除 (`'7 只全天候' in src == False`)。
- **按钮状态机落地闭环**:
  第 6204-6212 行 `btn_apply_combat29_rx` 彻底废除无用死状态 `tab2_sweep_tail = True`，完整设置了调仓场景驱动变量：
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
  在第 6273-6281 行，系统准确进入 `sweep_tail_and_c_class` 场景模式，提取目标锚定底仓 `002351`，并经 `WinRateOptimizer.optimize_rebalance_path` 精准执行 19 只免赎尾仓归拢至 002351 与 011613 极速置换 011612，零赎回摩擦。

---

### 观察项 3：Tab 3 实战回测双曲线与回撤图例颠倒彻底纠偏
- **文件路径**: `AGY2_FundAdvisory/app_gui.py`，第 7430-7436、7626-7645、7733-7751 行
- **图例与曲线映射**:
  在 `choice_kind == "preset_combat_29_vs_6"` 时：
  - `primary_weights = preset_info["reconstructed_6_weights"]` 对应图例名称：`pri_curve_name = "投顾重构 6 基核心组合"`
  - `secondary_weights = preset_info["raw_29_weights"]` 对应图例名称：`sec_curve_name = "原始 29 基存量组合"`
  - 水下回撤图主曲线名称：`pri_dd_name = "投顾重构 6 基水下回撤"`
  - 水下回撤图副曲线名称：`sec_dd_name = "原始 29 基水下回撤"`
  - 对普通的调仓对比模式（`choice_kind == "diff_rebal"`），保留原有“调仓前 vs 调仓后”的语义命名。
  - 彻底消除了将表现较差、回撤较大的旧 29 基错误标注为“调仓后”的颠倒因果 bug。

---

### 观察项 4：Tab 3 时光机 `dynamic_rebalance` 开关在前端完备接通
- **文件路径**: `AGY2_FundAdvisory/app_gui.py`，第 7260-7275 行
- **UI 开关与传参**:
  ```python
  tgl_dynamic = st.toggle("⚡ 启用时光机动态再平衡（按信号敏捷轮动）", value=True, key="tm_dynamic_rebalance_toggle", help="开启后在历史盲测中实施 Point-in-Time 动态调仓，消除 2024.09 政策底踏空")
  tm_res = StrategyBridge.run_historical_time_machine_backtest(
      target_date=curr_chosen_date,
      tier=st.session_state.get("active_tier_val", "C3"),
      capital=float(st.session_state.get("plan_capital", 100000.0)),
      dynamic_rebalance=tgl_dynamic
  )
  ```
- **实证效果比对 (2024-09-18 政策底)**:
  - 静态盲测 (`dynamic_rebalance=False`): 3M 净收益率 = **+6.73%**，超额沪深300 = **-17.80%** (踏空行情)
  - 动态轮动 (`dynamic_rebalance=True`): 3M 净收益率 = **+32.29%**，超额沪深300 = **+7.77%** (成功捕获右侧主升浪)
  - 动态超额收益高达 **+25.56%**，用户在前端通过 `tgl_dynamic` 可自由切换与同屏验证。

---

### 观察项 5：测试套件与基线核验全部绿灯通过
1. **指定测试套件**:
   ```powershell
   py -3 -m pytest tests/test_multi_ledger_manager.py tests/test_m3_item2_rebalance_impact.py tests/test_m3_item3_tab3_backtest.py tests/test_adversarial_m3_combat29_challenger.py -v
   ```
   **结果**: **22 passed, 31 warnings in 39.98s (100% 通过)**
2. **裁判基线测试**:
   ```powershell
   py -3 -m pytest tests/test_infra.py -v
   ```
   **结果**: **14 passed in 6.36s (100% 通过)**
3. **深层对抗压力测试**:
   ```powershell
   py -3 -m pytest tests/test_m3_adversarial_challenger2_stress.py -v
   py -3 scripts/verify_m3_r2_empirical.py
   py -3 scripts/test_m3_r2_adversarial_deep_stress.py
   ```
   **结果**: **18 passed in 8.88s (100% 通过)**，鸭子类型输入、极端微观 (0.01元) 与宏观 (10亿元) 市值压力测试、C1~C5 全档位弹性验证、交易日非工作日自适应平滑全部绿灯。
4. **全量回归与 GUI 渲染测试**:
   ```powershell
   py -3 -m pytest tests/test_g16_phase1_memo_and_combat29.py AGY2_FundAdvisory/tests/test_e2e_gui_render.py -v
   ```
   **结果**: **14 passed in 140.60s (100% 通过)**。

---

## 2. Logic Chain (推理链条)

1. **前提 1 (第 1 轮驳回原因)**: 第 1 轮审查驳回的核心在于 `StrategyBridge` schema 缺陷、Tab 2 缺乏真实调用而使用写死文字（被判定为 INTEGRITY VIOLATION）、按钮死状态、Tab 3 图例命名反转以及时光机动态开关未接通。
2. **前提 2 (代码修改核查)**: 经逐行 `git diff` 审查，Worker 在 `strategy_bridge.py` 中将 Step 3 列表内的标的代码均重构为标准的 `{"code": "...", "name": "...", "weight_pct": ...}`；在 `app_gui.py` Tab 2 中引入了真实的 `estimate_rebalance_impact` 动态计算并将结果注入 HTML；将“7 只”纠正为“6 只”；将按钮状态机正确绑定至场景模式与底仓；在 Tab 3 中纠正了图例判断逻辑并加入了 `tgl_dynamic` toggle 开关。
3. **前提 3 (无副作用与契约合规)**: `tests/test_infra.py` 14 项裁判测试零破坏；只读裁判文件零修改；工作区代码库完全符合《GEMINI.md》风控准则（先进先出安全赎回、零 7 天惩罚赎回费、零硬编码伪常数）。
4. **推导结论**: 所有的缺陷均已获得真实解决，无残留作弊或虚荣实现，完全符合买方投顾量化质量标准，应予无保留批准（APPROVE）。

---

## 3. Caveats (审查边界与留白)

- `portfolio_ledger.json` 在运行 `test_e2e_gui_render.py` 时由于 Streamlit 完整渲染被写入了测试状态，审查已执行 `git checkout portfolio_ledger.json` 将其恢复为干净工作区状态。
- 四个只读裁判文件（`judge_engine.py`、`holdout_vault.py`、`AGENT_SPEC.md`、`tests/test_infra.py`）哈希未变，零篡改。

---

## 4. Conclusion (裁决结论)

**裁决**: **`APPROVE`**

Milestone 3 的所有交付成果均已达到买方投顾实盘级水准：
1. **真实账本平账与隔离**：`combat_29_funds` 29 只基金市值 26,615.10 元分厘平账，元数据与运行时隔离稳健。
2. **科学三步瘦身方案**：19 只碎片尾仓全额免赎归拢回收 ¥442.70，科创50 C 类 011613 极速置换 011612 彻底消除每年 0.40% 抽血，重塑为 6 只全天候压舱石。
3. **量化对比与图例真实**：Tab 2 影响预估动态可信，Tab 3 回测图例因果清晰，时光机动态再平衡成功捕获 2024.09 政策底反转超额。
4. **对抗韧性完备**：各项单测与深层极限压力测试 100% 通过。

---

## 5. Verification Method (独立复核方法)

任何后续复核人员均可通过执行以下 PowerShell 命令独立验证：

```powershell
# 1. 验证 Step 3 处方 schema 与 100% 权重归一化
py -3 -c "from AGY2_FundAdvisory.strategy_bridge import StrategyBridge; rx = StrategyBridge.get_combat_29_rebalance_prescription(); funds = rx['step3_core_reconstruction']['funds']; assert len(funds) == 6; assert all(set(f.keys()) == {'code', 'name', 'weight_pct'} for f in funds); assert round(sum(f['weight_pct'] for f in funds), 2) == 100.0; print('Prescription Schema: PASS')"

# 2. 验证 Tab 2 动态调用与无死状态
py -3 -c "src = open('AGY2_FundAdvisory/app_gui.py', encoding='utf-8').read(); assert 'estimate_rebalance_impact' in src; assert '7 只全天候' not in src; assert '6 只全天候核心压舱石' in src; assert 'tab2_sweep_tail' not in src; print('Tab 2 GUI Integrity: PASS')"

# 3. 运行 M3 专项与对抗测试套件
py -3 -m pytest tests/test_multi_ledger_manager.py tests/test_m3_item2_rebalance_impact.py tests/test_m3_item3_tab3_backtest.py tests/test_adversarial_m3_combat29_challenger.py -v

# 4. 运行裁判基线测试
py -3 -m pytest tests/test_infra.py -v
```
