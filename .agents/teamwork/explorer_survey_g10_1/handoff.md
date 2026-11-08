# 需求 R2 深入调研报告：相关性压力突变预警与跨资产流动性平移预案

- **调查人员**: Teamwork Explorer (Survey Specialist)
- **调查时间**: 2026-11-08T03:28:00Z
- **目标文件**: `AGY2_FundAdvisory/advisory_engine.py`, `AGY2_FundAdvisory/portfolio_manager.py`
- **关联文件**: `AGY2_FundAdvisory/data_loader.py`, `tests/test_g3_evolution_loop.py`, `tests/test_g9_causal_brinson_and_suitability.py`

---

## 1. Observation (客观观察事实与代码溯源)

### 1.1 现有相关性与协方差测算逻辑与文件分布
在现有代码库中，动态相关性计算集中于 `AGY2_FundAdvisory/portfolio_manager.py`，而 `AGY2_FundAdvisory/advisory_engine.py` 内部仅存在被动调用，尚未实装独立的矩阵计算算子：

- **`AGY2_FundAdvisory/portfolio_manager.py:8329-8367` (`compute_ewma_correlation`)**:
  ```python
  @classmethod
  def compute_ewma_correlation(
      cls,
      series_a: pd.Series,
      series_b: pd.Series,
      decay_factor: float = 0.94
  ) -> pd.Series:
      ...
      alpha = max(1e-4, min(1.0, 1.0 - float(decay_factor)))
      cov_ewma = (ra * rb).ewm(alpha=alpha, adjust=True).mean().values
      var_a = (ra ** 2).ewm(alpha=alpha, adjust=True).mean().values
      var_b = (rb ** 2).ewm(alpha=alpha, adjust=True).mean().values
      denom = np.sqrt(np.maximum(0.0, var_a * var_b))
      corr_ewma = np.divide(cov_ewma, denom, out=np.zeros_like(cov_ewma, dtype=float), where=(denom > 1e-12))
      corr_series = pd.Series(corr_ewma, index=ra.index)
      return corr_series.clip(-1.0, 1.0)
  ```
  - **衰减因子**: $\lambda = 0.94$（对应 $\alpha = 0.06$，遵循 J.P. Morgan RiskMetrics 行业标准）。
  - **异常值过滤**: 第 8354 行 `valid_mask = (ra.abs() <= 0.15) & (rb.abs() <= 0.15)` 过滤除权异常跳空。
  - **无条件计算局限**: 计算公式基于全样本日收益率点积 $ra \cdot rb$，未针对大盘下行区间（Downside Regime）进行样本过滤。

- **`AGY2_FundAdvisory/portfolio_manager.py:8368-8426` (`evaluate_dynamic_correlation_mutation`)**:
  - 第 8372 行：默认阈值为 `threshold: float = 0.75`。
  - 第 8399-8400 行：提取标的固定为红利基准 `div_col`（优先 `H00922`，次选 `H30269`）与沪深300全收益 `bench_col = "H00300"`。
  - 第 8413 行：截取尾部 120 个交易日 `corr_s.tail(120)` 输出为走势字典。
  - 第 8423-8425 行：
    ```python
    current_corr = simulated_corr if simulated_corr is not None else real_corr
    current_corr = round(float(current_corr), 4)
    is_triggered = bool(current_corr >= threshold)
    ```
  - 第 8519-8530 行：状态标记为 `"MUTATION_ALERT"` / `"DECOUPLED_NORMAL"`，报警等级为 `"yellow"`（$\ge 0.75$）或 `"red"`（$\ge 0.85$）。

