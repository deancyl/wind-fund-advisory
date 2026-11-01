# AGY2 Web GUI (app_gui.py) 阶段二重构深度调研与实施架构报告

## 1. Observation (事实与直接观察)

本调研对 `d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py`（全量 2,486 行）、`strategy_bridge.py`、`portfolio_manager.py`、`ORIGINAL_REQUEST.md`（阶段二要求）及 `tests/` 全量测试套件进行了只读深潜排查。直接观察到的事实如下：

### 1.1 `time.sleep` 的出现位置与代码片段
在 `app_gui.py` 中，共有 4 处 `time.sleep` 调用，全部集中在步骤二（现场推演过程容器）中：
- **行 714**：`time.sleep(0.35)` —— Step 1/4 全市场海选漏斗假延迟；
- **行 724**：`time.sleep(0.35)` —— Step 2/4 宏观与衍生品定调假延迟；
- **行 735**：`time.sleep(0.40)` —— Step 3/4 跨牛熊回测压力精算假延迟；
- **行 756**：`time.sleep(0.35)` —— Step 4/4 交易摩擦与执行清单假延迟。
累计假延迟耗时：`0.35 + 0.35 + 0.40 + 0.35 = 1.45s`。此外：
- **行 12**：`import time`；
- **行 709**：`sim_t0 = time.time()`；
- **行 760**：`sim_elapsed = max(1.22, min(1.78, round(time.time() - sim_t0, 2)))` 强制将耗时卡在 1.22~1.78s。

### 1.2 顶部全局看板结构与省略号截断（`...`）根因
当前顶部状态栏占据了屏幕纵向超过 350px，分为 3 层纵向堆叠：
1. **第 1 层（行 305-314）**：
   - 带有蓝色左边框的独立 HTML 横幅，分别展示 `📅 调仓网格倒计时：{rebal_grid['countdown_display']}` 与 `🚨 破位预警：{rebal_grid['emergency_warning']}`。
2. **第 2 层（行 316-439）**：
   - 使用 `st.columns(7)` 强制将可用宽度切割为 7 窄列：
     - `status_col1`: 申赎时钟
     - `status_col2`: AI 策略大脑
     - `status_col3`: 沪深300 (实时)
     - `status_col4`: 股债性价比
     - `status_col_liq`: 宏观流动性
     - `status_col5`: 今日预估浮盈亏
     - `status_col6`: 全组合总资产
   - **CSS 样式根因（行 96-136）**：
     ```css
     .main-metric-card {
         min-height: 94px;
         height: 94px;
         padding: 8px 10px;
         ...
     }
     .metric-card-title {
         font-size: 13px; font-weight: 600; color: #334155;
         white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
     }
     .metric-value-huge {
         font-size: 15px; font-weight: 700;
         white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
     }
     .metric-card-sub {
         font-size: 11px; color: #64748b;
         white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
     }
     ```
   - 在 1080p 屏幕（扣除侧边栏 ~300px，主视口约 1620px）下，7 列平均每列仅分摊约 200px（再扣除 padding/gap 实际可用宽度不足 170px）。
   - 副标题文本例如 `MA20: 3,920 ｜ MA60: 3,850`、`DR007: 1.50% (偏离 +0.0bp)`、`可用: ¥10,000.0 ｜ 在途: ¥0.0` 字符数达 25~35 字符，在 170px 下必然发生溢出，被 CSS 的 `text-overflow: ellipsis;` 强制截断为 `...`。
3. **第 3 层（行 443-466）**：
   - `col_rt_info, col_rt_btn = st.columns([7.8, 2.2])`
   - 左侧渲染长条形宏观雷达：`st.info(f"💡 实时研判：{mkt_st} ｜ 🌊 宏观雷达：DR007 {dr_val:.2f}%，期权IV {opt_iv:.1f}%，IC贴水 {ic_basis:.1f}% ({deriv_tip})")`；右侧放置 `🔄 刷新盘中实时估值与大盘点位` 按钮。

### 1.3 写死“限额买500”或“现金分红·限额买500”的具体位置
- **行 1202**：
  ```python
  if it.get("has_split"):
      guide_action = "现金分红·限额买500"  # <--- 硬编码写死！
  elif it.get("require_cash_dividend"):
      guide_action = "现金分红·满期免赎A"
  elif it.get("share_class") == "C":
      guide_action = "红利再投·弹性进攻C"
  else:
      guide_action = "长钱持有·满期免赎A"
  ```
