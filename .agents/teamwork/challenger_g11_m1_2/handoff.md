# G11 Milestone 1 (Tab 1 State Transitions, Module 3 Actions & Bottom Drawer) Challenger Report

> **Agent**: `challenger_g11_m1_2` (Roles: critic, specialist)  
> **Working Directory**: `d:\Google\Workspace\Wind\.agents\teamwork\challenger_g11_m1_2\`  
> **Target Under Review**: `AGY2_FundAdvisory/app_gui.py` (Top Area, Wing Dashboard Jump, Tab 1 Actions & Bottom Drawer Expander)  
> **Timestamp**: 2026-11-08T13:20:00Z  

---

## 1. Observation (直观观测事实与证据)

在针对 `AGY2_FundAdvisory/app_gui.py` 进行对抗性压力测试与动态状态机走查中，直接观测到以下事实：

1. **Tab 1 模块 3 操作栏 (Action Bar Popovers & Buttons)**:
   - **覆盖写入当前账本 (`chk_confirm_t1_overwrite` + `btn_apply_bp_tier`)**:
     - `app_gui.py` 行 4017–4054: 采用 `with st.popover(f"📥 覆盖写入当前账本 ({cur_name})")`，内含红底警告区、目标账本名与 ID、现有存量只数、总资产、在途订单及新方案拟投入本金。
     - 门禁复选框 `chk_confirm_t1_overwrite` (默认 `value=False`) 强力控制 `btn_apply_bp_tier` 的 `disabled=not chk_confirm`。实测未勾选时按钮物理禁用；勾选后点击触发 `pm.apply_zero_start_blueprint`，并写入 `st.session_state["tab1_overwrite_success"]`。
     - 行 3979–4005: 覆盖成功后渲染提示条并露出 `btn_undo_t1_overwrite` 与 `btn_goto_t2_after_bp`。实测点击撤销通过 `pm.undo()` 100% 恢复原有持仓与现金；点击前往调仓正确设置 `tab2_view_mode = "🎯 持仓诊断与智能调仓 (主流程)"` 并触发跨 Tab 跳转。
   - **另存为全新独立账本 (`btn_confirm_save_new_ledger`)**:
     - `app_gui.py` 行 4056–4088: Popover 内部提供 `t1_save_new_name`、`t1_save_new_type` (sandbox/family/live) 与 `t1_save_new_tier`。
     - 点击后调用 `mlm_inst.create_ledger` 生成全新物理账本，通过 `new_pm.apply_zero_start_blueprint` 写入持仓并持久化，调用 `switch_active_ledger(new_lid)` 切换。
     - 实测主实盘文件 `portfolio_ledger.json` 的 SHA256 哈希值在创建并写入新账本前后保持 100% 严格一致，零跨账本污染。
   - **下单小抄 Popover (`active_cheat_sheet_text`)**:
     - `app_gui.py` 行 4090–4094: 采用 `st.popover("📱 下单小抄")` 并以 `st.code(active_cheat_sheet_text, language="text")` 渲染。
     - 在单笔全额建仓、稳健三步分批（50%底仓+30%网格+20%右侧）及智能定投（扣款乘数+微观执行滑点节省）三种节奏下，小抄均自动生成格式完备、含标的代码、买入金额、分红方式及实操指引的纯文本。
   - **送入穿透回测 (`btn_send_bp_to_bt`)**:
     - `app_gui.py` 行 4096–4100: 点击后设置 `st.session_state.selected_backtest_weights = dict(cur_opt_w)`、`st.session_state.selected_backtest_target = "新建仓组合"` 及 `st.session_state.tab3_backtest_activated = True`。
     - 行 6416 与 6459: Tab 3 成功检测到 `has_t1 == True`，在目标方案选择器 `sel_backtest_target_type` 候选项中动态挂载 `🌱 Tab 1 最新建仓方案 ({len(t1_w)}只)`，整个回测画布无崩溃、无异常。

2. **双翼看板跳转按钮 (`btn_master_action_switch`) 与跨区状态联动**:
   - `app_gui.py` 行 2720–2780:
     - 4 种账户/市场状态下动态呈现：
       - ① 存在 `<7d` 惩罚期持仓：🔴 状态，标题含 `【锁定防御】`，按钮 `👉 查看锁仓保护`，目标 Tab 1；
       - ② 存在其他主动风控预警：🟡 状态，标题含 `【时机就绪】`，按钮 `👉 查看今日调仓单`，目标 Tab 1；
       - ③ 空仓状态（`len(pm.holdings) == 0`）：🚀 状态，标题含 `【空仓建仓】`，按钮 `👉 立即开始新资建仓`，目标 Tab 0；
       - ④ 持仓健康平稳：🟢 状态，标题含 `【按兵不动】`，按钮 `👉 检视持仓账本`，目标 Tab 1。
     - 点击 `btn_master_action_switch` 后，写入 `pending_cross_tab_jump` 与 `last_cross_tab_action` 字典。
   - 行 3144–3196: 在下一个 Rerun 中，`pending_cross_tab_jump` 触发真实的 DOM 标签切换与平滑滚动 JS 脚本注入，并立即执行 `st.session_state.pop("pending_cross_tab_jump", None)`，物理杜绝无限跳转死循环；同时 `last_cross_tab_action` 在 `session_state` 中永久留存供后续审计。

3. **底部唯一白盒折叠抽屉子组件稳定性**:
   - `app_gui.py` 行 4103–4450: `with st.expander("🔬 展开机构级量化压力测试与选基白盒证据", expanded=False)`：
     - 跨牛熊滚动胜率卡：3 周期（1/2/3年）胜率、中位年化、正收益概率、跑赢货基概率及 CVaR 数学定义子展开框正常解析；
     - 5 张大字号人话指标卡（最好情况、最坏情况、水下回本天数、目标胜率、适合资金）正常渲染；
     - 组合内生股息与票息安全垫卡片（年化收益与加权息率）正常渲染；
     - 历史三大黑天鹅极端承压测试卡片与 10,000 次蒙特卡洛块重采样 CVaR 99% 卡片正常解析；
     - 蒙特卡洛 3D 曲面图（Plotly Surface）正常生成三大危机情景与 C1~C5 风险等级曲面；
     - 全市场选基漏斗 4 指标、六维评分公式 Popover、`quant_table` 数据表及 `alts_map` 赛道冠军备选替换下拉框正常联动；
     - 宏观决策信号 4 卡（ERP、MA20/ER20/动量加速度、DR007、iVIX）正常渲染；
     - 大额订单流动性折价明细表（ADV、AUM、折价基点、优化节省金额）正常渲染；
     - 智能定投执行调度表正常渲染。

4. **自动化测试执行结果**:
   - `py -3 -m pytest tests/test_challenger_g11_m1_actions.py -k "not test_apptest"`：
     `7 passed in 23.90s` (100% 通过)。
   - `py -3 -m pytest tests/test_challenger_g11_m1_actions.py -k test_apptest_tab1_module3_and_wing_switch_e2e`：
     `1 passed in 40.69s` (100% 通过)。
   - `py -3 -m pytest tests/test_challenger_g11_m1_actions.py -k test_apptest_tab1_interactive_button_clicks`：
     `1 passed in 49.66s` (100% 通过)。
   - `py -3 -m pytest tests/test_challenger_g11_m1_actions.py`：
     `9 passed in 94.16s` (全量 9 项测试 100% 绿灯)。
   - `py -3 -m pytest tests/test_infra.py`：
     `14 passed in 5.05s` (四个只读裁判文件 100% 守死)。

---

## 2. Logic Chain (推理链条与论证)

1. **状态机与操作按钮完整性推演 (基于 1.1)**:
   - 原界面中步骤二与步骤三割裂，且缺乏对覆盖存量账本的防误触门禁。
   - 重构后的 Module 3 将覆盖当前账本与另存为新账本收纳为 Popover 弹出框。测试验证：
     - 未勾选 `chk_confirm_t1_overwrite` 时，按钮处于不可点击状态，有效防止误操作清空实盘；
     - 勾选确认后执行覆盖写入，能够自适应一次性、三步建仓与定投三种模式，将待买入资金或分批订单精准分配到持仓和保留现金中；
     - 覆盖后留存快照，点击 Undo 按钮能通过 `pm.undo()` 分厘不差恢复原始持仓；
     - 另存为新账本利用 `MultiLedgerManager` 生成独立的物理 JSON 文件，对主实盘文件做 SHA256 哈希比对确认零改动，满足账本间强物理隔离要求；
     - 下单小抄能够在三种建仓节奏下自适应生成对应格式的指导文本；
     - 送入穿透回测按钮成功将新建仓方案的权重注入 Session State，使 Tab 3 在无异常的情况下承接并列出该方案。
   - 因此，Module 3 的 4 大动作按钮与 Popover 弹窗交互逻辑严谨、状态自洽。

2. **双翼看板跳转与跨区事件防循环推演 (基于 1.2)**:
   - 双翼看板折叠框标题与右侧跳转按钮根据组合持仓实时状况判定优先级（锁定防御 > 异动调仓 > 空仓建仓 > 稳健吃息）。
   - 用户点击跳转按钮后，系统触发 `st.rerun()`，下一轮由顶层捕获 `pending_cross_tab_jump` 注入前端 DOM 切换 JS，随后立即 `pop` 清除该键。
   - 该消费-清除机制有效避免了在后续组件交互或参数调整时重复触发 Tab 跳转；同时保留 `last_cross_tab_action` 供工作区记录用户最近操作。

3. **白盒证据抽屉多维量化健壮性推演 (基于 1.3)**:
   - 底部抽屉收纳了多项重型量化计算（滚动胜率、黑天鹅历史回放、蒙特卡洛 10,000 次块重采样、选基漏斗与流动性折价）。
   - 在测试中，即使面对极限本金、零持仓或自定义标的替换，所有渲染函数（`render_black_swan_stress_card`、`render_monte_carlo_3d_chart`、`render_liquidity_haircut_table` 等）均具备良好的入参防御和异常兜底（内部均有 try-except 或空值判断），展开折叠面板时 0 白屏、0 异常抛出。

---

## 3. Caveats (注意事项与假设)

1. **只读裁判文件与底线隔离**:
   - 四大只读裁判文件（`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`）哈希未发生任何改变，14 项基础设施测试 100% 绿灯。
   - 本 Challenger 遵守 Review-only 原则，未修改任何生产业务代码（`AGY2_FundAdvisory/app_gui.py` 或量化引擎），所有测试均在独立测试文件 `tests/test_challenger_g11_m1_actions.py` 中编写并执行。
2. **Tab 3 方案选择器默认选中项 UX 观察**:
   - 当点击 Tab 1 的“送入穿透回测”按钮后，Tab 3 的目标方案候选项中成功动态挂载了 `🌱 Tab 1 最新建仓方案`，但此时 `sel_backtest_target_type` 下拉框的默认选中项仍为索引 0 的当前主实盘账本，用户需在下拉框中手动点选 Tab 1 方案进行对比。这属于纯界面体验层面的默认索引偏好，并不影响回测功能的正确性与稳定性。

---

## 4. Conclusion (结论)

经过多维度对抗性测试与 Streamlit AppTest 实机走查验证：
1. **Module 3 操作栏**: 覆盖写入当前账本（含防误触复选框门禁与一键 Undo）、另存为全新独立账本（多账本物理隔离哈希未变）、下单小抄格式生成、送入穿透回测均具备完全的经验正确性与状态原子性；
2. **双翼看板跳转**: 4 档状态机判定准确，`pending_cross_tab_jump` 注入与自清除机制完备，`last_cross_tab_action` 状态持久化可靠；
3. **底部白盒抽屉**: 包含跨牛熊滚动胜率、历史黑天鹅、蒙特卡洛 3D 曲面图、选基漏斗及流动性折价明细表在内的全部子组件在展开时均稳定运行，0 异常崩溃；
4. **裁决结果**: **EMPIRICAL CORRECTNESS: PASSED (经验实证正确性：通过)**。

---

## 5. Verification Method (独立复核与重现指令)

后续代理、审阅员或协调器可通过执行以下指令独立复现本次全部测试结果：

```powershell
# 1. 运行基础设施与只读裁判守卫测试 (14 passed)
py -3 -m pytest tests/test_infra.py

