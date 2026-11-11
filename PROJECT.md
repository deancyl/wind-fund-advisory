# Project: G17 世代五维/十维全息投顾决策大脑与移动端极致体验闭环

## Architecture
- **Web UI & Visualization Layer**: `AGY2_FundAdvisory/app_gui.py`
  - 手机端 (<=768px, <=640px) 顶层 4 个主导航强制重构为 **2x2 双排四宫格** (`grid-template-columns: repeat(2, 1fr) !important; gap: 6px !important;`)，按钮高度 `40px !important; font-size: 14px !important;`，彻底消灭「🔍 穿透工具」截断溢出。
  - 顶部 4 张全局指标卡在移动端设为 **2x2 田字格紧凑布局**，垂直空间压缩 50%。
  - 首屏「五维备忘录」与「今日投顾参谋折叠框」合流为统一的 **「🧭 首席投顾今日裁决台」**：
    - 首屏默认直显区总高度严格控制在 **≤ 110px**：第一行「今日核心定调 + 仓位推导因果链 + 数据截面时间戳」（防文字竖排挤压）；第二行以 **5 个紧凑胶囊（桌面端 1行5列，移动端 2列流式）** 展示宏观政策、国际汇率、产业击球区、持仓病灶、14:30尾盘指令的 ≤20 字精要人话结论。
    - 详细十维逻辑、Top 3 机会雷达卡与十三维风控体检收纳于「🔭 展开十维深度逻辑、Top 3 机会雷达与十三维风控体检详情」展开抽屉。
  - **存量账本自动路由**：在 `switch_active_ledger` 中，当切换至含存量持仓的账本（如 29 基存量组合）时，自动注入跨 Tab 跳转指令跳转至 `tab_index: 1` (`💼 持仓调仓`)，并自动激活诊断与调仓卡片。
  - **表格核心列优先**：Tab 0 与 Tab 1 表格排布强制将「基金代码/名称、金额/市值、盈亏率/目标占比、建议操作/实操指引」锁定在前 3~4 列；收拢表格底部 5 个堆叠长条，无折价时自动折叠冗余流动性表。
- **Quant Strategy & Cross-Market Data Engine Layer**: `AGY2_FundAdvisory/advisory_engine.py`, `data_loader.py`
  - **彻底拔除 5 大静态假常数与断裂字典键** (`628.5`, `-0.25%`, `7.2450`, `1.6258`, `4.40%`)。
  - 打通本地 Parquet 湖仓与实时数据源：
    - 10Y 国债收益率与中美利差：直接读取 `data/macro/bond_zh_us_rate.parquet` 最新交易日 `cn_yield_10y` (1.6376%)、`us_yield_10y` (5.0000%)、中美利差 (-336.2bp) 及近 20 交易日变动 bp；
    - 黄金与全球股市联动：区分场内黄金 ETF 518880 (¥8.29/份) 与 AU9999 现货总回报序列 (1479.55)，绝不混淆；从 `data/global/global_indices.parquet` 读取纳斯达克 (`IXIC` +0.82%, Bias -2.46%)、标普500 (`SPX` +0.70%)、恒生科技 (`HSTECH` -0.37%, Bias -6.32%)；
    - 离岸人民币汇率：调用 `DataLoader.fetch_realtime_usdcnh_fx(use_cache=True)`，离线降级读取 `data/global/fx_rates.parquet` (6.6676)，绝不回退至 7.2450；
  - **实装十维投顾量化投票模型**：涵盖 ①宏观经济、②货币政策、③股债ERP、④国际联动、⑤外汇锁汇、⑥产业估值、⑦资金情绪、⑧技术信噪比、⑨历史同温层、⑩期权IV与黑天鹅，输出量化评分、多空投票与仓位增减项。
  - **生成透明仓位推导因果链**：`基准权益中枢 60% + ERP极低估溢价(+10%) + 货币宽松(+5%) + 结构性机会(+5%) - 美债倒挂约束(-3%) = 当前建议权益仓位 77% (防守固收 23%)`。
- **Portfolio & Execution Layer**: `AGY2_FundAdvisory/portfolio_manager.py`, `strategy_bridge.py`
  - **长截图双因子交叉锁定**：从 OCR 文本中恢复提取 `yesterday_pnl`，建立会计公式 $R_{\text{yesterday}} = \frac{\text{yesterday\_pnl}}{\text{market\_value} - \text{yesterday\_pnl}}$，以「名称关键字 + 昨日收益率（容差 ≤ 0.3%）」双因子交叉锁定 28,177 只基金中带省略号截断的标的；预览表增加存疑标的修改助手。
  - **Tab 3 全真交易摩擦扣减明细栏**：在时光机盲测与 29 基重构对比中，显式列出申购费、阶梯赎回费、C类销售服务费 (0.40%/年)、T+1/T+2 在途损耗与限购拆单。实证 29 基重构为 6 纯 A 类组合后最大回撤由 -17.24% 压降至 -16.76%，最大回撤回本天数由 452 交易日缩短至 394 交易日（节省 58 交易日）。