- **行 1090**：在步骤二第四个白盒抽屉说明文案中硬编码：`- 限额标的 (如 050025 限 500 元) 自动拆单并路由至备选 (001071)<br>`。
- **行 1225**：在手机下单小抄生成中硬编码了固定文案。
- **阶段一实际接口对比**：阶段一在 `portfolio_manager.py`（行 3247、3291、3306）中已输出动态生成的 `action_guide`（如 `单日限额¥500·已拆单`、`承接超额·不限购正常买`）以及 `blueprint.get("dca_plan")`。`app_gui.py` 之前直接丢弃了阶段一的 `it["action_guide"]`，用常量覆盖。

### 1.4 当前 Tabs 导航结构与 R3 要求差距
当前 `app_gui.py`（行 501-506）的声明为：
```python
tab_brain, tab_backtest, tab_ledger, tab_toolbox = st.tabs([
    "🧭 AI 投顾大脑与今日建议",
    "📈 策略胜率、回测与风控档案",
    "💼 我的持仓账本与接管向导",
    "🔍 组合穿透诊断、对账与工具箱"
])
```
与需求 R3 的差距：
1. **职责混杂**：当前 Tab 1 内嵌了 `gui_scenario_mode_v2`（行 590-597）下拉框：“🌱 场景一：【从 0 开始现场推演建仓】”与“🔄 场景二：【存量组合诊断与调仓建议】”。用户在新资金建仓与存量日常看盘之间需要反复切下拉框，心智模型割裂。
2. **层级失序**：存量持仓的接管录入在 Tab 3，而存量调仓建议在 Tab 1 场景二，账本与操作分离。
3. **未装配阶段一算法**：Tab 1 场景二未调用阶段一新实现的 `StrategyBridge.evaluate_today_rebalance_suitability`（今日是否适合调仓裁决卡）和 `StrategyBridge.simulate_rebalance_modes_and_consequences`（温和 vs 强行双模式调仓推演及四大后果账单）。
4. **面板默认展开问题**：Tab 3 的持仓接管向导（行 1850）虽然设了 `expanded=(len(pm.holdings) == 0)`，但编辑修改表格（行 2079）直接平铺在页面上占用大量垂直空间，FIFO 批次透视（行 2145）固定为 `expanded=False`。

### 1.5 既有自动化测试套件的兼容性与雷区发现
运行 pytest 结果与排查事实：
1. `tests/test_milestone_phase1_r1_r5.py`：全量 11 项核心算法测试 **100% PASS**（13.89s），阶段一后端闭环完全就绪。
2. `tests/test_infra.py`：4 个裁判基建文件测试 **100% PASS**（5.50s），未被修改。
3. `tests/test_portfolio_manager.py` + `tests/test_strategy_bridge.py`：34 项单元测试 **100% PASS**（39.97s）。
4. **【重要雷区】`tests/test_adversarial_m3_challenger2.py`**：
   该文件是 Milestone 3 编写的旧挑战测试，其中硬编码了对旧版 `app_gui.py` 内部 AST/正则的断言：
   - 行 43-78 `test_sleep_delay_cadence_and_non_repetition`：**用 AST 静态断言 `app_gui.py` 必须包含 4 个 sleep 且数值必须为 `[0.35, 0.35, 0.40, 0.35]`！**
   - 行 159-209 `test_top_seven_metric_cards_compact_and_no_truncation`：**用正则断言必须包含 `st.columns(7)` 且必须包含 7 个特定名称与 7 个 `ⓘ` 标签！**
   - 行 504 `test_apptest_scenario_two_rebalance_table`：**断言 `gui_scenario_mode_v2` 下拉框存在！**
   当阶段二根据 R1 彻底删除 `time.sleep` 并按 R2 将 7 窄卡瘦身为 4 宽卡、按 R3 去除 Tab 1 场景下拉框时，该旧测试文件必然触发断言失败。该测试文件不属于 4 个只读裁判基建文件（4 个只读文件为 `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`），实施时需由测试员同步升级或对齐阶段二验收标准。
