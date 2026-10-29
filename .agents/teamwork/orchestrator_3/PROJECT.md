# Project: AGY2_FundAdvisory 架构级进化与通用量化重构

## Architecture
- **架构范式**: 底层通用量化模型驱动、零硬编码规则引擎、四阶推演白盒交互。
- **模块边界**:
  - `strategy_bridge.py`: 宏观流动性与衍生品桥接、动态风险预算模型 (`compute_dynamic_tier_weights`)、双向变盘网格点位推导 (`get_rebalance_grid_status`)。
  - `portfolio_manager.py`: 三层通用财务排雷引擎 (`screen_fund_look_through_risk`)、全市场通用资产分类解析器 (`classify_fund_asset_class`)、真多因子六维选基动态评分正规化、账户账本管理与建仓执行。
  - `app_gui.py`: 四阶推演白盒（1.2~1.8s 舒适递进反馈、4 个独立面板）、顶部 7 张核心卡片零截断与 ⓘ 悬停、《三句话看懂本方案》三栏作战卡片、9 列建仓单与存量调仓单。
  - `tests/`: AST 静态反硬编码审计、动态风险预算单调性测试、双向变盘点位测试、AppTest 端到端回归。
- **物理安全红线**: `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py` 4 个裁判基建文件 100% 保持只读、未修改。

## Code Layout
- `AGY2_FundAdvisory/strategy_bridge.py` (Exclusive Owner: Agent-1)
- `AGY2_FundAdvisory/portfolio_manager.py` (Exclusive Owner: Agent-2)
- `AGY2_FundAdvisory/app_gui.py` (Exclusive Owner: Agent-3)
- `AGY2_FundAdvisory/tests/` (Exclusive Owner: Agent-4, target file: `tests/test_architecture_m3.py`)

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | C1~C5 通用动态风险预算模型 | 在 `compute_dynamic_tier_weights` 中以目标波动率与最大回撤为边界，根据市场三态（进攻/收息/防御）自适应动态调节，严格满足 C1 < C2 < C3 < C4 < C5 风险单调性 | M1 (Agent-1) | Survey / R2 |
| 2 | 双向变盘触发点位修复 | `get_rebalance_grid_status` 基于 MA20/60/120 真实位置，确保突破进攻线 > 现价、跌破防守线 < 现价，彻底消除 4180.5/4053.0 倒挂 | M1 (Agent-1) | Survey / R5 |
| 3 | 宏观与衍生品自适应决策桥接 | 将 DR007、利差、期指贴水与期权 IV 深度融入动态权重调节与防御降仓逻辑，剔除静态权重字典 | M1 (Agent-1) | Survey / R2 |
| 4 | 三层通用基本面财务排雷 | 彻底剔除 77 只金融股硬编码，实现申万行业金融识别、重资产硬科技/公用事业现金流校验 (CFO>0) 以及高现金高息真伪造假排查 | M2 (Agent-2) | Survey / R3 |
| 5 | 全局统一资产分类解析器 | 实现 `classify_fund_asset_class`，基于基金名称、类型、指数与行业动态归类，彻底消灭 app_gui.py 中的静态 `cat_map` | M2 (Agent-2) | Survey / R3 |
| 6 | 真多因子六维选基动态评分 | 接入 DuckDB 真实数据并经 Min-Max/Z-Score 映射至 0~100 分，剔除 `FUND_SIX_DIMENSION_PROFILE` 伪造打分字典 | M2 (Agent-2) | Survey / R2 |
| 7 | 四阶量化推演工作流白盒 | 1.2~1.8 秒舒适递进演算反馈，4 个独立可折叠白盒面板（漏斗海选+PK明细、四维信号卡片、实境回测、交易摩擦与拆单路由） | M3 (Agent-3) | Survey / R4 |
| 8 | 顶部 7 张卡片零截断与白话翻译 | 主数值 15~16px 紧凑单行无省略号，通俗标签 + ⓘ 悬停原理解析 | M3 (Agent-3) | Survey / R5, R6 |
| 9 | 《三句话看懂本方案》三栏作战卡片 | 收益引擎拆解、跨资产对冲反脆弱机制、极端浮亏与两条铁律，位于步骤二与三之间 | M3 (Agent-3) | Survey / R5 |
| 10 | 执行单与调仓表 9 列精简 | 保持 `cols_9` 声明，最后一列 15 字以内指令 + 表头 ⓘ 悬停；存量调仓单 9 列并引入醒目操作图标 | M3 (Agent-3) | Survey / R6 |
| 11 | AST 静态反硬编码红队审计测试 | 遍历 AST 校验 `portfolio_manager.py`、`strategy_bridge.py`、`app_gui.py` 无 6 位股票代码 if/else 分支及静态 `cat_map` | M4 (Agent-4) | Survey / AC |
| 12 | 动态风险预算单调性与攻防测试 | 针对牛市、震荡、熊市三组输入，断言 C1 至 C5 目标权益仓位严格单调 `C1 < C2 < C3 < C4 < C5` 且自适应调仓 | M4 (Agent-4) | Survey / AC |
| 13 | 双向变盘点位无倒挂测试 | 断言任意市场点位下 `breakdown < current < breakout` 恒成立 | M4 (Agent-4) | Survey / AC |
| 14 | 9列无截断 AppTest 端到端渲染测试 | 验证步骤三建仓执行单 9 列、存量调仓单 9 列、顶部 7 张卡片无文字截断，且全档位 AppTest 渲染无异常 | M4 (Agent-4) | Survey / AC |
| 15 | 全量 222+ 测试回归与 8501 端口服务重启 | 确保既有 222 项测试及新增用例 100% 通过，平滑重启本地 8501 端口 Streamlit 服务 | M4 (Agent-4) | Survey / AC |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | strategy_bridge.py 架构进化 | 动态风险预算模型、攻防状态机自适应、双向网格点位修复 | none | DONE |
| M2 | portfolio_manager.py 架构进化 | 三层通用财务排雷、统一资产分类器、真多因子六维评分 | none | DONE |
| M3 | app_gui.py 交互架构进化 | 移除静态 cat_map、四阶推演白盒、顶部零截断、三句话作战卡片、9列表格精简 | M1, M2 接口对齐 | DONE |
| M4 | tests/ 自动化审计与全量回归 | AST 静态反硬编码审计、单调性与点位测试、AppTest 端到端回归、重启服务 | M1, M2, M3 | DONE |

