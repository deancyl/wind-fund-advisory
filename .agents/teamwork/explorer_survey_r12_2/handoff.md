# Handoff Report — Explorer Survey R12-2

## 1. Observation

- **文件观测 1**：`AGY2_FundAdvisory/advisory_engine.py` (第 1545-1670 行) 存在 `SmartExecutionDCAEngine.verify_historical_inflection_signals(cls, df=None)`：
  ```python
  m2021 = hist_metrics.get("2021-02-18", {"erp_pct": 28.9, "bias_20": 4.30})
  m2022 = hist_metrics.get("2022-04-26", {"erp_pct": 76.0, "bias_20": -8.27})
  m2024 = hist_metrics.get("2024-09-18", {"erp_pct": 90.6, "bias_20": -2.60})
  ```
  实测运行返回：
  - `2021_top`: `multiplier = 0.50`, `multiplier_tag = "🟡 0.5x 防守微扣"`, `is_valid = True`
  - `2022_bottom`: `multiplier = 1.93`, `multiplier_tag = "🚀 2.0x 逆向猛扣"`, `is_valid = True`
  - `2024_bottom`: `multiplier = 1.94`, `multiplier_tag = "🚀 2.0x 逆向猛扣"`, `is_valid = True`
  - `all_inflections_verified = True`

- **文件观测 2**：`AGY2_FundAdvisory/strategy_bridge.py` (第 2878-2900 行 与 第 3220 行) 提取当前市场 ERP 与 Bias20：
  - 调用 `StrategyBridge.get_latest_market_snapshot()` 实测返回：
    - `erp_percentile`: `82.63%`
    - `bias_20`: `-2.07%`
    - `pe_ttm_300`: `12.23`
    - `treasury_10y`: `1.623%`
    - 调用 `plan_smart_dca` 计算当前定投乘数为 `1.76x` (`⚡ 1.5x 加速吸筹`)，处于极度低估水下超跌收集廉价筹码阶段。

- **文件观测 3**：`AGY2_FundAdvisory/portfolio_manager.py` (第 2214-2280 行) 实现了 `fetch_realtime_fund_quote(fund_code)`，返回 `FundQuote`（第 2104 行）：
  - 包含 `[name, dwjz, gsz, gszzl, gztime, fund_code, valuation_corrected]`。
  - 实测运行：
    - `005561`: `dwjz=2.2141, gsz=2.2361, gszzl=+0.99%, gztime=2026-11-06 16:02:00`
    - `011613`: `dwjz=1.0298, gsz=1.0044, gszzl=-2.47%, gztime=2026-11-06 16:03:00`
    - `002351`: `dwjz=1.6060, gsz=1.6070, gszzl=+0.06%`

- **文件观测 4**：`AGY2_FundAdvisory/advisory_engine.py` (第 1367-1372 行) 遗留三档固定波动率常数：
  ```python
  elif any(k in fn for k in ["债", "固收", "纯债"]) or fc == "002351":
      vol = 0.04
  elif any(k in fn for k in ["黄金"]) or fc == "000216":
      vol = 0.14
  else:
      vol = 0.18
  ```
  通过 `data/processed/aligned_matrix_total_return.parquet` 测算真实 20 日指标：
  - 纯债 `H11009`: $\sigma_{\text{day}} = 0.05\%$, 年化波动率 $0.82\%$
  - 红利低波 `H30269`: $\sigma_{\text{day}} = 0.92\%$, 年化波动率 $14.59\%$
  - 沪深300 `H00300`: $\sigma_{\text{day}} = 1.08\%$, 年化波动率 $17.08\%$
  - 黄金ETF `AU9999`: $\sigma_{\text{day}} = 1.32\%$, 年化波动率 $20.82\%$
  - 科创50 `STAR50_STITCH`: $\sigma_{\text{day}} = 2.39\%$, 年化波动率 $37.75\%$

- **文件观测 5**：`AGY2_FundAdvisory/app_gui.py`：
  - 首屏双翼看板在第 2163-2173 行渲染“📢 今日市场脉搏晨报”；
  - Tab 1 在第 3415-3515 行渲染智能定投及小抄；
  - Tab 2 在第 5280-5338 行渲染调仓执行表 `df_orders_tbl`，包含 `建议操作` 与 `实操要点` 列；
  - `<style>` 在第 362 行定义了全局 CSS。

---

## 2. Logic Chain

