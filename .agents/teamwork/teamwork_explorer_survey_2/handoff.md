# 阶段一后端量化算法与数据接口对接调研报告 (Phase 2 Survey Report)

## 一、直接观察 (Observation)

通过对 `AGY2_FundAdvisory/strategy_bridge.py`、`AGY2_FundAdvisory/portfolio_manager.py`、`AGY2_FundAdvisory/data_loader.py` 以及现有 `app_gui.py` 源码的深入只读调查，直接观察到以下关键接口实现与数据定义：

### 1. 今日调仓适宜度裁决器 `evaluate_today_rebalance_suitability`
- **代码位置**：`AGY2_FundAdvisory/strategy_bridge.py:4892-5048`
- **导出方式**：`StrategyBridge.evaluate_today_rebalance_suitability`，亦在模块顶层导出 `from strategy_bridge import evaluate_today_rebalance_suitability`
- **函数签名**：
  ```python
  @classmethod
  def evaluate_today_rebalance_suitability(
      cls,
      pm: Any,
      active_tier: str = "C3"
  ) -> Dict[str, Any]
  ```
- **核心逻辑与三色裁决分支**：
  - 调用 `TradingClock().get_market_window_status(datetime.now())` 获取 `w_type`（"GOLDEN_WINDOW", "OBSERVATION", "CRITICAL_CLOSING", "CLOSED_PREMARKET", "POST_MARKET_DELAYED", "NON_TRADING_DAY"）与 `effective_trade_date`。
  - 调用 `cls.get_latest_market_snapshot()` 获取 `bias_20`、`erp_percentile`、`trigger_lines`。
  - 调用 `cls.compute_dynamic_tier_weights(tier=active_tier, market_snapshot=snapshot)` 获取今日目标动态权重，计算最大标的权重偏离 `d_max`。
  - 检查 FIFO 批次锁定期：检测是否存在强行卖出未满 7 天份额（`has_forbidden_penalty_sell`）或临界免赎阶梯（`has_approaching_cliff`）。
  - **裁决评级等级与一句话结论规则**：
    - 若 `has_forbidden_penalty_sell`：
      - `verdict_level`: `"FORBIDDEN"`
      - `verdict_title`: `"🔴 今日不宜调仓·高损预警：持仓包含未满7天份额，强行卖出将触发1.5%惩罚费"`
    - 否则若 `(-1.5 <= bias_20 <= 1.2) or (d_max < 0.03) or (w_type in ["POST_MARKET_DELAYED", "NON_TRADING_DAY"]) or has_approaching_cliff`：
      - `verdict_level`: `"HOLD_ON"`
      - `verdict_title`: 根据触发主因生成，如 `f"🟡 今日建议按兵不动：大盘处于均线震荡噪音带，且您的持仓最大偏离仅 {d_max*100:.1f}%"` 或 `f"🟡 今日建议按兵不动：当前已过 15:00 申赎生死线，下单将延期至下一交易日"`
    - 否则：
      - `verdict_level`: `"SUITABLE"`
      - `verdict_title`: `"🟢 今日适合调仓：大盘形成有效突破，且调仓预期超额显著覆盖摩擦成本"`
  - **四维诊断字典 `reasons_4d` 键名与内容**：
    1. `market_position_reason` (str)：近期大盘位置诊断（区分左侧超卖、右侧超买、MA20噪音带、右侧突破、跌破防守线 5 大行情）；
    2. `clock_window_reason` (str)：15:00 交易时钟诊断（区分 14:30-14:55 黄金窗口、盘中观察期、14:55-15:00 临界关账、盘前未开市、盘后/非交易日延时窗口）；
    3. `deviation_utility_reason` (str)：偏离度与净效用诊断（区分空仓、d_max < 3% 免折腾缓冲区、d_max >= 3% 具备再平衡价值）；
    4. `lockup_fee_reason` (str)：FIFO 批次锁定期诊断（区分无需卖出、含未满7天惩罚份额、临界免赎期、已满免赎期、常规阶梯费）。
  - **返回完整结构**：
    ```python
    {
        "verdict_level": "SUITABLE" | "HOLD_ON" | "FORBIDDEN",
        "verdict_title": str,
        "reasons_4d": {
            "market_position_reason": str,
            "clock_window_reason": str,
            "deviation_utility_reason": str,
            "lockup_fee_reason": str
        },
        "d_max": float,        # 四舍五入保留4位小数，如 0.0120
        "bias_20": float,      # 20日均线乖离率，如 +0.85
        "window_type": str,    # TradingClock window_type
        "active_tier": str     # 如 "C3"
    }
    ```

---

