# Handoff Report — Explorer 2 (G6 Codebase Survey)

## 1. Observation
1. **用户风险档位 C1~C5 定义与约束**:
   - `d:\Google\Workspace\Wind\AGY2_FundAdvisory\strategy_bridge.py:191-282`: 定义了 `RISK_TIERS_CONFIG`，包含 C1（安稳保守型，目标 5%~8%，回撤限制 5%）、C2（稳健固收+型，目标 8%~12%，回撤限制 10%）、C3（平衡进取型，目标 12%~18%，回撤限制 15%）、C4（成长进攻型，目标 18%~30%，回撤限制 25%）、C5（极限高Beta追击型，目标 30%~100%+，回撤限制 40%）。
   - `d:\Google\Workspace\Wind\AGY2_FundAdvisory\portfolio_optimizer.py:226-232`: 定义了 `MAX_DRAWDOWN_BY_TIER = {"C1": 0.05, "C2": 0.10, "C3": 0.18, "C4": 0.25, "C5": 0.35}`。
2. **20 日单基波动率与组合风险穿透算子**:
   - `d:\Google\Workspace\Wind\AGY2_FundAdvisory\advisory_engine.py:1260-1405`: `SmartExecutionDCAEngine.get_fund_real_volatility_and_bias` 实现了基于本地真实日线湖仓的单基过去 20 个交易日真实年化波动率穿透：`vol = float(np.std(rets, ddof=1) * np.sqrt(250))`。
   - `d:\Google\Workspace\Wind\AGY2_FundAdvisory\portfolio_optimizer.py:1870-1953`: `calculate_portfolio_risk_contributions` 计算了协方差风险贡献及组合年化波动率 `ann_vol = round(float(np.sqrt(port_var * 252.0)) * 100.0, 2)`。
3. **调仓路径与交易风控拦截**:
   - `d:\Google\Workspace\Wind\AGY2_FundAdvisory\portfolio_optimizer.py:1441-1592`: `WinRateOptimizer.optimize_rebalance_path` 接收 `current_holdings`、`optimal_weights`、`total_value`，在第 1489~1505 行通过 `penalty_free_shares` 强制保护未满 7 天锁定份额。
   - `d:\Google\Workspace\Wind\AGY2_FundAdvisory\portfolio_manager.py:6070-6085`: `get_penalty_free_redeemable_shares` 基于 FIFO 顺序累加满 7 天免惩罚份额；第 6126-6130 行阻断强行卖出未满 7 天批次。
4. **分红追踪与分红除权机制**:
   - `d:\Google\Workspace\Wind\AGY2_FundAdvisory\portfolio_manager.py:273`: `FundHolding` 包含 `dividend_method: str = "cash"`；
   - `d:\Google\Workspace\Wind\AGY2_FundAdvisory\portfolio_manager.py:7734-7787`: `process_dividend` 处理分红除权：现金分红调降成本净值、分红款入账 `available_cash`；红利再投资折算新增批次，批次持有天数 `holding_days = 0`。
   - `d:\Google\Workspace\Wind\AGY2_FundAdvisory\strategy_bridge.py:6476-6486`: `dividend_yield_map` 维护了标的的真实股息率（如 100032 为 5.2%，005561 为 5.5%）。
5. **在途交收与踏空摩擦模型**:
   - `d:\Google\Workspace\Wind\AGY2_FundAdvisory\portfolio_manager.py:6259-6263` 与 `strategy_bridge.py:6869`: 在途踏空成本 `InTransitCost = Amount * sigma_index * sqrt(delta_t / 250)`。
6. **只读裁判文件与测试套件**:
   - `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py` Git 状态均为 0 修改。
   - 运行测试套件：`py -3 -m pytest tests/test_infra.py tests/test_adv_final_closure.py tests/test_g3_evolution_loop.py tests/test_gui_multi_ledger_stress.py`，全部 50 项通过（100% Pass）。

