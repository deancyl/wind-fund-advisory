## 2026-11-07T14:41:44Z
You are the Lead Implementation Worker (worker_g7_1) for G7 Generation.
Your working directory is: d:\Google\Workspace\Wind\.agents\teamwork\worker_g7_1

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

MANDATORY: Read before starting:
- d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
- d:\Google\Workspace\Wind\GEMINI.md
- d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_9\PROJECT.md
- d:\Google\Workspace\Wind\.agents\teamwork\explorer_g7_1\handoff.md (Tab 2 structure, dual view switcher, test invariants)
- d:\Google\Workspace\Wind\.agents\teamwork\explorer_g7_2\handoff.md (Risk Watchdog dual buttons, Tab 4 promotion, session_state contracts)
- d:\Google\Workspace\Wind\.agents\teamwork\explorer_g7_3\handoff.md (OnlineHeuristicFactorEvolver fitness function with turnover penalty & tail MDD, 60-day comparison micro-chart, SHA256 hashes)

STRICT READ-ONLY INVARIANTS:
- Absolutely DO NOT modify: judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py.
- Absolutely DO NOT modify DataLoader.simulate_execution default signature or fee logic in data_loader.py.

EXCLUSIVELY OWNED FILES:
- AGY2_FundAdvisory/advisory_engine.py
- AGY2_FundAdvisory/app_gui.py
- AGY2_FundAdvisory/strategy_bridge.py
- AGY2_FundAdvisory/portfolio_optimizer.py
- tests/test_g3_evolution_loop.py (or dedicated tests/test_g7_interactions.py)

TASKS:
1. OnlineHeuristicFactorEvolver & Mathematical Fitness Enhancement
2. Opportunity Radar Whitebox Badge & Comparison Micro-Charts
3. Three-Way Risk Linkage (Watchdog -> Tab 2 -> Tab 4)
4. Tab 2 Dual-View Decoupling
5. Code Architecture Purification
6. Test Verification


## 2026-11-07T14:43:21Z
**Context**: 【最高优先级红线指令】主代理协同通报与 app_gui.py HTML 渲染保护
**Content**: 主代理刚刚已在 app_gui.py 中修复了首屏历史拐点对照尺被渲染为裸 HTML 源代码块的 Bug：
1. render_historical_inflection_ruler_html 已改写为紧凑行并在返回前包裹 _clean_html；
2. render_portfolio_cushion_and_stress_card_html 已包裹 _clean_html；
3. 首屏晨报与 top3 赛道卡片已由原先的 st.markdown(...) 切换为统一的 safe_markdown_html(...)。

【强制硬契约】：你在对 app_gui.py 进行任何代码修改与重构时：
1. 务必严格保留上述 _clean_html 与 safe_markdown_html 修复，严禁退回带多层前导空格的裸 st.markdown，物理杜绝裸 HTML 渲染回流；
2. 继续推进 Tab 2 双视图解耦（默认主视图为持仓诊断与智能调仓，独立宽屏视图为账本运维与实盘复盘档案）；
3. 实装主动风险预警哨联动按钮（「👉 去调仓处置」/「去 Tab 2 生成处置调仓单」与「🔍 穿透到底层」/「去 Tab 4 穿透看底层证据」）与 Tab 4 顶部核心诊断区提权及高亮响应；
4. 落地 OnlineHeuristicFactorEvolver 换手率惩罚与尾部最大回撤约束及近 60 日动态微图。
**Action**: 请在实施过程中严格遵守此项保护规则，并在最终 handoff.md 中明确汇报该项契约的保持情况。
