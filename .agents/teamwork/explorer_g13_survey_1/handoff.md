# G13 调研报告：痛点 1（首屏秒开与因子进化缓存）与痛点 4（回测图表遮挡与去伪打假）

## 1. Observation (直接观察事实与精确代码证据)

### 1.1 痛点 1：首屏主线程严重阻塞与重型计算链剖析

在 `AGY2_FundAdvisory/app_gui.py` 与 `AGY2_FundAdvisory/advisory_engine.py` 中，直接观察到以下阻塞代码路径：

1. **首屏同步双重实例化雷达引擎与重复遗传算法演化**：
   - `AGY2_FundAdvisory/app_gui.py` 第 2720 行：
     ```python
     sentry = ActiveRiskSentry()
     # ...
     sentry_rep = sentry.inspect_portfolio(...)  # L2740
     ```
     在 `AGY2_FundAdvisory/advisory_engine.py` 第 1876 行 `ActiveRiskSentry.inspect_portfolio` 内部：
     ```python
     radar_engine = OpportunityRadarEngine()
     radar_dynamic = radar_engine.dynamic_metrics or {}
     ```
     而在 `advisory_engine.py` 第 823-825 行 `OpportunityRadarEngine.__init__` 内部：
     ```python
     self.evolver = OnlineHeuristicFactorEvolver()
     self.evolved_result = self.evolver.evolve_factor_weights()  # 触发 32 种群 x 15 代遗传算法演化！
     self.factor_weights = self.evolved_result["weights"]
     ```
   - 随后在 `app_gui.py` 第 2810 行，`with wing_expander:`（即使设置了 `expanded=False`，Streamlit 服务端仍无条件执行其上下文内部代码）：
     ```python
     radar_engine = OpportunityRadarEngine()  # 第二次实例化！又跑了一遍遗传算法！
     all_scanned_sectors = radar_engine.scan_all_sectors()
     ```
2. **未展开 Popover 中同步触发 12 切片推进式演化**：
   - `app_gui.py` 第 2820-2825 行：
     ```python
     with st.popover(f"🧬 因子进化: ..."):
         # 用户根本没有点击弹窗，但主线程同步执行：
         traj_data = radar_engine.evolver.get_60d_rolling_nav_and_trajectory()
     ```
     在 `advisory_engine.py` 第 746-772 行 `get_60d_rolling_nav_and_trajectory` 内部：
     ```python
     T_oos = 60
     step = 5
     num_slices = T_oos // step  # 12 个走步切片
     for s in range(num_slices):
         sub_evolver = OnlineHeuristicFactorEvolver(population_size=16, generations=5, ...)
         sub_res = sub_evolver.evolve_factor_weights(lookback_days=min(60, train_end - 25))
     ```
     连续执行了 12 次子模型遗传进化与特征张量构建，且每次请求均从内存重新计算，**没有任何磁盘或进程级持久化缓存**！
3. **主线程同步串行外发网络请求**：
   - `app_gui.py` 第 2730 行：`fetch_realtime_fund_quote(_c, use_cache=True)` 在循环中遍历持仓基金。
   - `app_gui.py` 第 2840 行：`news_res = DataLoader.fetch_realtime_market_news_and_catalysts()`，同步请求东财快讯/新浪资讯。
   - `app_gui.py` 第 3016 行：`arb_sensors = DataLoader.fetch_etf_feeder_arbitrage_sensors(use_cache=True)`。
   - `app_gui.py` 第 3040 行：`DataLoader.fetch_options_implied_volatility_sensors(use_cache=True)`。
   - `app_gui.py` 第 3065 行：`PortfolioManager.evaluate_all_qdii_fx_arbitrage()`。
4. **刺眼的右侧空白列与伪交易总开关按钮**：
   - `app_gui.py` 第 2786-2803 行：
     ```python
     col_wing_exp, col_wing_btn = st.columns([8.2, 1.8])
     with col_wing_btn:
         if st.button(act_btn_label, key="btn_master_action_switch", ...):
     ```
     右侧 18% 宽度的按钮切走了横向空间，当左侧展开时下方留下高达 850px 的纯白空洞；且按钮包含「查看锁仓保护 / 查看今日调仓单 / 检视持仓账本」等伪柜台控制指令。
