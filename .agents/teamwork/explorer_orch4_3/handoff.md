# 今日调仓适宜度裁决器、四大后果推演器、双红利协同豁免与红队测试勘测分析报告 (Handoff Report)

- **工作目录**: `d:\Google\Workspace\Wind\.agents\teamwork\explorer_orch4_3`
- **探索者角色**: `explorer_orch4_3 (Suitability and Test Explorer)`
- **服务对象**: Agent-3 (存量持仓调仓裁决与后果推演专家) & Agent-4 (红队反作弊与单元测试员)
- **勘测范围**: `portfolio_manager.py`、`strategy_bridge.py`、`trading_clock_fee.py`、`tests/`

---

## 1. Observation (客观事实与勘测证据链)

### 1.1 系统只读裁判文件与物理安全红线现状
通过对工程根目录及 `tests/` 目录进行只读勘测，确认系统只读裁判文件完整且未被篡改：
1. `AGY2_FundAdvisory/judge_engine.py` (844 行, 42,175 字节)：包含未来函数因果探针 (`probe_look_ahead_bias`)、AST 静态扫描 (`scan_ast_for_calendar_cheating`，严禁策略函数出现 `2018`~`2025` 日历年份字面量)、6 风格切片回归与参数扰动检验。
2. `AGY2_FundAdvisory/holdout_vault.py` (223 行, 8,460 字节)：盲测金库物理隔离与硬上限熔断锁。
3. `AGY2_FundAdvisory/AGENT_SPEC.md` (66 行, 2,900 字节)：架构规约。
4. `AGY2_FundAdvisory/tests/test_infra.py` (264 行, 10,524 字节)：裁判底层基建自动化验证套件。
- **验证结论**：4 个裁判基建文件均完好无损，严格遵守只读安全红线，后续开发严禁触碰或解锁。

### 1.2 `portfolio_manager.py` 重合度矩阵与协同豁免现状
查看 `portfolio_manager.py` 第 3499 ~ 3637 行 `calculate_stock_overlap_matrix()`：
- **现存豁免名单 `EXEMPT_OVERLAP_PAIRS`** (Lines 3539-3559)：
  ```python
  EXEMPT_OVERLAP_PAIRS = {
      frozenset({"050025", "001071"}), # 标普500官方限购拆单伴生组
      frozenset({"011612", "011613"}), # 华夏科创50 A/C 同源份额
      frozenset({"100032", "008682"}), # 富国红利增强 A/C 同源份额
      ...
  }
  ```
  *观察发现*：名单中已包含限购伴生对 `{"050025", "001071"}`，但**缺失策略推荐的标准双红利底仓对 `frozenset({"100032", "005561"})`**（富国中证红利指数增强A 与 创金合信中证红利低波动指数A）。
- **告警触发逻辑** (Lines 3605-3619)：
  当非豁免标的的重合度 `overlap >= 0.40` 时，系统在 `alerts` 中追加高重合度假分散警告（`msg = f"⚠️ 高重合度假分散预警..."`）。由于 `100032` 与 `005561` 均为红利底层资产，前十大重仓股（银行、煤炭、公用事业）重合度常超过 40%，导致用户持有标准推荐组合时触发黄色告警。
- **返回结构** (Lines 3630-3637)：
  当前返回字典为：
  `{"funds": fund_labels, "matrix": matrix, "alerts": alerts, "matrix_notes": matrix_notes, "exempt_pairs": exempt_pairs, "pending_external_funds": pending_external_funds}`。
  *观察发现*：**尚未计算并返回 `max_non_diag_unexcused` 字段**。

