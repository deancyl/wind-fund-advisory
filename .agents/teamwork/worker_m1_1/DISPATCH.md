## 2026-11-15T08:13:31Z

You are the Worker for Milestone 1 (M1: 十维真实投票与汇率校验及胶囊联动).
Working directory: d:\Google\Workspace\Wind
Your state folder: d:\Google\Workspace\Wind\.agents\teamwork\worker_m1_1
Authoritative user request: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
Project plan: d:\Google\Workspace\Wind\PROJECT.md
Scope definition: d:\Google\Workspace\Wind\.agents\teamwork\sub_orch_m1\SCOPE.md

Explorer findings to read and follow:
- Explorer 1 (Features 1-4: Ten Dimension votes & Circuit Breaker): d:\Google\Workspace\Wind\.agents\teamwork\explorer_m1_1\handoff.md
- Explorer 2 (Feature 5: 6.6676/5.0000 Cleanup & Calibration): d:\Google\Workspace\Wind\.agents\teamwork\explorer_m1_2\handoff.md
- Explorer 3 (Feature 6: Memo Capsule Linkage & Test Suite Design): d:\Google\Workspace\Wind\.agents\teamwork\explorer_m1_3\handoff.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Physical security baseline:
- DO NOT modify: judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py.
- DO NOT modify: DataLoader.simulate_execution default signature & default fee logic.

Your assigned scope (Milestone 1, Features 1-6):
1. 维度6产业估值真数据驱动：在 `advisory_engine.py` 的 `compute_ten_dimension_votes` 中，严禁使用列表长度恒真判断。读取全市场 14 大赛道的真实估值分位数列表（通过 `OpportunityRadarEngine.get_cached_sectors_fast()` 等真实缓存/湖仓），计算前 3 大机会赛道的平均估值分位与全市场估值中位数。当前 3 大赛道平均估值分位 <= 35% 时判定为 BULL 并上调 5% 仓位；当全市场估值中位数 > 70% 时判定为 BEAR 并下调 5% 仓位；其余为 NEUTRAL，并在 reason 中报出真实数值。
2. 维度7资金情绪多维融合：融合两市真实成交额、多方上涨家数占比以及 14 赛道真实平均拥挤度评分（通过 `DataLoader.fetch_market_turnover_and_sentiment()` 等）。当平均拥挤度 < 55 或存在动量衰竭预警时判定为 BEAR 并下调 5% 仓位；当拥挤度 >= 72 且未过热时判定为 BULL 并上调 2% 仓位；在 reason 中报出真实拥挤度均值与多方占比。
3. 维度10期权衍生品与避险：接入真实 option_iv_pct、ic_annualized_basis_rate 与动态相关性预警。当期权隐波 > 28% 或触发相关性突变预警时，强制判定为 BEAR 并下调 8% 仓位；当期权隐波 < 22% 且期指贴水提供充足安全垫且无相关性突变时判定为 BULL 上调 2% 仓位，在 reason 中报出真实数值。
4. 黑天鹅/灰犀牛一票否决熔断门禁：在十维投票汇总处，当 ivix >= 32.0 或 dyn_corr >= 0.80 或 usdcnh_chg > 0.60% 时，触发熔断，物理冻结所有低估加仓项归零（delta_pct > 0 设为 0），标记 `circuit_breaker_triggered: True`，并标注触发熔断原因。
5. 拔除 6.6676 与 5.0000 兜底常数并增加合理性校验哨：在 data_loader.py (fetch_macro_cross_market_indicators 等)、advisory_engine.py、app_gui.py、strategy_bridge.py、portfolio_manager.py 中全面清除 6.6676 和 5.0000。增加合理性校验哨：离岸人民币汇率点位必须在 [6.85, 7.60] 区间内，若超出或异常，离线校准为真实近期截面数据 7.2385，美债校准为 4.42%，中美利差校准为 -278.2 bp。
6. 胶囊4（持仓病灶）与胶囊5（今日行动准则）知行合一联动：在 `generate_chief_advisor_memo` 与 `render_chief_advisor_memo_card` 中，当检测到当前账本存在免赎碎片尾仓或深套出血点或红牌止盈预警时，第五颗胶囊今日行动准则的主结论与副标题优先输出账户级实战指令（如清扫尾仓并置换深套出血点），消除割裂。
7. 编写并运行自动化测试套件 `tests/test_g19_m1_ten_dimension_and_memo.py`，确保覆盖所有 6 项特性，并运行既有非只读测试，确保 100% 通过。

Files you own exclusively:
- `AGY2_FundAdvisory/advisory_engine.py`
- `AGY2_FundAdvisory/data_loader.py`
- `AGY2_FundAdvisory/strategy_bridge.py`
- `AGY2_FundAdvisory/portfolio_manager.py`
- `AGY2_FundAdvisory/app_gui.py`
- `tests/test_g19_m1_ten_dimension_and_memo.py`
