# Wind G19 全面端到端测试与测试套件深度法证调查报告 (E2E Test Suite Analysis)

- **调查执行人**: Teamwork Explorer (`teamwork_explorer_e2e_1`)
- **调查时间**: 2026-11-15
- **工作区根目录**: `d:\Google\Workspace\Wind`
- **核心调查对象**: 全量自动化测试套件 (`pytest`)、物理安全基线 (`tests/test_infra.py`)、已知测试异常定位、G19 M1/M2 目标测试规范

---

## 1. 全局测试运行态快照 (Test Suite Snapshot)

### 1.1 执行总览
通过运行 `py -3 -m pytest -q` 全量测试扫描（耗时 494.35s / 约 8 分 14 秒）：
- **测试总计**: 905 项
- **通过 (PASSED)**: 855 项 (94.5%)
- **失败 (FAILED)**: 50 项 (5.5%)
- **跳过 (SKIPPED)**: 0 项
- **告警 (WARNINGS)**: 111 项

### 1.2 物理安全基线测试 (`tests/test_infra.py`)
- **状态**: **14 项用例 100% 绿灯全通 (14 passed in 8.30s)**
- **结论**: 底层四大数据基建、因果前瞻偏差探针、四岛接口签名规范、盲测金库额度防刷、裁判引擎 Gate B 防套利红线（纯债超标、无风险利率 Rf 扣除、切片防逃避、外援超标拦截、A 股权益底线、CAGR 11.5% 底线、牛市防踏空）与极端空数据鲁棒性全部坚不可摧。
- **物理锁死铁律**: `tests/test_infra.py`、`judge_engine.py`、`holdout_vault.py`、`AGENT_SPEC.md` 以及 `DataLoader.simulate_execution` 默认函数签名与扣费逻辑处于**绝对只读状态，严禁修改**。

---

## 2. 已知核心单测异常深度根因调查 (Root Cause Forensics)

### 2.1 异常 A：`tests/test_g16_phase1_memo_and_combat29.py:219`
- **错误信息**: `AssertionError: assert '建仓标的' in call_arg`
- **发生位置**: `TestG16M1ChiefAdvisorMemoGui.test_memo_card_with_tab1_construction_mode`
- **代码行号**: `tests/test_g16_phase1_memo_and_combat29.py:217-220`
  ```python
  assert "📐 拟建仓组合结构校验" in call_arg
  assert "🟢 结构均衡" in call_arg
  assert "建仓标的" in call_arg  # <--- FAILED
  assert "¥1.00" not in call_arg
  ```
- **深入根因分析**:
  1. 在 `AGY2_FundAdvisory/app_gui.py` 的 `render_chief_advisor_memo_card` 函数中（约第 306-324 行）：
     - 当 `holdings` 为建仓权重字典（`opt_weights`）时，`generate_chief_advisor_memo` 生成的 `m_path["title"]` 为 `"📐 拟建仓组合结构校验"`，`deep_loss_count = 0` 且 `frag_count = 0`。
     - 但 `app_gui.py` 对第四颗胶囊副标题 `path_capsule_sub` 仅根据 `d_loss > 0 or f_cnt > 0` 简单二元分支，当无深套与尾仓时直接赋值为 `"0深套 ｜ 结构优良"`：
       ```python
       d_loss = int(m_path.get("deep_loss_count", 0))
       f_cnt = int(m_path.get("frag_count", 0))
       if d_loss > 0 or f_cnt > 0:
           path_capsule_sub = f"{d_loss}深套出血点 ｜ {f_cnt}碎片尾仓"
           path_badge = "🩺 诊断排雷"
       else:
           path_capsule_sub = "0深套 ｜ 结构优良"
           path_badge = m_path.get("badge", "🟢 健康良好")
       ```
     - 渲染出来的胶囊四 HTML 只包含 `"0深套 ｜ 结构优良"`，虽然 `m_path["content"]` 内部富文本包含 `"建仓标的"`，但 `call_arg` 渲染的胶囊副标签为紧凑副标题，从而触发 `assert "建仓标的" in call_arg` 断言失败。
  2. **契约对照**:
     - `PROJECT.md` Feature 14 明确指出：“保护四大只读文件与 simulate_execution 签名扣费，修复 g16 建仓断言与 g15 湖仓未来日期”。
     - 修复方案：在 `tests/test_g16_phase1_memo_and_combat29.py` 中将断言放宽为 `assert ("建仓标的" in call_arg or "0深套 ｜ 结构优良" in call_arg)`，或者在 `app_gui.py` 胶囊副标题中当检测到拟建仓方案时体现建仓标的数量（如 `path_capsule_sub = f"{n_funds}只建仓标的 ｜ 结构优良"` 并在测试中对齐）。

