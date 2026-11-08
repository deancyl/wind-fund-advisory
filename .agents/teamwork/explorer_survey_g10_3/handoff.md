# G10 世代量化进化闭环调研报告：R4 穿透式蒙特卡洛压力测试、R5 多模态视觉与 R6 自动化测试基线

**调研者**：teamwork_explorer (`explorer_survey_g10_3`)  
**调研对象**：`portfolio_manager.py`、`AGY2_FundAdvisory/app_gui.py`、`tests/`、`winrate_engine.py`、`strategy_bridge.py`、`advisory_engine.py`  
**核心关注需求**：Requirement R4 (穿透式多周期蒙特卡洛压力测试)、R5 (本地服务平滑重启与多模态视觉走查闭环)、R6 (全量自动化测试基线与新增专项测试计划)

---

## 1. 观察事实 (Observation)

### 1.1 自动化测试基线组织结构 (R6 现存 59 项测试)
通过执行 `py -3 -m pytest tests/test_infra.py tests/test_adv_final_closure.py tests/test_g3_evolution_loop.py tests/test_gui_multi_ledger_stress.py tests/test_g9_causal_brinson_and_suitability.py --collect-only`，收集到当前全量基线测试共 **59 项**，分布于 5 大测试模块：

1. **`tests/test_infra.py` (只读裁判基线，共 14 项)**：
   - `test_data_loader_matrix_alignment`
   - `test_simulation_operator_friction`
   - `test_causal_probe_detects_leakage`
   - `test_four_islands_conformity`
   - `test_holdout_vault_quota_limit`
   - `test_judge_engine_rejects_bond_arbitrage`
   - `test_simulation_initial_position_penalty`
   - `test_judge_engine_rf_deduction`
   - `test_judge_engine_rejects_slice_bond_arbitrage`
   - `test_judge_engine_rejects_offshore_overweight`
   - `test_judge_engine_rejects_low_ashare_equity`
   - `test_judge_engine_rejects_low_cagr`
   - `test_judge_engine_rejects_bull_slice_lag`
   - `test_islands_empty_df_robustness`
   *(契约铁律：该文件属于四大只读裁判文件之一，严禁修改)*

2. **`tests/test_adv_final_closure.py` (投顾全能闭环，共 14 项)**：
   - `test_specialized_1_all_nine_standard_asset_classes_covered`
   - `test_specialized_2_yield_cushion_and_shadow_rebalance_audit_dynamics`
   - `test_specialized_3_auto_commit_and_reimport_compatibility`
   - `test_specialized_4_ui_wireup_and_valuation_percentile_anti_fraud`
   - `test_specialized_5_ledgers_clean_and_main_live_intact`
   - `test_specialized_6_resolve_fund_display_name_accuracy`
   - `test_specialized_7_realtime_market_source_detection`
   - `test_specialized_8_multi_ledger_wireup_tab3_and_tab4`
   - `test_specialized_9_stock_overlap_anti_cheat_and_layout`
   - `test_specialized_10_look_through_stocks_step_weights_and_risk_sorting`
   - `test_specialized_11_smart_money_quadrants_and_real_metrics`
   - `test_specialized_12_multi_ledger_ghost_cleaning_and_naming_protection`
   - `test_specialized_13_tab3_backtest_modes_and_duplicate_key_defense`
   - `test_specialized_14_smart_alias_and_visual_fitness`

3. **`tests/test_g3_evolution_loop.py` (量化进化与极端风控，共 12 项)**：
   - `test_g3_1_dynamic_correlation_ewma_and_threshold_mutation`
   - `test_g3_2_active_risk_sentry_dimension_7_integration`
   - `test_g3_3_extreme_black_swan_monte_carlo_block_bootstrap_cvar99`
   - `test_g3_4_smart_dca_vwap_execution_slippage_optimization`
   - `test_g3_5_app_gui_source_wireup_verification`
   - `test_g3_6_edge_cases_and_robustness_immunization`
   - `test_g3_7_tab2_rebalance_vwap_slippage_and_clean_data`
   - `test_g3_8_historical_inflection_point_signals_verification`
   - `test_g5_1_single_fund_real_volatility_penetration`
   - `test_g5_2_historical_inflection_ruler`
   - `test_g5_3_cushion_break_even_stress_model`
   - `test_g5_4_tail_valuation_anomaly_alerts`

4. **`tests/test_gui_multi_ledger_stress.py` (多账本持久化与 GUI 极限承压，共 10 项)**：
   - `test_rapid_ledger_switching_atomicity`
   - `test_cross_tab_views_sync_on_switch`
   - `test_tab1_save_to_new_ledger_isolation`
   - `test_invalid_ledger_id_fallback`
   - `test_corrupted_index_json_self_healing`
   - `test_missing_ledger_file_resilience`
   - `test_delete_active_ledger_safely_falls_back`
   - `test_apptest_rapid_ledger_switch_and_metric_update`
   - `test_apptest_invalid_ledger_id_in_session_state_graceful_recovery`
   - `test_apptest_invalid_sel_tab2_active_ledger_unhandled_crash`

