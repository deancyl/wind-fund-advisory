# Milestone 1 投顾引擎与风控门禁调查报告 (Features 1, 2, 3, 4)

## 1. Observation (法证级直接观察)

### 1.1 文件与代码现状审查

#### 观察项 1: 维度 6 产业估值存在恒真假逻辑
- **文件路径**: `AGY2_FundAdvisory/advisory_engine.py` (第 4294–4300 行)
- **代码原文**:
  ```python
  # 6. 产业估值
  n_radar = len(radar_top3) if radar_top3 else 3
  d6_score = 80.0 if n_radar >= 2 else 55.0
  d6_vote = "BULL" if n_radar >= 2 else "NEUTRAL"
  d6_delta = 5.0 if n_radar >= 2 else 0.0
  d6_reason = "高股息红利与硬科技双轮驱动，精选低估值高票息产业底仓"
  ```
- **法证事实**: 
  - 当外部未传入 `radar_top3` 时，三元表达式直接回退为常数 `3`；当外部传入 `radar_top3` 时，默认包含 3 项。
  - `n_radar >= 2` 恒为 `True`，导致评分恒定为 80.0 分、多头投票恒定为 `BULL`、仓位加成恒定为 `+5.0%`。
  - 没有任何代码读取赛道真实估值分位（`val_percentile`），亦未计算前 3 大机会赛道平均估值分位或全市场估值中位数。

#### 观察项 2: 维度 7 资金情绪缺失真实成交额、上涨家数与 14 赛道拥挤度
- **文件路径**: `AGY2_FundAdvisory/advisory_engine.py` (第 4204–4205 行，第 4301–4312 行)
- **代码原文**:
  ```python
  crowd_score = float(snap.get("crowding_score", 85.0))
  has_exhaustion = bool(snap.get("momentum_exhaustion_warning", False))
  ...
  # 7. 资金情绪
  if crowd_score >= 70.0 and not has_exhaustion:
      d7_score = 75.0
      d7_vote = "BULL"
      d7_delta = 0.0
      d7_reason = f"市场拥挤度评分 {crowd_score:.1f}，动量健康未见泡沫衰竭"
  else:
      d7_score = 40.0
      d7_vote = "BEAR"
      d7_delta = -5.0
      d7_reason = "局部赛道情绪出现过热脉冲或量价动量衰竭预警"
  ```
- **法证事实**:
  - `snap` 字典中通常未注入 `crowding_score`，导致 `crowd_score` 永远取兜底值 `85.0`。
  - 判为 `BULL` 时仓位加成为 `0.0%`，不符合用户要求的“多方并上调 2% 仓位”。
  - 未接入 `DataLoader.fetch_market_turnover_and_sentiment` 提供的两市真实成交额（`turnover_str` 如 16,763 亿）与上涨家数占比（`up_pct` 如 64.5%）。
  - 未计算 14 大赛道的真实平均拥挤度。

#### 观察项 3: 维度 10 期权与避险未接入真实期权隐波与期指贴水
- **文件路径**: `AGY2_FundAdvisory/advisory_engine.py` (第 4353–4365 行)
- **代码原文**:
  ```python
  # 10. 期权与黑天鹅
  has_corr_warning = any("相关性" in a.get("title", "") or a.get("dimension") == "动态相关性突变" for a in alerts)
  if not has_corr_warning:
      d10_score = 80.0
      d10_vote = "BULL"
      d10_delta = 0.0
      d10_reason = "期权隐含波动率平稳，未见系统性相关性突变与黑天鹅尾部冲击"
  else:
      d10_score = 35.0
      d10_vote = "BEAR"
      d10_delta = -5.0
      d10_reason = "触发资产动态相关性突变预警，实施防守平移削减"
  ```
- **法证事实**:
  - 代码中完全未读取 `option_iv_pct` 或 `ic_annualized_basis_rate`。
  - 只要没有 `has_corr_warning`，就盲目投 `BULL`（且 `delta = 0.0`），无视真实期权隐波是否超过 28% 或处于 22%~28% 中性区间。
  - 判定为 `BEAR` 时下调仓位仅为 `-5.0%`，未达到紧急避险要求的 `-8.0%`。

#### 观察项 4: 十维汇总处缺少黑天鹅/灰犀牛一票否决熔断门禁
- **文件路径**: `AGY2_FundAdvisory/advisory_engine.py` (第 4384–4420 行)
- **法证事实**:
  - `compute_ten_dimension_votes` 汇总各维度 `delta_pct` 时为无条件简单加总：`tot_delta = sum(d["delta_pct"] for d in dimensions)`。
  - 当 `ivix >= 32.0`（如极端恐慌 35.0）、`dyn_corr >= 0.80`（如全市场资产同向踩踏）、`usdcnh_chg > 0.60%`（如汇率单日断崖贬值）时，系统未实施一票否决，仍允许 ERP（+10%）等低估加仓项生效，存在严重风控穿透缺陷。
  - 返回结果中无 `circuit_breaker_triggered` 标记与熔断因果说明。