- **`AGY2_FundAdvisory/advisory_engine.py:1834-1861` (`ActiveRiskSentry.inspect_portfolio` 维度 7)**:
  ```python
  # -------------------------------------------------------------
  # 维度 7: 动态相关性突变防御与组合集中度降级警报 (EWMA 滚动协方差矩阵)
  # -------------------------------------------------------------
  corr_eval = None
  sim_corr_val = kwargs.get("simulated_corr", snapshot.get("simulated_corr"))
  try:
      from portfolio_manager import PortfolioManager
      corr_eval = PortfolioManager.evaluate_dynamic_correlation_mutation(
          holdings=holdings,
          threshold=0.75,
          simulated_corr=sim_corr_val
      )
      if corr_eval and corr_eval.get("is_triggered"):
          alerts.append({
              "level": corr_eval.get("alert_level", "yellow"),
              "dimension": "动态相关性突变",
              "title": corr_eval.get("alert_title"),
              "desc": corr_eval.get("alert_message"),
              "action": "触发组合集中度降级：动态削减重仓敞口，增量平移至纯债固收/黄金对冲压舱石。",
              "action_type": "correlation_mutation_defense",
              "current_correlation": corr_eval.get("current_correlation"),
              "threshold": corr_eval.get("threshold", 0.75),
              "adjusted_weights": corr_eval.get("adjusted_weights"),
              "cut_details": corr_eval.get("cut_details"),
          })
  except Exception:
      corr_eval = None
  ```
  - **观察**: `advisory_engine.py` 内部当前**完全没有** `calculate_dynamic_correlation_matrix` 函数；其维度 7 仅通过 `PortfolioManager.evaluate_dynamic_correlation_mutation` 获取结果并打包为预警。

### 1.2 大盘急跌研判与下行协方差/相关性现状
- **大盘急跌信号现状**:
  - `advisory_engine.py:1812-1823`：防守底线判据 `breakdown_line = float(trigger_lines.get("breakdown_line", snapshot.get("breakdown_line", 4034.0)))`，当 `c300_point < breakdown_line` 时输出跌破防守底线警告。
  - `advisory_engine.py:2003-2012`：盘中异动安全垫传导检测 `intraday_chg_pct < -1.0%` 或 `consumed_cushion_ratio >= 50%`。
  - `data_loader.py:1027-1035`：本地湖仓已具备 14 大赛道全收益序列，包含 `H00300`（大盘）、`H30269`（红利低波）、`H00922`（中证红利）、`STAR50_STITCH`（科创50）、`H00852`（中证1000）、`H11009`（纯债）、`AU9999`（黄金）。
- **下行相关性/协方差（Downside Covariance）缺失**:
  - 当前两模块中均未实现 Ang & Chen (2002) 范式的下行半协方差或下行相关性函数。
  - 现有逻辑仅计算无条件全周期相关性，无法识别“平时各走各的（相关系数 0.35），大盘急跌时泥沙俱下（相关系数跳升至 0.80+）”的非对称风险踩踏。

### 1.3 现有减仓标的筛选逻辑与重大功能漏洞
在 `AGY2_FundAdvisory/portfolio_manager.py:8478-8496`:
```python
cat = cls.classify_fund_asset_class(code, fn)
is_div = cat in ("A股红利低波", "A股红利高股息") or any(k in fn for k in ["红利", "高股息"])
is_cyc = cat in ("核心蓝筹", "中盘均衡", "中小盘成长") or any(k in fn for k in ["白酒", "银行", "煤炭", "周期", "消费", "300", "500"])

if (is_div or is_cyc) and not any(ex in cat for ex in excluded_cats):
    cut_w = round(w * haircut_ratio, 4)
    new_w = round(w - cut_w, 4)
    adjusted_weights[code] = new_w
    total_cut_weight += cut_w
```
- **核心漏洞发现**:
  - `classify_fund_asset_class`（第 5274 行）将半导体、芯片、科创50等标的划分为 `"科技成长进攻"`；
  - 现存判定条件仅为 `if (is_div or is_cyc)`；
  - **`"科技成长进攻"` 既不在 `is_div` 也不在 `is_cyc` 中**！
  - 导致在当前实盘中，若用户持仓包含高估值、高波动的科技基金（如 `011613` 华夏科创50联接C、`008888` 华夏半导体芯片ETF联接A），在突变触发时**竟然完全不被削减**，仅削减了防御性的红利和部分蓝筹周期股！这与需求 R2 明确要求的“**将高估值与高波标的定向减仓，平移至纯债与实物黄金**”存在直接矛盾。