## 2. Logic Chain
1. 从观测 1，当前代码库完备定义了 C1~C5 风险画像，但尚缺少显式的 `TARGET_VOLATILITY_BY_TIER` 目标波动率红线字典。根据适当性制度，建立 `{"C1": 0.05, "C2": 0.08, "C3": 0.12, "C4": 0.16, "C5": 0.22}` 是最符合现有架构与业务常理的设定。
2. 从观测 2，单基 20 日年化波动率穿透算子已就绪，组合 20 日加权年化波动率可由各标的持仓权重与各单基 20 日年化波动率点积得出：$\sigma_{\text{port}} = \sum w_i \sigma_i$，该指标是组合波动率的数学保守上界，且抗样本噪声能力强。
3. 当 $\sigma_{\text{port}} > \sigma_{\text{target}}$ 时，压降比例由经典目标波动率理论推导为 $\text{reduction\_ratio} = \frac{\sigma_{\text{port}} - \sigma_{\text{target}}}{\sigma_{\text{port}}}$。高波资产（权益类、波动率 $>8\%$ 标的）按此比例削减，释放出的资金平移至百亿纯债旗舰 `002351` 或现金缓冲池，使得压降后权重严格归一化。
4. 从观测 4 与 5，公募基金向个人分配分红 100% 免征个人所得税。持有满 1 年以上（`holding_days >= 365`）的红利/高股息基金，若采用红利再投资，新增份额将变为 0 天批次重新受锁定期与赎回费制约；若动态切换为“现金分红”，分红直接以现金形态流入，0 赎回费、0 股息税、0 在途时滞，相比通过“赎回换仓”可为用户硬性节省 $0.50\%$ 的赎回费以及 $0.16\% \sim 0.30\%$ 的在途踏空损耗，实现无损再平衡。
5. 从观测 3 与 6，所有设计严格遵从 $<7$ 天 1.50% 惩罚费拦截、FIFO 批次拆分，且保证 `DataLoader.simulate_execution` 默认签名与 4 个只读裁判文件绝对零修改。

## 3. Caveats
- 组合波动率若采用完整协方差矩阵（$\sqrt{\mathbf{w}^T \mathbf{\Sigma} \mathbf{w}}$），在持仓基金数量较多且部分标的交易历史重叠较短时，可能因协方差矩阵病态或历史相关性突变而失真。因此，风控触发器应优先锚定加权波动率 $\sum w_i \sigma_i$ 或取两者的稳健极大值。
- 本报告为纯只读调查分析报告，未对工作区任何生产代码执行写入操作。

## 4. Conclusion
1. **目标波动率风控设计完备可行**：可在 `portfolio_optimizer.py` 中新增 `TARGET_VOLATILITY_BY_TIER` 与 `apply_target_volatility_risk_control`，并与 `WinRateOptimizer.optimize_rebalance_path` 及前端 Tab 1 / Tab 2 联动。
2. **分红免损耗再平衡路径清晰**：利用 `portfolio_manager.py` 已有的批次天数与 `dividend_method`，识别满 1 年红利标的，在 Tab 2 输出切换为现金分红的量化节省收益清单。
3. **底层安全红线 100% 守死**：四大裁判文件与 `simulate_execution` 签名未受任何触碰，全量 50+ 测试套件稳定全绿。

## 5. Verification Method
1. **只读裁判文件状态核验**:
   ```powershell
   git status --porcelain AGY2_FundAdvisory/judge_engine.py AGY2_FundAdvisory/holdout_vault.py AGY2_FundAdvisory/AGENT_SPEC.md AGY2_FundAdvisory/tests/test_infra.py tests/test_infra.py
   ```
   *预期结果*: 输出为空，确认未发生任何修改。
2. **基建与回归测试执行**:
   ```powershell
   py -3 -m pytest tests/test_infra.py
   py -3 -m pytest tests/test_adv_final_closure.py tests/test_g3_evolution_loop.py
   py -3 -m pytest tests/test_gui_multi_ledger_stress.py
   ```
   *预期结果*: 50 个用例 100% 全部 PASS。
3. **报告文件完整性核验**:
   查看 `d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r13_2\report.md` 确认详尽技术推导与代码引用。