### 1.2 数据源结构与真实快照测试法证

通过在工作区执行测试脚本得到的直接数据事实：
1. **14 大赛道真实湖仓/缓存**:
   - 文件: `data/cache/radar_sectors_cache.json` 存在且包含 14 个完整赛道。
   - 读取方法: `OpportunityRadarEngine.get_cached_sectors_fast()` 耗时 < 1ms，包含 14 个赛道对象。
   - 字段: 每个赛道均具有 `val_percentile`（真实估值分位数，如银行 45.7、白酒 37.6、纯债 40.0、半导体 10.1、科创50 5.1）与 `crowding_score`（真实拥挤度，如 94.2、93.3、89.5）。
   - 当前全市场 14 赛道估值中位数: `50.45%`；平均拥挤度: `93.48`。
2. **两市总成交额与情绪宽度**:
   - 调用 `DataLoader.fetch_market_turnover_and_sentiment()` 返回字典：
     - `total_turnover`: `16762.79` (float)
     - `turnover_str`: `"16,763 亿"` (str)
     - `up_pct`: `64.5` (float)
     - `up_count`: `3415`, `down_count`: `1676`
3. **衍生品指标**:
   - `StrategyBridge.get_latest_market_snapshot()` 包含:
     - `option_iv_pct`: `19.4` (float)
     - `ivix_index`: `19.5` (float)
     - `ic_annualized_basis_rate`: `17.84` (float)
     - `dynamic_correlation`: 默认基线 0.35

### 1.3 调用方接口兼容性法证
- `advisory_engine.py` 内 `generate_chief_advisor_memo`:
  ```python
  ten_dim_votes = compute_ten_dimension_votes(
      snapshot=snap,
      macro_multi=macro_multi,
      radar_top3=radar_top3,
      sentry_rep=sentry_rep,
      **kwargs
  )
  ```
- `portfolio_optimizer.py` (第 854 行):
  ```python
  tdv = compute_ten_dimension_votes(snapshot=self.market_snapshot, tier=self.tier)
  ```
- `tests/test_g17_advisory_real_data_and_ten_dimension.py` (第 82 行):
  ```python
  votes_result = compute_ten_dimension_votes(snapshot)
  ```
  该测试严格断言：返回字典中含有 `dimensions`（长度为 10）、`dimension_details`（10 项，包含 `score`, `vote`, `delta_pct`, `causal_reason`）、`causal_formula`、`bull_count + bear_count + neutral_count == 10`、`round(sugg_eq + sugg_fix, 4) == 1.0000`、`round(sugg_eq, 2) == round(0.60 + tilt, 2)`。

---

## 2. Logic Chain (从观察到重构方案的推导逻辑链)

### 逻辑推导 1: 维度 6 产业估值真数据驱动
1. 基于观察项 1，`len(radar_top3) >= 2` 恒真，必须彻底废弃。
2. 依据用户需求，必须获取全市场 14 大赛道的真实估值分位数列表，并提取前三大机会赛道。
3. 获取路径:
   - 优先从 `kwargs.get("all_sectors")` 获取；若无，调用 `OpportunityRadarEngine.get_cached_sectors_fast()`；若缓存失效，实例化 `OpportunityRadarEngine().scan_all_sectors()`。
   - 若传入了 `radar_top3`，前三大赛道取 `radar_top3[:3]`；否则取 `all_sectors[:3]`。
4. 计算指标:
   - `top3_val_avg = np.mean([s["val_percentile"] for s in top3])`
   - `market_val_median = np.median([s["val_percentile"] for s in all_sectors])`
5. 决策规则:
   - 若 `top3_val_avg <= 35.0`: `d6_vote = "BULL"`, `d6_delta = 5.0`, `d6_score = 85.0`，原因报出 `top3_val_avg` 与 `market_val_median`。
   - 否则若 `market_val_median > 70.0`: `d6_vote = "BEAR"`, `d6_delta = -5.0`, `d6_score = 40.0`，原因报出全市场高估中位数。
   - 其余情况: `d6_vote = "NEUTRAL"`, `d6_delta = 0.0`, `d6_score = 65.0`，原因报出两数值并定性中枢合理。

### 逻辑推导 2: 维度 7 资金情绪多维融合
1. 基于观察项 2，原逻辑取不存在字段导致默认 85.0 分，多头仓位加成为 0.0%，且未融入成交额与宽度。
2. 数据获取:
   - 14 赛道平均拥挤度: `avg_crowd = np.mean([s.get("crowding_score", s.get("s_crowd", 85.0)) for s in all_sectors])`。
   - 两市真实成交额与多方占比: 优先从 `snap` 读取，缺失时调用 `DataLoader.fetch_market_turnover_and_sentiment()`，得到 `turnover_str` 与 `up_pct`。
   - 动量衰竭预警: `has_exhaustion = bool(snap.get("momentum_exhaustion_warning", False))`。
   - 过热判定: `is_overheated = has_exhaustion or (up_pct >= 85.0) or (bias_20 > 6.0)`。
