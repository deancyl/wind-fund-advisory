## 2026-10-31T15:26:19Z
[Message] timestamp=2026-10-31T15:26:19Z sender=d536f3b8-ee96-41ed-9fa9-cbd10993bb6a priority=MESSAGE_PRIORITY_HIGH content=你是 Agent-3（存量持仓调仓裁决与后果推演专家），专精实现 Milestone 3 (M3)。
你的工作目录是: d:\Google\Workspace\Wind\.agents\teamwork\worker_agent3_orch4
原始需求文件路径 (必读): d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
项目工程蓝图: d:\Google\Workspace\Wind\PROJECT.md
前序勘测报告 (必读，包含代码行号、设计契约与伪代码): d:\Google\Workspace\Wind\.agents\teamwork\explorer_orch4_3\handoff.md
代码项目根目录: d:\Google\Workspace\Wind\AGY2_FundAdvisory

【文件修改范围】
你负责对以下两个文件进行增量扩展与修复：
- `AGY2_FundAdvisory/strategy_bridge.py`
- `AGY2_FundAdvisory/portfolio_manager.py`
严禁触碰只读裁判文件（`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`）。注意：前序 M1 和 M2 的工作已经合入，请在既有代码基础上平滑追加与修改，严禁覆盖或回滚 M1 / M2 的功能。

【MANDATORY INTEGRITY WARNING】
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

【核心实现任务】
依据 ORIGINAL_REQUEST.md §R4 与 explorer_orch4_3/handoff.md 中的指引，完整落地以下三大核心功能：

1. **`StrategyBridge.evaluate_today_rebalance_suitability(pm, active_tier="C3") -> Dict[str, Any]`**:
   - 综合联动 `TradingClock`、`get_latest_market_snapshot` 与 `pm.holdings` 的 FIFO 批次持有天数；
   - 返回标准字典：
     * `verdict_level`: `"SUITABLE"`（🟢 今日适合调仓） / `"HOLD_ON"`（🟡 今日建议按兵不动） / `"FORBIDDEN"`（🔴 今日不宜调仓·高损预警）
     * `verdict_title`: 一句话鲜明结论（如：`🟡 今日建议按兵不动：大盘处于均线震荡噪音带，且您的持仓最大偏离仅 1.2%`）
     * `reasons_4d`: 包含 4 个维度的详细白话字典：
       - `market_position_reason`: 近期行情位置诊断（大盘均线与迟滞带位置解析）
       - `clock_window_reason`: 15:00 交易时钟诊断（交易时间与黄金窗口解析）
       - `deviation_utility_reason`: 偏离度与净效用诊断（最大偏离度与调仓预期净效用解析）
       - `lockup_fee_reason`: FIFO 批次锁定期诊断（7天惩罚期与免赎阶梯解析）
   - 在 `strategy_bridge.py` 底部导出该方法：`evaluate_today_rebalance_suitability = StrategyBridge.evaluate_today_rebalance_suitability`。

2. **`StrategyBridge.simulate_rebalance_modes_and_consequences(pm, active_tier="C3") -> Dict[str, Any]`**:
   - 同时计算并返回两种调仓模式的完整订单列表与四大后果对比数据：
     * `mode_gentle` (模式一：温和免伤调仓): 遵循 3% 免折腾阈值（`min_buffer_pct = 3.0`），仅卖出已满免赎回费期份额（未满7天批次严格安全裁剪保护留存），优先同基金公司转换 `SWITCH`；
     * `mode_forced` (模式二：强行一步到位调仓): 无视 3% 缓冲带（`min_buffer_pct = 0.0`）与持有期限制，强行将所有持仓对齐至今日目标权重，对未满7天份额按 1.5% 真实计提惩罚费；
     * 每个模式下均精确计算 `consequences` 字典（四大后果精算矩阵）：
       1) `fee_loss`: `{"redemption_fee": float, "penalty_fee_7d": float, "subscription_fee": float, "total_fee": float, "payback_days": int}`（精确到每一笔 FIFO 批次的实际持有天数阶梯费率，分厘严格平账）；
       2) `in_transit_risk`: `{"in_transit_amount": float, "in_transit_pct": float, "lock_days": str, "switch_saved_amount": float, "missed_rally_cost_est": float}`（跨公司换仓 T+2/T+4 在途资金空窗期与潜在踏空成本，SWITCH 减免金额）；
       3) `risk_shift`: `{"equity_before": float, "equity_after": float, "vol_before": float, "vol_after": float, "mdd_before": float, "mdd_after": float, "div_yield_before": float, "div_yield_after": float}`；
       4) `lockup_reset`: `{"new_buy_amount": float, "reset_warning_text": str}`（新买入资金重新触发 7 天 1.5% 惩罚锁定期与 A 类免赎期清零提醒）。
   - 在 `strategy_bridge.py` 底部导出该方法：`simulate_rebalance_modes_and_consequences = StrategyBridge.simulate_rebalance_modes_and_consequences`。

3. **修复 `calculate_stock_overlap_matrix()` 重合度豁免逻辑**:
   - 在 `portfolio_manager.py`（约第 3539 行 `EXEMPT_OVERLAP_PAIRS`）中加入策略推荐的双红利底仓对 `frozenset({"100032", "005561"})`（与限购伴生对 `{"050025", "001071"}` 共同纳入豁免池）；
   - 记录豁免说明为 `"策略推荐双红利底仓协同组合 (红利增强 + 红利低波)"`；
   - 准确计算非豁免最大重合度 `max_non_diag_unexcused`（仅统计所有非对角线且未被任何规则豁免的基金对重合度；若为空则返回 0.0）；
   - 在返回字典中返回 `"max_non_diag_unexcused": max_non_diag_unexcused`；
   - 确保当用户持有标准推荐组合（100032 + 005561 + 002351 + 000216 + 050025/001071）时，绝不触发黄色伪分散警告！

【验收与验证要求】
- 编写或运行对 `portfolio_manager.py` 与 `strategy_bridge.py` 的测试（如 `py -3.11 -m pytest tests/test_portfolio_manager.py tests/test_strategy_bridge.py -v`），确认所有测试通过，无语法错误，无反作弊违规。
- 完成后在你的工作目录输出 `handoff.md`，并通过 `send_message` 向父编排者汇报。