### 1.3 `strategy_bridge.py` 调仓适宜度与后果推演现状
在 `strategy_bridge.py` 中进行全文检索：
- `evaluate_today_rebalance_suitability`：**尚未实现**（No results found）。
- `simulate_rebalance_modes_and_consequences`：**尚未实现**（No results found）。
- **已存在的关键可复用量化底座**：
  1. `StrategyBridge.get_latest_market_snapshot(force_reload=False)` (Lines 2355-2771)：
     返回 `bias_20` (沪深300 20日均线偏离度)、`m20_status_desc`、`dist_to_m20_breakout`、`market_state`、`market_state_code`、`erp_percentile`、`dual_track_radar`、`composite_z`、`sigmoid_gate`、`trigger_lines` (`surge_line`, `breakdown_line`)、`dr007`、`liquidity_status`。
  2. `StrategyBridge.generate_ai_rebalance_orders(...)` (Lines 3078-3317)：
     计算权重偏离 `diff_w`、3% 缓冲区过滤、FIFO 批次持有天数安全检查（`holding_days >= 7`）、卖出份额自动裁剪至安全上限、三级路由分配（`PRIORITY_1_SWITCH` / `PRIORITY_2_CASH_ADVANCE` / `PRIORITY_3_TWO_STEP` / `SELL_TO_CASH` / `NO_ACTION`）。
  3. `StrategyBridge.estimate_rebalance_impact(...)` (Lines 4719-4815)：
     已有初版实盘影响测算逻辑，计算了 `vol_before`, `vol_after`, `vol_diff`, `div_before`, `div_after`, `div_diff`, `total_fee`, `payback_days`。
  4. `PortfolioManager.calculate_rebalance_net_utility(...)` (Lines 4960-5080)：
     已实现单笔调仓预期净效用 $\Delta U$：
     $$\Delta U = \text{AlphaGain}_{20d} - \text{ExactRedemptionFee} - \text{SubscriptionFee} - \text{InTransitCost}$$
     明确了同公司 SWITCH 踏空天数 $\Delta t = 0$，跨公司境内 $T+2$、境外 $T+4$，折算波动率踏空成本。
  5. `TradingClock.get_market_window_status(now)` (`trading_clock_fee.py` Lines 106-220)：
     输出 `MarketWindowStatus`，包含 `window_type` (`CLOSED_PREMARKET` / `OBSERVATION` / `GOLDEN_WINDOW` / `CRITICAL_CLOSING` / `POST_MARKET_DELAYED` / `NON_TRADING_DAY`)、`title`、`message`、`is_trade_day`、`is_golden_window`、`is_after_market`、`seconds_to_close`。

### 1.4 测试运行环境与套件执行证据
- 测试运行解释器：`py -3.11 -m pytest`
- 运行针对 `portfolio_manager.py` 的测试验证：
  `py -3.11 -m pytest tests/test_portfolio_manager.py` 耗时 39.26 秒，22 passed, 100% 成功。
- 全量测试套件现有约 540 项测试用例，覆盖宏观数据加载、裁判引擎因果验证、四岛模型、交易时钟与组合接管。

---

## 2. Logic Chain (推理与量化计算推演)

### 2.1 `evaluate_today_rebalance_suitability` 接口契约与量化判定逻辑
- **方法签名**:
  `StrategyBridge.evaluate_today_rebalance_suitability(pm, active_tier: str = "C3") -> Dict[str, Any]`

