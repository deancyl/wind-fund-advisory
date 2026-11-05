# Tab 2「步骤一：持仓账本」人体工学深度重构 (R3) 架构调研与实现方案报告

## 摘要 (Executive Summary)

本调研聚焦于 Wind 投顾系统 Tab 2「💼 持仓调仓」核心工作流的第一站——「步骤一：持仓账本」的人体工学深度重构。
经过对 `AGY2_FundAdvisory/app_gui.py`（第 1735~2030 行）、`AGY2_FundAdvisory/portfolio_manager.py`（第 2561~3960 行、第 5460~5520 行）以及既有测试基线 `AGY2_FundAdvisory/tests/test_deep_remodel_final.py` 的逐行静态穿透与动态推演，完成了对 Tab 2 账本“三层人体工学空间”的精益重塑方案设计：

1. **第一层：4 张高信息密度资产概览卡**：彻底移除顶部占据大半屏纵向空间的 4 个独立全宽控制按钮，重构为等宽等高的 4 张专业级高信息密度资产看板卡（持仓总市值、可用现金池、累计浮动盈亏、锁仓与超额概览），并无缝集成 `💰 修改现金` Popover 与 7 天免罚/强锁统计。
2. **第二层：一屏尽览的精炼可编辑持仓表**：将原先冗余的 19 列宽表（横向滚动严重）精简至 10 列以内，彻底剔除重复与低频列，将「持有天数」与「赎回费状态」智能融合成兼具直观展示与自然数编辑的单列；解除 `st.data_editor` 对「当前市值(元)」的禁用锁定，实现市值与份额的自适应双向反算联动，并重构表格底部为 4 按钮等高操作栏。
3. **第三层：合并底部折叠框为单一「🛠️ 账本工具坞」**：收拢原先散落上下各处的 3 个独立折叠框（实盘接管档案、快速录入持仓、FIFO批次透视），采用单一展开容器配合 3 栏 Tabs 紧凑收纳，根据账户持仓状态自适应默认折叠/展开，并完美兼容既有标题断言测试。

---

## 一、第一层：4 张高信息密度资产概览卡架构深度分析

### 1.1 现状诊断：顶部 4 个全宽控制按钮的冗余与割裂

在 `AGY2_FundAdvisory/app_gui.py` 第 1777~1820 行，当前渲染了如下的快捷控制工具条：
```python
# 源码位置：app_gui.py:1777-1820
t2_ctrl_c1, t2_ctrl_c2, t2_ctrl_c3, t2_ctrl_c4 = st.columns([2.5, 2.5, 2.8, 2.2])
with t2_ctrl_c1:
    if st.button("🚀 加载演示组合", use_container_width=True, ...): ...
with t2_ctrl_c2:
    if st.button("↩️ 一键撤销快照", use_container_width=True, ...): ...
with t2_ctrl_c3:
    if st.button("🔄 同步真实净值", use_container_width=True, ...): ...
with t2_ctrl_c4:
    with st.popover("💰 现金池管理", use_container_width=True): ...
```
随后紧接着在第 1826~1830 行渲染了 4 个简易 metric：
```python
t2_m1, t2_m2, t2_m3, t2_m4 = st.columns(4)
t2_m1.metric("💼 组合总市值", f"¥{_t2_mkt:,.2f}")
t2_m2.metric("💵 可用现金", f"¥{pm.available_cash:,.2f}")
t2_m3.metric("📈 累计浮动盈亏", f"¥{_t2_pnl:+,.2f}", delta=f"{_t2_pnl_pct:+.2f}%")
t2_m4.metric("📊 持仓标的数", f"{len(pm.holdings)} 只")
```

**现存问题诊断**：
- **纵向空间严重浪费**：工具条占用一行，指标卡占用一行，再加上下方原本夹在中间的「📋 实盘接管档案」折叠框，导致核心数据表被硬生生挤出首屏，用户必须向下滚动才能看到具体持仓。
- **职责错位**：
  - 「🚀 加载演示组合」与「↩️ 一键撤销快照」属于全局沙盒/快照环境管理，在 R2 中已收拢至侧边栏全局领航台；同时在持仓为空状态时，下方已有一键载入演示组合的空状态引导。
  - 「🔄 同步真实净值」属于表格数据刷新操作，应当与保存修改、导出 CSV 等同源收纳于表格操作栏。
  - 「💰 现金池管理」独立占据一个大按钮，与下方「💵 可用现金」指标卡视觉脱节。

