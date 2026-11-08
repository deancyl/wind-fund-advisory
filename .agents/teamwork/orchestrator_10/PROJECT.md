# Project: G9 世代量化因果律严苛纠偏、防未来函数样本外滚动演化、真数据防幻觉锚定与 Brinson 归因及适当性主动风控闭环

## Architecture
- **Quant Algorithm & Evolution Engine**: `AGY2_FundAdvisory/advisory_engine.py`
  - `OnlineHeuristicFactorEvolver`: 严格滞后一期因果对齐 ($P_{[:-1]} \times R_{[1:]}$)，日度收益率真实内扣双边换手摩擦 (单边 10 bps，双边 20 bps)，夏普比率严格扣减 2.0% 年化无风险利率 ($0.02 / 250.0$)；
  - Walk-Forward 推进式样本外演化轨迹：12 切片 $\times$ 5 日无前瞻样本外真实滚动推演与权重记录，彻底废除 `lam = (t + 1) / 60.0` 线性插值；
  - 跨市场交易日历对齐：以 A 股交易日历（H00300）为基准索引 `reindex + ffill`，彻底废除 `np.linspace(1.0, 1.05)` 假序列；
  - 估值分位去趋势中枢化：接入 `index_valuation.json` 官方 5 年分位缓存与年线偏离中枢分位数，替代 85 天短窗估值错配；
  - `ActiveRiskSentry`: 2.5 亿元假规模清零，三级穿透真实反查，未查得标记“规模待核验”黄色告警；投资者适当性（C1-C5）权益与波动率超限巡检，提供一键降波纠偏；盘中实时异动对浮盈安全垫消耗传导；
  - `OpportunityRadarEngine`: 盘中末端 K 线真实重算（统一重算 MA20、Bias20、Slope20、ER20、Vol20、MDD20），动态量化证据链合成器与 Top 3 风险收益对称展示。
- **Data & Portfolio Engine**: `AGY2_FundAdvisory/data_loader.py`, `portfolio_manager.py`
  - `data_loader.py`: 快讯信源真伪双轨隔离与真实时间戳，离线快照严格保留 `updated_at`，严禁 `datetime.now()` 冒充；
  - `portfolio_manager.py`: 基于 9 大标准大类的 Brinson-Fachler 经典模型，主动调仓净增厚严格拆解为大类资产配置效应、优选基金超额效应与交易摩擦规避贡献；基线快照 `initial_baseline_snapshot` 纳入状态序列化持久化。
- **UI & Multi-Modal Layer**: `AGY2_FundAdvisory/app_gui.py`
  - 首屏双翼看板：Top 3 机会赛道卡片四维得分与风险指标（Vol20、MDD20）对称披露；晨报信源状态徽章；
  - Tab 2 工具坞：`dock_tab3` 实装 Brinson 三维归因卡片、多大类资产归因明细表与投顾复盘点评；
  - 全站亮色、暗黑主题及 640px 移动端视口自适应，零文字截断、零水平溢出。
- **Verification & Physical Redline Layer**:
  - 四大只读裁判文件（`judge_engine.py`、`holdout_vault.py`、`AGENT_SPEC.md`、`tests/test_infra.py`）及 `DataLoader.simulate_execution` 绝对锁定；
  - 针对性自动化测试套件 `tests/test_g9_causal_brinson_and_suitability.py`；全量回归 100% 通过。

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | 种群评估消除同日未来函数 | P[:-1] 滞后一期对应 R[1:]，严格杜绝同日收盘特征乘同日收益 | M1 | Survey-1 |
| 2 | 真实双边换手摩擦扣除 | 日度收益率真实内扣 0.0020 * daily_to 换手摩擦成本，真实累计净值 | M1 | Survey-1 |
| 3 | 夏普比率扣除无风险利率 | 从日均收益率中扣减 0.02 / 250.0，杜绝纯债白嫖高夏普 | M1 | Survey-1 |
| 4 | Walk-Forward 推进式样本外轨迹 | 12 切片 × 5 日滚动样本外演化，废除 lam 线性插值 | M1 | Survey-1 |
| 5 | A 股日历跨市场对齐 | 以 A 股日历为基准 reindex + ffill，彻底解决跨市场日期错位 | M1 | Survey-1 |
| 6 | 废除 np.linspace 假序列 | 缺失数据置常数 1.0 (收益率 0)，夏普为负自然淘汰 | M1 | Survey-1 |
| 7 | 估值分位长周期中枢化 | 接入官方 5 年分位缓存与年线去趋势分位，废除 85 天假短窗 | M1 | Survey-1 |
| 8 | 真实规模三级穿透反查 | 清零 2.5 亿假兜底，穿透元数据/API/核心池，查无标记“规模待核验” | M1 | Survey-2 |
| 9 | 投资者适当性越界预警 | C1-C5 权益上限与高波科技巡检，超配预警并提供一键降波建议 | M1 | Survey-2 |
| 10 | 盘中异动安全垫实时传导 | 单基 >=2% 或组合 >=1% 异动测算安全垫实时消耗金额与比例 | M1 | Survey-2 |
| 11 | 机会雷达盘中末端真实重算 | 最新价并入序列重算 MA20、Bias20、Slope20、ER20、Vol20、MDD20 | M1 | Survey-2 |
| 12 | 动态量化证据链合成器 | 结合真实分位、斜率、信噪比与反拥挤度动态生成 100% 自洽文案 | M1 | Survey-2 |
| 13 | 快讯信源真伪隔离与验真 | 区分实时联网与离线快照，保留原始时间戳，严禁 datetime.now() | M1 | Survey-2 |
| 14 | Brinson 三维超额收益归因 | 基于 9 大大类拆解大类配置效应、选基效应与摩擦规避贡献 | M2 | Survey-3 |
| 15 | 基线快照持久化修复 | initial_baseline_snapshot 纳入导入导出，解决重启丢失基线缺陷 | M2 | Survey-3 |
| 16 | Top 3 卡片风险收益对称展示 | 完整披露四维得分、两项风险指标与动态证据链 | M2 | Survey-2/3 |
| 17 | Tab 2 工具坞 Brinson 归因账单 | 渲染三维归因卡片、多大类资产归因明细表及买方投顾点评 | M2 | Survey-3 |
| 18 | G9 专项测试套件实装 | 编写 test_g9_causal_brinson_and_suitability.py 覆盖 5 大新特性 | M3 | Survey-3 |
| 19 | 全量自动化测试回归 | 50 项既有测试 + 5 项新增测试 100% 通过，裁判文件只读审计 | M3 | Survey-3 |
| 20 | 服务平滑重启与走查 | 终止旧 8501 进程，重启新服务，HTTP 200 自检与多模态走查 | M3 | Survey-3 |
| 21 | Git 归档与 G10 指令自举 | 更新 GEMINI.md/PROGRESS_LOG.md，打 tag v3.9-G9 推送远端 | M3 | Survey-3 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | 量化因果律核心纠偏与真数据底座实装 | Features 1-13 (`advisory_engine.py`, `data_loader.py`): 因果滞后对齐, 换手摩擦内扣, 夏普扣减 Rf, Walk-Forward 滚动轨迹, 交易日对齐, 估值中枢, 规模反查, 适当性与异动传导, 末端K线重算, 证据链, 快讯验真 | none | DONE |
| M2 | Brinson 三维归因、基线持久化与 UI 全栈闭环 | Features 14-17 (`portfolio_manager.py`, `app_gui.py`): Brinson-Fachler 经典归因拆解, 基线快照持久化, Top 3 风险收益对称展示, 晨报信源指示徽章, Tab 2 Brinson 归因账单与投顾点评 | M1 | DONE |
| M3 | 全量测试验证、服务重启、多模态走查与 Git 归档 | Features 18-21: G9 专项测试, 59 项测试全通, 四大裁判文件只读法证, 8501 重启自检, GEMINI.md/PROGRESS_LOG.md 沉淀, Git Tag v3.9-G9, G10 指令 | M1, M2 | DONE |