- **四维状态提取与白话解析字典 `reasons_4d` 逻辑链**:
  1. `market_position_reason` (近期行情位置诊断):
     - 数据来源: `snapshot = StrategyBridge.get_latest_market_snapshot()`
     - 提取字段: `bias_20 = snapshot.get("bias_20", 0.0)`, `c300 = snapshot.get("c300", 4053.0)`, `m20 = snapshot.get("m20", 4180.5)`, `trigger_lines = snapshot.get("trigger_lines", {})`
     - 量化逻辑:
       * 若 `bias_20 < -4.5%` 且 `snapshot.get("erp_percentile", 0) >= 75.0`: "大盘处于左侧极度超卖吸筹区 (20日乖离率 {bias_20:.1f}%, ERP分位 {erp_percentile:.1f}%)，触发逆向增配高弹性宽基信号。"
       * 若 `bias_20 >= 6.5%`: "大盘出现右侧极端超买 (20日乖离率 {bias_20:.1f}%)，触发阶梯止盈信号。"
       * 若 `-1.5% <= bias_20 <= +1.2%`: "大盘现价处于 MA20 迟滞震荡噪音带 (乖离率 {bias_20:+.1f}%)，未形成有效进攻突破 (进攻线: {trigger_lines.get('surge_line', 0):.1f})，建议锁定仓位不折腾。"
       * 其它情况输出对应突破/走弱方向的人话解析。
  2. `clock_window_reason` (15:00 交易时钟诊断):
     - 数据来源: `TradingClock().get_market_window_status(datetime.now())`
     - 量化逻辑:
       * 若 `window_type == "GOLDEN_WINDOW"`: "当前正处于 14:30-14:55 黄金执行窗口，盘中多空博弈与全天估值已锁定，最适宜提交申赎以锁定今日 T 日收盘净值。"
       * 若 `window_type == "OBSERVATION"`: "当前处于盘中观察期 (09:30-14:30)，盘中波动较大，建议待 14:30 黄金窗口再锁定操作，防日内跳水。"
       * 若 `window_type in ["POST_MARKET_DELAYED", "NON_TRADING_DAY"]`: "当前已过 15:00 申赎生死线 (或处于非交易日)，今日提交将延至下一交易日 ({effective_trade_date}) 收盘净值成交，面临隔夜波动风险。"
       * 若 `window_type == "CRITICAL_CLOSING"`: "处于 14:55-15:00 临界关账窗口，渠道即将截止，操作有滑点延期风险。"
  3. `deviation_utility_reason` (偏离度与净效用诊断):
     - 数据来源: `pm.holdings`, `pm.available_cash`, `target_weights = StrategyBridge.compute_dynamic_tier_weights(tier=active_tier, market_snapshot=snapshot)`
     - 量化逻辑:
       * 计算组合各标的绝对偏离度 $d_i = |w_{\text{curr}, i} - w_{\text{target}, i}|$，取最大偏离 $D_{\max} = \max_i d_i$。
       * 测算计划总调仓金额与潜在调仓的预期净效用 $\Delta U$。
       * 若 $D_{\max} < 0.03$: "当前组合持仓与目标配置高度贴合 (最大标的偏离仅 {D_max*100:.1f}%)，处于 3% 免折腾缓冲区内，微幅换仓的摩擦成本将吞噬潜在收益。"
       * 若 $D_{\max} \ge 0.03$: "持仓偏离显著 (最大标的偏离达 {D_max*100:.1f}%)，具备再平衡价值，预期调仓超额收益足以覆盖摩擦成本。"
  4. `lockup_fee_reason` (FIFO 批次锁定期诊断):
     - 数据来源: 遍历需减仓标的的 `h.batches`
     - 量化逻辑:
       * 统计拟卖出标的中是否存在持有天数 $< 7$ 天的份额。
       * 若拟减仓金额全部落入 $< 7$ 天批次: "持仓包含未满 7 天批次，强行卖出将全额触发 1.50% 证监会惩罚性赎回费，构成严重收益磨损。"
       * 若持有天数在 7~29 天 (C类) 或 30~179 天 (A类) 且距离免赎临界点 $\le 5$ 天: "部分持仓距离免赎回费阶梯仅剩数日，建议稍作等待以节约手续费。"
       * 若全部卖出份额均已满免赎期: "拟卖出份额均已满免赎期 (C类满30天/A类满180天)，赎回摩擦为零。"

- **综合裁决 `verdict_level` 与 `verdict_title` 推演规则**:
  - `FORBIDDEN` (🔴 今日不宜调仓·高损预警):
    * 触发条件: 存在调仓减仓需求，但该标的**全部可卖份额均处于未满 7 天惩罚期**（即 `penalty_free_shares <= 1e-4`，卖出将无情触发 1.50% 扣款）；或处于非交易日且偏离严重倒挂。
    * 标题模版: `🔴 今日不宜调仓·高损预警：持仓包含未满7天份额，强行卖出将触发1.5%惩罚费`
  - `HOLD_ON` (🟡 今日建议按兵不动):
    * 触发条件: 非 FORBIDDEN 且满足以下任一：
      1. 大盘处于施密特迟滞区间 `[-1.5%, +1.2%]`（无单边有效突破）；
      2. 组合最大偏离 $D_{\max} < 0.03$（在 3% 缓冲免折腾区内）；
      3. 调仓净效用 $\Delta U \le 0$（换仓得不偿失）；
      4. 当前已过 15:00 生死线；
      5. 存在临界免赎优化批次（5天内免赎）。
    * 标题模版: `🟡 今日建议按兵不动：大盘处于均线震荡噪音带，且您的持仓最大偏离仅 {D_max*100:.1f}%`
  - `SUITABLE` (🟢 今日适合调仓):
    * 触发条件: 满足突破均线/三段式信号触发，且 $D_{\max} \ge 0.03$，卖出份额均已过 7 天惩罚锁，净效用 $\Delta U > 0$，处于交易时间（黄金窗口最佳）。
    * 标题模版: `🟢 今日适合调仓：大盘形成有效突破，且调仓预期超额显著覆盖摩擦成本`

