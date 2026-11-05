# Project: Wind 投顾系统多账本体系与代码审计深度整改 (Multi-Ledger System & Anticheat Production Hardening)

## Architecture
- **Multi-Ledger Persistent Storage Layer**:
  - `AGY2_FundAdvisory/multi_ledger_manager.py`: 管理 `data/ledgers_index.json` 与各独立账本文件。
  - 主实盘账本：保持根目录 `portfolio_ledger.json` (`id="main_live"`, `name="主实盘账本"`, `type="live"`，硬性防删除保护)。
  - 派生/沙盒账本：存放于 `data/ledgers/<ledger_id>.json`，配对隔离 SQLite 数据库 `data/ledgers/<ledger_id>.db`（防止 `save_state` 时执行 `DELETE FROM holdings` 导致主实盘持仓在数据库中被清空）。
- **Web UI & Global State Hot-Assembly Layer**:
  - `AGY2_FundAdvisory/app_gui.py`:
    - `st.session_state.active_ledger_id` 绑定当前激活的 `PortfolioManager` (`st.session_state.pm`)。
    - 切换账本时：全局 `pm`、顶部第 4 张卡片（总资产与今日预估）、右翼主动风险哨、Tab 2、Tab 3、Tab 4 100% 同步重定向；自动将账本 `default_tier` 赋给 `active_tier_val`，清空 `tab2_diag_cache` 与 `tab2_rebal_cache`。
    - Tab 2 顶部多账本管理吧台：单行整合当前账本选择器、新建 Popover、克隆 Popover、管理 Popover、独立沙盒环境警示横幅。
    - Tab 1 步骤三初始持仓保存：双轨选项「覆盖写入当前激活账本」vs「🆕 另存为全新独立账本」。
- **Quant Rebalancing & Scenario Engine**:
  - `AGY2_FundAdvisory/strategy_bridge.py` & `portfolio_manager.py`:
    - 调仓场景参数传入：`scenario_mode`, `new_cash_amount`, `withdraw_cash_amount`, `freeze_reserved_cash`, `core_anchor_code` 真实贯通至底层并在缓存键 `cur_pool_sig` 中签名。
    - `new_cash_only`: 卖出金额严格为 0，买入金额严格等于 `new_cash_amount`。
    - `withdraw_cash_only`: 买入金额严格为 0，赎回金额严格等于 `withdraw_cash_amount`，优先免赎 C/A 类，严禁卖出 `<7` 天份额。
    - `freeze_reserved_chk`: 扣除 `pm.reserved_batch_cash`。
- **Analog Matching & Attribution Engine**:
  - Tab 3 顶部横幅动态统计：从 `analog_tab2["matches"]` 动态计算 60 日相对超额胜率、平均相对超额、策略平均收益、平均最大回撤。
  - 3 张历史卡片动态归因文案：依实际收益关系分别输出“右侧顺势共振”、“逆势抗跌护盾”、“防守底仓代价”。
- **Look-Through & Asset Classification Engine**:
  - `portfolio_manager.py`: 4 个穿透底层函数增加 `holdings_override: Optional[Dict[str, Any]] = None`。
  - 导出 `HoldingItem` 类并支持 `market_value` 自动折算与属性兼容。
  - `classify_fund_asset_class`: 深度反查各核心基金池与赛道池，精准分类医药、白酒、银行、恒科、半导体、美股QDII、红利低波、宽基、纯债、黄金，消除“其他权益资产”。
  - Tab 4 前端打通：向底层传入 `active_examine_holdings`，聪明钱循环遍历 `active_examine_holdings.items()`。
- **14-Sector Radar Real Dynamics Engine**:
  - `OpportunityRadarEngine._calc_dynamic_sector_metrics`: 多级抽取流水线（Parquet -> DuckDB `v_indices` -> NAV Cache -> 对齐矩阵），确保 14 个赛道指标基于真实历史净值算出，无一共享 (0.50, 1.0, 85.0)。
  - `get_sector_valuation_percentile`: 删除空 `pass` 与 40.0/52.0 写死常数，基于真实利差/均线偏离/历史序列动态计算分位。
- **Active Risk Sentry & Compact UI**:
  - 同维度预警 (>= 2 只) 自动聚合为单张卡片，提供“一键批量锁定”按钮。
  - 预警列表置于 `max-height: 320px; overflow-y: auto` 滚动容器中。