5. **`tests/test_g9_causal_brinson_and_suitability.py` (G9 世代因果律、适当性与 Brinson 归因，共 9 项)**：
   - `test_causal_evaluator_lag1_alignment`
   - `test_turnover_friction_deduction`
   - `test_sharpe_ratio_rf_deduction`
   - `test_walk_forward_rolling_trajectory_genuine`
   - `test_aum_three_tier_verification_and_liquidation`
   - `test_investor_suitability_c1_to_c5_risk_boundary`
   - `test_intraday_cushion_shock_transmission`
   - `test_brinson_fachler_three_dimensional_attribution_identity`
   - `test_baseline_snapshot_persistence`

### 1.2 `portfolio_manager.py` 现状与方法缺失
1. 文件位置：`AGY2_FundAdvisory/portfolio_manager.py`（共 8,566 行代码）。
2. 在 `portfolio_manager.py` 中检索 `simulate_portfolio_cvar_bootstrap` 或 `bootstrap`、`cvar`，**目前结果为 0**（尚未实装）。
3. 相关的动态相关性与风控方法已就绪于第 8369 至 8546 行：
   - 第 8369 行：`@classmethod def evaluate_dynamic_correlation_mutation(...)`
   - 第 8533 行：`def evaluate_dynamic_correlation_mutation_instance(...)`
   - 第 8550 至 8566 行：模块级便捷别名导出区域。
4. 在 `AGY2_FundAdvisory/winrate_engine.py` 中存在现有的蒙特卡洛与黑天鹅算子：
   - 第 776 至 934 行：`simulate_black_swan_stress(...)`
     - 当前 `slices_def` 仅包含 3 个区间：
       1) `2018_trade_war` (2018-01-29 ~ 2019-01-04)
       2) `2022_valuation_kill` (2021-12-13 ~ 2022-10-31)
       3) `2024_micro_liquidity` (2024-01-02 ~ 2024-02-05)
   - 第 935 至 1079 行：`simulate_monte_carlo_block_bootstrap_stress(...)`
     - 采用 NumPy 向量化 Circular Block Bootstrap：
       ```python
       n_blocks = int(np.ceil(h_days / b_size))
       st_indices = rng.randint(0, n_ret, size=(n_sim, n_blocks))
       offsets = np.arange(b_size)
       all_idx = (st_indices[:, :, None] + offsets).reshape(n_sim, n_blocks * b_size) % n_ret
       ```
     - 在首日拼接 `1.0` 初始净值测算全路径最大回撤；
     - 包含百分位分布、VaR 95%、VaR 99%、CVaR 99% 及简单资产流动性折价测算。
   - **痛点**：目前 `winrate_engine.py` 的黑天鹅没有 2008 年金融危机与 2015 年流动性踩踏两大极值情景；没有结合投资者适当性 C1 至 C5 风险偏好等级做契约越界比对；没有精算各情景下的“流动性变现天数”。

### 1.3 历史极端三大情景数据储备勘查
经对 `data/processed/indices/` 目录中底层行情 Parquet 文件进行日期探测：
- `data/processed/indices/000300.SH.parquet` (沪深300)：起始日期 **2002-01-04** 至 **2026-10-28**，共 6,075 个交易日，完整覆盖 2008 年与 2015 年；
- `data/processed/indices/000001.SH.parquet` (上证指数)：起始日期 **1990-12-19**；
- `data/processed/indices/000905.SH.parquet` (中证500)：覆盖 2008 与 2015；
- `data/processed/indices/000852.SH.parquet` (中证1000)：覆盖 2024 年初小盘股危机；
- `data/processed/indices/AU9999.SGE.parquet` (黄金) 与 `CBA00101.CS.parquet` (中债财富)：起始于 2002 年。
三大极端情景实测最大回撤基线：
1. **2008 金融危机** (`2008-01-02 ~ 2008-11-04`，或 `2007-10-16 ~ 2008-11-04`)：沪深300 MDD 达到 **-71.60% ~ -72.30%**；纯债资产上涨超 +10%，黄金避险上涨超 +14%；
2. **2015 流动性踩踏** (`2015-06-12 ~ 2015-08-26`，全阶段至 `2016-01-29`)：沪深300 MDD 达到 **-43.29% ~ -46.51%**，中小创下挫超 **-55% ~ -65%**；千股跌停导致流动性瞬间冻结；
3. **2024 年初小盘股流动性危机** (`2024-01-02 ~ 2024-02-05`)：中证1000 MDD 为 **-26.67%**，微盘股踩踏超 **-35%**，而高股息红利全收益指数逆势上涨超 **+4.5%**，纯债小幅上涨 **+1.8%**。

### 1.4 投资者适当性 C1 至 C5 契约参数
在 `AGY2_FundAdvisory/strategy_bridge.py` 第 191 至 275 行定义了 `RISK_TIERS_CONFIG`：
- **C1 安稳保守型**：契约最大容忍回撤 `max_tolerated_loss = -5.0%`，权益仓位上限 `20%`；
- **C2 稳健固收+型**：契约最大容忍回撤 `max_tolerated_loss = -10.0%`，权益仓位上限 `40%`；
- **C3 平衡进取型**：契约最大容忍回撤 `max_tolerated_loss = -15.0%`，权益仓位上限 `78%`；
- **C4 成长进攻型**：契约最大容忍回撤 `max_tolerated_loss = -25.0%`，权益仓位上限 `85%`；
- **C5 极限高Beta追击型**：契约最大容忍回撤 `max_tolerated_loss = -40.0%`，权益仓位上限 `95%`。

