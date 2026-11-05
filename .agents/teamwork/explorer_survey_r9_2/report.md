# Phase 0 技术调研报告：R3、R4、R7 深度审计与落地方案

**调研时间**: 2026-11-05  
**调研人员**: teamwork_explorer (`explorer_survey_r9_2`)  
**调研范围**: 
- **R3**: Tab 2 四大实盘调仓场景模式前后端真实计算闭环
- **R4**: Tab 3 历史相似匹配硬编码假文案清除与动态统计
- **R7**: 双翼看板右翼主动风险预警哨同类预警折叠聚合与紧凑布局

---

## 1. Tab 2 四大实盘调仓场景模式前后端真实计算闭环 (R3)

### 1.1 核心调用链与代码现状审计

#### A. 前端交互与函数调用 (`AGY2_FundAdvisory/app_gui.py`)
在 `app_gui.py` 的 Tab 2 中，当前调仓推演与指令生成的代码结构如下：

1. **缓存签名与模拟推演计算**（第 4362~4389 行）：
```python
cur_pool_sig = (chosen_target_pool, tuple(sorted(tier_target_w.items())))
if st.session_state.get("tab2_last_pool_sig") != cur_pool_sig:
    st.session_state.tab2_rebal_cache = None
    st.session_state.tab2_last_pool_sig = cur_pool_sig

if st.session_state.get("tab2_trigger_rebalance", False) or st.session_state.get("tab2_rebal_cache") is None:
    ...
    sim_res = StrategyBridge.simulate_rebalance_modes_and_consequences(
        pm,
        active_tier=active_tier,
        target_weights=tier_target_w,
        min_buffer_pct=(_cur_buf / 100.0),
        locked_funds=st.session_state.get("tab2_locked_funds"),
        pending_take_profit=st.session_state.get("tab2_pending_take_profit"),
        c_replace=st.session_state.get("tab2_c_replace")
    )
    st.session_state.tab2_rebal_cache = sim_res
```
**严重断层点 1**：`cur_pool_sig` 仅包含 `chosen_target_pool` 和 `tier_target_w`，**完全未包含** `scenario_mode`、`new_cash_amount`、`withdraw_cash_amount`、`freeze_reserved_cash`、`core_anchor_code`！

2. **场景模式 UI 渲染位置滞后**（第 4401~4450 行）：
```python
col_sc1, col_sc2 = st.columns([6.5, 3.5])
with col_sc1:
    sel_scenario_name = st.radio(
        "调仓意图场景：",
        [
            "⚖️ 存量标准再平衡 (平衡各大类资产偏离度)",
            "💵 新资注入免赎补仓 (发工资/定投补仓·零卖出零赎回费)",
            "🏧 智能低损耗提现 (急需用钱·零买入·阶梯免赎赎回·避开7天惩罚)",
            "🧹 尾部碎片与C类一键归拢 (清理<3%碎片与满期高费率C类至底仓)"
        ],
        index=0,
        key="rad_tab2_scenario_mode"
    )
with col_sc2:
    freeze_reserved_chk = st.checkbox(
        f"🛡️ 冻结分批建仓预留现金 (¥{pm.reserved_batch_cash:,.2f})",
        value=True,
        key="chk_freeze_reserved_cash"
    )
```
**严重断层点 2**：场景选择单选框及输入金额（`new_cash_val`, `withdraw_cash_val`）**位于模拟推演计算（第 4376 行）之后**！当用户切换单选框或修改金额触发 rerun 时，由于上方第 4367 行命中缓存，`simulate_rebalance_modes_and_consequences` 根本不会重新执行，即使重新执行也从未传入这些场景参数。

3. **调仓执行单生成调用**（第 4582~4592 行）：
```python
ai_orders_res = StrategyBridge.generate_ai_rebalance_orders(
    current_holdings=pm.holdings,
    available_cash=pm.available_cash,
    target_weights_funds=tier_target_w,
    pm=pm,
    mode=rebal_mode_param,
    min_buffer_pct=_cur_buf,
    locked_funds=st.session_state.get("tab2_locked_funds"),
    pending_take_profit=st.session_state.get("tab2_pending_take_profit"),
    c_replace=st.session_state.get("tab2_c_replace")
)
```
**严重断层点 3**：`generate_ai_rebalance_orders` 的调用参数中：
- 零场景参数：`scenario_mode`、`new_cash_amount`、`withdraw_cash_amount`、`freeze_reserved_cash`、`core_anchor_code` 一个都没传！
- 可用现金传入的是原始 `pm.available_cash`，未遵循 `freeze_reserved_chk` 扣除 `pm.reserved_batch_cash`！