5. **双翼折叠框内严重嵌套 5 大臃肿模块**：
   - ① 第 2887-2919 行：嵌套的晨报与牛熊拐点对照尺（文字拥挤重叠穿模）；
   - ② 第 2993-3011 行：嵌套的「查看全市场 14 大赛道量化温度计总表」；
   - ③ 第 3013-3034 行：嵌套的「场内ETF与场外联接 14:45 尾盘折溢价套利感知」；
   - ④ 第 3036-3058 行：嵌套的「50ETF与300ETF认沽期权隐含波动率防暴跌哨」；
   - ⑤ 第 3060-3082 行：嵌套的「跨境QDII溢价与外汇期货锁汇成本套利精算」；
   - 并在第 2963 行、3126 行、3202 行、3246 行堆满了「+ 入备选池」、「一键批量锁定」、「择机置换」、「平衡赛道敞口」、「穿透到底层」等 8+ 处伪操作与跨区跳转按钮。

---

### 1.2 痛点 4：Tab 3 回测图表文字遮挡、硬加 Alpha、基准失真与后视镜偏差剖析

在 `AGY2_FundAdvisory/app_gui.py`、`AGY2_FundAdvisory/strategy_bridge.py` 及底层行情数据中，直接观察到以下事实：

1. **Plotly 图例框盖死净值曲线与文字碰撞**：
   - `AGY2_FundAdvisory/app_gui.py` 第 6776-6786 行：
     ```python
     fig_nav.update_layout(
         title=f"2018-2026 全周期累计净值对比 (起始归一化 1.000)",
         margin=dict(t=40, b=10, l=10, r=10),
         legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
     )
     apply_theme_to_plotly_figure(fig_nav)  # L6785 在 update_layout 之后调用！
     ```
   - 在 `app_gui.py` 第 1841-1846 行 `apply_theme_to_plotly_figure` 内部：
     ```python
     legend=dict(
         font=dict(color=th["text_primary"]),
         bgcolor=th["bg_surface"],     # 覆盖了背景色为不透明纯色！
         bordercolor=th["border_subtle"]
     ),
     margin=dict(l=10, r=10, t=30, b=10) # 强行将顶部边距压缩至仅 30px！
     ```
   - 因为包含【主实盘账本】(6只标的)(理论+12.89%)、场外实盘校准、沪深300、红利低波、纯债指数等多个长字符串图例，Plotly 空间不足自动向下折行至绘图区内部（y=2.4~2.7 区间），以不透明白色背景长方形盖住了 2024 至 2026 年关键走势。
   - 同时，第 6764-6774 行 `fig_nav.add_vrect(..., annotation_position="top left")` 在绘图区顶部直接标注「去杠杆熊市、核心资产牛市、盲测金库」等 7 个文本，与净值最高点（y=2.8）直接碰撞粘连。
2. **每天硬加固定正 Alpha（人为加分造假）**：
   - `AGY2_FundAdvisory/strategy_bridge.py` 第 4927-4930 行 `build_custom_portfolio_backtest` 内部：
     ```python
     r_arr = np.zeros(n_days)
     r_arr[1:] = s_arr[1:] / np.maximum(s_arr[:-1], 1e-8) - 1.0
     r_arr[1:] += (alpha_ann / 250.0)  # <-- 铁证：无论涨跌，每天硬加 1.0%~4.5% 年化常数 Alpha！
     port_ret += fw * r_arr
     ```
     在 2145 个交易日（约 8.5 年）的复利累乘下，凭空凭常数凭空制造了超过 35%~45% 的无风险虚假超额收益，将真实的震荡走势强行拉成了一条 45 度向上直冲的“旱地拔葱线”。
