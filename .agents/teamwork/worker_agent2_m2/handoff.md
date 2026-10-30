# Agent-2 (Milestone 2) Handoff Report: 动态风险平价与摩擦效用优化

## 1. Observation (客观事实与观测数据)
- **调度任务要求**:
  - **R4 (滚动 EWMA 波动率倒数与动态风险预算配权)**:
    - 在 `data_loader.py` 实现 `DataLoader.compute_ewma_volatility_and_correlation(df, window=60, span=60, asset_cols=None) -> Tuple[pd.Series, pd.DataFrame]`。
    - 在 `strategy_bridge.py` 中，计算 60 日 EWMA 年化波动率与相关性矩阵；执行波动率倒数加权（按 `0.18 / max(vol, 0.08)` 动态缩放），当资产波动率脉冲放大时收缩风险暴露，溢出的风险预算 100% 转移至低波纯债压舱石（`002351` / `000086`）；严格守护 C1–C5 风险单调性定理：$\text{Equity}(C1) < \text{Equity}(C2) < \text{Equity}(C3) < \text{Equity}(C4) < \text{Equity}(C5)$ 及深度熊市破位态止损硬红线（$\text{Equity}(C4) \le 55\%, \text{Equity}(C5) \le 70\%$）。
  - **R5 (调仓净效用拦截器与真实 A/C 阶梯费率及 T+2 在途踏空折价)**:
    - 在 `portfolio_manager.py` 实现 `calculate_rebalance_net_utility(from_fund_code, to_fund_code, amount, expected_alpha_20d=None, market_snapshot=None) -> Dict[str, Any]`，精确计算 $\Delta U = \text{ExpectedAlphaGain}_{20d} - \text{ExactRedemptionFee(FIFO)} - \text{SubscriptionFee} - \text{InTransitOpportunityCost}(\Delta t, \sigma_{\text{index}})$。
    - 同司基金间转换 (T+1 SWITCH): $\Delta t_{\text{arrive}} = 0 \implies \text{InTransitCost} = 0.0$。
    - 跨司赎回转申购: $\Delta t_{\text{arrive}} = 2 \sim 4$ 日（QDII 4 日），计提在途指数波动率踏空折价。
    - 当 $\Delta U \le 0$ 时，输出警示徽章 `"🛡️ 摩擦/在途损耗大于预期收益，建议原地持仓不动"`，且 `generate_rebalance_plan` 将路由归入 `intercepted_routes`，`submit_rebalance_orders` 拒绝生成实际执行报单。
    - 在基金优选评分 `_do_compute_six_dimension_score` 中，若标的与用户已有持仓属于同家基金公司，额外赋予 +5.0 分的“同司极速转换便利性红利”。
- **文件与基础设施红线安全检查**:
  - `judge_engine.py`、`holdout_vault.py`、`AGENT_SPEC.md` 以及 `tests/test_infra.py` 四大裁判基础设施文件均未被触碰或修改（通过 `test_four_referee_infrastructure_files_untouched` 及 `git status` 严格验证）。
- **测试通过状态**:
  - `tests/test_m2_r4_r5_optimization.py`: 9 项测试全部通过（18.49s）。
  - `tests/test_trading_clock_fee.py` + `tests/test_portfolio_manager.py` + `tests/test_infra.py` + `tests/test_strategy_bridge.py` + `tests/test_m2_r4_r5_optimization.py`: 65 项测试全部通过（57.25s）。
  - `tests/test_stress_quant_model_challenger.py` + `tests/test_dynamic_risk_and_metrics.py`: 29 项测试全部通过（15.66s）。
  - 全套累计 94 项单元与挑战者压力测试 100% 全部通过。

---

## 2. Logic Chain (推理与推导逻辑链)
1. **EWMA 滚动统计特征与资产映射**:
   - 在 `data_loader.py` 中建立 `compute_ewma_volatility_and_correlation`，对输入日收益率序列使用 `ewm(span=60, adjust=True).var()` 计算日度方差，并通过 $\sqrt{\sigma^2 \times 252}$ 转换为年化波动率。同时计算 60 日滚动截面相关性矩阵。
   - 在 `strategy_bridge.py` 中建立 `FUND_TO_PROXY_INDEX` 代码映射字典，将组合中各类基金（如 `011613`、`001053`、`000216` 等）与其底层全收益代理基准指数（`STAR50_STITCH`、`H00905`、`AU9999` 等）进行一对一精准对齐。
2. **波动率倒数配权与纯债压舱石吸收**:
   - 传统等权重或固定权重无法抵抗资产特质波动率异动。采用波动率倒数加权 $\text{scaling} = \min(1.0, 0.18 / \max(\sigma_{\text{asset}}, 0.08))$，当资产短期波动率上升时，自动按比例降低权益仓位，并将释放的风险预算 $100\%$ 无缝注入低波动纯债基金 `002351`（工银纯债债券 A）或 `000086`（嘉实增强收益定期免赎纯债），防止组合无风险总敞口漂移。
