# G15 Phase 1 深度代码审查与精确改造实施方案报告 (Handoff Report)

- **作者/探针**: `explorer_g15_survey_1` (Read-only Survey Agent)
- **目标工程**: `AGY2_FundAdvisory` (包含 `app_gui.py`, `portfolio_manager.py`, `advisory_engine.py`, `strategy_bridge.py`)
- **对应里程碑**: G15 第一阶段 UI/UX、去技术炫技与代码对齐缺陷根治

---

## 1. 观察记录 (Observation)

### 1.1 蒙特卡洛 3D 曲面图与因子进化 RuleTree 代码框 (Chart Vanity)
1. **3D 曲面图实现与调用点**:
   - 定义位置：`AGY2_FundAdvisory/app_gui.py:2147-2189`，函数 `def render_monte_carlo_3d_chart(stress_data: Dict[str, Any]):`。内部使用 Plotly `go.Surface(x=tiers, y=scenarios, z=z_mdd, ...)` 绘制 3D 曲面。
   - 数据生成位置：`AGY2_FundAdvisory/portfolio_manager.py:9451-9468`。在循环 `for t in ["C1", "C2", "C3", "C4", "C5"]` 时，代码执行 `mdd_row.append(pred_mdd_pct)`，即 C1 至 C5 五列填充了完全相同的单一数值 `pred_mdd_pct`。导致 3D 曲面在 X 轴方向完全平直，是纯粹为画 3D 而画 3D 的视觉伪科学。
   - 调用位置 1 (Tab 1 新资建仓)：`AGY2_FundAdvisory/app_gui.py:4252-4260`：
     ```python
     bootstrap_stress_data = pm.simulate_portfolio_cvar_bootstrap(...)
     render_monte_carlo_3d_chart(bootstrap_stress_data)
     ```
   - 调用位置 2 (Tab 2 持仓调仓)：`AGY2_FundAdvisory/app_gui.py:5038-5047`：
     ```python
     with st.expander("🔬 查看实盘持仓蒙特卡洛极端承压 3D 分布曲面图", expanded=False):
         real_stress_data = pm.simulate_portfolio_cvar_bootstrap_instance(...)
         render_monte_carlo_3d_chart(real_stress_data)
     ```
2. **因子进化 Popover 中的 RuleTree 代码框**:
   - 位置：`AGY2_FundAdvisory/app_gui.py:2973-2974`：
     ```python
     rule_expr_txt = evo_res.get("operator_rule_expression") or "RuleTree: Mom_Win=0.30*5d+0.70*20d | Vol_Pulse=exp(-1.2*pulse) | Safe_Shift=1.0+0.5*panic"
     st.code(rule_expr_txt, language="text")
     ```
   - 产生源头：`AGY2_FundAdvisory/advisory_engine.py:841-845` 与 `advisory_engine.py:1039` 生成形如 `RuleTree: Mom_Win = 0.30*5d + 0.70*20d | Vol_Pulse_Penalty = exp(...) | Panic_Safe_Shift = ...` 的技术伪代码，散户完全无法在 3 秒内读懂。

### 1.2 右翼主动风控哨红牌变黄牌与详情丢失 Bug
1. **数据源结构 (ActiveRiskSentry)**:
   - 位置：`AGY2_FundAdvisory/advisory_engine.py:2341-2405`。
   - 警报级别字段名：`alert["level"]` 返回 `"red"` (如未满7天锁仓), `"yellow"` (如临免赎倒计时/C类满30天), `"green_notice"` 等。
   - 详情描述字段名：`alert["desc"]` (例如 `"严禁赎回！未满 7 天赎回将直接触发证监会规定的 1.50% 巨额惩罚性扣款！"`)。
   - 建议操作字段名：`alert["action"]` (例如 `"锁定持仓下界，暂缓赎回，待持有满 7 天后再行操作。"`)。
   - 标题字段名：`alert["title"]` (例如 `"【创金合信红利低波A (005561)】持有仅 3 天（≤3天）"`)。
