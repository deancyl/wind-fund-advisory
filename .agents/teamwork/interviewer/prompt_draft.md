由 4 个专家角色协作完成：Agent-1（核密度条件胜率与存量调仓胜率增益专家）、Agent-2（全市场选基排雷、实时限购拆单与缓存修复专家）、Agent-3（UI 大一统合龙设计师）、Agent-4（红队数学性质与端到端交互验证员）。启动“全市场胜率引擎大一统合龙与当下时点(T_now)核密度条件胜率升级”任务，全面解决当前 market_screener.py、winrate_engine.py、portfolio_optimizer.py、portfolio_manager.py、cache_manager.py、data_loader.py 与 app_gui.py 中的 6 处架构断层与金融逻辑缺陷，并完成自动化测试与服务重启。

Working directory: d:\Google\Workspace\Wind
Integrity mode: [OPEN: 团队行为限制模式]
物理安全红线：严禁触碰只读裁判文件（judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py）

## Verification Resources
- 现有测试套件位于 `tests/` 目录。
- 物理安全红线裁判文件：`judge_engine.py`、`holdout_vault.py`、`AGENT_SPEC.md`、`tests/test_infra.py`（只读，严禁修改）。
- [OPEN: 是否有额外的基准数据集、特定行情切片用例或外部参考实现？]

## Requirements

### R1. 升级为当下时点 ($T_{\text{now}}$) 高斯核同温层条件胜率体系
- 提取截至 `as_of_date (T_now)` 每一天 $t$ 的 5 维市场特征向量 $\mathbf{x}_t = [\text{ERP历史分位}_t, \text{Bias20均线乖离}_t, \text{Mom60动量}_t, \text{EWMA波动率}_t, \text{DR007利差}_t]$。
- 计算每个历史滚动窗口起点 $t \in [1, M]$ 的特征向量 $\mathbf{x}_t$ 与当下时点特征向量 $\mathbf{x}_{T_{\text{now}}}$ 的标准化马氏/欧氏距离 $d_t$，以距离分布的 30% 分位数作为自适应带宽 $h$，计算高斯核权重向量 $\kappa_t = \exp(-d_t^2 / (2h^2)) / \sum_\tau \exp(-d_\tau^2 / (2h^2))$。
- 同时向量化计算并输出两个胜率指标：
  1. 当下时点条件胜率（`conditional_win_rate`，作为优化器核心最大化目标）：$\sum_{t=1}^M \kappa_t \cdot \mathbb{I}(r_{\text{net}, t}(\mathbf{w}) \ge r^*)$；
  2. 历史全周期无条件胜率（`unconditional_win_rate`，作为对照参考）：$\frac{1}{M} \sum_{t=1}^M \mathbb{I}(r_{\text{net}, t}(\mathbf{w}) \ge r^*)$。
- 当用户在当下时点设定的目标年化过高导致最高条件胜率 `< 40%` 时，自动计算并在结果中返回 `feasible_recommendation`（提示在当前市场位置下，将目标年化调整为 X% 或持有期调整为 Y，条件胜率可提升至 75%+）。

### R2. 修正专家精选池基准对比与存量持仓调仓胜率增益算子
- 修正“双轨双池对比”中专家池等权基准错误：专家精选池对比基准必须调用 `StrategyBridge` 在当前对应档位 `mo_tier` 下生成的真实动态策略目标权重（即实际推荐的核心基金及其精确配比），与全市场 AI 选基组合进行同口径公平对比（同时对比两者的当下时点条件胜率、历史全周期胜率、不亏损率与最大回撤）。
- 在存量持仓评估中新增调仓胜率增益算子：实时计算维持当前持仓不动的未来目标条件胜率 `win_rate_keep`，以及按建议调仓后（严格扣除真实赎回费、申购费与 T+2 在途踏空损耗）的净条件胜率 `win_rate_rebal` 与净胜率提升幅度 `delta_win_rate`。