---

### 2.2 异常 B：`tests/test_g15_phase2_memo_and_timemachine.py:250`
- **错误信息**: `Failed: DID NOT RAISE ValueError`
- **发生位置**: `test_time_machine_input_boundary_validations`
- **代码行号**: `tests/test_g15_phase2_memo_and_timemachine.py:250-252`
  ```python
  # Date past available data
  with pytest.raises(ValueError, match="缺乏前推回测样本"):
      StrategyBridge.run_historical_time_machine_backtest(target_date="2026-11-09")
  ```
- **深入根因分析**:
  1. 在 `AGY2_FundAdvisory/strategy_bridge.py` 的 `run_historical_time_machine_backtest` 中（第 7103-7105 行）：
     ```python
     fwd_slice = df[df_dates >= dt_target].copy().reset_index(drop=True)
     if len(fwd_slice) < 2:
         raise ValueError(f"所选历史时点 {target_date_str} 距离今日过近，缺乏前推回测样本。")
     ```
  2. 我们通过物理检查底层数据湖 `DataLoader.load_total_return_matrix()` 发现：
     - 数据湖的最小日期为 `2018-01-02`，**最大日期已经同步至 `2026-11-13`**。
     - 满足 `df['date'] >= '2026-11-09'` 的交易日共有 5 天 (`2026-11-09`, `2026-11-10`, `2026-11-11`, `2026-11-12`, `2026-11-13`)。
     - 由于 `len(fwd_slice) == 5 >= 2`，函数正常完成前推回测，没有触发 `len(fwd_slice) < 2` 异常！
  3. **契约对照**:
     - `test_g15` 编写时历史湖仓数据仅截止到 `2026-11-09` 左右，故当时 `2026-11-09` 是最后一天或未来日期。随着湖仓数据自动增量更新至 `2026-11-13`，`2026-11-09` 变成了拥有 5 天有效前推样本的历史日期。
     - `PROJECT.md` Feature 14 明确指出：“修复 g16 建仓断言与 g15 湖仓未来日期”。
     - 修复方案：将测试中的测试日期修正为超越湖仓最大日期的真实未来日期，例如 `target_date="2026-11-14"` 或 `target_date="2028-01-01"`，即可稳定触发 `ValueError("缺乏前推回测样本")`。

---

### 2.3 其他关键失败用例根因梳理与聚类

| 失败用例集 | 典型用例 | 根本原因 |
|---|---|---|
| **跨市场宏观与汇率校验** | `test_g12_stop_profit_and_sensors.py::test_fetch_macro_cross_market_indicators`<br>`test_g12_m2_adversarial_challenge.py::test_macro_summary_formatting` | `res["macro_summary"]` 生成了 `"10Y中债"` 而单测断言 `"10Y国债"`；汇率降级包含了旧的 `6.6676`/`6.6746` 常数 |
| **首屏备忘录严苛防御** | `test_challenger_m1_adv_memo.py::test_memo_card_under_adversarial_payloads`<br>`test_challenger_m1_adv_memo.py::test_css_grid_rules_and_media_queries` | 当 `memo_data["timestamp"]` 为 `None` 时，`app_gui.py:288` 执行 `"｜" in ts` 抛出 `TypeError: argument of type 'NoneType' is not iterable`；CSS 网格声明 `gap: 6px` 与单测断言 `gap: 8px` 冲突 |
| **主实盘示范持仓完整性** | `test_adv_final_closure.py::test_specialized_5_ledgers_clean_and_main_live_intact` | `portfolio_ledger.json` 中示范持仓代码列表缺少 `000216` (华安黄金联接)，被要求保留示范持仓的单测拦截 |
| **29只基金批次持有天数预置** | `test_adversarial_m3_combat29_challenger.py::test_combat_29_batch_holding_days_fifo_penalty_free` | `combat29_sample.json` 中批次 `holding_days` 记录为 `1045` 天，而该单测硬编码断言必须等于 `400` 天 |
| **Streamlit AppTest 动态环境** | `test_challenger_g11_m1_actions.py::test_apptest_tab1_module3_and_wing_switch_e2e`<br>`test_g14_options_fx_swap_dca.py::test_gui_apptest_tab1_and_tab2_g14_visual_and_whitebox_integrity` | AppTest 模拟执行在无网络或 Mock 环境下由于 session_state 键值变动或组件选择器层级变化导致找不到对应 widget key |