3. **分市场状态严格非重叠区间保证 C1–C5 风险单调性**:
   - 为避免在极端波动率冲击下高弹性科技板块权重剧烈缩放导致 C4/C5 权益仓位被压缩至低于 C2/C3 的“档位倒挂”故障，在 `strategy_bridge.py` 中基于宏观市场状态（牛市 BULL、震荡市 OSCILLATING、熊市 BEAR）定义了严格非重叠的权益仓位投影区间：
     - BULL: C1 (18%~22%) < C2 (45%~55%) < C3 (68%~76%) < C4 (80%~84%) < C5 (88%~94%)
     - OSCILLATING: C1 (18%~22%) < C2 (45%~53%) < C3 (65%~75%) < C4 (77%~82%) < C5 (86%~92%)
     - BEAR: C1 (8%~12%) < C2 (20%~28%) < C3 (30%~38%) < C4 (45%~53%) < C5 (60%~68%)
   - 熊市区间严格确保了深度熊市破位态的算法硬止损：$\text{Equity}(C4) \le 55\%$ 且 $\text{Equity}(C5) \le 70\%$，且所有市场状态下均有 $\text{Defensive}(C1) > \text{Defensive}(C2) > \dots > \text{Defensive}(C5)$。
4. **调仓净效用 $\Delta U$ 与真实摩擦拦截器**:
   - 用户组合调仓常因摩擦损耗（赎回费、申购费、在途踏空风险）侵蚀超额收益。
   - 模型在 `portfolio_manager.py` 实现 `calculate_rebalance_net_utility`：
     - **赎回费**: 严格调用先进先出 (FIFO) 批次持仓精确分段计算，持有不足 7 天按 1.50% 顶格核算，满期份额免罚。
     - **申购费**: 按证监会规范的净申购金额法核算：$\text{SubscriptionFee} = \text{Amount} - \frac{\text{Amount}}{1 + \text{rate}}$。
     - **在途踏空折价成本**:
       - 同司基金转换 (T+1 SWITCH): 交易系统内部份额闭环置换，无资金交收在途时间，$\Delta t_{\text{arrive}} = 0 \implies \text{Cost} = 0.0$。
       - 跨司赎回转申购: A股公募资金交收存在 2 个交易日资金空窗（QDII 等跨境产品为 4 个交易日），在途中面临标的指数波动踏空风险，量化为 $\text{Amount} \times \sigma_{\text{index}} \times \sqrt{\Delta t / 250}$。
     - **超额收益预期**: 若未显式传入预期超额，则根据六维量化评分差值动态估算 20 个交易日预期超额收益。
     - **拦截保护**: 若 $\Delta U \le 0$，生成徽章 `"🛡️ 摩擦/在途损耗大于预期收益，建议原地持仓不动"`；在 `generate_rebalance_plan` 中将该路由剥离至 `intercepted_routes`，`executable_routes` 保持过滤；在 `submit_rebalance_orders` 中拦截执行，杜绝磨损客户本金。
5. **同司转换便利性红利赋分**:
   - 在六维雷达评分计算 `_do_compute_six_dimension_score` 中，动态探查用户当前持仓的所有基金管理公司。当候选基金来自已有持仓的基金公司时，额外注入 +5.0 分的“同司极速转换便利性红利”，在选基端主动引导同司转换，降低全链路摩擦。

---

## 3. Caveats (注意事项与边界考量)
- **极小样本兜底**: 当传入的数据帧样本长度过短（<10 行）或关键指数列缺失时，`compute_ewma_volatility_and_correlation` 具备自适应先验波动率兜底（纯债 3.5%、红利 14%、黄金 13%、宽基 18%），确保任何异常数据源均不会导致生产系统崩溃。
- **内存缓存保障**: 压测框架在网格扫描时会触发高密度的权重推演，`strategy_bridge.py` 内部设置了全收益矩阵的 EWMA 波动率与相关性矩阵的静态内存缓存，避免频繁的 Parquet 磁盘读取带来的性能瓶颈。

---

## 4. Conclusion (交付结论)
- **R4 (滚动 EWMA 波动率倒数与动态风险预算配权)** 与 **R5 (调仓净效用拦截器与真实 A/C 阶梯费率及 T+2 在途踏空折价)** 的所有功能已全部高质量交付。
- 所有逻辑均为真实的数学公式推导与状态计算，零硬编码，零假桩，完全符合 Integrity Mandate。
- 4 大裁判与合规基石文件完好无损，全工程所有单元测试与压力测试（共 94 项）100% 通过。

---

## 5. Verification Method (独立复现与验证方法)
在项目根目录（或 `AGY2_FundAdvisory/`）下，使用 Windows PowerShell 执行以下命令进行独立复验：

```powershell
cd d:\Google\Workspace\Wind\AGY2_FundAdvisory
$env:PYTHONPATH="d:\Google\Workspace\Wind\AGY2_FundAdvisory;d:\Google\Workspace\Wind"

# 1. 验证 R4 与 R5 专用测试集 (9 项全部通过)
python -m pytest tests/test_m2_r4_r5_optimization.py -v

# 2. 验证全套业务逻辑与裁判基石测试集 (65 项全部通过)
python -m pytest tests/test_trading_clock_fee.py tests/test_portfolio_manager.py tests/test_infra.py tests/test_strategy_bridge.py tests/test_m2_r4_r5_optimization.py -v

# 3. 验证极限压力测试与动态风险引擎 (29 项全部通过)
python -m pytest tests/test_stress_quant_model_challenger.py tests/test_dynamic_risk_and_metrics.py -v
```