3. **基准指数日度真实性与映射失真**：
   - `AGY2_FundAdvisory/strategy_bridge.py` 第 164 行：
     ```python
     BENCHMARK_INDICES_MAP: Dict[str, Dict[str, str]] = {
         # ...
         "纯债指数": {"col": "930609", "color": "#059669", "dash": "solid"},
     }
     ```
     代码将「纯债指数」映射到了 `930609`（中证纯债债券型基金指数，CAGR 仅 3.23%），而非标准公募基准 `H11009`（中证综合债全收益指数，CAGR 4.81%）。
   - 经对 `data/processed/aligned_matrix_total_return.parquet` 实际物理探针（2145 行，2018-01-02 至 2026-11-06）：
     - `H11009`：起始 168.00 -> 最新 251.5025，年化 CAGR 为 **+4.81%**，非零波动日达 2069/2144 天，是完全具备日度真实波动的官方全收益指数，不存在线性插值死线；
     - `H30269`：起始 9172.96 -> 最新 11182.31，年化 CAGR 为 **+2.34%**（2018 年熊市回撤 -20.49%，2020 年 -4.00%，2024 年反弹 +16.60%）；
     - `H00922`（中证红利全收益）：起始 6932.76 -> 最新 12030.78，年化 CAGR 为 **+6.64%**；
     - `AU9999`（黄金）：起始 382.39 -> 最新 1473.13，年化 CAGR 为 **+17.02%**；
     - `SPX_CNY`（纳斯达克/标普人民币）：起始 2695.81 -> 最新 7465.21，年化 CAGR 为 **+12.60%**。
4. **静态持仓回测后视镜幸存者效应**：
   - 当回测目标选为当前实盘账本（如 main_live）时，组合中包含了 30.8% 的黄金（000216）和 19.5% 的纳指（017436）。
   - 用户站在 2026 年配置了这两只近年来大涨的资产，系统却将该静态权重直接穿越回 2018 年回测，导致组合 8 年年化高达 +12.89%，让散户产生“过去 8 年我能稳赚 185%”的严重后视镜幻觉；界面上完全缺乏后视镜警示，且未提供样本外动态策略对照。

---

## 2. Logic Chain (推演逻辑链与因果溯源)

### 2.1 痛点 1：首屏从 4000ms+ 到 <150ms 极速秒开的工程逻辑链

```
[Observation]
1. 首屏渲染时，Python 解释器在主线程同步调用 render_dual_wing_advisory_dashboard。
2. 即使 expander 折叠，内部 2 次 OpportunityRadarEngine()、12 次 Walk-Forward 遗传算法、3 个网络接口与 4 个套娃面板无条件执行。
     │
     ▼ [Reasoning]
1. 顶部提示条的业务本质只是给用户一句话参谋结论（是否锁仓、是否吃息、是否空仓）。这完全可以通过内存中现成的 snapshot 与 pm.holdings 在 1ms 内纯计算得出，根本不需要雷达引擎和网络请求！
2. 机会雷达与因子进化的真实使用场景是低频研究。用户在首页浏览账本和建仓时并不需要每次都重新跑一次遗传进化算法；近 60 日滚动演化轨迹在盘后完全是确定性静态结果。
3. 嵌套的 4 个深度工具（14赛道总表、14:45折溢价、期权IV、QDII锁汇）属于专业级穿透分析，应按职责归位至 Tab 4 穿透工具二级选项卡中。
     │
     ▼ [Engineering Solution]
1. 首屏顶部投顾参谋条彻底改为纯内存计算（基于 pm.holdings 的 holding_days、share_class 与 snapshot 的 erp_percentile），耗时 < 1ms。
2. 删除 col_wing_btn 及其红色按钮，提示条改为 100% 全宽 expander。
3. 在 advisory_engine.py 中实装 data/cache/factor_evolution_cache.json（TTL 12小时）。只有当用户点开 Popover 并显式点击「🔄 刷新」时才重算，首屏加载时直接 0ms 读取磁盘缓存或静默占位。
4. 将 4 大深度工具移至 Tab 4，牛熊拐点尺移至 Tab 1，首屏展开后仅保留高度 <=220px 的 Top 3 赛道卡与极简风险提示。
```

### 2.2 痛点 4：回测图文字防遮挡与去伪打假的工程逻辑链

