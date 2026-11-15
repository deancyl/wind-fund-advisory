# Project: Wind G19 投顾引擎与交易风控闭环进化

## Architecture
- **核心数据层 (`data_loader.py`)**: 宏观跨市场数据抓取、离岸人民币与美债收益率合理性校验哨、14 大赛道真实估值与拥挤度湖仓接入、`DataLoader.simulate_execution` 物理锁死防作弊扣费。
- **投顾决策与裁决层 (`advisory_engine.py`)**: 十维投顾投票引擎重构（维度 6 产业估值真数据、维度 7 资金情绪与拥挤度融合、维度 10 期权隐波/期指贴水/动态相关性接入）、黑天鹅/灰犀牛一票否决熔断门禁、首席投顾备忘录胶囊 4（持仓病灶）与胶囊 5（今日行动准则）知行合一指令联动。
- **策略回测与资产组合层 (`strategy_bridge.py`, `portfolio_manager.py`)**: 动态持仓真实摩擦账单计算（彻底清除静态假常数）、历史时点盲测全额扣费、近三年双月/季度滚动发车定投盲测胜率实证表（零未来函数 Point-in-Time 推演）、OCR 双通道并集融合与中证 A500/持有期干扰词过滤。
- **人机交互与大屏展示层 (`app_gui.py`)**: 首次打开存量持仓账本自动路由至 Tab 2、首席备忘录样式集中合入全局主样式、移动端按钮组与列容器选择器修复（排除数字输入框加减按钮）、`IS_MOBILE_VIEW` 响应式视口激活、Tab 2 运维工具坞扁平化、Tab 2 Brinson 归因/Tab 4 交叉热力图/四象限散点图前置人话解读卡片。
- **全量测试与安全防线 (`tests/`, `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`)**: 物理只读裁判文件绝不改动、维护非只读测试确保全量 pytest 100% 绿灯、G20 指令无冒号无嵌套严格格式门禁。

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | 维度6产业估值真数据驱动 | 废除列表长度恒真，读取 14 赛道真实估值分位，计算 Top3 均值与中位数定多空 | M1 | ORIGINAL_REQUEST §二.1 |
| 2 | 维度7资金情绪多维融合 | 废除单基/默认 85 分，融合两市成交额、上涨家数占比与 14 赛道真实平均拥挤度 | M1 | ORIGINAL_REQUEST §二.1 |
| 3 | 维度10期权衍生品与避险 | 接入真实 option_iv_pct、ic_annualized_basis_rate 与动态相关性突变预警 | M1 | ORIGINAL_REQUEST §二.1 |
| 4 | 黑天鹅/灰犀牛一票否决熔断门禁 | ivix >= 32.0 或 dyn_corr >= 0.80 或 usdcnh_chg > 0.60% 时冻结低估加仓项并报出熔断 | M1 | agy2 Task 3 / Survey |
| 5 | 拔除 6.6676/5.0000 及校验哨 | 清除所有失真兜底常数，离岸汇率低于 6.85 或高于 7.60 触发校准机制与真实截面 | M1 | ORIGINAL_REQUEST §二.2 |
| 6 | 胶囊4与胶囊5知行合一联动 | 当检出深套或碎片尾仓时，胶囊5优先输出账户级清扫尾仓与置换止血实战指令 | M1 | ORIGINAL_REQUEST §二.3 |
| 7 | 首次加载存量账本自动路由 | 账本管理器 pm 初始化后立即检查持仓数 >= 10，自动跳转 Tab 2 激活诊断与调仓 | M2 | ORIGINAL_REQUEST §三.1 |
| 8 | 样式集中合并与手机端列选择器 | 将 chief-memo 样式移入全局主样式表，移动端补齐 stColumn 并排除数字输入框加减钮 | M2 | ORIGINAL_REQUEST §三.2 |
| 9 | 近3年滚动发车盲测胜率实证表 | 零未来函数推演 180d/365d，全额扣除申购/赎回/托管/销售服务费，统计胜率与超额 | M2 | ORIGINAL_REQUEST §三.3 |
| 10 | 摩擦账单动态精算与回测全额扣费 | strategy_bridge.py 清除 cagr/mdd/yield 假常数，回测计提 0.75%/250 托管管理费 | M2 | agy2 Task 1 / Survey |
| 11 | OCR 识别双通道并集与词表扩充 | 修复 OCR 只要 >= 1 即提前 return 缺陷，并集融合空间块聚类，扩充 A500/持有期词表 | M2 | agy2 Task 2 / Survey |
| 12 | IS_MOBILE_VIEW 激活与响应式布局 | 激活顶层 IS_MOBILE_VIEW 变量，Tab 关键分栏自适应切换单列容器 | M2 | agy2 Task 4 / Survey |
| 13 | Tab 2 工具坞扁平化与前置人话解读卡片 | 扁平化三层录入套娃为 st.radio，为 Brinson、交叉热力图、四象限散点图注入前置人话卡片 | M2 | agy2 Task 4 / Survey |
| 14 | 物理裁判底线保护与非只读测试修复 | 保护四大只读文件与 simulate_execution 签名扣费，修复 g16 建仓断言与 g15 湖仓未来日期 | M3 | ORIGINAL_REQUEST §一.2, 四.2 |
| 15 | 服务平滑重启与桌面/手机双视口核验 | 彻底终止 8501 端口，启动最新服务，桌面与手机双视口截图核验三大关键事实 | M3 | ORIGINAL_REQUEST §四.1 |
| 16 | Git 标签推送与无冒号 G20 指令门禁 | 跑通全量测试，执行 git 提交打标 v4.9-G19 推送，按严格纯字符序列输出 G20 指令 | M3 | ORIGINAL_REQUEST §四.2, 四.3 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | 十维真实投票与汇率校验及胶囊联动 | Features 1-6 (advisory_engine.py, data_loader.py, app_gui.py, strategy_bridge.py) | none | DONE (conv: a29ecba0; 113/113 passed, Auditor CLEAN) |
| M2 | 首次自动路由、滚动发车盲测与交互精修 | Features 7-13 (app_gui.py, strategy_bridge.py, portfolio_manager.py) | M1 | IN_PROGRESS |
| M3 | 测试回归、双视口验收与 G20 严格交付 | Features 14-16 (tests/, app restart, browser verification, git tag, G20 output) | M1, M2 | PLANNED |