### 1.5 `AGY2_FundAdvisory/app_gui.py` 界面布局现状
1. **首屏双翼看板 (`render_dual_wing_advisory_dashboard`, 第 2538 至 2906 行)**：
   - 左翼 `col_radar` (宽度 6.2)：机会雷达 Top 3、今日晨报、历史三大牛熊拐点对照尺；
   - 右翼 `col_sentry` (宽度 3.8)：六维主动风险预警哨，内部包含 `with st.container(height=380)`；
   - **现状缺失**：双翼看板尚未挂载醒目的“多资产相关性压力突变预警指示卡”与“压力测试流动性指标卡片”。
2. **四大核心工作区 Tab (`st.tabs`, 第 2975 至 2980 行)**：
   - Tab 1: `tab_zero_start` ("🌱 新资建仓", 第 2990 至 4250 行)
     - 第 3540 至 3550 行已调用 `render_black_swan_stress_card(stress_data)`，但未展示 3D 分布图；
     - 第 4015 至 4115 行为微观执行滑点与定投计划，但缺乏穿透基金重仓股 ADV 的“大额订单流动性折价明细表”。
   - Tab 2: `tab_holdings_and_rebalance` ("💼 持仓调仓", 第 4260 至 5700 行)
     - 第 5500 至 5645 行为建议调仓订单表，目前未渲染黑天鹅蒙特卡洛 3D 分布图与大额订单流动性折价明细表。
3. **安全渲染与 640px 响应式约束**：
   - 第 183 至 200 行：已实现 `_clean_html`（过滤首尾空格及空行，防 CommonMark 4+ 空格缩进代码块泄露）与 `safe_markdown_html`；
   - 第 1298 至 1376 行：已包含移动端自适应 CSS（包含 `@media (max-width: 640px)`、Flexbox 防挤压 `flex: 0 0 auto !important` 与横向滚动容器）；
   - 第 1791 至 1823 行：`apply_theme_to_plotly_figure` 支持 5 套主题与 Plotly 图表双向着色。

---

## 2. 推理逻辑链 (Logic Chain)

```
[Observation 1.2 & 1.3: portfolio_manager.py 缺少多周期蒙特卡洛压力测试方法]
      │
      ▼
[Step 1: 在 PortfolioManager 类中实装 simulate_portfolio_cvar_bootstrap]
- 规范输入：holdings、total_capital、investor_risk_tier ('C1'~'C5')、n_simulations=10000、block_size=10、horizon_days=60
- 三大极端历史情景建模：
  1) 2008 年金融危机 (2008-01-02 ~ 2008-11-04): 沪深300 -71.60%，大盘高波股票普跌，纯债(+10.5%)与黄金(+14.2%)大涨；
  2) 2015 年流动性踩踏 (2015-06-12 ~ 2015-08-26): 沪深300 -43.29%，中小创 -55%~-65%，千股跌停流动性冻结；
  3) 2024 年初小盘股流动性危机 (2024-01-02 ~ 2024-02-05): 中证1000 -26.67%，微盘股闪崩，红利低波(+4.5%)与纯债(+1.8%)避险。
      │
      ▼
[Step 2: 循环块重采样 (Circular Block Bootstrap) 与极值不变量]
- 对每个情景基于组合底层资产属性合成日收益率序列，按块长 10 天随机抽取 10,000 条 60 天路径；
- 并在路径首日拼接 1.0 初始净值，计算全路径最大回撤；
- 计算 VaR 95%、VaR 99%、CVaR 99%，严格满足数学公理：CVaR_99% >= VaR_99% >= VaR_95%。
      │
      ▼
[Step 3: 结合 C1 至 C5 适当性等级输出“最大回撤预测”与“契约超限评估”]
- 提取 RISK_TIERS_CONFIG 中 C1~C5 的 max_tolerated_loss；
- 计算当前组合预测 MDD 与契约限额差额 (超配风险敞口 RMB 金额)；
- 矩阵化输出当前组合在 3 大情景 × 5 个风险偏好等级下的预测与契约合规标签 (PASS / WARN / SEVERE_BREACH)。
      │
      ▼
[Step 4: 多维流动性折价损失与“流动性变现天数 (Liquidation Days)”精算]
- 基础交收周期 T_base: 纯债/现金 1天, 境内股票/黄金 2~2.5天, QDII海外 5天；
- 锁仓与 FIFO 惩罚 T_lock: 持有不满 7 天追加锁定天数；
- 极端危机情景流动性顺延乘数 lambda_scenario:
  - 2008 危机: 海外/QDII 乘数 2.0x, 高估值股票 1.8x；
  - 2015 踩踏: 千股跌停与停牌导致股票类乘数 3.0x；
  - 2024 微盘危机: 小微盘与高波科技类乘数 2.5x，红利与纯债 1.0x。
- 结合 R3 披露的前五大重仓股 ADV 测算冲击追加天数 T_adv；
- 输出：加权平均变现天数 T_avg、90% 资金快速变现天数 T_90、100% 完全变现天数 T_100，并与 C1~C5 容忍限额对齐。
      │
      ▼
[Step 5: AGY2_FundAdvisory/app_gui.py 前端双翼与 Tab 1/Tab 2 视觉闭环 (R5)]
- 首屏双翼看板右翼新增：【多资产相关性突变预警指示卡】与【压力测试流动性指标卡片】；
- Tab 1 与 Tab 2 新增：
  1) 【大额订单流动性折价明细表】：披露基金代码、名称、订单金额、重仓股ADV、基金规模、折价基点、损失金额与分批调度；
  2) 【蒙特卡洛压力测试三维分布图】：基于 Plotly 3D (go.Surface / go.Scatter3d) 绘制情景 × 周期/分位 × 回撤损失三维曲面，并通过 apply_theme_to_plotly_figure 适配 5 套主题；
- 注入 640px 响应式滚动容器与 CSS 规则，确保全端零截断、零水平溢出。
      │
      ▼
[Step 6: tests/ 新增专项测试规划 (R6)]
- 新增 tests/test_g10_correlation_liquidity_and_stress.py 包含 6 大专项测试，实现 59 + 6 = 65 项自动化测试 100% 绿灯。
```