2. **前端接收端的错配与逻辑缺陷**:
   - 位置 1 (折叠栏标题): `AGY2_FundAdvisory/app_gui.py:2905-2909`：
     ```python
     top_alert = alerts_list[0]
     lvl = top_alert.get("level", "WARNING")
     act_status_icon = "🔴" if lvl == "CRITICAL" else "🟡"
     ```
     `lvl` 值为 `"red"` 时，`lvl == "CRITICAL"` 判断为 `False`，导致外部折叠栏标题的红色警报被错误显示为黄色 `🟡`！
   - 位置 2 (右翼卡片列表): `AGY2_FundAdvisory/app_gui.py:3097-3104`：
     ```python
     for alert in alerts_list[:4]:
         al_lvl = alert.get("level", "WARNING")
         border_col = "var(--color-up)" if al_lvl == "CRITICAL" else ("var(--accent-primary)" if al_lvl == "INFO" else "var(--color-neutral)")
         icon = "🔴" if al_lvl == "CRITICAL" else ("ℹ️" if al_lvl == "INFO" else "🟡")
         title_str = alert.get("title", alert.get("message", "风控提示"))
         detail_str = alert.get("detail", alert.get("message", ""))
         action_str = alert.get("suggested_action", alert.get("action", ""))
     ```
     - `al_lvl == "CRITICAL"` 不匹配 `"red"`，导致红牌左边框变成灰色中性色 `var(--color-neutral)`，图标变成黄色 `🟡`！
     - `detail_str` 仅查找 `"detail"` 和 `"message"`，完全遗漏了后端生成的核心字段 `"desc"`，导致详情文字完全变为空字符串 `""`，病因详情 100% 丢失！
     - 截取 `alerts_list[:4]` 未经过严重程度排序，被大量重复的 `"规模待核验"` 黄牌刷屏，挤占了真正的致命红牌。

### 1.3 Tab 2 DataFrame 裸英文表头与底部重复大按钮
1. **DataFrame 裸英文表头**:
   - 位置 1 (Tab 1): `AGY2_FundAdvisory/app_gui.py:4410`：
     `st.dataframe(pd.DataFrame(sample_slices), use_container_width=True, hide_index=True)`
   - 位置 2 (Tab 2): `AGY2_FundAdvisory/app_gui.py:5732`：
     `st.dataframe(pd.DataFrame(v_slices), use_container_width=True, hide_index=True)`
   - 数据源：`advisory_engine.py:3616-3622` 与 `advisory_engine.py:3668-3674` 生成的字典键名均为裸英文：
     `phase, label, vol_ratio, slice_amount, strategy`。在页面上直接以英文列名渲染给用户，极度不专业。
2. **Tab 2 底部重复的第二个全宽蓝色覆盖按钮**:
   - 位置：`AGY2_FundAdvisory/app_gui.py:5808-5819`：
     在上方已有操作栏（行 5760 保存明日预案/立即执行调仓 + 行 5801 送入回测对比）的基础上，下方又并列了一个全宽深蓝色按钮：
     `if st.button("✅ 我已在手机端按此方案下单 ➔ 一键将调仓单同步至当前账本持仓", type="primary", use_container_width=True, key="btn_confirm_follow_rebalance_tab2"):`
     用户在界面上同时看到上下两个全宽深蓝色按钮，极易引发误解与重复覆盖操作。
3. **Tab 2 持仓表下方操作按钮收纳**:
   - 目前在持仓编辑表格下方（行 5202-5271）放置了 5 列工具栏（保存修改并入库、修改现金池、同步真实净值、导出快照CSV、删除指定标的）。
   - 顶部工具栏（行 4698-4726）目前仅有：切换账本、视图模式切换、➕极速录基、🔄同步估值、⚙️账本与环境管理。
   - 缺少直接在顶部工具栏访问“批量文本导入”、“截图识别导入”与“历史撤销”的紧凑入口。

### 1.4 Tab 4 二级导航按钮堆叠与全站基金名称一致性
1. **Tab 4 二级导航堆叠与层级混淆**:
   - 位置：`AGY2_FundAdvisory/app_gui.py:6976-6983`：
     ```python
     box_tab1, box_tab2, box_tab3, box_tab4, box_tab5, box_tab6 = st.tabs([
         "📊 资产穿透与排雷",
         "🌡️ 14赛道温度计",
         "⚡ 尾盘折溢价套利",
         "🛡️ 期权防暴跌哨",
         "🌐 跨境QDII与锁汇",
         "💡 A/C端选型算费"
     ])
     ```
   - 表现：在 `media_1794236135874_90d104f5.png` 实机截图中，原生 `st.tabs` 导致 6 个选项折行成两排（4 个 + 2 个），且选中态按钮呈现深蓝色实心块，与顶层四宫格大导航形成严重视觉冲突。
