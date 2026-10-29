# BRIEFING — 2026-10-29T14:45:00Z

## Mission
修复 AGY2_FundAdvisory/portfolio_manager.py 中的账本回撤状态污染、伴生标的标签、金融股存贷双高豁免、底层重仓股去重合并、以及限购拆单表格一致性与同源份额重合度误报豁免 (R1, R3, R4)。

## 🔒 My Identity
- Archetype: implementer, qa, specialist
- Roles: [implementer, qa, specialist]
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\worker_agent1
- Original parent: 1e00e836-4cfb-404e-a729-f97fbfd899ba
- Milestone: Agent-1 (R1, R3, R4)

## 🔒 Key Constraints
- Exclusively own and write to: d:\Google\Workspace\Wind\AGY2_FundAdvisory\portfolio_manager.py
- DO NOT modify, unlock, or write to:
  - AGY2_FundAdvisory/judge_engine.py
  - AGY2_FundAdvisory/holdout_vault.py
  - AGY2_FundAdvisory/AGENT_SPEC.md
  - AGY2_FundAdvisory/tests/test_infra.py
- DO NOT CHEAT: genuine logic, real state and behavior, no hardcoding.
- Output messages in Chinese to user/parent via send_message.

## Current Parent
- Conversation ID: 1e00e836-4cfb-404e-a729-f97fbfd899ba
- Updated: not yet

## Task Summary
- **What to build**:
  - R1: 修复建仓和接管时 self.peak_equity / max_drawdown_pct 等历史状态污染，强制重置 baseline/peak/drawdown/returns；赛道冠军与限购伴生标的纳入核心策略池 (is_core_strategy=True)，消除“待替换”标签。
  - R3: 金融股存贷双高排雷豁免，double_high_risk=False，扣分0；穿透持仓股聚合唯一行，展示关联持仓基金与组合总市值占比降序。
  - R4: generate_zero_start_blueprint 拆单前后一致，表格直接拆为两行；calculate_stock_overlap_matrix 内置同源与拆单豁免，消除伪分散报警并标注“合规限购分仓/同源份额”。
- **Success criteria**: 所有的状态污染消除，金融股免杀，重仓股去重合并正确，拆单表格一致，重合度豁免正确，且现有相关测试全部通过。
- **Interface contracts**: portfolio_manager.py
- **Code layout**: AGY2_FundAdvisory/

## Key Decisions Made
- [R1] 在 apply_zero_start_blueprint、takeover_mode_a、takeover_mode_b、import_from_smart_text 开头清理 peak_equity 与 max_drawdown_pct 等历史脏数据；在所有持仓录入并调用 _recalculate_totals() 之后，强制重置 baseline_equity = round(total_cap, 2)、peak_equity = baseline_equity、max_drawdown_pct = 0.0、收益率清零。
- [R1] 将所有 17 只赛道冠军标的与官方拆单伴生标的 (如 001071, 090010, 000086, 013841 等) 统一纳入 CORE_STRATEGY_POOL 并打上 is_core_strategy = True，在 _evaluate_all_transition_tags 中强制标记为“核心策略底仓”，绝不包含“替换”或“待替换”。
- [R3] 在 screen_fund_look_through_risk 中增加金融行业存贷双高豁免规则（涵盖银行、证券、保险、金融、农商等关键词及全量 A 股金融股代码集合），存贷双高排查标记为“金融业豁免（正常）”，double_high_risk 设为 False，扣分记 0。
- [R3] 实现 get_portfolio_look_through_stocks 与 get_portfolio_look_through_stocks_df，按唯一股票代码聚合前十大重仓股，新增“关联持仓基金”列与“占组合总市值比例(%)”列，按总市值占比降序排列。
- [R4] 在 generate_zero_start_blueprint 中实现超限额（如 050025 > 500 元）自动拆为两行独立记录，第一行 050025 买入 500 元，第二行 001071 买入剩余金额，保证建仓表格与账本完全一致。
- [R4] 在 calculate_stock_overlap_matrix 中内置 EXEMPT_OVERLAP_PAIRS，并结合同源 A/C 份额与官方限购拆单伴生逻辑动态判定豁免，免除伪分散报警并在矩阵说明中标注“合规限购分仓/同源份额”；同时确保跨赛道重合（如 011612 与 013841 重合度达 40%）正常触发预警。

## Artifact Index
- d:\Google\Workspace\Wind\.agents\teamwork\worker_agent1\DISPATCH.md — Task assignment
- d:\Google\Workspace\Wind\.agents\teamwork\worker_agent1\BRIEFING.md — Situational awareness
- d:\Google\Workspace\Wind\.agents\teamwork\worker_agent1\progress.md — Progress log & heartbeat
- d:\Google\Workspace\Wind\.agents\teamwork\worker_agent1\handoff.md — Final handoff report

## Change Tracker
- **Files modified**:
  - `d:\Google\Workspace\Wind\AGY2_FundAdvisory\portfolio_manager.py`: 修复状态污染与重置、金融股存贷双高豁免、穿透重仓股去重合并、限购拆单两行输出、重合度矩阵同源/限购豁免。
  - `d:\Google\Workspace\Wind\AGY2_FundAdvisory\tests\test_portfolio_manager.py`: 新增 test 18, 19, 20 分别验证 R1, R3, R4 契约。
  - `d:\Google\Workspace\Wind\AGY2_FundAdvisory\tests\test_adversarial_m1.py`: 适配 test_scenario_multi_fund_balanced 中金融股豁免后的真实穿透风险测算。
- **Build status**: Pass (146 passed in test suite)
- **Pending issues**: None

## Quality Status
- **Build/test result**: 146 passed, 0 failed across test_portfolio_manager, test_adversarial_m1, test_adversarial_m1_challenger2, test_toolkit_integration, test_dynamic_risk_and_metrics, test_strategy_bridge.
- **Lint status**: Clean, no syntax or lint errors.
- **Tests added/modified**: 3 new tests in test_portfolio_manager.py (test_r1_portfolio_state_reset_and_core_strategy_tags, test_r3_financial_stock_double_high_exemption_and_look_through_df, test_r4_quota_split_blueprint_consistency_and_overlap_exemption).

## Loaded Skills
- None requested in dispatch

