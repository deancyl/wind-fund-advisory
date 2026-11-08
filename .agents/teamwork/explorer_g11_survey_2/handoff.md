# Tab 2 (持仓调仓) 极简三块式重构调研报告与实施规划

## 1. 观察事实 (Observation)

### 1.1 Tab 2 在 `AGY2_FundAdvisory/app_gui.py` 中的范围与定位
- **入口与边界**：Tab 2 从第 4652 行 `with tab_holdings_and_rebalance:` 开始，至第 6485 行结束（共 1,834 行代码）。第 6489 行开始为 Tab 3（组合回测）。
- **顶层标题与步骤指示器**：
  - `L4656`: `st.subheader("💼 持仓调仓")`
  - `L4657`: `st.caption("穿透分析实盘持仓账本，研判五维调仓时机，精算调仓后果与生成执行清单。")`
  - `L4677-4684`: `render_workflow_step_indicator(["查看当前持仓与启动AI诊断", "AI综合裁决与调仓时机", "模拟调仓后果与生成执行单"], current_step=step_tab2, ...)`
- **主动风控指令横幅**：`L4687-4719`，检测 `tab2_locked_funds`、`tab2_pending_take_profit`、`tab2_c_replace`，提供清除按钮 `btn_clear_tab2_risk_orders`。

### 1.2 现有布局痛点与元素冗余现状
- **分段标题冗余**：
  - `L4723`: `st.markdown("### 步骤一：持仓账本")`
  - `L5327`: `st.markdown("### 步骤二：时机裁决")`
  - `L5449`: `st.markdown("### 步骤三：方案执行")`
- **分散的多账本与环境控制栏**：
  - `L4751-4839`: `st.columns([4.2, 1.8, 1.8, 2.2])`，包含账本选择框 `sel_tab2_ledger_picker_{active_lid}`、`➕ 新建账本` Popover、`📋 克隆当前副本` Popover、`⚙️ 账本管理` Popover。
  - `L4850-4859`: 独立单选切换器 `rad_tab2_view_mode`（主流程 vs 宽屏工具坞）。
  - `L4878-4916`: 散落的 3 个全宽环境按钮：`btn_tab2_load_demo`（载入演示组合）、`btn_tab2_undo`（撤销上次修改）、`btn_tab2_sync`（全局同步估值）。
  - `L5008-5076`: 持仓表上方独立占用一行的 `➕ 极速录基` Popover。
  - 围绕账本操作与环境管理散落了 8 个以上控件，垂直浪费超过 200px。
- **叠床架屋的双套 4 宫格与图表侵占首屏**：
  - `L4863-4866`: `render_portfolio_cushion_and_stress_card_html(_cushion_model)`，渲染 4 格安全垫卡片（加权Beta、安全垫厚度、破净临界、年化票息）+ 大段小作文 + 折叠详情。
  - `L4868-4876`: `render_monte_carlo_3d_chart(real_stress_data)` 蒙特卡洛 3D 曲面图直接暴露在表格上方，将持仓表推移至首屏折叠线以下！
  - `L4937-5001`: 又渲染第二套 4 张大指标卡（`t2_c1`: 持仓总市值、`t2_c2`: 可用现金池、`t2_c3`: 累计浮动盈亏、`t2_c4`: 锁仓与超额概览）。两套 4 宫格指标大量重叠、严重浪费纵向空间。