5. **【日历时钟雷区】`tests/test_e2e_gui_render.py` 行 112**：
   `test_bug3_pre_market_trading_clock_and_signal_harmony` 在周日执行时，因未 patch `datetime.now()` 的日期，导致 `evaluate_intraday_signal(current_time_str="08:21")` 判定为非交易日休市而抛出 `assert '盘前未开市' in '非交易日休市'`。测试用例在行 130 对 Saturday 进行了 mock，但遗漏了 Monday。

---

## 2. Logic Chain (推理链条与架构推演)

基于上述直接观察，推导阶段二重构的严密逻辑链条如下：

### 2.1 顶部看板由 3 层 7 窄卡压缩为“1 行 4 宽卡”的推理
- **依据**：观察 1.2 显示，7 列分栏下每列宽度仅 ~170px，配合 CSS 强制 `nowrap + ellipsis` 是造成省略号截断的物理根因；且 3 层纵向堆叠浪费了首屏首要黄金视口。
- **推理**：
  1. 将第 1 层的“调仓网格倒计时”融合入卡片 1 的副标题（`距下次常规网格日 X 天`）；
  2. 将第 1 层的“破位预警”与第 3 层的“宏观雷达攻防”融合入卡片 2 的副标题（`📈破 4,141 进攻 ｜ 🛡️跌 3,846 防守`），点击/悬停 `ⓘ` 即可查看沪深300现价与均线详情；
  3. 将第 2 层的“股债性价比”与“宏观流动性”合并为卡片 3（【🌡️ 估值与资金面温度 ⓘ】），主标题用大白话“估值极便宜 · 资金充裕”，副标题“股票性价比高 ｜ 央妈呵护”，所有 ERP 分位、DR007、期权 IV、IC 贴水专业指标全部收纳进 `ⓘ` 悬停提示中，主卡片零黑话；
  4. 将第 2 层的“今日预估浮盈亏”与“全组合总资产”合并为卡片 4（【💰 我的总资产与今日预估 ⓘ】），主值展示总资产，副值展示今日预估盈亏与涨跌幅；在右侧放置紧凑的 `🔄 刷新实时行情` 按钮。
- **结论**：4 张宽裕卡片单列宽度扩充至 ~360-400px（增加一倍以上空间），同时彻底消除 CSS 溢出截断，达成 1080p 零省略号、零横向滚动条。

### 2.2 彻底消除 `time.sleep` 的无感平滑推演推理
- **依据**：观察 1.1 显示，4 处 `time.sleep` 纯属人为制造的伪假延迟（合计 1.45s），严重降低了 Web GUI 的响应速度与 Streamlit AppTest 渲染效率。
- **推理**：
  1. 阶段一已经将 DuckDB 基金筛选、Hedge 多专家权重计算、全周期净值指标计算全部优化为纯数学本地矢量化计算，实际执行耗时小于 50ms。
  2. 直接移除 4 处 `time.sleep`，让 `st.status` 与推演容器瞬间跑完真实数据逻辑；
  3. `sim_elapsed = round(time.time() - sim_t0, 2)` 直接展示真实毫秒级耗时。

