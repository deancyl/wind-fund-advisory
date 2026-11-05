## 2026-11-05T14:11:57Z
You are a teamwork_explorer agent.
Your working directory: d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r9_2
User request specification: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md

Your mission is Phase 0 Technical Survey for R3, R4, and R7:
1. Tab 2 四大实盘调仓场景模式前后端真实计算闭环 (R3):
   - Inspect AGY2_FundAdvisory/app_gui.py and portfolio_optimizer.py / strategy_bridge.py / portfolio_manager.py:
   - Trace simulate_rebalance_modes_and_consequences and generate_ai_rebalance_orders: what arguments do they currently take? Are scenario_mode, new_cash_amount, withdraw_cash_amount, freeze_reserved_cash, core_anchor_code passed and included in cache keys?
   - Analyze requirements for each scenario mode:
     - standard
     - new_cash_only: sell amounts strictly 0, buy amounts strictly sum to new_cash_amount, zero redemption fees.
     - withdraw_cash_only: buy amounts strictly 0, redemption amounts strictly sum to withdraw_cash_amount, optimal redemption order (exempt C/A classes, overweight/gainers, skip <7d locked).
     - sweep_tail_and_c_class
     - freeze_reserved_chk: deduct pm.reserved_batch_cash from available rebalance cash.
2. Tab 3 历史相似匹配硬编码假文案清除与动态统计 (R4):
   - Inspect AGY2_FundAdvisory/app_gui.py Tab 3:
   - Trace analog_tab2 and its "matches" list. Where are strategy_ret_60d, h300_ret_60d, strategy_mdd_60d defined?
   - Check the top banner in Tab 3: identify hardcoded constants and replace with dynamic win-rate, excess return, strategy absolute return, and max drawdown over 60 days.
   - Check the 3 historical cards: identify how "历史镜鉴意义" is rendered and how to dynamically generate the 3 distinct attribution categories based on real return relationships.
3. 双翼看板右翼主动风险预警哨同类预警折叠聚合与紧凑布局 (R7):
   - Inspect ActiveRiskSentry in portfolio_manager.py / AGY2_FundAdvisory/advisory_engine.py and its rendering in app_gui.py.
   - Investigate how to aggregate same-dimension warnings (>= 2 funds) into single warning cards with batch add to tab2_locked_funds.
   - Check container styling (max-height: 320px; overflow-y: auto) and compact layout.
4. Deliverables:
   - Write a detailed survey report to d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r9_2\report.md with line numbers, code snippets, root causes of disconnection/hardcoding, and exact implementation recommendations.
   - Write handoff.md in your working directory following the Handoff Protocol.
   - Report back via send_message when done.