- **分步割裂的推进按钮与小作文轰炸**：
  - `L5299-5318`: 底部提供 `btn_tab2_diagnose`（诊断）与 `btn_tab2_all`（一键执行全案）两个按钮。
  - `L5354-5363`: 步骤二时机裁决巨型带框横幅。
  - `L5365-5397`: 4 张时机裁决卡片（均线突破、申赎时钟、偏离度与净效用、FIFO锁定期）。
  - `L5400-5435`: 巨型蓝色提示框（调仓净效用门禁精算，Net Utility Gate）。
  - `L5439-5442`: 中间又拦了一道按钮 `btn_t2_step_to_reb`（“⚖️ 模拟调仓方案与成本”），迫使用户进行二次点击。
  - `L5625-5674`: 步骤三又出现 4 张真实后果卡片（手续费损耗、T+2在途风险、攻防回撤、持有期清零）。
  - `L5675-5711`: 第二次重复出现巨型蓝色 Net Utility Gate 提示框。
  - `L5765-5775`: 第三次出现 Net Utility Delta U 文本框。
  - `L5820-5915`: 调仓建议执行单表格 `df_orders_tbl` 被挤到页面极深处（需向下滚动 3~4 屏才能看到）。

### 1.3 核心依赖状态键与关键函数
- **状态机键**：
  - `active_ledger_id`: 当前账本 ID（默认 `"main_live"`）
  - `sel_tab2_active_ledger`: 在 `test_gui_multi_ledger_stress.py` 中被 AppTest 显式断言的控件键
  - `tab2_view_mode` / `rad_tab2_view_mode`: 双视图模式切换（主流程 `is_t2_main_mode` vs 运维工具坞）
  - `tab2_diagnosed`, `tab2_rebalanced`, `tab2_trigger_diagnose`, `tab2_trigger_rebalance`
  - `tab2_diag_cache`, `tab2_rebal_cache`, `tab2_last_pool_sig`
  - `tab2_locked_funds`, `tab2_pending_take_profit`, `tab2_c_replace`
  - `rebalance_buffer_pct`: 缓冲带阈值（默认 3.0）
  - `tab2_rebal_buf_slider`: 唯一滑块控件键（测试严格断言全局仅出现 1 次）
  - `# tab2_rebal_buf_slider_bot`: 兼容注释标记（测试严格断言必须存在）
  - `tab2_cached_edited_table`: 持仓编辑表临时缓存
  - `main_holdings_editor_tab2`: `st.data_editor` 绑定的键
  - `btn_bar_add_holding`: 极速录基添加按钮键
  - `btn_confirm_cash_pop_tb`: 现金修改确认按钮键
  - `btn_sync_holdings_tab2`: 同步真实净值按钮键
  - `btn_pop_del_confirm_tab2`: 删除标的确认按钮键
  - `btn_confirm_follow_rebalance_tab2`: 一键跟单打卡按钮键
  - `sel_tab2_vwap_schedule_item`: VWAP 挂单调度选择器键
- **自动化测试关键断言引用**：
  - `tests/test_g8_ux_and_realtime_fusion.py`:
    - `assert "rad_tab2_view_mode" in src`
    - `assert "is_t2_main_mode" in src`
    - `assert "dock_tab1, dock_tab2, dock_tab3, dock_tab4, dock_tab5, dock_tab6" in src`
    - `assert "sub_tab1, sub_tab2, sub_tab3" in src`
    - `assert "<b>{len(pm.holdings)} 只</b>" in src`
    - `assert 'if "edited_table" in locals() and edited_table is not None:' in src`
    - `assert "tab2_rebal_buf_slider_bot" in src`
    - `assert "tab2_rebal_buf_slider" in src`
    - `assert "warn_placeholder = st.empty()" in gui_src`
    - `assert "_has_uncommitted_holdings_changes(edited_table, pm)" in gui_src`
    - `assert "btn_bar_add_holding" in gui_src`
    - `assert "btn_confirm_cash_pop_tb" in gui_src`
    - `assert "btn_sync_holdings_tab2" in gui_src`
    - `assert "btn_pop_del_confirm_tab2" in gui_src`
  - `tests/test_challenger_g9_m2_adversarial.py`:
    - `assert "dock_tab1" in else_code`
    - `assert "dock_tab1, dock_tab2" not in body_code`
    - `slider_keys = re.findall(r'key=["\']tab2_rebal_buf_slider["\']', code); assert len(slider_keys) == 1`
  - `tests/test_g3_evolution_loop.py`:
    - `assert "vwap_rebal_orders" in src`
    - `assert "买入快速冲击模拟损耗" in src`
    - `assert "sel_tab2_vwap_schedule_item" in src`
  - `tests/test_g10_correlation_liquidity_and_stress.py`:
    - `assert "render_monte_carlo_3d_chart" in code`
    - `assert "render_liquidity_haircut_table" in code`