### 1.4 平移资金配置与权重守恒现状
在 `AGY2_FundAdvisory/portfolio_manager.py:8498-8514`:
```python
if total_cut_weight > 0.0:
    bond_code = "002351"
    gold_code = "000216"
    add_bond = round(total_cut_weight * 0.60, 4)
    add_gold = round(total_cut_weight - add_bond, 4)
    adjusted_weights[bond_code] = round(adjusted_weights.get(bond_code, 0.0) + add_bond, 4)
    adjusted_weights[gold_code] = round(adjusted_weights.get(gold_code, 0.0) + add_gold, 4)

# 归一化闭合至 1.000000
tot_adj = sum(adjusted_weights.values())
if tot_adj > 0:
    adjusted_weights = {k: round(v / tot_adj, 6) for k, v in adjusted_weights.items()}
    diff = 1.0 - sum(adjusted_weights.values())
    k0 = list(adjusted_weights.keys())[0]
    adjusted_weights[k0] = round(adjusted_weights[k0] + diff, 6)
```
- **观察**:
  - 资金定向平移标的固定为纯债 `002351`（易方达裕祥回报债券A，分配 60%）与实物黄金 `000216`（华安易富黄金ETF联接A，分配 40%）。
  - 权重重分配后通过残差吸收保证严格 $\sum w_i = 1.000000$。该部分数学结构严密，应予保留并增强。

### 1.5 现有自动化回归测试套件强断言红线
检查 `tests/test_g3_evolution_loop.py:50-109`:
- 第 52 行：未触发时断言 `res_normal["status"] == "DECOUPLED_NORMAL"`。
- 第 60 行：触发时断言 `assert res_mutation["status"] == "MUTATION_ALERT"`（注意：当 `simulated_corr=0.82` 且 `threshold=0.75` 时，测试强校验此字段）。
- 第 105 行：`ActiveRiskSentry` 警报断言 `assert alert["action_type"] == "correlation_mutation_defense"`。
- 第 108 行：`assert "集中度降级" in alert["action"] or "集中度降级" in alert["title"] or "集中度降级" in alert["desc"]`。
- **红线结论**: 任何将状态字粗暴更改为纯 `"LIQUIDITY_SHIFT_TRIGGERED"` 或将 `action_type` 替换而丢失 `"correlation_mutation_defense"` 的行为都会导致现有 59 项测试挂掉。必须保证向后兼容性。

---

## 2. Logic Chain (推理链条与差距分析)

1. **前提一（需求 R2 契约）**:
   - 当大盘指数急跌时，动态测算红利低波与高 Beta 权益板块的下行协方差突变；
   - 若相关系数跳升至 0.80 以上，自动启动跨资产流动性平移预案；
   - 流动性平移预案须将高估值与高波标的定向减仓，平移至纯债与实物黄金联接资产；
   - 升级范围涉及 `advisory_engine.py` 与 `portfolio_manager.py`。

2. **推理步 1（测算引擎升级与资产配对）**:
   - 由 [1.1] 知，当前仅测算 `H00922/H30269` vs `H00300`，且未测算下行半协方差。
   - 红利低波通常以 `H30269` 为代表；高 Beta 权益板块以科创50（`STAR50_STITCH`）或中证1000（`H00852`）为代表。
   - 当大盘急跌（$r_{\text{bench}} < 0$ 或回撤超基线）时，下行相关系数公式定义为：
     $$\rho^- = \frac{\sum_{t \in \mathcal{D}} w_t (r_{\text{div}, t} - \mu_{\text{div}})(r_{\text{beta}, t} - \mu_{\text{beta}})}{\sqrt{\left(\sum_{t \in \mathcal{D}} w_t (r_{\text{div}, t} - \mu_{\text{div}})^2\right)\left(\sum_{t \in \mathcal{D}} w_t (r_{\text{beta}, t} - \mu_{\text{beta}})^2\right)}}$$
     其中 $\mathcal{D} = \{ t \mid r_{\text{bench}, t} < 0 \}$，权重 $w_t$ 采用 EWMA 衰减（$\lambda = 0.94$）。
   - 在 `portfolio_manager.py` 的 `compute_ewma_correlation` 中增加 `downside_only: bool = False` 与 `bench_series: Optional[pd.Series] = None` 参数，实现下行半协方差的严格向量化计算。

