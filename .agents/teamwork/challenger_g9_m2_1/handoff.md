# Milestone 2 对抗验证报告 (Handoff Report)

## 1. 观察 (Observation)

### 1.1 被审计实现代码现场观察
- **`portfolio_manager.py` (第 6674 至 6912 行)**：
  - `evaluate_rebalance_audit` 实现了基于 9 大标准大类与“现金管理”的 Brinson-Fachler 经典超额拆解模型；
  - 核心计算逻辑：
    - 大类资产配置效应：`AR_raw_map[cat] = (w_P[cat] - w_B[cat]) * (R_B_map[cat] - R_B_total)`
    - 优选基金超额效应：`SR_raw_map[cat] = w_P[cat] * (R_P_map[cat] - R_B_map[cat])`
    - 基准缺失新大类对齐（第 6803-6804 行）：`if v_b_init <= 0 and actual_cat_values[cat] > 0: R_B_map[cat] = R_P_map[cat]`
    - 平账与归一化投影（第 6822-6839 行）：当 `abs(TE_raw_sum) > 1e-9` 时按比例分配，`select_yuan = round(total_active_add_yuan - alloc_yuan, 2)`，并在第 6901 行内置物理断言：`assert abs(alloc_yuan + select_yuan - total_active_add_yuan) < 1e-4`；
    - 兼容性返回字典（第 6903-6912 行）：完整返回 7 个历史顶级键名 `current_actual_equity`, `shadow_hold_equity`, `rebalance_value_add`, `rebalance_value_add_pct`, `saved_penalty_and_buffer_fees`, `baseline_date`, `shadow_holdings_count`，并挂载新键 `brinson_attribution`；
  - 基线持久化支持（第 3513 与 3527 行）：`_export_state_dict` 与 `_import_state_dict` 中已包含 `"initial_baseline_snapshot"` 的深拷贝序列化与反序列化。

- **`app_gui.py` (第 5920 至 6050 行)**：
  - 真实调用 `pm.evaluate_rebalance_audit()` 并渲染 Brinson 三维超额卡片（大类资产配置、优选基金超额、交易摩擦及惩罚规避）、9 大资产大类归因明细表 (`category_breakdown`) 与买方投顾穿透复盘点评；
  - 所有卡片与富文本输出统一经由 `safe_markdown_html` 渲染，严格遵循 CommonMark 4+ 空格缩进防御铁律。

### 1.2 独立对抗测试套件编写与执行观察
- 编写独立对抗测试文件 `tests/test_challenger_g9_m2_adversarial.py`，共涵盖 4 个测试类、14 项针对性对抗用例：
  1. `test_multi_fund_same_category_rebalance`：同大类多基金调仓分化场景下的恒等式断言；
  2. `test_cross_category_complex_rebalance`：跨纯债、黄金、美股QDII、科技等 4 大类调仓的恒等式断言；
  3. `test_negative_active_return_scenario`：调仓负超额 (Alpha < 0) 亏损踩雷场景下的恒等式与主导驱动断言；
  4. `test_zero_active_return_identity`：组合完全未动 (Alpha == 0) 的严格归零恒等式断言；
  5. `test_boundary_single_asset_portfolio`：单一资产组合（无现金、全仓单只标的）防崩溃与恒等式断言；
  6. `test_boundary_all_cash_portfolio`：全现金组合（0持仓）防除零与防 KeyError 断言；
  7. `test_boundary_zero_equity_portfolio`：真空组合（0持仓、0现金）安全兜底断言；
  8. `test_boundary_new_asset_class_absent_in_benchmark`：实盘新调入标的大类在影子基准中完全缺失时的防御断言（验证选基效应归零，配置效应承接全部超额）；
  9. `test_boundary_benchmark_asset_liquidated_in_active`：影子基准原有资产在实盘中完全清仓的低配归因断言；
  10. `test_legacy_seven_keys_types_and_presence`：原有 7 个历史顶级键名与类型的 100% 向下兼容性断言；
  11. `test_baseline_snapshot_saved_and_restored_across_instances`：基线快照跨会话/跨实例导出载入不被后续调仓篡改的不变量断言；
  12. `test_200_random_portfolio_rebalance_invariants`：200 轮蒙特卡洛随机极端组合（随机标的、随机调仓、随机净值波动 ±40%、随机现金）强力应力测试；
  13. `test_friction_saving_7day_and_class_c_penalties`：主动风控 <7天 1.50% 惩罚费与 C 类份额 0.50% 赎回费规避精算；
  14. `test_app_gui_brinson_source_code_contract`：前端源码静态契约与 CommonMark 防御核验。