### 2. 双模式调仓推演与四大后果精算 `simulate_rebalance_modes_and_consequences`
- **代码位置**：`AGY2_FundAdvisory/strategy_bridge.py:5051-5463`
- **函数签名**：
  ```python
  @classmethod
  def simulate_rebalance_modes_and_consequences(
      cls,
      pm: Any,
      active_tier: str = "C3"
  ) -> Dict[str, Any]
  ```
- **核心逻辑与返回值结构**：
  返回包含两个顶层键的字典：`{"mode_gentle": dict, "mode_forced": dict}`。
  - `mode_gentle`（模式一：温和免伤调仓）：`min_buffer = 0.03`（遵循 3% 免折腾缓冲），卖出时调用 `pm.get_penalty_free_redeemable_shares(code)` 严格裁剪未满免赎期份额，`penalty_fee_7d` 严格归零；
  - `mode_forced`（模式二：强行一步到位调仓）：`min_buffer = 0.0`，无视持有期限制强行将所有持仓对齐至今日目标权重，全额核算每一笔批次的赎回费与 7 天 1.5% 惩罚费。
  - 每个模式内部包含：
    1. `mode_name`: str
    2. `orders`: list of order dicts（亦别名为 `items`），订单包含三种类型：
       - `SWITCH` 订单（同基金公司免在途转换）：
         ```python
         {
             "action": "SWITCH",
             "from_code": str,
             "to_code": str,
             "amount": float,
             "shares": float,
             "description": f"同公司转换：从 {from_name} 转换至 {to_name}"
         }
         ```
       - `BUY` 订单：
         ```python
         {
             "action": "BUY",
             "fund_code": str,
             "amount": float,
             "route": "PRIORITY_2_CASH_ADVANCE" | "PRIORITY_3_TWO_STEP",
             "description": str
         }
         ```
       - `SELL` 订单：
         ```python
         {
             "action": "SELL",
             "fund_code": str,
             "amount": float,
             "shares": float,
             "route": "SELL_TO_CASH",
             "description": str
         }
         ```
    3. `routes`: list of route trace dicts（包含优先路由级别 `PRIORITY_1_SWITCH`、`PRIORITY_2_CASH_ADVANCE`、`PRIORITY_3_TWO_STEP`、`SELL_TO_CASH`）。
    4. `consequences`: 四大后果量化精算字典：
       - `fee_loss`:
         ```python
         {
             "redemption_fee": float,   # 常规赎回费 (元)
             "penalty_fee_7d": float,   # 7天以内 1.5% 惩罚性赎回费 (元, 温和模式下为 0.0)
             "subscription_fee": float, # 申购费 (元)
             "total_fee": float,        # 总手续费 (元)
             "payback_days": int        # 预计靠分红增厚回本所需天数 (天)
         }
         ```
       - `in_transit_risk`:
         ```python
         {
             "in_transit_amount": float,     # 跨公司换仓导致的在途冻结资金 (元)
             "in_transit_pct": float,        # 在途资金占总资产比例 (%)
             "lock_days": str,               # "T+2 ~ T+4 交易日" 或 "0天 (同公司转换/现金直达)"
             "switch_saved_amount": float,   # 同公司转换节省的在途免冻结金额 (元)
             "missed_rally_cost_est": float  # 潜在踏空机会成本预估 (元)
         }
         ```
       - `risk_shift`:
         ```python
         {
             "equity_before": float,    # 调仓前总权益 (元)
             "equity_after": float,     # 调仓后扣除手续费总权益 (元)
             "vol_before": float,       # 调仓前年化波动率 (%)
             "vol_after": float,        # 调仓后年化波动率 (%)
             "mdd_before": float,       # 调仓前最大回撤水位 (%)
             "mdd_after": float,        # 调仓后最大回撤水位 (%)
             "div_yield_before": float, # 调仓前组合加权股息率 (%)
             "div_yield_after": float   # 调仓后组合加权股息率 (%)
         }
         ```
       - `lockup_reset`:
         ```python
         {
             "new_buy_amount": float,      # 新买入资金总额 (元)
             "reset_warning_text": str     # "新买入资金将重新锁定 7 天 (7天) 1.50% 惩罚性赎回费率；若为 A 类份额，免赎回费持有期将重新从第 0 天起算（需满 180 天方可免赎）。"
         }
         ```

---

### 3. 实时限购与从 0 建仓蓝图 `generate_zero_start_blueprint` 与 `fetch_realtime_fund_quota`
- **代码位置**：
  - `fetch_realtime_fund_quota`: `portfolio_manager.py:1624-1736`
  - `generate_zero_start_blueprint`: `portfolio_manager.py:3185-3354`（亦由 `StrategyBridge.generate_zero_start_blueprint` 维护）