3. **推理步 2（advisory_engine.py 核心算子缺失弥补）**:
   - 由 [1.1] 知，`advisory_engine.py` 缺乏直接的矩阵计算能力。
   - 应在 `advisory_engine.py` 中实装：
     `OpportunityRadarEngine.calculate_dynamic_correlation_matrix(matrix_df=None, lookback=120, decay_factor=0.94, downside_only=False)`
     或顶级方法 `calculate_downside_correlation_matrix`，以对齐需求契约中“在 advisory_engine.py 与 portfolio_manager.py 中升级相关性压力突变预警机制”的明确规定。

4. **推理步 3（0.80 阈值与双层触发机制设计）**:
   - 现存基线为 0.75（常规集中度预警），R2 引入 0.80 极端下行突变阈值。
   - 建议设计**双阶梯自适应触发模型**：
     - **第一阶梯（$0.75 \le \rho < 0.80$）**: 状态为 `MUTATION_ALERT`，级别 `yellow`，执行常规红利/周期集中度降级；
     - **第二阶梯（$\rho \ge 0.80$ 或大盘急跌且下行相关性超限）**: 状态保留 `MUTATION_ALERT`（向后兼容测试），但升级附加标识 `liquidity_shift_triggered = True`，级别升为 `red`，标题与预案文案升级为“【相关性压力突变】触发跨资产流动性平移预案”，重点启动高估值高波标的定向减仓。

5. **推理步 4（减仓标的精准靶向修复）**:
   - 由 [1.3] 知，当前代码漏掉了 `"科技成长进攻"` 以及高估值/高波动资产。
   - 在 `evaluate_dynamic_correlation_mutation` 的资产扫描循环中，必须引入高估值高波标的识别逻辑：
     - 分类为 `"科技成长进攻"`（科创50、半导体芯片等）；
     - 或通过 `SmartExecutionDCAEngine.get_fund_real_volatility_and_bias` 穿透出的波动率 $\sigma_{20} \ge 0.22$；
     - 或估值分位 $> 70\%$；
     - 结合原有的重仓红利/周期共振资产，一并纳入阶梯削减（削减率 $15\% \sim 35\%$）。

6. **推理步 5（定向平移至纯债 002351 与实物黄金 000216）**:
   - 释放的 `total_cut_weight` 按 60% : 40% 分配给 `002351` 与 `000216`，并执行归一化保证 $\sum w_i = 1.000000$。
   - 调仓方案可无缝对接 `pm.generate_rebalance_plan(target_weights=corr_eval["adjusted_weights"])`，直接生成可落地的执行订单。

---

## 3. Caveats (约束条件与边界说明)

1. **现有测试套件兼容性约束**:
   - `tests/test_g3_evolution_loop.py` 明确对 `res_mutation["status"] == "MUTATION_ALERT"`、`res_normal["status"] == "DECOUPLED_NORMAL"`、`alert["action_type"] == "correlation_mutation_defense"` 进行了硬编码断言。
   - 改造时，返回字典必须维持这些键值不变，仅在 `title`, `desc`, `action` 中注入“流动性平移预案”，并增加拓展字段如 `is_liquidity_shift_triggered`, `downside_correlation` 等。
2. **测试环境与真实数据环境差异**:
   - 在单元测试中，常用 `simulated_corr=0.82` 或 `simulated_corr=0.85` 模拟突变；真实运行时则依赖 `DataLoader().load_total_return_matrix()` 中的 `H30269`、`H00300`、`STAR50_STITCH` 数据。若某列因历史切片数据缺失，代码必须有稳健的安全回退逻辑。
3. **四个只读裁判文件绝对零修改**:
   - `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py` 不可触碰。

---

## 4. Conclusion (调查结论与具体实施方案)

