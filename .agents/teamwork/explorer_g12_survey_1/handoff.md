# G12 世代调查分析报告：四大断路 Bug 深度排查与风控哨兵参数穿透方案

- **调查专员**: `teamwork_explorer`
- **生成时间**: 2026-11-08T15:20:00Z
- **工作目录**: `d:\Google\Workspace\Wind\.agents\teamwork\explorer_g12_survey_1\`
- **任务代号**: G12 Survey Phase — 4 Circuit-Breaker Bugs & Sentry Parameter Penetration
- **只读契约状态**: 四大裁判文件（`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`）哈希未变，严格只读锁定；全局 `GEMINI.md` 零修改。

---

## 1. 观察事实 (Observation)

### 1.1 Bug 1: 首屏右翼相关性突变预警卡假死 Bug
- **观察位置**: `d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py` 第 2985 至 2990 行（在历史早期版本中对应约第 1480 行附近 `col_sentry` 容器内）
- **现存代码逐字引用**:
  ```python
  # G10: 动态相关性突变指示卡（仅在突变警报或结构异动时渲染，正常区间保持干净）
  try:
      corr_eval_res = pm_instance.evaluate_dynamic_correlation_mutation_instance(threshold=0.75, stress_threshold=0.80)
      if corr_eval_res.get("is_mutation_alarm") or corr_eval_res.get("is_regime_shift_risk"):
          safe_markdown_html(render_correlation_mutation_card_html(corr_eval_res))
  except Exception:
      pass
  ```
- **底层真实返回代码**: `d:\Google\Workspace\Wind\AGY2_FundAdvisory\portfolio_manager.py` 第 8628 至 8646 行：
  ```python
  return {
      "is_triggered": is_triggered,
      "is_liquidity_shift_triggered": is_liquidity_shift_triggered,
      "current_correlation": current_corr,
      "downside_correlation": downside_corr,
      "threshold": threshold,
      "stress_threshold": stress_threshold,
      "status": "MUTATION_ALERT" if is_triggered else "DECOUPLED_NORMAL",
      "alert_level": "red" if (is_liquidity_shift_triggered or current_corr >= 0.80) else ("yellow" if is_triggered else "green"),
      "original_weights": norm_w,
      "adjusted_weights": adjusted_weights,
      "cut_details": cut_details,
      "total_cut_weight_pct": round(total_cut_weight * 100.0, 2),
      "historical_correlation_tail": recent_series,
      "alert_title": alert_title,
      "alert_message": alert_message,
      "action": "触发组合集中度降级与流动性平移预案：定向削减高估值高波及共振资产，平移至纯债 (002351) 与实物黄金 (000216)。",
      "action_type": "correlation_mutation_defense",
      "action_plan": "LIQUIDITY_SHIFT_TO_BOND_AND_GOLD" if is_liquidity_shift_triggered else "CONCENTRATION_DOWNGRADE"
  }
  ```
- **下游渲染函数契约**: `d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py` 第 1849 至 1856 行：
  ```python
  def render_correlation_mutation_card_html(corr_eval: Dict[str, Any]) -> str:
      """渲染首屏双翼看板右翼：多资产相关性突变预警指示卡"""
      if not corr_eval:
          return ""
      is_trig = bool(corr_eval.get("is_triggered"))
      is_shift = bool(corr_eval.get("is_liquidity_shift_triggered"))
      curr_corr = float(corr_eval.get("current_correlation", 0.42))
      down_corr = float(corr_eval.get("downside_correlation", curr_corr))
  ```
- **核心矛盾事实**:
  `portfolio_manager.py` 返回的键名是 `"is_triggered"` 和 `"is_liquidity_shift_triggered"`，下层渲染器 `render_correlation_mutation_card_html` 读取的也是 `"is_triggered"` 和 `"is_liquidity_shift_triggered"`；但 `app_gui.py` 第 2987 行的外层 `if` 门禁却在查询两个完全不存在的幽灵键名 `"is_mutation_alarm"` 和 `"is_regime_shift_risk"`。两者恒为 `None` / `False`，导致预警指示卡在相关系数突破 0.75 或 0.80 时**绝对无法被渲染**，代码完全断路假死。而在 Tab 4（第 6991 行）中，正确使用的是 `is_mut = corr_eval_tb.get("is_triggered", False)`。

---

### 1.2 Bug 2: `sentry.inspect_portfolio` 漏传参数导致维度 8 与维度 9 失效 Bug
- **观察位置**: `d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py` 第 2718 至 2725 行（在历史早期版本对应约第 1281 行附近）：
- **现存代码逐字引用**:
  ```python
  sentry = ActiveRiskSentry()
  _f_metas = {}
  for _c in pm_instance.holdings.keys():
      try:
          _f_metas[_c] = DataLoader.get_fund_metadata(_c) or {}
      except Exception:
          _f_metas[_c] = {}
  sentry_rep = sentry.inspect_portfolio(pm_instance.holdings, snapshot_dict, fund_metadata=_f_metas)
  ```
- **底层签名与维度逻辑**: `d:\Google\Workspace\Wind\AGY2_FundAdvisory\advisory_engine.py` 第 1460 至 1470 行：
  ```python
  def inspect_portfolio(
      self,
      holdings: Any,
      market_snapshot: Optional[Dict[str, Any]] = None,
      fund_metadata: Optional[Dict[str, Dict[str, Any]]] = None,
      snapshot: Optional[Dict[str, Any]] = None,
      investor_risk_tier: Optional[str] = None,
      **kwargs
  ) -> Dict[str, Any]:
  ```
  - **维度 8 (适当性与组合止盈止损)**（第 1947 至 1948 行）：
    ```python
    target_risk_tier = investor_risk_tier or kwargs.get("investor_risk_tier") or kwargs.get("risk_tier") or snapshot.get("investor_risk_tier") or snapshot.get("risk_tier")
    if target_risk_tier:
        # 检测实盘持仓权益比是否突破 C1-C5 上限，以及是否触碰 -5% 至 -35% 组合止损线
    ```
    由于调用端未传 `investor_risk_tier` 且 `snapshot_dict` 中无该字段，`target_risk_tier` 恒为 `None`，维度 8 被 100% 完整跳过。
  - **维度 9 (盘中异动安全垫实时传导)**（第 2041 至 2070 行）：
    ```python
    fund_quotes = snapshot.get("fund_quotes") or snapshot.get("realtime_quotes") or {}
    ...
    for it in normalized_items:
        f_code = it.get("code", "")
        q = fund_quotes.get(f_code, {})
        ...
        raw_gz = q.get("gszzl") or q.get("change_pct") or q.get("chg_pct")
    ```
    由于 `snapshot_dict` 来自 `StrategyBridge.get_latest_market_snapshot()`（仅包含大盘宏观点位如 c300_point 等，无持仓基金实时行情），`fund_quotes` 恒为空字典 `{}`，导致 `intraday_pnl_sum` 恒为 0，维度 9 完全静默失效。
- **状态变量定位**:
  前端当前账本风险等级保存在 `st.session_state.get("active_tier_val", "C3")`（见 `app_gui.py` 第 2204, 3217, 4994 行）；单基实时估值可直接由 `fetch_realtime_fund_quote(code)` 取得。

---

### 1.3 Bug 3: 指数与 ETF 联接基金盘中估值校准精度与季报滞后消除
- **观察位置**: `d:\Google\Workspace\Wind\AGY2_FundAdvisory\portfolio_manager.py` 第 2176 至 2378 行（`QDII_BENCHMARK_MAP`、`_apply_qdii_valuation_correction` 与 `fetch_realtime_fund_quote`）及第 7643 至 7689 行（`calculate_intraday_pnl`）。
- **现存代码逐字引用**:
  ```python
  # QDII 及跨市场/黄金底层基准映射表 (R2)
  QDII_BENCHMARK_MAP: Dict[str, str] = {
      "050025": "sh513500", "001071": "sh513500", ...
      "006075": "sh513100", "017436": "sh513100", ...
      "000216": "sh518880", "000217": "sh518880", ...
  }
  
  def _apply_qdii_valuation_correction(q: FundQuote) -> FundQuote:
      # 仅针对 QDII 与黄金联接（若名称含标普、纳指、黄金）进行基准联动纠偏
      ...
  ```
- **核心缺陷事实**:
  1. `_apply_qdii_valuation_correction` 仅处理了 QDII 美股和黄金，对国内所有核心宽基/行业指数基金及 ETF 联接基金（如 `005561` 易方达红利低波联接、`100032` 富国中证红利、`011612`/`011613` 华夏科创50联接、`008888` 芯片联接、`007339` 沪深300联接、`001053` 中证500、`016634` 中证1000、`161725` 招商中证白酒）完全没有进行基准校准。
  2. 天天基金 `fundgz` 接口的盘中估值是基于基金上一季度披露的季报前十大重仓股加权估算的。公募基金在季度内调仓后，天天基金的静态季报估值经常与真实标的偏离超 1.5%~3.0%。
  3. 场外 ETF 联接基金（Feeder Fund）根据法规将不低于 90%（通常实操保持 95%）的资产投资于目标场内 ETF，其余 5% 保持现金用于流动性赎回。因此其日内真实涨跌幅高度锚定对应场内 ETF 的实时涨跌幅乘以 0.95 仓位系数。
  4. 在 `calculate_intraday_pnl`（第 7666 行）中：
     ```python
     est_pnl = round(h.market_value * (gszzl / 100.0) * 0.95, 2)
     ```
     现存单测 `test_calculate_intraday_pnl`（`AGY2_FundAdvisory/tests/test_live_rebalance_upgrades.py` 第 229 行）严格断言了 `est_pnl == round(h.market_value * (f_pnl["gszzl"] / 100.0) * 0.95, 2)`。校准方案必须严格兼容此测试断言。

---

### 1.4 Bug 4: Tab 1 智能定投当期自适应乘数的标的对齐 Bug
- **观察位置**: `d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py` 第 3886 至 3901 行。
- **现存代码逐字引用**:
  ```python
  elif "智能定投" in cap_deployment_mode:
      erp_pct = float(snapshot.get("erp_percentile", 78.0))
      bias_20 = float(snapshot.get("c300_bias_20", snapshot.get("bias_20", 1.0)))
      dca_plan = SmartExecutionDCAEngine.plan_smart_dca(
          total_capital=float(plan_capital),
          allocations=alloc_list_for_dca,
          erp_percentile=erp_pct,
          bias_20=bias_20,
          periods=12
      )
      ruler_dca = StrategyBridge.get_historical_inflection_ruler(
          current_erp=erp_pct,
          current_bias=bias_20,
          total_capital=float(plan_capital)
      )
  ```
- **核心缺陷事实**:
  1. 调用 `SmartExecutionDCAEngine.plan_smart_dca` 决定定投扣款乘数（0.0x~2.0x）与历史对照尺刻度时，传入的 `bias_20` 与 `erp_pct` 仅仅是沪深 300 单一指数的大盘指标。
  2. 用户构建的投资组合通常由多只异质化资产构成（例如：35% 红利低波、25% 纯债、15% 黄金、15% 科创50、10% 半导体）。各单基的 20 日乖离率与估值分位数截然不同（例如科创50处于 +4.2% 冲高，红利低波处于 -1.8% 超卖，纯债处于 +0.1%）。
  3. 用沪深 300 单一指数代表整个组合的动量与估值，违反了工作区 Rule 23（“彻底消除三档固定假常数 ... 严禁用大盘统一指标抹平单基异质性”），会导致在沪深 300 暴跌但重仓标的逆势抗跌时错误打出 2.0x 追高，或在沪深 300 冲高但重仓标的深幅调整时错误刹车停扣。

---

## 2. 逻辑推导链 (Logic Chain)

### 2.1 Bug 1 修复推导链
- **依据 [1.1]**: `portfolio_manager.py` 的 `evaluate_dynamic_correlation_mutation` 稳定返回 `is_triggered` 和 `is_liquidity_shift_triggered`。
- **依据 [1.1]**: 下游卡片渲染函数 `render_correlation_mutation_card_html` 内部严格依赖 `is_triggered` 与 `is_liquidity_shift_triggered`。
- **推导**:
  1. `app_gui.py` 第 2987 行只需将条件改为 `if corr_eval_res.get("is_triggered") or corr_eval_res.get("is_liquidity_shift_triggered"):`，即可瞬间打通断路。
  2. 为实现双向防撞壁防御，在 `portfolio_manager.py` 的返回字典中补充键名别名 `"is_mutation_alarm": is_triggered` 与 `"is_regime_shift_risk": is_liquidity_shift_triggered`，使无论上游调用方使用哪组键名均 100% 安全命中。

### 2.2 Bug 2 修复推导链
- **依据 [1.2]**: `ActiveRiskSentry.inspect_portfolio` 的维度 8 要求 `investor_risk_tier`，维度 9 要求 `fund_quotes`。
- **依据 [1.2]**: `st.session_state` 中常驻有 `active_tier_val`（默认 `"C3"`）；当前实盘持仓每只标的均可通过 `fetch_realtime_fund_quote(code)` 获取实时报价对象 `FundQuote`（字典结构，包含 `name, dwjz, gsz, gszzl, gztime`）。
- **推导**:
  在 `app_gui.py` 调用 `sentry.inspect_portfolio` 前：
  1. 提取当前风险档位：`_cur_tier = st.session_state.get("active_tier_val", "C3")`；
  2. 遍历 `pm_instance.holdings.keys()`，拉取实时估值注入 `_f_quotes` 字典；
  3. 拷贝 `snapshot_dict`，挂载 `_augmented_snapshot["fund_quotes"] = _f_quotes` 与 `_augmented_snapshot["investor_risk_tier"] = _cur_tier`；
  4. 显式调用 `sentry.inspect_portfolio(pm_instance.holdings, _augmented_snapshot, fund_metadata=_f_metas, investor_risk_tier=_cur_tier)`；
  5. 此时维度 8 成功获取风险等级，开始检测权益占比越界；维度 9 成功获取单基 `gszzl`，在单基异动超 2% 或组合波动超 1% 且消耗安全垫时自动发出预警。

### 2.3 Bug 3 修复推导链
- **依据 [1.3]**: 天天基金 `fundgz` 存在季报滞后偏差，而国内场内 ETF / 核心基准指数拥有高频实时行情。
- **依据 [1.3]**: ETF 联接基金的法定与实际持仓约为 95% 目标 ETF + 5% 现金。
- **推导**:
  1. 建立指数与 ETF 联接基金到场内基准的代码映射字典 `INDEX_AND_FEEDER_BENCHMARK_MAP`（涵盖红利低波 512890、中证红利 515080/000922、科创50 588000、芯片 159995、半导体设备 159516、沪深300 510300、中证500 510500、中证1000 560010、白酒 399997/512690、黄金 518880、标普 513500、纳指 513100、国债 000012），并支持基金名称关键字自动识别。
  2. 在 `fetch_realtime_fund_quote` 内部统一调用 `_apply_index_and_feeder_calibration`：
     - 若为联接基金（名称含“联接”或映射表标记），拉取目标基准行情后，按 `calibrated_gszzl = round(bench_change * 0.95, 2)` 校准；
     - 若为纯指数/增强指数基金，按 `calibrated_gszzl = round(bench_change, 2)` 校准；
     - 当与天天基金估算值偏差绝对值超过 0.1% 或天天基金为 0% 时，用校准值覆盖 `gszzl`，更新 `gsz = round(dwjz * (1.0 + gszzl / 100.0), 4)`，并打上 `valuation_corrected: True` 标签。
  3. 在 `calculate_intraday_pnl` 中保持原有计算与返回值结构，确保对 `test_live_rebalance_upgrades.py` 100% 兼容。

### 2.4 Bug 4 修复推导链
- **依据 [1.4]**: 智能定投决策应反映组合整体的加权资产特征。
- **依据 [1.4]**: `SmartExecutionDCAEngine.get_fund_real_volatility_and_bias` 已经能够精准穿透每只单基过去 20 日的自身均线乖离率 `bias_20`。
- **依据 [1.4]**: 每只基金对应的赛道具有各自的历史估值分位数 `val_percentile`（可由 `OpportunityRadarEngine` 提取，若赛道估值分位为 20%，则权益性风险溢价 ERP 分位对应为 $100 - 20 = 80\%$；纯债固收资产则对齐宏观中性 ERP）。
- **推导**:
  1. 在 `SmartExecutionDCAEngine` 中封装独立函数 `compute_portfolio_weighted_bias_and_erp(allocations, snapshot)`：
     - 归一化各标的权重 $w_i = \text{weight}_i / \sum \text{weight}$；
     - 加权单基乖离率：$\text{bias}_{20,\text{weighted}} = \sum w_i \cdot \text{bias}_{20,i}$；
     - 加权单基 ERP 分位：$\text{ERP}_{\text{weighted}} = \sum w_i \cdot \text{ERP}_i$；
  2. 在 `app_gui.py` 调用 `plan_smart_dca` 与 `get_historical_inflection_ruler` 时，传入上述组合加权指标，使定投扣款乘数与历史对照尺真正与建仓标的精准对齐。

---

## 3. 注意事项与边界约束 (Caveats)

1. **测试兼容性约束**:
   - `tests/test_live_rebalance_upgrades.py` 中 `test_calculate_intraday_pnl` 明确校验了 `f_pnl["est_pnl"] == round(h.market_value * (f_pnl["gszzl"] / 100.0) * 0.95, 2)`。修改 `calculate_intraday_pnl` 时严禁变更该乘积形式，以防旧测试失败。
   - `tests/test_g10_correlation_liquidity_and_stress.py` 中静态源码断言了 `safe_markdown_html(render_correlation_mutation_card_html` 和 `evaluate_dynamic_correlation_mutation_instance`。修复 Bug 1 时必须保留该函数名与静态特征。
2. **只读裁判文件绝对保护**:
   - 四大只读裁判文件（`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`）严禁发生任何代码改动。
3. **全局配置隔离**:
   - 严禁修改全局 `c:\Users\deanc\.gemini\GEMINI.md`，所有规则与经验必须严格沉淀于工作区根目录 `GEMINI.md` 与 `PROGRESS_LOG.md`。
4. **行号漂移说明**:
   - 原 Prompt 提及的行号 1480、1281 属于 G8/G9 世代历史版本。经全量扫描核实，在当前 v4.1-G11 版本的 `app_gui.py` 中，实际对应行号分别为第 2987 行（相关性卡片判断）和第 2725 行（`inspect_portfolio` 调用）。实现时必须以最新真实行号为准。

---

## 4. 实施结论与精准代码方案 (Conclusion)

### 4.1 Bug 1 精准代码方案
- **目标文件**: `AGY2_FundAdvisory/app_gui.py` (第 2985 至 2990 行)
- **修改前**:
  ```python
  try:
      corr_eval_res = pm_instance.evaluate_dynamic_correlation_mutation_instance(threshold=0.75, stress_threshold=0.80)
      if corr_eval_res.get("is_mutation_alarm") or corr_eval_res.get("is_regime_shift_risk"):
          safe_markdown_html(render_correlation_mutation_card_html(corr_eval_res))
  except Exception:
      pass
  ```
- **修改后**:
  ```python
  try:
      corr_eval_res = pm_instance.evaluate_dynamic_correlation_mutation_instance(threshold=0.75, stress_threshold=0.80)
      if corr_eval_res.get("is_triggered") or corr_eval_res.get("is_liquidity_shift_triggered") or corr_eval_res.get("is_mutation_alarm") or corr_eval_res.get("is_regime_shift_risk"):
          safe_markdown_html(render_correlation_mutation_card_html(corr_eval_res))
  except Exception:
      pass
  ```
- **双保险增强**: `AGY2_FundAdvisory/portfolio_manager.py` 第 8628 行返回字典中补齐：
  ```python
  "is_triggered": is_triggered,
  "is_liquidity_shift_triggered": is_liquidity_shift_triggered,
  "is_mutation_alarm": is_triggered,
  "is_regime_shift_risk": is_liquidity_shift_triggered,
  ```

---

### 4.2 Bug 2 精准代码方案
- **目标文件**: `AGY2_FundAdvisory/app_gui.py` (第 2718 至 2728 行)
- **修改前**:
  ```python
  sentry = ActiveRiskSentry()
  _f_metas = {}
  for _c in pm_instance.holdings.keys():
      try:
          _f_metas[_c] = DataLoader.get_fund_metadata(_c) or {}
      except Exception:
          _f_metas[_c] = {}
  sentry_rep = sentry.inspect_portfolio(pm_instance.holdings, snapshot_dict, fund_metadata=_f_metas)
  ```
- **修改后**:
  ```python
  sentry = ActiveRiskSentry()
  _cur_tier = str(st.session_state.get("active_tier_val", "C3")).upper()
  _f_metas = {}
  _f_quotes = {}
  for _c in pm_instance.holdings.keys():
      try:
          _f_metas[_c] = DataLoader.get_fund_metadata(_c) or {}
      except Exception:
          _f_metas[_c] = {}
      try:
          _q = fetch_realtime_fund_quote(_c, use_cache=True)
          if _q:
              _f_quotes[_c] = _q
      except Exception:
          pass

  _augmented_snapshot = dict(snapshot_dict) if isinstance(snapshot_dict, dict) else {}
  _augmented_snapshot["fund_quotes"] = _f_quotes
  _augmented_snapshot["investor_risk_tier"] = _cur_tier

  sentry_rep = sentry.inspect_portfolio(
      pm_instance.holdings,
      _augmented_snapshot,
      fund_metadata=_f_metas,
      investor_risk_tier=_cur_tier
  )
  ```

---

### 4.3 Bug 3 精准代码方案
- **目标文件**: `AGY2_FundAdvisory/portfolio_manager.py` (第 2176 至 2240 行)
- **实现方案**:
  扩充基准映射字典并将 `_apply_qdii_valuation_correction` 升级为支持全市场指数基金与 ETF 联接基金的通用校准函数 `_apply_fund_valuation_calibration`（保持原函数名别名向下兼容）：
  ```python
  # 统一指数、ETF 与场外联接底层基准映射表
  INDEX_AND_FEEDER_BENCHMARK_MAP: Dict[str, str] = {
      # 标普 500
      "050025": "sh513500", "001071": "sh513500", "003718": "sh513500", "012860": "sh513500",
      # 纳斯达克 100
      "006075": "sh513100", "017436": "sh513100", "017437": "sh513100",
      # 黄金联接
      "000216": "sh518880", "000217": "sh518880", "002610": "sh518880", "002611": "sh518880",
      # 科创 50
      "011612": "sh588000", "011613": "sh588000",
      # 芯片 / 半导体
      "008888": "sz159995", "012414": "sz159516", "013841": "sz159995",
      # 红利低波 / 中证红利
      "005561": "sh512890", "005562": "sh512890", "100032": "sh515080", "100033": "sh515080",
      # 沪深 300 / 中证 500 / 中证 1000
      "007339": "sh510300", "110020": "sh510300", "001053": "sh510500", "161017": "sh510500",
      "016633": "sh560010", "016634": "sh560010",
      # 白酒
      "161725": "sz399997",
      # 纯债 / 偏债
      "002351": "s_sh000012", "018757": "s_sh000012",
  }
  QDII_BENCHMARK_MAP = INDEX_AND_FEEDER_BENCHMARK_MAP  # 保持旧字典引用向下兼容

  def _apply_fund_valuation_calibration(q: FundQuote) -> FundQuote:
      """
      校准指数基金与场外 ETF 联接基金的盘中实时估值精度：
      优先结合其对应基准指数或场内 ETF 的实时涨跌幅（联接基金乘以 0.95 仓位系数）校准 gszzl，消除季报滞后重仓股带来的估算偏差。
      """
      if q.valuation_corrected:
          return q

      code = q.fund_code
      bench_sym = INDEX_AND_FEEDER_BENCHMARK_MAP.get(code)
      if not bench_sym:
          f_n = q.name
          if "标普500" in f_n: bench_sym = "sh513500"
          elif "纳斯达克" in f_n or "纳指" in f_n: bench_sym = "sh513100"
          elif "黄金" in f_n: bench_sym = "sh518880"
          elif "科创" in f_n: bench_sym = "sh588000"
          elif "芯片" in f_n or "半导体" in f_n: bench_sym = "sz159995"
          elif "红利低波" in f_n: bench_sym = "sh512890"
          elif "红利" in f_n: bench_sym = "sh515080"
          elif "300" in f_n: bench_sym = "sh510300"
          elif "500" in f_n: bench_sym = "sh510500"
          elif "1000" in f_n: bench_sym = "sh560010"
          elif "白酒" in f_n: bench_sym = "sz399997"

      if bench_sym:
          try:
              b_q = fetch_realtime_index_quote(bench_sym, use_cache=True)
              if b_q and "change_pct" in b_q:
                  b_change = float(b_q.get("change_pct", 0.0))
                  is_feeder = "联接" in q.name or "feeder" in q.name.lower()
                  # 联接基金按 0.95 仓位折算；纯指数按 1.0 折算
                  factor = 0.95 if is_feeder else 1.0
                  calibrated_gszzl = round(b_change * factor, 2)
                  # 检验与天天基金季报估算涨跌幅的绝对偏差，若偏差 > 0.1% 或天天基金为0则纠偏
                  if abs(q.gszzl - calibrated_gszzl) > 0.1 or q.gszzl == 0.0:
                      calibrated_gsz = round(q.dwjz * (1.0 + calibrated_gszzl / 100.0), 4) if q.dwjz > 0 else q.gsz
                      calibrated_gztime = f"{q.gztime} (基准校准: {bench_sym} {b_change:+.2f}%)".strip()
                      return FundQuote(
                          name=q.name,
                          dwjz=q.dwjz,
                          gsz=calibrated_gsz,
                          gszzl=calibrated_gszzl,
                          gztime=calibrated_gztime,
                          fund_code=q.fund_code,
                          valuation_corrected=True
                      )
          except Exception:
              pass
      return q

  _apply_qdii_valuation_correction = _apply_fund_valuation_calibration
  ```

---

### 4.4 Bug 4 精准代码方案
- **目标文件 1**: `AGY2_FundAdvisory/advisory_engine.py` (在 `SmartExecutionDCAEngine` 类内新增方法)
  ```python
  @classmethod
  def compute_portfolio_weighted_bias_and_erp(
      cls,
      allocations: List[Dict[str, Any]],
      snapshot: Optional[Dict[str, Any]] = None
  ) -> Tuple[float, float]:
      """
      穿透精算建仓组合加权 20 日均线乖离率 (weighted_bias_20) 与加权风险溢价分位 (weighted_erp_pct)
      """
      snap = snapshot or {}
      macro_erp = float(snap.get("erp_percentile", 78.0))
      c300_bias = float(snap.get("c300_bias_20", snap.get("bias_20", 0.0)))
      if not allocations:
          return macro_erp, c300_bias

      total_w = sum(float(a.get("weight", 0.0)) for a in allocations) or 1.0
      weighted_bias = 0.0
      weighted_erp = 0.0

      for a in allocations:
          w = float(a.get("weight", 0.0)) / total_w
          fc = a.get("code", "")
          fn = a.get("name", "")
          m = cls.get_fund_real_volatility_and_bias(fc, fn)
          f_bias = float(m.get("bias_20", 0.0))
          weighted_bias += w * f_bias

          # 根据赛道属性反推资产 ERP 分位数 (低估资产对应高 ERP)
          # 纯债/黄金/海外对冲保持宏观中性 ERP，权益/行业资产结合自身乖离率调节
          if any(k in fn for k in ["债", "裕祥", "固收", "黄金", "货币"]):
              f_erp = macro_erp
          else:
              # 乖离率越低，表明短期越处于左侧估值击球区，ERP 相应上浮
              f_erp = float(np.clip(macro_erp - f_bias * 1.5, 10.0, 95.0))
          weighted_erp += w * f_erp

      return round(weighted_erp, 2), round(weighted_bias, 2)
  ```
- **目标文件 2**: `AGY2_FundAdvisory/app_gui.py` (第 3886 至 3901 行)
  ```python
  elif "智能定投" in cap_deployment_mode:
      erp_pct, bias_20 = SmartExecutionDCAEngine.compute_portfolio_weighted_bias_and_erp(
          allocations=alloc_list_for_dca,
          snapshot=snapshot
      )
      dca_plan = SmartExecutionDCAEngine.plan_smart_dca(
          total_capital=float(plan_capital),
          allocations=alloc_list_for_dca,
          erp_percentile=erp_pct,
          bias_20=bias_20,
          periods=12
      )
      ruler_dca = StrategyBridge.get_historical_inflection_ruler(
          current_erp=erp_pct,
          current_bias=bias_20,
          total_capital=float(plan_capital)
      )
      safe_markdown_html(render_historical_inflection_ruler_html(ruler_dca))
  ```

---

## 5. 独立验证方法 (Verification Method)

### 5.1 自动化测试回归命令
在实施代码修改后，依次运行以下测试套件以验证 100% 绿灯通过且零退化：
1. **基础设施与反作弊裁判校验**:
   ```powershell
   py -3 -m pytest tests/test_infra.py -v
   ```
2. **核心业务与因子演化闭环测试**:
   ```powershell
   py -3 -m pytest tests/test_adv_final_closure.py tests/test_g3_evolution_loop.py -v
   ```
3. **相关性突变与压力测试专项**:
   ```powershell
   py -3 -m pytest tests/test_g10_correlation_liquidity_and_stress.py -v
   ```
4. **实时行情校准与盘中盈亏计算专项**:
   ```powershell
   py -3 -m pytest AGY2_FundAdvisory/tests/test_live_rebalance_upgrades.py AGY2_FundAdvisory/tests/test_realtime_and_upgrades.py -v
   ```

### 5.2 专项验证用例设计建议
在 `tests/test_g12_circuit_breakers_and_sentry.py` 中补充以下专项断言：
1. **Bug 1 验证**:
   模拟 `evaluate_dynamic_correlation_mutation_instance(simulated_corr=0.82)`，断言返回字典中同时包含 `is_triggered=True`, `is_liquidity_shift_triggered=True`, `is_mutation_alarm=True`, `is_regime_shift_risk=True`；并在 AppTest 环境下断言 `col_sentry` 成功渲染出相关性压力突变预警卡。
2. **Bug 2 验证**:
   构建 C1 保守型账户持仓 80% 权益标的与 013841 高波科技基，调用 `sentry.inspect_portfolio(..., investor_risk_tier="C1", snapshot={"fund_quotes": {...}})`，断言返回 alerts 中包含维度 8（适当性超标）与维度 9（安全垫消耗传导）。
3. **Bug 3 验证**:
   传入 ETF 联接基金（如 `011613` 华夏科创50联接），通过 mock `fetch_realtime_index_quote("sh588000")` 返回 `change_pct = -2.0%`，断言 `fetch_realtime_fund_quote("011613")` 输出 `gszzl == -1.90%`（即 `-2.0 * 0.95`），且 `valuation_corrected == True`。
4. **Bug 4 验证**:
   构建包含科创50 (bias +5%) 与红利低波 (bias -2%) 的 50:50 组合，调用 `compute_portfolio_weighted_bias_and_erp`，断言加权 `bias_20` 为 `+1.5%`，非单一沪深 300 点位。

### 5.3 失效判定条件 (Invalidation Conditions)
- 若修改导致四大只读裁判文件哈希发生变动，直接判定整改违规。
- 若 `test_calculate_intraday_pnl` 报错（95% 系数被二次折减或签名破坏），判定逻辑不兼容。
- 若 `app_gui.py` 在未触发相关性预警时依然渲染了突变卡，判定门禁判断逻辑破坏了常态干净规则。
