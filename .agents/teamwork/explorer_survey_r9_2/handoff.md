# Handoff Report — Phase 0 Technical Survey (R3, R4, R7)

## 1. Observation
1. **R3 前端与后端断层点**：
   - 文件 `AGY2_FundAdvisory/app_gui.py`：
     - 第 4362~4365 行：缓存键 `cur_pool_sig = (chosen_target_pool, tuple(sorted(tier_target_w.items())))` 完全不包含场景模式和资金输入；
     - 第 4376~4384 行：`StrategyBridge.simulate_rebalance_modes_and_consequences` 调用中未传入 `scenario_mode`、`new_cash_amount`、`withdraw_cash_amount`、`freeze_reserved_cash`、`core_anchor_code`；
     - 第 4403~4450 行：场景选择控件 `rad_tab2_scenario_mode` 与新增/提现资金输入框位于模拟推演执行代码之后；
     - 第 4582~4592 行：`StrategyBridge.generate_ai_rebalance_orders` 调用中同样未传入场景参数，且 `available_cash` 未扣减 `pm.reserved_batch_cash`。
   - 文件 `AGY2_FundAdvisory/strategy_bridge.py`：
     - 第 3626~3750 行：`generate_ai_rebalance_orders` 计算每只基金动作时，直接使用 `diff_w = t_w - c_w`，在 `new_cash_only` 时对超配标的生成 `action = "SELL"`，在 `withdraw_cash_only` 时对欠配标的生成 `action = "BUY"`，未遵循场景约束；
     - 第 6140~6680 行：`simulate_rebalance_modes_and_consequences` 内部 `_simulate_single_mode` 忽略 `kwargs.get("scenario_mode")`，固定计算存量卖出摩擦账单。
   - 文件 `AGY2_FundAdvisory/portfolio_manager.py`：
     - 第 6232~6600 行：`generate_scenario_rebalance_plan` 已经完整实现了四大场景底层数学逻辑与红线拦截（`new_cash_only` 零卖出零赎回费，`withdraw_cash_only` 零买入且通过 `get_penalty_free_redeemable_shares` 排除 `<7` 天标的）。

2. **R4 硬编码与假文案**：
   - 文件 `AGY2_FundAdvisory/app_gui.py`：
     - 第 5142 行：`<b>【实盘胜率启示】</b>历史 3 次高度相似情景中，后 60 交易日策略平均胜率达 <b>100.0%</b>，平均绝对收益 <b>+8.5%</b>，明显战胜纯宽基基准。<br>` 中 `100.0%` 与 `+8.5%` 为写死常数。
     - 第 5165 行：3 张卡片底部均写死同一句模板文案 `💡 历史镜鉴意义：高股息与纯债底仓有效缓冲市场剧震，并在右侧反弹中实现超额Alpha。`。
   - 探针运行结果（`py -3` 执行 `StrategyBridge.find_historical_analogs(top_k=3)`）：
     - Match 1 (2024-01-30): `strat_60d=+14.33%`, `h300_60d=+12.00%`, `mdd_60d=-2.62%`（双涨共振）；
     - Match 2 (2023-09-14): `strat_60d=-2.85%`, `h300_60d=-10.37%`, `mdd_60d=-4.52%`（逆势抗跌跑赢 +7.52%）；
     - Match 3 (2022-04-07): `strat_60d=-1.38%`, `h300_60d=+6.20%`, `mdd_60d=-3.06%`（急跌反抽防守落后 -7.58%）；
     - 真实统计：相对超额胜率 66.7%（非 100%），平均相对超额 +0.76%，策略平均绝对收益 +3.37%（非 +8.5%），平均最大回撤 3.40%。

3. **R7 预警哨折叠与紧凑布局**：
   - 文件 `AGY2_FundAdvisory/advisory_engine.py`：
     - 第 702~726 行：未满 7 天锁仓对每只标的逐个生成预警，多只触发时产生多张独立红牌卡片。
   - 文件 `AGY2_FundAdvisory/app_gui.py`：
     - 第 2030~2073 行：无高度限制滚动容器，竖向拉长界面；按钮仅对单个标的加入 `st.session_state.tab2_locked_funds`。

