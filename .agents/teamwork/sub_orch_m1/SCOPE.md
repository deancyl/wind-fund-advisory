# Scope: Milestone 1 (M1: 十维真实投票与汇率校验及胶囊联动)

## Architecture
- **Advisory Engine (`advisory_engine.py`)**:
  - `compute_ten_dimension_votes`:
    - 维度 6 产业估值真数据驱动：读取全市场 14 大赛道真实估值分位数列表，计算前 3 大机会赛道平均估值分位与全市场估值中位数。Top 3 平均 <= 35% 判定 BULL 上调 5% 仓位；全市场中位数 > 70% 判定 BEAR 下调 5% 仓位；其余 NEUTRAL；reason 中报出真实数值。
    - 维度 7 资金情绪多维融合：融合两市真实成交额、多方上涨家数占比、14 赛道真实平均拥挤度评分。平均拥挤度 < 55 或动量衰竭预警判定 BEAR 下调 5% 仓位；拥挤度 >= 72 且未过热判定 BULL 上调 2% 仓位；reason 中报出真实拥挤度均值与多方占比。
    - 维度 10 期权衍生品与避险：接入真实 option_iv_pct、ic_annualized_basis_rate 与动态相关性预警。期权隐波 > 28% 或触发相关性突变预警强制判定 BEAR 下调 8% 仓位；隐波 < 22% 且期指贴水提供充足安全垫且无相关性突变判定 BULL；reason 报出真实数值。
    - 黑天鹅/灰犀牛一票否决熔断门禁：在十维投票汇总处，当 ivix >= 32.0 或 dyn_corr >= 0.80 或 usdcnh_chg > 0.60% 时，冻结低估加仓项并标注触发熔断。
  - `generate_chief_advisor_memo` & `render_chief_advisor_memo_card`:
    - 胶囊 4（持仓病灶）与胶囊 5（今日行动准则）联动：当检测到当前账本存在免赎碎片尾仓或深套出血点或红牌止盈预警时，第五颗胶囊今日行动准则主结论与副标题优先输出账户级实战指令（如清扫尾仓并置换深套出血点），消除割裂。
- **Data Layer (`data_loader.py`) & Across Workspace**:
  - 拔除 6.6676 与 5.0000 兜底常数并增加合理性校验哨：在 data_loader.py (fetch_macro_cross_market_indicators 等)、advisory_engine.py、app_gui.py、strategy_bridge.py、portfolio_manager.py 中全面清除 6.6676 和 5.0000。
  - 若离岸汇率低于 6.85 或高于 7.60，离线校准为真实近期截面数据 7.2385，美债校准为 4.42%，利差校准为 -278.2 bp。

## Feature Inventory
| # | Feature | Description | Milestone | Source | Status |
|---|---------|-------------|-----------|--------|--------|
| 1 | 维度6产业估值真数据驱动 | 废除列表长度恒真，读取 14 赛道真实估值分位，计算 Top3 均值与中位数定多空 | M1 | ORIGINAL_REQUEST §二.1 | DONE |
| 2 | 维度7资金情绪多维融合 | 废除单基/默认 85 分，融合两市成交额、上涨家数占比与 14 赛道真实平均拥挤度 | M1 | ORIGINAL_REQUEST §二.1 | DONE |
| 3 | 维度10期权衍生品与避险 | 接入真实 option_iv_pct、ic_annualized_basis_rate 与动态相关性突变预警 | M1 | ORIGINAL_REQUEST §二.1 | DONE |
| 4 | 黑天鹅/灰犀牛一票否决熔断门禁 | ivix >= 32.0 或 dyn_corr >= 0.80 或 usdcnh_chg > 0.60% 时冻结低估加仓项并报出熔断 | M1 | agy2 Task 3 / Survey | DONE |
| 5 | 拔除 6.6676/5.0000 及校验哨 | 清除所有失真兜底常数，离岸汇率低于 6.85 或高于 7.60 触发校准机制与真实截面 | M1 | ORIGINAL_REQUEST §二.2 | DONE |
| 6 | 胶囊4与胶囊5知行合一联动 | 当检出深套或碎片尾仓时，胶囊5优先输出账户级清扫尾仓与置换止血实战指令 | M1 | ORIGINAL_REQUEST §二.3 | DONE |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | 十维真实投票与汇率校验及胶囊联动 | Features 1-6 (advisory_engine.py, data_loader.py, app_gui.py, strategy_bridge.py, portfolio_manager.py) | none | DONE |

## Verification Results
- 自动化测试用例：`tests/test_g19_m1_ten_dimension_and_memo.py` 28/28 passed
- 既有回归及只读裁判测试：`tests/test_infra.py` 等 61/61 passed
- 独立挑战者对抗极限测试：`scratch/test_adv_m1_challenger1.py` (24/24 passed), `scratch/test_adv_m1_challenger2.py` (18/18 passed)
- 门禁裁决：Reviewer 1 APPROVE, Reviewer 2 APPROVE, Challenger 1 APPROVE, Challenger 2 APPROVE, Forensic Auditor CLEAN