2. **全站基金名称字典不一致 (以 `017436` 等标的为例)**:
   - `app_gui.py:2300`: `"017436": "华安纳斯达克100ETF联接A"` (标准名称)
   - `portfolio_manager.py:607`: `"fund_name": "华安纳斯达克100ETF联接A"`
   - `portfolio_manager.py:842` & `847`: `"name": "华安纳斯达克100A"` (不一致，简称)
   - `strategy_bridge.py:491, 588, 704, 820`: `"name": "华安纳斯达克100A"` (不一致，简称)
   - `portfolio_manager.py:2600`: `"017436": "华安纳指100"` (别名)
   - `portfolio_manager.py:283`: `if self.fund_code == "017436" and ("华宝" in self.fund_name or not self.fund_name): self.fund_name = "华安纳斯达克100ETF联接A"` (防御补丁)
   - `strategy_bridge.py:3758-3770`: 生成调仓单时仅检索 `INDEX_TO_FUND_MAP`，若未命中直接命名为 `存量标的_{code}`，且将未持有标的 holding_days 默认设为 0，导致新买标的在 `app_gui.py:5345` 被误判为“未满7天锁仓保护”。

### 1.5 “📱 手机极简盯盘视图 / 🖥️ 桌面专业模式” 架构现状
1. 目前全站无全局视图模式切换器，所有复杂的 15 列大宽表与 Plotly 图表均在手机视口（<640px）下直接展开，造成严重水平滚动与视觉压迫。
2. 散户 90% 的手机端场景仅需关注：① 今日总资产与预估盈亏、② 14:30 尾盘关键操作口令、③ 核心风险红黄牌与截图导入。

---

## 2. 逻辑推导链 (Logic Chain)

```
[Observation 1.1] 3D曲面图在C1-C5填入相同数值 + RuleTree代码框暴露晦涩字符串
       ↓ (推导: 违反“零炫技、3秒看懂”买方原则，增加认知负担)
[Step 1] 彻底删除 3D 曲面图，以 2D 三大危机对照表与人话结论替代；删除 st.code，以 2D 自适应进化机制表替代。

[Observation 1.2] Sentry后端返回 level="red", desc="...", action="..."
                  app_gui.py 仅判断 level=="CRITICAL" 并仅读取 alert["detail"]
       ↓ (推导: "red" 不匹配 "CRITICAL"，红牌强制降级为黄牌/灰边框；desc 未读取导致详情完全丢失)
[Step 2] 扩展匹配条件为 al_lvl in ("red", "critical")，并将详情取值扩展为 alert.get("desc") or alert.get("detail") or alert.get("message")。对警报按严重度排序，置顶致命风险。

[Observation 1.3] vwap_slices 字典键名为 phase, label, vol_ratio, slice_amount, strategy
                  调仓表格底部同时存在保存预案行与全宽确认下单覆盖按钮
       ↓ (推导: 表格裸露英文表头缺乏买方温度；双执行按钮导致用户盘后/盘中重复点击困惑)
[Step 3] 强制对 DataFrame 执行中文重命名映射，数字格式化；删除第二个全宽重复按钮，收纳操作栏至顶部工具栏与单行确认条。

[Observation 1.4] Tab 4 st.tabs 折行成两排 + 017436 在各字典分别叫联接A、100A、纳指100
       ↓ (推导: 二级 Tab 样式与一级大导航冲突；名称不一致造成全站单源同真失效)
[Step 4] 将 Tab 4 改造为单行 st.segmented_control (或水平单行单选)；全站统一 017436 为“华安纳斯达克100ETF联接A”，补齐 strategy_bridge 基金池检索。

[Observation 1.5] 移动端视口下 15 列大宽表产生水平滚动，散户高频盯盘痛点未满足
       ↓ (推导: 桌面工作台与手机盯盘需物理分层)
[Step 5] 在侧边栏/顶栏增加“📱 手机极简盯盘 / 🖥️ 桌面专业模式”开关，极简模式下单列卡片流精准承载 3 项核心诉求。
```

---

## 3. 局限与注意事项 (Caveats)

1. **测试用例断言容错**:
   - 部分旧单元测试（如 `tests/test_adv_final_closure.py` 或 `tests/test_phase2_apptest_gui.py`）中可能包含对旧按钮名称（如 `"我已在手机端按此方案下单"`）或旧 3D 曲面图折叠框文案（如 `"查看蒙特卡洛极端承压 3D 分布曲面图"`）的字面量断言。实施时需同步更新非只读测试断言，确保全量绿灯。
2. **只读红线防御**:
   - 严禁修改 4 个只读裁判文件：`judge_engine.py`、`holdout_vault.py`、`AGENT_SPEC.md`、`tests/test_infra.py`。
   - 严禁修改 `DataLoader.simulate_execution` 的默认签名与默认费率扣除逻辑。
3. **Streamlit 兼容性**:
   - Streamlit 1.66.1 原生支持 `st.segmented_control`。若在较旧环境回退，必须优雅 fallback 至 `st.radio(..., horizontal=True)`。

---

## 4. 改造结论与具体代码实施方案 (Conclusion & Precise Proposals)

### 4.1 课题 1：彻底砍除 3D 炫技图与 RuleTree 代码框