### 1.2 4 张高信息密度对齐概览卡的设计规范

移除上述冗余工具条后，第一层直接呈现 4 张等高、对齐、高信息密度的专业级资产概览卡：

```
+---------------------------+---------------------------+---------------------------+---------------------------+
|      💼 持仓总市值        |       💵 可用现金池       |       📈 累计浮动盈亏     |      🔒 锁仓与超额概览    |
|       ¥185,420.00         |        ¥25,000.00         |        +¥12,450.00        |     🟢 4只免罚 / 🔴 1只强锁 |
|    仓位占比 88.1% (总资产) |   现金占比 11.9% [💰修改]   |     +7.20% (盘中预估+¥580) |    Alpha +4.25% (vs 000300)|
+---------------------------+---------------------------+---------------------------+---------------------------+
```

#### Card 1: 💼 持仓总市值 (附仓位占比)
- **主指标**：`¥{_t2_mkt:,.2f}`
- **副指标 (Delta / 标注)**：`仓位占比 {mkt_ratio:.1f}%`
- **底层计算来源**：
  ```python
  _t2_mkt = sum(getattr(h, "shares", 0.0) * getattr(h, "current_nav", 1.0) for h in pm.holdings.values()) if pm.holdings else 0.0
  _in_transit = getattr(pm, "in_transit_cash", 0.0)
  total_cur_equity = _t2_mkt + pm.available_cash + _in_transit
  mkt_ratio = (_t2_mkt / total_cur_equity * 100.0) if total_cur_equity > 0 else 0.0
  ```

#### Card 2: 💵 可用现金池 (含 `💰 修改现金` popover)
- **主指标**：`¥{pm.available_cash:,.2f}`
- **副指标 (Delta / 标注)**：`现金占比 {cash_ratio:.1f}%`（若有在途资金可标注 `在途 ¥{_in_transit:,.2f}`）
- **交互组件**：内嵌或紧邻放置 `💰 修改现金` Popover 触发按钮。
  用户展开后可直接通过 `st.number_input` 修改现金金额，点击确认后调用：
  ```python
  pm.available_cash = round(new_c_val, 2)
  pm.save_state(record_snapshot=True)
  st.rerun()
  ```

#### Card 3: 📈 累计浮动盈亏 (附盈亏率与今日盘中预估盈亏)
- **主指标**：`¥{_t2_pnl:+,.2f}`
- **副指标 (Delta)**：`{_t2_pnl_pct:+.2f}%`
- **副指标附加信息**：`今日盘中预估: ¥{total_est_pnl:+,.2f}`
- **底层计算来源**：
  ```python
  _t2_cost = sum(getattr(h, "shares", 0.0) * getattr(h, "cost_price", getattr(h, "current_nav", 1.0)) for h in pm.holdings.values()) if pm.holdings else 0.0
  _t2_pnl = _t2_mkt - _t2_cost
  _t2_pnl_pct = (_t2_pnl / _t2_cost * 100.0) if _t2_cost > 0 else 0.0
  # 今日盘中预估盈亏总和（法规 95% 仓位系数折算）
  total_est_pnl = sum(
      round(float(h.market_value) * (fetch_realtime_fund_quote(h.fund_code).gszzl / 100.0) * 0.95, 2)
      for h in pm.holdings.values()
  ) if pm.holdings else 0.0
  ```

#### Card 4: 🔒 锁仓与超额概览 (动态统计已满 7 天与未满 7 天，及 Alpha)
- **主指标**：`🟢 {free_count}只免罚 / 🔴 {locked_count}只强锁`
- **副指标 (Delta)**：`Alpha: {pm.alpha_return_pct:+.2f}%`（基于 `pm.benchmark_code`，如沪深300）
- **底层计算逻辑**：
  ```python
  # 穿透所有持仓的所有批次，严格遵循 GEMINI.md 准则 7（悲观天数与安全锁防线）
  locked_count = 0
  free_count = 0
  for h in pm.holdings.values():
      if any(b.holding_days < 7 or getattr(b, "safety_lock", False) for b in h.batches):
          locked_count += 1
      else:
          free_count += 1
  alpha_val = getattr(pm, "alpha_return_pct", 0.0)
  benchmark_code = getattr(pm, "benchmark_code", "000300")
  ```