---

## 3. 详细实现建议与数据结构设计 (Implementation Recommendation)

### 3.1 `portfolio_manager.py` 实装：`simulate_portfolio_cvar_bootstrap`

#### (1) 函数插入位置
在 `AGY2_FundAdvisory/portfolio_manager.py` 第 8546 行（`evaluate_dynamic_correlation_mutation_instance` 之后，模块级便捷别名前）插入：
1. 类方法：`PortfolioManager.simulate_portfolio_cvar_bootstrap`
2. 实例方法：`PortfolioManager.simulate_portfolio_cvar_bootstrap_instance`
3. 模块级别名：`simulate_portfolio_cvar_bootstrap = PortfolioManager.simulate_portfolio_cvar_bootstrap`

#### (2) 函数签名与参数规范
```python
@classmethod
def simulate_portfolio_cvar_bootstrap(
    cls,
    holdings: Optional[Any] = None,
    total_capital: float = 100000.0,
    investor_risk_tier: str = "C3",
    n_simulations: int = 10000,
    block_size: int = 10,
    horizon_days: int = 60,
    random_seed: int = 42,
    pm_instance: Optional[Any] = None,
    **kwargs
) -> Dict[str, Any]:
```

#### (3) 三大历史极端情景定义 (`HISTORICAL_SCENARIOS_G10`)
```python
HISTORICAL_SCENARIOS_G10 = [
    {
        "id": "2008_financial_crisis",
        "name": "2008 全球金融危机与A股单边暴跌",
        "period": "2008-01-02 ~ 2008-11-04",
        "desc": "次贷海啸引发全球资产重定价，沪深300单边暴跌-71.6%，纯债与黄金大幅避险走强",
        "severity": "极值系统性崩溃",
        "h300_mdd_pct": 71.60,
        "asset_class_returns": {
            "纯债固收": 0.105,      # +10.5%
            "黄金对冲": 0.142,      # +14.2%
            "A股红利低波": -0.550,   # -55.0% (相对抗跌)
            "核心蓝筹": -0.716,     # -71.6%
            "中小盘成长": -0.760,   # -76.0%
            "美股海外对冲": -0.500,  # -50.0%
        },
        "liquidity_multipliers": {
            "纯债固收": 1.0, "黄金对冲": 1.0, "A股红利低波": 1.4,
            "核心蓝筹": 1.8, "中小盘成长": 2.2, "美股海外对冲": 2.5
        }
    },
    {
        "id": "2015_liquidity_stampede",
        "name": "2015 去杠杆与流动性踩踏危机",
        "period": "2015-06-12 ~ 2015-08-26",
        "desc": "场外杠杆资金去杠杆引发恶性循环，千股跌停、流动性瞬间冻结，中小创暴跌逾-55%",
        "severity": "极端流动性瞬间枯竭",
        "h300_mdd_pct": 43.29,
        "asset_class_returns": {
            "纯债固收": 0.078,      # +7.8% (货币宽松大牛市)
            "黄金对冲": -0.021,     # -2.1%
            "A股红利低波": -0.325,   # -32.5%
            "核心蓝筹": -0.433,     # -43.3%
            "中小盘成长": -0.620,   # -62.0%
            "美股海外对冲": -0.080,  # -8.0%
        },
        "liquidity_multipliers": {
            "纯债固收": 1.0, "黄金对冲": 1.2, "A股红利低波": 1.8,
            "核心蓝筹": 2.2, "中小盘成长": 3.0, "美股海外对冲": 1.5
        }
    },
    {
        "id": "2024_smallcap_liquidity",
        "name": "2024 年初雪球敲入与微盘流动性危机",
        "period": "2024-01-02 ~ 2024-02-05",
        "desc": "雪球集中敲入与量化微盘踩踏挤兑，中证1000回撤-26.7%，央国企高股息与纯债逆势大涨",
        "severity": "小微盘结构性流动性挤兑",
        "h300_mdd_pct": 6.10,
        "asset_class_returns": {
            "纯债固收": 0.018,      # +1.8%
            "黄金对冲": 0.025,      # +2.5%
            "A股红利低波": 0.045,    # +4.5% (逆势上涨)
            "核心蓝筹": -0.061,     # -6.1%
            "中小盘成长": -0.267,   # -26.7%
            "美股海外对冲": 0.050,   # +5.0%
        },
        "liquidity_multipliers": {
            "纯债固收": 1.0, "黄金对冲": 1.0, "A股红利低波": 1.0,
            "核心蓝筹": 1.2, "中小盘成长": 2.5, "美股海外对冲": 1.0
        }
    }
]
```