4. **立即执行按钮**（第 4726 行）：
```python
rebal_plan = pm.generate_scenario_rebalance_plan(
    tier_target_w, 
    scenario_mode=scenario_key, 
    new_cash_amount=new_cash_val, 
    withdraw_cash_amount=withdraw_cash_val, 
    freeze_reserved_cash=freeze_reserved_chk, 
    min_buffer_pct=(0.0 if sel_mode_key == "mode_forced" else _cur_buf), 
    core_anchor_code=anchor_target_code
)
```
**严重断层点 4**：唯独在点击执行调仓按钮时调用了 `pm.generate_scenario_rebalance_plan`，导致**“前端表格展示的是标准存量调仓建议，点击执行却执行了另一个场景模式”**，前后端完全精神分裂脱节！

---

#### B. 策略桥接层 (`AGY2_FundAdvisory/strategy_bridge.py`)

1. **`simulate_rebalance_modes_and_consequences`**（第 6140~6680 行）：
- 当前函数入参：`cls, pm, active_tier="C3", target_weights=None, min_buffer_pct=0.03, **kwargs`
- 内部完全忽略 `kwargs.get("scenario_mode")`，固定计算存量卖出与买入的四大后果账单（`fee_loss`, `in_transit_risk`, `risk_shift`, `lockup_reset`）。
- 导致选择 `new_cash_only` 时，后果卡片上仍然显示存量标的的高额赎回费、在途风险；选择 `withdraw_cash_only` 时，后果卡片依然显示申购费与买入锁仓！

2. **`generate_ai_rebalance_orders`**（第 3470~3885 行）：
- 在第 3581 行，代码虽然试图调用 `pm.generate_scenario_rebalance_plan`：
```python
if pm is not None and hasattr(pm, "generate_scenario_rebalance_plan"):
    try:
        pm_plan = pm.generate_scenario_rebalance_plan(...)
    except Exception:
        pm_plan = None
```
- 但在后续构建表格 items 时（第 3626~3750 行）：
```python
for code in all_codes:
    c_w = current_weights.get(code, 0.0)
    t_w = target_weights_funds.get(code, 0.0)
    diff_w = t_w - c_w
    diff_amount = diff_w * total_equity
    ...
```
**致命缺陷**：代码直接用 `diff_w = t_w - c_w` 和 `diff_amount = diff_w * total_equity` 机械计算每个标的的买卖方向与金额！
- 在 `new_cash_only` 模式下：原有持仓只要当前权重偏高（`diff_w < 0`），代码就会直接生成 `action = "SELL"`，完全违反“卖出金额严格为 0、零赎回费”要求！
- 在 `withdraw_cash_only` 模式下：原有持仓只要当前权重偏低（`diff_w > 0`），代码就会直接生成 `action = "BUY"`，完全违反“买入金额严格为 0”要求！
- `pm_plan` 中计算出的 `sell_actions` 与 `buy_actions` 核心结果被直接废弃，仅提取了路由名称！

---

#### C. 底层资产组合管理器 (`AGY2_FundAdvisory/portfolio_manager.py`)
在 `portfolio_manager.py` 第 6232~6600 行中，`generate_scenario_rebalance_plan` 已经完整实现了四大场景的底层数学逻辑：
- `standard`（第 6253 行）：支持 `freeze_reserved_cash` 扣减 `reserved_batch_cash`；
- `new_cash_only`（第 6268 行）：`sell_actions` 严格为 `[]`，`total_sell_amount = 0.0`，`total_redemption_fee = 0.0`，根据短板缺口精准分配新增资金，金额总和通过误差修正严格等于 `new_cash_amount`；
- `withdraw_cash_only`（第 6358 行）：`buy_actions` 严格为 `[]`，严格调用 `get_penalty_free_redeemable_shares` 排除 `<7` 天标的，按优先级（C类满期/A类满期/意愿清仓）赎回，赎回金额总和严格等于 `withdraw_cash_amount`（或最大免赎额度）；
- `sweep_tail_and_c_class`（第 6475 行）：清理 `<3%` 碎片和满 30 天 C 类，全额汇聚申购 `core_anchor_code`。