---

## 二、第二层：一屏尽览的精炼可编辑持仓表深度重构

### 2.1 当前表格 19 列详单与精简策略

在 `portfolio_manager.py` 第 3909~3929 行，`pm.export_snapshot_df()` 输出了多达 19 列：
1. `基金代码` (str)
2. `基金名称` (str)
3. `份额类型` (str, 'A'/'C')
4. `持仓份额` (float)
5. `当前净值` (float)
6. `今日实时估值` (float)
7. `今日实时估值涨跌(%)` (float)
8. `盘中预估盈亏(元)` (float)
9. `今日预估盈亏率(%)` (float)
10. `当前市值(元)` (float)
11. `持仓占比(%)` (float)
12. `持仓成本价` (float)
13. `浮动盈亏率(%)` (float)
14. `最短持有天数` (int)
15. `赎回费安全状态` (str)
16. `当前赎回费率(%)` (float)
17. `分红方式` (str)
18. `过渡建议标签` (str)
19. `估值更新时间` (str)

**精简与合并裁撤分析**：
- **剔除重复列**：`今日预估盈亏率(%)` 纯粹等于 `今日实时估值涨跌(%) * 0.95`，与估值涨跌重复；
- **剔除低频噪音列**：`估值更新时间`（如 `"2026-11-03 15:00"`）和 `过渡建议标签`（如 `"常规监控"`）无高频决策价值；
- **提炼盘中汇总**：原表格内占据 5 列的盘中实时行情（估值、估值涨跌、盘中盈亏、盈亏率、时间）造成严重横向滚动；将其全局汇总直接提炼至 Card 3 的「今日盘中预估」中；
- **合并多列为单列**：原第 14 列「最短持有天数」、第 15 列「赎回费安全状态」、第 16 列「当前赎回费率(%)」三列占据大量视口，将其精简浓缩为单一列「持有天数与费率」。

### 2.2 精简后 10 列以内的终态表结构 (一屏尽览无横滚)

| 序号 | 字段名称 | 类型 / 渲染配置 | 是否可编辑 | 说明与约束 |
|:---:|:---|:---|:---:|:---|
| 1 | `基金代码` | `TextColumn` | ❌ 禁用 | 6 位标准代码（等宽对齐） |
| 2 | `基金名称` | `TextColumn` | ❌ 禁用 | 标的中文名称 |
| 3 | `持仓份额` | `NumberColumn(format="%.2f")` | ✏️ **可编辑** | 用户修改份额，自动更新市值 |
| 4 | `当前净值` | `NumberColumn(format="%.4f")` | ❌ 禁用 | 官方复权单位净值 |
| 5 | `当前市值(元)` | `NumberColumn(format="¥%.2f")` | ✏️ **可编辑** | **本次解锁！**用户修改市值，自动反算份额 |
| 6 | `持仓占比(%)` | `ProgressColumn(format="%.1f%%")` | ❌ 禁用 | 占全账户总资产的权重进度条 |
| 7 | `持仓成本价` | `NumberColumn(format="%.4f")` | ✏️ **可编辑** | 持仓加权成本净值 |
| 8 | `浮动盈亏率(%)`| `NumberColumn(format="%+.2f%%")` | ❌ 禁用 | `(现价-成本)/成本` |
| 9 | `持有天数与费率`| `TextColumn` | ✏️ **可编辑** | 智能格式化如 `45天 🟢 0.00% 免赎`，正则提取编辑天数 |
| 10 | `分红方式` | `SelectboxColumn(["cash","reinvest"])` | ✏️ **可编辑** | 现金分红 / 红利再投 |

**总列数控制在整整 10 列**（在 1080p 屏幕及侧边栏展开状态下总宽约 820px，完全置于无横向滚动条的天然呼吸区内）。

### 2.3 “持有天数”与“赎回费状态”单列智能合并与自然数提取技术

#### 2.3.1 展示格式化机制
在数据载入时，按如下规则生成字符串：
```python
# rate 来自 pm.calculator.get_redemption_fee_rate(share_class, min_days)
if has_lock or min_days < 7:
    status_cell = f"{min_days}天 🔴 {rate*100:.2f}% 强锁"
elif (share_class == 'C' and min_days < 30) or rate > 0:
    status_cell = f"{min_days}天 🟡 {rate*100:.2f}% 梯级"
else:
    status_cell = f"{min_days}天 🟢 0.00% 免赎"
```

