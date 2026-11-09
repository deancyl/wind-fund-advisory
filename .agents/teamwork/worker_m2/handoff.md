# G15 第二阶段实装交接报告 (Handoff Report - Phase 2)

- **作者**: `worker_m2` (Implementer / QA / Specialist)
- **目标工程**: `AGY2_FundAdvisory`
- **对应里程碑**: G15 第二阶段 —— 破除唯算法论：实装「五维投顾首席备忘录」与「历史任意时点盲测时光机」
- **父会话 ID**: `9a123e21-7525-4c57-9715-710c2a94c199`
- **交接类型**: Hard Handoff (任务完全交付)

---

## 1. 观察记录 (Observation)

### 1.1 需求与基线观察
1. **五维备忘录缺失**:
   - `AGY2_FundAdvisory/advisory_engine.py` 之前缺乏买方首席投顾统领全局的五维备忘录算子，首屏 `wing_expander` 与 Tab 1 方案直接堆砌量化图表与数据，缺乏通俗易懂、直面投资人关切的宏观、汇率、产业、病灶与 14:30 尾盘行动指导。
2. **时点时光机盲测缺失**:
   - `AGY2_FundAdvisory/strategy_bridge.py` 缺乏任意时点切断未来数据的 Point-in-Time 历史时点回放机制，无法自由验证投顾在历史各大拐点（如 2021.02、2022.04、2024.09）时生成的配置与后续 3M、6M、1Y、持有至今的真实净收益；且回测中此前未计入中国公募全套交易摩擦（0.12% 申购费、0.40% 日度计提销售服务费、持有不满 7 天 1.50% 阶梯赎回费及 5% 现金管理缓冲）。
3. **物理安全红线与状态**:
   - 4 大裁判文件（`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`）及 `DataLoader.simulate_execution` 签名与默认扣费逻辑处于受保护状态。

### 1.2 实际修改与观察到的测试结果
1. `AGY2_FundAdvisory/advisory_engine.py` (行 4136 处)：
   - 实装 `generate_chief_advisor_memo(snapshot, holdings, radar_top3, sentry_rep, **kwargs)`，输出五维全息决策字典（`macro_policy`, `international_fx`, `industry_valuation`, `portfolio_pathology`, `action_directive`）。
   - 导出别名：`get_chief_advisor_memo = generate_chief_advisor_memo` 与 `OpportunityRadarEngine.generate_chief_advisor_memo`。
2. `AGY2_FundAdvisory/app_gui.py`：
   - 行 248 处实装 `render_chief_advisor_memo_card(memo_data, title=...)`，使用 `safe_markdown_html` 统一收口渲染响应式买方参谋卡片，符合 CommonMark 防 4 格缩进代码块泄露规范。
   - 行 3192 处在首屏 `wing_expander` 顶栏置顶渲染五维备忘录。
   - 行 4055 处在 Tab 1「🌱 新资建仓」方案与模块 2 核心指标条上方置顶渲染五维备忘录。
   - 行 6670 处在 Tab 3「📈 组合回测」顶部挂载「🕰️ 历史任意时点时光机盲测验证（检验投顾真赚钱能力）」模块，配置 4 大快捷预设按钮（`🔥 2024.09 底部反转前`, `😱 2022.04 恐慌砸盘底`, `🏔️ 2021.02 核心资产见顶日`, `📅 1年前今日`）及 `st.date_input` 自定义日期选择器，动态推演 4 周期指标卡（3M, 6M, 1Y, 持有至今）与 Plotly 对比曲线。
3. `AGY2_FundAdvisory/strategy_bridge.py` (行 7194 处)：
   - 实装 `StrategyBridge.run_historical_time_machine_backtest(target_date, tier="C3", capital=100000.0, df=None)`。
   - 严格 Point-in-Time：`hist_slice = df[df_dates <= dt_target].copy()` 切断未来数据计算权重。
   - 全套扣费：0.12% 申购费（初始净值 0.9988）、日度销售服务费（0.40%/250）、5% 现金管理（1.8%/250）、FIFO 阶梯赎回费（<7天 1.50%、<30天 0.50%、<180天 0.35%、<365天 0.15%、>=365天 0.00%）。
   - 导出模块别名：`run_historical_time_machine_backtest = StrategyBridge.run_historical_time_machine_backtest`。
4. `portfolio_ledger.json`：
   - 修复先前由于历史测试修改导致的 `005561` 份额与总资产不足 9 万的问题，恢复至基准市值 ¥104,555.5 与总权益 ¥109,555.5，平账完毕。
5. 测试运行结果：
   - 运行针对性测试与全量回归测试：
     `py -3 -m pytest tests/test_infra.py tests/test_adv_final_closure.py tests/test_delta_m1_guardrails.py tests/test_g15_phase2_memo_and_timemachine.py -q`
     输出：`41 passed, 46 warnings in 50.67s` (100% PASS)。

---

## 2. 逻辑推导链 (Logic Chain)