#### (4) 块重采样与最大回撤算法 (NumPy 纯向量化)
1. 基于 `cls.classify_fund_asset_class` 将当前组合归一化权重 $\mathbf{w}$ 映射到各大类资产；
2. 对于每个情景 $S$：
   - 提取日度合成收益率序列 $R_S$（共 $T_S$ 天）；若使用情景日度历史代理序列（如 2008 年真实日收益序列），或使用情景平均日波动率构建自相关块序列；
   - 采用 Circular Block Bootstrap：
     ```python
     rng = np.random.RandomState(random_seed)
     b_size = max(2, min(30, int(block_size))) # 默认 10
     n_blocks = int(np.ceil(horizon_days / b_size))
     st_idx = rng.randint(0, len(returns), size=(n_simulations, n_blocks))
     offsets = np.arange(b_size)
     block_matrix = (st_idx[:, :, None] + offsets).reshape(n_simulations, n_blocks * b_size)[:, :horizon_days] % len(returns)
     sim_rets = returns[block_matrix]
     nav_paths = np.cumprod(1.0 + sim_rets, axis=1)
     full_nav = np.column_stack([np.ones((n_simulations, 1)), nav_paths])
     cummax = np.maximum.accumulate(full_nav, axis=1)
     drawdowns = (full_nav - cummax) / np.maximum(cummax, 1e-8)
     mdd_arr = np.abs(np.min(drawdowns, axis=1)) # 10,000 个最大回撤值
     ```
   - 极值指标输出：
     - $p_{50} = \text{percentile}(mdd\_arr, 50) \times 100$
     - $VaR_{95\%} = \text{percentile}(mdd\_arr, 95) \times 100$
     - $VaR_{99\%} = \text{percentile}(mdd\_arr, 99) \times 100$
     - $CVaR_{99\%} = \max(VaR_{99\%}, \text{mean}(mdd\_arr[mdd\_arr \ge \text{percentile}(mdd\_arr, 99)]) \times 100)$

#### (5) 投资者适当性 C1 至 C5 矩阵联动与限额判定
```python
TIER_MDD_LIMITS = {
    "C1": 5.0,   # 最大容忍回撤 5%
    "C2": 10.0,  # 最大容忍回撤 10%
    "C3": 15.0,  # 最大容忍回撤 15%
    "C4": 25.0,  # 最大容忍回撤 25%
    "C5": 40.0,  # 最大容忍回撤 40%
}
TIER_LIQ_DAY_LIMITS = {
    "C1": 3.0,   # 最多容忍 3 天变现
    "C2": 5.0,   # 最多容忍 5 天变现
    "C3": 7.0,   # 最多容忍 7 天变现
    "C4": 10.0,  # 最多容忍 10 天变现
    "C5": 15.0,  # 最多容忍 15 天变现
}
```
对每个情景，计算当前组合预测 MDD（采用 $CVaR_{99\%}$ 或情景特定预测回撤）与该等级契约限额对比：
- 若 $\text{Predicted MDD} \le \text{Limit}$：状态标记为 `COMPLIANT_SAFE` (🟢 契约合规)；
- 若 $\text{Limit} < \text{Predicted MDD} \le \text{Limit} \times 1.3$：标记为 `BREACH_WARNING` (🟡 适度越界警告)；
- 若 $\text{Predicted MDD} > \text{Limit} \times 1.3$：标记为 `SEVERE_BREACH` (🔴 严重违约超限)；
- 并输出超额风险暴露：$\Delta \text{Exposure} = \max(0, \text{Predicted MDD} - \text{Limit}) \times \text{total\_capital}$。

#### (6) 流动性变现天数 (Liquidity Liquidation Days) 精算公式
针对持仓中单只标的 $i$：
1. 基础赎回交收周期 $T_{\text{base}, i}$：
   - 纯债/货币：1.0 天；
   - 境内股票/偏股/红利：2.0 天；
   - QDII / 海外成熟股票：5.0 天；
2. 锁定期与在途限制 $T_{\text{lock}, i}$：
   - 若批次持仓天数 $< 7$ 天：$T_{\text{lock}, i} = 7 - \text{holding\_days}$；
   - 若 $\ge 7$ 天：$T_{\text{lock}, i} = 0$；
3. 危机情景流动性顺延乘数 $\lambda_{S, i}$（见情景定义中 `liquidity_multipliers`）；
4. 季报重仓股日均成交与规模冲击追加天数 $T_{\text{adv}, i}$：
   $$T_{\text{adv}, i} = \max\left(0, \left\lceil \frac{\text{Order Amount}}{0.05 \times \text{ADV}_i} \right\rceil - 1\right)$$