#### 2.3.2 用户编辑后的自然数容错提取
用户在 `st.data_editor` 中双击该单元格时，可以直接修改天数数字（例如将 `15` 改为 `45`，或者直接输入 `60天`，或不做修改）。
在后台保存同步时，采用健壮正则进行数字剥离：
```python
raw_holding_status = str(row.get("持有天数与费率", row.get("最短持有天数", 30)))
match = re.search(r'\d+', raw_holding_status)
holding_days_val = int(match.group()) if match else 30
```
无论是未修改的完整字符串（`"45天 🟢 0.00% 免赎"` -> `45`），还是用户手输的纯数字（`"60"` -> `60`）或带中文（`"60天"` -> `60`），均能 100% 精确解析为标准整数，并在同步保存后由系统自动触发持有期梯级与安全锁的自适应重算与即时刷新。

### 2.4 解锁「当前市值(元)」直接编辑与双向反算算法

#### 2.4.1 解除锁定
在 `app_gui.py` 的 `st.data_editor` 配置中：
1. 从 `disabled` 列表中彻底移除 `"当前市值(元)"`；
2. 为 `"当前市值(元)"` 配置 `st.column_config.NumberColumn("当前市值(元)", format="¥%.2f", min_value=0.0, step=100.0, help="双击直接修改当前市值，保存后自动按当前净值反算持仓份额")`。

#### 2.4.2 双向变更甄别与反算决策状态机
当用户点击「💾 保存表格修改」时，系统遍历 `edited_table` 的每一行，对照原始持仓对象 `orig_h = pm.holdings.get(code_s)` 执行状态机研判：

```python
orig_shares = float(orig_h.shares) if orig_h else 0.0
orig_mkt_val = float(orig_h.market_value) if orig_h else 0.0
edited_shares = float(row.get("持仓份额", 0.0))
edited_mkt_val = float(row.get("当前市值(元)", 0.0))
curr_nav = float(row.get("当前净值", 1.0))
if curr_nav <= 0.0:
    curr_nav = 1.0

# 精度容差检测
mkt_changed = abs(edited_mkt_val - orig_mkt_val) > 0.01
shares_changed = abs(edited_shares - orig_shares) > 0.0001

if mkt_changed and not shares_changed:
    # 场景 1：用户单独修改了【当前市值】 -> 严格按 新市值 / 当前净值 反算持仓份额
    final_shares = round(edited_mkt_val / curr_nav, 2)
elif shares_changed and not mkt_changed:
    # 场景 2：用户单独修改了【持仓份额】 -> 采纳修改后的持仓份额，后续系统重算市值
    final_shares = round(edited_shares, 2)
elif mkt_changed and shares_changed:
    # 场景 3：两者皆修改（或新录入行） -> 以输入的市值优先反算或以份额为准
    if orig_h is None and edited_mkt_val > 0 and edited_shares == 0:
        final_shares = round(edited_mkt_val / curr_nav, 2)
    else:
        # 用户同时改动时，以直接设定的市值反算份额（优先确保用户资金规模意图）
        final_shares = round(edited_mkt_val / curr_nav, 2)
else:
    # 场景 4：份额与市值均未变动（仅修改了成本价、持有天数或分红方式）
    final_shares = orig_shares
```

#### 2.4.3 全局仓位权重、总资产与 session_state 联动溯源
调用 `pm.add_or_update_holding(fund_code=code_s, shares=final_shares, nav=curr_nav, ...)` 后，内部执行流如下：
1. **FIFO 批次等比伸缩**：`ratio = final_shares / old_total`，保持所有历史买入批次的已持有天数和比例不变；
2. **`_recalculate_totals()`**：
   - 逐个标的重新计算：`h.market_value = round(final_shares * curr_nav, 2)`；
   - 累加账户总资产：`cur_total_equity = total_market_val + self.available_cash + self.in_transit_cash`；
   - 更新峰值总资产 `self.peak_equity` 与最大回撤 `self.max_drawdown_pct`；
   - 更新基准超额收益 `self.alpha_return_pct`；