- **实测执行结果**：
  - 运行命令：`py -3 -m pytest tests/test_challenger_g9_m2_adversarial.py -v`
  - 结果：`14 passed in 2.58s`，退出码 0，所有对抗断言 100% 通过。
  - 运行命令：`py -3 -m pytest tests/test_infra.py tests/test_adv_final_closure.py tests/test_g8_ux_and_realtime_fusion.py tests/test_causality_adversarial_m1.py tests/test_challenger_g9_m1_adversarial.py tests/test_challenger_g9_m2_adversarial.py`
  - 结果：`64 passed in 40.16s`，退出码 0，全量回归与四大裁判文件零破坏。

---

## 2. 逻辑链 (Logic Chain)

1. **数学恒等式严格闭合证明**：
   - 理论上，Brinson-Fachler 经典模型满足 $AR + SR = \sum (w_P - w_B)(R_B - R_B^{tot}) + \sum w_P(R_P - R_B) = R_P - R_B = TE$；
   - 代码中通过 `alloc_ratio = AR_raw_sum / TE_raw_sum`，并将金额与百分比残差完全收敛至选基项：`select_yuan = round(total_active_add_yuan - alloc_yuan, 2)` 与 `select_pct = round(total_active_add_pct - alloc_pct, 2)`；
   - 经测试 1、2、3、4 及 200 轮蒙特卡洛随机调仓实证，`abs(allocation_effect_yuan + selection_effect_yuan - total_active_add_yuan) < 1e-4` 与 `abs(allocation_effect_pct + selection_effect_pct - total_active_add_pct) < 1e-4` 在所有测试中 100% 绝对成立，零浮点击穿。

2. **极端边界鲁棒性证明**：
   - 全现金组合（测试 6）：`shadow_equity == current_actual_equity == cash`，`total_active_add_yuan == 0.0`，所有分类归集自动落入“现金管理”，收益率与权重完全对齐，零 KeyError，零除以零；
   - 单一资产组合（测试 5）：单一资产权重为 1.0，全链路无多资产缺失异常，正常产出归因账单；
   - 极限真空组合（测试 7）：资产为 0 时内部各分母夹持 `cur_actual > 0` 与 `shadow_equity > 0` 保护，安全返回 0.0；
   - 基准缺失新大类调入（测试 8）：第 6803 行对 `v_b_init <= 0 and actual_cat_values[cat] > 0` 实施了基准收益对齐，使 $R_B[cat] = R_P[cat]$，从而将选基超额物理隔离为 0，并将主动超配全额计入配置效应，数学模型与实盘逻辑高度严密。

3. **历史契约与基线持久化证明**：
   - 测试 10 验证了 7 个既有键名字段名、数值类型（int/float/str）与结构 100% 保持不变，已有调用方无需任何改动；
   - 测试 11 验证了 `initial_baseline_snapshot` 在导出导入后完整留存，重启后的调仓绝不会冲刷初始接管影子基线，彻底根治了历史复盘数据丢失的缺陷。

---

## 3. 局限与前提假设 (Caveats)

1. **测试范围边界**：本次对抗聚焦于 M2 的 `evaluate_rebalance_audit` 算法与前端渲染，未修改任何生产代码；
2. **基准指数日频行情**：影子组合标的的区间收益率依赖于 `FundHolding.current_nav` 或 `resolve_fund_meta` 反查得到的最新净值，若数据源出现缺失，依赖于系统兜底机制；
3. **No caveats on redlines**：四个裁判文件绝对只读，契约零触碰。

---

## 4. 结论 (Conclusion)

**对抗裁决：APPROVE**

Milestone 2 中关于 Brinson-Fachler 经典归因模型、基线快照持久化及前端三维账单渲染的实现质量卓越：
1. 经受住了 200 轮蒙特卡洛应力测试与各类极限边界探针考验；
2. 数学恒等式在浮点 $10^{-4}$ 精度下绝对平账；
3. 极端边界（全现金、单一资产、新大类调入、全清仓）零除零、零 KeyError；
4. 既有 7 个顶级键名完全向下兼容。
建议 Orchestrator 立即推进至 Milestone 3。

---

## 5. 独立验证方法 (Verification Method)

在工作区根目录执行以下命令即可全量复现本次对抗验证：

```powershell
# 1. 运行 M2 独立对抗验证套件 (14 项对抗断言 + 200 轮蒙特卡洛)
py -3 -m pytest tests/test_challenger_g9_m2_adversarial.py -v

# 2. 运行包含四大裁判文件在内的全量回归套件
py -3 -m pytest tests/test_infra.py tests/test_adv_final_closure.py tests/test_g8_ux_and_realtime_fusion.py tests/test_causality_adversarial_m1.py tests/test_challenger_g9_m1_adversarial.py tests/test_challenger_g9_m2_adversarial.py
```

**期望结果**：
- `test_challenger_g9_m2_adversarial.py`：14 passed；
- 联合回归套件：64 passed；
- 退出代码均为 0。