---

## 2. 逻辑链推演 (Logic Chain)

1. **步骤指示器与副标题的视觉开销 (对应 R1 & R2)**：
   - 当前在 `L4657` 渲染了 caption，在 `L4677-4684` 渲染了三步骤胶囊指示器 `render_workflow_step_indicator`。
   - 胶囊条高度约 48px，且向导式心智（Step 1 -> 2 -> 3）割裂了用户的一体化工作流。
   - 彻底删除 `render_workflow_step_indicator` 与 caption 后，页面垂直高度立即释放 60px 以上，首屏能直接呈现核心操作工具栏与资产顶栏。

2. **工具栏集中化（收纳散落按钮与录基吧台，对应 R2 Tab 2 模块 1）**：
   - 目前界面在多处分散放置了账本切换、新建、克隆、管理、视图切换、录基吧台、环境管理（演示组合、撤销、同步）等 8 处控件。
   - 通过将它们全部收敛至第一行（单行全能账本工具栏）：
     `col_tb_led, col_tb_mode, col_tb_quick, col_tb_sync, col_tb_mgr = st.columns([2.6, 3.2, 1.4, 1.3, 1.5])`
     - 账本选择下拉框保持在最左；
     - 双视图切换 `rad_tab2_view_mode` 置于其右；
     - `➕ 极速录基` 收敛为弹窗 Popover，保留原有全部表单与自动入库校验逻辑（内部包含 `btn_bar_add_holding`），平常状态 0 占高；
     - `🔄 同步估值` 按钮单行内联；
     - `⚙️ 账本与环境管理` Popover 集中收纳：新建独立账本、克隆副本、重命名、删除、载入演示组合（`btn_tab2_load_demo`）、撤销上次修改（`btn_tab2_undo`）及家庭资产汇总。
   - 这样不仅消除了主界面上原本霸占整行的 5 列录基吧台和 3 个散落环境按钮，而且将工具栏高度完全锁定在单行 44px 之内。

3. **双套 4 宫格合并与持仓表提权（对应 R2 Tab 2 模块 2）**：
   - 原先上方有 `render_portfolio_cushion_and_stress_card_html`（浮盈安全垫 4 格 + 文本），紧接着有蒙特卡洛 3D 曲面图，再下方又有 `t2_c1~t2_c4`（持仓市值/现金池/累计盈亏/锁仓概览 4 卡），累计垂直高度超过 600px，持仓表直接被挤出屏幕。
   - 解决方案：
     - 将重复的两套 4 宫格彻底合二为一，生成单一干练的 4 格资产安全垫顶栏：
       - 格 1：💼 持仓总市值（仓位占比、总资产基线、持仓只数）
       - 格 2：💵 可用现金池（现金比、在途资金、备用缓冲状态）
       - 格 3：📈 累计浮动盈亏（浮盈率、今日预估盈亏与涨跌幅）
       - 格 4：🛡️ 综合安全垫厚度与破净防线（加权 Beta、安全垫厚度及占比、沪深300破净/回本临界点，卡片底部附带紧凑 `<details>` 可点击展开 -3%/-5%/-10% 三级抗震承压情景推演）
     - 将实盘持仓蒙特卡洛 3D 曲面图（`render_monte_carlo_3d_chart`）收纳进紧凑的展开折叠框或点击弹层中，避免无谓霸占首屏。
     - 在 4 格顶栏正下方零间距直接展示可编辑实时持仓资产明细表（`st.data_editor`），配合下方紧凑的操作条（保留 `btn_save_holdings_tab2`, `btn_confirm_cash_pop_tb`, `btn_sync_holdings_tab2`, `btn_pop_del_confirm_tab2`, `btn_dl_csv_tab2`）。
     - 此时用户打开 Tab 2 第一眼就能看全资产底盘与全部持仓标的，实现真正的首屏即操作。