### 1.2 R3 整改技术落地方案

1. **调整 `app_gui.py` 布局与执行流**：
   - 将“🎛️ 实盘调仓场景模式”及其单选框、预留资金复选框、场景参数输入组件（`new_cash_val`, `withdraw_cash_val`, `sel_anchor`）**整体移至缓存校验与 `simulate_rebalance_modes_and_consequences` 调用之前**。
   - 升级缓存签名 `cur_pool_sig` 为全要素元组：
     ```python
     cur_pool_sig = (
         chosen_target_pool,
         tuple(sorted(tier_target_w.items())),
         scenario_key,
         float(new_cash_val),
         float(withdraw_cash_val),
         bool(freeze_reserved_chk),
         str(anchor_target_code),
         float(_cur_buf),
         tuple(sorted(st.session_state.get("tab2_locked_funds") or [])),
         str(st.session_state.get("tab2_pending_take_profit")),
         str(st.session_state.get("tab2_c_replace"))
     )
     ```
   - 调整可用调仓现金：当 `freeze_reserved_chk` 为 True 时，计算传入的 `effective_cash = max(0.0, pm.available_cash - pm.reserved_batch_cash)`。
   - 传参全量贯通：将 `scenario_mode=scenario_key`, `new_cash_amount=new_cash_val`, `withdraw_cash_amount=withdraw_cash_val`, `freeze_reserved_cash=freeze_reserved_chk`, `core_anchor_code=anchor_target_code` **同时传入** `simulate_rebalance_modes_and_consequences` 和 `generate_ai_rebalance_orders`。

2. **升级 `strategy_bridge.py` 中的 `generate_ai_rebalance_orders`**：
   - 当 `pm is None` 时，自动利用 `current_holdings` 与 `available_cash` 初始化临时 `pm` 实例以驱动 `generate_scenario_rebalance_plan`。
   - 深度集成 `pm_plan` 的输出结果：
     - 若 `scenario_mode == "new_cash_only"`：
       - 所有现有持仓的 `action` 强制设为 `HOLD`（维持当前仓位，`diff_amount = 0.0`，卖出为 0）；
       - 遍历 `pm_plan.get("buy_actions", [])`，对有买入配置的标的精准生成 `action = "BUY"`，金额严格使用 `b_act["amount"]`；买入金额之和严格等于 `new_cash_amount`。
     - 若 `scenario_mode == "withdraw_cash_only"`：
       - 所有持仓的买入 `diff_amount` 强制为 0（零买入）；
       - 遍历 `pm_plan.get("sell_actions", [])`，对被选中的赎回标的生成 `action = "SELL"`，卖出金额严格使用 `s_act["amount"]`，未选中的设为 `HOLD`；卖出总额严格等于 `withdraw_cash_amount`，且完全规避未满 7 天标的。
     - 若 `scenario_mode == "sweep_tail_and_c_class"`：
       - 卖出严格来自 `pm_plan["sell_actions"]`，买入仅有 `core_anchor_code`，金额等于净回收资金。

3. **升级 `strategy_bridge.py` 中的 `simulate_rebalance_modes_and_consequences`**：
   - 将 `scenario_mode` 及其金额参数纳入 `_simulate_single_mode`：
     - `new_cash_only`：`redemption_fee = 0.0`，`penalty_fee_7d = 0.0`，`in_transit_amount = 0.0`，`payback_days = 0`，`new_buy_amount = new_cash_amount`；
     - `withdraw_cash_only`：`subscription_fee = 0.0`，`new_buy_amount = 0.0`，`redemption_fee` 按免惩罚批次真实计算。

---

## 2. Tab 3 历史相似匹配硬编码假文案清除与动态统计 (R4)

### 2.1 核心调用链与代码现状审计

