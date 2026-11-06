# Task Assignment: Survey Explorer 1

## 目标
勘测单基真实历史波动率与单基乖离率穿透现状与实现方案。

## 调查范围
1. 深入排查 `advisory_engine.py` 中 `calculate_vwap_execution_slippage` 函数。精确找到固定波动率回退常数（0.04、0.14、0.18）所在位置及逻辑。
2. 调研 `advisory_engine.py`、`data_loader.py` 或本地缓存中现有的净值序列、赛道日线或对齐收益率矩阵结构。如何高效、真实地计算单个基金过去 20 个交易日的真实年化波动率（如使用真实的 20 日对数或百分比收益率标准差 × sqrt(250) 或 sqrt(242)）与基金自身对 20 日均线的乖离率 `bias_20 = (nav - ma20) / ma20 * 100%`。
3. 排查 `advisory_engine.py`（如 `plan_smart_dca` 等方法）与 `app_gui.py` 中所有调用 `calculate_vwap_execution_slippage` 的位置，列出所有调用点及其当前参数传递。
4. 确保无作弊、无硬编码常数，且在本地缓存缺失或冷启动时有合理的真实回退机制（需说明真实计算链）。

## 输出要求
将调研结论与具体实现建议写入 `.agents/teamwork/explorer_survey_r12_1/report.md`，并通过 send_message 向 orchestrator (ID: 71f16351-ac4e-45f7-b8a4-89e38ec8863c) 汇报。


## 2026-11-06T16:55:20Z
Sender: 71f16351-ac4e-45f7-b8a4-89e38ec8863c
Content:
你是一个专业代码与需求探索员（teamwork_explorer）。
你的专属工作目录是：d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r12_1\
上级调度员 ID: 71f16351-ac4e-45f7-b8a4-89e38ec8863c

【必须执行的任务】
1. 首先阅读原始需求文件：d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md 以及本任务派发文档 d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r12_1\DISPATCH.md。
2. 重点排查单基真实历史波动率与单基乖离率穿透：
   - 查看 d:\Google\Workspace\Wind\advisory_engine.py 中的 calculate_vwap_execution_slippage 函数，定位固定波动率回退常数（0.04、0.14、0.18）及相关逻辑。
   - 深入查看 advisory_engine.py、data_loader.py 或本地数据湖中已有的净值与价格缓存机制，查明如何从本地历史净值计算单只基金过去 20 个交易日的真实年化波动率与该基金自身的 20 日均线乖离率 bias_20。
   - 排查 advisory_engine.py（如 plan_smart_dca）与 app_gui.py 中所有调用 calculate_vwap_execution_slippage 的位置与传参。
   - 提出精确、可落地的修改方案与函数实现代码草案，严禁伪常数，严禁伪随机数。
3. 将详尽报告写入 d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r12_1\report.md。
4. 完成后使用 send_message 向 71f16351-ac4e-45f7-b8a4-89e38ec8863c 汇报核心发现与报告路径。注意：你是一个只读探索员，严禁修改任何源代码。