3. 决策规则:
   - 若 `avg_crowd < 55.0 or has_exhaustion`: `d7_vote = "BEAR"`, `d7_delta = -5.0`, `d7_score = 40.0`。
   - 否则若 `avg_crowd >= 72.0 and not is_overheated`: `d7_vote = "BULL"`, `d7_delta = 2.0`, `d7_score = 80.0`。
   - 其余情况: `d7_vote = "NEUTRAL"`, `d7_delta = 0.0`, `d7_score = 65.0`。
   - 原因中显式格式化真实 `avg_crowd`、`up_pct` 与 `turnover_str`。

### 逻辑推导 3: 维度 10 期权衍生品与避险
1. 基于观察项 3，原代码完全缺失 `option_iv_pct` 与 `ic_annualized_basis_rate` 判定。
2. 数据获取:
   - `option_iv = float(snap.get("option_iv_pct") or snap.get("option_iv") or snap.get("ivix_index", 19.40))`
   - `ic_basis = float(snap.get("ic_annualized_basis_rate") or snap.get("ic_basis", 17.84))`
   - 动态相关性预警: `has_corr_warning = any("相关性" in str(a.get("title", "")) or a.get("dimension") == "动态相关性突变" or "相关性突变" in str(a.get("message", "")) for a in alerts) or (float(snap.get("dynamic_correlation", snap.get("dyn_corr", 0.35))) >= 0.75)`
   - 贴水安全垫: `has_basis_cushion = (ic_basis >= 8.0)`（贴水率年化 >= 8.0% 提供安全垫）。
3. 决策规则:
   - 若 `option_iv > 28.0 or has_corr_warning`: 强制 `d10_vote = "BEAR"`, `d10_delta = -8.0`, `d10_score = 30.0`。
   - 否则若 `option_iv < 22.0 and has_basis_cushion and not has_corr_warning`: `d10_vote = "BULL"`, `d10_delta = 2.0`, `d10_score = 80.0`。
   - 其余情况: `d10_vote = "NEUTRAL"`, `d10_delta = 0.0`, `d10_score = 65.0`。
   - 原因中显式报出 `option_iv` 与 `ic_basis`。

### 逻辑推导 4: 黑天鹅/灰犀牛一票否决熔断门禁
1. 基于观察项 4，必须在十维汇总处实施硬风控熔断，防止极端风险下的虚假做多。
2. 触发条件定义:
   - `ivix = float(snap.get("ivix_index") or snap.get("ivix") or snap.get("option_iv_pct", 19.5))`
   - `dyn_corr = float(snap.get("dynamic_correlation") or snap.get("dyn_corr", 0.35))`
   - `eff_usdcnh_chg = usdcnh_chg if abs(usdcnh_chg) > 0.1 else usdcnh_chg * 100.0`
   - 触发判断: `ivix >= 32.0` 或 `dyn_corr >= 0.80` 或 `eff_usdcnh_chg > 0.60`
3. 熔断执行效应:
   - 遍历 `dimensions` 中所有项：凡 `d["delta_pct"] > 0` 的加仓项，物理冻结为 `d["delta_pct"] = 0.0`，并在 `d["reason"]` 追加 `【🚨 触发极值风控熔断，加仓项物理冻结】`。
   - 重新计算 `tot_delta`（此时只有负数减仓项或 0，无任何正向加仓）。
   - 目标权益仓位 `target_equity` 被封顶在 `base_equity` 之内。
   - `causal_formula` 中追加熔断警告文案。
   - 返回字典新增字段：`circuit_breaker_triggered = True`，`circuit_breaker_reason = ...`，`circuit_breaker_triggers = [...]`。
   - `summary["verdict"]` 标记为 `🚨 极值熔断防御`。

---

## 3. Caveats (约束与边界条件)

1. **离线与无网边界**: 当无网络连接且东财接口无法连通时，`DataLoader.fetch_market_turnover_and_sentiment` 依赖 `data/cache/market_breadth.json` 本地缓存，该缓存已在湖仓中持久化（16,763 亿，64.5% 上涨），能平滑离线穿透。
2. **只读裁判安全底线**:
   - 绝对严禁修改 `judge_engine.py`、`holdout_vault.py`、`AGENT_SPEC.md`、`tests/test_infra.py`。
   - 绝对严禁修改 `DataLoader.simulate_execution` 的默认函数签名与扣费逻辑。
3. **接口契约向下兼容**:
   - `compute_ten_dimension_votes` 的所有既有返回字段（`dimensions`, `dimension_details`, `bull_count`, `bear_count`, `neutral_count`, `summary`, `causal_formula`, `target_equity_pct`, `target_defensive_pct`, `equity_tilt_pct`, `suggested_equity_ratio`, `suggested_fixed_ratio`）必须 100% 保留且类型量纲一致，供 `test_g17_advisory_real_data_and_ten_dimension.py` 及 `portfolio_optimizer.py` 无缝消费。