4. **调仓裁决与执行单合流（对应 R2 Tab 2 模块 3）**：
   - 原先用户必须先在步骤一底部点击“诊断今日调仓时机”，跳出步骤二看 4 张裁决卡，再点击“模拟调仓方案与成本”，跳出步骤三看 4 张后果卡，再滑到最底部看执行单，经历 3 阶段跳跃。
   - 解决方案：
     - 在持仓表正下方，仅保留主操作按钮：“🔍 诊断并生成调仓方案”（`btn_tab2_diagnose`，同时兼容 `btn_tab2_all`），旁边并排保留全局唯一的调仓缓冲带滑块 `tab2_rebal_buf_slider`。
     - 点击该按钮后，系统在后台一次性运行健康诊断与调仓路径推演（设置 `tab2_diagnosed=True` 与 `tab2_rebalanced=True`），无需二次点击。
     - 将原本散落的 4 张时机裁决卡与 4 张调仓后果卡收敛合并为**单行紧凑 4 格调仓摘要条**：
       - 格 1：🎯 时机裁决结论（今日维持底仓或建议调仓，附带均线状态与最大偏离度）
       - 格 2：💸 手续费直接损耗（总损耗金额、赎回费/申购费、是否包含 1.5% 惩罚费）
       - 格 3：⏳ T+2在途踏空风险（在途资金、同公司转换免在途节省）
       - 格 4：🛡️ 攻防与回撤变化（波动率前后变化、回撤水位前后变化、组合股息垫）
     - 摘要条正下方紧贴展示《调仓建议执行表》（`df_orders_tbl` 10 列表）及一键跟单打卡按钮（`btn_confirm_follow_rebalance_tab2`），买入标的 VWAP 调度表（`sel_tab2_vwap_schedule_item`）及流动性折价表（`render_liquidity_haircut_table`）置于紧凑折叠项内按需查看。
     - 彻底清除全页多处重复的“调仓净效用门禁精算”蓝色小作文文本框与说教式段落。

---

## 3. 需注意的约束与兼容陷阱 (Caveats)

1. **测试契约硬性静态检查点**：
   - `rad_tab2_view_mode` 与 `is_t2_main_mode`：必须保持原有变量名与 `if is_t2_main_mode: ... else: ...` 严格语法树分支结构，禁止改动分支名称。
   - `dock_tab1, dock_tab2, dock_tab3, dock_tab4, dock_tab5, dock_tab6` 以及 `sub_tab1, sub_tab2, sub_tab3`：必须严格保留在 `else:` 运维工具坞分支内部，主流程模式下绝不定义。
   - `tab2_rebal_buf_slider` 与 `# tab2_rebal_buf_slider_bot`：`tab2_rebal_buf_slider` 全局正则匹配必须恰好出现 1 次；`# tab2_rebal_buf_slider_bot` 兼容注释必须存在。
   - 按钮键名保留：`btn_bar_add_holding`、`btn_confirm_cash_pop_tb`、`btn_sync_holdings_tab2`、`btn_pop_del_confirm_tab2`、`btn_save_holdings_tab2`、`btn_tab2_sync`、`btn_tab2_load_demo`、`btn_tab2_undo`、`btn_confirm_follow_rebalance_tab2` 均有静态或动态测试依赖，必须保留。
   - `sel_tab2_vwap_schedule_item` 与 `vwap_rebal_orders`：必须保留在调仓执行结果中，供 `test_g3_evolution_loop.py` 校验。
   - `render_monte_carlo_3d_chart` 与 `render_liquidity_haircut_table`：必须在 Tab 2 中被调用，满足 `test_g10_correlation_liquidity_and_stress.py` 断言。
   - `<b>{len(pm.holdings)} 只</b>`：在 `dock_tab2`（L6167）中已存在，切勿误删。