- **实时限购接口返回**：
  ```python
  {
      "fund_code": "050025",
      "status": "限制大额" | "开放申购" | "暂停申购",
      "daily_limit": 500.0,
      "is_limited": True
  }
  ```
  内部具备 L1 内存缓存、L2 SQLite 带日期戳缓存、akshare 联网以及断网回退三级容灾。
- **瀑布流拆单与 `action_guide` 动态生成**：
  - 当某标的分配金额 `amt > quota["daily_limit"]`：
    - 首选标的分得 `quota["daily_limit"]`，其 `action_guide` 为：`f"单日限额¥{int(daily_lim)}·已拆单"`；
    - 遍历备选标的（如 001071），若自身不限购（`alt_limit >= rem_amt`），`action_guide` 为：`"承接超额·不限购正常买"`；若自身也限购，则分得 `alt_limit`，`action_guide` 为：`f"单日限额¥{int(alt_limit)}·已拆单"`；
    - 若全赛道备选遍历完仍有未分配完的剩余资金，自动在蓝图顶层及对应条目生成 `dca_plan`：
      `blueprint["dca_plan"] = "剩余¥XXXX受全市场QDII限额约束，建议分X个交易日定投买入，或暂存货币/黄金底仓"`；
  - 当标的不限购（`amt <= daily_lim`）：
    - `action_guide` 为：`"正常买入"`。
- **与 `app_gui.py` 步骤三 9 列表格对接点**：
  - 既有 `app_gui.py:1201-1209` 硬编码了 `guide_action = "现金分红·限额买500"`，违反 R1 与 R2 规范！
  - 必须改为直接提取并绑定 `it.get("action_guide")`：
    ```python
    raw_guide = it.get("action_guide") or ("已拆单" if it.get("has_split") else "正常买入")
    if it.get("require_cash_dividend"):
        if raw_guide and raw_guide != "正常买入":
            guide_action = f"现金分红·{raw_guide}"
        else:
            guide_action = "现金分红·满期免赎A"
    elif raw_guide and raw_guide != "正常买入":
        guide_action = raw_guide
    elif it.get("share_class") == "C":
        guide_action = "红利再投·弹性进攻C"
    else:
        guide_action = "长钱持有·满期免赎A"
    ```
  - 并在步骤三表格下方检查 `if blueprint.get("dca_plan"): st.info(f"💡 **《超限资金分批定投执行计划》**：{blueprint['dca_plan']}")`。

---

### 4. 顶部 1 行 4 宽卡所需数据接口
原 `app_gui.py` 顶部为 3 层（调仓网格横幅 + 7 张窄卡片 + 蓝色宏观雷达长条），在 1080p 屏幕下存在大量省略号（`...`）截断。重构为 1 行 4 宽卡 + 1 个刷新按钮所需接口映射如下：

1. **卡片 1【🕒 交易时钟与窗口 ⓘ】**：
   - 数据源：
     - `clock = TradingClock()`
     - `clock_status = clock.get_market_window_status(datetime.now())`
     - `rebal_grid = snapshot.get("rebal_grid") or StrategyBridge.get_rebalance_grid_status()`
     - `days_to_next = rebal_grid.get("days_to_next", 0)`
   - 主值：
     - 若 `clock_status.window_type == "GOLDEN_WINDOW"`：`f"🟢 14:30黄金窗口 ({clock_status.countdown_str})"`
     - 若 `clock_status.window_type == "OBSERVATION"`：`f"🔵 盘中观察期 ({clock_status.countdown_str})"`
     - 否则：`f"🟡 盘后已关账 ({clock_status.countdown_str})"`
   - 副标题：`f"距下次常规网格日 {days_to_next} 天"`
   - 悬停 `ⓘ`：15:00 申赎规则、当前时间、有效确认日与提示文案。

2. **卡片 2【🧭 市场定调与攻防线 ⓘ】**：
   - 数据源：
     - `snapshot = StrategyBridge.get_latest_market_snapshot()`
     - `raw_mkt_state = snapshot.get("market_state", "震荡收息期")`
     - `c300_price = snapshot.get("c300_price", 4053.0)`
     - `m20_price = snapshot.get("m20_price", 4140.0)`
     - `m60_price = snapshot.get("m60_price", 3962.0)`
     - `trigger_lines = snapshot.get("trigger_lines") or {}`
     - `surge_line = float(trigger_lines.get("surge_line", snapshot.get("surge_line", c300_price * 1.012)))`
     - `breakdown_line = float(trigger_lines.get("breakdown_line", snapshot.get("breakdown_line", c300_price * 0.985)))`
   - 主值：大白话定调（如 `🟢 震荡收息期` / `🔥 科技主升浪` / `🛡️ 熊市防守期` / `📈 结构分化期`）
   - 副标题：`f"📈破 {surge_line:,.0f} 进攻 ｜ 🛡️跌 {breakdown_line:,.0f} 防守"`
   - 悬停 `ⓘ`：`f"沪深300现价: {c300_price:,.1f}\nMA20生命线: {m20_price:,.1f} (偏离 {snapshot['bias_20']:+.2f}%)\nMA60中线: {m60_price:,.1f}\n突破加仓线: 突破 {surge_line:,.1f} 后增配科技成长(科创50/中证1000)\n跌破防守线: 跌破 {breakdown_line:,.1f} 后减仓避险至纯债压舱石"`