```
[Observation]
1. apply_theme_to_plotly_figure 强制覆盖了 margin(t=30) 与 legend(bgcolor=不透明)，导致长图例被压入绘图区内部盖住曲线。
2. strategy_bridge.py 第 4929 行写死了 r_arr[1:] += (alpha_ann / 250.0)，无论当年行情如何每天硬加正 Alpha。
3. BENCHMARK_INDICES_MAP 中纯债指数配置为 930609，且实盘账本包含 50%+ 黄金与纳指等后视镜高收益标的。
     │
     ▼ [Reasoning]
1. 视觉空间几何：将 margin(t=75) 扩大，并将 legend 锚定在图表外上方 y=1.06、背景透明，使得绘图区顶部完全留空给净值曲线；同时将牛熊切片文字移至绘图区顶部边缘并淡化字体颜色（font_size=9, muted color），可彻底消除碰撞。
2. 真实量化防线：投顾系统必须实事求是。彻底删除 r_arr[1:] += (alpha_ann / 250.0)，真实反映资产历史被动持有收益；将纯债指数映射修正为 H11009，直接从 aligned_matrix_total_return.parquet 读取日度序列。
3. 预期管理与合规透明：针对静态账本回测，必须明确告知投资者这是“后视镜静态回溯”，并提供一键同屏对比【全天候滚动样本外动态策略曲线】（C3 标杆），客观还原真实实盘期望。
```

---

## 3. Caveats (边界、假设与潜在风险)

1. **测试用例对旧组件名与断言的依赖**：
   - 部分测试（如 `tests/test_m3_full_integration_apptest.py` 第 32 行 `assert "btn_add_radar_pool_" in gui_text`）对被删除的旧按钮名称存在静态字串匹配。实施时必须按指示同步更新非只读测试用例断言。
2. **纯只读红线契约严格保留**：
   - 四个裁判文件 `judge_engine.py`、`holdout_vault.py`、`AGENT_SPEC.md`、`tests/test_infra.py` 必须保持绝对只读（SHA256 不可改变）。
   - 本次回测图表改造仅在 `strategy_bridge.py` 的 `build_custom_portfolio_backtest` 与 `BENCHMARK_INDICES_MAP`，绝不修改裁判文件的评判逻辑。
3. **Streamlit Expander 执行模型限制**：
   - Streamlit 的 `st.expander` 在 Python 端无论展开与否都会执行其内部 Python 语句。因此，首屏提速的关键在于：必须确保展开框内部的代码本身是毫秒级轻量的（读取 10KB 本地 JSON 缓存，绝不发 HTTP 请求、绝不现场执行遗传算法），或者通过 `st.toggle` 按需渲染重型图表。

---

## 4. Conclusion (具体实施设计与落地行动清单)

### 4.1 痛点 1 具体实施方案（修改 `app_gui.py` 与 `advisory_engine.py`）

#### 实施点 1.1：`app_gui.py` 顶部投顾参谋条纯内存化与全宽重构
- **目标位置**：`AGY2_FundAdvisory/app_gui.py` 第 2712-2804 行。
- **具体修改**：
  1. 彻底删除 `sentry.inspect_portfolio()` 中的全量外部请求与重复 radar 初始化；
  2. 采用纯内存秒级判断（耗时 < 1ms）：
     ```python
     # 纯内存毫秒级快速风控与参谋判断
     lock_funds = []
     c_free_funds = []
     for c, h in pm_instance.holdings.items():
         h_days = getattr(h, "holding_days", 30)
         if h_days < 7:
             lock_funds.append((c, getattr(h, "fund_name", c)))
         elif str(getattr(h, "share_class", "A")).upper() == "C" and h_days >= 30:
             c_free_funds.append((c, getattr(h, "fund_name", c)))

     erp_pct = float(snapshot_dict.get("erp_percentile", 82.0))
     bias_val = float(snapshot_dict.get("c300_bias_20", snapshot_dict.get("bias_20", -2.07)))

     if lock_funds:
         act_status_icon = "🔴"
         act_title = f"今日投顾参谋：持仓含 {len(lock_funds)} 只未满 7 天标的，赎回需扣 1.5% 惩罚费，调仓算法已自动为您避开卖出 ｜ 点击展开市场机会与持仓体检"
     elif c_free_funds:
         act_status_icon = "🟡"
         act_title = f"今日投顾参谋：检测到 {len(c_free_funds)} 只 C 类份额持有已满 30 天免赎回费，建议择机置换为 A 类节省销售服务费 ｜ 点击展开市场机会与持仓体检"
     elif len(pm_instance.holdings) == 0:
         act_status_icon = "🚀"
         act_title = f"今日投顾参谋：宏观 ERP 处于黄金击球区 ({erp_pct:.1f}%)，建议一键启动新资建仓 ｜ 点击展开市场机会与配置指引"
     else:
         act_status_icon = "🟢"
         act_title = "今日投顾参谋：持仓资产结构健康，安全垫充沛，今日安心吃息 ｜ 点击展开市场机会与持仓体检"
     ```
  3. **彻底删除 `col_wing_btn` 及其内部的 `btn_master_action_switch`**：
     直接以 100% 全宽渲染折叠面板：
     ```python
     wing_expander = st.expander(f"{act_status_icon} {act_title}", expanded=False)
     ```
     彻底消灭右侧 18% 宽度的空白竖柱死区！