### 2.3 四大主导航 Tab 重构与职责单一化推理
- **依据**：观察 1.4 显示，原设计将新资金从 0 建仓与存量持仓诊断混合在 Tab 1，且存量账本散落在 Tab 3。
- **推理与重塑**：
  - **Tab 1：`🌱 新资金从0建仓推演`**
    - 剥离所有场景二逻辑，仅保留新资金从 0 建仓流程。
    - 步骤一：模式 A（收益率滑块 C1~C5 即拉即变）与模式 B（30 秒测评），去除“场景一/场景二”下拉框。
    - 步骤二：现场推演 4 个白盒抽屉（`expanded=False`），抽屉标题动态呈现核心量化数字摘要（如：`🔍 【Step 1 白盒：全市场 28,177 只公募基金四级漏斗海选与金牌标的】（DuckDB海选 28,177 ➔ 锁定 5 只金牌标的）`）；保留 5 张核心结果卡与《三句话看懂本方案》三栏卡片。
    - 步骤三：9 列建仓执行单表格，第 9 列 `实操分红与限购指引` 严格绑定阶段一 `blueprint["items"]` 的动态 `action_guide`，彻底消除写死“限额买500”；当 `blueprint.get("dca_plan")` 存在时，在表格下方醒目展示《超限资金分批定投执行计划》提示条。
  - **Tab 2：`💼 我的当前持仓与今日调仓建议`**
    - 严格落地三层垂直布局：“先给今日结论 ➔ 再给调仓方案与后果 ➔ 最后看持仓账本”。
    - **第 1 层**：调用 `StrategyBridge.evaluate_today_rebalance_suitability(pm, active_tier)` 渲染醒目的红/黄/绿灯横幅与 4 胶囊四维实测结论。
    - **第 2 层**：调用 `StrategyBridge.simulate_rebalance_modes_and_consequences(pm, active_tier)` 提供单选切换（模式一：温和免伤调仓 vs 模式二：强行一步到位调仓），并排渲染 4 张《本次调仓四大真实后果量化账单》卡片（手续费直接损耗、T+2在途踏空风险、攻防与回撤变化、持有期清零后果），紧跟 9 列调仓执行单与一键执行/预案保存按钮。
    - **第 3 层**：展示实时持仓明细表，并将《✨ 零门槛导入/新增持仓向导》、《✏️ 编辑修改持仓数据》、《📦 FIFO 份额批次免赎倒计时》全部配置为 `expanded=(len(pm.holdings) == 0)`（有持仓时默认收起，无持仓时默认展开）。
  - **Tab 3：`🔍 组合深度体检与算费工具箱`**
    - 将原 Tab 4 完整平移至此，涵盖大类资产缺口图、加权行业暴露、重仓股重叠交叉检测（已在阶段一豁免双红利与限购伴生对）、底层重仓股排雷大宽表、聪明钱监控、在途对账与 A/C 算费器、场内 ETF 溢价监控。
  - **Tab 4：`📈 策略历史回测与胜率档案`**
    - 将原 Tab 2 完整平移至此，涵盖 C1~C5 档位回测曲线、水下回撤图、大类仓位变迁面积图、6 大历史风格切片明细表与历史相似行情匹配器。

---

## 3. Caveats (局限性、假设与风险预警)

1. **测试套件历史债务**：
   - `tests/test_adversarial_m3_challenger2.py` 是上个里程碑（Milestone 3）的产物，其内部包含对 4 个 `time.sleep`（行 68-73）、7 列卡片 `st.columns(7)`（行 168-171）和 `gui_scenario_mode_v2`（行 515）的硬编码静态检测。
   - 当阶段二按照新需求执行后，直接运行该测试文件会报错。建议协调测试角色将其断言升级为断言 `app_gui.py 中 time.sleep 调用为 0`、`顶部卡片为 4 宽卡`，以避免断言倒退。
2. **`cols_9` 变量名保护**：
   - 现存 `tests/test_acceptance_r1_r7.py` 行 325 通过静态正则检测 `cols_9 = [...]`，因此重构时必须保留 `cols_9 = [...]` 变量名与对应 9 个列名字段，确保既有验收测试平稳通过。
3. **Streamlit AppTest 内存消耗**：
   - 端到端 AppTest 连续跑 C1~C5 全档位需加载 DuckDB 和回测数据 5 次，在 Windows 终端下单测耗时约为 40~50 秒，建议保持 `default_timeout=60` 以上。

---

## 4. Conclusion (调查结论与重构落地代码蓝图)

### 4.1 核心结论
`app_gui.py` 阶段二重构目标非常明确，阶段一后端方法（实时限购、多级瀑布流拆单、CUSUM优胜劣汰、三色调仓适宜度裁决、双模式调仓后果精算）均已完备且通过 100% 测试，可直接无缝对接。主要工作是对前端展示层进行彻底的视觉大扫除与导航重塑。

### 4.2 具体重构实施代码蓝图 (Implementation Blueprint)