3. **卡片 3【🌡️ 估值与资金面温度 ⓘ】**：
   - 数据源：
     - `erp_pct = snapshot.get("erp_percentile", 81.9)`
     - `dr007 = snapshot.get("dr007", 1.39)`
     - `dr007_bp = snapshot.get("dr007_spread_bp", -11.1)`
     - `option_iv = snapshot.get("option_iv_pct", 19.4)`
     - `ic_basis = snapshot.get("ic_annualized_basis_rate", 17.9)`
   - 主值：大白话温度（如 `估值极便宜 · 资金充裕`）
   - 副标题：`股票性价比高 ｜ 央妈呵护`
   - 悬停 `ⓘ`：
     `f"ERP股债性价比分位: {erp_pct:.1f}% (极高分位·股票极具吸引力)\nDR007利率: {dr007:.2f}% (较基准 {dr007_bp:+.1f}bp·资金面宽裕)\n期权IV隐含波动率: {option_iv:.1f}% (定价平稳)\nIC期指年化贴水率: {ic_basis:.1f}% (对冲基差温和)"`

4. **卡片 4【💰 我的总资产与今日预估 ⓘ】**：
   - 数据源：
     - 若 `pm.total_equity <= 0` 则先调用 `pm._recalculate_totals()`
     - `total_cur_equity = float(getattr(pm, 'total_equity', 0.0))`
     - `pnl_today = pm.calculate_intraday_pnl()`
     - `est_pnl = pnl_today.get("total_est_pnl", 0.0)`
     - `est_pnl_pct = pnl_today.get("total_est_pnl_pct", 0.0)`
   - 主值：`f"¥{total_cur_equity:,.2f}"`
   - 副标题：`f"今日预估 ¥{est_pnl:+,.2f} ({est_pnl_pct:+.2f}%)"`
   - 悬停 `ⓘ`：可用现金、在途资金、持仓市值明细
   - 按钮：紧贴其右放置 `🔄 刷新实时行情`（调用 `clear_realtime_cache(); pm.sync_holdings_live_nav(); st.rerun()`）。

---

### 5. 重合度检测豁免机制 `calculate_stock_overlap_matrix`
- **代码位置**：`AGY2_FundAdvisory/portfolio_manager.py:3923-4078`
- **豁免集合定义**：`EXEMPT_OVERLAP_PAIRS` 显式包含了：
  - `frozenset({"100032", "005561"})`：策略推荐双红利底仓协同组合（红利增强 + 红利低波）；
  - `frozenset({"050025", "001071"})`：标普500官方限购拆单伴生组；
  - 全套 A/C 同源份额对（如 `011612+011613`, `100032+008682`, `000216+000217`, `002351+002352` 等）。
- **返回值关键字段**：
  - `max_non_diag_unexcused` (float)：**仅统计非豁免组合对的最大重叠度**！
  - `exempt_pairs` (list)：豁免对明细与豁免说明；
  - `matrix_notes` (list)：每对豁免标的的中文协同说明（如“策略推荐双红利底仓协同组合 (红利增强 + 红利低波)”）；
  - `alerts` (list)：**仅当非豁免对 overlap >= 0.40 时才产生报警**！
- **`app_gui.py` 现有 Bug 根因**：
  `app_gui.py:2288-2293` 直接遍历了原始 `matrix[i][j]` 计算 `max_non_diag`，忽略了 `max_non_diag_unexcused` 与 `alerts`，导致持有标准组合（100032 + 005561）时误触黄色伪分散报警。
- **Tab 3 修复方案**：
  判定逻辑必须收口为：
  ```python
  max_unexcused = overlap_res.get("max_non_diag_unexcused", 0.0)
  alerts = overlap_res.get("alerts", [])
  if max_unexcused < 0.20 and len(alerts) == 0:
      st.success("✅ **您的组合跨大类分散度极佳！** 前十大重仓股无未豁免交叉重叠（最高重叠仅 {:.1f}%，低于 20% 警戒线）。".format(max_unexcused * 100))
  ```