#### 实施点 1.2：因子进化与 60 日轨迹磁盘缓存机制
- **目标位置**：`AGY2_FundAdvisory/advisory_engine.py` 第 746-826 行。
- **缓存文件**：`data/cache/factor_evolution_cache.json`（TTL 12 小时）。
- **具体修改**：
  在 `OnlineHeuristicFactorEvolver` 中实装磁盘读写逻辑：
  ```python
  def _get_cache_file_path(self) -> Path:
      cache_dir = Path(WORKSPACE_ROOT) / "data" / "cache"
      cache_dir.mkdir(parents=True, exist_ok=True)
      return cache_dir / "factor_evolution_cache.json"

  def evolve_factor_weights(self, force_refresh: bool = False, **kwargs) -> Dict[str, Any]:
      cache_f = self._get_cache_file_path()
      if not force_refresh and cache_f.exists():
          try:
              with open(cache_f, "r", encoding="utf-8") as f:
                  cached_obj = json.load(f)
              if time.time() - cached_obj.get("timestamp", 0) < 43200: # 12小时有效
                  res = cached_obj.get("evolved_result")
                  if res:
                      self._cached_evolution = res
                      return res
          except Exception:
              pass
      # 缓存未命中或超时才真实跑遗传算法
      # ... 跑完后将 evolved_result 写入缓存 ...
  ```
  在 `get_60d_rolling_nav_and_trajectory(self, force_refresh: bool = False, **kwargs)` 中同样接入该缓存，磁盘读取仅耗时 1ms！
  在 Popover 弹窗中加入一个小型刷新按钮：
  ```python
  if st.button("🔄 重新演化因子与60日轨迹", key="btn_refresh_factor_evolution"):
      radar_engine.evolver.evolve_factor_weights(force_refresh=True)
      radar_engine.evolver.get_60d_rolling_nav_and_trajectory(force_refresh=True)
      st.rerun()
  ```

#### 实施点 1.3：从首屏双翼折叠框彻底移出 5 大臃肿模块与伪按钮
- **彻底移出**：
  - 牛熊拐点尺：从双翼看板删除，仅在 Tab 1 定投模式保留，并调整宽度；
  - 14赛道总表、14:45尾盘折溢价、认沽期权IV哨、QDII锁汇套利：从双翼看板彻底移入 Tab 4「穿透工具」的二级选项卡（例如 `dock_tab_etf_arb`、`dock_tab_options`、`dock_tab_qdii`）；
  - 删除 Top 3 赛道卡片下方的 3 个「➕ 入备选池」按钮，卡片直接静态展示优选基金名称与 6 位代码；
  - 删除右翼卡片中的「一键批量锁定这2只标的调仓下界」、「择机置换」、「穿透到底层」等所有按钮，改为极简只读文本列表。
  - 双翼展开后仅为干净利落的一排「左翼 Top 3 赛道卡 + 右翼极简风险列表」，高度稳定控制在 220px 以内。

---

### 4.2 痛点 4 具体实施方案（修改 `strategy_bridge.py` 与 `app_gui.py`）