#### (1) 顶部 1 行 4 宽卡渲染模块（替换行 298-466）
```python
# -------------------------------------------------------------
# 顶部全局看板：1 行 4 宽卡 + 1 个紧凑刷新按钮 (彻底消灭省略号)
# -------------------------------------------------------------
market_status = clock.get_market_window_status()
intraday_eval = StrategyBridge.evaluate_intraday_signal()
rebal_grid = snapshot.get("rebal_grid") or StrategyBridge.get_rebalance_grid_status()
pnl_today = pm.calculate_intraday_pnl()
pnl_color = "#ef4444" if pnl_today["total_est_pnl"] >= 0 else "#10b981"
total_cur_equity = sum(h.market_value for h in pm.holdings.values()) + pm.available_cash + pm.in_transit_cash

# 动态计算双向触发线与估值温度
c300_disp = intraday_eval.get("realtime_c300", snapshot.get("c300_price", snapshot['c300']))
bias_disp = intraday_eval.get("bias_m20", snapshot['bias_20'])
m20_disp = intraday_eval.get("m20", snapshot.get("m20_price", snapshot['m20']))
m60_disp = intraday_eval.get("m60", snapshot.get("m60_price", snapshot['m60']))
surge_line = float(snapshot.get("trigger_lines", {}).get("surge_line", c300_disp * 1.012))
breakdown_line = float(snapshot.get("trigger_lines", {}).get("breakdown_line", c300_disp * 0.985))

# 宏观指标
erp_pct = snapshot.get("erp_percentile", 82.5)
erp_val = snapshot.get("erp_val", 5.82)
dr007_val = snapshot.get("dr007", 1.50)
dr007_bp = snapshot.get("dr007_spread_bp", 0.0)
opt_iv = float(snapshot.get("option_iv_pct", 19.4))
ic_basis = float(snapshot.get("ic_annualized_basis_rate", 17.9))

# 4 宽卡 + 1 紧凑刷新按钮列
top_c1, top_c2, top_c3, top_c4, top_btn = st.columns([2.4, 2.7, 2.5, 2.5, 0.9])

with top_c1:
    clock_color = '#16a34a' if market_status.is_golden_window else ('#dc2626' if market_status.is_after_market else '#0284c7')
    clock_title = "🟢 14:30黄金窗口" if market_status.is_golden_window else ("🟡 盘后已关账" if market_status.is_after_market else "🔵 盘中观察期")
    st.markdown(f"""
    <div class="main-metric-card">
        <div class="metric-card-title">
            🕒 交易时钟与窗口 
            <span title="场外公募基金每日 15:00 关账。15:00 前下单按今日未知收盘净值成交，15:00 后下单顺延至下一交易日。" style="cursor:help; color:#94a3b8; font-size:12px;">ⓘ</span>
        </div>
        <div class="metric-value-huge" style="color: {clock_color};">
            {clock_title}
        </div>
        <div class="metric-card-sub" style="color: #64748b;">
            倒计时 {market_status.countdown_str} ｜ 距网格日 {rebal_grid.get('days_to_grid', 3)} 天
        </div>
    </div>
    """, unsafe_allow_html=True)

with top_c2:
    st_name = snapshot.get('market_state', '震荡收息期')
    st_color = snapshot.get('state_color', '#16a34a')
    st.markdown(f"""
    <div class="main-metric-card">
        <div class="metric-card-title">
            🧭 市场定调与攻防线 
            <span title="沪深300现价: {c300_disp:,.1f} (MA20: {m20_disp:,.0f}, MA60: {m60_disp:,.0f}, 乖离率: {bias_disp:+.1f}%)。突破进攻线加仓弹性进攻，跌破防守线启动防守。" style="cursor:help; color:#94a3b8; font-size:12px;">ⓘ</span>
        </div>
        <div class="metric-value-huge" style="color: {st_color};">
            🟢 {st_name}
        </div>
        <div class="metric-card-sub" style="color: #475569;">
            📈破 {surge_line:,.0f} 进攻 ｜ 🛡️跌 {breakdown_line:,.0f} 防守
        </div>
    </div>
    """, unsafe_allow_html=True)

with top_c3:
    val_status = "估值极便宜 · 资金充裕" if (erp_pct >= 75 and dr007_bp <= 5) else "估值合理 · 流动性中性"
    st.markdown(f"""
    <div class="main-metric-card">
        <div class="metric-card-title">
            🌡️ 估值与资金面温度 
            <span title="真实 ERP: {erp_val:.2f}% (分位 {erp_pct:.1f}%) ｜ DR007: {dr007_val:.2f}% (偏离 {dr007_bp:+.1f}bp) ｜ 期权IV: {opt_iv:.1f}% ｜ IC贴水: {ic_basis:.1f}%" style="cursor:help; color:#94a3b8; font-size:12px;">ⓘ</span>
        </div>
        <div class="metric-value-huge" style="color: #16a34a;">
            {val_status}
        </div>
        <div class="metric-card-sub" style="color: #64748b;">
            股票性价比高 ｜ 央妈呵护
        </div>
    </div>
    """, unsafe_allow_html=True)

with top_c4:
    st.markdown(f"""
    <div class="main-metric-card">
        <div class="metric-card-title">
            💰 我的总资产与今日预估 
            <span title="总资产 = 市值 + 可用现金 (¥{pm.available_cash:,.1f}) + 在途资金 (¥{pm.in_transit_cash:,.1f})。" style="cursor:help; color:#94a3b8; font-size:12px;">ⓘ</span>
        </div>
        <div class="metric-value-huge" style="color: #0f172a;">
            ¥{total_cur_equity:,.2f}
        </div>
        <div class="metric-card-sub" style="color: {pnl_color}; font-weight:600;">
            今日预估 ¥{pnl_today['total_est_pnl']:+,.2f} ({pnl_today['total_est_pnl_pct']:+.2f}%)
        </div>
    </div>
    """, unsafe_allow_html=True)

with top_btn:
    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
    if st.button("🔄\n刷新", help="重新拉取实时净值与大盘点位", use_container_width=True, type="primary"):
        clear_realtime_cache()
        StrategyBridge._cached_snapshot = None
        StrategyBridge._cached_matrix = None
        st.rerun()
```