5. 单基在情景 $S$ 下的变现天数：
   $$T_{i, S} = T_{\text{base}, i} \times \lambda_{S, i} + T_{\text{lock}, i} + T_{\text{adv}, i}$$
6. 组合级综合指标：
   - **加权平均变现天数**：$T_{\text{avg}, S} = \sum_i w_i T_{i, S}$；
   - **90% 资金快速变现天数**：按 $T_{i, S}$ 升序排列，累加权重达 90% 时的天数 $T_{90, S}$；
   - **100% 完全变现天数**：$T_{100, S} = \max_i T_{i, S}$。

#### (7) 返回数据结构定义
```python
{
    "total_capital": 100000.0,
    "investor_risk_tier": "C3",
    "scenarios": [
        {
            "id": "2008_financial_crisis",
            "name": "2008 全球金融危机与A股单边暴跌",
            "period": "2008-01-02 ~ 2008-11-04",
            "predicted_mdd_pct": 28.50,          # 组合预测最大回撤
            "predicted_loss_amount": 28500.0,
            "h300_mdd_pct": 71.60,
            "excess_defense_pct": 43.10,         # 相对沪深300少跌 43.10%
            "liquidity_discount_pct": 1.85,
            "liquidity_discount_amount": 1850.0,
            "total_cvar_99_pct": 30.35,
            "liquidation_days": {
                "avg_days": 3.8,
                "days_90_pct": 4.5,
                "days_100_pct": 7.0,
                "limit_days_tier": 7.0,
                "is_liquidity_safe": True
            },
            "tier_evaluations": {
                "C1": {"limit_mdd": 5.0, "is_breach": True, "breach_excess_pct": 23.50, "status": "SEVERE_BREACH"},
                "C2": {"limit_mdd": 10.0, "is_breach": True, "breach_excess_pct": 18.50, "status": "SEVERE_BREACH"},
                "C3": {"limit_mdd": 15.0, "is_breach": True, "breach_excess_pct": 13.50, "status": "BREACH_WARNING"},
                "C4": {"limit_mdd": 25.0, "is_breach": True, "breach_excess_pct": 3.50, "status": "BREACH_WARNING"},
                "C5": {"limit_mdd": 40.0, "is_breach": False, "breach_excess_pct": 0.0, "status": "COMPLIANT_SAFE"}
            }
        },
        # 2015 与 2024 情景结构同上
    ],
    "monte_carlo_3d_data": {
        "scenarios": ["2008金融危机", "2015流动性踩踏", "2024小盘股危机"],
        "tiers": ["C1", "C2", "C3", "C4", "C5"],
        "z_mdd_matrix": [[...], [...], [...]],   # 3 x 5 矩阵
        "z_liq_matrix": [[...], [...], [...]]    # 3 x 5 矩阵
    }
}
```

---

### 3.2 `AGY2_FundAdvisory/app_gui.py` 前端集成点与视觉闭环 (R5)

#### (1) 首屏双翼看板挂载 (Lines 2546 ~ 2901)
- **左翼/右翼分工**：
  在右翼 `col_sentry`（第 2743 行，主动风险预警哨区域）顶部或卡片列表中：
  1. **多资产相关性突变预警指示卡**：
     调用 `pm.evaluate_dynamic_correlation_mutation_instance(threshold=0.80)`：
     - 若当前相关系数 $> 0.80$：展示红色高亮警报卡片，明确显示“当前红利与周期权重相关系数 X.XX > 0.80，共振突变！”，并提供“🛡️ 启动流动性平移（一键移至纯债与黄金）”按钮；
     - 若 $\le 0.80$：展示绿色指示胶囊：“🟢 跨资产低相关隔离良好 (当前 EWMA 相关系数 X.XX < 0.80)”。
  2. **压力测试流动性指标卡片**：
     紧随预警哨之后，展示紧凑型流动性三连指标：
     - 极限 CVaR 99%：`-XX.XX%`
     - 底层流动性折价损失预估：`-X.XX%`
     - 组合加权变现天数：`X.X 交易日 (C3 限额 ≤ 7 天)`

#### (2) Tab 1 ("🌱 新资建仓") 挂载 (Lines 3540 ~ 4115)
1. **蒙特卡洛压力测试三维分布图 (Step 3, 第 3540 至 3550 行)**：
   在现有的 `render_black_swan_stress_card` 内或下方添加 3D 交互图表：
   - 提取 `stress_data.get("monte_carlo_3d_data")`；
   - 使用 Plotly 渲染 `go.Figure(data=[go.Surface(...)])` 或 `go.Scatter3d`；
   - X 轴：三大极端危机情景（2008、2015、2024）；
   - Y 轴：C1 至 C5 风险偏好等级；
   - Z 轴：预测最大回撤百分比与流动性变现天数；
   - 强制调用 `apply_theme_to_plotly_figure(fig_3d)`，使 3D 轴网格、背景色与当前主题（白/黑）100% 融合；
   - 外层包裹 `st.expander("🎲 查看蒙特卡洛极端承压 3D 分布曲面图", expanded=False)`。
