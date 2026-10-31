## 2026-10-31T15:48:06Z
你是 Agent-4（红队反作弊与单元测试员），专精实现 Milestone 4 (M4)。
你的工作目录是: d:\Google\Workspace\Wind\.agents\teamwork\worker_agent4_orch4
原始需求文件路径 (必读): d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
项目工程蓝图: d:\Google\Workspace\Wind\PROJECT.md
前序勘测报告与测试用例设计表 (必读): d:\Google\Workspace\Wind\.agents\teamwork\explorer_orch4_3\handoff.md
各专家交接报告:
- Agent-1 (M1): d:\Google\Workspace\Wind\.agents\teamwork\worker_agent1_orch4\handoff.md
- Agent-2 (M2): d:\Google\Workspace\Wind\.agents\teamwork\worker_agent2_orch4\handoff.md
- Agent-3 (M3): d:\Google\Workspace\Wind\.agents\teamwork\worker_agent3_orch4\handoff.md
代码项目根目录: d:\Google\Workspace\Wind\AGY2_FundAdvisory

【文件修改范围】
你独占拥有: `AGY2_FundAdvisory/tests/` 目录。
严禁触碰、修改或解锁系统只读裁判文件：
- `judge_engine.py`
- `holdout_vault.py`
- `AGENT_SPEC.md`
- `tests/test_infra.py`

【MANDATORY INTEGRITY WARNING】
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

【核心实现任务】
依据 ORIGINAL_REQUEST.md §R5 与 explorer_orch4_3/handoff.md §4.2 中的规划，在 `AGY2_FundAdvisory/tests/test_milestone_phase1_r1_r5.py` 中编写完整、严密的自动化测试套件，全面覆盖以下 11 个红队断言用例：

1. `test_case_01_read_only_invariants`: 4 大系统裁判基建文件只读与防篡改验证，断言其未被修改。
2. `test_case_02_ast_no_cheating`: AST 静态扫描，断言核心代码中无 `time.sleep`，无硬编码日历年份，前端无猴子补丁，无硬编码 daily_limit 为 500 或 1000。
3. `test_case_03_realtime_quota_fetch_and_cache`: `fetch_realtime_fund_quota` 真实返回值断言，包含 `is_limited`, `daily_limit`, `status`；mock 断网时正确回退读取最近有效缓存文件。
4. `test_case_04_waterfall_quota_split_and_dca`: 瀑布流拆单算法边界测试。当首选基金限额 1000 时，断言首选仅买 1000，`action_guide` 动态包含单日限额且无硬编码字样；备选基金承接超额；若均限额则断言生成 `dca_plan`，定投天数与金额精确平账。
5. `test_case_05_qdii_intraday_valuation_correction`: QDII 估值纠偏测试。偏差 <= 1.5% 时保持原样；偏差 > 1.5% 时（如估值 -4.92% vs 基准 +1.0%），自动按基准 * 0.95 覆盖纠偏，`valuation_corrected` 为 True。
6. `test_case_06_dynamic_tier_weights_no_c3_hijack`: C1~C5 动态权重测试。断言 C3 返回值并非静态常数 `[0.38, 0.30, 0.14, 0.12, 0.06]`，权重和为 1.0，随市场动态演进，满足权益风险预算单调性 $\text{Equity}(C1) < \text{Equity}(C2) < \text{Equity}(C3) < \text{Equity}(C4) < \text{Equity}(C5)$。
7. `test_case_07_three_stage_offensive_defensive`: 三段式攻防闭环触发测试。1) 左侧超卖 (bias_20 <= -4.5%, erp >= 75%) 纯债划拨 10%~15% 增配宽基；2) 迟滞噪音带 [-1.5%, +1.2%] 维持仓位锁定；3) 右侧超买 (bias_20 >= +6.5% 或 crowding_warning) 削减成长转入纯债与红利低波。
8. `test_case_08_ladder_redemption_fee_alignment`: 7天/30天/180天 真实阶梯赎回费对齐断言。针对 5天(1.50%)、15天(0.50%)、200天(0.00%) 进行逐笔校验。
9. `test_case_09_suitability_verdict_4d_and_levels`: `evaluate_today_rebalance_suitability` 裁决测试。断言 `verdict_level` 为 `"SUITABLE"` | `"HOLD_ON"` | `"FORBIDDEN"`（注意：如果代码中目前使用了其他字符串如 SUGGESTED/DISCOURAGED/BLOCKED，请注意兼容性断言或确保返回包含标准三级枚举），`verdict_title` 非空，且 `reasons_4d` 包含 `market_position_reason`, `clock_window_reason`, `deviation_utility_reason`, `lockup_fee_reason` 4 个字段。
10. `test_case_10_simulate_rebalance_modes_consequences`: 温和 vs 强行调仓双模式及四大后果量化校验。断言 `mode_gentle` 惩罚费 `penalty_fee_7d == 0.0`，卖出份额被安全裁剪；`mode_forced` 强平全额偏离，惩罚费真实计提；`consequences` 四大字典（`fee_loss`, `in_transit_risk`, `risk_shift`, `lockup_reset`）结构完整、分厘平账。
11. `test_case_11_stock_overlap_dual_dividend_exemption`: 双红利底仓对 `{"100032", "005561"}` 与限购伴生对 `{"050025", "001071"}` 豁免对抗测试。同时持有推荐组合时 alerts 无告警，`max_non_diag_unexcused` < 0.40；对抗测试：持有非豁免高重合基金必须真实触发伪分散警告且 `max_non_diag_unexcused` >= 0.40。

【验收与验证要求】
- 运行你编写的新增测试套件以及全量 pytest 测试套件：
  `py -3.11 -m pytest tests/test_milestone_phase1_r1_r5.py -v`
  `py -3.11 -m pytest tests/test_portfolio_manager.py tests/test_strategy_bridge.py tests/test_infra.py -v`
- 确保所有测试 100% 通过（PASS）。
- 完成后在你的工作目录输出 `handoff.md`，并通过 `send_message` 向父编排者汇报。