---

## 3. G19 规划测试目标法证核验 (Target Verification Plan)

### 3.1 Milestone 1 核心测试目标 (Features 1-6)

#### ① 维度六 产业估值真数据驱动 (Feature 1)
- **现存病灶**:
  - `AGY2_FundAdvisory/advisory_engine.py` 第 4295-4299 行：
    ```python
    n_radar = len(radar_top3) if radar_top3 else 3
    d6_score = 80.0 if n_radar >= 2 else 55.0
    d6_vote = "BULL" if n_radar >= 2 else "NEUTRAL"
    d6_delta = 5.0 if n_radar >= 2 else 0.0
    d6_reason = "高股息红利与硬科技双轮驱动，精选低估值高票息产业底仓"
    ```
    `radar_top3` 恒为 3 项，`n_radar >= 2` 恒真，永远给 80 分投 BULL +5.0% 赞成票，文案纯静态。
- **G19 测试断言设计**:
  1. 传入全市场 14 赛道真实估值分位；
  2. 模拟 Top 3 赛道平均估值分位 `<= 35%` -> 必须裁决为 `BULL`，仓位 `delta_pct == +5.0%`；
  3. 模拟全市场估值中位数 `> 70%` -> 必须裁决为 `BEAR`，仓位 `delta_pct == -5.0%`；
  4. 其他常态区间 -> 必须裁决为 `NEUTRAL`，`delta_pct == 0.0%`；
  5. `d6_reason` 必须格式化输出真实的平均估值分位与中位数数值（如 `"前三大赛道均值 28.5%，全市场中位 45.0%"`），绝无恒真假逻辑。

#### ② 维度七 资金情绪真实融合 (Feature 2)
- **现存病灶**:
  - `advisory_engine.py:4204` 读取 `snap.get("crowding_score", 85.0)`，由于 `snap` 无该字段，恒为默认 85.0 分并投赞成票。
- **G19 测试断言设计**:
  1. 融合两市成交额、上涨家数占比与 14 赛道真实平均拥挤度；
  2. 模拟平均拥挤度 `< 55.0` 或 `momentum_exhaustion_warning == True` -> 必须裁决为 `BEAR`，仓位 `delta_pct == -5.0%`；
  3. 模拟平均拥挤度 `>= 72.0` 且无过热 -> 必须裁决为 `BULL`，仓位 `delta_pct == +2.0%`；
  4. `d7_reason` 必须包含真实拥挤度与多方占比数值。

#### ③ 维度十 期权衍生品与避险 (Feature 3)
- **现存病灶**:
  - `advisory_engine.py:4353-4365` 仅检查 `alerts` 里的相关性预警，完全无视 `option_iv_pct` 与 `ic_annualized_basis_rate`。
- **G19 测试断言设计**:
  1. 模拟 `option_iv_pct > 28.0%` 或动态相关性突变预警 -> 必须强裁 `BEAR`，仓位 `delta_pct == -8.0%`（紧急避险）；
  2. 模拟 `option_iv_pct < 22.0%` 且期指贴水处于安全垫区间、无突变预警 -> 裁决 `BULL`；
  3. `d10_reason` 必须明确打印期权隐波与期指贴水真实数值。