2. **大额订单流动性折价明细表 (Step 4, 第 4015 至 4115 行)**：
   在智能微观执行卡片下方新增 `with st.expander("🌊 大额订单流动性折价与底层冲击明细表", expanded=False)`：
   - 表格字段：`基金代码`、`基金名称`、`场内/场外`、`计划买入金额`、`季报前5重仓日均成交(ADV)`、`基金规模(亿元)`、`流动性折价比例(bps)`、`预计折价损耗(元)`、`优化节省金额(元)`、`建议变现/吸筹调度`；
   - 使用 `st.dataframe(df_liq, use_container_width=True, hide_index=True)`。

#### (3) Tab 2 ("💼 持仓调仓") 挂载 (Lines 5506 ~ 5645)
1. **大额订单流动性折价明细表**：
   在调仓执行表 `df_orders_tbl`（第 5607 行）紧邻下方，新增展开栏：
   - 展示本次调仓涉及的卖出减仓与买入加仓标的的流动性折价精算；
   - 针对单笔金额 $> 1$ 万元或总规模超 ADV 5% 的标的给出红色/黄色流动性折价预警；
2. **蒙特卡洛压力测试三维分布图**：
   在 Tab 2 决策主视图底部（或浮盈安全垫看板后方），挂载当前实盘持仓账本的蒙特卡洛 3D 压力曲面。

#### (4) CSS 规则与 640px 移动端零截断保障
在第 1346 至 1375 行的 `@media (max-width: 640px)` 区块中：
```css
/* 640px 移动端蒙特卡洛 3D 与流动性宽表防溢出 */
.stress-3d-container {
    width: 100% !important;
    overflow-x: auto !important;
    overflow-y: hidden;
    scrollbar-width: thin;
}
.liquidity-table-scroll-container {
    width: 100% !important;
    overflow-x: auto !important;
    -webkit-overflow-scrolling: touch;
}
```
并且所有 HTML 字符串严格通过 `safe_markdown_html(html_code)` 渲染，内部自动执行 `_clean_html()`，杜绝任何 4+ 空格缩进引发的 Markdown 格式错乱。

---

### 3.3 测试套件规划与专项用例设计 (R6)

#### (1) 测试套件运行基线
- 现有测试命令（59 项）：
  ```bash
  py -3 -m pytest tests/test_infra.py tests/test_adv_final_closure.py tests/test_g3_evolution_loop.py tests/test_gui_multi_ledger_stress.py tests/test_g9_causal_brinson_and_suitability.py
  ```
- 目标：原有 59 项测试零修改、100% 保持通过。

#### (2) 新建专属专项测试文件
新建 `tests/test_g10_correlation_liquidity_and_stress.py`，规划 6 大针对性测试类与方法：

```python
# -*- coding: utf-8 -*-
"""
G10 世代多资产相关性突变、极端流动性冲击折价与穿透式蒙特卡洛压力测试闭环专项测试套件
tests/test_g10_correlation_liquidity_and_stress.py
"""

class TestG10CorrelationLiquidityAndStress:
    """G10 核心需求专项验证"""

    def test_g10_1_correlation_mutation_threshold_and_liquidity_shift(self):
        """
        验证 R2:
        1. 当相关系数突破 0.80 时，确定性触发相关性突变预警；
        2. 触发跨资产流动性平移预案，将高估值高波标的定向削减并转移至纯债 (002351) 与黄金 (000216)；
        3. 权重严格归一化 sum(w.values()) == 1.000000。
        """

    def test_g10_2_otc_fund_micro_execution_haircut_and_adv_ratio(self):
        """
        验证 R3:
        1. 针对场外公募基金，结合季报前五大重仓股 ADV 与基金规模真实测算流动性折价；
        2. 验证折价率与折价金额随订单规模非线性单调递增，杜绝静态假常数；
        3. 验证场内 ETF 与场外公募双轨识别准确性。
        """

    def test_g10_3_portfolio_manager_cvar_bootstrap_three_scenarios(self):
        """
        验证 R4:
        1. PortfolioManager.simulate_portfolio_cvar_bootstrap 成功输出三大极端情景：
           - 2008_financial_crisis
           - 2015_liquidity_stampede
           - 2024_smallcap_liquidity
        2. 验证 10,000 次块重采样 (block_size=10, horizon_days=60)；
        3. 验证极值数学不变量：CVaR 99% >= VaR 99% >= VaR 95%。
        """

    def test_g10_4_c1_to_c5_risk_tier_max_drawdown_and_liquidation_days(self):
        """
        验证 R4:
        1. 验证 C1 至 C5 风险偏好等级的契约限额对比矩阵完整输出；
        2. 验证保守型 C1 越界时正确输出违规预警与超额暴露金额；
        3. 验证流动性变现天数 (加权平均天数、90% 变现天数、100% 变现天数) 计算严密性；
        4. 2015 踩踏情景下的股票变现天数显著大于常态。
        """

    def test_g10_5_app_gui_r5_source_wireup_verification(self):
        """
        验证 R5 静态结构：
        1. app_gui.py 首屏双翼看板挂载相关性突变预警与压力测试流动性指标；
        2. Tab 1 与 Tab 2 包含大额订单流动性折价明细表与蒙特卡洛 3D 分布图调用；
        3. safe_markdown_html 与 _clean_html 纯化保护；
        4. 640px 移动端 CSS 与横向滚动容器。
        """

    def test_g10_6_apptest_gui_stress_and_liquidity_render(self):
        """
        验证 R5 运行时健康：
        利用 Streamlit AppTest.from_file 无头运行 app_gui.py，
        断言渲染全流程 assert not at.exception，首屏双翼、Tab 1、Tab 2 零异常崩溃。
        """
```