### 4.1 数据结构升级定义
`PortfolioManager.evaluate_dynamic_correlation_mutation` 返回字典格式应扩展如下：
```python
{
    "is_triggered": bool,                   # 是否突破 threshold (>=0.75 或 >=0.80)
    "is_liquidity_shift_triggered": bool,   # 当 current_corr >= 0.80 时为 True
    "current_correlation": float,          # 当前相关系数 (如 0.82)
    "downside_correlation": float,         # 大盘下行区间的下行相关系数
    "threshold": float,                    # 触发阈值 (0.75 或 0.80)
    "stress_threshold": 0.80,              # 流动性平移硬阈值
    "status": "MUTATION_ALERT",            # 保持测试向后兼容
    "alert_level": "red" if current_corr >= 0.80 else ("yellow" if is_triggered else "green"),
    "original_weights": Dict[str, float],
    "adjusted_weights": Dict[str, float],  # 满足 sum == 1.000000
    "cut_details": List[Dict[str, Any]],   # 包含高估值、高波科技、红利等标的的减仓明细
    "total_cut_weight_pct": float,
    "historical_correlation_tail": Dict[str, float],
    "alert_title": str,                    # 包含"相关性压力突变"与"集中度降级"
    "alert_message": str,
    "action_plan": "LIQUIDITY_SHIFT_TO_BOND_AND_GOLD"
}
```

### 4.2 具体代码落点与修改建议

#### 落点 1：`AGY2_FundAdvisory/portfolio_manager.py:8329-8367`
- **函数**: `PortfolioManager.compute_ewma_correlation`
- **改造内容**:
  - 增加入参 `downside_only: bool = False`, `bench_series: Optional[pd.Series] = None`。
  - 若 `downside_only=True` 且提供了 `bench_series`：
    对齐日期后，构造 `down_mask = (r_bench < 0.0)`（或 $r_A < 0 \land r_B < 0$）；
    仅在 `down_mask` 的有效子序列上计算 EWMA 协方差与方差，提取下行相关系数序列。

#### 落点 2：`AGY2_FundAdvisory/portfolio_manager.py:8368-8532`
- **函数**: `PortfolioManager.evaluate_dynamic_correlation_mutation`
- **改造内容**:
  - 增加入参 `stress_threshold: float = 0.80`, `market_snapshot: Optional[Dict[str, Any]] = None`。
  - 从 `df_mat` 中提取 `high_beta_col = "STAR50_STITCH"`（科创50）或 `"H00852"`（中证1000），与 `div_col = "H30269"` 进行配对，计算两者的下行 EWMA 相关系数。
  - 判断大盘急跌状态：从 `market_snapshot` 检查 `c300_point < breakdown_line` 或基准日收益 $< -1.0\%$。
  - 当 `current_corr >= 0.80` 或（大盘急跌且下行相关系数 $\ge 0.80$）时，激活流动性平移预案：
    - **修改减仓筛选逻辑**（原 8482 行）：
      将 `cat == "科技成长进攻"`、波动率 $\ge 0.22$ 的高波科技标的，与原有的重仓红利/周期资产共同纳入削减池；
      对科技高波资产执行 $20\% \sim 35\%$ 的定向降级削减。
    - **资金定向平移**（原 8498-8506 行）：
      释放资金定向平移至纯债 `002351`（60%）与黄金 `000216`（40%）。
    - **权重守恒**：
      保持现有的浮点数精确归一化逻辑，确保 $\sum w_i = 1.000000$。

#### 落点 3：`AGY2_FundAdvisory/advisory_engine.py`
- **新增函数**: `OpportunityRadarEngine.calculate_dynamic_correlation_matrix`
  - 入参: `window_days: int = 120, decay_factor: float = 0.94, downside_only: bool = False`
  - 提取本地对齐矩阵中 14 大赛道（或核心对冲与进攻赛道），按交易日对齐，调用下行 EWMA 协方差算法，输出跨板块动态相关性矩阵字典。
- **修改函数**: `ActiveRiskSentry.inspect_portfolio:1834-1861` (维度 7)
  - 传入 `market_snapshot=snapshot` 与 `threshold=0.75` / `stress_threshold=0.80`。
  - 当 `corr_eval.get("current_correlation", 0.0) >= 0.80` 或 `corr_eval.get("is_liquidity_shift_triggered")` 时：
    - 警报标题明确标注 `【相关性压力突变】红利低波与高Beta权益相关系数达 X.XX (突破 0.80 警戒线)`；
    - 警报动作标注 `启动跨资产流动性平移预案与集中度降级：定向削减高估值与高波标的，平移至纯债 (002351) 与实物黄金 (000216)。`；
    - 警报动作类型保持 `action_type = "correlation_mutation_defense"`（保持原有测试兼容），并携带 `is_liquidity_shift_triggered = True`。

---

