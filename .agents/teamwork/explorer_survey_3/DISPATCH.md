## 2026-11-11T00:25:38Z
【任务背景与目标】
你是只读探索智能体 (teamwork_explorer)。本任务旨在针对 G16 世代第二阶段后半部分及第三、第四阶段任务（29基真实存量组合、Tab 2 / Tab 3 实战演练、回归测试套件与安全红线）进行代码实地走查与深度探查，产出详尽的调查报告。
你拥有只读权限，严禁修改任何代码。

【重要约束与输入文件】
- 原始需求：d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
- 外部审计参考：c:\Users\deanc\Downloads\agy2_ui_ux_audit_and_fix_plan (4).md
- 你的状态文件夹：d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_3
- 你的工作目录：d:\Google\Workspace\Wind
- 成果交付文件：d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_3\handoff.md

【核心调查范围】
1. `multi_ledger_manager.py`:
   - 检查 `combat_29_funds`（`实战存量组合（29只·¥2.66万）`）的初始化与幂等挂载机制。
   - 检查其持仓数据：总市值是否为 ¥26,615.10，投入本金 ¥27,568.50，累计收益 -¥953.40。
   - 检查持有天数：`buy_date` 与 `_recalculate_totals` 计算出的持仓天数（400天 vs 1040天问题），如何规范。
   - 确保在 UI 启动时由 MultiLedgerManager 自动幂等挂载该 29 基账本，即使单测检查 `data/ledgers_index.json` 时也能安全兼容。

2. `strategy_bridge.py` & `app_gui.py` (Tab 2 & Tab 3):
   - Tab 2：检查针对 29 基组合的「🧹 执行三步瘦身重构模拟（清扫 19 只免赎尾仓 + 置换深套出血点）」对比面板逻辑，量化指标（持仓数量 29只 -> 6只，盘活资金 ¥442.70 ~ ¥962.57，票息垫提升，回本天数缩短）。
   - Tab 3：检查「组合回测」与「历史时点时光机盲测验证」（`run_historical_time_machine_backtest`），定位「实战存量组合：原始29基 vs 投顾重构6基（近1年真规则回测对比）」的接入点，检查是否支持真实申赎费率、限购与 T+1 规则下的同图双曲线绘制。
   - 检查时光机盲测中静态锁死权重的问题（2024.09 底部反转前夜踏空问题）及其在当前代码中的实现状态。

3. 测试套件与物理红线：
   - 探查四个只读裁判文件：`judge_engine.py`、`holdout_vault.py`、`AGENT_SPEC.md`、`tests/test_infra.py` 的当前哈希与保护状态。
   - 探查待运行的测试文件：`tests/test_infra.py`、`tests/test_adv_final_closure.py`、`tests/test_g3_evolution_loop.py`、`tests/test_gui_multi_ledger_stress.py` 是否存在，运行方式是什么。
   - 探查新增 `generate_chief_advisor_memo` 对 `HoldingItem` 深套识别（断言 `deep_loss_count >= 3`）单测的最佳编写位置。
   - 明确 G17 世代进化指令输出格式门禁（严禁带冒号的 slashCommand: 格式，必须为 /goal, /boost, /teamwork, /browser 纯文本）。

【交付要求】
请将探查到的确切代码行号、现有实现逻辑、测试套件现状、红线合规要点及修改建议，写入你的 handoff.md，并在完成后通过 send_message 通知父智能体（conversation ID: a4d409c2-aeca-47df-a18c-528d9465a6c8）。