### R3. 全市场最优组合接入排雷反拥挤、实时限购瀑布流拆单与建仓小抄
- 在 `MarketScreener` 评分阶段接入 `screen_fund_look_through_risk()` 与 `get_fund_smart_money_crowding()` 过滤暴雷与极度拥挤标的。
- 对 `WinRateOptimizer` 输出的最优组合强制调用 `fetch_realtime_fund_quota()` 执行多级限购拆单：入选基金分配金额超过其实时 `daily_limit` 时，自动裁剪至 `daily_limit`，超额资金顺延分配给同类型桶排名紧随其后的不限购备选基金（或生成分批定投计划 `dca_plan`）。
- 完整提供《📱 手机银行/天天基金下单一键复制小抄》折叠框与【🚀 一键将此全市场最优组合设为我的初始持仓】按钮（调用 `pm.apply_zero_start_blueprint()` 直接写入持仓账本并重置回撤基准）。
- 在 Tab 1 选择“模式 C：AI全市场胜率最优选基”时内联执行并渲染完整结果与建仓按钮，消除与 Tab 5 的割裂（布局形式：[OPEN: 是否彻底合并为四大核心 Tab，或 Tab 1 与 Tab 5 共用组件]）。

### R4. 重构 Tab 2 调仓建议：接入胜率增益对比并彻底修复双模式联动 Bug
- 在 Tab 2 第一层上方加入【📅 计划持有期（短期 3~6月 / 中期 1~2年 / 长期 3~5年）× 🎚️ 期望年化收益率】控制条，展示维持持仓不动 vs 调仓后扣费净胜率对比结论。
- 彻底修复切换温和/强行调仓模式时表格与执行按钮不变的 Bug：删除调仓表格处对 `generate_ai_rebalance_orders()` 的冗余调用，直接绑定并渲染选定模式的 `cur_sim["items"]`（或 `cur_sim["orders"]`），确保温和模式呈现缓冲保护、强行模式呈现一步到位对齐的买卖金额；【立即按今日盘中估值执行调仓】与【保存为明日盯盘待办预案】按钮严格执行选定模式的调仓路由。

### R5. 修复底层缓存与数据识别缺陷及遵守裁判红线
- 在 `cache_manager.py` 的 `make_winrate_key()` 与 `make_optimizer_key()` 中加入 `as_of_date: str = ""` 参数并拼入 MD5 原串。
- 将 `cache_manager.py` 中 `should_invalidate_winrate()` 的慢速接口替换为 `portfolio_manager.fetch_realtime_index_quote("sh000300")`。
- 修复 `data_loader.py` 中判断纯数字基金代码 A/C 份额类别的逻辑，通过基金简称或 `fund_catalog` 准确识别。
- 严禁触碰只读裁判文件（`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`）。

## Acceptance Criteria

### 条件胜率数学性质与优化器
- [ ] 从历史矩阵中选取 ERP 极高截面与极低超买截面，同一组合在底部时点的 `conditional_win_rate` 显著高于顶部超买时点，且与 `unconditional_win_rate` 区分清晰。
- [ ] 当目标收益率过高导致条件胜率 `< 40%` 时，能正确返回可行的调优建议 `feasible_recommendation`。
- [ ] 专家精选池对比基准使用 `StrategyBridge` 真实动态目标权重，而非全部基金简单等权。

### 限购拆单与组合落盘
- [ ] 全市场选基经过重仓排雷与反拥挤过滤，且输出组合自动完成实时限购拆单。
- [ ] 全市场选基结果可一键调用 `pm.apply_zero_start_blueprint()` 成功落盘写入持仓账本。
- [ ] 提供手机下单小抄，且在 Tab 1 模式 C 内联呈现，无跨页面割裂。

### Tab 2 交互联动与胜率对比
- [ ] Tab 2 顶部展示持有期与期望年化控制条，并正确计算维持持仓不动 vs 调仓扣费后的净胜率及增益值。
- [ ] 切换温和免伤与强行调仓模式时，下方调仓建议表格与执行按钮严格随选定模式实时动态联动变化。

### 底层修复与系统测试
- [ ] `cache_manager.py` 的缓存键包含 `as_of_date`，且行情检查接口使用快速网关报价。
- [ ] `data_loader.py` 准确识别 A/C 份额类别。
- [ ] 只读裁判文件完全未被修改。
- [ ] 全量 pytest 测试套件与 Streamlit AppTest 渲染测试 100% 通过，8501 端口服务成功重启可用。