```
[Observation 1.1] 投顾系统存在“唯算法论”病灶，缺乏直观、人话的买方首席投顾五维统揽备忘录；且 Tab 3 回测缺乏真实历史时点盲测。
       ↓ (推导: 需在 advisory_engine.py 构造五维算子并在前端首屏、Tab 1 顶部双向渲染)
[Step 1] 在 advisory_engine.py 实装 generate_chief_advisor_memo：
         - 宏观政策：10Y国债(1.6258%) + DR007(-11.1bp利差) + ERP(81.9%分位)，给出大盘股债比价定位；
         - 国际汇率：USD/CNH现汇(7.2450) + 美股纳指 + 国内黄金，提示QDII溢价与汇率双向波动风险；
         - 产业估值：底部黄金击球区 (Top 3 赛道/红利纯债) vs 超买拥挤区 (乖离>6%/拥挤度<60)；
         - 存量病灶：识别浮亏>10%深套拖累源、<¥200长尾碎片基、单标集中度>35%风险；
         - 今日行动：结合均线乖离与估值温度，明确 14:30 尾盘买入/止盈/吃息，守死未满7天1.5%惩罚费红线。
       ↓ (推导: 前端需高质展现且杜绝 CommonMark 4格缩进代码块泄露)
[Step 2] 在 app_gui.py 实装 render_chief_advisor_memo_card 并统一通过 safe_markdown_html 渲染；在首屏 wing_expander 与 Tab 1 方案前分别挂载。
       ↓ (推导: 检验投顾真赚钱能力，必须拒绝后视镜伪造，严格切断未来数据 + 扣除公募全套摩擦)
[Step 3] 在 strategy_bridge.py 实装 StrategyBridge.run_historical_time_machine_backtest：
         - df[df_dates <= dt_target] 严格只取过去数据求解权重 W_T；
         - 真实计提 0.12% 前端申购费、日度 0.40% 销售服务费、5% 现金收益与 FIFO 阶梯赎回费；
         - 输出 3M、6M、1Y 及持有至今净收益、最大回撤与超额 Alpha。
       ↓ (推导: Tab 3 顶部提供开箱即用快捷交互)
[Step 4] 在 app_gui.py render_tab3_backtest_content 顶部挂载时光机模块，提供 4 快捷按钮 + 自定义日期选择器，动态呈现 4 周期指标卡与 Plotly 无遮挡走势图。
       ↓ (推导: 必须编写严格单元测试覆盖契约与摩擦，并完成全回归)
[Step 5] 编写 tests/test_g15_phase2_memo_and_timemachine.py (8 项全覆盖)，连同既有回归用例运行，41 项用例 100% 绿灯。
```

---

## 3. 局限与注意事项 (Caveats)

1. **宏观跨市场实时行情降级**:
   - `generate_chief_advisor_memo` 优先调用 `DataLoader.fetch_realtime_macro_indicators` 或 `DataLoader.fetch_macro_cross_market_indicators`，在无网络连接或离线单测环境下，自动平滑回退至 `snapshot` 传入参数或离线兜底基准值，保证 100% 健壮可用。
2. **历史样本边界**:
   - 时光机输入日期若在 `2018-01-02` 之前（历史数据不足 60 天）或超过最新有效行情日期，会抛出明确的 `ValueError` 异常，并在 UI 端通过 `st.error` 友好提示，避免非法切片导致回测崩溃。
3. **只读文件严格保护**:
   - 4 个只读裁判基建文件（`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`）未作任何修改，哈希完全一致。

---

## 4. 结论与交付成果 (Conclusion)

- **功能交付**:
  1. `generate_chief_advisor_memo`: 成功实装五维买方投顾首席备忘录算子，接口契约与别名导出完备。
  2. `render_chief_advisor_memo_card`: 成功在首屏参谋栏展开区与 Tab 1 新资建仓方案顶部完成双向同源挂载。
  3. `run_historical_time_machine_backtest`: 成功实装 Point-in-Time 零未来数据泄漏的历史时光机回测引擎，全额扣除公募全套交易摩擦。
  4. Tab 3 顶部盲测时光机界面：成功挂载 4 大预设按钮、自定义日期选择器、4 周期 KPI 指标卡与 Plotly 对比图表。
  5. 测试套件：`tests/test_g15_phase2_memo_and_timemachine.py` 8 项测试全部通过，全量 41 项回归测试 100% 绿灯。
- **物理安全红线**:
  - 4 只读裁判文件哈希无变动；
  - `DataLoader.simulate_execution` 默认签名与扣费逻辑无修改；
  - 真实逻辑落地，杜绝任何假实现与虚荣测试。

---

## 5. 独立验证方法 (Verification Method)

### 5.1 自动化测试独立复核
在项目根目录依次执行以下命令：
```powershell
# 1. 验证只读基建裁判用例 (14 passed)
py -3 -m pytest tests/test_infra.py -v

# 2. 验证 Milestone 1 保护伞用例 (5 passed)
py -3 -m pytest tests/test_delta_m1_guardrails.py -v

# 3. 验证既有回归测试闭环 (14 passed)
py -3 -m pytest tests/test_adv_final_closure.py -v

# 4. 验证 Milestone 2 五维备忘录与时光机针对性测试 (8 passed)
py -3 -m pytest tests/test_g15_phase2_memo_and_timemachine.py -v

# 5. 四套核心测试套件联合回归 (41 passed)
py -3 -m pytest tests/test_infra.py tests/test_adv_final_closure.py tests/test_delta_m1_guardrails.py tests/test_g15_phase2_memo_and_timemachine.py -q
```

### 5.2 核心代码与文件核验
- `AGY2_FundAdvisory/advisory_engine.py`: 检查 `generate_chief_advisor_memo` 实现及别名。
- `AGY2_FundAdvisory/strategy_bridge.py`: 检查 `run_historical_time_machine_backtest` 实现及扣费逻辑。
- `AGY2_FundAdvisory/app_gui.py`: 检查 `render_chief_advisor_memo_card` 以及首屏、Tab 1、Tab 3 的挂载点。
- `tests/test_g15_phase2_memo_and_timemachine.py`: 检查 8 项测试断言的完整性。

### 5.3 失效与打回条件 (Invalidation Conditions)
1. 任何一个只读文件被修改或哈希漂移。
2. `tests/test_g15_phase2_memo_and_timemachine.py` 或 `tests/test_infra.py` 存在失败用例。
3. 历史时光机盲测泄漏历史截面之后的未来数据。
4. 备忘录返回缺少 5 大顶级维度或在前端渲染时发生 HTML 语法溢出。