- **Physical Safety Redline Layer**:
  - `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`（物理只读红线，SHA-256 锁定，严禁修改）。
  - `DataLoader.simulate_execution` 默认函数签名与默认扣费逻辑保持绝对原生。

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | 拔除五维备忘录 5 大静态假常数 | 彻底清除 628.5, -0.25%, 7.2450, 1.6258, 4.40%，打通 bond_zh_us_rate, global_indices, fx_rates 与实时接口 | M1 | ORIGINAL_REQUEST §二.1 |
| 2 | 十维投顾量化投票与仓位因果链 | 实现 10 个显式投票维度量化评分、多空裁决与仓位增减项，输出透明人话因果推导公式 | M1 | ORIGINAL_REQUEST §二.2 |
| 3 | 手机端 2x2 主导航与顶栏田字格 | CSS @media <=768px 强制设为 2x2 双排四宫格与 2x2 紧凑指标卡，消灭「🔍 穿透工具」截断 | M2 | ORIGINAL_REQUEST §三.2 |
| 4 | 首屏「🧭 首席投顾今日裁决台」合流 | 双框合流，默认直显区总高度 ≤ 110px，含定调+公式+5精炼胶囊，深层十维逻辑收拢于展开抽屉 | M2 | ORIGINAL_REQUEST §三.1 |
| 5 | 存量账本自动路由至 💼 持仓调仓 | 在 switch_active_ledger 中检测存量标的，自动注入 pending_cross_tab_jump 跳转 Tab 1 并展开 29 基诊断 | M2 | ORIGINAL_REQUEST §三.3 |
| 6 | 表格核心列优先与底部工具栏紧凑化 | 表格前 3-4 列固定为代码/名称、金额、盈亏/占比、操作建议，收拢底部 5 长条并自适应隐藏全 0 冗余表 | M2 | ORIGINAL_REQUEST §一.1, 三.2 |
| 7 | 长截图双因子交叉验真匹配器 | 提取昨日收益计算收益率，以名称关键字+昨日收益率双因子锁定 28,177 基金截断标的，增加预览修改助手 | M3 | ORIGINAL_REQUEST §四.1 |
| 8 | Tab 3 全真交易摩擦账单与回测明细 | 显式输出 5 大公募摩擦扣减明细栏，实证 29 基重构 6 基在最大回撤（-16.76% vs -17.24%）与回本天数（394d vs 452d）优势 | M3 | ORIGINAL_REQUEST §四.2 |
| 9 | 物理安全红线锁定与 Delta 测试套件 | 验证裁判文件 SHA-256，编写 tests/test_g17_*.py，验证假常数清零断言与全量回归 | M4 | ORIGINAL_REQUEST §一.2, 门禁契约 |
| 10| 8501 服务重启与 /browser 双视口验收 | 终止旧进程，启动服务，在 1920x1080 与 390x844 截图比对核验，执行 Git 归档 v4.7-G17 并输出 G18 指令 | M4 | ORIGINAL_REQUEST §五 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | 拔除静态假常数、打通真实数据湖仓与十维因果传导 | Features 1-2 (`advisory_engine.py`, `data_loader.py`) | none | COMPLETED |
| M2 | 手机端 2x2 四宫格、首屏裁决台合流 (<=110px)、存量自动路由与表格优化 | Features 3-6 (`app_gui.py`) | none | COMPLETED |
| M3 | 长截图双因子交叉验真与 Tab 3 全真公募摩擦扣减账单 | Features 7-8 (`portfolio_manager.py`, `strategy_bridge.py`, `app_gui.py`) | none | COMPLETED |
| M4 | 针对性测试、全量回归、裁判审计、8501 服务探针、Git 归档与 G18 生成 | Features 9-10 (`tests/`, service restart, git tag v4.7-G17) | M1, M2, M3 | COMPLETED |

## Code Layout
- `AGY2_FundAdvisory/advisory_engine.py`: 十维投顾量化投票与因果传导公式、拔除静态常数
- `AGY2_FundAdvisory/data_loader.py`: 真实 Parquet 湖仓对接 (bond_zh_us_rate, global_indices, fx_rates, 518880 ETF)
- `AGY2_FundAdvisory/app_gui.py`: 2x2 主导航网格 CSS、首屏裁决台 (<=110px)、存量账本跨 Tab 路由、表格列排布
- `AGY2_FundAdvisory/portfolio_manager.py`: 长截图昨日收益提取与双因子交叉锁定
- `AGY2_FundAdvisory/strategy_bridge.py`: Tab 3 全真公募交易摩擦明细计算与 29 基对比指标
- `tests/test_g17_advisory_real_data_and_ten_dimension.py`: 假常数绝迹与十维因果测试
- `tests/test_g17_friction_and_screenshot.py`: 双因子长截图与全真摩擦账单测试
- `tests/test_g17_ui_mobile_and_ledger_routing.py`: 2x2 移动端与存量账本自动路由 AppTest 测试