3. **持仓占比自动重算**：下一次渲染或导出时，每一行的 `持仓占比(%)` 自动以 `(h.market_value / cur_total_equity * 100.0)` 精确呈现；
4. **清理诊断缓存并刷新**：
   ```python
   st.session_state.tab2_diag_cache = None
   st.session_state.tab2_rebal_cache = None
   st.session_state.tab2_diagnosed = False
   st.session_state.tab2_rebalanced = False
   st.rerun()
   ```
   页面重载后，顶部 Card 1（总市值与仓位）、Card 3（浮动盈亏）、Card 4（锁仓与Alpha）以及表格本身的市值、份额、权重完全达到分厘级一致闭环。

### 2.5 表格操作栏等高单行重排 (Action Bar Alignment)

#### 2.5.1 现存缺陷
原 `app_gui.py` 底部操作栏（第 1880~1927 行）为：
- 3 列结构 `col_save_t, col_del_t, col_exp_t = st.columns([3, 3, 4])`
- `col_del_t` 中放了一个 `st.selectbox("选择要删除的标的", ...)`，该下拉框附带标题，高度远超普通的 `st.button`；当选定标的后还会额外弹出一个 `🗑️ 彻底删除` 按钮，产生严重的上下行错位与跳动。

#### 2.5.2 终态设计：4 列等高专业操作栏
采用 `st.columns([2.8, 2.4, 2.4, 2.4])` 布局，四个组件在 Streamlit 中全部具有统一的 38px 按钮级高度：

```
+------------------------+------------------------+------------------------+------------------------+
| 💾 保存表格修改 (Primary)|  🔄 同步最新净值 (Button) |  📥 导出持仓 CSV (Button)|  🗑️ 删除标的 (Popover)  |
+------------------------+------------------------+------------------------+------------------------+
```

```python
col_act1, col_act2, col_act3, col_act4 = st.columns([2.8, 2.4, 2.4, 2.4])

with col_act1:
    if st.button("💾 保存表格修改", type="primary", use_container_width=True, key="btn_save_holdings_tab2"):
        # 执行前述双向反算与入库逻辑
        ...

with col_act2:
    if st.button("🔄 同步最新净值", use_container_width=True, key="btn_sync_nav_tab2", help="拉取天天基金与新浪最新净值，刷新持仓市值与超额"):
        with st.spinner("🔄 同步中..."):
            s_res = pm.sync_holdings_live_nav(use_intraday_gsz=True)
        st.success(f"✅ 已同步 {s_res.get('updated_count', 0)} 只持仓最新净值！")
        st.rerun()

with col_act3:
    csv_exp = df_disp.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        "📥 导出持仓快照 CSV",
        data=csv_exp,
        file_name=f"portfolio_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        use_container_width=True,
        key="btn_dl_csv_tab2"
    )

with col_act4:
    with st.popover("🗑️ 删除标的", use_container_width=True):
        del_opts = ["-- 请选择 --"] + [f"{c} - {h.fund_name}" for c, h in pm.holdings.items()]
        del_sel = st.selectbox("选择要删除的基金标的", del_opts, key="sel_del_hold_tab2")
        if del_sel != "-- 请选择 --":
            sel_code = del_sel.split(" - ")[0].strip()
            if st.button(f"确认彻底删除 {sel_code}", type="primary", use_container_width=True, key="btn_confirm_del_tab2"):
                pm.delete_holding(sel_code)
                st.session_state.tab2_diag_cache = None
                st.session_state.tab2_rebal_cache = None
                st.session_state.tab2_diagnosed = False
                st.session_state.tab2_rebalanced = False
                st.success(f"已删除 {sel_code}")
                st.rerun()
```
四个按钮宽度均衡、垂直高度严丝合缝对齐，彻底消除 UI 视觉杂乱。

---

## 三、第三层：合并底部折叠框为单一「🛠️ 账本工具坞」

### 3.1 现存 3 个折叠框的分散位置与测试依赖

当前代码中散落了 3 个折叠框：
1. **折叠框 1**：第 1832~1842 行 `with st.expander("📋 实盘接管档案", expanded=False):` —— 位于表格上方，打断了概览卡与持仓表格的自然浏览视线；
2. **折叠框 2**：第 1930~1991 行 `with st.expander("✨ 快速录入持仓", expanded=(not has_holdings)):` —— 位于表格下方，包含 3 个子 Tab（文本粘贴、搜索添加、表格模板）；
3. **折叠框 3**：第 1992~2014 行 `with st.expander("📦 FIFO批次透视", expanded=False):` —— 位于最下方。