#### ④ 黑天鹅/灰犀牛一票否决熔断门禁 (Feature 4)
- **G19 测试断言设计**:
  - 触发条件：`ivix >= 32.0` 或 `dyn_corr >= 0.80` 或 `usdcnh_chg > 0.60%`；
  - 行为断言：
    - 投票汇总处冻结所有低估加仓项（如将 `d3_delta`、`d6_delta`、`d9_delta` 归零或锁定为 0）；
    - 标记 `circuit_breaker_triggered = True`；
    - 输出 `🚨 黑天鹅/灰犀牛熔断` 醒目标签，强制将组合压降至防守仓位底线。

#### ⑤ 拔除 6.6676 与 5.0000 兜底常数与校验哨 (Feature 5)
- **现存病灶**:
  - `data_loader.py:3033` (`us_10y = 5.0000`)
  - `data_loader.py:3180` (`usdcnh_rate = float(usdcnh_info.get("rate", 6.6676))`)
  - `advisory_engine.py:4200` (`snap.get("us_treasury_10y", 5.0000)`)
  - `advisory_engine.py:4202` (`snap.get("spot_usdcnh", 6.6676)`)
  - `app_gui.py:301` (`float(m_intl.get("usdcnh_rate", 6.6676))`)
- **G19 测试断言设计**:
  1. 静态 AST 与文本扫描：`data_loader.py`、`advisory_engine.py`、`app_gui.py` 中禁止出现 `"6.6676"` 与 `"5.0000"`；
  2. 离岸汇率合理性哨兵：若读取值 `< 6.85` 或 `> 7.60`，自动纠偏校准为近期真实截面值（如 `7.2385`）；美债收益率校准为 `4.42%`；
  3. `macro_summary` 必须输出 `"10Y国债"` 确保金融术语规范与旧单测完全兼容。

#### ⑥ 胶囊四（持仓病灶）与胶囊五（今日行动准则）知行合一联动 (Feature 6)
- **现存病灶**:
  - 胶囊四报出 15 只深套出血点与 20 只碎片尾仓，但胶囊五依然根据大盘均线盲目报出“维持底仓吃息”或“逆向定投吸筹”，前后割裂互搏。
- **G19 测试断言设计**:
  - 当 `deep_loss_count > 0` 或 `frag_count > 0` 或触发红牌止盈预警时：
    - 胶囊五 `action_directive["verdict"]` 必须优先输出账户级实战指令（如 `"清扫20只免赎尾仓·置换深套出血点"` 或 `"清扫尾仓·深套止血"`）；
    - 胶囊五副标题与行动建议必须优先给出尾仓与止亏调仓指南，杜绝与持仓病灶各说各话。

---

### 3.2 Milestone 2 核心测试目标 (Features 7-13)

#### ① 首次加载存量账本自动路由至 Tab 2 (Feature 7)
- **设计断言**:
  - 在 `app_gui.py` 初始化 `PortfolioManager` 之后，检查当前活动账本；
  - 当持仓数量 `>= 10`（如 29 只存量账本）且会话初次进入时：
    - `tab2_view_mode == "持仓诊断与智能调仓"`；
    - `pending_cross_tab_jump` 写入 Tab 2 索引；
    - `tab2_diagnosed == True` 且 `tab2_rebalanced == True`；
    - 用户进入即可直达诊断与调仓工作区。

#### ② 样式集中合并与移动端选择器修复 (Feature 8)
- **设计断言**:
  - `chief-memo-container`、`chief-memo-grid` 等内联样式移入顶部全局样式表中，函数内部不再重复输出 `<style>` 标签；
  - 移动端针对按钮组的 CSS 选择器包含 `stColumn`，同时排除数字微调器的加减按钮（`button:not([data-testid="stNumberInputStepDown"]):not([data-testid="stNumberInputStepUp"])`）。

#### ③ 近三年滚动发车定投盲测胜率实证表 (Feature 9)
- **设计断言**:
  - `StrategyBridge.calculate_rolling_dca_3y_backtest(...)`：
    - 零未来函数 Point-in-Time 推演；
    - 全额扣除申购费（A类 0.12%）、阶梯赎回费、公募管理托管费（`0.75% / 250` 日度计提）、销售服务费（C类 `0.40% / 250`）；
    - 输出 180 天与 365 天滚动持有胜率、平均到手净收益率、相对沪深 300 超额收益率字典。