## Interface Contracts
### `portfolio_manager.py` ↔ `app_gui.py`
- `PortfolioManager.classify_fund_asset_class(fund_code: str, fund_name: Optional[str] = None) -> str`:
  - 返回归一化大类名称：`"纯债固收"`, `"黄金对冲"`, `"美股海外对冲"`, `"A股红利高股息"`, `"A股红利低波"`, `"科技成长进攻"`, `"中小盘成长"`, `"中盘均衡"`, `"核心蓝筹"`。若无法识别则返回 `"其他权益资产"`，杜绝误归为 `"其他存量资产"`。
- `PortfolioManager.screen_fund_look_through_risk(fund_code, ...)`:
  - 返回包含 `double_high_risk`, `avg_risk_score`, `stock_details` 的诊断字典，内部无硬编码股票代码。

### `strategy_bridge.py` ↔ `portfolio_manager.py` / `app_gui.py`
- `StrategyBridge.compute_dynamic_tier_weights(history_df, tier: str, market_snapshot: dict) -> Dict[str, float]`:
  - 输入当前行情截面与档位，返回动态标的及权重字典，严格满足目标波动率与回撤约束，且 $\text{Equity}(C1) < \text{Equity}(C2) < \text{Equity}(C3) < \text{Equity}(C4) < \text{Equity}(C5)$。
- `StrategyBridge.get_rebalance_grid_status() -> dict`:
  - 必须返回包含 `surge_threshold_c300`, `breakdown_threshold_c300`, `c300_current` 的字典，严格保证 `breakdown_threshold_c300 < c300_current < surge_threshold_c300`。
- `StrategyBridge.generate_zero_start_blueprint(tier, plan_capital, ...)`:
  - 统一定义于 `strategy_bridge.py`，调用 `compute_dynamic_tier_weights` 动态生成建仓蓝图。

### `tests/` ↔ All Source Files
- `tests/test_architecture_m3.py` 将直接作为裁判红队，利用 `ast` 模块深度解析 `strategy_bridge.py`、`portfolio_manager.py`、`app_gui.py` 的抽象语法树，扫描硬编码股票代码与静态 cat_map。