#### A. 后端真实数据生产能力 (`AGY2_FundAdvisory/strategy_bridge.py`)
在 `strategy_bridge.py` 第 5736~5866 行：
`StrategyBridge.find_historical_analogs(top_k=3)` 提取了 4 维特征向量（沪深300 MA20偏离度、MA120斜率、科创50 vs 红利60日动量差、真实ERP分位数），在 2018~2026 历史交易日中真实匹配出 Top 3 相似时期。
实测运行结果如下：
```
Match 1: date=2024-01-30, similarity=72.2%, strat_60d=+14.33%, h300_60d=+12.00%, mdd_60d=-2.62%
Match 2: date=2023-09-14, similarity=70.4%, strat_60d=-2.85%,  h300_60d=-10.37%, mdd_60d=-4.52%
Match 3: date=2022-04-07, similarity=68.9%, strat_60d=-1.38%,  h300_60d=+6.20%,  mdd_60d=-3.06%
```
后端数据结构中已完整包含：`strategy_ret_60d`、`h300_ret_60d`、`strategy_mdd_60d`、`strategy_ret_20d`、`h300_ret_20d`、`alloc_desc`！

#### B. 前端假文案与硬编码位置 (`AGY2_FundAdvisory/app_gui.py`)
在 `app_gui.py` 第 5134~5168 行：

1. **顶部横幅实盘胜率启示（第 5142 行）**：
```html
<b>【实盘胜率启示】</b>历史 3 次高度相似情景中，后 60 交易日策略平均胜率达 <b>100.0%</b>，平均绝对收益 <b>+8.5%</b>，明显战胜纯宽基基准。<br>
```
**严重作弊/假代码审计**：
- `100.0%` 和 `+8.5%` 是**直接写死的字符串常数**！
- 真实数据计算：
  - Match 1 相对超额：`14.33% - 12.00% = +2.33% > 0`（跑赢）
  - Match 2 相对超额：`-2.85% - (-10.37%) = +7.52% > 0`（跑赢）
  - Match 3 相对超额：`-1.38% - 6.20% = -7.58% <= 0`（落后）
  - 跑赢沪深300的相对超额胜率真实值是 **66.7%**，不是 100.0%！
  - 平均相对超额收益率真实值是 `(+2.33 + 7.52 - 7.58) / 3 =` **+0.76%**！
  - 策略平均绝对收益率真实值是 `(14.33 - 2.85 - 1.38) / 3 =` **+3.37%**，不是 +8.5%！
  - 平均最大回撤真实值是 `(2.62 + 4.52 + 3.06) / 3 =` **3.40%**！

2. **下方 3 张历史卡片历史镜鉴意义（第 5164~5166 行）**：
```html
<div style="font-size:10.5px; color:var(--accent-primary); font-weight:600; margin-top:6px; border-top:1px dashed var(--border-subtle); padding-top:4px;">
    💡 历史镜鉴意义：高股息与纯债底仓有效缓冲市场剧震，并在右侧反弹中实现超额Alpha。
</div>
```
**严重作弊/假代码审计**：
3 张卡片完全循环展示同一句写死的模板文案，无论该期大盘涨跌或策略表现如何，完全丧失了量化归因与镜鉴价值。

### 2.2 R4 整改技术落地方案

1. **顶部横幅动态数学统计**：
   在渲染前提取 `matches = analog_tab2.get("matches", [])`：
   ```python
   n_matches = len(matches)
   if n_matches > 0:
       wins = sum(1 for m in matches if (m.get("strategy_ret_60d", 0.0) - m.get("h300_ret_60d", 0.0)) > 0)
       win_rate_60d = (wins / n_matches) * 100.0
       avg_excess_60d = sum(m.get("strategy_ret_60d", 0.0) - m.get("h300_ret_60d", 0.0) for m in matches) / n_matches
       avg_abs_ret_60d = sum(m.get("strategy_ret_60d", 0.0) for m in matches) / n_matches
       avg_mdd_60d = sum(abs(m.get("strategy_mdd_60d", 0.0)) for m in matches) / n_matches
   else:
       win_rate_60d = 0.0
       avg_excess_60d = 0.0
       avg_abs_ret_60d = 0.0
       avg_mdd_60d = 0.0
   ```
   横幅文案动态填充：
   `<b>【实盘胜率启示】</b>历史 {n_matches} 次高度相似情景中，后 60 交易日策略跑赢沪深300的相对超额胜率达 <b>{win_rate_60d:.1f}%</b>，平均相对超额收益率 <b>{avg_excess_60d:+.2f}%</b>，策略平均绝对收益率 <b>{avg_abs_ret_60d:+.2f}%</b>，平均最大回撤仅 <b>{avg_mdd_60d:.2f}%</b>。<br>`