#### [方案 1.1] 改造 `app_gui.py:2147-2189`：用 2D 人话对照表替代 3D 曲面图
将 `render_monte_carlo_3d_chart` 函数重写为 `render_monte_carlo_stress_table`（保留兼容别名）：

```python
def render_monte_carlo_stress_table(stress_data: Dict[str, Any]):
    """渲染三大历史极端危机承压 2D 人话对照表（替代 3D 炫技曲面图）"""
    if not stress_data or not stress_data.get("scenarios"):
        return
    scenarios = stress_data.get("scenarios", [])
    tier = str(stress_data.get("investor_risk_tier", "C3"))
    risk_tol = float(stress_data.get("risk_tolerance_mdd", 15.0))

    rows = []
    for sc in scenarios:
        pred_mdd = float(sc.get("predicted_mdd_pct", 0.0))
        h300_mdd = float(sc.get("h300_mdd_pct", 0.0))
        excess = float(sc.get("excess_defense_pct", 0.0))
        loss_amt = float(sc.get("predicted_loss_amount", 0.0))
        liq_days = float(sc.get("liquidation_days", {}).get("avg_days", 4.0))
        is_breach = pred_mdd > risk_tol
        status_tag = f"🔴 超出契约 ({pred_mdd - risk_tol:+.1f}%)" if is_breach else "🟢 契约合规"

        rows.append({
            "历史极端情景": sc.get("name", ""),
            "时期背景": sc.get("period", ""),
            "组合预测最大回撤": f"-{pred_mdd:.1f}%",
            "预估浮亏金额": f"-¥{loss_amt:,.0f}",
            "同期沪深300": f"-{h300_mdd:.1f}%",
            "超额防御(少亏)": f"+{excess:.1f}%" if excess > 0 else f"{excess:.1f}%",
            f"{tier}契约红线(≤{risk_tol:.0f}%)": status_tag,
            "流动性变现天数": f"{liq_days:.1f} 天"
        })

    with st.expander("🎲 查看三大历史极端危机承压情景 2D 人话对照表", expanded=False):
        df_sc = pd.DataFrame(rows)
        st.dataframe(df_sc, use_container_width=True, hide_index=True)
        
        worst_sc = max(scenarios, key=lambda s: s.get("predicted_mdd_pct", 0.0))
        w_mdd = worst_sc.get("predicted_mdd_pct", 0.0)
        w_loss = worst_sc.get("predicted_loss_amount", 0.0)
        w_excess = worst_sc.get("excess_defense_pct", 0.0)
        w_name = worst_sc.get("name", "极端历史危机")
        breach_note = "已超出您的风险承受红线，建议增加纯债固收底仓平抑波动。" if w_mdd > risk_tol else "处于您的风险偏好承受范围以内，具备稳健的抗跌韧性。"
        
        safe_markdown_html(f"""
        <div style="background: var(--bg-elevated); border: 1px solid var(--border-subtle); border-radius: 6px; padding: 8px 12px; margin-top: 6px; font-size: 11.5px; color: var(--text-primary); line-height: 1.5;">
            💡 <b>投顾人话裁决</b>：若历史重演【{w_name}】，当前组合预计最大浮亏 <b>-¥{w_loss:,.0f} (-{w_mdd:.1f}%)</b>，比同期沪深300多抵御 <b>+{w_excess:.1f}%</b> 跌幅，{breach_note}
        </div>
        """)

# 保留原函数名兼容现有调用
render_monte_carlo_3d_chart = render_monte_carlo_stress_table
```

在 Tab 1（行 4258）与 Tab 2（行 5045）直接调用 `render_monte_carlo_stress_table`，并将 Tab 2 行 5038 的 expander 标题改为 `"🔬 查看实盘持仓极端承压 2D 对照表"`。

#### [方案 1.2] 改造 `app_gui.py:2973-2982`：消除 RuleTree 代码框
将原生 `st.code(...)` 替换为直白的人话对照表：

```python
# app_gui.py 约第 2973 行前后的替换代码：
# 彻底移除 st.code(rule_expr_txt, language="text")
mom_w = float(evo_res.get("adaptive_momentum_window", 0.30))
vol_p = float(evo_res.get("vol_pulse_penalty_coef", 1.20))
safe_s = float(evo_res.get("panic_safe_haven_shift", 0.50))
df_rule = pd.DataFrame([
    {"自适应进化机制": "动量感知窗口 (Mom_Win)", "参数设定": f"5日({mom_w*100:.0f}%) + 20日({(1.0-mom_w)*100:.0f}%)", "业务参谋意义": "平抑短线波动杂波，锁定中期主升赛道"},
    {"自适应进化机制": "波动率脉冲惩罚 (Vol_Pulse)", "参数设定": f"惩罚系数 {vol_p:.2f}", "业务参谋意义": "赛道短期波幅异动急剧放大时自动降权规避"},
    {"自适应进化机制": "恐慌避险增强 (Panic_Safe)", "参数设定": f"避险上浮 +{safe_s*100:.0f}%", "业务参谋意义": "大盘急跌错杀期优先上调红利低波与纯债权重"}
])
st.dataframe(df_rule, use_container_width=True, hide_index=True)
st.caption("💡 **进化结论**：模型根据当前波动与估值状态机自适应调节动量敏感度与波动惩罚，兼顾进攻弹性与回撤保护。")
```

