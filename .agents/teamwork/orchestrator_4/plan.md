# Execution Plan — 阶段一重构（后端核心算法与真数据闭环）

## Phase 0: Survey 全景勘测 (3 Explorers 并行)
- **Explorer 1** (`explorer_orch4_1`): 调研 `portfolio_manager.py`（针对 Agent-1 范围：实时限购获取 `akshare.fund_purchase_em()`、缓存表结构、瀑布流拆单算法逻辑、QDII 盘中估值纠偏机制）。
- **Explorer 2** (`explorer_orch4_2`): 调研 `strategy_bridge.py` 与 `data_loader.py`（针对 Agent-2 范围：清除 C3 静态权重劫持、`compute_dynamic_tier_weights` 动态配权实现、三段式攻防闭环触发机制与 7d/30d/180d 阶梯赎回费对齐）。
- **Explorer 3** (`explorer_orch4_3`): 调研 `strategy_bridge.py`、`portfolio_manager.py` 与 `tests/`（针对 Agent-3 与 Agent-4 范围：`evaluate_today_rebalance_suitability`、`simulate_rebalance_modes_and_consequences`、`calculate_stock_overlap_matrix` 协同豁免池、以及既有测试套件结构与运行方式）。

## Phase 1: Milestone 1 — 实时限购、瀑布拆单与 QDII 纠偏 (Agent-1)
- 目标文件: `portfolio_manager.py`
- 专精角色: Agent-1 (`worker_agent1_orch4`)
- 产出: `fetch_realtime_fund_quota`、日期戳缓存、多级瀑布流拆单、QDII 盘中估值基准纠偏。

## Phase 2: Milestone 2 — 清除静态权重劫持与三段式攻防闭环 (Agent-2)
- 目标文件: `strategy_bridge.py`, `data_loader.py`
- 专精角色: Agent-2 (`worker_agent2_orch4`)
- 产出: 100% 动态权重、左侧极值吸筹、右侧施密特迟滞、右侧极端超买阶梯止盈、阶梯赎回费对齐。

## Phase 3: Milestone 3 — 调仓适宜度裁决、四大后果推演与底仓豁免 (Agent-3)
- 目标文件: `strategy_bridge.py`, `portfolio_manager.py`
- 专精角色: Agent-3 (`worker_agent3_orch4`)
- 产出: `evaluate_today_rebalance_suitability`、`simulate_rebalance_modes_and_consequences`（温和与强行两模式、四大后果精算）、`calculate_stock_overlap_matrix` 双红利与限购对豁免。

## Phase 4: Milestone 4 — 红队反作弊与单元测试覆盖 (Agent-4)
- 目标文件: `tests/`
- 专精角色: Agent-4 (`worker_agent4_orch4`)
- 产出: 覆盖 R1~R4 真实断言的完整测试集，绝不修改只读裁判文件，无作弊无硬编码。

## Phase 5: Verification & Gate 双轨终审
- 独立审查员 (`reviewer_orch4_1`, `reviewer_orch4_2`)
- 实证红队挑战者 (`challenger_orch4_1`, `challenger_orch4_2`)
- 法医审计员 (`auditor_orch4_1`) 严查作弊与只读文件完整性