2. **3 张历史卡片差异化镜鉴分类归因**：
   对每个 `m in matches`，根据 `s_ret = m['strategy_ret_60d']` 与 `h_ret = m['h300_ret_60d']` 动态匹配归因分类：
   - **类别 1（双双上涨：`s_ret > 0 and h_ret > 0`）**：
     `💡 历史镜鉴意义：右侧顺势共振：底部击球区反弹期紧跟主升浪，兼顾进攻弹性与低回撤（最大回撤仅 {abs(m['strategy_mdd_60d']):.1f}%）`
   - **类别 2（逆势抗跌：`h_ret <= 0 and s_ret > h_ret`）**：
     `💡 历史镜鉴意义：逆势抗跌护盾：大盘阴跌寻底期，凭借红利与纯债底仓大幅跑赢大盘 {s_ret - h_ret:+.2f}%，守住本金安全垫`
   - **类别 3（防守代价：`h_ret > 0 and s_ret <= h_ret`）**：
     `💡 历史镜鉴意义：防守底仓代价：急跌反抽期高配纯债避险导致短期弹性收敛，但换取了熊市下半场极高本金安全度`
   - **其他备选（双双下跌但落后）**：
     `💡 历史镜鉴意义：极端下行冲击：市场流动性承压阶段，需坚守攻防底线，分批低吸优质资产`

---

## 3. 双翼看板右翼主动风险预警哨同类预警折叠聚合与紧凑布局 (R7)

### 3.1 核心调用链与代码现状审计

#### A. 预警哨后端巡检 (`AGY2_FundAdvisory/advisory_engine.py`)
在 `advisory_engine.py` 第 522~946 行：
`ActiveRiskSentry.inspect_portfolio` 对持仓进行六维巡检。
当持仓中存在多只基金满足同一维度时（例如组合中有 3 只新买入基金持有均未满 7 天，或者多只 C 类满 30 天）：
- 代码对每只基金分别 `alerts.append(...)`；
- 生成了多个独立的预警字典。

#### B. 前端渲染展开过长与单只锁定痛点 (`AGY2_FundAdvisory/app_gui.py`)
在 `app_gui.py` 第 2029~2125 行：
1. **页面撑长**：
   前端直接用循环渲染每条卡片与按钮：
   ```python
   alerts_to_show = report.get("alerts", [])[:4]
   for i, alert in enumerate(alerts_to_show):
       st.markdown(...)
       st.button(...)
   ```
   没有设置最大高度容器，4 条大卡片和 4 个全宽按钮直接竖向堆叠，右翼高度远超左翼雷达，破坏整体视口平衡；且受限于 `[:4]`，若同一维度产生 3 条预警，其他重要预警就会被截断挤出视口！
2. **无法批量处置**：
   点击“🔒 锁定【011612】调仓下界”按钮（第 2074 行）：
   ```python
   if fcode and fcode not in st.session_state.tab2_locked_funds:
       st.session_state.tab2_locked_funds.append(fcode)
   ```
   只能单个单笔将 1 只基金加入 `tab2_locked_funds`，用户若有 3~4 只新买入标的，需要反复刷新点按多次。

### 3.2 R7 整改技术落地方案

1. **同类预警折叠聚合算法**：
   在 `ActiveRiskSentry` 中新增静态/类方法 `aggregate_alerts(alerts: List[Dict[str, Any]]) -> List[Dict[str, Any]]`：
   - 遍历 `alerts`，按 `(dimension, level, action_type)` 进行聚合分组；
   - 若某组只数 `< 2`：保持原样单只卡片输出；
   - 若某组只数 `>= 2`：
     - 提取这批基金的名称和代码：`items = [(a.get("fund_name", a.get("fund_code")), a.get("fund_code")) for a in group]`；
     - 提取前 2 只简称，例如：`富国中证红利(100032)、创金合信红利低波(005561)`；
     - 聚合标题：`🔴 【未满7天锁仓红牌】{items[0][0]}({items[0][1]})、{items[1][0]}({items[1][1]}) 等 {len(group)} 只标的持有未满 7 天`；
     - 聚合描述：`严禁赎回！包含上述 {len(group)} 只标的持仓均未满 7 天，赎回直接扣除 1.50% 巨额惩罚费！`；
     - 聚合动作：`严格锁定持仓下界，一键批量加入调仓保护名单，待满 7 天后再行操作。`；
     - 标记 `action_type = "batch_lock_shares"`，并将全部基金代码保存在 `fund_codes = [it[1] for it in items]` 中。