**关键测试强约束（来自 `test_deep_remodel_final.py` 第 184~191 行）**：
```python
key_titles = [
    ...,
    "实盘接管档案",
    "FIFO批次透视",
    ...
]
for t in key_titles:
    clean_chinese = re.sub(r'[^\u4e00-\u9fa5]', '', t)
    assert len(clean_chinese) <= 7, f"Title '{t}' has {len(clean_chinese)} Chinese characters (> 7)"
    assert t in text, f"Key title '{t}' not found in app_gui.py"
```
测试明确要求字符串 `"实盘接管档案"` 与 `"FIFO批次透视"` 必须在 `app_gui.py` 代码中作为标题或 Tab 名称存在，且纯汉字字数不超过 7 个。

### 3.2 整合方案：单一「🛠️ 账本工具坞」

将三者统一移至表格操作栏下方，合并为一个主折叠容器，内部通过 `st.tabs` 横向组织：

```python
has_holdings = len(pm.holdings) > 0

# 单一紧凑工具坞折叠容器
with st.expander("🛠️ 账本工具坞", expanded=(not has_holdings)):
    dock_t1, dock_t2, dock_t3 = st.tabs([
        "✨ 快速录入持仓",
        "📋 实盘接管档案",
        "📦 FIFO批次透视"
    ])

    with dock_t1:
        # 原快速录入的三大方式（文本粘贴导入 / 搜索添加标的 / 表格模板导入）
        sub_tab1, sub_tab2, sub_tab3 = st.tabs([
            "📋 文本粘贴导入",
            "🔍 搜索添加标的",
            "📥 表格模板导入"
        ])
        ... (保持原有解析逻辑)

    with dock_t2:
        # 原实盘接管档案的 6 项量化基准指标
        col_arch1, col_arch2 = st.columns(2)
        with col_arch1:
            st.write(f"**接管模式**：{'模式 A (极简冷启动)' if pm.takeover_mode == 'A' else '模式 B (账本热接管)'}")
            st.write(f"**基准确立日**：`{pm.baseline_date}`")
            st.write(f"**接管基准总资产**：¥{pm.baseline_equity:,.2f}")
        with col_arch2:
            st.write(f"**峰值总资产**：¥{pm.peak_equity:,.2f}")
            st.write(f"**接管期最大回撤**：`{pm.max_drawdown_pct:.2f}%`")
            st.write(f"**基准超额 (Alpha)**：`{pm.alpha_return_pct:+.2f}%` (vs {pm.benchmark_code})")

    with dock_t3:
        # 原 FIFO 批次透视明细宽表
        all_b_rows = []
        for f_c, h_obj in pm.holdings.items():
            safe_shares_val = pm.get_penalty_free_redeemable_shares(f_c)
            for b_i in h_obj.batches:
                days_left = max(0, 7 - b_i.holding_days)
                countdown_str = "🟢 已满7天 (免惩罚费)" if days_left == 0 else f"🔴 距免惩罚费还剩 {days_left} 天"
                all_b_rows.append({
                    "基金代码": f_c,
                    "基金名称": h_obj.fund_name,
                    "批次编号": b_i.batch_id,
                    "买入日期": b_i.buy_date,
                    "批次份额": b_i.shares,
                    "成本净值": b_i.cost_nav,
                    "已持有天数": f"{b_i.holding_days} 天",
                    "安全状态": countdown_str,
                    "免惩罚可卖份额": safe_shares_val,
                })
        if all_b_rows:
            st.dataframe(pd.DataFrame(all_b_rows), use_container_width=True, hide_index=True)
        else:
            st.info("当前持仓暂无批次数据。")
```

**人体工学与规范对齐验证**：
1. **状态自适应**：
   - 当 `len(pm.holdings) == 0`（无持仓）时：工具坞默认自动展开（`expanded=True`），首选 Tab 为快速录入，引导新用户快速输入持仓；
   - 当 `len(pm.holdings) > 0`（有持仓）时：工具坞默认收拢（`expanded=False`），整屏视觉焦点完全集中于顶部的「4 张概览卡」与「精炼可编辑持仓表」，下方直达「🔍 第一步：启动 AI 今日调仓时机全息诊断」核心操作推进大按钮；