---

### 2.2 `simulate_rebalance_modes_and_consequences` 算法推演与结构设计
- **方法签名**:
  `StrategyBridge.simulate_rebalance_modes_and_consequences(pm, active_tier: str = "C3") -> Dict[str, Any]`

- **双调仓模式生成机制**:
  1. `mode_gentle` (模式一：温和免伤调仓):
     - 执行参数: `min_buffer_pct = 3.0`。
     - 偏离度 $< 3.0\%$ 的标的直接标记为 `HOLD`，不产生交易动作。
     - 卖出份额上限被 `pm.get_penalty_free_redeemable_shares(code)` 严格限制在 `holding_days >= 7` 范围内，未满 7 天批次 100% 保护留存。
     - 优先将同基金公司且方向相反的标的匹配为 `PRIORITY_1_SWITCH`（同公司转换，T+1，0 在途）。
  2. `mode_forced` (模式二：强行一步到位调仓):
     - 执行参数: `min_buffer_pct = 0.0`。
     - 无视 3% 缓冲带，微小偏离亦强行校准。
     - 卖出份额无视 7 天限制，直接按理论目标权重计算所需卖出总份额 `desired_shares = min(h.shares, round(diff_amount / h.current_nav, 2))`。
     - 对未满 7 天批次强行平仓，如实计算 1.50% 惩罚费。

- **四大后果字典 `consequences` 精算推演**:
  每个模式均必须返回结构对称、量化精确的 `consequences`：
  ```python
  "consequences": {
      "fee_loss": {
          "redemption_fee": float,    # 满7天后的常规阶梯赎回费
          "penalty_fee_7d": float,    # 未满7天强扣的 1.50% 惩罚费 (mode_gentle 中恒为 0.0)
          "subscription_fee": float,  # 新买入/调入产生的申购费 (A类按0.12%~0.15%, C类0.0, SWITCH优惠)
          "total_fee": float,         # 三者精确相加: redemption_fee + penalty_fee_7d + subscription_fee
          "payback_days": int         # 手续费预计回本天数
      },
      "in_transit_risk": {
          "in_transit_amount": float,    # 跨公司/两阶段在途资金总额
          "in_transit_pct": float,       # (in_transit_amount / total_equity) * 100
          "lock_days": str,              # 在途时滞文本 (如 "T+2 ~ T+4 交易日" 或 "0天 (同公司转换)")
          "switch_saved_amount": float,  # 通过 SWITCH 成功免去在途的资金总额
          "missed_rally_cost_est": float # 在途资金潜在踏空机会成本 (in_transit_amount * vol/sqrt(250) * sqrt(days))
      },
      "risk_shift": {
          "equity_before": float,      # 调仓前总权益 (总市值 + 现金 + 在途)
          "equity_after": float,       # 调仓后净资产 (equity_before - total_fee)
          "vol_before": float,         # 调仓前历史年化波动率 (%)
          "vol_after": float,          # 调仓后年化波动率 (%)
          "mdd_before": float,         # 调仓前历史最大回撤 (%)
          "mdd_after": float,          # 调仓后历史最大回撤 (%)
          "div_yield_before": float,   # 调仓前加权股息率 (%)
          "div_yield_after": float     # 调仓后加权股息率 (%)
      },
      "lockup_reset": {
          "new_buy_amount": float,     # 新增买入总金额
          "reset_warning_text": str    # "新买入资金将重新锁定 7 天 1.50% 惩罚性赎回费率；若为 A 类份额，免赎回费持有期将重新从第 0 天起算（需满 180 天方可免赎）。"
      }
  }
  ```

