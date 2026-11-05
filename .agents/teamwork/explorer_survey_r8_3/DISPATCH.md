## 2026-11-05T01:37:49Z
You are Explorer Survey R8-3.
Your working directory is d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r8_3\.
Read the original user request at: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md.
Also review the project rules at: d:\Google\Workspace\Wind\GEMINI.md.

YOUR FOCUS: Requirement R3 & R4 - 扩充 7 大机构级量化定权模型、历史黑天鹅压力测试器、UI 细节修复与物理安全红线
1. 实装 7 大机构定权求解算子：
   - 调查 QUANT_MODELS_CATALOG 与 WinRateOptimizer 的现有代码结构：
     1. 模型1：鲁棒双核HRP（层次风险平价 + 极值CVaR约束）；
     2. 模型2：核心-卫星杠铃模型（Core-Satellite，70%~80%纯债红利核心底仓 + 20%~30%高弹性成长/雷达精选卫星仓）；
     3. 模型3：全天候风险平价模型（All-Weather，跨A股宽基、红利、纯债、黄金、海外QDII实现等风险贡献度配置）；
     4. 模型4：BL主客观观点融合模型（Black-Litterman，以市场均衡配置为先验，贝叶斯融合机会雷达Top赛道与自选观点）；
     5. 模型5：条件胜率最优模型（同温层状态机核密度加权）；
     6. 模型6：尾部风控CVaR模型（最小化 95% 极端尾部亏损）；
     7. 模型7：凯利动量增强模型（考夫曼信噪比自适应半凯利公式）。
   - 重点分析：各模型的真实数学公式、权重归一化（权重和必须严格等于 1.0）、边界约束处理（如单只基金权重上限、下界惩罚保护）、步骤一模型对比说明卡片与宏观推荐逻辑更新。
2. 历史黑天鹅压力测试器：
   - 调查 Tab 1 步骤二与 Tab 3 推演结果中的现有卡片渲染位置。
   - 调查如何基于真实历史切片（2018 贸易摩擦熊市、2022 杀估值熊市、2024 年初微盘流动性危机）测算当前组合的最大浮亏金额与回本天数。
3. UI 细节修复：
   - 调查 app_gui.py 中的全局 CSS 样式，定位 button[kind="primary"] 及其内部 span/p 的颜色设置，分析如何强制为 color: #ffffff !important；
   - 调查 Tab 1 步骤一中的顶部灰框与下方提示语，定位资产锚点与权益上限的重复文案描述，分析如何精炼合并为单一策略锚点卡片。
4. 物理安全红线与自动化验证：
   - 调查 verify_referee_hashes.py 与 4 大只读裁判文件（judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py）的 SHA256 哈希完整性。
   - 调查既有 pytest 测试用例与 Streamlit AppTest 用例，规划增量测试覆盖（验证 7 大模型权重和严格等于 1.0、6 维风险预警哨准确识别 011612、011613、013841 三类风险、图1与图2估值分位一致性）。
5. 约束与红线：
   - 严禁修改裁判文件（judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py）。
   - 作为只读 Explorer，绝对不要修改或编写任何源码，只需深入探索与输出分析报告。

Write your detailed findings to d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r8_3\analysis.md and write a standard handoff report to d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r8_3\handoff.md. When finished, send a message to the orchestrator.
