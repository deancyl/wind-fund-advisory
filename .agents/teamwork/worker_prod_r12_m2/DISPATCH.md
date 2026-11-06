## 2026-11-06T17:28:06Z
你是一个高级全栈与前端工程专家（teamwork_worker）。
你的专属工作目录是：d:\Google\Workspace\Wind\.agents\teamwork\worker_prod_r12_m2\
上级调度员 ID: 71f16351-ac4e-45f7-b8a4-89e38ec8863c

【必须阅读的基准文档】
- 原始需求：d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
- 项目架构与契约：d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_7\PROJECT.md
- 任务派发规范：d:\Google\Workspace\Wind\.agents\teamwork\worker_prod_r12_m2\DISPATCH.md
- M1 交付物参考：d:\Google\Workspace\Wind\.agents\teamwork\worker_prod_r12_m1\handoff.md (查阅已完成的后端接口与数学模型签名)

【独占写权限文件】
- AGY2_FundAdvisory/app_gui.py

【只读禁改红线】
- judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py 严禁做任何修改！
- DataLoader.simulate_execution 默认函数签名与扣费逻辑严禁修改！

【MANDATORY INTEGRITY WARNING】
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

【核心实施任务】
1. 在首屏市场脉搏卡片与 Tab 1 定投规划区，调用 StrategyBridge.get_historical_inflection_ruler()，接入紧凑一行式 4 节点历史牛熊拐点对照条（2021见顶 0.50x、2022底 1.93x、2024底 1.94x、今日 1.76x），精简冗余文案以遵循界面复杂度守恒原则；
2. 在 Tab 2 持仓账本概览区，重构升级原静态纯文字横幅为“🛡️ 浮盈安全垫抗震承压与本金破净临界看板”，调用 pm.calculate_portfolio_cushion_and_stress_model()，渲染加权 Beta、安全垫厚度、破净跌幅/回本涨幅及 -3%/-5%/-10% 大盘承压推演卡片；
3. 在 Tab 2 调仓执行表与 Tab 1 定投计划实操要点列，接入 StrategyBridge.evaluate_tail_valuation_anomaly() 尾盘异动标签（防追高/黄金坑），并传入单基真实年化波动率与自身 bias_20，展现纯债、红利、科技等差异化尾盘损耗基点；
4. 针对 640px 移动端视口实施紧凑自适应 CSS，包含防压扁、横向滚动与文字安全呼吸空间，严格保证每个 Tab 具备独立错误边界；

## 2026-11-06T17:37:39Z
**Context**: 服务端限额中断已恢复，后台环境已重新就绪
**Content**: 请无缝接续 Milestone 2 前端界面实装任务。请在 `AGY2_FundAdvisory/app_gui.py` 中完成：
1. 首屏与 Tab 1 接入历史三大拐点对照尺（StrategyBridge.get_historical_inflection_ruler），精简冗余文案以遵循界面复杂度守恒；
2. Tab 2 接入浮盈安全垫抗震承压与破净临界看板（加权 Beta、安全垫厚度、破净/回本临界点、-3%/-5%/-10% 承压推演卡片）；
3. Tab 2 调仓执行表与定投计划接入 14:30 尾盘估值异动预警（防追高/黄金坑）及单基真实波动率/乖离率差异化损耗基点；
4. 640px 移动端 CSS 自适应与 Tab 独立错误边界；
5. 验证 GUI 并产出 handoff.md。
**Action**: 请立即继续执行并完成 app_gui.py 修改与自测。