#### 实施点 2.1：Tab 3 Plotly 图表布局与防遮挡修复
- **目标位置**：`AGY2_FundAdvisory/app_gui.py` 第 6754-6786 行。
- **具体修改**：
  1. 将图表顶部边距扩大至 `margin=dict(t=75, b=10, l=10, r=10)`；
  2. 将图例置于图表外部上方，水平排列且背景透明：
     ```python
     legend=dict(
         orientation="h",
         yanchor="bottom",
         y=1.06,
         xanchor="left",
         x=0,
         bgcolor="rgba(0,0,0,0)"
     )
     ```
  3. 确保在调用 `apply_theme_to_plotly_figure(fig_nav)` 之后，或者在该函数内部保留上述自定义 `margin` 与 `legend` 设置，严禁被 `margin(t=30)` 和纯色背景覆盖！
  4. 将 7 个牛熊切片文字标注调淡并移至顶部边缘：
     ```python
     fig_nav.add_vrect(
         # ...
         annotation_position="top left",
         annotation_font_size=9,
         annotation_font_color=active_th.get("text_muted", "rgba(148, 163, 184, 0.55)")
     )
     ```
     彻底根除文字与曲线的重叠！

#### 实施点 2.2：彻底删除 `strategy_bridge.py` 人工加分代码
- **目标位置**：`AGY2_FundAdvisory/strategy_bridge.py` 第 4927-4930 行。
- **具体修改**：
  ```python
  # 修改前:
  r_arr = np.zeros(n_days)
  r_arr[1:] = s_arr[1:] / np.maximum(s_arr[:-1], 1e-8) - 1.0
  r_arr[1:] += (alpha_ann / 250.0)  # <-- 删除此行！
  port_ret += fw * r_arr

  # 修改后:
  r_arr = np.zeros(n_days)
  r_arr[1:] = s_arr[1:] / np.maximum(s_arr[:-1], 1e-8) - 1.0
  port_ret += fw * r_arr
  ```
  清零任何人工加分，严格以真实全收益指数为准！

#### 实施点 2.3：基准指数映射对齐至官方全收益 `H11009`
- **目标位置**：`AGY2_FundAdvisory/strategy_bridge.py` 第 157-167 行 `BENCHMARK_INDICES_MAP`。
- **具体修改**：
  ```python
  BENCHMARK_INDICES_MAP: Dict[str, Dict[str, str]] = {
      "沪深300": {"col": "H00300", "color": "#64748b", "dash": "dash"},
      "中证500": {"col": "H00905", "color": "#0284c7", "dash": "dot"},
      "中证1000": {"col": "H00852", "color": "#8b5cf6", "dash": "dot"},
      "科创50": {"col": "STAR50_STITCH", "color": "#ec4899", "dash": "dashdot"},
      "红利低波": {"col": "H30269", "color": "#d97706", "dash": "dash"},
      "中证红利": {"col": "H00922", "color": "#ea580c", "dash": "dot"},
      "纯债指数": {"col": "H11009", "color": "#059669", "dash": "solid"}, # 修正为 H11009 综合债全收益 (CAGR +4.81%)
      "国内黄金": {"col": "AU9999", "color": "#eab308", "dash": "dashdot"},
      "股债50/50": {"col": "BENCHMARK_50_50", "color": "#3b82f6", "dash": "dash"},
  }
  ```
  在 `build_custom_portfolio_backtest` 中，`code_to_col_alpha` 的纯债标的（如 `002351`）索引列统一改为 `H11009`，从 `aligned_matrix_total_return.parquet` 中直接读取日度收盘序列归一化，严禁线性插值！

