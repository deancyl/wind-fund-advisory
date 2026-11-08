# Project Scope: G10 Generation (Correlation Stress Defense, Liquidity Haircut & Monte Carlo Stress Testing)

## Architecture
- **Web UI & Visualization Layer**: `AGY2_FundAdvisory/app_gui.py`
  - 首屏双翼看板右翼 (`col_sentry`): 多资产相关性突变预警指示卡与压力测试流动性指标卡片
  - Tab 1 & Tab 2: 大额订单流动性折价明细表与基于 Plotly 3D 的蒙特卡洛压力测试三维分布图
  - 样式适配: 亮色、暗黑主题以及 640px 移动端视口 (零截断、零水平溢出、防 CommonMark 4+ 空格泄露)
- **Quant & Advisory Engine Layer**: `AGY2_FundAdvisory/advisory_engine.py`
  - 升级动态相关性与下行半协方差计算矩阵
  - 当大盘急跌且下行相关系数 > 0.80 时输出相关性压力突变预警并触发流动性平移预案
  - 实装场外公募非线性底层流动性折价惩罚模型 (`calculate_otc_fund_execution_slippage` / `calculate_vwap_execution_slippage`)，严格单调递增，无假常数
- **Portfolio Management & Stress Testing Layer**: `AGY2_FundAdvisory/portfolio_manager.py`
  - `evaluate_dynamic_correlation_mutation`: 跨资产流动性平移预案，定向减仓高估值高波标的（含科技成长进攻），资金平移至 002351 (60%) 与 000216 (40%)，权重归一 $\sum w_i = 1.000000$
  - `simulate_portfolio_cvar_bootstrap`: 基于 Circular Block Bootstrap（块长10天、10,000次重采样），针对 C1-C5 评估 2008 金融危机、2015 流动性踩踏及 2024 初小盘股危机三大极端情景，输出最大回撤预测与流动性变现天数
- **Data & Execution Simulation Layer**: `AGY2_FundAdvisory/data_loader.py`
  - `DataLoader.simulate_execution`: 严格保持默认签名与扣费逻辑只读
  - 季报前五大重仓股 ADV、基金 AUM 与权益仓位数据穿透提取
- **Physical Safety Redline Layer**:
  - `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py` (物理只读红线，SHA256 绝对锁定)

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | 核心安全底线与反作弊契约 | 4裁判文件只读、simulate_execution 只读、夏普扣 2.0% 无风险利率、无未来函数与伪常数 | M1, M3 | R1 |
| 2 | 下行半协方差与相关性压力突变预警 | 大盘急跌时动态测算红利低波与高Beta下行相关系数，> 0.80 自动触发预警 | M1 | R2 |
| 3 | 跨资产流动性平移预案 | 定向减仓高估值高波标的（修复漏科技漏洞），平移至 002351 与 000216，权重守恒 | M1 | R2 |
| 4 | 场外公募底层流动性折价惩罚模型 | 基于季报前五大重仓股 ADV 与基金 AUM 比例建立非线性模型，严格单调，ETF 隔离 | M1 | R3 |
| 5 | 穿透式多周期蒙特卡洛压力测试 | 10k 次块重采样，针对 C1-C5 输出 2008/2015/2024 三大情景最大回撤与变现天数 | M1 | R4 |
| 6 | 本地服务平滑重启与探针核验 | 彻底终止旧 8501 进程，平滑启动新服务，核验 _stcore/health 返回 HTTP 200 | M2 | R5 |
| 7 | 多模态视觉走查闭环 (/browser) | 走查首屏双翼看板、Tab 1/2 折价表与 3D 分布图、亮暗主题与 640px 移动端零截断零溢出 | M2 | R5 |
| 8 | 全量自动化测试套件与专项新增 | 原有 59 项基线 + 新增 6 项专项测试 100% 绿灯通过，验证只读裁判零变动 | M3 | R6 |
| 9 | 成果沉淀与 Git 打标归档 | 更新工作区 GEMINI.md 与 PROGRESS_LOG.md，git add/commit，打标 v3.10-G10 并推送 | M3 | R6 |
| 10 | 独立胜利审计与 G11 指令自举 | 胜利审计确认通过，报告末尾输出纯文本干净排版的 G11 世代进化指令 | M3 | R6 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | 金融量化与流动性风控核心整改 | Features 1-5 (R1-R4): 相关性下行半协方差与 0.80 突变平移预案, 场外公募非线性执行折价模型, 穿透式多周期蒙特卡洛压力测试 | none | DONE |
| M2 | 本地服务平滑重启与多模态视觉走查闭环 | Features 6-7 (R5): 终止旧 8501 端口, 启动新服务, /browser 走查双翼看板、Tab 1/2 折价表与 3D 分布图、亮暗主题与 640px 移动端 | M1 | DONE |
| M3 | 全量自动化测试、只读裁判核验、Git 打标归档与 G11 指令自举 | Features 8-10 (R6): 运行 59 + 6 = 65 项自动化测试 100% 绿灯, 裁判哈希审计, 工作区 GEMINI.md/PROGRESS_LOG.md 沉淀, Git commit + v3.10-G10 标签推送, 胜利审计与 G11 指令 | M1, M2 | IN_PROGRESS |