---

## 二、逻辑推理链 (Logic Chain)

1. **从 R1/R2（顶部看板大瘦身）到后端接口装配**：
   - 观测表明：顶部卡片需要的数据（时钟、沪深300现价、MA20/MA60、双向触发线、ERP分位、DR007、期权IV、IC贴水、总资产、今日预估）均已在 `TradingClock`、`StrategyBridge.get_latest_market_snapshot()` 与 `pm.calculate_intraday_pnl()` 中完整就绪。
   - 推理：前端只需一次性获取 `snapshot = StrategyBridge.get_latest_market_snapshot()` 与 `pnl_today = pm.calculate_intraday_pnl()`，即可在 `st.columns(4)` 中以紧凑卡片渲染，无需多次网络/文件读取，彻底消除延迟并杜绝文字截断。

2. **从 R3（四大 Tab 入口重塑）到职责分离**：
   - **Tab 1（🌱 新资金从0建仓推演）**：面向没有持仓或准备投入新资金的用户。移除原场景下拉框；步骤二直接调用 `generate_zero_start_blueprint`，4 个抽屉标题动态呈现数值摘要；步骤三 9 列表格第 9 列严格从 `it.get("action_guide")` 取值，全赛道限购超额时展示 `blueprint.get("dca_plan")`。
   - **Tab 2（💼 我的当前持仓与今日调仓建议）**：面向存量持仓管理。垂直排布：
     - 第一层：调用 `StrategyBridge.evaluate_today_rebalance_suitability(pm, active_tier)` 渲染红/黄/绿灯横幅与四维胶囊。
     - 第二层：调用 `StrategyBridge.simulate_rebalance_modes_and_consequences(pm, active_tier)`，单选切换温和 vs 强行模式，并排 4 张后果账单卡片，展示 9 列执行单。
     - 第三层：实时持仓表及 3 个接管向导面板（持仓数 > 0 时默认折叠）。
   - **Tab 3（🔍 组合深度体检与算费工具箱）**：大类缺口图、加权行业、已豁免的重合度检测、排雷宽表、在途对账与 A/C 算费器。
   - **Tab 4（📈 策略历史回测与胜率档案）**：净值曲线、水下回撤、仓位图、6大历史切片与相似行情匹配器。

3. **从 R4（存量调仓四大后果量化精算）到 UI 视觉账单映射**：
   - 观测表明 `simulate_rebalance_modes_and_consequences` 精确返回了 `consequences` 的 4 大字典。
   - 前端 Tab 2 第二层并排渲染 4 列卡片：
     - 卡片① 手续费直接损耗：`¥{fee_loss['total_fee']:,.2f}`（若 `penalty_fee_7d > 0` 红字高亮警告），回本天数 `{fee_loss['payback_days']} 天`；
     - 卡片② 在途踏空风险：在途金额 `¥{in_transit_risk['in_transit_amount']:,.2f} ({in_transit_risk['in_transit_pct']:.1f}%)`，空窗期 `{in_transit_risk['lock_days']}`，同公司转换节省 `¥{in_transit_risk['switch_saved_amount']:,.2f}`；
     - 卡片③ 组合攻防与回撤：权益仓位 `{risk_shift['equity_before']:,.0f} ➔ {risk_shift['equity_after']:,.0f}`，波动率 `{risk_shift['vol_before']:.1f}% ➔ {risk_shift['vol_after']:.1f}%`，回撤 `{risk_shift['mdd_before']:.1f}% ➔ {risk_shift['mdd_after']:.1f}%`；
     - 卡片④ 持有期清零重算：新买入 `¥{lockup_reset['new_buy_amount']:,.2f}` 重新进入 7 天惩罚期预警。

---

## 三、注意与局限 (Caveats)

1. **`pm.get_portfolio_summary()` 方法名考证**：
   - 观测：`PortfolioManager` 目前没有直接命名为 `get_portfolio_summary()` 的方法，其实际是由 `pm.total_equity`、`pm.available_cash`、`pm.in_transit_cash` 与 `pm.calculate_intraday_pnl()` 共同构成。
   - 建议：在 `app_gui.py` 中可编写轻量 helper 函数或直接就地组装，或由 implementer 在 `PortfolioManager` 中添加同名便捷方法。