---

### 4.2 课题 2：修复右翼主动风控哨对接 Bug

#### [方案 2.1] 修复 `app_gui.py:2905-2909` (折叠栏标题)
```python
        elif not all_passed and alerts_list:
            # 排序：优先提取红牌 (red/CRITICAL)
            def _top_lvl_rank(a):
                _l = str(a.get("level", "yellow")).lower()
                return 0 if _l in ("red", "critical") else 1
            sorted_alerts_top = sorted(alerts_list, key=_top_lvl_rank)
            top_alert = sorted_alerts_top[0]
            lvl = str(top_alert.get("level", "WARNING")).lower()
            act_status_icon = "🔴" if lvl in ("red", "critical") else "🟡"
            t_msg = top_alert.get("title") or top_alert.get("desc") or top_alert.get("message", "存在待关注风险")
            expander_title = f"今日投顾参谋：{t_msg} ｜ 点击展开机会雷达与十二维主动风控"
```

#### [方案 2.2] 修复 `app_gui.py:3097-3115` (右翼风控卡片列表渲染)
```python
                    # 按风险严重度与有效性排序：red/CRITICAL(0) > yellow/WARNING(1) > 规模待核验(2) > INFO(3)
                    def _sentry_alert_sorter(a):
                        _lvl = str(a.get("level", "yellow")).lower()
                        _t = str(a.get("title", "")) + str(a.get("desc", ""))
                        is_scale_unknown = "规模待核验" in _t
                        if _lvl in ("red", "critical"):
                            return (0, 0)
                        elif _lvl in ("yellow", "warning"):
                            return (1, 1 if is_scale_unknown else 0)
                        elif "green" in _lvl or _lvl in ("info", "notice"):
                            return (3, 0)
                        return (2, 0)

                    sorted_sentry_alerts = sorted(alerts_list, key=_sentry_alert_sorter)

                    for alert in sorted_sentry_alerts[:4]:
                        raw_lvl = str(alert.get("level", "WARNING")).lower()
                        is_red = raw_lvl in ("red", "critical")
                        is_yellow = raw_lvl in ("yellow", "warning")
                        is_info = raw_lvl in ("info", "green_notice", "notice")

                        if is_red:
                            border_col = "var(--color-up)"
                            icon = "🔴"
                        elif is_yellow:
                            border_col = "var(--accent-primary)"
                            icon = "🟡"
                        else:
                            border_col = "var(--color-down)" if "green" in raw_lvl else "var(--color-neutral)"
                            icon = "🟢" if "green" in raw_lvl else "ℹ️"

                        title_str = alert.get("title") or alert.get("message") or alert.get("dimension", "风控提示")
                        detail_str = alert.get("desc") or alert.get("detail") or alert.get("message", "")
                        action_str = alert.get("action") or alert.get("suggested_action", "")

                        safe_markdown_html(f"""
                        <div class="decision-card" style="border-left: 3px solid {border_col}; padding: 8px 10px; margin-bottom: 5px;">
                            <div style="font-size: 12px; font-weight: 700; color: {border_col}; margin-bottom: 2px;">
                                {icon} {title_str}
                            </div>
                            <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 2px; line-height: 1.4;">
                                {detail_str}
                            </div>
                            {f'<div style="font-size: 11px; color: var(--text-primary); font-weight: 600;">💡 应对建议: {action_str}</div>' if action_str else ''}
                        </div>
                        """)
```

---

### 4.3 课题 3：Tab 2 表头汉化与操作按钮重构