---

### 2.3 `calculate_stock_overlap_matrix()` 双红利底仓协同豁免与非豁免重叠度
- **代码定位**: `portfolio_manager.py` 第 3499 ~ 3637 行。
- **协同豁免池扩容**:
  在 `EXEMPT_OVERLAP_PAIRS` 中新增标准双红利底仓组合：
  ```python
  EXEMPT_OVERLAP_PAIRS = {
      frozenset({"050025", "001071"}), # 标普500官方限购拆单伴生组
      frozenset({"100032", "005561"}), # 策略推荐双红利底仓协同组合 (红利增强 + 红利低波)
      frozenset({"011612", "011613"}), # 华夏科创50 A/C 同源份额
      ...
  }
  ```
- **豁免判定与原因标注**:
  ```python
  is_dual_dividend = (pair_set == frozenset({"100032", "005561"}))
  is_exempt = (
      pair_set in EXEMPT_OVERLAP_PAIRS
      or is_same_ac
      or is_quota_split
      or is_dual_dividend
  )
  if is_exempt:
      note_text = "策略推荐双红利底仓协同组合 (红利增强 + 红利低波)" if is_dual_dividend else "合规限购分仓/同源份额"
      matrix_notes.append(f"标的【{fund_labels[i]}】与【{fund_labels[j]}】重合度 {overlap:.2f}：{note_text}")
      exempt_pairs.append({
          "fund1": c1,
          "fund2": c2,
          "overlap": overlap,
          "common_stocks": list(s1.intersection(s2)) if s1 and s2 else [],
          "note": note_text
      })
  ```
- **`max_non_diag_unexcused` 计算公式**:
  只统计所有非对角线（$i \ne j$）且**未经任何豁免**（`not is_exempt`）的基金对的前十大重仓股重叠度：
  ```python
  unexcused_overlaps = []
  # 在遍历 i, j 循环中:
  if not is_exempt:
      unexcused_overlaps.append(overlap)

  max_non_diag_unexcused = round(float(max(unexcused_overlaps)), 2) if unexcused_overlaps else 0.0
  ```
- **返回值更新**:
  字典中显式注入 `"max_non_diag_unexcused": max_non_diag_unexcused`。
- **预期业务效果**:
  持有标准推荐组合（100032 + 005561 + 002351 + 000216 + 050025/001071）时：
  1. `100032` 与 `005561` 即使重叠度高达 0.50，也因进入豁免池而绝不出现在 `alerts` 中；
  2. 其余跨大类资产（红利与纯债、红利与美股、红利与黄金）重合度均为 0；
  3. `max_non_diag_unexcused` 严格为 `0.0`（远低于 0.40 预警红线）；
  4. 绝不触发任何黄色伪分散警告！

---

## 3. Caveats (注意事项与边界)

1. **裁判文件绝对只读铁律**:
   `judge_engine.py`、`holdout_vault.py`、`AGENT_SPEC.md` 以及 `tests/test_infra.py` 为系统只读基准，Agent-3 与 Agent-4 严禁试图修改其任何内容，否则将被裁判引擎判定为作弊违规。
2. **反作弊 AST 日历字面量红线**:
   `judge_engine.py` 的 `scan_ast_for_calendar_cheating()` 严格禁止在策略逻辑中出现 `'2018'` ~ `'2025'` 的年份字符串。在 `strategy_bridge.py` 新增代码中，禁止在策略逻辑中使用硬编码年份，必须使用 `datetime.now()`、动态日期或相对偏移计算。
3. **空持仓与单只持仓边界处理**:
   当用户清空持仓或仅有 1 只持仓时：
   - `calculate_stock_overlap_matrix()` 必须安全返回 `max_non_diag_unexcused = 0.0`，不得抛出 `ValueError: max() arg is an empty sequence`；
   - `evaluate_today_rebalance_suitability()` 在总资产为 0 时需妥善处理，避免除以零；
   - `simulate_rebalance_modes_and_consequences()` 需支持可用现金为 0 或持仓批次为空的边界输入。