# 2. 运行 Challenger 专项对抗性逻辑测试 (7 passed in ~24s)
py -3 -m pytest tests/test_challenger_g11_m1_actions.py -k "not test_apptest"

# 3. 运行 Tab 1 Module 3 与双翼看板 AppTest E2E 测试 (1 passed in ~41s)
py -3 -m pytest tests/test_challenger_g11_m1_actions.py -k test_apptest_tab1_module3_and_wing_switch_e2e

# 4. 运行 Tab 1 动作按钮交互点击与状态跳转 AppTest 测试 (1 passed in ~50s)
py -3 -m pytest tests/test_challenger_g11_m1_actions.py -k test_apptest_tab1_interactive_button_clicks

# 5. 全量 9 项 Challenger 对抗性套件一次性回归
py -3 -m pytest tests/test_challenger_g11_m1_actions.py
```

### Invalidation Conditions (失效判定)
- 若未勾选 `chk_confirm_t1_overwrite` 时仍能执行覆盖写入，则判定失败。
- 若另存为新账本导致主实盘文件哈希值改变，则判定失败。
- 若双翼看板跳转按钮触发后导致页面进入无限循环跳转，则判定失败。
- 若展开底部白盒抽屉时发生任何 unhandled exception 或界面白屏，则判定失败。