#### [方案 3.1] 汉化微观执行拆单 DataFrame 表头 (`app_gui.py:4410` 与 `app_gui.py:5732`)
```python
def format_micro_execution_slices_df(v_slices: List[Dict[str, Any]]) -> pd.DataFrame:
    """统一汉化与格式化微观执行挂单调度表"""
    if not v_slices:
        return pd.DataFrame()
    col_map = {
        "phase": "执行阶段",
        "label": "窗口类型",
        "vol_ratio": "分配比例",
        "slice_amount": "建议挂单金额(元)",
        "strategy": "微观执行策略"
    }
    df = pd.DataFrame(v_slices).rename(columns=col_map)
    if "分配比例" in df.columns:
        df["分配比例"] = df["分配比例"].apply(lambda v: f"{v*100:.0f}%" if isinstance(v, (int, float)) else str(v))
    if "建议挂单金额(元)" in df.columns:
        df["建议挂单金额(元)"] = df["建议挂单金额(元)"].apply(lambda v: f"¥{v:,.2f}" if isinstance(v, (int, float)) else str(v))
    return df
```
在 Tab 1（行 4410）与 Tab 2（行 5732）替换为：
`st.dataframe(format_micro_execution_slices_df(v_slices), use_container_width=True, hide_index=True)`

#### [方案 3.2] 统一收纳顶部工具栏与删除底部重复大按钮 (`app_gui.py:4698-4726` & `5807-5820`)
1. **重构 Tab 2 顶部工具栏 (`app_gui.py:4698`)**:
   将工具栏拓展为包含极速录基、批量文本导入、截图识别、历史撤销、同步与环境管理的清晰 6 键矩阵：
   - 切换账本下拉框
   - 主流程/工具坞模式单选
   - `➕ 极速录基` (Popover: 单只极速录基)
   - `📋 批量导入` (Popover: 批量文本粘贴或 CSV 上传)
   - `📸 截图导入` (Popover: 手机持仓长截图无损切片上传)
   - `↩️ 撤销修改` (一键 `pm.undo()`)
   - `🔄 同步估值`
   - `⚙️ 账本管理`
2. **清除底部重复的第二个全宽蓝色覆盖按钮 (`app_gui.py:5807-5820`)**:
   彻底删除行 5809 的全宽独立按钮：
   `if st.button("✅ 我已在手机端按此方案下单 ➔ 一键将调仓单同步至当前账本持仓", ...):`
   合并为单行 3 等分操作栏：
   - 列 1: `✅ 采纳并写入当前账本` (盘后显示为 `📌 保存明日预案`)
   - 列 2: `📋 复制下单小抄` (点击复制紧凑下单指令)
   - 列 3: `📈 送入回测对比` (原样保留)

---

### 4.4 课题 4：Tab 4 二级导航改造与全站基金名称归一

#### [方案 4.1] Tab 4 改造为单行紧凑分段切换器 (`app_gui.py:6976-6983`)
```python
    sub_modules = [
        "📊 资产穿透与排雷",
        "🌡️ 14赛道温度计",
        "⚡ 尾盘折溢价套利",
        "🛡️ 期权防暴跌哨",
        "🌐 跨境QDII与锁汇",
        "💡 A/C端选型算费"
    ]
    if hasattr(st, "segmented_control"):
        sel_sub_mod = st.segmented_control(
            "穿透深度工具导航",
            options=sub_modules,
            default=sub_modules[0],
            key="tab4_sub_nav_seg",
            label_visibility="collapsed"
        ) or sub_modules[0]
    else:
        sel_sub_mod = st.radio(
            "穿透深度工具导航",
            options=sub_modules,
            horizontal=True,
            key="tab4_sub_nav_rad",
            label_visibility="collapsed"
        )

    # 严格单列无折行渲染当前选中子模块
    if sel_sub_mod == "📊 资产穿透与排雷":
        # 原 box_tab1 内容
        ...
    elif sel_sub_mod == "🌡️ 14赛道温度计":
        # 原 box_tab2 内容
        ...
    elif sel_sub_mod == "⚡ 尾盘折溢价套利":
        # 原 box_tab3 内容
        ...
    elif sel_sub_mod == "🛡️ 期权防暴跌哨":
        # 原 box_tab4 内容
        ...
    elif sel_sub_mod == "🌐 跨境QDII与锁汇":
        # 原 box_tab5 内容
        ...
    elif sel_sub_mod == "💡 A/C端选型算费":
        # 原 box_tab6 内容
        ...
```

#### [方案 4.2] 全站基金名称字典归一
1. **统一 `017436` 标准名称为 `"华安纳斯达克100ETF联接A"`**:
   - `portfolio_manager.py:842` & `847`: 将 `"name": "华安纳斯达克100A"` 修正为 `"name": "华安纳斯达克100ETF联接A"`。
   - `strategy_bridge.py:491, 588, 704, 820`: 将 `"name": "华安纳斯达克100A"` 修正为 `"name": "华安纳斯达克100ETF联接A"`。
   - `portfolio_manager.py:2600`: 保持别名同时确保 `resolve_fund_meta("017436")["fund_name"]` 严格返回 `"华安纳斯达克100ETF联接A"`。