4. **同公司 SWITCH 与跨公司在途资金核对**:
   同公司转换虽然踏空天数为 0，但仍需核验基金公司名称字符串是否严格对齐（如 `meta.get("company")` 均为 "富国基金"）。若公司名缺失或不同，必须降级为跨公司两阶段换仓并计提在途资金。
5. **浮点数精度与舍入对齐**:
   `total_fee` 必须与 `redemption_fee + penalty_fee_7d + subscription_fee` 分厘严格平账（保留两位小数 `round(..., 2)`），严禁出现因浮点累加导致的 0.01 元对账误差。

---

## 4. Conclusion (结论与各角色实施指引)

### 4.1 给 Agent-3 的精确落地清单
1. **修改 `portfolio_manager.py` 中的 `calculate_stock_overlap_matrix()`** (Lines 3499-3637):
   - 在 `EXEMPT_OVERLAP_PAIRS` 集合中追加 `frozenset({"100032", "005561"})`；
   - 记录豁免说明为 `"策略推荐双红利底仓协同组合 (红利增强 + 红利低波)"`；
   - 计算非豁免最大重合度 `max_non_diag_unexcused`；
   - 在返回字典中返回 `"max_non_diag_unexcused": max_non_diag_unexcused`。
2. **在 `strategy_bridge.py` 中新增 `evaluate_today_rebalance_suitability(cls, pm, active_tier="C3")`**:
   - 联动 `TradingClock`、`get_latest_market_snapshot` 与 `pm.holdings` 的 FIFO 批次持有天数；
   - 返回 `verdict_level` ("SUITABLE" | "HOLD_ON" | "FORBIDDEN")、`verdict_title` 与包含 `market_position_reason`, `clock_window_reason`, `deviation_utility_reason`, `lockup_fee_reason` 的 `reasons_4d` 字典。
3. **在 `strategy_bridge.py` 中新增 `simulate_rebalance_modes_and_consequences(cls, pm, active_tier="C3")`**:
   - 分别以 `min_buffer_pct=3.0` (且带 7 天安全裁剪) 与 `min_buffer_pct=0.0` (全额强平) 生成 `mode_gentle` 与 `mode_forced`；
   - 输出完整的 `consequences`（包含 `fee_loss`, `in_transit_risk`, `risk_shift`, `lockup_reset`）。
4. **在 `strategy_bridge.py` 底部导出这两个新方法**:
   - 追加 `evaluate_today_rebalance_suitability = StrategyBridge.evaluate_today_rebalance_suitability`
   - 追加 `simulate_rebalance_modes_and_consequences = StrategyBridge.simulate_rebalance_modes_and_consequences`

### 4.2 给 Agent-4 的红队测试设计与断言规划
编写高覆盖率的自动化测试套件（建议在 `tests/test_milestone_phase1_r1_r5.py` 中落地），覆盖以下 11 个红队断言用例：