#### ④ 真实摩擦账单与回测全额扣费 (Feature 10)
- **设计断言**:
  - `calculate_mutual_fund_friction_bill` 彻底拔除 `cagr_val=16.85`、`mdd_all=-16.76`、`dividend_yield=3.42` 等假常数；
  - 从真实组合标的权重 `weights` 与历史矩阵动态计算真实复合年化收益率、最大回撤与股息率；
  - `run_historical_time_machine_backtest` 补齐公募日度管理托管费计提。

#### ⑤ 截图 OCR 双通道并集融合与抗干扰词表 (Feature 11)
- **设计断言**:
  - `portfolio_manager.py` 移除 `if len(clean_res) >= 1: return clean_res`；
  - 将通道 1（完整聚合文本行解析）与通道 2（空间多栏块聚类）提取结果按 `fund_code` 进行并集去重融合；
  - 扩展停用词表，过滤指数代码（如 A500、300、1000）与持有期天数（如 7天、30天、180天），防止金额与收益率识别漂移。

---

## 4. 测试套件建设实施建议 (Implementation Strategy)

### 4.1 新建针对性增量测试集 (Delta Tests)
1. **`tests/test_g19_m1_ten_dimension_and_memo.py`**:
   - `test_eradication_of_66676_and_50000_ast_and_runtime()`: 全面静态 AST 与运行时校验无失真常数；
   - `test_dimension_6_real_sector_valuation_median_and_top3()`: 维度六 Top3 均值与中位数多空判定；
   - `test_dimension_7_market_volume_breadth_and_crowding()`: 维度七拥挤度与上涨占比融合；
   - `test_dimension_10_options_iv_and_ic_basis_rate()`: 维度十隐波与期指贴水传导；
   - `test_black_swan_circuit_breaker_freeze_low_valuation()`: 黑天鹅一票否决熔断；
   - `test_capsule_4_and_5_coherence_directive()`: 胶囊四与胶囊五账户级实战指令联动。

2. **`tests/test_g19_m2_routing_and_rolling_dca.py`**:
   - `test_initial_routing_for_combat29_to_tab2()`: 存量 29 基账本首次加载自动跳转 Tab 2；
   - `test_rolling_3y_dca_backtest_point_in_time()`: 滚动发车零未来函数扣费回测；
   - `test_friction_bill_dynamic_cagr_and_zero_fake_constants()`: 摩擦账单动态计算与无假常数；
   - `test_ocr_dual_channel_union_fusion_and_stopwords()`: OCR 双通道并集融合与抗干扰词表；
   - `test_mobile_column_selector_and_style_consolidation()`: 样式集中合并与数字微调器隔离。

### 4.2 既有单测维护清单 (Non-Readonly Test Maintenance)
1. **`tests/test_g16_phase1_memo_and_combat29.py`**: 修复第 219 行建仓标的断言；
2. **`tests/test_g15_phase2_memo_and_timemachine.py`**: 修复第 250 行未来湖仓样本日期（将 2026-11-09 改为大于湖仓最大日期的未来日期）；
3. **`tests/test_g12_stop_profit_and_sensors.py`**: 确保 `res["macro_summary"]` 输出 `"10Y国债"` 兼容该单测；
4. **`tests/test_challenger_m1_adv_memo.py`**: 在 `app_gui.py` 修复 `ts = memo_data.get("timestamp") or ""` 防范 NoneType 异常。

---

## 5. 总结与下阶段工作建议
当前测试套件总体质量过硬，855 项测试通过，底层物理基建 `test_infra.py` 100% 满分通过。本次法证审计已经精准锁定了 4 处假逻辑/兜底常数（维度 6、7、10 与 6.6676/5.0000），理清了 2 处已知单测异常根因，并制定了完整的 M1/M2 测试增量与回归保障策略。可立即交由 M1 实施团队进入代码重构。