2. **批量一键锁定加入 `tab2_locked_funds`**：
   在 `app_gui.py` 预警按钮响应中：
   - 按钮文案：`btn_lbl = f"🔒 一键批量锁定这 {len(alert['fund_codes'])} 只标的调仓下界"`；
   - 点击逻辑：
     ```python
     if "tab2_locked_funds" not in st.session_state:
         st.session_state.tab2_locked_funds = []
     for fc in alert.get("fund_codes", [fcode]):
         if fc and fc not in st.session_state.tab2_locked_funds:
             st.session_state.tab2_locked_funds.append(fc)
     st.session_state.tab2_diagnosed = True
     st.session_state.tab2_rebalanced = True
     st.session_state.tab2_rebal_cache = None
     st.toast(f"🔒 已批量锁定 {len(alert.get('fund_codes', []))} 只未满7天标的持仓下界！")
     st.rerun()
     ```

3. **紧凑布局与滚动容器**：
   - 在 `col_sentry` 预警区域外层包裹固定高度滚动容器：
     `with st.container(height=320):`（Streamlit 1.66 原生支持），或者通过 CSS 类 `.sentry-scroll-container { max-height: 320px; overflow-y: auto; padding-right: 4px; }` 包裹；
   - 每张预警卡片与处置按钮采用紧凑间距（内边距 6px 10px，底部留白 4px），确保视觉精练不撑屏。

---

## 4. 实施计划与伪代码清单

### 4.1 R3 修改清单
- **目标文件**: `AGY2_FundAdvisory/app_gui.py`
  - 调整组件位置：将场景选择模式从第 4393 行前移至第 4361 行。
  - 扩展缓存键：`cur_pool_sig` 纳入所有场景参数。
  - 参数传递：为 `simulate_rebalance_modes_and_consequences` 和 `generate_ai_rebalance_orders` 传入 `scenario_mode`, `new_cash_amount`, `withdraw_cash_amount`, `freeze_reserved_cash`, `core_anchor_code`。
- **目标文件**: `AGY2_FundAdvisory/strategy_bridge.py`
  - 升级 `generate_ai_rebalance_orders`：对 `new_cash_only`、`withdraw_cash_only` 接入 `pm_plan` 生成的真实买卖列表，禁绝错误 SELL/BUY 指令。
  - 升级 `simulate_rebalance_modes_and_consequences`：后果矩阵适配各场景，`new_cash_only` 赎回费清零。

### 4.2 R4 修改清单
- **目标文件**: `AGY2_FundAdvisory/app_gui.py`
  - 在第 5134 行前添加胜率与超额动态汇总计算逻辑。
  - 替换第 5142 行写死常数。
  - 替换第 5165 行写死镜鉴意义，替换为 3 类条件动态分支。

### 4.3 R7 修改清单
- **目标文件**: `AGY2_FundAdvisory/advisory_engine.py`
  - 新增 `ActiveRiskSentry.aggregate_alerts` 方法，当同一维度 >= 2 时折叠聚合。
- **目标文件**: `AGY2_FundAdvisory/app_gui.py`
  - 调用 `aggregate_alerts` 获取展示列表。
  - 预警列表包裹在 `st.container(height=320)` 中。
  - 新增 `batch_lock_shares` 批量锁定处置分支。

---

## 5. 调研结论
本报告针对 R3、R4、R7 进行了逐行代码级审计、实盘数据探针验证与边界压力评估：
1. 迎合性假代码与硬编码已精确定位（R4 胜率写死 100%、收益写死 8.5%、镜鉴文案全同；R3 场景前端虽画了组件却与后端真实计算断层）。
2. 底层能力已就绪（`portfolio_manager.py` 的 `generate_scenario_rebalance_plan` 数学严密，`strategy_bridge.py` 的 `find_historical_analogs` 数据真实）。
3. 改造路径明确，风险可控，无破坏性改动，符合 GEMINI.md 架构与测试隔离规范。
