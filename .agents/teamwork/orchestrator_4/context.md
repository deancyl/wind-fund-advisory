# Context — 阶段一重构关键上下文与接口约束

## 1. 物理安全红线（零容忍）
- 系统只读裁判文件（严禁修改、触碰或写入）：
  - `judge_engine.py`
  - `holdout_vault.py`
  - `AGENT_SPEC.md`
  - `tests/test_infra.py`
- 严禁 `time.sleep` 伪造耗时。
- 严禁将 `daily_limit` 写死为 500 或 1000。
- 严禁 C3 档位硬编码常数绕过动态权重函数。
- 严禁前端打猴子补丁或使用测试硬编码字典应付断言。

## 2. 核心架构与模块分工
- `portfolio_manager.py`:
  - `fetch_realtime_fund_quota(fund_code: str)`: 调用 `akshare.fund_purchase_em()`，本地 SQLite/Parquet 带日期戳缓存。
  - 多级瀑布流拆单算法与 `action_guide` 动态说明。
  - QDII 与基准实时涨跌幅对比纠偏（绝对偏差 > 1.5% 时以基准 * 0.95 覆盖）。
  - `calculate_stock_overlap_matrix()`: 双红利底仓对 `{"100032", "005561"}` 与限购伴生对 `{"050025", "001071"}` 协同豁免。
- `strategy_bridge.py` & `data_loader.py`:
  - C1~C5 目标基金配比 100% 动态算出。
  - 三段式攻防：左侧超卖极值吸筹（ERP >= 75% 且 bias_20 <= -4.5% 从纯债划拨 10%~15% 增配宽基 011613/001053）；右侧施密特迟滞（[-1.5%, +1.2%]）；右侧极端超买止盈（bias_20 >= +6.5% 或 crowding_warning 时削减 30%~35% 进攻仓位至纯债 002351 与红利 005561）。
  - 7天/30天/180天 阶梯赎回费。
  - `evaluate_today_rebalance_suitability`（四维原因白话字典与三级裁决）。
  - `simulate_rebalance_modes_and_consequences`（温和与强行两模式、四大后果精算）。
- `tests/`:
  - 红队反作弊单元测试与全量断言。
