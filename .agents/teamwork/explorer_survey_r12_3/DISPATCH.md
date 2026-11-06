# Task Assignment: Survey Explorer 3

## 目标
勘测浮盈安全垫抗震承压、本金破净临界点模型及全量自动化测试套件基线。

## 调查范围
1. 排查 `portfolio_manager.py`、`strategy_bridge.py` 与 `app_gui.py`（Tab 2 持仓账本概览区）。分析当前持仓账本的浮盈金额（total_unrealized_pnl）、持仓权重、持仓分类及 Beta 计算方法。
2. 调研如何利用真实历史净值与基准（沪深300指数 000300）序列计算每个标的的真实历史 Beta，并加权计算组合总 Beta。
3. 调研浮盈安全垫厚度（`cushion_ratio = (浮盈 + 年化票息安全垫) / 本金`）及破净临界点（沪深300需下跌多少百分比或多少点，使加权亏损等于安全垫厚度；若已浮亏，大盘需反弹多少百分比可回本）的数学模型与实现方案。
4. 调研大盘单日急跌 3%、周度回调 5%、极端回调 10% 三种承压情景推演的实现与前端 Tab 2 展示方案。
5. 梳理测试套件现状：`pytest tests/test_infra.py`、`tests/test_adv_final_closure.py`、`tests/test_g3_evolution_loop.py`、`tests/test_gui_multi_ledger_stress.py`。确认如何在 `tests/test_g3_evolution_loop.py` 中新增 G5 专属测试。

## 输出要求
将调研结论与具体实现建议写入 `.agents/teamwork/explorer_survey_r12_3/report.md`，并通过 send_message 向 orchestrator (ID: 71f16351-ac4e-45f7-b8a4-89e38ec8863c) 汇报。


## 2026-11-06T16:55:35Z
你是一个专业代码与需求探索员（teamwork_explorer）。
你的专属工作目录是：d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r12_3\
上级调度员 ID: 71f16351-ac4e-45f7-b8a4-89e38ec8863c

【必须执行的任务】
1. 首先阅读原始需求文件：d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md 以及本任务派发文档 d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r12_3\DISPATCH.md。
2. 重点排查浮盈安全垫抗震承压、本金破净临界点模型及全量测试套件：
   - 查看 d:\Google\Workspace\Wind\portfolio_manager.py、strategy_bridge.py 与 app_gui.py（Tab 2 持仓账本概览区）。分析当前账本的浮盈（total_unrealized_pnl）、持仓资产分类、各标的真实持仓权重及 Beta 弹性系数计算机制。
   - 调研如何基于真实历史净值与基准（沪深300 000300）序列计算每个标的的真实历史 Beta，并加权计算组合加权 Beta。
   - 深入推演浮盈安全垫厚度（占总本金百分比）与本金破净安全边际（计算沪深 300 指数需要连续下跌多少百分比或多少点，才会把当前账面浮盈加年内生票息安全垫全部跌光触及本金成本线；若当前已处于浮亏状态，则计算大盘反弹多少百分比可实现组合整体回本）。
   - 调研大盘单日急跌 3%、周度回调 5%、极端回调 10% 三种承压情景推演的实现与前端 Tab 2 展示方案。
   - 调研全量自动化测试套件：pytest tests/test_infra.py、tests/test_adv_final_closure.py、tests/test_g3_evolution_loop.py、tests/test_gui_multi_ledger_stress.py，以及如何在 tests/test_g3_evolution_loop.py 中新增 G5 专属测试。
3. 将详尽报告写入 d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r12_3\report.md。
4. 完成后使用 send_message 向 71f16351-ac4e-45f7-b8a4-89e38ec8863c 汇报。注意：只读探索，严禁修改任何源代码。