- **Physical Safety Redline Baseline**:
  - 4 大裁判文件 SHA256 绝对锁定：`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`。
  - `DataLoader.simulate_execution` 默认签名与费率逻辑严格保留。

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | MultiLedgerManager 底层持久化与管理 | 增删改查克隆、家庭资产汇总、主实盘删除物理保护、独立 SQLite DB 派生 | M1 | R1 |
| 2 | 多账本全站热装配与跨 Tab 贯通 | active_ledger_id 全局绑定，顶部卡片4、预警哨、Tab 2/3/4 同步，缓存重置 | M1 | R2 |
| 3 | Tab 2 多账本管理吧台与沙盒提示 | 单行多账本吧台（选择器、新建、克隆、管理 Popover）及沙盒警示横幅 | M1 | R2 |
| 4 | Tab 1 双轨保存初始持仓 | 覆盖写入当前账本 vs 另存为全新独立账本 | M1 | R2 |
| 5 | 四大调仓场景前后端闭环与缓存贯通 | scenario_mode 与金额入缓存签名，真实传入计算，UI 控件前置 | M2 | R3 |
| 6 | new_cash_only 免赎补仓真实执行 | 卖出严格为 0，买入总额严格等于 new_cash_amount，零赎回费 | M2 | R3 |
| 7 | withdraw_cash_only 智能提现真实执行 | 买入严格为 0，赎回总额严格等于 withdraw_cash_amount，避开 <7d 标的 | M2 | R3 |
| 8 | freeze_reserved_cash 预留网格资金冻结 | 真实扣除 pm.reserved_batch_cash | M2 | R3 |
| 9 | Tab 3 历史相似匹配动态指标统计 | 真实计算 60 日超额胜率、相对超额、策略收益、最大回撤，清零假常数 | M2 | R4 |
| 10 | 3 张历史卡片动态镜鉴归因文案 | 依真实收益关系输出顺势共振、抗跌护盾、防守代价 3 类归因 | M2 | R4 |
| 11 | Tab 4 穿透底层函数 holdings_override 注入 | 4 个函数支持 holdings_override，导出 HoldingItem 类 | M3 | R5 |
| 12 | Tab 4 聪明钱与视图真实联动 | 传入 active_examine_holdings，聪明钱遍历当前选择持仓 | M3 | R5 |
| 13 | classify_fund_asset_class 精准资产分类 | 反查基金池，精准识别 14 赛道、宽基、纯债、黄金，清零“其他权益资产” | M3 | R5 |
| 14 | 14 赛道雷达真实历史净值动态指标 | 多级抽取 DuckDB/Parquet，消除 (0.50, 1.0, 85.0)，各赛道动态分化 | M3 | R6 |
| 15 | get_sector_valuation_percentile 去 pass 去常数 | 删除 pass 与 40.0/52.0，基于利差/均线偏离/历史序列真实计算 | M3 | R6 |
| 16 | 双翼主动风险预警哨折叠聚合与批量锁定 | 同维度 >= 2 只自动合并，一键批量加入 tab2_locked_funds | M4 | R7 |
| 17 | 预警哨滚动容器紧凑化 | max-height: 320px; overflow-y: auto 消除垂直拉长 | M4 | R7 |
| 18 | 物理安全红线与 SHA256 锁定 | 4 大裁判文件哈希完好无损，simulate_execution 默认签名完好 | M4 | R8 |
| 19 | 专项防作弊测试 A/B/C/D 闭环验证 | 自动化防作弊测试 100% 通过，pytest 全量测试 100% 通过 | M4 | R8 |
| 20 | Streamlit AppTest 与 8501 服务平滑重启 | 浅色/深色主题全站零报错，端口平滑重启健康探针 HTTP 200 | M4 | R8 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | 多账本体系存储管理与全站热装配 | Features 1-4 (R1, R2): MultiLedgerManager, 独立DB, app_gui active_ledger_id 贯通, Tab 2 吧台, Tab 1 双轨保存 | none | DONE |
| M2 | 四大调仓场景真实性与 Tab 3 动态历史镜鉴 | Features 5-10 (R3, R4): 调仓参数缓存签名与前后端真实闭环, new_cash_only/withdraw_cash_only, Tab 3 动态横幅与 3 卡片归因 | M1 | IN_PROGRESS |
| M3 | Tab 4 组合穿透切换、资产精准分类与 14 赛道雷达真动态 | Features 11-15 (R5, R6): holdings_override 注入, HoldingItem 导出, 资产精准分类, 14 赛道 DuckDB 抽取真动态, 估值分位去 pass | none | PLANNED |
| M4 | 预警哨折叠紧凑化、防作弊测试 A/B/C/D 与验收交付 | Features 16-20 (R7, R8): 预警哨折叠聚合与紧凑滚动, 裁判文件哈希锁定, 专项防作弊测试 A/B/C/D, AppTest, 8501 重启 | M1, M2, M3 | PLANNED |