## 2. Logic Chain
1. 从 Observation 1.1 可知，`app_gui.py` 界面上虽然提供了 4 种调仓意图单选框与现金输入框，但由于位置滞后于缓存判断与模拟计算，且缓存签名未收录这些参数，导致用户切换场景或修改金额时，前端根本不重新调用计算或仍使用旧缓存。
2. 从 Observation 1.2 可知，`generate_ai_rebalance_orders` 虽生成了 `pm_plan`，却废弃了其中的 `buy_actions` 与 `sell_actions`，回退为机械的偏离度直接计算，因此在 `new_cash_only` 下产生卖出、在 `withdraw_cash_only` 下产生买入，与用户意图彻底相悖。
3. 从 Observation 2.1 与 2.2 可知，Tab 3 顶部横幅胜率 100% 和收益 +8.5% 是人工编造的迎合性假文案；真实数据计算表明实际胜率为 66.7%、收益为 +3.37%，且 3 个历史匹配切片刚好分别对应“右侧顺势共振”、“逆势抗跌护盾”、“防守底仓代价”三大典型市场归因。
4. 从 Observation 3.1 与 3.2 可知，预警哨缺乏同维度聚合逻辑，导致同类预警重复霸屏，且缺乏一键批量保护入口；外层缺少 `max-height: 320px; overflow-y: auto` 滚动容器。

## 3. Caveats
1. 未涉及 R1/R2（多账本存储与跨 Tab 贯通）、R5（Tab 4 穿透与资产分类）、R6（14 赛道雷达真实净值序列指标），这些由其他调研/实施任务负责。
2. 本调研为只读审计，未直接修改任何业务源文件。
3. 单元测试 `tests/test_anticheat_full_closure.py` 等依赖特定单标的预警标题，因此 `ActiveRiskSentry` 的聚合逻辑建议采用前端聚合或显式参数聚合，保持原始 `alerts` 字段兼容性。

## 4. Conclusion
1. **R3 可行且路径清晰**：调整 `app_gui.py` 场景组件顺序，补全缓存签名；将 `generate_ai_rebalance_orders` 和 `simulate_rebalance_modes_and_consequences` 真正接入 `pm.generate_scenario_rebalance_plan` 的买卖指令结果。
2. **R4 具备 100% 真实替换条件**：清除硬编码字面量，接入实测 4 大指标公式（相对超额胜率、平均相对超额、策略绝对收益、平均最大回撤），并针对 3 个历史切片真实收益关系分别渲染 3 类独立归因文案。
3. **R7 改造方案完全成熟**：在 `ActiveRiskSentry` 增设聚合方法，前端增加 `st.container(height=320)` 并支持一键批量写入 `tab2_locked_funds`。

## 5. Verification Method
1. **R3 验证**：
   - 编写专项测试脚本，以 `scenario_mode="new_cash_only"` 调用 `StrategyBridge.generate_ai_rebalance_orders`，断言所有 sell amount 均为 0，buy amount 之和严格等于 `new_cash_amount`；
   - 以 `scenario_mode="withdraw_cash_only"` 调用，断言所有 buy amount 均为 0，sell amount 之和严格等于 `withdraw_cash_amount` 且不含 `<7` 天标的；
   - 验证 `freeze_reserved_cash=True` 时扣除预留资金。
2. **R4 验证**：
   - 运行 AST 静态扫描，断言 `app_gui.py` Tab 3 中不再包含硬编码字符串 `"100.0%"` 与 `"+8.5%"`；
   - 调用 `_cached_find_historical_analogs(top_k=3)`，验证计算出的胜率与超额与横幅显示一致，且 3 张卡片的镜鉴文案互不相同。
3. **R7 验证**：
   - 构造包含 2 只以上 `<7` 天标的的持仓传入 `ActiveRiskSentry`，验证聚合卡片包含前 2 只名称及总只数；
   - 模拟点击批量锁定按钮，验证 `st.session_state.tab2_locked_funds` 包含全部对应代码。
4. **全量基线**：
   - 运行 `py -3 -m pytest tests/test_infra.py`，确认 14 项基线测试 100% 通过且裁判文件 SHA256 完好。