---

## 4. Conclusion (具体落地改造方案与 Worker 施工代码建议)

建议 Worker 在 `AGY2_FundAdvisory/advisory_engine.py` 中对 `compute_ten_dimension_votes` 进行如下精准重构：

### 4.1 核心代码实现建议 (精准替换 `compute_ten_dimension_votes`)

```python
def compute_ten_dimension_votes(
    snapshot: Optional[Dict[str, Any]] = None,
    macro_multi: Optional[Dict[str, Any]] = None,
    radar_top3: Optional[List[Dict[str, Any]]] = None,
    sentry_rep: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    【十维全息投顾量化投票模型与仓位因果传导算子】
    显式输出 10 个维度的量化评分、多空投票裁决、因果逻辑与仓位增减项：
    ① 宏观经济 (cgb_10y)
    ② 货币政策 (dr007, dr007_bp)
    ③ 股债ERP (erp_percentile, erp_val)
    ④ 国际联动 (us_yield_10y, cgb_us_spread_bp)
    ⑤ 外汇锁汇 (usdcnh_rate, usdcnh_chg)
    ⑥ 产业估值 (14赛道真估值分位、前3大机会均值与全市场中位数)
    ⑦ 资金情绪 (两市成交额、多方上涨占比、14赛道平均拥挤度)
    ⑧ 技术信噪比 (bias_20, er_snr)
    ⑨ 历史同温层 (inflection_point_ruler)
    ⑩ 期权与黑天鹅 (option_iv_pct, ic_annualized_basis_rate, 动态相关性)
    """
    snap = snapshot or {}
    mm = macro_multi or {}
    alerts = sentry_rep.get("alerts", []) if sentry_rep else []

    cgb_10y = float(mm.get("cgb_10y_yield") or snap.get("cgb_10y_yield") or snap.get("treasury_10y", 1.6376))
    dr007 = float(snap.get("dr007", 1.389))
    dr007_bp = float(snap.get("dr007_spread_bp", -11.1))
    erp_pct = float(snap.get("erp_percentile", 82.6))
    erp_val = float(snap.get("erp_val", 6.55))
    us_10y = float(mm.get("us_10y_yield") or mm.get("us_treasury_10y") or snap.get("us_treasury_10y", 4.4200))
    spread_bp = float(mm.get("cgb_us_spread_bp") or snap.get("cn_us_spread_bp") or round((cgb_10y - us_10y) * 100.0, 1))
    usdcnh_rate = float(mm.get("usdcnh_rate") or snap.get("spot_usdcnh", 7.2385))
    raw_usdcnh_chg = float(mm.get("change_pct") or mm.get("usdcnh_change_pct") or snap.get("usdcnh_change_pct", -0.0225))
    usdcnh_chg = raw_usdcnh_chg if abs(raw_usdcnh_chg) > 0.05 else (raw_usdcnh_chg * 100.0)
    has_exhaustion = bool(snap.get("momentum_exhaustion_warning", False))
    bias_20 = float(snap.get("bias_20", -1.58))
    er_snr = float(snap.get("er_snr", 0.35))

    # 1. 宏观经济
    if cgb_10y <= 1.80:
        d1_score = 85.0; d1_vote = "BULL"; d1_delta = 3.0
        d1_reason = f"10Y国债 {cgb_10y:.2f}% 处于极低水位，无风险利率下行托底资产估值"
    elif cgb_10y <= 2.30:
        d1_score = 70.0; d1_vote = "NEUTRAL"; d1_delta = 0.0
        d1_reason = f"10Y国债 {cgb_10y:.2f}% 处于合理常态中枢，宏观预期平稳"
    else:
        d1_score = 45.0; d1_vote = "BEAR"; d1_delta = -3.0
        d1_reason = f"10Y国债 {cgb_10y:.2f}% 利率中枢上行，对权益分母端构成折现压制"

    # 2. 货币政策
    if dr007_bp <= 0.0:
        d2_score = 90.0; d2_vote = "BULL"; d2_delta = 5.0
        d2_reason = f"DR007为 {dr007:.3f}% (利差 {dr007_bp:+.1f}bp)，银行间资金面合理充裕宽松"
    elif dr007_bp <= 25.0:
        d2_score = 65.0; d2_vote = "BULL"; d2_delta = 3.0
        d2_reason = f"资金面处于中性偏松平衡区间 (DR007利差 {dr007_bp:+.1f}bp)"
    else:
        d2_score = 35.0; d2_vote = "BEAR"; d2_delta = -3.0
        d2_reason = f"DR007利差 {dr007_bp:+.1f}bp 边际收紧，流动性摩擦升高"

    # 3. 股债ERP
    if erp_pct >= 75.0:
        d3_score = 95.0; d3_vote = "BULL"; d3_delta = 10.0
        d3_reason = f"沪深300 ERP达 {erp_val:.2f}% (历史分位 {erp_pct:.1f}%)，处于绝对黄金击球区"
    elif erp_pct >= 45.0:
        d3_score = 60.0; d3_vote = "NEUTRAL"; d3_delta = 0.0
        d3_reason = f"股债性价比中性均衡 (ERP分位 {erp_pct:.1f}%)"
    else:
        d3_score = 30.0; d3_vote = "BEAR"; d3_delta = -8.0
        d3_reason = f"ERP分位仅 {erp_pct:.1f}% 偏向高估区，权益性价比收敛"

    # 4. 国际联动
    if spread_bp < -250.0:
        d4_score = 45.0; d4_vote = "BEAR"; d4_delta = -3.0
        d4_reason = f"中美10Y利差倒挂 {spread_bp:+.1f}bp (美债 {us_10y:.2f}%)，海外高息压制外资流动性"
    elif spread_bp >= -150.0:
        d4_score = 70.0; d4_vote = "BULL"; d4_delta = 2.0
        d4_reason = f"中美利差倒挂明显收窄至 {spread_bp:+.1f}bp，外流压力大幅趋缓"
    else:
        d4_score = 55.0; d4_vote = "NEUTRAL"; d4_delta = 0.0
        d4_reason = f"中美利差倒挂 {spread_bp:+.1f}bp，海外市场震荡消化"

    # 5. 外汇锁汇
    if abs(usdcnh_chg) <= 0.25:
        d5_score = 80.0; d5_vote = "BULL"; d5_delta = 2.0
        d5_reason = f"离岸人民币现汇 {usdcnh_rate:.4f} 运行平稳 (日变动 {usdcnh_chg:+.2f}%)，双向波动可控"
    elif usdcnh_chg < -0.25:
        d5_score = 85.0; d5_vote = "BULL"; d5_delta = 3.0
        d5_reason = f"人民币汇率呈现升值态势 ({usdcnh_chg:+.2f}%)，资产吸引力增强"
    else:
        d5_score = 40.0; d5_vote = "BEAR"; d5_delta = -3.0
        d5_reason = f"离岸汇率单日承压变动 {usdcnh_chg:+.2f}%，需警惕资金跨市场流出"

    # ── 6. 产业估值真数据驱动 (全市场 14 赛道穿透) ─────────────────
    all_sectors = kwargs.get("all_sectors") or kwargs.get("sectors")
    if not all_sectors:
        try:
            all_sectors = OpportunityRadarEngine.get_cached_sectors_fast()
        except Exception:
            all_sectors = None
    if not all_sectors:
        try:
            radar_engine = OpportunityRadarEngine()
            all_sectors = radar_engine.scan_all_sectors()
        except Exception:
            all_sectors = []

    # 提取前三大机会赛道
    top3 = radar_top3[:3] if (radar_top3 and len(radar_top3) >= 1) else (all_sectors[:3] if all_sectors else [])
    top3_vals = [float(s.get("val_percentile", 50.0)) for s in top3 if s.get("val_percentile") is not None]
    top3_val_avg = float(np.mean(top3_vals)) if top3_vals else 41.1

    all_vals = [float(s.get("val_percentile", 50.0)) for s in all_sectors if s.get("val_percentile") is not None]
    market_val_median = float(np.median(all_vals)) if all_vals else 50.5

    if top3_val_avg <= 35.0:
        d6_score = 85.0
        d6_vote = "BULL"
        d6_delta = 5.0
        d6_reason = f"前三大机会赛道平均估值分位 {top3_val_avg:.1f}% (<=35%) 处于低估击球区，全市场估值中位数 {market_val_median:.1f}%，具备结构性配置价值"
    elif market_val_median > 70.0:
        d6_score = 40.0
        d6_vote = "BEAR"
        d6_delta = -5.0
        d6_reason = f"全市场估值中位数达 {market_val_median:.1f}% (>70%) 呈现全面高估风险，前三大赛道估值分位 {top3_val_avg:.1f}%，需下调仓位防御"
    else:
        d6_score = 65.0
        d6_vote = "NEUTRAL"
        d6_delta = 0.0
        d6_reason = f"前三大机会赛道平均估值分位 {top3_val_avg:.1f}%，全市场估值中位数 {market_val_median:.1f}%，产业估值处于合理中枢震荡区间"

    # ── 7. 资金情绪多维融合 (两市成交额 + 上涨家数占比 + 14赛道平均拥挤度) ──
    all_crowds = [float(s.get("crowding_score", s.get("s_crowd", 85.0))) for s in all_sectors if (s.get("crowding_score") is not None or s.get("s_crowd") is not None)]
    avg_crowd = float(np.mean(all_crowds)) if all_crowds else float(snap.get("crowding_score", 85.0))

    mb_data = snap.get("market_turnover_sentiment") or snap.get("market_breadth") or kwargs.get("market_breadth")
    if not mb_data:
        try:
            from AGY2_FundAdvisory.data_loader import DataLoader
            mb_data = DataLoader.fetch_market_turnover_and_sentiment(use_cache=True)
        except Exception:
            mb_data = {}
    turnover_str = mb_data.get("turnover_str", "16,763 亿") if mb_data else "16,763 亿"
    up_pct = float(mb_data.get("up_pct", 64.5)) if mb_data else 64.5

    is_overheated = has_exhaustion or (up_pct >= 85.0) or (bias_20 > 6.0)

    if avg_crowd < 55.0 or has_exhaustion:
        d7_score = 40.0
        d7_vote = "BEAR"
        d7_delta = -5.0
        d7_reason = f"14赛道平均拥挤度 {avg_crowd:.1f}分 (<55分) 或触发动量衰竭预警 (两市成交 {turnover_str}，多方占比 {up_pct:.1f}%)，资金情绪退潮承压"
    elif avg_crowd >= 72.0 and not is_overheated:
        d7_score = 80.0
        d7_vote = "BULL"
        d7_delta = 2.0
        d7_reason = f"两市成交额 {turnover_str}，多方占比 {up_pct:.1f}%，14赛道平均拥挤度 {avg_crowd:.1f}分 (>=72分且未过热)，情绪健康做多"
    else:
        d7_score = 65.0
        d7_vote = "NEUTRAL"
        d7_delta = 0.0
        d7_reason = f"两市成交额 {turnover_str}，多方占比 {up_pct:.1f}%，14赛道平均拥挤度 {avg_crowd:.1f}分，情绪中性平衡"

    # 8. 技术信噪比
    if bias_20 > 6.0:
        d8_score = 35.0; d8_vote = "BEAR"; d8_delta = -5.0
        d8_reason = f"沪深300 MA20乖离达 {bias_20:+.1f}% 严重超买，触发均值回归折价约束"
    elif -4.0 <= bias_20 <= 0.0:
        d8_score = 70.0; d8_vote = "NEUTRAL"; d8_delta = 0.0
        d8_reason = f"指数回踩 MA20 良性蓄势 (乖离 {bias_20:+.1f}%)，信噪比 {er_snr:.2f}"
    elif bias_20 > 0.0:
        d8_score = 75.0; d8_vote = "BULL"; d8_delta = 2.0
        d8_reason = f"指数站稳 20日均线上方 (乖离 {bias_20:+.1f}%)，均线多头共振"
    else:
        d8_score = 65.0; d8_vote = "NEUTRAL"; d8_delta = 0.0
        d8_reason = f"均线水下负乖离超卖修复 (乖离 {bias_20:+.1f}%)"

    # 9. 历史同温层
    ruler_mult = float(kwargs.get("ruler_multiplier", 1.76))
    if ruler_mult >= 1.50:
        d9_score = 90.0; d9_vote = "BULL"; d9_delta = 5.0
        d9_reason = f"历史三大拐点对照尺达 {ruler_mult:.2f}x，高度贴近2022/2024底部反转击球区"
    elif ruler_mult >= 0.80:
        d9_score = 65.0; d9_vote = "NEUTRAL"; d9_delta = 0.0
        d9_reason = f"周期对照尺处于 {ruler_mult:.2f}x 正常中枢震荡区间"
    else:
        d9_score = 30.0; d9_vote = "BEAR"; d9_delta = -8.0
        d9_reason = f"周期对照尺仅 {ruler_mult:.2f}x 处于历史顶部狂热区，提示止盈保护"

    # ── 10. 期权与黑天鹅 (接入真实 option_iv_pct、ic_basis 与动态相关性预警) ──
    option_iv = float(snap.get("option_iv_pct") or snap.get("option_iv") or snap.get("ivix_index", 19.40))
    ic_basis = float(snap.get("ic_annualized_basis_rate") or snap.get("ic_basis", 17.84))
    dyn_corr = float(snap.get("dynamic_correlation") or snap.get("dyn_corr", 0.35))
    has_corr_warning = any("相关性" in str(a.get("title", "")) or a.get("dimension") == "动态相关性突变" or "相关性突变" in str(a.get("message", "")) for a in alerts) or (dyn_corr >= 0.75)
    has_basis_cushion = (ic_basis >= 8.0)

    if option_iv > 28.0 or has_corr_warning:
        d10_score = 30.0
        d10_vote = "BEAR"
        d10_delta = -8.0
        d10_reason = f"期权隐波 {option_iv:.1f}% (>28%) 或触发动态相关性突变预警 (IC贴水 {ic_basis:.1f}%)，尾部风险升高紧急避险"
    elif option_iv < 22.0 and has_basis_cushion and not has_corr_warning:
        d10_score = 80.0
        d10_vote = "BULL"
        d10_delta = 2.0
        d10_reason = f"期权隐波 {option_iv:.1f}% 低位平稳 (<22%)，IC年化贴水率 {ic_basis:.1f}% 提供充足安全垫，无相关性突变"
    else:
        d10_score = 65.0
        d10_vote = "NEUTRAL"
        d10_delta = 0.0
        d10_reason = f"期权隐波 {option_iv:.1f}% 处于常态区间，IC年化贴水率 {ic_basis:.1f}%，衍生品定价平稳"

    dimensions = [
        {"dimension_id": 1, "name": "① 宏观经济", "score": d1_score, "vote": d1_vote, "delta_pct": d1_delta, "reason": d1_reason},
        {"dimension_id": 2, "name": "② 货币政策", "score": d2_score, "vote": d2_vote, "delta_pct": d2_delta, "reason": d2_reason},
        {"dimension_id": 3, "name": "③ 股债ERP", "score": d3_score, "vote": d3_vote, "delta_pct": d3_delta, "reason": d3_reason},
        {"dimension_id": 4, "name": "④ 国际联动", "score": d4_score, "vote": d4_vote, "delta_pct": d4_delta, "reason": d4_reason},
        {"dimension_id": 5, "name": "⑤ 外汇锁汇", "score": d5_score, "vote": d5_vote, "delta_pct": d5_delta, "reason": d5_reason},
        {"dimension_id": 6, "name": "⑥ 产业估值", "score": d6_score, "vote": d6_vote, "delta_pct": d6_delta, "reason": d6_reason},
        {"dimension_id": 7, "name": "⑦ 资金情绪", "score": d7_score, "vote": d7_vote, "delta_pct": d7_delta, "reason": d7_reason},
        {"dimension_id": 8, "name": "⑧ 技术信噪比", "score": d8_score, "vote": d8_vote, "delta_pct": d8_delta, "reason": d8_reason},
        {"dimension_id": 9, "name": "⑨ 历史同温层", "score": d9_score, "vote": d9_vote, "delta_pct": d9_delta, "reason": d9_reason},
        {"dimension_id": 10, "name": "⑩ 期权与黑天鹅", "score": d10_score, "vote": d10_vote, "delta_pct": d10_delta, "reason": d10_reason},
    ]

    # ── 门禁与黑天鹅一票否决熔断判断 ──────────────────────────────
    ivix = float(snap.get("ivix_index") or snap.get("ivix") or option_iv)
    cb_triggers = []
    if ivix >= 32.0:
        cb_triggers.append(f"期权隐波IVIX({ivix:.1f}>=32.0)")
    if dyn_corr >= 0.80:
        cb_triggers.append(f"动态相关性({dyn_corr:.2f}>=0.80)")
    if usdcnh_chg > 0.60:
        cb_triggers.append(f"人民币贬值波动({usdcnh_chg:+.2f}%>+0.60%)")

    circuit_breaker_triggered = len(cb_triggers) > 0
    circuit_breaker_reason = " ｜ ".join(cb_triggers)

    if circuit_breaker_triggered:
        # 一票否决：物理冻结所有低估加仓项 (delta_pct > 0 强制归零)
        for d in dimensions:
            if d["delta_pct"] > 0:
                orig_d = d["delta_pct"]
                d["delta_pct"] = 0.0
                d["reason"] += f"【🚨 触发风控熔断({circuit_breaker_reason})，+{orig_d:.0f}%低估加仓项物理冻结】"

    bull_count = sum(1 for d in dimensions if d["vote"] == "BULL")
    bear_count = sum(1 for d in dimensions if d["vote"] == "BEAR")
    neutral_count = sum(1 for d in dimensions if d["vote"] == "NEUTRAL")
    total_score = round(sum(d["score"] for d in dimensions) / len(dimensions), 1)

    # 仓位推导因果传导公式
    tier_u = str(kwargs.get("tier", "C3")).upper()
    tier_base_map = {
        "C1": (20.0, 10.0, 30.0),
        "C2": (40.0, 20.0, 50.0),
        "C3": (60.0, 40.0, 85.0),
        "C4": (75.0, 55.0, 90.0),
        "C5": (85.0, 65.0, 95.0)
    }
    base_equity, min_eq, max_eq = tier_base_map.get(tier_u, (60.0, 20.0, 85.0))
    tot_delta = sum(d["delta_pct"] for d in dimensions)
    raw_target = int(round(base_equity + tot_delta))
    target_equity = int(round(max(min_eq, min(max_eq, raw_target))))
    target_defensive = 100 - target_equity

    # 构造清晰人话因果链
    causal_parts = [f"基准权益中枢 {int(base_equity)}%"]
    for d in dimensions:
        d_del = d["delta_pct"]
        if d_del != 0:
            causal_parts.append(f"{d['name'][2:]}({d_del:+.0f}%)")

    formula_head = " + ".join(causal_parts).replace("+ -", "- ")
    cb_suffix = f" [🚨 触发黑天鹅/灰犀牛一票否决熔断({circuit_breaker_reason})，低估加仓项已全部物理冻结为0%]" if circuit_breaker_triggered else ""
    
    if raw_target > max_eq:
        causal_formula = f"{formula_head} = {raw_target}% -> 触及风控上限锁定，当前建议权益仓位 {target_equity}% (防守固收 {target_defensive}%){cb_suffix}"
    elif raw_target < min_eq:
        causal_formula = f"{formula_head} = {raw_target}% -> 触及风控下限锁定，当前建议权益仓位 {target_equity}% (防守固收 {target_defensive}%){cb_suffix}"
    else:
        causal_formula = f"{formula_head} = 当前建议权益仓位 {target_equity}% (防守固收 {target_defensive}%){cb_suffix}"

    if circuit_breaker_triggered:
        verdict = "🚨 极值熔断防御"
    else:
        verdict = "积极做多" if bull_count >= 6 else ("防守防御" if bear_count >= 5 else "稳健攻防")

    equity_tilt = round((target_equity - base_equity) / 100.0, 4)
    suggested_equity_ratio = round(target_equity / 100.0, 4)
    suggested_fixed_ratio = round(target_defensive / 100.0, 4)

    dim_details_dict = {}
    for d in dimensions:
        dim_key = d.get("name", f"dim_{d.get('dimension_id')}")
        dim_details_dict[dim_key] = {
            "score": float(d.get("score", 0.0)),
            "vote": str(d.get("vote", "NEUTRAL")),
            "delta_pct": float(d.get("delta_pct", 0.0)),
            "causal_reason": str(d.get("reason", "") or d.get("causal_reason", "中性配置")),
            "dimension_id": d.get("dimension_id", 0),
            "name": d.get("name", "")
        }

    return {
        "dimensions": dimensions,
        "dimension_details": dim_details_dict,
        "bull_count": bull_count,
        "bear_count": bear_count,
        "neutral_count": neutral_count,
        "summary": {
            "bull_votes": bull_count,
            "bear_votes": bear_count,
            "neutral_votes": neutral_count,
            "total_score": total_score,
            "verdict": verdict
        },
        "causal_formula": causal_formula,
        "target_equity_pct": target_equity,
        "target_defensive_pct": target_defensive,
        "equity_tilt_pct": equity_tilt,
        "suggested_equity_ratio": suggested_equity_ratio,
        "suggested_fixed_ratio": suggested_fixed_ratio,
        "circuit_breaker_triggered": circuit_breaker_triggered,
        "circuit_breaker_reason": f"🚨 黑天鹅/灰犀牛熔断：{circuit_breaker_reason}" if circuit_breaker_triggered else "",
        "circuit_breaker_triggers": cb_triggers
    }
```