2. **`StrategyBridge.generate_zero_start_blueprint` 与 `PortfolioManager.generate_zero_start_blueprint` 的一致性**：
   - 观测：`portfolio_manager.py:3185` 的 `PortfolioManager.generate_zero_start_blueprint` 是在阶段一完全升级为实时限购与瀑布流拆单的版本；`strategy_bridge.py:4054` 亦保留有早期版本的映射。
   - 建议：在 `app_gui.py` 中统一调用 `pm.generate_zero_start_blueprint(...)` 或 `portfolio_manager.generate_zero_start_blueprint(...)`，以确保 100% 具备动态 `action_guide` 与 `dca_plan`。
3. **Streamlit 执行环境与缓存清理**：
   - 阶段二重构必须在每次行情变动或点击刷新时调用 `clear_realtime_cache()` 与 `pm.sync_holdings_live_nav()`，防止 Streamlit 渲染陈旧的 session_state。

---

## 四、调研结论与前端对接伪代码说明 (Conclusion & Frontend Pseudocode)

### 1. 顶部 4 张大宽卡渲染伪代码
```python
# 1. 获取全局快照与交易时钟
clock = TradingClock()
clock_status = clock.get_market_window_status(datetime.now())
snapshot = StrategyBridge.get_latest_market_snapshot()
rebal_grid = snapshot.get("rebal_grid") or StrategyBridge.get_rebalance_grid_status()
days_to_next = rebal_grid.get("days_to_next", 0)

# 计算卡片 4 总资产与今日预估
if pm.total_equity <= 0:
    pm._recalculate_totals()
total_cur_equity = float(getattr(pm, "total_equity", 0.0))
pnl_today = pm.calculate_intraday_pnl()
est_pnl = pnl_today.get("total_est_pnl", 0.0)
est_pnl_pct = pnl_today.get("total_est_pnl_pct", 0.0)
pnl_color = "#dc2626" if est_pnl >= 0 else "#16a34a"

# 渲染 1 行 4 宽卡 + 1 个刷新按钮
c1, c2, c3, c4 = st.columns([1, 1, 1, 1.2])

with c1:
    # 卡片 1: 交易时钟与窗口
    w_type = clock_status.window_type
    w_main = f"🟢 14:30黄金窗口 ({clock_status.countdown_str})" if w_type == "GOLDEN_WINDOW" else (
        f"🔵 盘中观察期 ({clock_status.countdown_str})" if w_type == "OBSERVATION" else f"🟡 盘后已关账 ({clock_status.countdown_str})"
    )
    c1_tip = f"当前时间: {clock_status.current_time_str}\n状态: {clock_status.title}\n成交规则: 15:00前下单锁定今日(T日)收盘净值；15:00后顺延至下一交易日({clock_status.effective_trade_date})成交。\n{clock_status.message}"
    st.markdown(f"""
    <div class="wide-header-card">
        <div class="wide-card-title">🕒 交易时钟与窗口 <span title="{c1_tip}" class="help-icon">ⓘ</span></div>
        <div class="wide-card-val">{w_main}</div>
        <div class="wide-card-sub">距下次常规网格日 {days_to_next} 天</div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    # 卡片 2: 市场定调与攻防线
    raw_mkt = str(snapshot.get("market_state", "震荡收息期"))
    mkt_main = "🟢 震荡收息期" if any(k in raw_mkt for k in ["震荡", "收息", "慢牛"]) else (
        "🔥 科技主升浪" if any(k in raw_mkt for k in ["科技", "主升", "进攻"]) else "🛡️ 熊市防守期"
    )
    trig = snapshot.get("trigger_lines") or {}
    surge_l = float(trig.get("surge_line", snapshot.get("surge_line", 4141.0)))
    break_l = float(trig.get("breakdown_line", snapshot.get("breakdown_line", 3846.0)))
    c300_p = snapshot.get("c300_price", 4053.0)
    m20_p = snapshot.get("m20_price", 4140.0)
    m60_p = snapshot.get("m60_price", 3962.0)
    c2_tip = f"沪深300现价: {c300_p:,.1f}\nMA20生命线: {m20_p:,.1f} (偏离 {snapshot.get('bias_20', 0):+.2f}%)\nMA60中线: {m60_p:,.1f}\n突破加仓线: 突破 {surge_l:,.1f} 增配科技成长\n跌破防守线: 跌破 {break_l:,.1f} 减仓避险至纯债"
    st.markdown(f"""
    <div class="wide-header-card">
        <div class="wide-card-title">🧭 市场定调与攻防线 <span title="{c2_tip}" class="help-icon">ⓘ</span></div>
        <div class="wide-card-val">{mkt_main}</div>
        <div class="wide-card-sub">📈破 {surge_l:,.0f} 进攻 ｜ 🛡️跌 {break_l:,.0f} 防守</div>
    </div>
    """, unsafe_allow_html=True)

with c3:
    # 卡片 3: 估值与资金面温度
    erp_pct = snapshot.get("erp_percentile", 81.9)
    dr007 = snapshot.get("dr007", 1.39)
    dr007_bp = snapshot.get("dr007_spread_bp", -11.1)
    opt_iv = snapshot.get("option_iv_pct", 19.4)
    ic_basis = snapshot.get("ic_annualized_basis_rate", 17.9)
    c3_tip = f"ERP股债性价比分位: {erp_pct:.1f}% (极高分位·股票高性价比)\nDR007利率: {dr007:.2f}% (较基准 {dr007_bp:+.1f}bp·资金面宽裕)\n期权IV: {opt_iv:.1f}%\nIC期指年化贴水: {ic_basis:.1f}%"
    st.markdown(f"""
    <div class="wide-header-card">
        <div class="wide-card-title">🌡️ 估值与资金面温度 <span title="{c3_tip}" class="help-icon">ⓘ</span></div>
        <div class="wide-card-val">估值极便宜 · 资金充裕</div>
        <div class="wide-card-sub">股票性价比高 ｜ 央妈呵护</div>
    </div>
    """, unsafe_allow_html=True)

with c4:
    # 卡片 4: 我的总资产与今日预估 + 刷新按钮
    col_c4_text, col_c4_btn = st.columns([3, 1])
    with col_c4_text:
        c4_tip = f"全组合总资产: ¥{total_cur_equity:,.2f}\n可用现金: ¥{pm.available_cash:,.2f}\n在途资金: ¥{pm.in_transit_cash:,.2f}"
        st.markdown(f"""
        <div class="wide-header-card">
            <div class="wide-card-title">💰 我的总资产与今日预估 <span title="{c4_tip}" class="help-icon">ⓘ</span></div>
            <div class="wide-card-val">¥{total_cur_equity:,.2f}</div>
            <div class="wide-card-sub" style="color:{pnl_color};">今日预估 ¥{est_pnl:+,.2f} ({est_pnl_pct:+.2f}%)</div>
        </div>
        """, unsafe_allow_html=True)
    with col_c4_btn:
        st.write("") # 垂直对齐
        if st.button("🔄 刷新\n行情", key="btn_refresh_top_cards", use_container_width=True):
            clear_realtime_cache()
            pm.sync_holdings_live_nav()
            st.rerun()
```