#### (2) Tab 1 步骤三动态限额指引修复（替换行 1201-1209）
```python
# 彻底删除写死的 "现金分红·限额买500"，动态绑定阶段一 action_guide
act_raw = it.get("action_guide") or ""
if it.get("has_split"):
    if act_raw and act_raw != "正常买入":
        guide_action = f"现金分红·{act_raw}" if it.get("require_cash_dividend") else act_raw
    else:
        guide_action = "现金分红·已智能拆单"
elif it.get("require_cash_dividend"):
    guide_action = f"现金分红·{act_raw}" if act_raw and act_raw != "正常买入" else "现金分红·满期免赎A"
elif it.get("share_class") == "C":
    guide_action = "红利再投·弹性进攻C"
else:
    guide_action = "长钱持有·满期免赎A"

# 在表格下方展示超限定投计划
if blueprint.get("dca_plan"):
    st.info(f"💡 **《超限资金分批定投执行计划》**：{blueprint['dca_plan']}")
```

#### (3) Tab 2 三层核心驾驶舱结构（完全重塑）
```python
with tab_holdings_and_rebalance:
    # -------------------------------------------------------------
    # 第一层【🚦 今日是否适合调仓？AI 综合裁决卡】
    # -------------------------------------------------------------
    suit = StrategyBridge.evaluate_today_rebalance_suitability(pm, active_tier=st.session_state.active_tier_val)
    v_level = suit["verdict_level"]
    v_bg = "rgba(16, 185, 129, 0.08)" if v_level == "SUITABLE" else ("rgba(245, 158, 11, 0.08)" if v_level == "HOLD_ON" else "rgba(239, 68, 68, 0.08)")
    v_border = "#16a34a" if v_level == "SUITABLE" else ("#d97706" if v_level == "HOLD_ON" else "#dc2626")

    st.markdown(f"""
    <div style="background: {v_bg}; border: 1.5px solid {v_border}; border-radius: 8px; padding: 14px 18px; margin-bottom: 14px;">
        <div style="font-size: 16px; font-weight: 700; color: {v_border}; margin-bottom: 6px;">
            {suit['verdict_title']}
        </div>
    </div>
    """, unsafe_allow_html=True)

    r4d = suit["reasons_4d"]
    c_r1, c_r2, c_r3, c_r4 = st.columns(4)
    with c_r1:
        st.markdown(f"**📍 行情位置**\n\n<span style='font-size:12px; color:#475569;'>{r4d['market_position_reason']}</span>", unsafe_allow_html=True)
    with c_r2:
        st.markdown(f"**⏰ 申赎时钟**\n\n<span style='font-size:12px; color:#475569;'>{r4d['clock_window_reason']}</span>", unsafe_allow_html=True)
    with c_r3:
        st.markdown(f"**⚖️ 偏离净效用**\n\n<span style='font-size:12px; color:#475569;'>{r4d['deviation_utility_reason']}</span>", unsafe_allow_html=True)
    with c_r4:
        st.markdown(f"**🔒 批次锁定期**\n\n<span style='font-size:12px; color:#475569;'>{r4d['lockup_fee_reason']}</span>", unsafe_allow_html=True)

    st.markdown("---")

    # -------------------------------------------------------------
    # 第二层【⚖️ 今日怎么调？如果一定要调仓会有什么后果？】
    # -------------------------------------------------------------
    rebal_sim = StrategyBridge.simulate_rebalance_modes_and_consequences(pm, active_tier=st.session_state.active_tier_val)
    rebal_mode = st.radio(
        "选择调仓推演模式：",
        [
            "🛡️ 模式一：AI 温和免伤调仓 (仅调动免惩罚费份额·遵循3%免折腾缓冲，推荐)",
            "⚡ 模式二：如果今天一定要调仓 (无视缓冲带强行一步到位对齐目标配比，查看真实代价)"
        ],
        horizontal=True,
        key="rad_rebal_mode_choice"
    )
    chosen_sim = rebal_sim["mode_gentle"] if rebal_mode.startswith("🛡️") else rebal_sim["mode_forced"]
    cq = chosen_sim["consequences"]

    st.markdown("#### 📊 《本次调仓四大真实后果量化账单》")
    cq1, cq2, cq3, cq4 = st.columns(4)
    with cq1:
        fee_p = cq['fee_loss']['penalty_fee_7d']
        warn_txt = f"<br><span style='color:#dc2626; font-size:11px;'>⚠️ 含未满7天惩罚费 ¥{fee_p:,.2f}</span>" if fee_p > 0 else ""
        st.markdown(f"""
        <div class="decision-card">
            <div class="decision-title">💰 后果① 手续费直接损耗</div>
            <div class="decision-val" style="color: {'#dc2626' if fee_p > 0 else '#0284c7'};">¥{cq['fee_loss']['total_fee']:,.2f}</div>
            <div class="decision-desc">
                预计回本：<b>{cq['fee_loss']['payback_days']} 天</b> (通过股息平抑){warn_txt}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with cq2:
        st.markdown(f"""
        <div class="decision-card">
            <div class="decision-title">⏳ 后果② T+2在途踏空风险</div>
            <div class="decision-val" style="color: #d97706;">¥{cq['in_transit_risk']['in_transit_amount']:,.2f}</div>
            <div class="decision-desc">
                在途占比：<b>{cq['in_transit_risk']['in_transit_pct']:.1f}%</b> ({cq['in_transit_risk']['lock_days']})<br>
                同公司转换已省：¥{cq['in_transit_risk']['switch_saved_amount']:,.2f}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with cq3:
        rs = cq['risk_shift']
        st.markdown(f"""
        <div class="decision-card">
            <div class="decision-title">⚖️ 后果③ 组合攻防与回撤</div>
            <div class="decision-val" style="color: #16a34a;">{rs['vol_before']:.1f}% ➔ {rs['vol_after']:.1f}%</div>
            <div class="decision-desc">
                极限回撤：{rs['mdd_before']:.1f}% ➔ {rs['mdd_after']:.1f}%<br>
                组合股息：{rs['div_yield_before']:.2f}% ➔ {rs['div_yield_after']:.2f}%
            </div>
        </div>
        """, unsafe_allow_html=True)

    with cq4:
        st.markdown(f"""
        <div class="decision-card">
            <div class="decision-title">🔒 后果④ 持有期清零重算</div>
            <div class="decision-val" style="color: #7c3aed;">¥{cq['lockup_reset']['new_buy_amount']:,.2f}</div>
            <div class="decision-desc">
                重新进入 7 天 1.5% 惩罚锁定期；A 类免赎持有期重新起算。
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 渲染调仓执行单与按钮
    # (复用原有 9 列 df_orders_tbl 逻辑，并在下方支持一键执行 / 保存预案)
    ...

    st.markdown("---")

    # -------------------------------------------------------------
    # 第三层【📋 我的实时持仓明细与接管录入】
    # -------------------------------------------------------------
    st.subheader("📋 我的实时持仓明细与账本")
    df_disp = pm.export_snapshot_df()
    if not df_disp.empty:
        st.dataframe(df_disp, use_container_width=True, hide_index=True)
    else:
        st.info("当前账本为空，请展开下方向导添加持仓！")

    is_empty_portfolio = (len(pm.holdings) == 0)

    with st.expander("✨ 零门槛导入/新增持仓向导 (支持自由粘贴、搜索与模板导入)", expanded=is_empty_portfolio):
        # 4 个导入子选项卡
        ...

    with st.expander("✏️ 编辑修改持仓数据 (支持双击单元格修改与删除同步)", expanded=is_empty_portfolio):
        # st.data_editor 编辑表格与保存删除按钮
        ...

    with st.expander("📦 【点击展开：全组合 FIFO 批次透视与免赎回费倒计时汇总表】", expanded=is_empty_portfolio):
        # FIFO 批次表格
        ...
```