2. **修复 `strategy_bridge.py:3758-3770` 产生 `存量标的_XXXXXX` 缺陷**:
   在 `strategy_bridge.py` 中，当目标标的代码不在当前持仓且不在 `INDEX_TO_FUND_MAP` 时，依次检索 `CORE_STRATEGY_POOL`、`EXTENDED_FUND_CATALOG` 与 `pm.resolve_fund_meta(code)`：
   ```python
   if not fund_name:
       meta_c = CORE_STRATEGY_POOL.get(code) or EXTENDED_FUND_CATALOG.get(code)
       if meta_c:
           fund_name = meta_c.get("fund_name") or meta_c.get("name")
           share_class = meta_c.get("share_class", "A")
   if not fund_name:
       fund_name = PortfolioManager.resolve_fund_meta(code).get("fund_name", "")
   if not fund_name:
       fund_name = f"优选标的_{code}"
   ```
   同时，当 `h is None` 时，将 `h_holding_days` 设为 `None` (或 `-1` 代表新买未持有)，在 `app_gui.py:5345` 将锁仓判断限定在 `mv > 0 and diff_amt <= 0`，彻底消灭新买标的被标为“未满7天锁仓”的严重 Bug。

---

### 4.5 课题 5：“📱 手机极简盯盘视图 / 🖥️ 桌面专业模式” 架构落地

#### [方案 5.1] 顶栏/侧边栏一键切换开关配置
在 `app_gui.py` 侧边栏顶部或主标题旁放置模式开关：
```python
if "app_view_layout_mode" not in st.session_state:
    st.session_state.app_view_layout_mode = "🖥️ 桌面专业模式"

with st.sidebar:
    st.session_state.app_view_layout_mode = st.radio(
        "📱 视图模式切换",
        ["🖥️ 桌面专业模式", "📱 手机极简盯盘"],
        index=0 if st.session_state.app_view_layout_mode == "🖥️ 桌面专业模式" else 1,
        horizontal=True,
        key="sb_view_layout_radio"
    )
```

#### [方案 5.2] 手机极简视图三大卡片流渲染
当 `st.session_state.app_view_layout_mode == "📱 手机极简盯盘"` 时，跳过 4 列大卡、双翼折叠与 4 大 Tab 的宽幅渲染，直接输出紧凑单列流：

```python
if st.session_state.app_view_layout_mode == "📱 手机极简盯盘":
    # ① 今日总资产与预估盈亏卡片
    pnl_sign = "+" if est_pnl >= 0 else ""
    safe_markdown_html(f"""
    <div class="decision-card" style="border-left: 4px solid var(--accent-primary); padding: 14px 16px; margin-bottom: 12px; border-radius: 10px;">
        <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 2px;">📱 账户总资产</div>
        <div style="font-size: 28px; font-weight: 800; color: var(--text-primary); font-family: monospace;">¥{total_cur_equity:,.2f}</div>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 8px; padding-top: 8px; border-top: 1px dashed var(--border-subtle); font-size: 12.5px;">
            <span>今日预估: <b style="color: {pnl_color}; font-size: 14px;">{pnl_sign}¥{est_pnl:,.2f} ({est_pnl_pct:+.2f}%)</b></span>
            <span>累计浮盈: <b style="color: {tot_pnl_color};">¥{_t2_pnl:+,.2f}</b></span>
        </div>
        <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">
            可用现金 ¥{pm.available_cash:,.2f} ｜ 在途 ¥{pm.in_transit_cash:,.2f}
        </div>
    </div>
    """)

    # ② 14:30 尾盘关键操作指令
    clock_g = clock.get_action_guidance_for_window()
    c_status = "🟢 14:30 黄金操作窗口（适合尾盘估值锚定下单）" if clock.is_golden_window else ("🟡 盘中观察期（建议等待 14:30 趋势确认）" if not clock.is_after_market else "🔴 盘后已关账（按明日 15:00 净值成交）")
    
    # 获取精炼下单建议
    orders_brief = []
    if pm.holdings:
        for fc, h in list(pm.holdings.items())[:3]:
            if int(getattr(h, "holding_days", 30)) < 7:
                orders_brief.append(f"🔒 {h.fund_name} ({fc}): 未满7天锁仓保护，禁卖")
    if not orders_brief:
        orders_brief.append("✅ 今日组合结构健康，维持底仓安心持仓吃息，无强制调仓要求")

    safe_markdown_html(f"""
    <div class="decision-card" style="border-left: 4px solid var(--color-down); padding: 14px 16px; margin-bottom: 12px; border-radius: 10px;">
        <div style="font-size: 13.5px; font-weight: 700; color: var(--text-primary); margin-bottom: 4px;">
            ⏱️ 14:30 尾盘操作指令
        </div>
        <div style="font-size: 11.5px; color: var(--text-muted); margin-bottom: 8px;">
            {c_status}
        </div>
        <div style="font-size: 12.5px; color: var(--text-primary); line-height: 1.6; background: rgba(37,99,235,0.06); padding: 8px 12px; border-radius: 6px;">
            {'<br>'.join(orders_brief)}
        </div>
    </div>
    """)

    # ③ 持仓红黄牌风险提醒与截图导入入口
    if alerts_list:
        safe_markdown_html("<div style='font-size: 13.5px; font-weight: 700; color: var(--text-primary); margin-bottom: 6px;'>🚨 核心风险提醒</div>")
        for al in sorted(alerts_list, key=_sentry_alert_sorter)[:3]:
            _lvl = str(al.get("level", "yellow")).lower()
            _col = "var(--color-up)" if _lvl in ("red", "critical") else "var(--accent-primary)"
            _ic = "🔴" if _lvl in ("red", "critical") else "🟡"
            _title = al.get("title") or al.get("message", "风控提醒")
            _desc = al.get("desc") or al.get("detail", "")
            safe_markdown_html(f"""
            <div class="decision-card" style="border-left: 3px solid {_col}; padding: 8px 12px; margin-bottom: 6px; border-radius: 6px;">
                <div style="font-size: 12px; font-weight: 700; color: {_col};">{_ic} {_title}</div>
                <div style="font-size: 11px; color: var(--text-secondary); margin-top: 2px;">{_desc}</div>
            </div>
            """)

    safe_markdown_html("<div style='height: 8px;'></div>")
    st.markdown("##### 📸 手机持仓长截图一键更新")
    mob_img = st.file_uploader("上传支付宝/天天基金/招行/且慢手机长截图", type=["png", "jpg", "jpeg", "webp"], key="mob_uploader_feed")
    if mob_img:
        st.success(f"已接收截图【{mob_img.name}】，点击切换至【桌面专业模式】查看结构化切片解析与平账表。")

    # 停止后续桌面端复杂 Tab 渲染
    st.stop()
```

