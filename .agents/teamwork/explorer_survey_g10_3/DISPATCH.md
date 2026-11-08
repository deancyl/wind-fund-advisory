## 2026-11-08T03:19:26Z
You are a Codebase Survey Explorer (teamwork_explorer).
Your working directory is: d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_g10_3\
Mandatory inputs:
- Read d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
- Read d:\Google\Workspace\Wind\GEMINI.md
- Read d:\Google\Workspace\Wind\AGENT_SPEC.md

Your mission:
Investigate portfolio_manager.py, AGY2_FundAdvisory/app_gui.py, and tests/ regarding Requirement R4, R5 & R6:
- R4. 穿透式多周期蒙特卡洛压力测试:
  - 在 portfolio_manager.py 中实装多周期穿透式蒙特卡洛压力测试。
  - 基于块重采样（Block Bootstrap），结合投资者风险等级 C1 至 C5，自动输出当前组合在 2008 年金融危机、2015 年流动性踩踏及 2024 年初小盘股流动性危机三大极端情景下的最大回撤预测与流动性变现天数。
- R5. 本地服务平滑重启与多模态视觉走查闭环:
  - 核查首屏双翼看板：多资产相关性突变预警指示卡与压力测试流动性指标；
  - 核查 Tab 1 与 Tab 2：大额订单流动性折价明细表与蒙特卡洛压力测试三维分布图；
  - 核查亮色、暗黑主题及 640px 移动端视口，确认图表、文字与表格零截断、零水平溢出。
- R6. 全量自动化测试基线与新增专项测试计划:
  - 查看当前 59 项测试组织结构（tests/test_infra.py, tests/test_adv_final_closure.py, tests/test_g3_evolution_loop.py, tests/test_gui_multi_ledger_stress.py, etc.）。
  - 规划新增测试用例结构。

Details to investigate:
1. In portfolio_manager.py: inspect simulate_portfolio_cvar_bootstrap and existing stress test methods. How are historical scenarios defined or simulated? How to implement Block Bootstrap with block length 10 days, 10,000 resamples or appropriate chunking, mapping to 2008, 2015, and 2024 scenarios, combined with risk grade C1-C5.
2. How are "max drawdown prediction" and "liquidity liquidation days" calculated for each scenario and C1-C5?
3. In AGY2_FundAdvisory/app_gui.py:
   - Where in the double-wing dashboard should the correlation stress mutation warning card and stress test liquidity metrics be rendered?
   - Where in Tab 1 and Tab 2 should the large order liquidity haircut table and Monte Carlo 3D distribution chart be rendered?
   - CSS rules, safe_markdown_html, _clean_html, and responsive layouts to ensure zero overflow/truncation in 640px.
4. Check the test suite structure in tests/, identify what pytest commands are run, and what new test assertions are required for R6.
5. Provide exact function names, line numbers, data structures, and concrete implementation recommendations.

Output:
Write your complete survey report to d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_g10_3\handoff.md.
Also update progress.md in your working directory.
When finished, send a message to your caller indicating you are done and the report path.
DO NOT modify any source code files. You are read-only.