#### 实施点 2.4：后视镜幸存者效应明确提示卡与样本外动态策略对照
- **目标位置**：`AGY2_FundAdvisory/app_gui.py` 第 6701 行上方。
- **具体修改**：
  当 `choice_kind == "ledger"`（回测目标为当前实盘账本）时：
  1. 若持仓中包含黄金（`000216` 等）或纳指/海外（`017436` 等），自动在默认勾选的对标基准中添加 `"国内黄金"`；
  2. 在全周期净值曲线正上方渲染醒目的警示提示卡：
     ```python
     safe_markdown_html("""
     <div style="background: rgba(245, 158, 11, 0.08); border-left: 3px solid var(--accent-primary); padding: 8px 14px; border-radius: 6px; margin-bottom: 12px; font-size: 12px; color: var(--text-primary);">
         <b>⚠️ 当前持仓静态权重历史回溯（含历史后视镜权重效应，非滚动样本外实盘记录）</b><br>
         <span style="color: var(--text-secondary); font-size: 11px; line-height: 1.5;">
             本回测基于当前实盘持仓的静态配置权重，反向穿越回溯至 2018 年并进行每日再平衡推演。因当前持仓中包含了近几年涨幅领先的黄金或跨市场资产，存在已知的历史后视镜权重效应与幸存者偏差，不代表历史上按滚动策略真实运行的样本外业绩。
         </span>
     </div>
     """)
     ```
  3. 提供一键切换开关同屏对比动态策略：
     ```python
     tgl_compare_oos = st.toggle("🔄 同屏对比【全天候滚动样本外动态策略曲线】(C3 标杆)", value=False, key="tgl_compare_oos_dynamic")
     if tgl_compare_oos:
         base_bt = StrategyBridge.get_backtest_nav_for_tier(tier="C3")
         fig_nav.add_trace(go.Scatter(
             x=base_bt['date'],
             y=base_bt['strategy_nav'],
             mode='lines',
             name='全天候滚动样本外动态策略 (C3)',
             line=dict(color='#8b5cf6', width=2.0, dash='dashdot')
         ))
     ```

---

## 5. Verification Method (独立可复现核验指令)

实施智能体完成代码修改后，应通过以下具体命令与断言进行分层验证：

### 5.1 痛点 1 验证命令与断言
1. **因子进化缓存文件验证**：
   ```powershell
   py -3 -c "from advisory_engine import OnlineHeuristicFactorEvolver; evolver = OnlineHeuristicFactorEvolver(); res = evolver.evolve_factor_weights(); print(res['status']); traj = evolver.get_60d_rolling_nav_and_trajectory(); print('dates:', len(traj['dates']))"
   ```
   检查 `data/cache/factor_evolution_cache.json` 是否生成，且第二次运行时耗时小于 5ms。
2. **首屏渲染零重型计算断言**：
   在 `AGY2_FundAdvisory/app_gui.py` 的 `render_dual_wing_advisory_dashboard` 前后打上时间戳 `time.perf_counter()`，确认纯内存提示条在无点击展开时主线程耗时 `< 20ms`（首屏整体 `< 150ms`）。

### 5.2 痛点 4 验证命令与断言
1. **无人工加分验证**：
   检查 `AGY2_FundAdvisory/strategy_bridge.py` 中 `alpha_ann` 是否已被移除，运行：
   ```powershell
   py -3 -c "import inspect; from strategy_bridge import StrategyBridge; src = inspect.getsource(StrategyBridge.build_custom_portfolio_backtest); assert 'alpha_ann / 250' not in src, '仍然存在硬加Alpha造假代码！'; print('Verified: No artificial alpha!')"
   ```
2. **纯债指数基准数据验证**：
   运行探针检查 `H11009` 数据是否直接从 `aligned_matrix_total_return.parquet` 正确提取且真实年化收益在 4.5%~5.0% 区间：
   ```powershell
   py -3 -c "from strategy_bridge import StrategyBridge, BENCHMARK_INDICES_MAP; assert BENCHMARK_INDICES_MAP['纯债指数']['col'] == 'H11009'; df = StrategyBridge.build_custom_portfolio_backtest({'002351': 1.0}); print('纯债基准CAGR:', (df['bm_nav_纯债指数'].iloc[-1] ** (252.0 / len(df)) - 1.0) * 100.0)"
   ```

### 5.3 全量自动化测试回归
运行全量四大基线测试套件，确保 100% 绿灯（50 passed）：
```powershell
py -3 -m pytest tests/test_infra.py tests/test_adv_final_closure.py tests/test_g3_evolution_loop.py tests/test_gui_multi_ledger_stress.py
```
并在 `tests/test_infra.py` 物理只读裁判文件审计中确认 0 修改，哈希完全吻合。