---

## 5. Verification Method (独立可复现验证方法)

### 5.1 自动化测试命令
在工作区根目录下执行以下测试命令：
```powershell
py -3 -m pytest tests/test_g17_advisory_real_data_and_ten_dimension.py -v
```

### 5.2 新增 M1 门禁测试用例建议
Worker 在实现后应创建 `tests/test_g19_m1_ten_dimension_and_circuit_breaker.py`，覆盖以下 4 个场景：
1. **维度 6 估值驱动测试**:
   - 构造 `radar_top3` 平均分位 <= 35%（如半导体 10.1%, 恒生科技 22.5%, 科创50 5.1%），断言第 6 维判定为 `BULL`，`delta_pct == 5.0`，`reason` 包含真实数值。
   - 构造全市场中位数 > 70% 的情景，断言第 6 维判定为 `BEAR`，`delta_pct == -5.0`。
   - 构造中间常态，断言第 6 维判定为 `NEUTRAL`，`delta_pct == 0.0`。
2. **维度 7 资金情绪融合测试**:
   - 构造平均拥挤度 < 55 或 `momentum_exhaustion_warning=True`，断言第 7 维为 `BEAR`，`delta_pct == -5.0`。
   - 构造平均拥挤度 >= 72 且未过热，断言第 7 维为 `BULL`，`delta_pct == 2.0`，`reason` 包含 `turnover_str` 与 `up_pct`。