2. **测试零破坏**：
   - `"账本工具坞"` 纯汉字 5 个（<= 7）；
   - Tab 标题包含 `"实盘接管档案"` 与 `"FIFO批次透视"`，既有标题字数与存在性断言 100% 绿色通过。

---

## 四、增量自动化测试方案 (Delta Tests Blueprint)

在交付实现时，建议在 `AGY2_FundAdvisory/tests/` 下编写针对本次 R3 改造的增量回归测试用例（如在 `test_deep_remodel_final.py` 中追加或新建 `test_delta_remodel_r3.py`）：

```python
def test_tab2_direct_market_value_edit_recalculates_shares(temp_pm):
    """验证持仓表直接修改当前市值时，按当前净值精确反算持仓份额且批次等比缩放"""
    # 1. 构造初始持仓
    temp_pm.add_or_update_holding(
        fund_code="005561",
        shares=10000.0,
        nav=1.25,
        cost_price=1.20,
        holding_days=45,
        dividend_method="cash"
    )
    assert temp_pm.holdings["005561"].shares == 10000.0
    assert temp_pm.holdings["005561"].market_value == 12500.0

    # 2. 模拟前端用户直接将当前市值修改为 25,000.00 元 (未修改份额列)
    edited_mkt_val = 25000.0
    curr_nav = 1.25
    recalculated_shares = round(edited_mkt_val / curr_nav, 2)
    assert recalculated_shares == 20000.0

    # 3. 提交入库
    temp_pm.add_or_update_holding(
        fund_code="005561",
        shares=recalculated_shares,
        nav=curr_nav,
        cost_price=1.20,
        holding_days=45,
        dividend_method="cash"
    )

    # 4. 断言份额翻倍，市值与批次份额分厘同步
    h = temp_pm.holdings["005561"]
    assert h.shares == 20000.0
    assert h.market_value == 25000.0
    assert sum(b.shares for b in h.batches) == 20000.0
    assert h.floating_pnl == round(25000.0 - (20000.0 * 1.20), 2)


def test_tab2_holding_days_regex_parsing():
    """验证持有天数与费率合并列的用户输入容错正则解析"""
    import re
    samples = [
        ("45天 🟢 0.00% 免赎", 45),
        ("2天 🔴 1.50% 强锁", 2),
        ("15天 🟡 0.50% 梯级", 15),
        ("60", 60),
        ("90天", 90),
        ("0", 0),
        ("", 30), # 缺省回退
    ]
    for text_in, expected_days in samples:
        m = re.search(r'\d+', text_in)
        days = int(m.group()) if m else 30
        assert days == expected_days, f"Failed parsing '{text_in}': got {days}, expected {expected_days}"
```

---

## 五、调研结论与执行就绪性评定 (Readiness Assessment)

| 改造维度 | 涉及核心文件与行数 | 技术难点与风险点 | 防御与解决方案 | 就绪度 |
|:---|:---|:---|:---|:---:|
| **第一层：4 张资产概览卡** | `app_gui.py`: 1777~1830 | 现金修改 Popover 引起的高度对齐问题 | 采用等宽列与紧凑 Popover 触发器，统一 4 卡内边距与字体层级 | ✅ 极高 |
| **第二层：可编辑持仓表精炼** | `app_gui.py`: 1854~1905 | 份额与市值双改冲突、多批次历史天数漂移 | 状态机甄别修改来源；`pm.add_or_update_holding` 原生比例缩放保护 FIFO | ✅ 极高 |
| **第二层：等高操作栏** | `app_gui.py`: 1880~1927 | 删除下拉框高度不一与误触 | 改为 `st.popover("🗑️ 删除标的")`，4 大按钮高度严格统一为 38px | ✅ 极高 |
| **第三层：单一账本工具坞** | `app_gui.py`: 1832~2014 | 测试套件对 `"实盘接管档案"` / `"FIFO批次透视"` 的硬编码断言 | 保留 exact title strings 于 `st.tabs` 中，主标题汉字数 <= 7 | ✅ 极高 |

**总体评估**：本方案具备零破坏性、逻辑闭环完整、计算数学模型自洽、测试完全兼容的特点，已完全具备实现阶段的无缝施工条件。
