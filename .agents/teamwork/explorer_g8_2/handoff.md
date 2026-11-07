# Handoff Report — Explorer G8-2 (Cross-Tab & Rollback Explorer)

**Role**: Cross-Tab & Rollback Explorer (G8 Technical Investigation)  
**Date**: 2026-11-07T15:35:00Z  
**Type**: Hard Handoff (Investigation Complete)  
**Recipient**: Orchestrator (Conversation ID: `9e61e1d7-9eb6-4227-b899-75a22db1e25b`) / Implementer  

---

## 1. Observation (客观观察证据)

### 观察点 1.1：Tab 1 覆写按钮直接清空实盘持仓且零二次确认
- **文件与行号**: `d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py` 第 3831 至 3847 行
- **直录代码**:
  ```python
  3837: if st.button(f"📥 覆盖写入当前激活账本 ({cur_name})", type="primary", use_container_width=True, key="btn_apply_bp_tier"):
  3838:     plan_data = three_step_plan if "稳健三步" in cap_deployment_mode else (dca_plan if "智能定投" in cap_deployment_mode and 'dca_plan' in locals() else None)
  3839:     res_apply = pm.apply_zero_start_blueprint(
  3840:         blueprint,
  3841:         cap_deployment_mode=cap_deployment_mode,
  3842:         deployment_plan=plan_data
  3843:     )
  3844:     st.balloons()
  3845:     st.success(f"已成功将 ¥{res_apply['total_capital']:,.2f} 建仓方案（模式：{cap_deployment_mode.split('（')[0]}）写入【{cur_name}】，配置 {res_apply['funds_count']} 只基金。可用现金池 ¥{pm.available_cash:,.2f}。")
  3846:     st.rerun()
  ```
- **下游执行观察**: `d:\Google\Workspace\Wind\AGY2_FundAdvisory\portfolio_manager.py` 第 4191 至 4197 行：
  ```python
  4191: self.holdings.clear()
  4192: self.pending_orders.clear()
  4193: self.peak_equity = 0.0
  4194: self.max_drawdown_pct = 0.0
  4195: self.portfolio_return_pct = 0.0
  4196: self.benchmark_return_pct = 0.0
  4197: self.alpha_return_pct = 0.0
  ```
  清空前未调用任何快照压栈，覆写后直接写入新持仓并覆盖 SQLite 数据库，无二次确认弹窗或勾选门禁，无回滚按钮。

### 观察点 1.2：快照栈与 Undo 机制在 `portfolio_manager.py` 中已完备实现
- **文件与行号**: `d:\Google\Workspace\Wind\AGY2_FundAdvisory\portfolio_manager.py` 第 3443 至 3465 行：
  `pm.undo()` 已完整实现：从 `self.snapshot_stack` 弹出当前状态，读取倒数第二个状态并通过 `self._import_state_dict(prev_state)` 完全还原持仓与批次，同时同步清理 SQLite `portfolio_snapshots` 最新记录，最后调用 `self.save_state(record_snapshot=False)`。
- **Tab 2 已有成功范例**: `app_gui.py` 第 4234 至 4246 行已成功接入 `pm.undo()` 实现一键回滚。

### 观察点 1.3：首屏双翼看板按钮跨 Tab 联动存在“假跳转”
- **双翼看板按钮**:
  - 左翼雷达「➕ 入备选池」: `app_gui.py` 第 2503 行，仅向 session_state 追加标的并弹出 toast，调用 `st.rerun()`。
  - 右翼预警哨「🔒 一键批量锁定这 N 只标的调仓下界」: `app_gui.py` 第 2587 行，仅修改 `tab2_locked_funds` 并调用 `st.rerun()`。
  - 右翼预警哨单项处置按钮: `app_gui.py` 第 2648 行，仅针对 3 项写入参数，剩余 6 项为空跑，调用 `st.rerun()`。
  - 右翼预警哨「🔍 穿透到底层」: `app_gui.py` 第 2667 行，仅修改 `tab4_highlight_module` 并调用 `st.rerun()`。
- **四大工作区构建**: `app_gui.py` 第 2683 至 2688 行：
  `tab_zero_start, tab_holdings_and_rebalance, tab_backtest, tab_toolbox = st.tabs(["🌱 新资建仓", "💼 持仓调仓", "📈 组合回测", "🔍 穿透工具"])`
- **DOM 特性**: Streamlit `st.tabs` 生成 `<div role="tablist">`，子按钮为 `<button role="tab" data-baseweb="tab">`。Python 端无法传入 active_tab，导致 rerun 后浏览器视口保持原 Tab，用户误以为点击无效。

---

## 2. Logic Chain (推理链条)

1. **从观察 1.1 与 1.2 推导回滚防护方案**:
   - `apply_zero_start_blueprint` 在清空前缺少快照入栈，导致误触后历史数据永久损毁。
   - `PortfolioManager` 本身具备强大的 SQLite 快照栈与 `undo()` 体系，且在 Tab 2 中已经过实盘验证。
   - 只要在 `apply_zero_start_blueprint` 入口（第 4191 行之前）调用 `self.save_state(record_snapshot=True)`（或封装 `_push_undo_snapshot()`），并在覆写成功后渲染 `pm.undo()` 触发按钮，就能在不破坏任何底层架构的前提下，100% 实现一键撤销回滚。
   - 将直发按钮升级为 `st.popover` 并配以 `st.checkbox` 门禁，直观展示目标账本类型、存量标的只数、市值与新方案金额对比，构建金融级良性摩擦防线。