## Interface Contracts
### advisory_engine.py ↔ app_gui.py / data_loader.py
- `compute_ten_dimension_votes(snap: dict, alerts: list = None, radar_top3: list = None) -> dict`:
  - 必须返回包含 10 个维度的列表，每个维度为 `{"name": str, "dimension": str, "score": float, "vote": str ("BULL"|"BEAR"|"NEUTRAL"), "delta_pct": float, "reason": str}`。
  - 新增熔断门禁逻辑：当 `ivix >= 32.0` 或 `dyn_corr >= 0.80` 或 `usdcnh_chg > 0.60%` 时，触发熔断冻结低估加仓项并打上 `🚨 黑天鹅/灰犀牛熔断` 标记。
  - 必须真实计算维度 6（14 赛道 Top3 估值分位均值与全市场中位数）、维度 7（两市成交额、上涨占比、14 赛道平均拥挤度）、维度 10（option_iv_pct、ic_annualized_basis_rate、动态相关性突变）。
- `generate_chief_advisor_memo(radar_top3=..., portfolio_pathology=..., ...) -> dict`:
  - 接收持仓病灶信息；当 `deep_loss_count > 0` 或 `frag_count > 0` 或存在红牌止盈时，第 5 颗胶囊主结论优先输出账户级实战指令（如“清扫X只免赎尾仓·置换深套止血”），副标题优先输出账户级处置细则。
- `DataLoader.fetch_macro_cross_market_indicators()`:
  - 严格校验 `usdcnh_rate` 在 `[6.85, 7.60]` 区间内；若超出或读取失败，校准为真实近期截面数据（如 `7.2385`），美债收益率校准为 `4.42%`，绝不出现 `6.6676` 或 `5.0000`。

### strategy_bridge.py ↔ app_gui.py
- `calculate_rolling_dca_3y_backtest(...) -> dict`:
  - 统计过去 3 年按双月/季度滚动发车持有满 180 天、365 天的正收益胜率、平均净收益率、超额收益率（相对沪深 300）。
  - 全额扣除申购费、赎回费、公募管理托管费（0.75%/250）、销售服务费。
- `calculate_mutual_fund_friction_bill(weights: dict, ...) -> dict`:
  - 基于真实 `weights` 动态测算 CAGR、最大回撤、股息率与回本天数，严禁返回假常数。

## Code Layout
- `AGY2_FundAdvisory/` (以及根目录对应包)
  - `data_loader.py`: 数据湖加载器、宏观跨市场数据、真实执行模拟器
  - `advisory_engine.py`: 十维投票引擎、熔断门禁、首席备忘录五大胶囊
  - `strategy_bridge.py`: 策略桥接层、摩擦账单精算、滚动盲测、动态相关性
  - `portfolio_manager.py`: 账本管理器、OCR 空间块与文本双通道并集提取
  - `app_gui.py`: Streamlit 交互大屏、首次加载自动路由、全局样式与响应式视口
- `tests/`: 自动化测试用例
  - `tests/test_infra.py` [只读神圣]
  - `tests/test_g19_m1_ten_dimension_and_memo.py` [新建/补充针对性测试]
  - `tests/test_g19_m2_routing_and_rolling_dca.py` [新建/补充针对性测试]
  - 既有回归测试用例 (维持 100% 绿灯)
