## 2026-11-05T15:17:03Z
You are a teamwork_worker agent.
Your working directory: d:\Google\Workspace\Wind\.agents\teamwork\worker_prod_r9_m2
User request specification: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
Master Project document: d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_1\PROJECT.md
Survey Report: d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r9_2\report.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT
hardcode test results, create dummy/facade implementations, or
circumvent the intended task. A teamwork_auditor will independently
verify your work. Integrity violations WILL be detected and your
work WILL be rejected.

File Ownership:
- You exclusively own: `AGY2_FundAdvisory/strategy_bridge.py` (rebalance order & simulation methods), `AGY2_FundAdvisory/app_gui.py` (Tab 2 scenario controls, cache key, Tab 3 dynamic analog attribution).
- Strictly DO NOT modify: `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`.

Your mission is Milestone 2 (R3 & R4):
1. R3: Tab 2 四大实盘调仓场景模式前后端真实计算闭环
   - In `app_gui.py`: ensure `scenario_mode`, `new_cash_amount`, `withdraw_cash_amount`, `freeze_reserved_cash`, `core_anchor_code` are fully captured and included in cache key `cur_pool_sig`.
   - In `strategy_bridge.py`: pass these scenario parameters down to `pm.generate_scenario_rebalance_plan` inside `generate_ai_rebalance_orders` and `simulate_rebalance_modes_and_consequences`.
   - In `generate_ai_rebalance_orders`: use the scenario plan's `buy_actions` and `sell_actions` so that:
     - `new_cash_only`: sell orders = 0, buy orders sum strictly to `new_cash_amount`, redemption fees = 0.
     - `withdraw_cash_only`: buy orders = 0, sell orders sum strictly to `withdraw_cash_amount`, skips `<7` days locked funds.
     - `freeze_reserved_chk`: deduct `pm.reserved_batch_cash` from available rebalance funds.
2. R4: 清除 Tab 3「历史相似匹配」硬编码假文案，改为真实动态统计
   - In `app_gui.py`: remove hardcoded `"胜率达 100.0%，平均绝对收益 +8.5%"`. Dynamically compute from `analog_tab2["matches"]`:
     - 跑赢沪深300的相对超额胜率 (%)
     - 平均相对超额收益率 (%)
     - 策略平均绝对收益率 (%)
     - 平均最大回撤 (%)
   - For the 3 cards below, classify dynamically based on each match's `strategy_ret_60d` and `h300_ret_60d`:
     - Double positive -> "右侧顺势共振：底部击球区反弹期紧跟主升浪，兼顾进攻弹性与低回撤（最大回撤仅 X.X%）"
     - h300 down, strategy outperforming -> "逆势抗跌护盾：大盘阴跌寻底期，凭借红利与纯债底仓大幅跑赢大盘 +X.XX%，守住本金安全垫"
     - h300 up, strategy defensive lagging -> "防守底仓代价：急跌反抽期高配纯债避险导致短期弹性收敛，但换取了熊市下半场极高本金安全度"
3. Verification:
   - Run: `py -3 -m pytest tests/test_anticheat_suite.py -k "TestRebalancingScenariosRealness" -v` (must be 3 passed 100%).
   - Run: `py -3 -m pytest tests/test_infra.py tests/test_portfolio.py tests/test_multi_ledger_manager.py -v` (ensure 0 regressions).
   - Run: `py -3 -m pytest tests/test_streamlit_apptest_run.py -v`.
   - Deliver handoff report (`handoff.md`) and notify orchestrator via `send_message`.


## 2026-11-05T15:27:35Z
**Context**: Milestone 2 Implementation (R3 & R4)
**Content**: 请汇报当前四大调仓场景与 Tab 3 动态历史镜鉴的编写进度及预计交付时间。
**Action**: 请简要回复进度更新。

## 2026-11-05T15:39:11Z
**Context**: Milestone 2 Implementation (R3 & R4)
**Content**: 请汇报当前编写与测试验证进度。
**Action**: 请简要回复进度更新。
