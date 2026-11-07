# Project: G5 世代真量化投顾工程闭环

## Architecture
- **核心计算层 (`AGY2_FundAdvisory/advisory_engine.py`)**:
  - `SmartExecutionDCAEngine.get_fund_real_volatility_and_bias`: 本地时序四级湖仓穿透计算单基真实 20 日波动率与 MA20 乖离率；
  - `SmartExecutionDCAEngine.calculate_vwap_execution_slippage`: 消除 0.04/0.14/0.18 假常数，使用单基真实波动率与单基乖离率；
  - `SmartExecutionDCAEngine.get_historical_inflection_ruler`: 提供历史三大拐点与当前水位的结构化对照尺；
  - `SmartExecutionDCAEngine.evaluate_tail_valuation_anomaly`: 基于实时估值 `gszzl` 与单基日均波幅 `sigma_day` 进行 14:30 异动预警。
- **持仓管理层 (`AGY2_FundAdvisory/portfolio_manager.py`)**:
  - `PortfolioManager.calculate_portfolio_cushion_and_stress_model`: 计算各标的历史 Beta、组合加权 Beta、综合安全垫厚度、破净临界下跌幅度和 3%/5%/10% 大盘急跌情景推演。
- **桥接协调层 (`AGY2_FundAdvisory/strategy_bridge.py`)**:
  - 桥接持仓安全垫推演模型与历史拐点对照尺，向下兼容所有调用方。
- **交互呈现层 (`AGY2_FundAdvisory/app_gui.py`)**:
  - 首屏与 Tab 1 渲染历史三大拐点对照尺；
  - Tab 2 概览区渲染浮盈安全垫抗震承压与破净临界看板；
  - Tab 2 调仓执行表与 Tab 1 定投计划渲染单基差异化损耗与尾盘异动标签，遵循复杂度守恒与移动端 CSS 自适应。

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| F1 | 单基真实 20 日年化波动率与乖离率穿透 | 本地多级时序穿透，消除 0.04/0.14/0.18 假常数，单基真实年化波动率与自身 MA20 乖离率 | M1 | Survey 1 |
| F2 | 历史三大牛熊拐点对照尺数据模型 | 2021见顶(0.50x)、2022恐慌底(1.93x)、2024反转底(1.94x) 与今日实时水位对照模型 | M1 | Survey 2 |
| F3 | 浮盈安全垫抗震承压与本金破净临界点模型 | 真实历史 Beta、组合加权 Beta、综合安全垫厚度、大盘破净跌幅/回本涨幅及 3 级承压推演 | M1 | Survey 3 |
| F4 | 14:30 尾盘实时估值异动预警算法 | 基于盘中真实估值 `gszzl`、20 日日均波动幅度 `sigma_day` 与乖离率触发防追高/黄金坑 | M1 | Survey 2 |
| F5 | 定投规划与执行穿透传参优化 | `plan_smart_dca` 穿透各单基真实波动率与自身乖离率 | M1 | Survey 1 |
| F6 | 前端历史三大拐点对照条接入 | 首屏与 Tab 1 一行式 4 节点紧凑胶囊对照条渲染，精简冗余文案 | M2 | Survey 2 |
| F7 | Tab 2 浮盈安全垫与破净临界看板接入 | Tab 2 概览区展示加权 Beta、安全垫厚度、破净点位及 -3%/-5%/-10% 承压推演卡片 | M2 | Survey 3 |
| F8 | Tab 2 调仓与定投尾盘异动标签与差异化损耗 | 调仓执行表与定投计划实操要点接入异动标签、差异化损耗基点及 640px 紧凑 CSS | M2 | Survey 1, 2 |
| F9 | 多模态视觉走查审查 | 通过 /browser 走查四大 Tab、亮暗色主题、640px 视口无错位无重叠 | M3 | System Msg |
| F10 | 扩展全量自动化测试套件 | 在 `tests/test_g3_evolution_loop.py` 中新增 G5 专项测试，全量 100% 通过 | M3 | Survey 3 |
| F11 | 独立法证审计核验 | 四大裁判文件只读未篡改、无常数伪造、无数据伪造 | M3 | System Msg |
| F12 | 版本归档与 G6 世代指令生成 | 更新 GEMINI.md/PROGRESS_LOG.md，git commit，tag v3.5-G5，push，生成 G6 指令 | M3 | System Msg |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | 量化核心算法升级与穿透计算 | F1, F2, F3, F4, F5 (`advisory_engine.py`, `portfolio_manager.py`, `strategy_bridge.py`) | none | DONE |
| M2 | 前端实盘界面联动与紧凑排版 | F6, F7, F8 (`app_gui.py`) | M1 | DONE |
| M3 | 视觉走查、全量测试回归与交付 | F9, F10, F11, F12 (browser inspection, `test_g3_evolution_loop.py`, audit, git tag) | M2 | DONE |

## Code Layout
- `AGY2_FundAdvisory/advisory_engine.py`: 量化投顾决策大脑（单基波动率/乖离率穿透、历史拐点对照尺、14:30 尾盘估值异动预警、DCA 穿透）
- `AGY2_FundAdvisory/portfolio_manager.py`: 持仓资产管理器（单基 Beta、组合加权 Beta、综合安全垫厚度、破净临界点、大盘急跌压力推演）
- `AGY2_FundAdvisory/strategy_bridge.py`: 策略桥接协调层（历史拐点对照尺桥接、安全垫与压力推演桥接）
- `AGY2_FundAdvisory/app_gui.py`: Streamlit 买方投顾终端（历史拐点胶囊条、安全垫承压看板、尾盘异动标签与自适应 CSS）
- `tests/test_g3_evolution_loop.py`: G3-G5 进化回归测试套件
- 裁判文件（绝对只读）：`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`