---

## 5. 独立验证方法 (Verification Method)

### 5.1 自动化单元测试验证
执行以下命令核验红线与功能完整性：
```bash
pytest tests/test_infra.py
pytest tests/test_adv_final_closure.py
pytest tests/test_delta_m1_guardrails.py
```
**断言验证目标**:
1. `ActiveRiskSentry().inspect_portfolio(...)` 返回的 `alerts` 中包含 `level in ("red", "yellow")` 与完整的 `desc` 和 `action` 字段。
2. `render_monte_carlo_stress_table` 正常执行，无任何 Plotly 3D Surface 渲染错误。
3. `pd.DataFrame(v_slices).rename(...)` 包含标准中文列名 `执行阶段, 窗口类型, 分配比例, 建议挂单金额(元), 微观执行策略`。
4. `017436` 在各核心池反查中均能唯一确定返回 `"华安纳斯达克100ETF联接A"`。

### 5.2 页面走查验证 (Browser Verification)
1. 访问 `http://localhost:8501`:
   - 检查首屏投顾折叠栏与展开后右翼：当持仓包含未满 7 天标的时，确认徽章与左边框为明艳鲜红 `🔴`，且完整展示“严禁赎回！持仓仅 X 天未满 7 天，赎回直接扣除 1.50% 惩罚费！”描述文字。
   - 检查因子进化 Popover：确认晦涩的 RuleTree 伪代码框已彻底消失，呈现为规整的 2D 参数机制表。
   - 检查 Tab 1 与 Tab 2：确认 3D 曲面图已彻底消失，呈现为 2D 历史危机承压人话对照表。
   - 检查 Tab 2 调仓表格：确认微观执行表头全部为纯中文，调仓单底部仅保留一行清晰操作按钮（无第二个重复的全宽蓝色覆盖按钮）。
   - 检查 Tab 4 穿透工具：确认二级导航为整齐的单行分段切换器，零折行，零视觉层级冲突。
   - 切换侧边栏“📱 手机极简盯盘”：确认全屏无水平滚动，单列呈现总资产、14:30 操作指令、核心红黄牌与截图上传入口。

### 5.3 失效与打回条件 (Invalidation Conditions)
1. 任何一个只读裁判文件被修改（`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`）。
2. 首屏或右翼预警中红牌再次呈现为黄色中性框，或描述文字再次出现空白。
3. Tab 2 微观执行表出现任何未经汉化的 `phase` 或 `vol_ratio` 英文表头。
4. Tab 4 二级子 Tab 再次折行为两行大实心按钮。