| 用例 ID | 涉及需求 | 测试场景 | 核心断言内容 |
|:---|:---|:---|:---|
| `test_case_01_read_only_invariants` | R1 | 4大裁判文件只读与防篡改验证 | 断言 4 个文件 SHA256 与基线完全一致，未被任何流程触碰 |
| `test_case_02_ast_no_cheating` | R1 | AST 语法树静态扫描 | 断言新编写代码无 `time.sleep`，无硬编码日历年份，前端无猴子补丁 |
| `test_case_03_realtime_quota_fetch_and_cache` | R2 | 实时限购拉取与断网缓存回退 | 断言返回 `is_limited`/`daily_limit`；mock 断网时正确回退读取最近真实有效缓存文件 |
| `test_case_04_waterfall_quota_split_and_dca` | R2 | 瀑布流拆单与动态 action_guide 与定投生成 | 当首选限额 1000 时，断言首选仅买 1000且文案动态包含单日限额；备选承接超额；若均限额则断言生成 DCA 计划且天数金额精确平账 |
| `test_case_05_qdii_intraday_valuation_correction` | R2 | QDII 与跨市场估值失真覆盖纠偏 | 偏差 $\le 1.5\%$ 不纠偏；偏差 $> 1.5\%$（如 -4.92% vs +1.0%）自动覆盖为基准涨跌幅 * 0.95 |
| `test_case_06_dynamic_tier_weights_no_c3_hijack` | R3 | C1~C5 动态权重与解除 C3 常数劫持 | 断言 C3 返回值并非静态常数 `[0.38, 0.30...]`，权重和为 1.0，随市场动态演进 |
| `test_case_07_three_stage_offensive_defensive` | R3 | 三段式攻防闭环触发测试 | 1) 左侧极值超卖 (bias<=-4.5%, erp>=75) 从纯债划拨 10%~15% 增配宽基；2) 噪音带 [-1.5%, +1.2%] 维持迟滞锁定；3) 右侧超买 (bias>=6.5%) 削减成长转入防御 |
| `test_case_08_ladder_redemption_fee_alignment` | R3 | 7天/30天/180天 真实阶梯赎回费对齐 | 针对 5天(1.5%)、15天(0.5%)、200天(0%) 进行逐笔校验 |
| `test_case_09_suitability_verdict_4d_and_levels` | R4 | 调仓适宜度三色裁决与四维白话完整性 | 1) 突破且偏离>3% 返回 SUITABLE; 2) 噪音带或偏离<3% 返回 HOLD_ON; 3) 存在<7天惩罚份额返回 FORBIDDEN；断言 `reasons_4d` 4个字段非空 |
| `test_case_10_simulate_rebalance_modes_consequences`| R4 | 温和 vs 强行调仓双模式及四大后果量化校验 | 1) mode_gentle 惩罚费严格为 0，卖出份额被裁剪；2) mode_forced 强平全额偏离，惩罚费真实计提；3) consequences 四大字典结构完整、分厘平账 |
| `test_case_11_stock_overlap_dual_dividend_exemption`| R4 | 双红利底仓对与限购伴生对豁免对抗测试 | 1) 同时持有 100032 与 005561 时，alerts 无告警，max_non_diag_unexcused < 0.40；2) 对抗测试：持有非豁免高重合基金 (011612与013841) 必须真实触发伪分散告警且 max_non_diag_unexcused >= 0.40 |

---

## 5. Verification Method (独立复现与验证步骤)

后续接手的 Agent-3 与 Agent-4 可通过以下命令进行精确验证：

1. **核验裁判文件不可变性**:
   ```powershell
   git status AGY2_FundAdvisory/judge_engine.py AGY2_FundAdvisory/holdout_vault.py AGY2_FundAdvisory/AGENT_SPEC.md AGY2_FundAdvisory/tests/test_infra.py
   # 必须显示 clean，无任何修改
   ```

2. **单模块运行现有组合管理器测试**:
   ```powershell
   cd d:\Google\Workspace\Wind\AGY2_FundAdvisory
   py -3.11 -m pytest tests/test_portfolio_manager.py -v
   ```

3. **单模块运行策略桥接器测试**:
   ```powershell
   cd d:\Google\Workspace\Wind\AGY2_FundAdvisory
   py -3.11 -m pytest tests/test_strategy_bridge.py -v
   ```

4. **运行重构与升级验收测试**:
   ```powershell
   cd d:\Google\Workspace\Wind\AGY2_FundAdvisory
   py -3.11 -m pytest tests/test_acceptance_r1_r7.py -v
   ```

5. **运行全量测试套件（严守 100% 通过红线）**:
   ```powershell
   cd d:\Google\Workspace\Wind\AGY2_FundAdvisory
   py -3.11 -m pytest
   ```

6. **反向作弊与判定失效条件 (Invalidation Conditions)**:
   - 若 `max_non_diag_unexcused` 计算时误将豁免对纳入统计，导致推荐标准组合触发告警，判定为实现失败；
   - 若 `mode_gentle` 产生任何未满 7 天的卖出动作并计提了 `penalty_fee_7d > 0`，判定为安全裁剪失效；
   - 若 `evaluate_today_rebalance_suitability` 返回缺失 `reasons_4d` 任意字段或使用假随机字典应付测试，红队断言将坚决拦截。