2. **状态机回退保护**：
   - 切换账本时需重置 `tab2_diag_cache`、`tab2_rebal_cache`、`tab2_diagnosed`、`tab2_rebalanced` 为空/False。
   - 未保存表格修改前置检测：在极速录基、修改现金、同步、诊断等操作前，必须保留 `_commit_edited_holdings_table` 自动提交钩子，防止用户编辑丢失。

---

## 4. 结论与具体实施方案 (Conclusion & Implementation Blueprint)

### 4.1 总体架构改造对比

| 区域 / 模块 | 重构前现状 (G10 世代) | 重构后形态 (G11 世代三块式) | 优化效益 |
| :--- | :--- | :--- | :--- |
| **顶部导引** | `render_workflow_step_indicator` + caption | 彻底移除指示器与 caption，仅保留 `st.subheader("💼 持仓调仓")` | 节省 60px 垂直高度，心智无阻断 |
| **模块 1<br>(全能工具栏)** | 4 处分散工具条（4 列账本栏 + 单选视图 + 3 列环境按钮 + 独立录基吧台）占用多行 | 单行 5 栏内联工具栏：① 账本切换、② 双视图切换、③ ➕极速录基 Popover、④ 🔄同步估值、⑤ ⚙️账本与环境管理 Popover | 整合 8 个分散按钮，平时零占高，高度缩减至 44px |
| **模块 2<br>(顶栏+持仓表)** | 上下叠床架屋的两套 4 宫格（安全垫看板 4 格 + 概览 4 卡）+ 暴露在外的 3D 曲面图 | 合二为一的单排 4 格资产安全垫顶栏（市值、现金、浮盈、安全垫），曲面图收起，正下方零间距贴合实时持仓明细大表 | 纵向缩短 400px+，持仓表直接居于首屏黄金视野 |
| **模块 3<br>(调仓裁决与执行)** | 步骤二与步骤三多处切断，2 处 Net Utility 蓝框，8 张散落卡片，中间夹杂推进按钮 | 仅保留“诊断并生成调仓方案”主按钮与滑块；一键生成 4 格摘要条（时机、费率、在途、攻防）+ 10 列执行单大表 + 一键跟单打卡 | 削减 75% 重复卡片与小作文，一步直达交易清单 |

---

### 4.2 详细代码级修改规划

#### 步骤 1：移除顶部向导条与 caption
- 定位：`AGY2_FundAdvisory/app_gui.py` L4656 - L4685。
- 动作：
  - 保留 `st.subheader("💼 持仓调仓")`；
  - 删除 `st.caption(...)`；
  - 保留状态机初始化代码（`tab2_diagnosed`、`tab2_rebalanced` 等）；
  - 删除 `render_workflow_step_indicator(...)` 及计算 `step_tab2` 的代码；
  - 保留顶部主动风控指令横幅（若存在未满 7 天锁仓等紧急指令）。

#### 步骤 2：重构模块 1（单行全能账本工具栏）
- 定位：`AGY2_FundAdvisory/app_gui.py` L4720 - L4916。
- 动作：
  - 删除 `st.markdown("### 步骤一：持仓账本")`；
  - 构造单行容器：
    ```python
    col_tb_led, col_tb_mode, col_tb_quick, col_tb_sync, col_tb_mgr = st.columns([2.6, 3.2, 1.4, 1.3, 1.5])
    ```
  - `col_tb_led`: 账本切换 `st.selectbox`（key=`f"sel_tab2_ledger_picker_{active_lid}"`）；
  - `col_tb_mode`: 视图模式切换 `st.radio`（key=`"rad_tab2_view_mode"`）；
  - `col_tb_quick`: `with st.popover("➕ 极速录基", use_container_width=True):`，移入 `bar_fund_input`、`bar_amt_input`、`bar_pnl_input`、`bar_dur_choice` 及 `btn_bar_add_holding` 的全部逻辑；
  - `col_tb_sync`: `st.button("🔄 同步估值", key="btn_tab2_sync", type="primary")`；
  - `col_tb_mgr`: `with st.popover("⚙️ 账本与环境管理", use_container_width=True):`，收纳新建账本、克隆副本、重命名、删除、`btn_tab2_load_demo`（载入演示组合）、`btn_tab2_undo`（撤销修改）以及家庭资产汇总表。
  - 删除原本散落在外部的 `col_t2_env1, col_t2_env2, col_t2_env3`。

