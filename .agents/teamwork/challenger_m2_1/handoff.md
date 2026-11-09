# G15 第二阶段实证质询报告 (Milestone 2 Challenger Handoff Report)

- **质询代理**: `challenger_m2_1` (Critic / Specialist)
- **质询对象**: G15 第二阶段（Phase 2）「破除唯算法论：实装五维投顾首席备忘录与历史任意时点盲测时光机」
- **父会话 ID**: `9a123e21-7525-4c57-9715-710c2a94c199`
- **交接类型**: Hard Handoff (审查完全交付)
- **终审定性裁决**: **`APPROVE` (通过)**

---

## 1. 观察记录 (Observation)

### 1.1 物理安全红线核验 (Zero Tolerance Redlines)
1. **4 只读裁判文件**:
   - `git status --porcelain judge_engine.py holdout_vault.py AGENT_SPEC.md tests/test_infra.py AGY2_FundAdvisory/data_loader.py` 命令输出为空，确认 100% 保持未修改。
   - 执行 `py -3 -m pytest tests/test_infra.py -v`：
     ```
     tests/test_infra.py::test_data_loader_matrix_alignment PASSED            [  7%]
     tests/test_infra.py::test_simulation_operator_friction PASSED            [ 14%]
     tests/test_infra.py::test_causal_probe_detects_leakage PASSED            [ 21%]
     tests/test_infra.py::test_four_islands_conformity PASSED                 [ 28%]
     tests/test_infra.py::test_holdout_vault_quota_limit PASSED               [ 35%]
     tests/test_infra.py::test_judge_engine_rejects_bond_arbitrage PASSED     [ 42%]
     tests/test_infra.py::test_simulation_initial_position_penalty PASSED     [ 50%]
     tests/test_infra.py::test_judge_engine_rf_deduction PASSED               [ 57%]
     tests/test_infra.py::test_judge_engine_rejects_slice_bond_arbitrage PASSED [ 64%]
     tests/test_infra.py::test_judge_engine_rejects_offshore_overweight PASSED [ 71%]
     tests/test_infra.py::test_judge_engine_rejects_low_ashare_equity PASSED  [ 78%]
     tests/test_infra.py::test_judge_engine_rejects_low_cagr PASSED           [ 85%]
     tests/test_infra.py::test_judge_engine_rejects_bull_slice_lag PASSED     [ 92%]
     tests/test_infra.py::test_islands_empty_df_robustness PASSED             [100%]
     ============================= 14 passed in 6.24s ==============================
     ```
2. **`DataLoader.simulate_execution` 签名与扣费锁定**:
   - 查看 `AGY2_FundAdvisory/data_loader.py` 第 1437 行，签名保持 `simulate_execution(weights_df, prices_df, is_otc=True, penalty_days=7, penalty_rate=0.015, etf_impact=0.001)`，默认参数及惩罚费逻辑无任何篡改。

### 1.2 `generate_chief_advisor_memo` 源码与极端边界质询观察
1. **代码审查定位**:
   - `AGY2_FundAdvisory/advisory_engine.py` 第 4137 行至 4341 行实装 `generate_chief_advisor_memo`。
   - 返回 5 个固定顶级维度（`macro_policy`, `international_fx`, `industry_valuation`, `portfolio_pathology`, `action_directive`），每个维度均提供 `title`, `badge`, `content`。
