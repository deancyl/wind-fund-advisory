## 2026-10-31T14:30:10Z
[Message] timestamp=2026-10-31T14:30:10Z sender=d536f3b8-ee96-41ed-9fa9-cbd10993bb6a priority=MESSAGE_PRIORITY_HIGH content=你是 explorer_orch4_3 (Suitability and Test Explorer)。
你的工作目录是: d:\Google\Workspace\Wind\.agents\teamwork\explorer_orch4_3
原始需求文件路径 (必读): d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
代码项目根目录: d:\Google\Workspace\Wind\AGY2_FundAdvisory

【核心任务】
针对阶段一重构需求中的 R4（今日调仓适宜度裁决器与强行调仓四大后果推演器、双红利底仓协同豁免）与 R5（红队单元测试与断言覆盖），对 AGY2_FundAdvisory/strategy_bridge.py、portfolio_manager.py 以及 tests/ 目录进行深度只读勘测分析，为后续 Agent-3 与 Agent-4 的实现提供准确的证据链、代码行号、接口契约与测试设计方案：

1. 必须首先阅读 d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md，掌握全部任务背景与安全红线（严禁触碰、修改或解锁系统只读裁判文件 judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py；严禁在前端打猴子补丁；严禁使用硬编码字典应付测试）。
2. 勘测调仓适宜度与四大后果推演现状与设计方案（针对 Agent-3 范围）：
   - `StrategyBridge.evaluate_today_rebalance_suitability(pm, active_tier="C3") -> Dict[str, Any]`：
     * 应如何评估并返回 `verdict_level`（"SUITABLE" | "HOLD_ON" | "FORBIDDEN"）与 `verdict_title`？
     * `reasons_4d` 字典的 4 个维度白话解析如何从已有状态（如大盘均线位置、15:00时钟窗口、持仓偏离度与净效用、FIFO批次锁定期）中提取与量化？
   - `StrategyBridge.simulate_rebalance_modes_and_consequences(pm, active_tier="C3") -> Dict[str, Any]`：
     * 如何生成 `mode_gentle`（温和免伤调仓：仅卖出已免赎回费份额、优先同公司 SWITCH、遵循 3% 阈值）？
     * 如何生成 `mode_forced`（强行一步到位调仓：无视 3% 缓冲与持有期，强行对齐目标权重）？
     * `consequences` 字典的四大维度如何精确计算：
       1) `fee_loss`: redemption_fee, penalty_fee_7d, subscription_fee, total_fee, payback_days (基于每笔 FIFO 批次实际持有天数阶梯费率)；
       2) `in_transit_risk`: in_transit_amount, in_transit_pct, lock_days, switch_saved_amount, missed_rally_cost_est；
       3) `risk_shift`: equity_before, equity_after, vol_before, vol_after, mdd_before, mdd_after, div_yield_before, div_yield_after；
       4) `lockup_reset`: new_buy_amount, reset_warning_text。
   - `calculate_stock_overlap_matrix()` 豁免逻辑：
     * 检查当前 `portfolio_manager.py` 中的 `calculate_stock_overlap_matrix()` 实现。
     * 如何将双红利对 `{"100032", "005561"}` 与限购伴生对 `{"050025", "001071"}` 纳入组合协同豁免池，并在计算 `max_non_diag_unexcused` 时排除，确保标准推荐组合不产生黄色伪分散警告？
3. 勘测测试架构与红队断言规划（针对 Agent-4 范围）：
   - 检查 `tests/` 目录现有测试结构，如何运行测试？
   - 确认 4 个系统只读裁判文件的状态：`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`（绝对严禁触碰！）。
   - 为 R1~R4 各项需求规划完整的单元测试与端到端测试用例设计，涵盖边界、极端情况（如限购断网回退缓存、QDII估值偏差覆盖、三段式攻防仓位划拨、四维裁决与四大后果量化校验）。
4. 注意事项：你是只读探索者，严禁修改任何代码。将勘测分析、代码定位、计算逻辑与测试设计详细写入你的工作目录下的 handoff.md，完成后通过 send_message 向父编排者汇报。