---

## 5. Verification Method (独立验证方法)

重构实施完成后，测试员或复核人可通过以下确切指令进行独立验证：

### 5.1 语法树静态检测（确保无 `time.sleep` 与无死代码）
```powershell
# 1. 验证 app_gui.py 中绝对无 time.sleep
C:\Users\deanc\AppData\Local\Programs\Python\Python311\python.exe -c "
import ast
tree = ast.parse(open('AGY2_FundAdvisory/app_gui.py', encoding='utf-8').read())
sleeps = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and getattr(getattr(n, 'func', None), 'attr', '') == 'sleep']
assert len(sleeps) == 0, f'app_gui.py 仍存在 {len(sleeps)} 处 sleep 调用！'
print('✅ AST 验证通过：app_gui.py 中 0 个 time.sleep！')
"

# 2. 验证 app_gui.py 中无硬编码“限额买500”
C:\Users\deanc\AppData\Local\Programs\Python\Python311\python.exe -c "
content = open('AGY2_FundAdvisory/app_gui.py', encoding='utf-8').read()
assert '限额买500' not in content, '仍存在硬编码 限额买500！'
assert '现金分红·限额买500' not in content, '仍存在硬编码 现金分红·限额买500！'
print('✅ 验证通过：无硬编码限额 500！')
"
```

