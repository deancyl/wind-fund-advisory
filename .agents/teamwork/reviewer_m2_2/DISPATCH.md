# DISPATCH - Reviewer M2-2 (Color Purge, Dynamic PnL Colors & Layout Consistency)
- Task: Verify Milestone 2 Features 7, 8, 10 in AGY2_FundAdvisory/app_gui.py
- Working directory: .agents/teamwork/reviewer_m2_2/
- Original request: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
- Scope document: d:\Google\Workspace\Wind\.agents\teamwork\orchestrator\PROJECT.md
- Worker handoff: d:\Google\Workspace\Wind\.agents\teamwork\worker_prod_m2\handoff.md

## 2026-11-04T11:46:48Z
你作为专业代码审查员（Reviewer M2-2），对 Milestone 2（Features 7, 8, 10: 颜色清洗、动态涨跌色联动、顶部行情带与侧边栏）执行独立、客观、严谨的代码审查与测试复核。

【必须阅读的上下文文件】
1. 原始需求文件：d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
2. 架构与里程碑规范：d:\Google\Workspace\Wind\.agents\teamwork\orchestrator\PROJECT.md
3. 工作区准则：d:\Google\Workspace\Wind\GEMINI.md
4. Worker 交付报告：d:\Google\Workspace\Wind\.agents\teamwork\worker_prod_m2\handoff.md
5. 目标实现文件：d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py

【你的工作目录】
d:\Google\Workspace\Wind\.agents\teamwork\reviewer_m2_2\
请在你的工作目录下维护 BRIEFING.md、progress.md，并在完成审查后输出 handoff.md。

【审查重点】
1. Feature 7（色彩字面量清理与动态多配色联动）：扫描确认 safe_markdown_html 与 Plotly 图表中已消除 `#ffffff`、`#f8fafc`、`#0f172a` 等硬编码十六进制颜色；Python 端动态计算的盈亏颜色（`pnl_c`、`pnl_color` 等）及 Plotly 涨跌色必须动态读取当前激活的 `active_co["color_up"]` 与 `active_co["color_down"]`，支持 A 股红涨绿跌与国际绿涨红跌全站实时联动。
2. Feature 10（顶部行情带与侧边栏职责）：
   - 顶部 4 张核心状态卡下方全宽呈现 6 大指数行情带（展示真实估值标签、点位与涨跌幅）；
   - 左侧边栏移除阻塞主线程的逐个 SVG 分时微图循环请求，聚焦于四大控盘职责，且首个按钮 `at.sidebar.button[0]` 保持为载入演示组合（兼容既有自动化测试）。
3. 运行验证命令：
   - `cmd /c "set PYTHONPATH=AGY2_FundAdvisory;. && py -3 -m pytest AGY2_FundAdvisory/tests/test_deep_remodel_final.py -v"`
   - `cmd /c "set PYTHONPATH=AGY2_FundAdvisory;. && py -3 -m pytest AGY2_FundAdvisory/tests/test_infra.py -v"`
   - 校验 4 个裁判文件的 SHA-256 哈希是否完好。
4. 在 handoff.md 中明确给出 Verdict：APPROVE 或 REQUEST_CHANGES，并使用 send_message 向 orchestrator (c98181d5-8d61-4839-8d62-5dbcef7c85af) 发送完成通知。