## Interface Contracts
### advisory_engine ↔ portfolio_manager (Downside Correlation & Liquidity Shift)
- **Function**: `PortfolioManager.evaluate_dynamic_correlation_mutation(holdings, threshold=0.75, simulated_corr=None, downside_only=True, bench_symbol="H00300")`
- **Output Schema**:
  - `status`: `"MUTATION_ALERT"` | `"DECOUPLED_NORMAL"` (兼容现有 test_g3_evolution_loop.py)
  - `is_triggered`: bool (corr >= threshold, 支持 0.80 极端突变判定)
  - `is_liquidity_shift_triggered`: bool (当 corr >= 0.80 或下行相关性超限时为 True)
  - `current_correlation`: float (4位小数)
  - `downside_correlation`: float (4位小数)
  - `alert_level`: `"yellow"` | `"red"`
  - `alert_title`: str (包含 "相关性压力突变" 与 "流动性平移预案")
  - `alert_message`: str
  - `action`: str (包含 "集中度降级" 与 "流动性平移")
  - `action_type`: `"correlation_mutation_defense"` (保持向后兼容)
  - `adjusted_weights`: dict[str, float] (归一化至 1.000000，高估值高波削减，002351 + 000216 平移)
  - `cut_details`: list[dict]

### data_loader & advisory_engine (OTC Fund Liquidity Haircut)
- **Function**: `SmartExecutionDCAEngine.calculate_otc_fund_execution_slippage(fund_code, order_amount, ...)`
- **Formula**: $\text{Haircut}_{\text{bps}} = \sigma_{\text{day\_bps}} \times [\kappa_1 (Q \cdot w_{\text{eq}} / ADV_{\text{top5}})^{0.5} + \kappa_2 (Q / AUM)^{1.25} (1 + \ln(1 + AUM/ADV_{\text{top5}}))]$
- **Invariants**:
  - 严格单调递增：随着订单规模（1,000 元至 50 万元）单调递增，无常数夹取平台；
  - 场内 ETF 物理隔离（`haircut_bps = 0.0`）；
  - `DataLoader.simulate_execution` 签名与默认扣费逻辑 100% 保持只读。

### portfolio_manager (Monte Carlo Stress Testing)
- **Function**: `PortfolioManager.simulate_portfolio_cvar_bootstrap(holdings, total_capital=100000.0, risk_level="C3", n_sims=10000, block_size=10)`
- **Scenarios**: `2008_financial_crisis`, `2015_liquidity_stampede`, `2024_small_cap_crisis`
- **Output Schema**:
  - `scenarios`: dict[str, dict]包含 `max_drawdown_pred`, `cvar_99`, `var_99`, `liquidity_days`, `exceeds_risk_tolerance`
  - `risk_level`: str ("C1" ~ "C5")
  - `risk_tolerance_mdd`: float
  - `overall_cvar_99`: float
  - `overall_liquidity_days`: int
  - `distribution_data`: list[dict] (用于 3D 散点/曲面图渲染)