3. **维度 10 期权衍生品测试**:
   - 构造 `option_iv_pct = 30.5`（> 28%），断言第 10 维为 `BEAR`，`delta_pct == -8.0`。
   - 构造 `option_iv_pct = 19.4`（< 22%）且贴水充足，断言第 10 维为 `BULL`，`delta_pct == 2.0`。
4. **熔断门禁一票否决测试**:
   - 传入 `ivix = 35.0` 或 `dynamic_correlation = 0.85` 或 `usdcnh_change_pct = 0.85`，断言 `circuit_breaker_triggered is True`。
   - 断言所有原本 `> 0` 的加仓项被冻结为 `0.0`，`target_equity_pct <= base_equity`（60%），`causal_formula` 包含熔断标识。

### 5.3 判废条件 (Invalidation Conditions)
- 若第 6 维依然出现 `n_radar >= 2` 或无真实估值分位数。
- 若第 7 维多头投票时仓位增量非 `+2.0%` 或未输出真实成交额与多方占比。
- 若第 10 维空头投票时仓位扣减非 `-8.0%` 或未读取真实 `option_iv_pct`。
- 若在 `ivix >= 32.0` 时低估加仓项仍存在正值增加权益仓位。
- 若修改了任何一个只读神圣文件 (`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`)。