1. **从观测 1 与观测 2 到历史三大牛熊拐点实盘对照尺**：
   - 观测 1 证实后端的 `verify_historical_inflection_signals` 已经实现了三大拐点的实证回放；
   - 观测 2 证实前端已具备通过 `StrategyBridge.get_latest_market_snapshot()` 实时提取当前宏观 ERP 分位与 MA20 乖离率的能力；
   - 因此，只需在 `SmartExecutionDCAEngine` 增加统一的数据结构接口 `get_historical_inflection_ruler`，并在 `app_gui.py` 的首屏“今日市场脉搏晨报”（观测 5）与 Tab 1 智能定投区渲染 4 节点对比条（2021 核心见顶 0.50x、2022 恐慌底 1.93x、2024 反转底 1.94x、今日实时 1.76x），同时精简原本重复的文本，即可完全满足需求并达成“界面复杂度守恒原则”。

2. **从观测 3 与观测 4 到 14:30 尾盘实时估值异动预警**：
   - 观测 3 证实无需任何外部新接口，现有的 `fetch_realtime_fund_quote` 即可毫秒级返回真实估算涨跌幅 `gszzl`；
   - 观测 4 证实各品类资产日均波动幅度差异巨大（纯债 0.05% vs 科创50 2.39%），若使用固定常量会导致严重的误判或漏判；
   - 因此，必须通过三级穿透（单基日线 -> 赛道日线 -> 对齐矩阵对应列）计算单基真实 $\sigma_{\text{day}}$ 与自身 $\text{Bias20}$，构建 $1.5\sigma_{\text{day}}$ 动态异动判别阈值：
     - $gszzl > +1.5\sigma_{\text{day}}$ 且 $\text{Bias20} > 0 \rightarrow$ 触发防追高，建议下调申购/定投额 30%~50%；
     - $gszzl < -1.5\sigma_{\text{day}}$ 且 $\text{Bias20} < 0 \rightarrow$ 触发黄金坑，建议 14:30~14:50 正常或适度增配 10%~20%；
   - 将上述判定接入 Tab 2 调仓执行表的 `建议操作` 与 `实操要点` 列（观测 5），并配合 CSS 媒体查询，即可完成完整风控闭环。

---

## 3. Caveats

- **无盘中估值的特殊标的**：若遇个别纯债基金或特定 QDII 基金在盘中无天天基金估值数据，`fetch_realtime_fund_quote` 会自动回退至最新官方净值或基准指数纠偏（`valuation_corrected = True`），`gszzl` 此时为跟踪基准实时涨跌幅，算法需兼容该纠偏值。
- **历史数据不足 20 个交易日的新基金**：对于上市不足 20 天的新发次新基金，日线序列长度 $< 20$，算法应按第三顺位平滑回退至其对标的一级赛道基准指数日线。

---

## 4. Conclusion

1. **历史三大牛熊拐点实盘对照尺**：底层计算完备（2021: 0.50x, 2022: 1.93x, 2024: 1.94x, 当前: 1.76x），实现方案明确，建议在 `advisory_engine.py` 暴露 `get_historical_inflection_ruler`，并在 `app_gui.py` 首屏市场脉搏以一行式横向滚动胶囊条呈现。
2. **14:30 尾盘实时估值异动预警**：数据源与算法模型完备，消除三档固定常量后，通过单基穿透计算真实 $\sigma_{\text{day}}$ 与自身 $\text{Bias20}$，以 $\pm 1.5\sigma_{\text{day}}$ 为界触发防追高与黄金坑，并在 Tab 2 与 Tab 1 调仓执行单与定投指引中落地，完全符合公募基金真实交易规则与界面自适应不变量。

---

## 5. Verification Method

后续实施智能体与测试人员可通过以下方式进行独立复验：
1. **单测套件命令**：
   `pytest tests/test_infra.py tests/test_g3_evolution_loop.py -k "inflection"`
2. **专项探针运行**：
   - 运行 `py -3 d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r12_2\test_snapshot.py` 验证当前市场与历史三大拐点的数据一致性；
   - 运行 `py -3 d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r12_2\test_quote.py` 验证 `fetch_realtime_fund_quote` 的实时盘中估值返回值；
   - 运行 `py -3 d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r12_2\test_metrics.py` 验证各资产真实 20 日波动率与乖离率。
3. **失效条件**：
   - 若拐点定投乘数背离实证约束（2021年乘数 $>0.5$ 或 2024年乘数 $<1.8$），则验证失败；
   - 若 `calculate_vwap_execution_slippage` 仍输出硬编码的固定伪常数，则验证失败；
   - 若在 640px 窄视口下出现文字重叠截断，则验证失败。