## Interface Contracts
### M1 ↔ M2: Factor Evolver & Risk Sentry to Portfolio/UI
- **Evolver Output**: `OnlineHeuristicFactorEvolver.get_60d_rolling_nav_and_trajectory()` returns `{ "dates": list[str], "nav_dynamic": list[float], "nav_static": list[float], "trajectory": list[dict], "final_nav_dynamic": float, "final_nav_static": float, "alpha_pct": float, "mdd_dynamic_pct": float, "mdd_static_pct": float }` with length 60, fully causal.
- **Sentry Alerts**: `ActiveRiskSentry.inspect_portfolio()` returns alerts with `action_type` in `["lock_shares", "countdown_hold", "switch_a_class", "take_profit", "deep_loss_rebalance", "rebalance_sector", "replace_fund", "defense_mode", "offense_mode"]`.
  - Pending verification: `aum_status="PENDING_VERIFICATION"`, `action_type="replace_fund"`;
  - Appropriateness over-equity: `dimension="投资者适当性"`, `action_type="rebalance_sector"`;
  - Intraday cushion shock: `dimension="盘中异动安全垫传导"`, `action_type="defense_mode"`.
- **Radar Output**: `OpportunityRadarEngine.evaluate_sector()` includes `vol_20`, `mdd_20`, dynamic `core_logic`, recalculated `bias_20`, `slope_20`, `er_20`.

### M2 ↔ M3: Rebalance Audit & Test Contracts
- **Brinson Return Structure**: `PortfolioManager.evaluate_rebalance_audit()` returns all 7 legacy keys for backward compatibility, PLUS `"brinson_attribution"`:
  - `"allocation_effect_yuan"`, `"allocation_effect_pct"`
  - `"selection_effect_yuan"`, `"selection_effect_pct"`
  - `"friction_saving_yuan"`, `"friction_saving_pct"`
  - `"total_active_add_yuan"`, `"total_active_add_pct"`
  - `"category_breakdown"`: list of dicts with per-category allocation & selection effects.
  - **Mathematical Invariant**: `abs(allocation_effect_yuan + selection_effect_yuan - total_active_add_yuan) < 1e-4`.

## Code Layout
- `AGY2_FundAdvisory/`
  - `advisory_engine.py`: OnlineHeuristicFactorEvolver, ActiveRiskSentry, OpportunityRadarEngine (M1)
  - `data_loader.py`: Realtime news fetch & timestamp isolation (M1)
  - `portfolio_manager.py`: Brinson attribution, snapshot persistence (M2)
  - `app_gui.py`: Top 3 cards, news badge, Tab 2 Brinson workbench (M2)
  - `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`: Physical read-only redlines (LOCKED)
- `tests/`
  - `test_infra.py`: Physical read-only baseline (LOCKED)
  - `test_g9_causal_brinson_and_suitability.py`: New targeted test suite (M3)
  - `test_adv_final_closure.py`, `test_g3_evolution_loop.py`, `test_gui_multi_ledger_stress.py`: Regression baselines