## 5. Verification Method (独立核验方法与测试设计)

### 5.1 自动化测试专项用例设计
后续实现完成后，可在 `tests/test_g10_correlation_and_liquidity.py` 中编写以下两组核心测试用例进行独立验证：

1. **下行协方差与 0.80 阈值触发测试**:
   ```python
   def test_stress_downside_correlation_and_080_liquidity_shift():
       pm = PortfolioManager(db_path=":memory:")
       pm.add_or_update_holding("005561", shares=30000, nav=1.5, fund_name="创金合信红利低波A") # 45,000
       pm.add_or_update_holding("011613", shares=20000, nav=1.5, fund_name="华夏科创50联接C") # 30,000 (高波科技)
       pm.add_or_update_holding("002351", shares=15000, nav=1.0, fund_name="易方达裕祥回报债券A") # 15,000
       
       # 模拟相关系数突破 0.80 (0.83)
       res = pm.evaluate_dynamic_correlation_mutation_instance(
           threshold=0.75,
           stress_threshold=0.80,
           simulated_corr=0.83
       )
       assert res["is_triggered"] is True
       assert res["current_correlation"] == 0.83
       assert res["is_liquidity_shift_triggered"] is True
       assert res["alert_level"] == "red"
       
       # 验证高波科技 011613 被定向削减
       adj_w = res["adjusted_weights"]
       orig_w = res["original_weights"]
       assert adj_w["011613"] < orig_w["011613"], "高波科技 011613 必须被定向削减！"
       assert adj_w["005561"] < orig_w["005561"], "红利低波共振标的必须被削减！"
       
       # 验证平移至纯债与黄金
       assert adj_w["002351"] > orig_w["002351"], "纯债 002351 必须吸收削减释放资金！"
       assert "000216" in adj_w and adj_w["000216"] > 0, "黄金 000216 必须吸收平移资金！"
       
       # 权重严格守恒
       assert abs(sum(adj_w.values()) - 1.0) < 1e-5
   ```

2. **ActiveRiskSentry 维度 7 闭环预警测试**:
   ```python
   def test_sentry_dimension_7_liquidity_shift_alert():
       sentry = ActiveRiskSentry(watchdog_path="data/test_watchdog.json")
       holdings = [
           {"code": "005561", "name": "创金合信红利低波A", "market_value": 40000.0, "category": "红利低波"},
           {"code": "011613", "name": "华夏科创50联接C", "market_value": 40000.0, "category": "科技成长"},
           {"code": "002351", "name": "易方达裕祥回报纯债A", "market_value": 20000.0, "category": "纯债固收"},
       ]
       snapshot = {"simulated_corr": 0.84, "c300_point": 3950.0, "breakdown_line": 4034.0}
       rep = sentry.inspect_portfolio(holdings, market_snapshot=snapshot)
       
       dim7 = [a for a in rep["alerts"] if a.get("dimension") == "动态相关性突变"]
       assert len(dim7) >= 1
       alert = dim7[0]
       assert alert["level"] == "red"
       assert "流动性平移预案" in alert["action"] or "流动性平移预案" in alert["title"]
       assert "集中度降级" in alert["action"] or "集中度降级" in alert["title"]
       assert alert["action_type"] == "correlation_mutation_defense"
   ```

### 5.2 全量回归验证命令
在实施代码变更后，在根目录执行以下测试以确保零回归：
```powershell
py -3 -m pytest tests/test_g3_evolution_loop.py -v
py -3 -m pytest tests/test_g9_causal_brinson_and_suitability.py -v
py -3 -m pytest tests/test_infra.py -v
py -3 -m pytest tests/test_adv_final_closure.py -v
```

### 5.3 失效判定条件 (Invalidation Conditions)
- 若 `test_g3_evolution_loop.py` 报错 `AssertionError: 'MUTATION_ALERT' != ...` 或缺少 `"集中度降级"` 关键字，表明向后兼容破坏；
- 若测试输入高波科技标的（如 `011613`）但 `adjusted_weights["011613"] == original_weights["011613"]`，表明高估值高波削减仍存在漏洞；
- 若权重和 $\sum w_i \ne 1.000000$（误差 $\ge 1e-5$），表明归一化残差未闭合。