2. **极端与异常边界输入实证**:
   - None / 空输入：在 `snapshot=None, holdings=None, radar_top3=None, sentry_rep=None` 下正常生成完整降级字典，无任何 KeyError 或 TypeError。
   - 负流动性利差：传入 `dr007_spread_bp = -150.0`，正确映射为 `🟢 货币宽松充裕`。
   - 利率倒挂 / 极端低利率：传入 `treasury_10y = -0.15%`，格式化渲染正常不崩溃。
   - ERP 极端分位：实测 0.0%、34.9%、35.0%、50.0%、74.9%、75.0%、100.0% 七档区间，在 0%~35% 正确归类为【高估谨慎区】，在 75%~100% 正确归类为【极高性价比黄金击球区】。
   - 深套多标的排序：传入 -80%、-50%、-15% 浮亏标的，按绝对亏损金额精确识别最大拖累源为 -80% 标的，并在报告中呈现。
   - 25 只长尾碎片基：传入 25 笔小于 ¥200 的碎片持仓，正确统计 `frag_count = 25` 并准确累加清扫金额，触发 `🧹 长尾碎片尾仓` 诊断。
   - 单标超集中：传入第一大重仓 95% 占比，正确触发 `⚠️ 单标集中度过高：第一大重仓占比达 95.0%`。
   - 异构持仓格式兼容：传入 `dict of dicts`、`list of objects` 以及 Tab 1 纯浮点权重字典 `{"005561": 0.40, ...}`，算子均自适应识别并平滑回退，0 报错。
   - 前端卡片渲染：`render_chief_advisor_memo_card` 对 None、空字典及极端输入均能 0 异常返回并通过 `safe_markdown_html` 纯化渲染。

### 1.3 `StrategyBridge.run_historical_time_machine_backtest` 源码与摩擦扣费实证观察
1. **代码审查定位**:
   - `AGY2_FundAdvisory/strategy_bridge.py` 第 7194 行至 7351 行实装 `run_historical_time_machine_backtest`。
2. **Point-in-Time 零未来数据泄漏（未来数据投毒测试）**:
   - 测试方法：在真实全收益矩阵中选定 `target_date = 2022-04-26`，运行基准回测获取 `weights_clean`；随后拷贝数据矩阵，将 `target_date` 之后所有资产价格恶意篡改放大 100 倍（+999.0），再次运行回测获取 `weights_corrupted`。
   - 实证结果：`weights_clean` 与 `weights_corrupted` 差异小于 `1e-12`，实证证明未来数据变化对截面 T 的权重决策影响绝对为 0。
3. **交易摩擦与费用扣除实证**:
   - 前端申购费：第 0 日（起点）策略净值严格初始化为 `1.0 * (1 - 0.0012) = 0.9988`（基准为 1.0）。
   - 日度销售服务费与现金缓冲：将未来价格完全冷冻（日收益率 0.0%），实测每日策略净值缩减比例严格等于：
     $$0.05 \times \frac{0.018}{250} - 0.5 \times \frac{0.0040}{250} = -0.0000044/\text{天}$$
     实测 `day_ratio` 与理论预期值误差 $< 10^{-8}$。
   - 5 档 FIFO 阶梯赎回费严格对齐：
     * $< 7$ 天：1.50%
     * $< 30$ 天：0.50%
     * $< 180$ 天：0.35%
     * $< 365$ 天：0.15%
     * $\ge 365$ 天：0.00%
     在 2021-02-18、2022-04-26、2024-09-18 历史拐点回放中，到手收益率 `net_return_pct` 均严格由 `gross_nav * (1.0 - red_fee)` 精确推导。
4. **基准曲线真实跟踪**:
   - 沪深300基准：`h300_nav` 末期累计值与 `fwd_slice['H00300']` 实际价格变动完全一致（误差 $< 10^{-4}$）。
   - 50/50基准：同源跟踪 `BENCHMARK_50_50` 或 `0.5*H00300 + 0.5*H11009`。
5. **边界异常校验**:
   - 历史样本不足 60 天（如传入 2018-01-05）：抛出 `ValueError("所选历史时点 ... 前历史样本不足 60 天...")`。
   - 前推样本不足 2 天（如传入 2028-12-31）：抛出 `ValueError("所选历史时点 ... 缺乏前推回测样本。")`。
   - 日期类型兼容性：传入 `str`, `pd.Timestamp`, `datetime.date`, `datetime.datetime` 均返回完全相同的权重与净值。

### 1.4 自动化实证测试套件运行结果
编写专用对抗测试套件 `tests/test_challenger_m2_adversarial.py`（24 项独立用例）：
```powershell
py -3 -m pytest tests/test_challenger_m2_adversarial.py -v
```
**结果**: `24 passed in 21.95s` (100% PASS, 0 warning)。