### 2. Tab 2 第一层与第二层伪代码
```python
# 第一层：今日是否适合调仓？AI 综合裁决卡
suit_res = StrategyBridge.evaluate_today_rebalance_suitability(pm, active_tier=active_tier)
v_level = suit_res["verdict_level"]
v_title = suit_res["verdict_title"]
reasons = suit_res["reasons_4d"]

banner_bg = "#f0fdf4" if v_level == "SUITABLE" else ("#fefce8" if v_level == "HOLD_ON" else "#fef2f2")
banner_border = "#22c55e" if v_level == "SUITABLE" else ("#eab308" if v_level == "HOLD_ON" else "#ef4444")
banner_text = "#15803d" if v_level == "SUITABLE" else ("#a16207" if v_level == "HOLD_ON" else "#b91c1c")

st.markdown(f"""
<div style="background:{banner_bg}; border:1px solid {banner_border}; border-left:6px solid {banner_border}; border-radius:8px; padding:12px 16px; margin-bottom:12px;">
    <div style="font-size:16px; font-weight:700; color:{banner_text};">{v_title}</div>
</div>
""", unsafe_allow_html=True)

# 4 个简短胶囊列出四维实测结论
c_r1, c_r2, c_r3, c_r4 = st.columns(4)
with c_r1:
    st.markdown(f"**【行情位置】**：{reasons['market_position_reason']}")
with c_r2:
    st.markdown(f"**【申赎时钟】**：{reasons['clock_window_reason']}")
with c_r3:
    st.markdown(f"**【偏离净效用】**：{reasons['deviation_utility_reason']}")
with c_r4:
    st.markdown(f"**【批次锁定期】**：{reasons['lockup_fee_reason']}")

st.markdown("---")

# 第二层：双模式调仓推演与四大真实后果账单
sim_res = StrategyBridge.simulate_rebalance_modes_and_consequences(pm, active_tier=active_tier)

mode_choice = st.radio(
    "选择调仓推演模式：",
    [
        "🛡️ 模式一：AI 温和免伤调仓 (仅调动免惩罚费份额·遵循3%免折腾缓冲，推荐)",
        "⚡ 模式二：如果今天一定要调仓 (无视缓冲带强行一步到位对齐目标配比，查看真实代价)"
    ],
    horizontal=True
)
cur_sim = sim_res["mode_gentle"] if "模式一" in mode_choice else sim_res["mode_forced"]
cq = cur_sim["consequences"]
fee_loss = cq["fee_loss"]
in_transit = cq["in_transit_risk"]
risk_shift = cq["risk_shift"]
lockup = cq["lockup_reset"]

# 并排 4 张后果量化账单卡片
c_cq1, c_cq2, c_cq3, c_cq4 = st.columns(4)
with c_cq1:
    pen_warn = f"<div style='color:#ef4444; font-size:12px; font-weight:700;'>⚠️ 含7天内惩罚费: ¥{fee_loss['penalty_fee_7d']:,.2f}</div>" if fee_loss['penalty_fee_7d'] > 0 else "<div style='color:#10b981; font-size:12px;'>✅ 0 惩罚性赎回费</div>"
    st.markdown(f"""
    <div class="consequence-card">
        <div class="consequence-title">① 手续费直接损耗</div>
        <div class="consequence-val">¥{fee_loss['total_fee']:,.2f}</div>
        <div class="consequence-sub">
            赎回费: ¥{fee_loss['redemption_fee']:,.2f} ｜ 申购费: ¥{fee_loss['subscription_fee']:,.2f}<br>
            预计靠分红回本: <b>{fee_loss['payback_days']} 天</b><br>
            {pen_warn}
        </div>
    </div>
    """, unsafe_allow_html=True)

with c_cq2:
    st.markdown(f"""
    <div class="consequence-card">
        <div class="consequence-title">② T+2 资金在途踏空风险</div>
        <div class="consequence-val">¥{in_transit['in_transit_amount']:,.2f}</div>
        <div class="consequence-sub">
            在途占比: <b>{in_transit['in_transit_pct']:.1f}%</b> (空窗期 {in_transit['lock_days']})<br>
            同公司 SWITCH 节省在途: <b>¥{in_transit['switch_saved_amount']:,.2f}</b><br>
            潜在踏空机会成本预估: ¥{in_transit['missed_rally_cost_est']:,.2f}
        </div>
    </div>
    """, unsafe_allow_html=True)

with c_cq3:
    st.markdown(f"""
    <div class="consequence-card">
        <div class="consequence-title">③ 组合攻防与回撤变化</div>
        <div class="consequence-val">{risk_shift['vol_before']:.1f}% ➔ {risk_shift['vol_after']:.1f}%</div>
        <div class="consequence-sub">
            组合权益: ¥{risk_shift['equity_before']:,.0f} ➔ ¥{risk_shift['equity_after']:,.0f}<br>
            最大回撤: {risk_shift['mdd_before']:.1f}% ➔ <b>{risk_shift['mdd_after']:.1f}%</b><br>
            加权股息率: {risk_shift['div_yield_before']:.2f}% ➔ <b>{risk_shift['div_yield_after']:.2f}%</b>
        </div>
    </div>
    """, unsafe_allow_html=True)

with c_cq4:
    st.markdown(f"""
    <div class="consequence-card">
        <div class="consequence-title">④ 持有期清零重算后果</div>
        <div class="consequence-val">¥{lockup['new_buy_amount']:,.2f}</div>
        <div class="consequence-sub">
            新买入资金将重新锁定 <b>7天</b> 1.5% 惩罚期。<br>
            A类免赎持有期清零，需重新持有满 180 天方可免赎。
        </div>
    </div>
    """, unsafe_allow_html=True)
```

---

## 五、验证方法 (Verification Method)

### 1. 独立执行自动化测试套件
```bash
# 1. 验证阶段一量化算法与边界断言 (11 passed)
py -3.11 -m pytest AGY2_FundAdvisory/tests/test_milestone_phase1_r1_r5.py -v

# 2. 验证 StrategyBridge 与 PortfolioManager 全量单元测试 (34 passed)
py -3.11 -m pytest AGY2_FundAdvisory/tests/test_strategy_bridge.py AGY2_FundAdvisory/tests/test_portfolio_manager.py -v

# 3. 验证端到端 GUI 渲染与 Tab 切换测试
py -3.11 -m pytest AGY2_FundAdvisory/tests/test_e2e_gui_render.py -v
```

### 2. 人工检查清单与反作弊红线
- 检查 `app_gui.py` 中无 `time.sleep`；
- 检查 `app_gui.py` 中无硬编码 `"现金分红·限额买500"`；
- 检查 Tab 3 中 `calculate_stock_overlap_matrix()` 使用 `overlap_res["max_non_diag_unexcused"]` 与 `alerts`，标准组合绝不误报黄色伪分散警告；
- 检查顶部 4 张大宽卡在 1080p 屏幕下无 `...` 截断。