## Interface Contracts
### M1: MultiLedgerManager Interface
- **Class**: `MultiLedgerManager` in `AGY2_FundAdvisory/multi_ledger_manager.py` (re-exported in `portfolio_manager.py`)
- **Signatures**:
  - `list_ledgers() -> List[Dict[str, Any]]`
  - `create_ledger(name: str, base_cash: float = 100000.0, ledger_type: str = "sandbox", default_tier: str = "C3") -> str`
  - `clone_ledger(src_id: str, target_name: str) -> str`
  - `rename_ledger(ledger_id: str, new_name: str) -> bool`
  - `delete_ledger(ledger_id: str) -> bool` (fails/raises on `main_live`)
  - `get_all_ledgers_summary() -> Dict[str, Any]` (total_assets, total_pnl, total_funds, ledgers_breakdown)
  - `get_pm(ledger_id: str) -> PortfolioManager`
- **Storage**:
  - Main live: `portfolio_ledger.json` (`id="main_live"`, `db_path="portfolio_state.db"`)
  - Custom ledgers: `data/ledgers/<id>.json` (`db_path="data/ledgers/<id>.db"`)
  - Index: `data/ledgers_index.json`

### M2: Rebalance Scenarios & Analog Attribution Interface
- **Functions in `strategy_bridge.py` & `portfolio_manager.py`**:
  - `simulate_rebalance_modes_and_consequences(..., scenario_mode="standard", new_cash_amount=0.0, withdraw_cash_amount=0.0, freeze_reserved_cash=False, core_anchor_code="")`
  - `generate_ai_rebalance_orders(..., scenario_mode="standard", new_cash_amount=0.0, withdraw_cash_amount=0.0, freeze_reserved_cash=False, core_anchor_code="")`
  - `cur_pool_sig = (chosen_target_pool, tuple(sorted(tier_target_w.items())), scenario_mode, new_cash_amount, withdraw_cash_amount, freeze_reserved_cash, core_anchor_code)`
- **Invariants**:
  - `new_cash_only`: `all(o["action"] != "SELL" for o in orders)`, `sum(o["amount"] for o in orders if o["action"] == "BUY") == pytest.approx(new_cash_amount)`
  - `withdraw_cash_only`: `all(o["action"] != "BUY" for o in orders)`, `sum(o["amount"] for o in orders if o["action"] == "SELL") == pytest.approx(withdraw_cash_amount)`
- **Analog Matches in `app_gui.py`**:
  - Dynamic calculations over `matches`: `rel_winrate`, `avg_excess_ret`, `strat_avg_ret`, `avg_mdd`.

### M3: Look-Through & Sector Dynamics Interface
- **Signatures in `portfolio_manager.py`**:
  - `calculate_look_through_industry_exposure(..., holdings_override: Optional[Dict[str, Any]] = None)`
  - `calculate_stock_overlap_matrix(..., holdings_override: Optional[Dict[str, Any]] = None)`
  - `calculate_portfolio_penetration_risk(..., holdings_override: Optional[Dict[str, Any]] = None)`
  - `get_portfolio_look_through_stocks_df(..., holdings_override: Optional[Dict[str, Any]] = None)`
  - `HoldingItem` class exported: `HoldingItem(code, name, shares, current_nav, ...)`
  - `classify_fund_asset_class(fund_code: str, fund_name: str = "") -> str`
- **Signatures in `advisory_engine.py`**:
  - `OpportunityRadarEngine._calc_dynamic_sector_metrics(sector_id, ...)`: computes real `er_20`, `bias_20`, `slope_20`, `crowding_score`.
  - `get_sector_valuation_percentile(sector_id, ...)`: dynamically evaluates percentile, no pass or static 40.0/52.0.

### M4: Active Risk Sentry & Verification Interface
- **Signatures in `advisory_engine.py` & `app_gui.py`**:
  - `ActiveRiskSentry.get_aggregated_alerts(alerts) -> List[Dict[str, Any]]`: combines same-dimension alerts (>= 2 funds).
  - Front-end button:批量加入 `tab2_locked_funds`.
  - Tests: `tests/test_anticheat_suite.py` containing Tests A, B, C, D.

## Code Layout
- `AGY2_FundAdvisory/`
  - `multi_ledger_manager.py`: 多账本管理器 (M1)
  - `portfolio_manager.py`: 账本隔离、穿透覆盖、资产分类 (M1, M3)
  - `app_gui.py`: UI 状态绑定、四大 Tab 联动与紧凑化 (M1, M2, M3, M4)
  - `strategy_bridge.py`: 调仓参数闭环与雷达对接 (M2, M3)
  - `advisory_engine.py`: 14 赛道雷达真动态与预警哨聚合 (M3, M4)
- `tests/`
  - `test_infra.py`: 只读测试基线（绝对只读）
  - `test_anticheat_suite.py`: 专项防作弊测试 A/B/C/D (M4)
- `data/`
  - `ledgers_index.json`: 账本元数据索引 (M1)
  - `ledgers/`: 独立账本与独立 SQLite 存储 (M1)