运行包含裁判、既有闭环与全阶段 M2 的联合测试：
```powershell
py -3 -m pytest tests/test_infra.py tests/test_delta_m1_guardrails.py tests/test_adv_final_closure.py tests/test_g15_phase2_memo_and_timemachine.py tests/test_challenger_m2_adversarial.py -q
```
**结果**: `65 passed, 34 warnings in 50.13s` (100% PASS)。

---

## 2. 逻辑推导链 (Logic Chain)

```
[Observation 1.1] 4 只读裁判文件与 DataLoader.simulate_execution 哈希与签名未变，test_infra 14项全过。
       ↓ (推理: 物理安全红线零触碰，裁判基建完全受保护)
[Observation 1.2] generate_chief_advisor_memo 经受住 None、负利差、负利率、ERP极限边界、深套多标的、25只长尾碎片、95%超高集中度及异构数据结构测试，0 异常且维度结构完整。
       ↓ (推理: 首席备忘录算子具备工业级鲁棒性，首屏与 Tab 1 挂载安全可靠)
[Observation 1.3] 历史时光机在未来数据投毒测试下 weights_at_t 绝对不变；且真实扣除 0.12% 申购费、日度服务费与 5 档 FIFO 阶梯赎回费。
       ↓ (推理: 盲测时光机严格遵守 Point-in-Time 零未来函数铁律，彻底杜绝“后视镜唯算法论”，回测净值具备实盘可兑现性)
[Observation 1.4] 增量 8 项测试 + 对抗 24 项测试 + 全量 65 项回归测试 100% 绿灯。
       ↓ (推理: 无功能缺陷，无回归破坏，满足交付验收标准)
[Conclusion] 裁定 APPROVE。
```

---

## 3. 局限与注意事项 (Caveats)

1. **外部自定义数据集列名约定**:
   - `run_historical_time_machine_backtest` 默认调用 `StrategyBridge.load_matrix()`。若外部测试传入自定义 `df`，该数据集应包含全收益矩阵的标准大盘基准列（如 `H00922`, `H00300`, `H11009`, `STAR50_STITCH` 等），因底层策略流派会基于该基准列提取宏观与动量特征。若缺失此类基准列会抛出 `KeyError`。实际生产环境中统一由 `DataLoader` 对齐矩阵输出，不存在缺失隐患。
2. **离线与实时宏观指标切换**:
   - 备忘录中汇率与外盘指标优先尝试调用 `DataLoader.fetch_realtime_macro_indicators`，离线环境下平滑使用 `snapshot` 兜底常数。

---

## 4. 结论与终审裁决 (Conclusion)

- **终审定性裁决**: **`APPROVE` (通过)**
- **裁决理由**:
  1. **零红线触碰**: 4 个只读裁判文件与执行算子签名 100% 保持锁定，`tests/test_infra.py` 14 项全绿。
  2. **备忘录鲁棒性满分**: `generate_chief_advisor_memo` 在全套极端宏观指标、极端亏损、碎片尾仓与异构数据输入下 0 报错，产出结构完备的五维全息买方建议。
  3. **时光机纯正 PIT**: 通过未来数据投毒实证，证明截面权重对未来数据完全绝缘；公募全套交易摩擦（0.12% 申购、日服务费、FIFO 5 档阶梯赎回）精确计提。
  4. **实证测试闭环**: 增量与对抗测试 32 项、全回归 65 项用例 100% 绿灯。

---

## 5. 独立复核验证方法 (Verification Method)

在项目工作区根目录下执行以下命令即可复现全部质询与回归结果：

```powershell
# 1. 验证只读基建裁判测试 (14 passed)
py -3 -m pytest tests/test_infra.py -v

# 2. 运行 Milestone 2 核心针对性测试 (8 passed)
py -3 -m pytest tests/test_g15_phase2_memo_and_timemachine.py -v

# 3. 运行 Milestone 2 专职对抗质询测试套件 (24 passed)
py -3 -m pytest tests/test_challenger_m2_adversarial.py -v

# 4. 全量五大核心套件联合回归验证 (65 passed)
py -3 -m pytest tests/test_infra.py tests/test_delta_m1_guardrails.py tests/test_adv_final_closure.py tests/test_g15_phase2_memo_and_timemachine.py tests/test_challenger_m2_adversarial.py -q
```
