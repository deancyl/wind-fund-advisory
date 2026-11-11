## 2026-11-11T00:53:48Z
【任务背景与目标】
你是具有高可靠工程与量化投顾开发能力的执行智能体 (teamwork_worker)。
当前里程碑：M1 —— 修复 `advisory_engine.py` 中 `generate_chief_advisor_memo` 的持仓成本属性 Bug，并重构首屏「十维感知·五维横向投顾情报矩阵」(`render_chief_advisor_memo_card`)。

【强制诚信警告 (MANDATORY INTEGRITY WARNING)】
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

【关键输入与参考文件】
- 原始需求：d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
- 范围与契约：d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_g16_gen2\SCOPE.md
- 详细勘察报告：d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_1\handoff.md
- 外部审计参考：c:\Users\deanc\Downloads\agy2_ui_ux_audit_and_fix_plan (4).md
- 你的独占所有权文件：
  1. `d:\Google\Workspace\Wind\AGY2_FundAdvisory\advisory_engine.py`
  2. `d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py` (仅限 memo 卡片函数与首屏调用位置)
- 你的状态文件夹：d:\Google\Workspace\Wind\.agents\teamwork\worker_m1
- 成果交付文件：d:\Google\Workspace\Wind\.agents\teamwork\worker_m1\handoff.md

【核心实现要求】
1. 修复 `advisory_engine.py` 中的 `generate_chief_advisor_memo` (第 4170~4375 行)：
   - **多字段兼容读取成本与盈亏率**：
     彻底修复第 4284 行读取不存在的 `cost_value` 的 Bug！必须按以下层级读取：
     优先读取 `getattr(h, "cost_basis", 0.0)`，若为 0 则尝试 `getattr(h, "cost_price", 0.0) * getattr(h, "shares", 0.0)`，再兼容字典取值与降级 `cost_value`；
     同时支持直接读取 `floating_pnl_pct` 或 `pnl_pct`：若存在且不为 0，则直接用 `pl_ratio = float(pnl_pct) / 100.0`；
     对 `pl_ratio < -0.10` 的标的精确计入 `deep_loss_list`，确保 29 基账本中的 011613 (-17.1%)、100032 (-12.0%)、161725 (-25.1%) 准确报出且 `deep_loss_count >= 3`！
   - **Tab 1 权重字典误判修复**：
     检测 `holdings` 是否为目标权重字典（如 `{"005561": 0.35, ...}`，所有值在 0~1 之间且和约为 1.0）。若为权重字典，则将其定位为“拟建仓资产组合结构校验”，展示攻防配比与单标的集中度，坚决跳过碎片尾仓和深套亏损检查，彻底消除“6 只碎片合计 ¥1.00”的荒谬文案！
   - **19 只免赎碎片与 ¥442.70 严格对齐**：
     按照 `ActiveRiskSentry` 的碎片尾仓标准统计，识别出市值 < ¥200 且满足免赎/C类/联接特征的碎片尾仓，精确锁定 19 只免赎碎片合计 ¥442.70（排除 #10 005827 易方达蓝筹 ¥124.14）。
   - **强化五维决策备忘录因果叙事**：
     宏观政策面（10Y国债、DR007利差、ERP分位）、国际汇率面（USD/CNH、黄金纳指联动、中美利差）、产业估值面（Top 3低估黄金击球区赛道与高拥挤度赛道）、存量持仓病灶（精确点名出血点标的与金额、碎片尾仓数量与金额）、今日 14:30 明确行动准则。

2. 重构 `app_gui.py` 中的 `render_chief_advisor_memo_card` (第 249~329 行与第 3196~3202 行)：
   - **提权至首屏主视野**：
     将 `render_chief_advisor_memo_card` 从第 3196 行收起的 `wing_expander` 内部移出，直接放置在顶部 4 张全局指标卡（第 3028 行之后、双翼展开栏之前），使首屏一打开立即可见！
   - **重构为 1 行 5 列横向等高响应式矩阵网格**：
     CSS 布局从纵向单列重构为横向网格：`grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 8px;`（在移动端或窄屏宽度 `< 768px` 时自动流式折行）。
     每张子卡片高度控制在 115px 左右，顶部带鲜明色标（宏观蓝/国际紫/产业青/病灶橙红/行动绿）与结论胶囊，正文精炼干脆。
     使用 `_clean_html()` 与 `safe_markdown_html()`，严格遵循规则 27 消除任何 CommonMark 代码块转义泄露。

3. 执行构建与针对性测试验证：
   - 编写针对 `generate_chief_advisor_memo` 的单测（支持 `HoldingItem`、支持 29 基真实持仓、验证 `deep_loss_count >= 3`、验证 Tab 1 权重字典不报碎片）。
   - 运行测试并确保通过，并在交付报告中提供命令和测试输出证据。

【交付要求】
在独占所有权文件中完成修改，运行测试验证，将修改详情、测试结果、验证证据写入 `d:\Google\Workspace\Wind\.agents\teamwork\worker_m1\handoff.md`，并通过 send_message 通知父智能体 (conversation ID: a4d409c2-aeca-47df-a18c-528d9465a6c8)。
