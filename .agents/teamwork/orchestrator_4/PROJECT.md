# Project: AGY2_FundAdvisory Phase 1 Refactoring (Backend Core Algorithm & Real Data Closed Loop)

## Architecture
- **Host System**: `AGY2_FundAdvisory`
- **Scope**: Backend core algorithms and real data closed loop (`portfolio_manager.py`, `strategy_bridge.py`, `data_loader.py`, `tests/`)
- **Key Modules**:
  1. `portfolio_manager.py`: 实时限购获取与本地缓存、多级瀑布流拆单算法与动态 action_guide、QDII 盘中估值纠偏与美股指数前缀修复、双红利底仓与限购伴生对重合度豁免。
  2. `strategy_bridge.py` & `data_loader.py`: 100% 动态配权模型（彻底清除 C3 静态权重劫持）、三段式攻防闭环（左侧极值吸筹、右侧迟滞锁定、右侧超买止盈）、7天/30天/180天 阶梯赎回费对齐、调仓适宜度四维裁决器、强行调仓四大后果推演器。
  3. `tests/`: 覆盖 R1~R5 需求的红队单元测试与端到端对抗验证套件。
  4. System Read-Only Invariants: `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py` 严格保持 0 变动。

## Code Layout
- `AGY2_FundAdvisory/portfolio_manager.py`: Agent-1 (M1) 与 Agent-3 (M3 局部) 负责
- `AGY2_FundAdvisory/strategy_bridge.py`: Agent-2 (M2) 与 Agent-3 (M3) 负责
- `AGY2_FundAdvisory/data_loader.py`: Agent-2 (M2) 负责
- `AGY2_FundAdvisory/tests/`: Agent-4 (M4) 负责
- Read-Only Invariants (严禁修改):
  - `AGY2_FundAdvisory/judge_engine.py`
  - `AGY2_FundAdvisory/holdout_vault.py`
  - `AGY2_FundAdvisory/AGENT_SPEC.md`
  - `AGY2_FundAdvisory/tests/test_infra.py`

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Realtime Fund Quota Fetch | `fetch_realtime_fund_quota()` 通过 akshare 获取限额，带日期戳本地 SQLite/Parquet 缓存 | M1 | ORIGINAL_REQUEST §R2 |
| 2 | Waterfall Order Splitting | 多级瀑布流拆单算法，动态生成 action_guide，备选限额检查与超额 DCA 排期 | M1 | ORIGINAL_REQUEST §R2 |
| 3 | QDII Valuation Correction | 对比底层基准（sh513500/gb_inx/sh518880），绝对偏差 > 1.5% 时以基准 * 0.95 覆盖纠偏 | M1 | ORIGINAL_REQUEST §R2 |
| 4 | US Index Prefix Repair | 修复 `fetch_realtime_index_quote()` 对美股代码 `gb_` 的前缀拼接 Bug | M1 | Survey Report (Explorer 1) |
| 5 | Clear C3 Static Weight Hijack | 拔除 C3 硬编码常数 `0.38/0.30/0.14/0.12/0.06`，全档位 100% 动态计算 | M2 | ORIGINAL_REQUEST §R3 |
| 6 | 3-Stage Attack/Defense Loop | 左侧极值超卖逆向吸筹、右侧施密特迟滞锁定、右侧极端超买阶梯止盈 | M2 | ORIGINAL_REQUEST §R3 |
| 7 | Ladder Fee Alignment | 在回测与实盘算子中完整对齐 7天/30天/180天 阶梯赎回费 | M2 | ORIGINAL_REQUEST §R3 |
| 8 | Suitability 4D Evaluator | `evaluate_today_rebalance_suitability` 返回 3 级裁决与四维白话字典 `reasons_4d` | M3 | ORIGINAL_REQUEST §R4 |
| 9 | Rebalance Modes & Consequences | `simulate_rebalance_modes_and_consequences` 输出温和与强行两模式及四大后果量化矩阵 | M3 | ORIGINAL_REQUEST §R4 |
| 10 | Stock Overlap Exemption | `calculate_stock_overlap_matrix` 豁免双红利对与限购对，计算 `max_non_diag_unexcused` | M3 | ORIGINAL_REQUEST §R4 |
| 11 | Red-Team Unit Test Suite | 针对 R1~R4 真实断言的完整测试覆盖（11 组对抗测试用例） | M4 | ORIGINAL_REQUEST §R5 |
| 12 | Anti-Cheating & Invariants | 严守 4 大裁判基建，无 time.sleep，无硬编码日历年份，前端无猴子补丁 | M5 | ORIGINAL_REQUEST §R1 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | 实时限购、瀑布拆单与 QDII 纠偏 (Agent-1) | `portfolio_manager.py` | none | DONE |
| M2 | 清除静态权重劫持与三段式攻防闭环 (Agent-2) | `strategy_bridge.py`, `data_loader.py` | none | DONE |
| M3 | 调仓适宜度裁决、四大后果推演与底仓豁免 (Agent-3) | `strategy_bridge.py`, `portfolio_manager.py` | M1, M2 | DONE |
| M4 | 红队反作弊与单元测试覆盖 (Agent-4) | `tests/` | M1, M2, M3 | DONE |
| M5 | 阶段一门禁双轨独立终审 (Reviewer + Challenger + Auditor) | 全量工程与测试套件 | M4 | DONE |

## Interface Contracts
### 1. `portfolio_manager.fetch_realtime_fund_quota(fund_code: str) -> Dict[str, Any]`
- 返回: `{"fund_code": code, "status": "开放申购"|"限制大额"|"暂停申购", "daily_limit": float, "is_limited": bool}`
- 异常安全: 网络失败时自动读取本地 SQLite 缓存或 `data/master/fund_trading_rules.parquet`

### 2. `portfolio_manager.generate_zero_start_blueprint(investment_amount, tier, ...)`
- 动态拆单: 首选 `min(target, quota["daily_limit"])`，`action_guide: f"单日限额¥{int(quota['daily_limit'])}·已拆单"`
- 备选承接: 备选检查配额，未限购显示 `承接超额·不限购正常买`，超额输出 `dca_plan`

### 3. `strategy_bridge.compute_dynamic_tier_weights(tier, market_snapshot)`
- 100% 动态，随 Hedge 专家话语权与 EWMA 波动率动态演进，单调性约束
- 三段式触发调整仓位

### 4. `strategy_bridge.evaluate_today_rebalance_suitability(pm, active_tier="C3") -> Dict[str, Any]`
- 返回: `{"verdict_level": "SUITABLE"|"HOLD_ON"|"FORBIDDEN", "verdict_title": str, "reasons_4d": {"market_position_reason": str, "clock_window_reason": str, "deviation_utility_reason": str, "lockup_fee_reason": str}}`

### 5. `strategy_bridge.simulate_rebalance_modes_and_consequences(pm, active_tier="C3") -> Dict[str, Any]`
- 返回: `{"mode_gentle": {...}, "mode_forced": {...}}`，每个包含 `consequences`: `fee_loss`, `in_transit_risk`, `risk_shift`, `lockup_reset`

### 6. `portfolio_manager.calculate_stock_overlap_matrix(...)`
- 豁免对: `frozenset({"100032", "005561"})` 与 `frozenset({"050025", "001071"})`
- 返回包含: `"max_non_diag_unexcused": float`