#### 步骤 3：重构模块 2（合一 4 格资产安全垫顶栏 + 实时持仓大表）
- 定位：`AGY2_FundAdvisory/app_gui.py` L4861 - L5321。
- 动作：
  - 计算资产指标（`_tot_equity`、`_t2_mkt`、`_t2_cost`、`_t2_pnl`、`_pos_pct` 等）与安全垫模型（`cushion_model = pm.calculate_portfolio_cushion_and_stress_model(...)`）；
  - 删除上下分离的两套 4 宫格（`render_portfolio_cushion_and_stress_card_html` 与 `t2_c1~t2_c4`）；
  - 渲染精炼合一的 4 格卡片：
    - 格 1：持仓总市值（仓位占比、总资产、持仓只数）
    - 格 2：可用现金池（现金比、在途资金）
    - 格 3：累计浮动盈亏（浮盈率、今日预估盈亏）
    - 格 4：综合安全垫厚度（加权 Beta、安全垫厚度、破净/回本临界点，卡片下方内嵌 `<details>` 展开 -3%/-5%/-10% 情景推演）
  - 实盘持仓蒙特卡洛 3D 曲面图（`render_monte_carlo_3d_chart`）封装入可折叠组件：
    ```python
    with st.expander("🔬 查看实盘持仓蒙特卡洛极端承压 3D 分布曲面图", expanded=False):
        render_monte_carlo_3d_chart(real_stress_data)
    ```
  - 紧贴顶栏正下方渲染持仓明细表：
    - 呈现 `warn_placeholder = st.empty()`；
    - 渲染 `edited_table = st.data_editor(..., key="main_holdings_editor_tab2")`；
    - 紧跟 5 栏轻量操作工具条（保存 `btn_save_holdings_tab2`、现金修改 `pop_edit_cash_pool_tb` + `btn_confirm_cash_pop_tb`、同步 `btn_sync_holdings_tab2`、导出 CSV `btn_dl_csv_tab2`、删除标的 `pop_del_sel_tab2` + `btn_pop_del_confirm_tab2`）。

#### 步骤 4：重构模块 3（调仓裁决与执行单一键合流）
- 定位：`AGY2_FundAdvisory/app_gui.py` L5296 - L6018。
- 动作：
  - 在持仓表操作栏正下方，仅保留一行控制栏：
    - 主操作按钮：“🔍 诊断并生成调仓方案”（`btn_tab2_diagnose`，同时提供 `btn_tab2_all` 兼容触发），点击后自动同步表格并执行：
      ```python
      st.session_state.tab2_diagnosed = True
      st.session_state.tab2_rebalanced = True
      st.session_state.tab2_trigger_diagnose = True
      st.session_state.tab2_trigger_rebalance = True
      ```
    - 调仓缓冲带滑块：`tab2_rebal_buf_slider`（步长 0.5%，范围 1.0%~5.0%，标注 `# tab2_rebal_buf_slider_bot` 兼容注释）；
  - 触发后，删除原本的“### 步骤二：时机裁决”、“### 步骤三：方案执行”两级标题，删除中间多余的“⚖️ 模拟调仓方案与成本”二次按钮；
  - 将 4 张时机裁决卡与 4 张后果卡合并为单行 4 格调仓摘要条：
    - 格 1：🎯 时机裁决结论（今日定调、均线偏离）
    - 格 2：💸 手续费损耗（包含 7 天免罚金核验）
    - 格 3：⏳ T+2 在途踏空风险（在途天数、同公司免在途节省）
    - 格 4：🛡️ 攻防回撤变化（波动率、极端回撤变化、股息垫）
  - 摘要条正下方紧贴展示《调仓建议执行表》（`df_orders_tbl` 10 列表）及“✅ 我已在手机端按此方案下单 ➔ 一键将调仓单同步至当前账本持仓”（`btn_confirm_follow_rebalance_tab2`）；
  - 将买入标的 VWAP 5 阶段挂单调度表（`sel_tab2_vwap_schedule_item`）及大额流动性折价明细表（`render_liquidity_haircut_table`）置于紧凑折叠项内；
  - 彻底清理全页 3 处重复的“调仓净效用门禁精算”蓝色小作文框及盘后冗长说教文本框。

