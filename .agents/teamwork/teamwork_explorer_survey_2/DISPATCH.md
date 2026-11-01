## 2026-10-31T23:32:19Z
你是一名代码探索专家（teamwork_explorer）。
你的工作目录是：d:\Google\Workspace\Wind\.agents\teamwork\teamwork_explorer_survey_2\
你必须严格遵守只读调查原则，只在你的工作目录下写入 metadata/报告文件，不要修改任何源码。

【必读文件】：
1. d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md（尤其是 Follow-up — 2026-10-31T23:29:05Z 阶段二重构要求以及阶段一背景）
2. d:\Google\Workspace\Wind\AGY2_FundAdvisory\strategy_bridge.py
3. d:\Google\Workspace\Wind\AGY2_FundAdvisory\portfolio_manager.py
4. d:\Google\Workspace\Wind\AGY2_FundAdvisory\data_loader.py

【调查任务】：
1. 深入调研阶段一已实现的后端量化算法与数据接口，弄清在 `app_gui.py` 中如何完整装配调用：
   - `StrategyBridge.evaluate_today_rebalance_suitability(pm, active_tier)`：
     - 函数入参与返回值结构（`verdict_level`: SUITABLE/HOLD_ON/FORBIDDEN, `verdict_title`, `reasons_4d` 的 4 个字段具体键名与含义：`market_position_reason`, `clock_window_reason`, `deviation_utility_reason`, `lockup_fee_reason`）。
   - `StrategyBridge.simulate_rebalance_modes_and_consequences(pm, active_tier)`：
     - 函数入参与返回值结构（`mode_gentle`, `mode_forced` 各自包含什么，`orders` 结构，`consequences` 中的 4 大后果：`fee_loss`, `in_transit_risk`, `risk_shift`, `lockup_reset` 字段及其类型与格式化要求）。
   - `portfolio_manager.py` 中的 `generate_zero_start_blueprint(total_amount, tier)` 与 `fetch_realtime_fund_quota(fund_code)`：
     - `blueprint["items"]` 中的第 9 列 `实操分红与限购指引`（`action_guide`）如何动态生成（如 `现金分红·今日限额¥500`、`承接超额·不限购正常买`），以及全赛道限购溢出时的 `dca_plan` 字段结构。
   - 顶部 4 张大宽卡所需的数据接口：
     - 卡片 1（交易时钟与窗口）：当前时钟状态、15:00 申赎成交规则、距下次常规网格日 X 天（如何计算/获取）。
     - 卡片 2（市场定调与攻防线）：定调名称、沪深300现价、MA20/MA60、双向触发点位 `📈破 4,141 进攻 ｜ 🛡️跌 3,846 防守`（带施密特迟滞上下轨）。
     - 卡片 3（估值与资金面温度）：ERP 分位数、DR007、期权 IV、IC 贴水率在 `get_latest_market_snapshot()` 或其它函数中的获取方式。
     - 卡片 4（我的总资产与今日预估）：总资产计算、今日预估收益（`pm.get_portfolio_summary()`）。
   - 检查 `calculate_stock_overlap_matrix()` 在 Tab 3 中的调用方式及重合度豁免机制。
2. 在 `d:\Google\Workspace\Wind\.agents\teamwork\teamwork_explorer_survey_2\handoff.md` 输出详细的后端接口契约与前端对接伪代码说明。
3. 并在完成后通过 send_message 发送完成通知给父 agent。
