# DISPATCH Log

## 2026-11-15T07:58:27Z

【Implementation Track: Milestone 1 Sub-Orchestrator】
You are the Sub-Orchestrator for Milestone 1 (M1: 十维真实投票与汇率校验及胶囊联动).
Your working directory is: d:\Google\Workspace\Wind
Your state folder is: d:\Google\Workspace\Wind\.agents\teamwork\sub_orch_m1
Authoritative user request: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
Project plan: d:\Google\Workspace\Wind\PROJECT.md
Survey findings: d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_1\handoff.md

Your scope is Milestone 1 (Features 1-6):
1. 维度6产业估值真数据驱动：在 `advisory_engine.py` 的 `compute_ten_dimension_votes` 中，严禁使用列表长度恒真判断。读取全市场 14 大赛道的真实估值分位数列表，计算前 3 大机会赛道的平均估值分位与全市场估值中位数。当前 3 大赛道平均估值分位 <= 35% 时判定为 BULL 并上调 5% 仓位；当全市场估值中位数 > 70% 时判定为 BEAR 并下调 5% 仓位；其余为 NEUTRAL，并在 reason 中报出真实数值。
2. 维度7资金情绪多维融合：融合两市真实成交额、多方上涨家数占比以及 14 赛道真实平均拥挤度评分。当平均拥挤度 < 55 或存在动量衰竭预警时判定为 BEAR 并下调 5% 仓位；当拥挤度 >= 72 且未过热时判定为 BULL 并上调 2% 仓位；在 reason 中报出真实拥挤度均值与多方占比。
3. 维度10期权衍生品与避险：接入真实 option_iv_pct、ic_annualized_basis_rate 与动态相关性预警。当期权隐波 > 28% 或触发相关性突变预警时，强制判定为 BEAR 并下调 8% 仓位；当期权隐波 < 22% 且期指贴水提供充足安全垫且无相关性突变时判定为 BULL，在 reason 中报出真实数值。
4. 黑天鹅/灰犀牛一票否决熔断门禁：在十维投票汇总处，当 ivix >= 32.0 或 dyn_corr >= 0.80 或 usdcnh_chg > 0.60% 时，冻结低估加仓项并标注触发熔断。
5. 拔除 6.6676 与 5.0000 兜底常数并增加合理性校验哨：在 data_loader.py (fetch_macro_cross_market_indicators 等)、advisory_engine.py、app_gui.py、strategy_bridge.py、portfolio_manager.py 中全面清除 6.6676 和 5.0000。若离岸汇率低于 6.85 或高于 7.60，离线校准为真实近期截面数据 7.2385，美债校准为 4.42%，利差校准为 -278.2 bp。
6. 胶囊4（持仓病灶）与胶囊5（今日行动准则）知行合一联动：在 generate_chief_advisor_memo 与 render_chief_advisor_memo_card 中，当检测到当前账本存在免赎碎片尾仓或深套出血点或红牌止盈预警时，第五颗胶囊今日行动准则的主结论与副标题优先输出账户级实战指令（如清扫尾仓并置换深套出血点），消除割裂。

Rules & Architecture:
- Follow the Sub-orchestrator procedure: Assess -> Iteration loop (Explorer -> Worker -> Reviewer -> Challenger -> Forensic Auditor).
- MANDATORY INTEGRITY WARNING to Worker: "DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work."
- Physical security baseline: DO NOT modify judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py. DO NOT modify DataLoader.simulate_execution default signature & default fee logic.
- Run builds and tests via pytest, run Challenger stress tests, run Forensic Auditor integrity check, maintain GATE_STATUS.md.
- Pass criteria: Build/tests pass, all reviewers APPROVE, challengers pass, auditor CLEAN.
- Send a message to your parent orchestrator (conversation ID: 2b4a5c42-da01-49e9-b9b9-7a42b49250ea) with your completion report when M1 is done.