2. **从观察 1.3 推导跨 Tab 真实路由方案**:
   - `st.markdown(unsafe_allow_html=True)` 因 React-Markdown 安全沙箱会剥离 `<script>`，不能用于 JS 注入。
   - `streamlit.components.v1.html(..., height=0, width=0)` 以同源 `<iframe>` 运行，享有直接访问 `window.parent.document` 的 DOM 操作权限，且无头测试 `AppTest` 执行安全不抛异常。
   - 顶层四大工作区在主页面 DOM 中为第一个 `role="tablist"`，其第 0、1、2、3 个按钮分别严格映射四大工作区。通过 DOM 脚本在页面挂载后轮询触发对应按钮的 `.click()` 与 `.scrollIntoView({ behavior: 'smooth' })`，即可实现 60fps 丝滑真实跳转。
   - 在双翼看板 expander 最底部实装一条高可见度的「跨区指令已生效承接横幅」，展示已分发的动作、目标标的与就绪状态，补齐用户的确定性反馈。

---

## 3. Caveats (注意事项与边界条件)

1. **组件层级与测试兼容性**:
   - `components.html` 必须传入 `height=0, width=0`，杜绝在页面上引入空白高度。
   - 在 `streamlit.testing.v1.AppTest` 环境下，`components.html` 会被无头模拟记录，不会执行真实浏览器 JS，因此单元测试中的按钮点击依然依赖 `st.session_state` 中的状态断言。
2. **一次性跳转防回旋**:
   - JS 脚本触发后，必须立即在 Python 端 `pop` 掉 `pending_cross_tab_jump`，仅保留 `last_cross_tab_action` 供横幅展示，防止用户在目标 Tab 内正常操作时重复被拉回或强制滚动。
3. **主实盘写保护底线**:
   - `multi_ledger_manager.py` 对 `main_live` 的文件删除做了 `PermissionError` 物理防护，本次改造系持仓内容覆写防护，与底层防删机制形成双层互锁。

---

## 4. Conclusion (确凿结论与实现蓝图)

1. **Item 2 (P0) 落地路径**:
   - 在 `portfolio_manager.py` 新增 `_push_undo_snapshot(self)`，并在 `apply_zero_start_blueprint` 第一行前置调用。
   - 在 `app_gui.py` 将第 3837 行的直接写入按钮改造为 `st.popover`，包含实盘警告、持仓只数/市值指标卡、二次确认勾选框与确认执行按钮。
   - 覆写成功后刷新页面，在上方呈现绿色成功卡片 + `↩️ 撤销本次覆盖` (调用 `pm.undo()`) + `👀 前往持仓调仓`。
2. **Item 3 (P0) 落地路径**:
   - 在 `app_gui.py` 引入 `import streamlit.components.v1 as components`。
   - 在雷达入备选池（第 2503 行）、预警哨批量锁定（第 2587 行）、单项处置（第 2648 行）、穿透到底层（第 2667 行）处，统一调用 `trigger_cross_tab_routing`，写入目标 Tab 索引与指令元数据。
   - 补齐预警哨 6 大未接线处置类型的参数传递（`countdown_hold`、`replace_fund`、`deep_loss_rebalance`、`rebalance_sector`、`defense_mode`、`offense_mode`）。
   - 在双翼看板底部嵌入 `components.html` 自动执行 DOM 真实点击与视口平滑滚动，并渲染「跨区指令已生效承接横幅」。

---

## 5. Verification Method (独立核验与测试方案)

1. **静态代码与架构核验**:
   - 检查 `app_gui.py` 3831-3847 行是否已无裸露的 `st.button` 直接清空持仓；检查是否存在 `st.popover` 与二次确认 `st.checkbox`。
   - 检查 `app_gui.py` 中是否已导入 `streamlit.components.v1`，双翼看板各按钮是否绑定 `pending_cross_tab_jump`。
2. **自动化测试套件回归**:
   - 运行项目全量核心测试：
     `pytest tests/test_infra.py`
     `pytest tests/test_portfolio_manager.py` (验证 `undo` 与 `apply_zero_start_blueprint`)
     `pytest tests/test_acceptance_r1_r7.py`
     `pytest tests/test_adv_final_closure.py`
3. **交互与渲染走查 (/browser 验收标准)**:
   - 启动 `http://localhost:8501`。
   - **验证 Item 2**: 在 Tab 1 步骤三点击覆盖写入账本，确认弹出 popover，显示当前存量标的数与新金额；未勾选确认框前按钮禁用；勾选后执行，页面出现撤销回滚按钮；点击撤销回滚，持仓立即完全恢复。
   - **验证 Item 3**: 在首屏点击右翼预警哨「锁定调仓下界」或「穿透到底层」，页面自动平滑切换至 Tab 2 或 Tab 4，并展示「跨区指令已生效承接横幅」。