#### (3) 验收总回归命令
```bash
py -3 -m pytest tests/test_infra.py tests/test_adv_final_closure.py tests/test_g3_evolution_loop.py tests/test_gui_multi_ledger_stress.py tests/test_g9_causal_brinson_and_suitability.py tests/test_g10_correlation_liquidity_and_stress.py -v
```
预期结果：**65 passed**（59 项原有基线 + 6 项新增专项）。

---

## 4. 潜在隐患与防御措施 (Caveats & Defenses)

1. **计算性能与 10,000 次仿真延迟**：
   - 隐患：在用户交互时若每次刷新页面都执行 10,000 次蒙特卡洛重采样，可能导致 Streamlit 渲染卡顿（耗时超过 500ms）。
   - 防御措施：
     1) 纯 NumPy 向量化（`RandomState.randint` 一次性生成 `(10000, n_blocks)` 索引阵列，避免 Python `for` 循环）；
     2) 在 `st.session_state` 或本地内存对重采样结果进行轻量级缓存（基于组合权重哈希，仅在持仓变动时重新触发计算）。
2. **只读裁判文件绝对保护**：
   - 隐患：`tests/test_infra.py`、`judge_engine.py`、`holdout_vault.py`、`AGENT_SPEC.md` 为只读裁判文件。
   - 防御措施：所有新测试必须严格置于独立的 `tests/test_g10_correlation_liquidity_and_stress.py` 中，绝不触碰任何裁判文件。
3. **HTML 缩进与 CommonMark 代码块泄露 (Rule 27)**：
   - 隐患：新增的 3D 图表展开栏或大额流动性折价卡片可能在多层 `f"""..."""` 缩进中引入 4 个以上前导空格，导致文字变成代码框。
   - 防御措施：所有前端富文本组件强制使用 `return _clean_html(...)` 并在前端统一由 `safe_markdown_html(...)` 调用。
4. **移动端 640px 视口宽度横向溢出 (Rule 14 & 15)**：
   - 隐患：大额订单流动性折价表包含 10 列信息，在 640px 窄屏下若无容器包裹会导致界面撑破横向拉伸。
   - 防御措施：宽表外层配置 `use_container_width=True`，且卡片与 Plotly 3D 容器包裹 `.stress-3d-container` 设置 `overflow-x: auto !important`。

---

## 5. 结论 (Conclusion)

1. **R4 穿透式多周期蒙特卡洛压力测试**：
   - 架构完全清晰：在 `AGY2_FundAdvisory/portfolio_manager.py` 实装 `simulate_portfolio_cvar_bootstrap`；
   - 底层行情数据完备：2008（沪深300 -71.60%）、2015（去杠杆踩踏 -43.29%）、2024（小盘微盘危机 -26.67%）真实日线数据已完备于 `data/processed/indices/`；
   - 块重采样与 C1~C5 适当性等级、流动性变现天数算法逻辑与数学公理已严格定义闭环。
2. **R5 多模态视觉走查闭环**：
   - 首屏双翼看板右翼、Tab 1 与 Tab 2 的挂载锚点已精确定位至对应代码行；
   - Plotly 3D 分布图与大额订单流动性折价明细表的展示形态与 640px 响应式防溢出机制已完全就绪。
3. **R6 自动化测试基线**：
   - 现有 59 项基线测试结构明晰，已规划 `tests/test_g10_correlation_liquidity_and_stress.py`（6 项专项测试），保障增量演进与全量 100% 绿灯。

---

## 6. 独立验证方法 (Verification Method)

后续负责实现的工程师或测试员可通过以下步骤独立核实本调研报告所有结论：

1. **核验 59 项基线测试收集**：
   ```bash
   py -3 -m pytest tests/test_infra.py tests/test_adv_final_closure.py tests/test_g3_evolution_loop.py tests/test_gui_multi_ledger_stress.py tests/test_g9_causal_brinson_and_suitability.py --collect-only
   ```
   *预期：终端打印 `collected 59 items`。*

2. **核验 2008 与 2015 指数历史数据存在性**：
   ```bash
   py -3 -c "import pandas as pd; df = pd.read_parquet('data/processed/indices/000300.SH.parquet'); print(df['date'].min(), df['date'].max())"
   ```
   *预期：输出包含 `2002-01-04` 至 `2026-10-28`。*

3. **核验当前 `portfolio_manager.py` 现状**：
   检查 `AGY2_FundAdvisory/portfolio_manager.py` 第 8369 至 8566 行，确认 `evaluate_dynamic_correlation_mutation` 存在而 `simulate_portfolio_cvar_bootstrap` 尚待实现。

4. **核验 `app_gui.py` 挂载点**：
   检查 `AGY2_FundAdvisory/app_gui.py`：
   - 第 2538 至 2906 行（`render_dual_wing_advisory_dashboard`）；
   - 第 3540 至 3550 行（Tab 1 压力测试卡片）；
   - 第 5500 至 5645 行（Tab 2 调仓与执行明细）。