---

## 5. 独立验证方法 (Verification Method)

### 5.1 自动化测试验证命令
在实施修改后，执行针对 Tab 2 布局、交互及多账本状态机的精准自动化回归测试：
```powershell
py -3 -m pytest tests/test_g8_ux_and_realtime_fusion.py tests/test_gui_multi_ledger_stress.py tests/test_g3_evolution_loop.py -k "tab2 or ledger or vwap" -q
```
要求：所有用例 100% 绿灯通过，无断言失败。

### 5.2 关键静态红线扫描 (AST / 正则核验)
1. 验证 `render_workflow_step_indicator` 在 Tab 2 内已彻底移除：
   ```powershell
   py -3 -c "code = open('AGY2_FundAdvisory/app_gui.py', encoding='utf-8').read(); t2 = code.split('with tab_holdings_and_rebalance:')[1].split('def render_tab3')[0]; assert 'render_workflow_step_indicator' not in t2; print('OK: Step indicator removed from Tab 2')"
   ```
2. 验证滑块全局唯一且包含兼容注释：
   ```powershell
   py -3 -c "import re; code = open('AGY2_FundAdvisory/app_gui.py', encoding='utf-8').read(); assert len(re.findall(r'key=[\"\']tab2_rebal_buf_slider[\"\']', code)) == 1; assert '# tab2_rebal_buf_slider_bot' in code; print('OK: Single buffer slider verified')"
   ```
3. 验证关键按钮键与组件完整驻留：
   ```powershell
   py -3 -c "code = open('AGY2_FundAdvisory/app_gui.py', encoding='utf-8').read(); keys = ['btn_bar_add_holding', 'btn_confirm_cash_pop_tb', 'btn_sync_holdings_tab2', 'btn_pop_del_confirm_tab2', 'btn_tab2_sync', 'btn_tab2_load_demo', 'btn_tab2_undo', 'btn_confirm_follow_rebalance_tab2', 'sel_tab2_vwap_schedule_item']; [assert k in code, f'Missing {k}' for k in keys]; print('OK: All required button and component keys present')"
   ```

### 5.3 运行时健康与多模态视觉走查 (浏览器核验)
- 启动服务后调用 `/browser` 访问 `http://localhost:8501`：
  - 点击 Tab 2（💼 持仓调仓）：在 1920x1080 标准桌面分辨率下，首屏（无需向下滚动）必须能完整看到：单行全能工具栏、合一的 4 格资产安全垫顶栏、以及实时持仓明细大表；
  - 点击“➕ 极速录基”确认弹出 Popover 输入表单，录完即合，平时不占用垂直空间；
  - 点击“⚙️ 账本与环境管理”确认集中集成了新建、克隆、重命名、删除、演示组合与撤销操作；
  - 点击“🔍 诊断并生成调仓方案”确认一步直出 4 格调仓摘要条与 10 列调仓建议执行单，无中间二次点击阻断，全屏无裸露小作文或重复蓝色框。