### 5.2 核心算法与 GUI 端到端渲染测试
```powershell
cd d:\Google\Workspace\Wind\AGY2_FundAdvisory

# 1. 运行阶段一核心算法测试（确保 100% PASS）
C:\Users\deanc\AppData\Local\Programs\Python\Python311\python.exe -m pytest tests/test_milestone_phase1_r1_r5.py

# 2. 运行裁判基建测试（确保 100% PASS）
C:\Users\deanc\AppData\Local\Programs\Python\Python311\python.exe -m pytest tests/test_infra.py

# 3. 运行 GUI 端到端渲染测试
C:\Users\deanc\AppData\Local\Programs\Python\Python311\python.exe -m pytest tests/test_acceptance_r1_r7.py
```

### 5.3 界面目视核验准则（8501 端口）
1. 启动服务：`streamlit run AGY2_FundAdvisory/app_gui.py --server.port 8501 --server.headless true`
2. 检查顶部看板：仅占 1 行，包含 4 张大号清晰卡片（时钟、定调、温度、资产）与 1 个刷新按钮，在 1080p 屏幕下无任何 `...` 省略号。
3. 检查四大一级 Tab：
   - Tab 1 为 `🌱 新资金从0建仓推演`，无场景切换下拉框，点击推演无卡顿假延迟，白盒抽屉默认收起且标题含有动态数字摘要；
   - Tab 2 为 `💼 我的当前持仓与今日调仓建议`，顶部呈现红/黄/绿调仓裁决卡，中间呈现双模式单选与 4 张后果账单卡片，底部持仓明细正常，3 个向导面板默认收起；
   - Tab 3 为 `🔍 组合深度体检与算费工具箱`，所有穿透与算费模块完整可用；
   - Tab 4 为 `📈 策略历史回测与胜率档案`，回测图表与切片战报清晰展示。
